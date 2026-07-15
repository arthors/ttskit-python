#!/bin/bash
# TTSKit relay watchdog — only starts if relay is dead, never kills
while true; do
    COUNT=$(pgrep -cf relay.py 2>/dev/null || echo 0)
    if [ "$COUNT" -eq 0 ]; then
        echo "[$(date)] Relay down, restarting..." >> /tmp/relay_watchdog.log
        cd /Users/apple/projects/ttskit && python3 relay.py >> /tmp/relay.log 2>&1 &
    fi
    sleep 30
done
