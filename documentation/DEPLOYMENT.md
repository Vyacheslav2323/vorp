# Deploying LexiPark with Cloudflare Tunnel

## Step 1: Add Domain to Cloudflare

1. Go to [cloudflare.com](https://cloudflare.com) and sign up/login
2. Click "Add a Site" and enter `lexipark.com`
3. Select the Free plan
4. Cloudflare will scan your DNS records
5. Update your domain's nameservers at your registrar to Cloudflare's nameservers:
   - Example: `alice.ns.cloudflare.com` and `bob.ns.cloudflare.com`
6. Wait for DNS propagation (can take up to 24 hours, usually faster)

## Step 2: Install Cloudflare Tunnel (cloudflared)

### macOS Installation
```bash
brew install cloudflared
```

Or download from: https://developers.cloudflare.com/cloudflare-one/connections/connect-apps/install-and-setup/installation/

### Verify Installation
```bash
cloudflared --version
```

## Step 3: Authenticate cloudflared

```bash
cloudflared tunnel login
```

This opens a browser window to authorize cloudflared with your Cloudflare account.

## Step 4: Create a Tunnel

```bash
cloudflared tunnel create lexipark
```

This creates a tunnel and saves credentials to:
`~/.cloudflared/<TUNNEL-ID>.json`

Save the Tunnel ID that's displayed.

## Step 5: Create Tunnel Configuration

Create the config file:
```bash
mkdir -p ~/.cloudflared
nano ~/.cloudflared/config.yml
```

Add this configuration:
```yaml
tunnel: <YOUR-TUNNEL-ID>
credentials-file: /Users/slimslavik/.cloudflared/<YOUR-TUNNEL-ID>.json

ingress:
  - hostname: lexipark.com
    service: http://localhost:8000
  - hostname: www.lexipark.com
    service: http://localhost:8000
  - hostname: ws.lexipark.com
    service: ws://localhost:8765
  - service: http_status:404
```

## Step 6: Create DNS Records

```bash
cloudflared tunnel route dns lexipark lexipark.com
cloudflared tunnel route dns lexipark www.lexipark.com
cloudflared tunnel route dns lexipark ws.lexipark.com
```

This automatically creates CNAME records in Cloudflare DNS.

## Step 7: Run the Tunnel

### Test run (foreground):
```bash
cloudflared tunnel run lexipark
```

### Run as background service (production):
```bash
cloudflared service install
sudo launchctl load /Library/LaunchDaemons/com.cloudflare.cloudflared.plist
```

## Step 8: Update Frontend Configuration

Update your frontend to use the production URLs:

**front-end/main.js** or **front-end/utils.js**:
```javascript
const API_BASE = 'https://lexipark.com';
const WS_URL = 'wss://ws.lexipark.com';
```

## Step 9: Start Your Server

```bash
cd /Users/slimslavik/core/back-end/server
source ../../.venv/bin/activate
python3 server.py
```

## Step 10: Test Your Deployment

1. Visit `https://lexipark.com` in your browser
2. Test WebSocket connection to `wss://ws.lexipark.com`
3. Test API endpoints:
   - `https://lexipark.com/translate`
   - `https://lexipark.com/register`
   - `https://lexipark.com/login`

## Useful Commands

### Check tunnel status
```bash
cloudflared tunnel list
cloudflared tunnel info lexipark
```

### View tunnel logs
```bash
tail -f ~/.cloudflared/tunnel.log
```

### Stop tunnel service
```bash
sudo launchctl unload /Library/LaunchDaemons/com.cloudflare.cloudflared.plist
```

### Restart tunnel service
```bash
sudo launchctl unload /Library/LaunchDaemons/com.cloudflare.cloudflared.plist
sudo launchctl load /Library/LaunchDaemons/com.cloudflare.cloudflared.plist
```

## Security Considerations

1. **SSL/TLS**: Cloudflare automatically provides SSL certificates
2. **Environment Variables**: Store sensitive data in environment variables
3. **CORS**: Update CORS headers in `server.py` if needed:
   ```python
   self.send_header('Access-Control-Allow-Origin', 'https://lexipark.com')
   ```

## Process Management (Production)

Consider using a process manager to keep your Python server running:

### Option 1: launchd (macOS native)
Create `/Library/LaunchDaemons/com.lexipark.server.plist`

### Option 2: systemd (Linux)
Create a systemd service file

### Option 3: PM2
```bash
npm install -g pm2
pm2 start "python3 server.py" --name lexipark --interpreter none
pm2 save
pm2 startup
```

## Monitoring

1. **Cloudflare Dashboard**: Monitor traffic, analytics, and threats
2. **Server Logs**: Monitor your Python server logs
3. **Uptime Monitoring**: Use services like UptimeRobot or Cloudflare's monitoring

## Troubleshooting

### Tunnel not connecting
- Check firewall settings
- Verify tunnel is running: `ps aux | grep cloudflared`
- Check logs: `cloudflared tunnel info lexipark`

### DNS not resolving
- Verify nameservers are set correctly at registrar
- Check DNS propagation: `dig lexipark.com`
- Wait for DNS propagation (up to 24 hours)

### 502 Bad Gateway
- Ensure your Python server is running on port 8000
- Check server logs for errors
- Verify the tunnel config points to correct ports

