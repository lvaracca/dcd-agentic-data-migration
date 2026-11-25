#!/usr/bin/env bash
# ==============================================================================
# Executed inside quickbite-airbyte-vm (Ubuntu 24.04) via IAP SSH
# Installs Docker, launches PostgreSQL OLTP (port 5439), and installs Airbyte OSS
# via abctl on port 8000 (--insecure-cookies for smooth SSH/IAP localhost access).
# ==============================================================================
set -euo pipefail

echo "=== [VM 1/4] Installing Docker Engine & Compose ==="
if ! command -v docker >/dev/null 2>&1; then
  sudo apt-get update -qq
  sudo DEBIAN_FRONTEND=noninteractive apt-get install -y -qq ca-certificates curl jq docker.io docker-compose-v2
  sudo systemctl enable --now docker
  sudo usermod -aG docker "$USER"
fi

echo "=== [VM 2/4] Starting urbanfork-oltp-postgres Container (Port 5439) ==="
mkdir -p ~/urbanfork-oltp
mv -f ~/docker-compose.oltp.yml ~/urbanfork-oltp/docker-compose.oltp.yml
mv -f ~/init_oltp.sql ~/urbanfork-oltp/init_oltp.sql
sudo docker compose -f ~/urbanfork-oltp/docker-compose.oltp.yml up -d

echo "=== [VM 3/4] Installing Airbyte abctl CLI ==="
if ! command -v abctl >/dev/null 2>&1; then
  curl -LsfS https://get.airbyte.com | bash -
fi

echo "=== [VM 4/4] Deploying Airbyte OSS (Port 8000, HTTP tunnel-friendly) ==="
sg docker -c "abctl local install --port 8000 --insecure-cookies"

echo "=== Fetching Airbyte Local Credentials ==="
sg docker -c "abctl local credentials" > ~/airbyte_credentials.txt
echo "✅ PostgreSQL OLTP (5439) + Airbyte OSS (8000) are LIVE on VM!"
