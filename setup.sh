#!/bin/bash
# =============================================================================
# Numbers10 PCMonitor — One-Command VPS Setup Script
# Run: chmod +x setup.sh && sudo ./setup.sh
# =============================================================================

set -e

DOMAIN="monitor.numbers10.co.za"
EMAIL="joe@numbers10.co.za"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "============================================"
echo "  Numbers10 PCMonitor — VPS Setup"
echo "============================================"
echo ""

# ── 1. Docker ────────────────────────────────────────────────────────────────
if ! command -v docker &>/dev/null; then
    echo "[1/6] Installing Docker..."
    curl -fsSL https://get.docker.com | sh
    systemctl enable docker
    systemctl start docker
else
    echo "[1/6] Docker already installed."
fi

if ! docker compose version &>/dev/null; then
    apt-get update -qq
    apt-get install -y -qq docker-compose-plugin
fi

# ── 2. .env ──────────────────────────────────────────────────────────────────
if [ ! -f .env ]; then
    echo "[2/6] Creating .env..."
    cp backend/.env.example .env
    DB_PASS=$(openssl rand -hex 16)
    SECRET=$(openssl rand -hex 32)
    sed -i "s/CHANGE_ME_strong_password_here/$DB_PASS/" .env
    sed -i "s/CHANGE_ME_generate_a_random_hex_string/$SECRET/" .env
    sed -i "s|https://localhost:8443|https://$DOMAIN:8443|g" .env
    sed -i "s|https://your-vps-ip:8443|https://$DOMAIN:8443|g" .env
    echo "  .env created with random passwords."
else
    echo "[2/6] .env already exists, skipping."
fi

# ── 3. Let's Encrypt certificate ─────────────────────────────────────────────
echo "[3/6] Checking SSL certificate..."

CERT_PATH="/etc/letsencrypt/live/$DOMAIN/fullchain.pem"

if [ -f "$CERT_PATH" ]; then
    echo "  Certificate already exists for $DOMAIN."
else
    echo "  Obtaining Let's Encrypt certificate for $DOMAIN..."

    # Install certbot if missing
    if ! command -v certbot &>/dev/null; then
        if command -v snap &>/dev/null; then
            snap install --classic certbot
            ln -sf /snap/bin/certbot /usr/bin/certbot
        else
            apt-get update -qq
            apt-get install -y certbot
        fi
    fi

    # Detect how to get the cert based on what's on port 80
    PORT80=$(ss -tlnp | grep ':80 ' | awk '{print $NF}' | grep -oP '"[^"]+"' | head -1 | tr -d '"')

    if echo "$PORT80" | grep -q "nginx"; then
        echo "  System nginx detected on port 80 — using nginx plugin..."
        certbot certonly --nginx \
            --non-interactive --agree-tos --email "$EMAIL" \
            -d "$DOMAIN"
    elif [ -z "$PORT80" ]; then
        echo "  Port 80 is free — using standalone mode..."
        certbot certonly --standalone \
            --non-interactive --agree-tos --email "$EMAIL" \
            -d "$DOMAIN"
    else
        echo "  Unknown process on port 80 ($PORT80) — trying standalone after stopping it..."
        PID80=$(ss -tlnp | grep ':80 ' | grep -oP 'pid=\K[0-9]+' | head -1)
        kill -STOP "$PID80" 2>/dev/null || true
        certbot certonly --standalone \
            --non-interactive --agree-tos --email "$EMAIL" \
            -d "$DOMAIN" || true
        kill -CONT "$PID80" 2>/dev/null || true
    fi

    if [ ! -f "$CERT_PATH" ]; then
        echo ""
        echo "  ERROR: Could not obtain certificate automatically."
        echo "  Run manually: certbot certonly --nginx -d $DOMAIN"
        echo "  Then re-run this script."
        exit 1
    fi

    echo "  Certificate obtained."

    # Auto-renewal: stop Docker nginx briefly, renew, restart
    RENEW_PRE="docker compose -f $SCRIPT_DIR/docker-compose.yml stop nginx"
    RENEW_POST="docker compose -f $SCRIPT_DIR/docker-compose.yml up -d nginx"
    CRON="0 3 * * 1 certbot renew --quiet --standalone --pre-hook \"$RENEW_PRE\" --post-hook \"$RENEW_POST\""
    (crontab -l 2>/dev/null | grep -v "certbot renew"; echo "$CRON") | crontab -
    echo "  Auto-renewal cron set (every Monday 3am)."
fi

# ── 4. Start containers ───────────────────────────────────────────────────────
echo "[4/6] Building and starting containers..."
docker compose up -d --build

# ── 5. Firewall ───────────────────────────────────────────────────────────────
echo "[5/6] Configuring firewall..."
if command -v ufw &>/dev/null; then
    ufw allow 8443/tcp
    echo "  UFW: port 8443 opened."
else
    echo "  UFW not found — ensure port 8443 is open in your firewall."
fi

# ── 6. Done ───────────────────────────────────────────────────────────────────
echo ""
echo "[6/6] Waiting for backend to be ready..."
sleep 5

echo ""
echo "============================================"
echo "  Numbers10 PCMonitor is running!"
echo "============================================"
echo ""
echo "  Dashboard:  https://$DOMAIN:8443"
echo ""
echo "  Default admin credentials:"
echo "    Email:    admin@numbers10.co.za"
echo "    Password: admin123"
echo ""
echo "  CHANGE THE DEFAULT PASSWORD IMMEDIATELY!"
echo ""
echo "  Port assignments:"
echo "    Public:   8443 → nginx (HTTPS, Let's Encrypt)"
echo "    Internal: 8888 → FastAPI backend"
echo "    Internal: 3030 → React frontend"
echo "    Internal: 5433 → PostgreSQL"
echo ""
echo "  To view logs: docker compose logs -f"
echo "  To stop:      docker compose down"
echo "============================================"
