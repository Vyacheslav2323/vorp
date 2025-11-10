from openai import OpenAI
import json
import os

def get_openai_client():
    api_key = os.getenv('OPENAI_API_KEY')
    if not api_key:
        raise ValueError("OPENAI_API_KEY environment variable is not set")
    return OpenAI(api_key=api_key)

def translation_api_call(text, speaker_lang, listener_lang):
    client = get_openai_client()
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": f"Translate the following text from {speaker_lang} to {listener_lang}. Return only the translation, no explanations:\n\n{text}"}],
        temperature=0.1
    )
    return response.choices[0].message.content.strip()

def translate_vocab_batch(sentence, base_pos_pairs, target_languages):
    client = get_openai_client()
    words_list = [f"{base} ({pos})" for base, pos in base_pos_pairs]
    words_str = "\n".join(words_list)
    langs_str = ", ".join(target_languages)
    
    prompt = f"""Given this Korean sentence: "{sentence}"

Translate each of the following Korean words (with their part-of-speech tags) into all target languages ({langs_str}).

Words to translate:
{words_str}

Return a JSON object where each key is "base|pos" and the value is an object with keys for each target language. Example format:
{{
  "word1|POS1": {{"en": "translation", "ru": "перевод", "zh": "翻译", "vi": "bản dịch"}},
  "word2|POS2": {{"en": "translation", "ru": "перевод", "zh": "翻译", "vi": "bản dịch"}}
}}

Return only valid JSON, no explanations."""
    
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.1,
        response_format={"type": "json_object"}
    )
    
    result_text = response.choices[0].message.content.strip()
    parsed = json.loads(result_text)
    
    translations = {}
    for base, pos in base_pos_pairs:
        key = f"{base}|{pos}"
        if key in parsed:
            translations[(base, pos)] = parsed[key]
        else:
            translations[(base, pos)] = {lang: "" for lang in target_languages}
    
    return translations

if __name__ == "__main__":
    text = "Hi! How are you doing?"
    speaker_lang = "en"
    listener_lang = "vi"
    print(translation_api_call(text, speaker_lang, listener_lang))