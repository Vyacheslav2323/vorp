# Manual Setup Steps for LexiPark on Intel Mac

## Prerequisites Installation

Since Homebrew requires sudo access, you'll need to run these commands manually in your terminal:

### 1. Install Homebrew (if not already installed)

```bash
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
```

After installation, add Homebrew to your PATH by adding this to your `~/.zshrc`:

```bash
echo 'eval "$(/opt/homebrew/bin/brew shellenv)"' >> ~/.zshrc
source ~/.zshrc
```

### 2. Install PostgreSQL and MeCab

```bash
brew install postgresql@14 mecab mecab-ipadic
```

### 3. Set Up PostgreSQL on External Disk

Run the automated setup script:

```bash
cd /Users/slim/vorp
./setup-postgres-external.sh
```

This will:
- Initialize PostgreSQL data directory on `/Volumes/Slim's/lexipark-db`
- Start PostgreSQL server
- Create the `lexipark` database
- Set up the database user

### 4. Initialize Database Schema

After PostgreSQL is running, initialize the database schema:

```bash
cd /Users/slim/vorp
source venv/bin/activate
python back-end/init_db.py
```

### 5. (Optional) Set Environment Variables

You can set these in your `~/.zshrc` or create a `.env` file:

```bash
export DB_HOST=localhost
export DB_PORT=5432
export DB_NAME=lexipark
export DB_USER=your_username
export DB_PASSWORD=lexipark2024
export OPENAI_API_KEY=your_openai_key  # if using OpenAI features
```

## Starting the Server

Once everything is set up:

```bash
cd /Users/slim/vorp
bash start-production.sh
```

## Troubleshooting

### PostgreSQL won't start

Check if the data directory exists:
```bash
ls -la "/Volumes/Slim's/lexipark-db"
```

Start PostgreSQL manually:
```bash
postgres -D "/Volumes/Slim's/lexipark-db" &
```

### MeCab import errors

If you see `No module named 'mecab'` errors, try:
```bash
source venv/bin/activate
pip install mecab-python3
```

Then update `back-end/logic/text/analysis.py`:
```python
import MeCab as mecab  # Change from: import mecab
```

### Database connection errors

Verify PostgreSQL is running:
```bash
psql -h localhost -U your_username -d lexipark -c "SELECT version();"
```

Check the connection settings match your environment variables.

## Notes

- The database is stored on `/Volumes/Slim's/lexipark-db` - make sure the external disk is mounted before starting the server
- PostgreSQL will run on port 5432 by default
- The default database password is `lexipark2024` (change this in production!)


