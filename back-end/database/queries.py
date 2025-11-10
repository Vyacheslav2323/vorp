import psycopg2
from typing import Optional
from .connection import db_pool
from .models import User, UserCreate, UserLogin, AuthResult
import bcrypt
import jwt
import os
from datetime import datetime, timedelta

def hash_password(password: str) -> str:
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')

def verify_password(password: str, hash: str) -> bool:
    return bcrypt.checkpw(password.encode('utf-8'), hash.encode('utf-8'))

def create_user(user_data: UserCreate) -> AuthResult:
    conn = db_pool.get_connection()
    if not conn:
        return AuthResult(success=False, error="db_connection_failed")
    
    try:
        if user_data.native_language and user_data.target_language:
            if user_data.native_language == user_data.target_language:
                return AuthResult(success=False, error="same_languages")
        
        cursor = conn.cursor()
        password_hash = hash_password(user_data.password)
        
        cursor.execute("""
            INSERT INTO users (username, email, password_hash, native_language, target_language, created_at)
            VALUES (%s, %s, %s, %s, %s, %s)
            RETURNING id, username, email, password_hash, created_at, native_language, target_language
        """, (user_data.username, user_data.email, password_hash, 
              user_data.native_language, user_data.target_language, datetime.now()))
        
        row = cursor.fetchone()
        user = User(id=row[0], username=row[1], email=row[2], 
                   password_hash=row[3], created_at=row[4], 
                   native_language=row[5], target_language=row[6])
        
        token = generate_token(user.id)
        conn.commit()
        return AuthResult(success=True, user=user, token=token)
        
    except psycopg2.IntegrityError:
        return AuthResult(success=False, error="user_exists")
    except Exception as e:
        return AuthResult(success=False, error=str(e))
    finally:
        db_pool.return_connection(conn)

def authenticate_user(login_data: UserLogin) -> AuthResult:
    conn = db_pool.get_connection()
    if not conn:
        return AuthResult(success=False, error="db_connection_failed")
    
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, username, email, password_hash, created_at, native_language, target_language, last_login
            FROM users WHERE username = %s
        """, (login_data.username,))
        
        row = cursor.fetchone()
        if not row:
            return AuthResult(success=False, error="user_not_found")
        
        user = User(id=row[0], username=row[1], email=row[2], 
                   password_hash=row[3], created_at=row[4],
                   native_language=row[5], target_language=row[6],
                   last_login=row[7])
        
        if not verify_password(login_data.password, user.password_hash):
            return AuthResult(success=False, error="invalid_password")
        
        cursor.execute("""
            UPDATE users SET last_login = %s WHERE id = %s
        """, (datetime.now(), user.id))
        
        token = generate_token(user.id)
        conn.commit()
        return AuthResult(success=True, user=user, token=token)
        
    except Exception as e:
        return AuthResult(success=False, error=str(e))
    finally:
        db_pool.return_connection(conn)

def get_user_by_id(user_id: int) -> Optional[User]:
    conn = db_pool.get_connection()
    if not conn:
        return None
    
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, username, email, password_hash, created_at, native_language, target_language, last_login
            FROM users WHERE id = %s
        """, (user_id,))
        
        row = cursor.fetchone()
        if not row:
            return None
        
        return User(id=row[0], username=row[1], email=row[2], 
                   password_hash=row[3], created_at=row[4], 
                   native_language=row[5], target_language=row[6],
                   last_login=row[7])
        
    except Exception:
        return None
    finally:
        db_pool.return_connection(conn)

def generate_token(user_id: int) -> str:
    payload = {
        'user_id': user_id,
        'exp': datetime.utcnow() + timedelta(days=7)
    }
    secret = os.getenv('JWT_SECRET', 'your-secret-key-change-in-production')
    return jwt.encode(payload, secret, algorithm='HS256')

def verify_token(token: str) -> Optional[int]:
    try:
        secret = os.getenv('JWT_SECRET', 'your-secret-key-change-in-production')
        payload = jwt.decode(token, secret, algorithms=['HS256'])
        return payload.get('user_id')
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None

def get_all_vocab():
    conn = db_pool.get_connection()
    if not conn:
        return []
    
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT base, translation, pos, count, last_added, audio_path
            FROM vocab
            ORDER BY last_added DESC
        """)
        rows = cursor.fetchall()
        return [{'base': r[0], 'translation': r[1], 'pos': r[2], 'frequency': r[3], 'last_seen': r[4].isoformat() if r[4] else '', 'audio_path': r[5]} for r in rows]
    except Exception:
        return []
    finally:
        db_pool.return_connection(conn)

def get_all_global_vocab():
    conn = db_pool.get_connection()
    if not conn:
        return []
    
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT base, pos, translation_en, translation_ru, translation_zh, translation_vi, audio_path, count
            FROM global_vocab
            ORDER BY count DESC
        """)
        rows = cursor.fetchall()
        return [{'base': r[0], 'pos': r[1], 'translation_en': r[2], 'translation_ru': r[3], 'translation_zh': r[4], 'translation_vi': r[5], 'audio_path': r[6], 'count': r[7]} for r in rows]
    except Exception:
        return []
    finally:
        db_pool.return_connection(conn)

