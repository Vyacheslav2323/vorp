from deep_translator import GoogleTranslator

def translate_text(text, from_code, to_code):
    translator = GoogleTranslator(source=from_code, target=to_code)
    return translator.translate(text)

def translate_en_to_ko(text):
    return translate_text(text, "en", "ko")

def translate_en_to_ru(text):
    return translate_text(text, "en", "ru")

def translate_en_to_zh(text):
    return translate_text(text, "en", "zh-CN")

def translate_en_to_vi(text):
    return translate_text(text, "en", "vi")

def translate_ko_to_en(text):
    return translate_text(text, "ko", "en")

def translate_ko_to_ru(text):
    return translate_text(text, "ko", "ru")

def translate_ko_to_zh(text):
    return translate_text(text, "ko", "zh-CN")

def translate_ko_to_vi(text):
    return translate_text(text, "ko", "vi")

def test_english_translations():
    test_sentence = "How have you been?"
    results = []
    
    ko_result = translate_en_to_ko(test_sentence)
    ru_result = translate_en_to_ru(test_sentence)
    zh_result = translate_en_to_zh(test_sentence)
    vi_result = translate_en_to_vi(test_sentence)
    
    results.append(f"English → KO: {ko_result}")
    results.append(f"English → RU: {ru_result}")
    results.append(f"English → ZH: {zh_result}")
    results.append(f"English → VI: {vi_result}")
    
    return results

def test_korean_translations():
    korean_sentence = '''합성 데이터에 시간(time) 과 위치(location) 변수를 추가하겠습니다.

Exploitation(활용) 은 동일하게 유지하되, Exploration(탐색) 은 ① 유사도(similarity), ② 위치(location), ③ 시간(time)을 함께 고려하도록 하겠습니다.'''
    results = []
    
    en_result = translate_ko_to_en(korean_sentence)
    ru_result = translate_ko_to_ru(korean_sentence)
    zh_result = translate_ko_to_zh(korean_sentence)
    vi_result = translate_ko_to_vi(korean_sentence)
    
    results.append(f"Korean → EN: {en_result}")
    results.append(f"Korean → RU: {ru_result}")
    results.append(f"Korean → ZH: {zh_result}")
    results.append(f"Korean → VI: {vi_result}")
    
    return results

def run_tests():
    english_results = test_english_translations()
    for result in english_results:
        print(result)
    
    print("=" * 60)
    
    korean_results = test_korean_translations()
    for result in korean_results:
        print(result)

if __name__ == "__main__":
    run_tests()
