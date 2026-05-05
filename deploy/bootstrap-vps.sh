#!/usr/bin/env bash
# Bootstrap script — run once on a fresh VPS
# Usage: bash deploy/bootstrap-vps.sh
set -euo pipefail

echo "==> HAWKEYE VPS Bootstrap"

# ── Docker ────────────────────────────────────────────────────────────────────
if ! command -v docker &>/dev/null; then
    echo "Installing Docker..."
    curl -fsSL https://get.docker.com | sh
    systemctl enable docker
    systemctl start docker
else
    echo "Docker already installed: $(docker --version)"
fi

if ! docker compose version &>/dev/null; then
    echo "Installing docker compose plugin..."
    apt-get install -y docker-compose-plugin
fi

# ── nginx ─────────────────────────────────────────────────────────────────────
if ! command -v nginx &>/dev/null; then
    echo "Installing nginx..."
    apt-get update && apt-get install -y nginx
    systemctl enable nginx
    systemctl start nginx
else
    echo "nginx already installed: $(nginx -v 2>&1)"
fi

# ── certbot ───────────────────────────────────────────────────────────────────
if ! command -v certbot &>/dev/null; then
    echo "Installing certbot..."
    apt-get install -y certbot python3-certbot-nginx
else
    echo "certbot already installed"
fi

# ── Directories ───────────────────────────────────────────────────────────────
echo "Creating data directories..."
mkdir -p /opt/hawkeye-data/{postgres,neo4j/data,neo4j/logs,kafka/data,redis/data,minio/data,keycloak/data,mlflow,grafana,artifacts,synthetic}
mkdir -p /opt/hawkeye
mkdir -p /var/www/certbot

# ── hawkeye user ──────────────────────────────────────────────────────────────
if ! id hawkeye &>/dev/null; then
    useradd -m -s /bin/bash hawkeye
    usermod -aG docker hawkeye
    echo "Created hawkeye user"
fi

chown -R hawkeye:hawkeye /opt/hawkeye /opt/hawkeye-data

# ── UFW ───────────────────────────────────────────────────────────────────────
if command -v ufw &>/dev/null; then
    ufw_status=$(ufw status | head -1)
    if echo "$ufw_status" | grep -q "active"; then
        echo "Configuring UFW..."
        ufw allow 22/tcp
        ufw allow 80/tcp
        ufw allow 443/tcp
        echo "UFW rules updated"
    fi
fi

echo ""
echo "==> Bootstrap complete!"
echo "    Next steps:"
echo "    1. Clone the repo to /opt/hawkeye"
echo "    2. Upload artifacts to /opt/hawkeye-data/artifacts/"
echo "    3. Upload synthetic data to /opt/hawkeye-data/synthetic/"
echo "    4. Install nginx config: cp infra/nginx/hawkeye.nineagents.in.conf /etc/nginx/sites-available/"
echo "    5. Run deploy/deploy.sh"
