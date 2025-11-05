#!/bin/bash

cd "$(dirname "$0")"

echo "Stopping any existing servers and tunnels..."
lsof -ti :8000 | xargs kill -9 2>/dev/null
lsof -ti :8765 | xargs kill -9 2>/dev/null
pkill -f "cloudflared tunnel run" 2>/dev/null
sleep 1

source .venv/bin/activate

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

