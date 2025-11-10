from openai import OpenAI
import os

def to_wav16k(path: str) -> str:
    import subprocess, tempfile
    if not os.path.exists(path):
        raise FileNotFoundError(path)
    dst = os.path.join(tempfile.gettempdir(), 'whisper_input_16k.wav')
    subprocess.run(['ffmpeg','-y','-i',path,'-ac','1','-ar','16000',dst], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return dst

def transcribe_and_translate(path, speaker_lang, listener_lang):
    from logic.text.translate import get_openai_client
    c = get_openai_client()
    # 1) Transcribe
    with open(path, "rb") as f:
        t = c.audio.transcriptions.create(model="gpt-4o-mini-transcribe", file=f)
    text = t.text.strip()
    # 2) Translate
    msg = f"Translate the following text from {speaker_lang} to {listener_lang}. " \
          f"Return only the translation:\n\n{text}"
    r = c.chat.completions.create(model="gpt-4o-mini",
                                  messages=[{"role": "user", "content": msg}],
                                  temperature=0.1)
    return text, r.choices[0].message.content.strip()

if __name__ == "__main__":
    src = '/Users/slimslavik/Downloads/Запись 32.m4a'
    wav = to_wav16k(src)
    txt, r = transcribe_and_translate(wav, 'ko', 'ru')
    print(txt,r)
