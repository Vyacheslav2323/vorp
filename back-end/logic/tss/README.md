# Text-to-Speech (TTS) Module

This module provides text-to-speech functionality using Google TTS (gTTS).

## Installation

The required package `gtts` is installed in the virtual environment.

## Functions

### `speak(text, lang='en', output_file='temp_audio.mp3')`
Speaks the given text and plays it using the system audio player.

Parameters:
- `text`: The text to speak
- `lang`: Language code (e.g., 'en' for English, 'ko' for Korean)
- `output_file`: Temporary file to save the audio (automatically deleted after playing)

### `save_to_file(text, lang='en', filename='output.mp3')`
Saves the spoken text to an audio file without playing it.

Parameters:
- `text`: The text to convert to speech
- `lang`: Language code (e.g., 'en' for English, 'ko' for Korean)
- `filename`: Output filename for the audio file

Returns:
- The filename where the audio was saved

## API Endpoint

### POST /tts
Converts text to speech and returns the audio as base64-encoded data.

Request body:
```json
{
  "text": "Hello, world",
  "lang": "en"
}
```

Response:
```json
{
  "success": true,
  "audio": "base64_encoded_audio_data",
  "error": ""
}
```

## Usage Example

```python
from logic.tss.tss import speak, save_to_file

# Speak Korean text
speak('안녕하세요', lang='ko')

# Save English text to file
filename = save_to_file('Hello, world', lang='en', filename='hello.mp3')
```

## Supported Languages

gTTS supports many languages. Common language codes:
- 'en': English
- 'ko': Korean
- 'ja': Japanese
- 'es': Spanish
- 'fr': French
- 'de': German
- 'zh': Chinese



