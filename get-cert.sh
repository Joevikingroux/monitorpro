#!/bin/bash
# Get or renew a Let's Encrypt certificate for monitor.numbers10.co.za
# Run this once on the server before starting the stack.

DOMAIN="monitor.numbers10.co.za"
EMAIL="joe@numbers10.co.za"

set -e

echo "=== Numbers10 PCMonitor — Let's Encrypt Setup ==="
echo "Domain: $DOMAIN"
echo ""

# Install certbot if not present
if ! command -v certbot &>/dev/null; then
    echo "[1/4] Installing certbot..."
    apt-get update -qq
    apt-get install -y certbot
else
    echo "[1/4] certbot already installed."
fi

# Create webroot directory (bind-mounted into nginx container)
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
mkdir -p "$SCRIPT_DIR/certbot-webroot"

echo "[2/4] Starting nginx with temporary self-signed cert so port 80 is reachable..."
# If the stack is already up, nginx is already serving port 80 (ACME challenge block)
# If not, start just nginx with self-signed cert temporarily
if ! docker compose ps nginx 2>/dev/null | grep -q "running\|Up"; then
    echo "  Stack not running — starting nginx temporarily..."
    # Use self-signed cert if LE cert doesn't exist yet
    if [ ! -f "/etc/letsencrypt/live/$DOMAIN/fullchain.pem" ]; then
        # Bootstrap: get cert via standalone (stop nginx if running)
        echo "[2/4] Getting initial cert via standalone mode (needs port 80 free)..."
        docker compose stop nginx 2>/dev/null || true
        certbot certonly \
            --standalone \
            --non-interactive \
            --agree-tos \
            --email "$EMAIL" \
            -d "$DOMAIN"
        echo "[3/4] Certificate obtained successfully."
    fi
else
    echo "[2/4] nginx is running — using webroot method..."
    # Nginx is already running with the ACME block on port 80
    # Use webroot pointed at the certbot-webroot volume
    WEBROOT="$SCRIPT_DIR/certbot-webroot"
    certbot certonly \
        --webroot \
        --webroot-path "$WEBROOT" \
        --non-interactive \
        --agree-tos \
        --email "$EMAIL" \
        -d "$DOMAIN"
    echo "[3/4] Certificate obtained successfully."
fi

echo "[4/4] Setting up auto-renewal cron job..."
CRON_JOB="0 3 * * * certbot renew --quiet --webroot --webroot-path $SCRIPT_DIR/certbot-webroot && docker compose -f $SCRIPT_DIR/docker-compose.yml exec nginx nginx -s reload"
(crontab -l 2>/dev/null | grep -v "certbot renew"; echo "$CRON_JOB") | crontab -

echo ""
echo "=== Done! ==="
echo "Certificate is at: /etc/letsencrypt/live/$DOMAIN/"
echo "Auto-renewal cron set for 3am daily."
echo ""
echo "Now run: docker compose up -d --build"
echo "Dashboard: https://$DOMAIN:8443"
