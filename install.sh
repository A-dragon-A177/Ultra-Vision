#!/usr/bin/env bash
# One-time setup on a fresh Ubuntu machine (the free cloud VM, or any computer when restoring from the pen drive).
# Run from inside the vision folder:  bash install.sh
set -euo pipefail
cd "$(dirname "$0")"

if ! command -v docker >/dev/null; then
  echo "Installing Docker..."
  curl -fsSL https://get.docker.com | sudo sh
  sudo usermod -aG docker "$USER"
fi

if [ ! -f .env ]; then
  cp .env.example .env
  chmod 600 .env
  echo
  echo "Created .env. Open it (nano .env), fill in the three values, then run this script again."
  exit 0
fi

# Small machines (like Google's free e2-micro with 1 GB RAM) need swap space to build and run smoothly
if [ "$(free -m | awk '/Mem:/{print $2}')" -lt 2000 ] && ! swapon --show | grep -q .; then
  echo "Adding 2 GB of swap space..."
  sudo fallocate -l 2G /swapfile && sudo chmod 600 /swapfile && sudo mkswap /swapfile && sudo swapon /swapfile
  echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab >/dev/null
fi

mkdir -p data backups
sudo docker compose up -d --build

# Nightly backup at 02:30
( crontab -l 2>/dev/null | grep -v 'vision/backup.sh' ; echo "30 2 * * * bash $(pwd)/backup.sh >/dev/null 2>&1" ) | crontab -

echo
echo "Vision is running. Open Telegram and send /start to your bot."
echo "Logs:  sudo docker compose logs -f vision"
