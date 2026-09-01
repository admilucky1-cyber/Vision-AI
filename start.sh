#!/bin/sh
set -e
cd /app 2>/dev/null || cd "$(dirname "$0")" || true
exec python run.py
