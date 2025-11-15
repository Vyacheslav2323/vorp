#!/bin/bash

cd "$(dirname "$0")"

echo "Checking Python 3..."
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is not installed. Please install Python 3.8 or higher."
    exit 1
fi

PYTHON_VERSION=$(python3 --version | cut -d' ' -f2 | cut -d'.' -f1,2)
echo "✓ Found Python $PYTHON_VERSION"

echo ""
echo "Setting up virtual environment..."
# Check for existing venv or .venv
if [ -d "venv" ]; then
    VENV_DIR="venv"
elif [ -d ".venv" ]; then
    VENV_DIR=".venv"
else
    echo "Creating virtual environment..."
    python3 -m venv venv
    if [ $? -ne 0 ]; then
        echo "❌ Failed to create virtual environment!"
        exit 1
    fi
    VENV_DIR="venv"
fi

source $VENV_DIR/bin/activate

echo "Upgrading pip..."
pip install --upgrade pip --quiet

echo "Installing requirements..."
if [ -f "requirements.txt" ]; then
    pip install -r requirements.txt
elif [ -f "back-end/requirements.txt" ]; then
    pip install -r back-end/requirements.txt
else
    echo "❌ requirements.txt not found!"
    exit 1
fi
if [ $? -ne 0 ]; then
    echo "❌ Failed to install requirements!"
    echo ""
    echo "Note: If mecab-python3 installation fails, you may need to install MeCab first:"
    echo "  brew install mecab mecab-ko mecab-ko-dic"
    exit 1
fi

echo "Checking MeCab Korean dictionary..."
if [ ! -d "/usr/local/lib/mecab/dic/mecab-ko-dic" ] && [ ! -d "/opt/homebrew/lib/mecab/dic/mecab-ko-dic" ]; then
    echo "⚠ Korean MeCab dictionary not found!"
    echo "  Installing Korean dictionary..."
    if command -v brew &> /dev/null; then
        brew install mecab-ko mecab-ko-dic 2>&1 | tail -5
        if [ $? -eq 0 ]; then
            echo "✓ Korean MeCab dictionary installed"
        else
            echo "⚠ Failed to install Korean dictionary. Korean text analysis may not work correctly."
            echo "  Install manually: brew install mecab-ko mecab-ko-dic"
        fi
    else
        echo "⚠ Homebrew not found. Cannot install Korean dictionary automatically."
        echo "  Install manually: brew install mecab-ko mecab-ko-dic"
    fi
else
    echo "✓ Korean MeCab dictionary found"
fi

echo ""
echo "Stopping any existing servers and tunnels..."
lsof -ti :8000 | xargs kill -9 2>/dev/null
lsof -ti :8765 | xargs kill -9 2>/dev/null
pkill -f "cloudflared tunnel run" 2>/dev/null
sleep 1

echo "Checking PostgreSQL..."
DB_DATA_DIR="/Volumes/Slim's/lexipark-db"
if ! psql -h localhost -U $USER -d lexipark -c "SELECT 1;" &>/dev/null; then
    echo "Starting PostgreSQL..."
    if [ -d "$DB_DATA_DIR" ]; then
        postgres -D "$DB_DATA_DIR" > /tmp/postgres.log 2>&1 &
        POSTGRES_PID=$!
        sleep 2
        if kill -0 $POSTGRES_PID 2>/dev/null; then
            echo "✓ PostgreSQL started (PID: $POSTGRES_PID)"
        else
            echo "⚠ PostgreSQL failed to start. Check /tmp/postgres.log"
            echo "  You may need to start it manually: postgres -D \"$DB_DATA_DIR\" &"
        fi
    else
        echo "⚠ Database directory not found: $DB_DATA_DIR"
        echo "  Please run: ./setup-postgres-external.sh"
        exit 1
    fi
else
    echo "✓ PostgreSQL is running"
fi

echo "Initializing database..."
cd back-end
python3 init_db.py
if [ $? -ne 0 ]; then
    echo "❌ Database initialization failed!"
    exit 1
fi
cd ..

echo "Starting LexiPark production server..."
cd back-end/server
python3 server.py &
SERVER_PID=$!
cd ../..

sleep 2

echo "Starting Cloudflare tunnel..."
if command -v cloudflared &> /dev/null; then
    # Check if config file exists
    if [ -f ~/.cloudflared/config.yml ]; then
        cloudflared tunnel run lexipark &
        TUNNEL_PID=$!
        sleep 3
        # Check if tunnel started successfully
        if kill -0 $TUNNEL_PID 2>/dev/null; then
            echo "✓ Tunnel started (PID: $TUNNEL_PID)"
        else
            echo "⚠ Cloudflare tunnel failed to start. Check configuration."
            TUNNEL_PID=""
        fi
    else
        echo "⚠ Cloudflared config not found. Skipping tunnel (optional)."
        echo "  Config file should be at: ~/.cloudflared/config.yml"
        TUNNEL_PID=""
    fi
else
    echo "⚠ Cloudflared not found. Skipping tunnel (optional)."
    echo "  Install with: brew install cloudflare/cloudflare/cloudflared"
    TUNNEL_PID=""
fi

sleep 2

echo ""
echo "✓ Server started (PID: $SERVER_PID)"
if [ ! -z "$TUNNEL_PID" ]; then
    echo "✓ Tunnel started (PID: $TUNNEL_PID)"
    echo ""
    echo "Your app is live at:"
    echo "  https://lexipark.com"
    echo "  https://www.lexipark.com"
else
    echo ""
    echo "Your app is running locally at:"
    echo "  http://localhost:8000"
fi
echo ""
echo "To stop everything:"
echo "  lsof -ti :8000,8765 | xargs kill -9"
if [ ! -z "$TUNNEL_PID" ]; then
    echo "  pkill cloudflared"
fi
echo ""
echo "Processes are running in the background. Press Ctrl+C to exit this script."
echo "(The server and tunnel will continue running after you exit)"
echo ""

# Keep script running and monitor processes
trap "echo ''; echo 'Script exited. Server and tunnel are still running.'; exit 0" INT TERM

while true; do
    sleep 10
    # Check if server is still running
    if ! kill -0 $SERVER_PID 2>/dev/null; then
        echo "⚠ Server process (PID: $SERVER_PID) has stopped!"
        break
    fi
    # Check if tunnel is still running (if it was started)
    if [ ! -z "$TUNNEL_PID" ] && ! kill -0 $TUNNEL_PID 2>/dev/null; then
        echo "⚠ Tunnel process (PID: $TUNNEL_PID) has stopped!"
        break
    fi
done

