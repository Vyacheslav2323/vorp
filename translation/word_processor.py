"""
OpenAI-based Word Processor
— Returns base-form & translation for every surface token
— First pass with GPT-3.5-turbo (cheap), second pass with GPT-4-turbo only
  for the tokens that came back blank.
"""

import json
import logging
import re
from typing import Dict, List

from django.conf import settings
from openai import OpenAI

logger = logging.getLogger(__name__)


# ───────────────────────────────────────────────────────────────
# Helper – build a strict prompt
# ───────────────────────────────────────────────────────────────
_PROMPT_TEMPLATE = """
You are a Korean-English vocabulary normaliser.

Return ONE JSON object whose keys are **exactly** the surface tokens supplied
by the user (unchanged, including particles, punctuation, quotes).

For every key provide:
  "base"    — dictionary form (verbs/adjectives end in -다; nouns without particles)
  "meaning" — concise English gloss.
              • If the word is a verb, start with "to " (e.g. "to eat").

Return nothing but valid JSON.
""".strip()


def _make_call(
    client: OpenAI,
    tokens: List[str],
    model: str = "gpt-3.5-turbo",
) -> Dict[str, Dict[str, str]]:
    """Call OpenAI once and parse JSON."""
    message_user = "Surface tokens (one per line):\n" + "\n".join(tokens)
    rsp = client.chat.completions.create(
        model=model,
        temperature=0,
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": _PROMPT_TEMPLATE},
            {"role": "user", "content": message_user},
        ],
    )
    return json.loads(rsp.choices[0].message.content)


# ───────────────────────────────────────────────────────────────
# Main class
# ───────────────────────────────────────────────────────────────
class WordProcessor:
    def __init__(self) -> None:
        api_key = settings.OPENAI_API_KEY
        if not api_key:
            raise ValueError("OpenAI API key is not set. Please set OPENAI_API_KEY in your environment.")
        
        # Initialize the OpenAI client with proper API key
        self.client = OpenAI(
            api_key=api_key,
            max_retries=3,  # Add some retries for robustness
            timeout=30.0    # Set a reasonable timeout
        )
        self._cache: Dict[str, Dict] = {}

    # -----------------------------------------------------------
    # Public: analyse a text string
    # -----------------------------------------------------------
    def get_vocabulary_forms_from_text(self, text: str) -> Dict[str, Dict[str, str]]:
        """
        Map each surface word to {'vocabulary_form': base, 'translation': meaning}.
        Guarantees both fields are non-empty, else raises.
        """
        if not text.strip():
            return {}
        
        cache_key = f"text_analysis_{hash(text)}"
        if cache_key in self._cache:
            return self._cache[cache_key]
        
        # 1️⃣ deduplicate surface tokens
        surface_tokens: List[str] = []
        seen = set()
        for tok in re.findall(r"[가-힣]+", text):
            if tok not in seen:
                surface_tokens.append(tok)
                seen.add(tok)
        if not surface_tokens:
            return {}
            
        # 2️⃣ first, cheap pass with GPT-3.5
        analysis = _make_call(self.client, surface_tokens, model="gpt-3.5-turbo")

        # 3️⃣ identify any tokens with blank base/meaning
        needs_retry = [
            tok
            for tok in surface_tokens
            if tok not in analysis
            or not analysis[tok].get("base")
            or not analysis[tok].get("meaning")
        ]

        # 4️⃣ retry only the problematic ones with GPT-4-turbo
        if needs_retry:
            logger.info("Retrying %d tokens with GPT-4-turbo: %s", len(needs_retry), needs_retry)
            retry = _make_call(self.client, needs_retry, model="gpt-4-turbo-preview")
            analysis.update(retry)

        # 5️⃣ final validation
        blanks = [
            k
            for k in surface_tokens
            if k not in analysis
            or not analysis[k].get("base")
            or not analysis[k].get("meaning")
        ]
        if blanks:
            raise ValueError(f"OpenAI returned empty base/meaning for: {', '.join(blanks)}")

        # 6️⃣ build result mapping
        result: Dict[str, Dict[str, str]] = {}
        for tok in surface_tokens:
            base = analysis[tok]["base"].strip()
            meaning = analysis[tok]["meaning"].strip()
            if base.endswith("다") and not meaning.startswith("to "):
                meaning = f"to {meaning}"
            result[tok] = {"vocabulary_form": base, "translation": meaning}

        self._cache[cache_key] = result
        return result

    # -----------------------------------------------------------
    # Remaining methods are unchanged from your last version
    # -----------------------------------------------------------
    @staticmethod
    def match_with_vocabulary(
        word_analysis: Dict[str, Dict[str, str]],
        user_vocabulary: Dict[str, Dict[str, str]],
    ) -> Dict[str, Dict[str, str]]:
        matched = {}
        for surf, info in word_analysis.items():
            base = info["vocabulary_form"]
            status = user_vocabulary.get(base, {}).get("status", "unknown")
            matched[surf] = {
                "vocabulary_form": base,
                "translation": info["translation"],
                "status": status,
            }
        return matched

    def process_text_for_vocabulary_test(
        self, text: str, user_vocabulary: Dict[str, Dict[str, str]]
    ) -> Dict:
        analysis = self.get_vocabulary_forms_from_text(text)
        matched = self.match_with_vocabulary(analysis, user_vocabulary)

        tokens = self._tokenize_text(text)
        stats = {"learned": 0, "learning": 0, "unknown": 0}
        processed = []

        for tok in tokens:
            if re.match(r"[가-힣]+", tok):
                entry = matched.get(tok, {"status": "unknown", "vocabulary_form": tok, "translation": ""})
                stats[entry["status"]] += 1
                processed.append(
                    {
                        "word": tok,
                        "status": entry["status"],
                        "vocabulary_form": entry["vocabulary_form"],
                        "translation": entry["translation"],
                        "is_korean": True,
                    }
                )
            else:
                processed.append(
                    {"word": tok, "status": "", "vocabulary_form": "", "translation": "", "is_korean": False}
                )

        html = self._generate_html(processed)
        return {
            "processed_tokens": processed,
            "stats": stats,
            "html": html,
            "word_analysis": analysis,
            "matched_words": matched,
        }

    @staticmethod
    def _tokenize_text(text: str) -> List[str]:
        pattern = r"([가-힣]+|[a-zA-Z]+|\d+|[^\w\s]|\s+)"
        return re.findall(pattern, text)
    
    @staticmethod
    def _generate_html(processed_tokens: List[Dict[str, str]]) -> str:
        html = []
        for t in processed_tokens:
            if t.get("is_korean"):
                wid = f"word_{hash(t['word'])}"
                html.append(
                    f'<span class="word-{t["status"]}" '
                    f'data-word-id="{wid}" '
                    f'data-word="{t["word"]}" '
                    f'data-status="{t["status"]}" '
                    f'data-vocabulary-form="{t["vocabulary_form"]}" '
                    f'data-translation="{t["translation"]}">'
                    f'{t["word"]}</span>'
                )
            else:
                html.append(t["word"])
        return "".join(html)
        

# -----------------------------------------------------------------
word_processor = WordProcessor() 
