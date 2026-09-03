#!/usr/bin/env bash
# Ping Vision AI every 8 minutes (run on any always-on machine / Termux)
# Usage: APP_URL=https://your-app.com ./scripts/keep_alive.sh

APP_URL="${APP_URL:-}"
INTERVAL="${INTERVAL:-480}"

if [ -z "$APP_URL" ]; then
  echo "Set APP_URL=https://your-deployed-app"
  exit 1
fi

URL="${APP_URL%/}/api/keep-alive"
echo "Keep-alive → $URL every ${INTERVAL}s"
while true; do
  code=$(curl -s -o /dev/null -w "%{http_code}" --max-time 25 "$URL" || echo "err")
  echo "$(date -u +%H:%M:%S) HTTP $code"
  sleep "$INTERVAL"
done
