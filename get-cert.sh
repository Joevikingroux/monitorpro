#!/bin/bash
# Get or renew a Let's Encrypt certificate for monitor.numbers10.co.za
# Uses certbot standalone — temporarily pauses whatever holds port 80.

DOMAIN="monitor.numbers10.co.za"
EMAIL="joe@numbers10.co.za"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

set -e

echo "=== Numbers10 PCMonitor — Let's Encrypt Setup ==="
echo "Domain: $DOMAIN"
echo ""

# Install certbot if not present
if ! command -v certbot &>/dev/null; then
    echo "[1/4] Installing certbot via snap..."
    apt-get update -qq
    snap install --classic certbot
    ln -sf /snap/bin/certbot /usr/bin/certbot
else
    echo "[1/4] certbot already installed."
fi

# Find what is holding port 80 and stop it temporarily
PORT80_PID=$(ss -tlnp | awk '/:80[ \t]/{match($0,/pid=([0-9]+)/,a); if(a[1]) print a[1]}' | head -1)
PORT80_SERVICE=""
if [ -n "$PORT80_PID" ]; then
    PORT80_SERVICE=$(systemctl list-units --type=service --state=running | awk '{print $1}' | while read svc; do
        systemctl show "$svc" --property=MainPID --value 2>/dev/null | grep -q "^$PORT80_PID$" && echo "$svc"
    done | head -1)
fi

echo "[2/4] Freeing port 80..."
if [ -n "$PORT80_SERVICE" ]; then
    echo "  Stopping $PORT80_SERVICE temporarily..."
    systemctl stop "$PORT80_SERVICE"
elif [ -n "$PORT80_PID" ]; then
    echo "  Killing PID $PORT80_PID temporarily..."
    kill -STOP "$PORT80_PID"
fi

# Also stop nginx container if it holds port 80
docker compose -f "$SCRIPT_DIR/docker-compose.yml" stop nginx 2>/dev/null || true

echo "[3/4] Obtaining certificate..."
certbot certonly \
    --standalone \
    --non-interactive \
    --agree-tos \
    --email "$EMAIL" \
    -d "$DOMAIN"

echo "  Certificate obtained."

# Restore whatever was stopped
echo "[4/4] Restoring services..."
if [ -n "$PORT80_SERVICE" ]; then
    systemctl start "$PORT80_SERVICE"
elif [ -n "$PORT80_PID" ]; then
    kill -CONT "$PORT80_PID"
fi

docker compose -f "$SCRIPT_DIR/docker-compose.yml" up -d nginx
echo "  nginx restarted."

# Set up auto-renewal cron (runs at 3am, uses standalone with pre/post hooks)
RENEW_PRE="docker compose -f $SCRIPT_DIR/docker-compose.yml stop nginx"
RENEW_POST="docker compose -f $SCRIPT_DIR/docker-compose.yml up -d nginx"
CRON_JOB="0 3 * * 1 certbot renew --quiet --standalone --pre-hook \"$RENEW_PRE\" --post-hook \"$RENEW_POST\""
(crontab -l 2>/dev/null | grep -v "certbot renew"; echo "$CRON_JOB") | crontab -

echo ""
echo "=== Done! ==="
echo "Certificate: /etc/letsencrypt/live/$DOMAIN/fullchain.pem"
echo "Auto-renewal: every Monday at 3am (nginx briefly stopped during renew)"
echo "Dashboard: https://$DOMAIN:8443"
