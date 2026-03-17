#!/bin/bash
# =============================================================================
# Numbers10 PCMonitor — One-Command VPS Setup Script
# Run: chmod +x setup.sh && ./setup.sh
# =============================================================================

set -e

echo "============================================"
echo "  Numbers10 PCMonitor — VPS Setup"
echo "============================================"
echo ""

# 1. Install Docker + Docker Compose if not present
if ! command -v docker &> /dev/null; then
    echo "[1/7] Installing Docker..."
    curl -fsSL https://get.docker.com | sh
    sudo systemctl enable docker
    sudo systemctl start docker
    sudo usermod -aG docker "$USER"
    echo "Docker installed."
else
    echo "[1/7] Docker already installed."
fi

if ! docker compose version &> /dev/null; then
    echo "[1/7] Installing Docker Compose plugin..."
    sudo apt-get update -qq
    sudo apt-get install -y -qq docker-compose-plugin
else
    echo "[1/7] Docker Compose already installed."
fi

# 2. Navigate to project directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"
echo "[2/7] Working directory: $SCRIPT_DIR"

# 3. Create .env from example if it doesn't exist
if [ ! -f .env ]; then
    echo "[3/7] Creating .env from .env.example..."
    cp .env.example .env

    # Generate random passwords
    DB_PASS=$(openssl rand -hex 16)
    SECRET=$(openssl rand -hex 32)

    sed -i "s/CHANGE_ME_strong_password_here/$DB_PASS/" .env
    sed -i "s/CHANGE_ME_generate_a_random_hex_string/$SECRET/" .env

    echo ""
    echo "  Generated random DB_PASSWORD and SECRET_KEY."
    echo "  Edit .env to configure SMTP and Telegram settings."
    echo ""

    read -p "  Enter your VPS public IP or domain: " VPS_IP
    if [ -n "$VPS_IP" ]; then
        sed -i "s|https://localhost:8443|https://$VPS_IP:8443|g" .env
        sed -i "s|https://your-vps-ip:8443|https://$VPS_IP:8443|g" .env
    fi
else
    echo "[3/7] .env already exists, skipping."
fi

# 4. Generate self-signed SSL cert if none exists
if [ ! -f certs/server.crt ]; then
    echo "[4/7] Generating self-signed SSL certificate..."
    mkdir -p certs

    # Get the IP/domain for the cert
    VPS_IP=$(grep DASHBOARD_URL .env | head -1 | sed 's|.*://||' | sed 's|:.*||')
    if [ -z "$VPS_IP" ]; then
        VPS_IP="localhost"
    fi

    openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
        -keyout certs/server.key \
        -out certs/server.crt \
        -subj "/C=ZA/ST=Gauteng/L=Johannesburg/O=Numbers10 Technology Solutions/CN=$VPS_IP" \
        -addext "subjectAltName=DNS:$VPS_IP,DNS:localhost,IP:127.0.0.1" \
        2>/dev/null

    chmod 600 certs/server.key
    echo "  SSL certificate generated for: $VPS_IP"
else
    echo "[4/7] SSL certificates already exist."
fi

# 5. Build and start containers
echo "[5/7] Building and starting containers..."
docker compose up -d --build

# 6. Open UFW port 8443
echo "[6/7] Configuring firewall..."
if command -v ufw &> /dev/null; then
    sudo ufw allow 8443/tcp
    echo "  UFW: port 8443 opened."
else
    echo "  UFW not found. Make sure port 8443 is open in your firewall."
fi

# 7. Print success
echo ""
echo "============================================"
echo "  Numbers10 PCMonitor is running!"
echo "============================================"
echo ""
echo "  Dashboard:  https://${VPS_IP:-localhost}:8443"
echo ""
echo "  Default admin credentials:"
echo "    Email:    admin@numbers10.co.za"
echo "    Password: admin123"
echo ""
echo "  CHANGE THE DEFAULT PASSWORD IMMEDIATELY!"
echo ""
echo "  Port assignments:"
echo "    Public:   8443 → nginx (HTTPS)"
echo "    Internal: 8888 → FastAPI backend"
echo "    Internal: 3030 → React frontend"
echo "    Internal: 5433 → PostgreSQL"
echo ""
echo "  To view logs: docker compose logs -f"
echo "  To stop:      docker compose down"
echo "============================================"
