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

CREATE TABLE IF NOT EXISTS recordings (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL,
    role VARCHAR(10) NOT NULL,
    audio_path VARCHAR(500) NOT NULL,
    transcript TEXT,
    language VARCHAR(10),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_recordings_user_id ON recordings(user_id);
CREATE INDEX IF NOT EXISTS idx_recordings_created_at ON recordings(created_at);