def get_user_vocab(user_id: int, native_language: str = 'en'):
    conn = db_pool.get_connection()
    if not conn:
        return []
    
    valid_langs = {'en', 'ru', 'zh', 'vi'}
    lang = native_language if native_language in valid_langs else 'en'
    translation_col = f'translation_{lang}'
    
    try:
        cursor = conn.cursor()
        cursor.execute(f"""
            SELECT v.base, g.{translation_col}, v.pos, v.count, v.last_added, g.audio_path
            FROM vocab v
            LEFT JOIN global_vocab g ON v.base = g.base AND v.pos = g.pos
            WHERE v.user_id = %s
            ORDER BY v.last_added DESC
        """, (user_id,))
        rows = cursor.fetchall()
        return [{'base': r[0], 'translation': r[1], 'pos': r[2], 'frequency': r[3], 'last_seen': r[4].isoformat() if r[4] else '', 'audio_path': r[5]} for r in rows]
    except Exception:
        return []
    finally:
        db_pool.return_connection(conn)

def get_global_vocab(base: str, pos: str):
    conn = db_pool.get_connection()
    if not conn:
        return None
    
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT base, pos, translation_en, translation_ru, translation_zh, translation_vi, audio_path, count
            FROM global_vocab
            WHERE base = %s AND pos = %s
        """, (base, pos))
        row = cursor.fetchone()
        if row:
            return {'base': row[0], 'pos': row[1], 'translation_en': row[2], 'translation_ru': row[3], 'translation_zh': row[4], 'translation_vi': row[5], 'audio_path': row[6], 'count': row[7]}
        return None
    except Exception:
        return None
    finally:
        db_pool.return_connection(conn)

def upsert_global_vocab(base: str, pos: str, translation: str, audio_path: str, target_lang: str = 'en'):
    conn = db_pool.get_connection()
    if not conn:
        return False
    
    valid_langs = {'en', 'ru', 'zh', 'vi'}
    lang = target_lang if target_lang in valid_langs else 'en'
    translation_col = f'translation_{lang}'
    
    try:
        cursor = conn.cursor()
        cursor.execute(f"""
            INSERT INTO global_vocab (base, pos, {translation_col}, audio_path, count)
            VALUES (%s, %s, %s, %s, 1)
            ON CONFLICT (base, pos)
            DO UPDATE SET 
                {translation_col} = COALESCE(EXCLUDED.{translation_col}, global_vocab.{translation_col}),
                count = global_vocab.count + 1
        """, (base, pos, translation, audio_path))
        conn.commit()
        return True
    except Exception:
        return False
    finally:
        db_pool.return_connection(conn)

def increment_global_vocab_count(base: str, pos: str):
    conn = db_pool.get_connection()
    if not conn:
        return False
    
    try:
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE global_vocab 
            SET count = count + 1
            WHERE base = %s AND pos = %s
        """, (base, pos))
        conn.commit()
        return True
    except Exception:
        return False
    finally:
        db_pool.return_connection(conn)

def upsert_user_vocab(user_id: int, base: str, pos: str, count_delta: int):
    conn = db_pool.get_connection()
    if not conn:
        return False
    
    try:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO vocab (user_id, base, pos, count, last_added)
            VALUES (%s, %s, %s, %s, %s)
            ON CONFLICT (user_id, base, pos)
            DO UPDATE SET
                count = vocab.count + %s,
                last_added = %s
        """, (user_id, base, pos, count_delta, datetime.now(), count_delta, datetime.now()))
        conn.commit()
        return True
    except Exception:
        return False
    finally:
        db_pool.return_connection(conn)

def get_vocab_translation(base: str, pos: str, target_lang: str = 'en'):
    conn = db_pool.get_connection()
    if not conn:
        return None
    
    valid_langs = {'en', 'ru', 'zh', 'vi'}
    lang = target_lang if target_lang in valid_langs else 'en'
    translation_col = f'translation_{lang}'
    
    try:
        cursor = conn.cursor()
        cursor.execute(f"""
            SELECT {translation_col} FROM global_vocab WHERE base = %s AND pos = %s
        """, (base, pos))
        row = cursor.fetchone()
        return row[0] if row and row[0] else None
    except Exception:
        return None
    finally:
        db_pool.return_connection(conn)

def upsert_vocab_item(base: str, pos: str, translation: str, count_delta: int):
    conn = db_pool.get_connection()
    if not conn:
        return False
    
    try:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO vocab (base, pos, translation, count, last_added)
            VALUES (%s, %s, %s, %s, %s)
            ON CONFLICT (base, pos)
            DO UPDATE SET
                count = vocab.count + %s,
                translation = COALESCE(EXCLUDED.translation, vocab.translation),
                last_added = %s
        """, (base, pos, translation, count_delta, datetime.now(), count_delta, datetime.now()))
        conn.commit()
        return True
    except Exception:
        return False
    finally:
        db_pool.return_connection(conn)

