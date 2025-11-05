# Quick Start: Deploy LexiPark to lexipark.com

## Prerequisites
- Domain: `lexipark.com` (purchased ✓)
- Cloudflare account
- Mac with server running

## 5-Minute Setup

### 1. Install Cloudflare Tunnel
```bash
brew install cloudflared
```

### 2. Login to Cloudflare
```bash
cloudflared tunnel login
```

### 3. Create Your Tunnel
```bash
cloudflared tunnel create lexipark
```
**Save the Tunnel ID that appears!**

### 4. Create Config File
```bash
nano ~/.cloudflared/config.yml
```

Paste this (replace `YOUR_TUNNEL_ID` with your actual tunnel ID):
```yaml
tunnel: YOUR_TUNNEL_ID
credentials-file: /Users/slimslavik/.cloudflared/YOUR_TUNNEL_ID.json

ingress:
  - hostname: lexipark.com
    service: http://localhost:8000
  - hostname: www.lexipark.com
    service: http://localhost:8000
  - hostname: ws.lexipark.com
    service: ws://localhost:8765
  - service: http_status:404
```

### 5. Set Up DNS Routes
```bash
cloudflared tunnel route dns lexipark lexipark.com
cloudflared tunnel route dns lexipark www.lexipark.com
cloudflared tunnel route dns lexipark ws.lexipark.com
```

### 6. Add Domain to Cloudflare
1. Go to https://dash.cloudflare.com
2. Click "Add a Site"
3. Enter `lexipark.com`
4. Follow the instructions to update nameservers at your registrar
5. Wait 10-30 minutes for DNS propagation

### 7. Start Everything
Open 2 terminal windows:

**Terminal 1 - Python Server:**
```bash
cd /Users/slimslavik/core
source .venv/bin/activate
cd back-end/server
python3 server.py
```

**Terminal 2 - Cloudflare Tunnel:**
```bash
cloudflared tunnel run lexipark
```

### 8. Test Your Site
Visit: https://lexipark.com

## That's it! 🎉

Your app is now live at:
- Main site: https://lexipark.com
- API: https://lexipark.com/translate
- WebSocket: wss://ws.lexipark.com

## Make It Permanent

To run automatically on startup:

```bash
cloudflared service install
sudo launchctl load /Library/LaunchDaemons/com.cloudflare.cloudflared.plist
```

For the Python server, use PM2:
```bash
npm install -g pm2
cd /Users/slimslavik/core/back-end/server
pm2 start server.py --name lexipark --interpreter python3
pm2 save
pm2 startup
```

## Troubleshooting

### Can't access site?
- Check nameservers are pointing to Cloudflare
- Wait for DNS propagation (can take up to 24 hours)
- Verify both servers are running: `ps aux | grep python` and `ps aux | grep cloudflared`

### 502 Bad Gateway?
- Make sure Python server is running on port 8000
- Check server logs for errors

### WebSocket not connecting?
- Verify WebSocket server is on port 8765
- Check tunnel config has correct ws.lexipark.com entry

## Useful Commands

```bash
# Check tunnel status
cloudflared tunnel list
cloudflared tunnel info lexipark

# View logs
tail -f ~/.cloudflared/tunnel.log
tail -f /var/log/cloudflared.log

# Restart tunnel
sudo launchctl unload /Library/LaunchDaemons/com.cloudflare.cloudflared.plist
sudo launchctl load /Library/LaunchDaemons/com.cloudflare.cloudflared.plist
```

## Next Steps

1. Set up SSL (automatic with Cloudflare)
2. Configure caching rules in Cloudflare dashboard
3. Set up analytics and monitoring
4. Add rate limiting for API endpoints
5. Set up automated backups for your database

For detailed instructions, see [DEPLOYMENT.md](DEPLOYMENT.md)

