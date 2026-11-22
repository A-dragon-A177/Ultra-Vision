#!/usr/bin/env bash
# Runs Vision on a Mac or Linux laptop:  bash run-mac-linux.sh   (keep the Terminal window open)
cd "$(dirname "$0")"
if [ ! -f .env ]; then
  cp .env.example .env && chmod 600 .env
  echo "Created .env. Open it, fill in your keys, save, then run this script again."
  exit 0
fi
if [ ! -d .venv ]; then
  echo "First run: setting up. This takes a minute..."
  python3 -m venv .venv && .venv/bin/pip install -q -r requirements.txt
fi
KEEP_AWAKE=""
command -v caffeinate >/dev/null && KEEP_AWAKE="caffeinate -is"   # stops a Mac sleeping while Vision runs
while true; do
  echo "Vision is starting. Press Ctrl+C twice to stop it."
  $KEEP_AWAKE .venv/bin/python -m app.main
  echo "Vision stopped. Restarting in 10 seconds..."
  sleep 10
done
