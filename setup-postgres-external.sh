#!/bin/bash
# Setup PostgreSQL on External Disk
# This script sets up PostgreSQL data directory on /Volumes/Slim's/

set -e

EXTERNAL_DISK="/Volumes/Slim's"
DB_DATA_DIR="${EXTERNAL_DISK}/lexipark-db"
DB_NAME="lexipark"
DB_USER="${USER:-slim}"
DB_PASSWORD="lexipark2024"

echo "=== PostgreSQL Setup on External Disk ==="
echo ""

# Check if external disk is mounted
if [ ! -d "$EXTERNAL_DISK" ]; then
    echo "❌ Error: External disk not found at $EXTERNAL_DISK"
    echo "   Please mount the external disk and try again."
    exit 1
fi

echo "✓ External disk found at $EXTERNAL_DISK"
echo ""

# Check if Homebrew is installed
if ! command -v brew &> /dev/null; then
    echo "❌ Homebrew is not installed."
    echo ""
    echo "Please install Homebrew first:"
    echo "  /bin/bash -c \"\$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)\""
    echo ""
    echo "Then add Homebrew to your PATH (add to ~/.zshrc):"
    echo "  echo 'eval \"\$(/opt/homebrew/bin/brew shellenv)\"' >> ~/.zshrc"
    echo "  source ~/.zshrc"
    exit 1
fi

echo "✓ Homebrew found"
echo ""

# Install PostgreSQL if not installed
if ! command -v psql &> /dev/null; then
    echo "Installing PostgreSQL..."
    brew install postgresql@14
    echo "✓ PostgreSQL installed"
else
    echo "✓ PostgreSQL already installed"
fi

# Check PostgreSQL version
PG_VERSION=$(psql --version | awk '{print $3}' | cut -d. -f1,2)
echo "PostgreSQL version: $PG_VERSION"
echo ""

# Initialize data directory on external disk if it doesn't exist
if [ ! -d "$DB_DATA_DIR" ] || [ -z "$(ls -A $DB_DATA_DIR 2>/dev/null)" ]; then
    echo "Initializing PostgreSQL data directory on external disk..."
    echo "Data directory: $DB_DATA_DIR"
    
    # Create directory
    mkdir -p "$DB_DATA_DIR"
    
    # Find initdb command
    if command -v initdb &> /dev/null; then
        INITDB_CMD="initdb"
    elif [ -f "/opt/homebrew/opt/postgresql@14/bin/initdb" ]; then
        INITDB_CMD="/opt/homebrew/opt/postgresql@14/bin/initdb"
    elif [ -f "/usr/local/opt/postgresql@14/bin/initdb" ]; then
        INITDB_CMD="/usr/local/opt/postgresql@14/bin/initdb"
    else
        echo "❌ Error: Could not find initdb command"
        echo "   Please ensure PostgreSQL is properly installed via Homebrew"
        exit 1
    fi
    
    # Initialize database
    $INITDB_CMD -D "$DB_DATA_DIR" --locale=en_US.UTF-8 --encoding=UTF8
    echo "✓ PostgreSQL data directory initialized"
else
    echo "✓ PostgreSQL data directory already exists"
fi

# Find postgres command
if command -v postgres &> /dev/null; then
    POSTGRES_CMD="postgres"
elif [ -f "/opt/homebrew/opt/postgresql@14/bin/postgres" ]; then
    POSTGRES_CMD="/opt/homebrew/opt/postgresql@14/bin/postgres"
elif [ -f "/usr/local/opt/postgresql@14/bin/postgres" ]; then
    POSTGRES_CMD="/usr/local/opt/postgresql@14/bin/postgres"
else
    echo "❌ Error: Could not find postgres command"
    exit 1
fi

# Start PostgreSQL with custom data directory
echo ""
echo "Starting PostgreSQL with data directory: $DB_DATA_DIR"
echo ""

# Create a custom postgresql.conf if needed
PG_CONF="$DB_DATA_DIR/postgresql.conf"
if [ ! -f "$PG_CONF" ]; then
    echo "Creating postgresql.conf..."
    cat > "$PG_CONF" <<EOF
# PostgreSQL configuration for LexiPark
listen_addresses = 'localhost'
port = 5432
max_connections = 100
shared_buffers = 128MB
dynamic_shared_memory_type = posix
max_wal_size = 1GB
min_wal_size = 80MB
log_timezone = 'UTC'
datestyle = 'iso, mdy'
timezone = 'UTC'
lc_messages = 'en_US.UTF-8'
lc_monetary = 'en_US.UTF-8'
lc_numeric = 'en_US.UTF-8'
lc_time = 'en_US.UTF-8'
default_text_search_config = 'pg_catalog.english'
EOF
fi

# Start PostgreSQL in background
echo "Starting PostgreSQL server..."
$POSTGRES_CMD -D "$DB_DATA_DIR" &
PG_PID=$!
sleep 3

# Check if PostgreSQL started successfully
if ! kill -0 $PG_PID 2>/dev/null; then
    echo "❌ Error: PostgreSQL failed to start"
    exit 1
fi

echo "✓ PostgreSQL server started (PID: $PG_PID)"
echo ""

# Wait a bit for PostgreSQL to be ready
sleep 2

# Create database if it doesn't exist
if psql -h localhost -U "$DB_USER" -lqt | cut -d \| -f 1 | grep -qw "$DB_NAME"; then
    echo "✓ Database '$DB_NAME' already exists"
else
    echo "Creating database '$DB_NAME'..."
    createdb -h localhost -U "$DB_USER" "$DB_NAME" || {
        # Try with postgres user
        createdb -h localhost -U postgres "$DB_NAME" || {
            echo "Creating database with superuser..."
            psql -h localhost -U "$DB_USER" -d postgres -c "CREATE DATABASE $DB_NAME;" || true
        }
    }
    echo "✓ Database '$DB_NAME' created"
fi

# Set password for user
echo ""
echo "Setting up database user..."
psql -h localhost -U "$DB_USER" -d "$DB_NAME" -c "ALTER USER $DB_USER WITH PASSWORD '$DB_PASSWORD';" 2>/dev/null || \
psql -h localhost -U postgres -d "$DB_NAME" -c "CREATE USER $DB_USER WITH PASSWORD '$DB_PASSWORD';" 2>/dev/null || \
psql -h localhost -U "$DB_USER" -d "$DB_NAME" -c "DO \$\$ BEGIN CREATE USER $DB_USER WITH PASSWORD '$DB_PASSWORD'; EXCEPTION WHEN duplicate_object THEN NULL; END \$\$;" 2>/dev/null || true

echo ""
echo "=== Setup Complete ==="
echo ""
echo "PostgreSQL is running with:"
echo "  Data directory: $DB_DATA_DIR"
echo "  Database: $DB_NAME"
echo "  User: $DB_USER"
echo "  Password: $DB_PASSWORD"
echo ""
echo "To start PostgreSQL in the future, run:"
echo "  $POSTGRES_CMD -D \"$DB_DATA_DIR\" &"
echo ""
echo "To stop PostgreSQL:"
echo "  pkill -f \"postgres.*$DB_DATA_DIR\""
echo ""
echo "To initialize the database schema, run:"
echo "  cd /Users/slim/vorp && source venv/bin/activate && python back-end/init_db.py"
echo ""


