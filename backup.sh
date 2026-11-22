#!/usr/bin/env bash
# Packs the whole of Vision (agents, procedures, memory, settings) into one file under backups/.
# Keeps the latest 7. Copy the newest file to your encrypted pen drive to carry Vision with you.
set -euo pipefail
cd "$(dirname "$0")"
mkdir -p backups
stamp=$(date +%Y-%m-%d_%H%M)
tar --exclude=./backups --exclude=./data/ollama -czf "backups/vision_$stamp.tar.gz" .
ls -1t backups/vision_*.tar.gz | tail -n +8 | xargs -r rm --
echo "Backup written: backups/vision_$stamp.tar.gz"
