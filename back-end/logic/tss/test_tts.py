import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from logic.tss.tss import speak, save_to_file

def test_speak_english():
    speak('Hello, this is a test of text to speech', lang='en')

def test_speak_korean():
    speak('안녕하세요', lang='ko')

def test_save_to_file():
    filename = save_to_file('This is a saved audio file', lang='en', filename='test_output.mp3')
    print(f'Audio saved to: {filename}')

if __name__ == '__main__':
    test_speak_korean()



