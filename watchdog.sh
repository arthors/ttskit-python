#!/bin/bash
# TTSKit relay watchdog — keeps relay.py alive
while true; do
    if ! pgrep -f relay.py > /dev/null; then
        echo "[$(date)] Relay down, restarting..." >> /tmp/relay_watchdog.log
        cd /Users/apple/projects/ttskit && python3 relay.py >> /tmp/relay.log 2>&1 &
    fi
    sleep 30
done
