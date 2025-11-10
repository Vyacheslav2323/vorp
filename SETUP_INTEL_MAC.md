# Setup Guide for Intel Mac

## Prerequisites

1. **Python 3.8+** (check with `python3 --version`)
2. **PostgreSQL** (for database)
3. **Homebrew** (for installing dependencies)

## Installation Steps

### 1. Install PostgreSQL
```bash
brew install postgresql@14
brew services start postgresql@14
createdb lexipark
```

### 2. Install MeCab (for Korean text analysis)
```bash
brew install mecab mecab-ipadic
```

### 3. Set Environment Variables (optional)
```bash
export DB_HOST=localhost
export DB_PORT=5432
export DB_NAME=lexipark
export DB_USER=your_username
export DB_PASSWORD=your_password
export OPENAI_API_KEY=your_openai_key
```

### 4. Run Setup Script
```bash
chmod +x start-production.sh
./start-production.sh
```

The script will:
- Check Python 3 installation
- Create virtual environment if needed
- Install all Python dependencies
- Initialize database schema
- Start the server

## Intel Mac Compatibility Notes

✅ **Should work smoothly:**
- All Python packages (psycopg2-binary, pandas, openai, etc.)
- PostgreSQL database
- Web server functionality

⚠️ **Potential issues:**
- **MeCab**: Requires Homebrew installation first (`brew install mecab mecab-ipadic`)
- **Performance**: May be slower than Apple Silicon, but should be fine for a server
- **Memory**: Ensure sufficient RAM (8GB+ recommended)

## Troubleshooting

### MeCab installation fails
```bash
brew install mecab mecab-ipadic
pip install --upgrade mecab-python3
```

### PostgreSQL connection issues
```bash
# Check if PostgreSQL is running
brew services list

# Start PostgreSQL
brew services start postgresql@14

# Create database
createdb lexipark
```

### Port already in use
```bash
# Kill processes on ports 8000 and 8765
lsof -ti :8000 | xargs kill -9
lsof -ti :8765 | xargs kill -9
```

## Performance Expectations

On an Intel Mac:
- Server startup: ~2-5 seconds
- Database queries: Fast (PostgreSQL is efficient)
- Text analysis (MeCab): ~100-500ms per sentence
- OpenAI API calls: Network dependent (~1-3 seconds)
- Overall: Should handle multiple concurrent users smoothly

