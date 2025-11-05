import os
import sys
sys.path.append(os.path.dirname(__file__))

from database.connection import db_pool
from database.queries import get_vocab_without_audio, update_vocab_audio_path
from logic.tss.tss import save_to_file

def generate_audio_file(base, pos):
    backend_dir = os.path.abspath(os.path.dirname(__file__))
    audio_dir = os.path.join(backend_dir, 'database', 'data', 'audio')
    os.makedirs(audio_dir, exist_ok=True)
    
    safe_filename = f"{base}_{pos}".replace('/', '_').replace('\\', '_')[:100]
    filename = f"{safe_filename}.mp3"
    filepath = os.path.join(audio_dir, filename)
    
    if not save_to_file:
        print(f"save_to_file is None, cannot generate audio for {base}", flush=True)
        return False
    
    try:
        result = save_to_file(base, lang='ko', filename=filepath)
        if os.path.exists(filepath):
            relative_path = f"data/audio/{filename}"
            update_vocab_audio_path(base, pos, relative_path)
            print(f"Generated audio: {filepath}", flush=True)
            return True
        else:
            print(f"Audio file was not created: {filepath}", flush=True)
            return False
    except Exception as e:
        print(f"Error generating audio for {base}: {e}", flush=True)
        import traceback
        traceback.print_exc()
        return False

def generate_all_audio():
    items = get_vocab_without_audio()
    print(f"Found {len(items)} items without audio")
    for item in items:
        print(f"Generating audio for: {item['base']}")
        generate_audio_file(item['base'], item['pos'])

def regenerate_all_audio():
    from database.queries import get_all_global_vocab
    db_pool.init_pool()
    items = get_all_global_vocab()
    print(f"Regenerating audio for {len(items)} items")
    for item in items:
        print(f"Generating audio for: {item['base']}")
        generate_audio_file(item['base'], item['pos'])

if __name__ == '__main__':
    db_pool.init_pool()
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == '--force':
        regenerate_all_audio()
    else:
        generate_all_audio()

