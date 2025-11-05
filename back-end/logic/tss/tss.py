from gtts import gTTS
import os

def speak(text, lang='en', output_file='temp_audio.mp3'):
    tts = gTTS(text=text, lang=lang, slow=False)
    tts.save(output_file)
    os.system(f'afplay {output_file}')
    os.remove(output_file)

def save_to_file(text, lang='en', filename='output.mp3'):
    tts = gTTS(text=text, lang=lang, slow=False)
    tts.save(filename)
    return filename