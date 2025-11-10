#!/usr/bin/env python3
import os
import sys

backend_root = os.path.abspath(os.path.join(os.path.dirname(__file__)))
sys.path.insert(0, backend_root)

from database.connection import db_pool

def check_global_vocab_audio():
    conn = db_pool.get_connection()
    if not conn:
        print("Failed to get database connection")
        return
    
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_name = 'global_vocab'
            )
        """)
        table_exists = cursor.fetchone()[0]
        
        if not table_exists:
            print("\n=== GLOBAL VOCAB AUDIO FILES ===")
            print("⚠ Global_vocab table does not exist in database")
            return
        
        cursor.execute("""
            SELECT base, pos, audio_path, count
            FROM global_vocab
            ORDER BY count DESC
        """)
        rows = cursor.fetchall()
        
        print("\n=== GLOBAL VOCAB AUDIO FILES ===")
        print(f"Total vocabulary items: {len(rows)}")
        
        with_audio = 0
        without_audio = 0
        missing_files = 0
        
        for base, pos, audio_path, count in rows:
            if audio_path:
                with_audio += 1
                if audio_path.startswith('data/'):
                    audio_full_path = os.path.join(backend_root, 'database', audio_path)
                else:
                    audio_full_path = os.path.join(backend_root, 'database', 'data', audio_path)
                if not os.path.exists(audio_full_path):
                    missing_files += 1
                    print(f"  ❌ {base} ({pos}) - DB has path but file missing: {audio_path}")
                    print(f"      Looked at: {audio_full_path}")
            else:
                without_audio += 1
        
        print(f"\nSummary:")
        print(f"  With audio_path in DB: {with_audio}")
        print(f"  Without audio_path: {without_audio}")
        print(f"  Files missing from disk: {missing_files}")
        
    except Exception as e:
        print(f"Error checking global_vocab: {e}")
    finally:
        db_pool.return_connection(conn)

def check_recordings():
    conn = db_pool.get_connection()
    if not conn:
        print("Failed to get database connection")
        return
    
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_name = 'recordings'
            )
        """)
        table_exists = cursor.fetchone()[0]
        
        if not table_exists:
            print("\n=== RAW USER RECORDINGS ===")
            print("⚠ Recordings table does not exist in database")
            print("  The recordings table needs to be created first.")
            return
        
        cursor.execute("""
            SELECT r.id, r.user_id, u.username, r.role, r.audio_path, r.transcript, r.language, r.created_at
            FROM recordings r
            LEFT JOIN users u ON r.user_id = u.id
            ORDER BY r.created_at DESC
        """)
        rows = cursor.fetchall()
        
        print("\n=== RAW USER RECORDINGS ===")
        print(f"Total recordings in database: {len(rows)}")
        
        missing_files = 0
        existing_files = 0
        total_size = 0
        
        print("\nDetailed list:")
        for rec_id, user_id, username, role, audio_path, transcript, language, created_at in rows:
            if audio_path:
                if audio_path.startswith('data/'):
                    audio_full_path = os.path.join(backend_root, 'database', audio_path)
                else:
                    audio_full_path = os.path.join(backend_root, 'database', 'data', audio_path)
                if os.path.exists(audio_full_path):
                    existing_files += 1
                    file_size = os.path.getsize(audio_full_path)
                    total_size += file_size
                    size_mb = file_size / (1024 * 1024)
                    print(f"  ✓ Recording ID {rec_id}")
                    print(f"    User: {username or f'ID:{user_id}'}")
                    print(f"    Role: {role}")
                    print(f"    Path: {audio_path}")
                    print(f"    Size: {file_size:,} bytes ({size_mb:.2f} MB)")
                    print(f"    Language: {language or 'N/A'}")
                    print(f"    Created: {created_at}")
                    if transcript:
                        transcript_preview = transcript[:100] + "..." if len(transcript) > 100 else transcript
                        print(f"    Transcript: {transcript_preview}")
                    print()
                else:
                    missing_files += 1
                    print(f"  ❌ Recording ID {rec_id} - File missing!")
                    print(f"    Expected path: {audio_full_path}")
                    print(f"    DB path: {audio_path}")
                    print(f"    User: {username or f'ID:{user_id}'}, Role: {role}, Date: {created_at}")
                    print()
            else:
                print(f"  ⚠ Recording ID {rec_id} - No audio_path in database!")
                print(f"    User: {username or f'ID:{user_id}'}, Role: {role}, Date: {created_at}")
                print()
        
        print(f"\nSummary:")
        print(f"  Total recordings in DB: {len(rows)}")
        print(f"  Files existing on disk: {existing_files}")
        print(f"  Files missing from disk: {missing_files}")
        if total_size > 0:
            total_mb = total_size / (1024 * 1024)
            print(f"  Total storage used: {total_size:,} bytes ({total_mb:.2f} MB)")
        
        cursor.execute("""
            SELECT COUNT(*), role, language
            FROM recordings
            GROUP BY role, language
            ORDER BY COUNT(*) DESC
        """)
        stats = cursor.fetchall()
        if stats:
            print(f"\nBreakdown by role and language:")
            for count, role, language in stats:
                print(f"  {role} ({language or 'N/A'}): {count} recordings")
        
    except Exception as e:
        print(f"Error checking recordings: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db_pool.return_connection(conn)

def check_audio_directory():
    audio_dir = os.path.join(backend_root, 'database', 'data', 'audio')
    recordings_dir = os.path.join(backend_root, 'database', 'data', 'recordings')
    
    print("\n=== AUDIO DIRECTORY CHECK ===")
    
    if os.path.exists(audio_dir):
        audio_files = [f for f in os.listdir(audio_dir) if f.endswith('.mp3')]
        print(f"Audio directory: {len(audio_files)} .mp3 files found")
        if len(audio_files) > 0:
            print(f"  Sample files: {', '.join(audio_files[:5])}")
    else:
        print(f"Audio directory not found: {audio_dir}")
    
    if os.path.exists(recordings_dir):
        recording_files = [f for f in os.listdir(recordings_dir) if f.endswith(('.webm', '.mp3', '.wav'))]
        print(f"Recordings directory: {len(recording_files)} audio files found")
        if len(recording_files) > 0:
            print(f"  Sample files: {', '.join(recording_files[:5])}")
    else:
        print(f"Recordings directory not found: {recordings_dir}")

if __name__ == '__main__':
    if not db_pool.init_pool():
        print("Failed to initialize database connection")
        sys.exit(1)
    
    print("Checking audio files in database...")
    check_global_vocab_audio()
    check_recordings()
    check_audio_directory()
    
    print("\n=== DONE ===")

