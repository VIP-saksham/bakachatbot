#!/usr/bin/env bash
# RyanBaka startup script with watchdog (restarts the bot on crash).
# Use this as the entrypoint for a tmux/screen session or a systemd/supervisor unit.

set -uo pipefail

cd /root/nakshu/ryanbaka

# Load .env if present
if [ -f /root/nakshu/ryanbaka/ryan.env ]; then
    set -a
    source /root/nakshu/ryanbaka/ryan.env
    set +a
fi

export GIT_PYTHON_REFRESH="${GIT_PYTHON_REFRESH:-quiet}"
export PYTHONUNBUFFERED=1
export PORT="${PORT:-5000}"

LOG_FILE="/root/nakshu/ryanbaka/baka.log"

# Watchdog loop: restart the bot whenever it exits (crash, signal, etc.)
while true; do
    echo "=== $(date '+%Y-%m-%d %H:%M:%S') bot restart ===" | tee -a "$LOG_FILE"
    /root/nakshu/venv/bin/python /root/nakshu/ryanbaka/Ryan.py >> "$LOG_FILE" 2>&1
    EXIT_CODE=$?
    echo "=== $(date '+%Y-%m-%d %H:%M:%S') bot exited with code $EXIT_CODE — restarting in 3s ===" | tee -a "$LOG_FILE"
    sleep 3
done
