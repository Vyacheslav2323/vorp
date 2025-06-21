"""
Service for managing Korean vocabulary analysis and translations
"""

import logging
import re
from typing import Dict, List, Tuple
from django.conf import settings
from openai import OpenAI

from .word_processor import word_processor

logger = logging.getLogger(__name__)


class VocabularyService:
    """Service for managing Korean vocabulary"""

    def __init__(self):
        self.client = OpenAI(api_key=settings.OPENAI_API_KEY)

    def get_vocabulary_form_and_translation(
        self, text: str, language: str = "ko", context: str = ""
    ) -> Tuple[str, str]:
        """
        Given a single Korean word (text) and optional surrounding context,
        return (base_form, translation). If `text` is not found exactly,
        try stripping leading/trailing punctuation and whitespace before lookup.
        """

        # 1️⃣ If the caller provided a larger context, run analysis on that;
        #    otherwise, analyse the single word itself.
        source = context if context.strip() else text
        analysis: Dict[str, Dict[str, str]] = word_processor.get_vocabulary_forms_from_text(source)

        # 2️⃣ Direct lookup: the service expects 'text' as one of the keys
        if text in analysis:
            data = analysis[text]
            return data.get("vocabulary_form", ""), data.get("translation", "")

        # 3️⃣ Try stripping common punctuation/whitespace around 'text'
        stripped = re.sub(r"^[^\w가-힣]+|[^\w가-힣]+$", "", text)
        if stripped and stripped in analysis:
            data = analysis[stripped]
            return data.get("vocabulary_form", ""), data.get("translation", "")

        # 4️⃣ As a last resort, try matching purely on the Hangul letters inside 'text'
        #    (e.g. drop any English letters or stray symbols)
        hangul_only = "".join(re.findall(r"[가-힣]+", text))
        if hangul_only in analysis:
            data = analysis[hangul_only]
            return data.get("vocabulary_form", ""), data.get("translation", "")

        # 5️⃣ If still not found, log a warning and return empty strings
        logger.warning(
            "VocabularyService: word '%s' not found in analysis keys %s",
            text,
            list(analysis.keys()),
        )
        return "", ""


# Global instance
vocabulary_service = VocabularyService()
