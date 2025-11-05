#!/usr/bin/env python3
import os
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), 'database'))

from connection import db_pool

def init_database():
    if not db_pool.init_pool():
        print("Failed to initialize database connection")
        return False
    
    conn = db_pool.get_connection()
    if not conn:
        print("Failed to get database connection")
        return False
    
    try:
        cursor = conn.cursor()
        schema_sql = """
        CREATE TABLE IF NOT EXISTS users (
            id SERIAL PRIMARY KEY,
            username VARCHAR(50) UNIQUE NOT NULL,
            email VARCHAR(100) UNIQUE NOT NULL,
            password_hash VARCHAR(255) NOT NULL,
            native_language VARCHAR(10),
            target_language VARCHAR(10),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_login TIMESTAMP
        );

        CREATE INDEX IF NOT EXISTS idx_users_username ON users(username);
        CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);

        CREATE TABLE IF NOT EXISTS global_vocab (
            base VARCHAR(255) NOT NULL,
            pos VARCHAR(50) NOT NULL,
            translation_en VARCHAR(500),
            translation_ru VARCHAR(500),
            translation_zh VARCHAR(500),
            translation_vi VARCHAR(500),
            audio_path VARCHAR(500),
            count INTEGER DEFAULT 0,
            PRIMARY KEY (base, pos)
        );

        CREATE INDEX IF NOT EXISTS idx_global_vocab_base ON global_vocab(base);

        CREATE TABLE IF NOT EXISTS vocab (
            user_id INTEGER NOT NULL,
            base VARCHAR(255) NOT NULL,
            pos VARCHAR(50) NOT NULL,
            count INTEGER DEFAULT 0,
            last_added TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            remember_count INTEGER DEFAULT 0,
            dont_remember_count INTEGER DEFAULT 0,
            PRIMARY KEY (user_id, base, pos),
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        );

        CREATE INDEX IF NOT EXISTS idx_vocab_user_id ON vocab(user_id);
        CREATE INDEX IF NOT EXISTS idx_vocab_base ON vocab(base);
        """
        cursor.execute("SELECT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name='vocab')")
        vocab_exists = cursor.fetchone()[0]
        
        if not vocab_exists:
            cursor.execute(schema_sql)
        else:
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id SERIAL PRIMARY KEY,
                    username VARCHAR(50) UNIQUE NOT NULL,
                    email VARCHAR(100) UNIQUE NOT NULL,
                    password_hash VARCHAR(255) NOT NULL,
                    native_language VARCHAR(10),
                    target_language VARCHAR(10),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_login TIMESTAMP
                );

                CREATE INDEX IF NOT EXISTS idx_users_username ON users(username);
                CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);

                CREATE TABLE IF NOT EXISTS global_vocab (
                    base VARCHAR(255) NOT NULL,
                    pos VARCHAR(50) NOT NULL,
                    translation_en VARCHAR(500),
                    translation_ru VARCHAR(500),
                    translation_zh VARCHAR(500),
                    translation_vi VARCHAR(500),
                    audio_path VARCHAR(500),
                    count INTEGER DEFAULT 0,
                    PRIMARY KEY (base, pos)
                );

                CREATE INDEX IF NOT EXISTS idx_global_vocab_base ON global_vocab(base);
            """)
        
        alter_sql = """
        ALTER TABLE users ADD COLUMN IF NOT EXISTS native_language VARCHAR(10);
        ALTER TABLE users ADD COLUMN IF NOT EXISTS target_language VARCHAR(10);
        ALTER TABLE vocab ADD COLUMN IF NOT EXISTS remember_count INTEGER DEFAULT 0;
        ALTER TABLE vocab ADD COLUMN IF NOT EXISTS dont_remember_count INTEGER DEFAULT 0;
        """
        cursor.execute(alter_sql)
        
        cursor.execute("""
            SELECT EXISTS (
                SELECT 1 FROM information_schema.tables 
                WHERE table_name='global_vocab'
            )
        """)
        global_vocab_exists = cursor.fetchone()[0]
        
        if global_vocab_exists:
            cursor.execute("""
                SELECT EXISTS (
                    SELECT 1 FROM information_schema.columns 
                    WHERE table_name='global_vocab' AND column_name='translation'
                )
            """)
            has_old_column = cursor.fetchone()[0]
            
            cursor.execute("""
                SELECT EXISTS (
                    SELECT 1 FROM information_schema.columns 
                    WHERE table_name='global_vocab' AND column_name='translation_en'
                )
            """)
            has_new_columns = cursor.fetchone()[0]
            
            if has_old_column and not has_new_columns:
                cursor.execute("""
                    ALTER TABLE global_vocab 
                    ADD COLUMN translation_en VARCHAR(500),
                    ADD COLUMN translation_ru VARCHAR(500),
                    ADD COLUMN translation_zh VARCHAR(500),
                    ADD COLUMN translation_vi VARCHAR(500)
                """)
                cursor.execute("""
                    UPDATE global_vocab 
                    SET translation_en = translation 
                    WHERE translation IS NOT NULL AND translation_en IS NULL
                """)
                cursor.execute("""
                    ALTER TABLE global_vocab DROP COLUMN translation
                """)
            elif not has_new_columns:
                cursor.execute("""
                    ALTER TABLE global_vocab 
                    ADD COLUMN IF NOT EXISTS translation_en VARCHAR(500),
                    ADD COLUMN IF NOT EXISTS translation_ru VARCHAR(500),
                    ADD COLUMN IF NOT EXISTS translation_zh VARCHAR(500),
                    ADD COLUMN IF NOT EXISTS translation_vi VARCHAR(500)
                """)
        
        cursor.execute("SELECT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name='vocab')")
        vocab_exists = cursor.fetchone()[0]
        
        if vocab_exists:
            cursor.execute("SELECT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='vocab' AND column_name='user_id')")
            has_user_id = cursor.fetchone()[0]
            
            if not has_user_id:
                cursor.execute("SELECT id FROM users LIMIT 1")
                user_row = cursor.fetchone()
                if not user_row:
                    cursor.execute("INSERT INTO users (username, email, password_hash) VALUES ('migrated_user', 'migrated@example.com', '$2b$12$migrated') RETURNING id")
                    user_id = cursor.fetchone()[0]
                else:
                    user_id = user_row[0]
                
                cursor.execute("ALTER TABLE vocab ADD COLUMN user_id INTEGER")
                cursor.execute("UPDATE vocab SET user_id = %s WHERE user_id IS NULL", (user_id,))
                
                cursor.execute("ALTER TABLE vocab ALTER COLUMN user_id SET NOT NULL")
                cursor.execute("ALTER TABLE vocab DROP CONSTRAINT IF EXISTS vocab_pkey")
                cursor.execute("ALTER TABLE vocab ADD PRIMARY KEY (user_id, base, pos)")
                cursor.execute("ALTER TABLE vocab DROP CONSTRAINT IF EXISTS vocab_user_id_fkey")
                cursor.execute("ALTER TABLE vocab ADD CONSTRAINT vocab_user_id_fkey FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE")
                
                cursor.execute("SELECT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='vocab' AND column_name='translation')")
                has_translation = cursor.fetchone()[0]
                if has_translation:
                    cursor.execute("""
                        INSERT INTO global_vocab (base, pos, translation_en, audio_path, count) 
                        SELECT base, pos, translation, COALESCE(audio_path, ''), count 
                        FROM vocab 
                        ON CONFLICT (base, pos) DO NOTHING
                    """)
                    cursor.execute("ALTER TABLE vocab DROP COLUMN IF EXISTS translation")
                cursor.execute("ALTER TABLE vocab DROP COLUMN IF EXISTS audio_path")
        
        conn.commit()
        print("Database schema initialized successfully")
        return True
    except Exception as e:
        import traceback
        print(f"Error initializing database: {e}")
        traceback.print_exc()
        return False
    finally:
        db_pool.return_connection(conn)

if __name__ == '__main__':
    init_database()