def record_remember(user_id: int, base: str, pos: str):
    conn = db_pool.get_connection()
    if not conn:
        return False
    
    try:
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE vocab 
            SET remember_count = remember_count + 1
            WHERE user_id = %s AND base = %s AND pos = %s
        """, (user_id, base, pos))
        conn.commit()
        return True
    except Exception:
        return False
    finally:
        db_pool.return_connection(conn)

def record_dont_remember(user_id: int, base: str, pos: str):
    conn = db_pool.get_connection()
    if not conn:
        return False
    
    try:
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE vocab 
            SET dont_remember_count = dont_remember_count + 1
            WHERE user_id = %s AND base = %s AND pos = %s
        """, (user_id, base, pos))
        conn.commit()
        return True
    except Exception:
        return False
    finally:
        db_pool.return_connection(conn)

def update_vocab_audio_path(base: str, pos: str, audio_path: str):
    conn = db_pool.get_connection()
    if not conn:
        return False
    
    try:
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE global_vocab 
            SET audio_path = %s
            WHERE base = %s AND pos = %s
        """, (audio_path, base, pos))
        conn.commit()
        return True
    except Exception:
        return False
    finally:
        db_pool.return_connection(conn)

def get_vocab_without_audio():
    conn = db_pool.get_connection()
    if not conn:
        return []
    
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT base, pos
            FROM global_vocab
            WHERE audio_path IS NULL OR audio_path = ''
        """)
        rows = cursor.fetchall()
        return [{'base': r[0], 'pos': r[1]} for r in rows]
    except Exception:
        return []
    finally:
        db_pool.return_connection(conn)

def is_admin(username: str, password: str) -> bool:
    return username == 'admin' and password == 'lexiadmin2306'

def get_all_users():
    conn = db_pool.get_connection()
    if not conn:
        return []
    
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, username, email, native_language, target_language, created_at, last_login
            FROM users
            ORDER BY created_at DESC
        """)
        rows = cursor.fetchall()
        return [{'id': r[0], 'username': r[1], 'email': r[2], 'native_language': r[3], 'target_language': r[4], 'created_at': r[5].isoformat() if r[5] else '', 'last_login': r[6].isoformat() if r[6] else ''} for r in rows]
    except Exception:
        return []
    finally:
        db_pool.return_connection(conn)

def delete_user(user_id: int) -> bool:
    conn = db_pool.get_connection()
    if not conn:
        return False
    
    try:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM users WHERE id = %s", (user_id,))
        conn.commit()
        return cursor.rowcount > 0
    except Exception:
        return False
    finally:
        db_pool.return_connection(conn)

def delete_global_vocab(base: str, pos: str) -> bool:
    conn = db_pool.get_connection()
    if not conn:
        return False
    
    try:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM global_vocab WHERE base = %s AND pos = %s", (base, pos))
        conn.commit()
        return cursor.rowcount > 0
    except Exception:
        return False
    finally:
        db_pool.return_connection(conn)

def update_global_vocab_translation(base: str, pos: str, translation: str, target_lang: str) -> bool:
    conn = db_pool.get_connection()
    if not conn:
        return False
    
    valid_langs = {'en', 'ru', 'zh', 'vi'}
    lang = target_lang if target_lang in valid_langs else 'en'
    translation_col = f'translation_{lang}'
    
    try:
        cursor = conn.cursor()
        cursor.execute(f"""
            UPDATE global_vocab 
            SET {translation_col} = %s
            WHERE base = %s AND pos = %s
        """, (translation, base, pos))
        conn.commit()
        return cursor.rowcount > 0
    except Exception:
        return False
    finally:
        db_pool.return_connection(conn)

def save_recording(user_id: int, role: str, audio_path: str, transcript: str = None, language: str = None) -> bool:
    conn = db_pool.get_connection()
    if not conn:
        return False
    
    try:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO recordings (user_id, role, audio_path, transcript, language, created_at)
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (user_id, role, audio_path, transcript, language, datetime.now()))
        conn.commit()
        return True
    except Exception:
        return False
    finally:
        db_pool.return_connection(conn)
