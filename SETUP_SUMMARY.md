# Setup Summary - LexiPark on Intel Mac

## ✅ Completed Automatically

1. **Python Virtual Environment**: Created and all dependencies installed
   - Location: `/Users/slim/vorp/venv`
   - All packages from `requirements.txt` installed

2. **Database Directory**: Created on external disk
   - Location: `/Volumes/Slim's/lexipark-db`
   - Ready for PostgreSQL data directory initialization

3. **Setup Scripts Created**:
   - `setup-postgres-external.sh` - Automated PostgreSQL setup on external disk
   - `MANUAL_SETUP_STEPS.md` - Complete manual setup instructions

## ⚠️ Manual Steps Required

You need to run these commands manually (they require sudo/admin access):

### Step 1: Install Homebrew
```bash
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
```

Then add to your `~/.zshrc`:
```bash
echo 'eval "$(/opt/homebrew/bin/brew shellenv)"' >> ~/.zshrc
source ~/.zshrc
```

### Step 2: Install PostgreSQL and MeCab
```bash
brew install postgresql@14 mecab mecab-ipadic
```

### Step 3: Set Up PostgreSQL on External Disk
```bash
cd /Users/slim/vorp
./setup-postgres-external.sh
```

This script will:
- Initialize PostgreSQL data directory on `/Volumes/Slim's/lexipark-db`
- Start PostgreSQL server
- Create the `lexipark` database
- Set up database user with password `lexipark2024`

### Step 4: Initialize Database Schema
```bash
cd /Users/slim/vorp
source venv/bin/activate
python back-end/init_db.py
```

### Step 5: Start the Server
```bash
cd /Users/slim/vorp
bash start-production.sh
```

## Database Configuration

The database will be configured with:
- **Host**: localhost
- **Port**: 5432
- **Database**: lexipark
- **User**: Your macOS username (or postgres)
- **Password**: lexipark2024
- **Data Directory**: `/Volumes/Slim's/lexipark-db`

## Troubleshooting

### If MeCab import fails:
The code uses `import mecab` but `mecab-python3` uses `import MeCab`. You may need to update `back-end/logic/text/analysis.py`:

```python
# Change from:
import mecab

# To:
import MeCab as mecab
```

### If PostgreSQL won't start:
Make sure the external disk is mounted, then start manually:
```bash
postgres -D "/Volumes/Slim's/lexipark-db" &
```

### Check PostgreSQL status:
```bash
psql -h localhost -U $USER -d lexipark -c "SELECT version();"
```

## Files Created

- `/Users/slim/vorp/setup-postgres-external.sh` - PostgreSQL setup script
- `/Users/slim/vorp/MANUAL_SETUP_STEPS.md` - Detailed manual instructions
- `/Volumes/Slim's/lexipark-db/` - PostgreSQL data directory (after running setup script)

## Next Steps

1. Run the manual steps above (Steps 1-4)
2. Start the server with `bash start-production.sh`
3. Access the app at `http://localhost:8000`

For detailed troubleshooting, see `MANUAL_SETUP_STEPS.md`.


