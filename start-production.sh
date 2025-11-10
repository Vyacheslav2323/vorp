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
if [ ! -d ".venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv .venv
    if [ $? -ne 0 ]; then
        echo "❌ Failed to create virtual environment!"
        exit 1
    fi
fi

source .venv/bin/activate

echo "Upgrading pip..."
pip install --upgrade pip --quiet

echo "Installing requirements..."
pip install -r back-end/requirements.txt
if [ $? -ne 0 ]; then
    echo "❌ Failed to install requirements!"
    echo ""
    echo "Note: If mecab-python3 installation fails, you may need to install MeCab first:"
    echo "  brew install mecab mecab-ipadic"
    exit 1
fi

echo ""
echo "Stopping any existing servers and tunnels..."
lsof -ti :8000 | xargs kill -9 2>/dev/null
lsof -ti :8765 | xargs kill -9 2>/dev/null
pkill -f "cloudflared tunnel run" 2>/dev/null
sleep 1

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
cloudflared tunnel run lexipark &
TUNNEL_PID=$!

sleep 2

echo ""
echo "✓ Server started (PID: $SERVER_PID)"
echo "✓ Tunnel started (PID: $TUNNEL_PID)"
echo ""
echo "Your app is live at:"
echo "  https://lexipark.com"
echo "  https://www.lexipark.com"
echo ""
echo "To stop everything:"
echo "  lsof -ti :8000,8765 | xargs kill -9"
echo "  pkill cloudflared"

