#!/usr/bin/env bash
# ModFerry launcher for Linux and macOS
set -e
cd "$(dirname "$0")"
[ -x .venv/bin/python ] || python3 -m venv .venv
.venv/bin/python -m pip install --disable-pip-version-check -q -r requirements.txt
PORT="${MODFERRY_PORT:-8765}"
URL="http://127.0.0.1:${PORT}"
echo "ModFerry: open ${URL} in your browser"
( sleep 2; (command -v xdg-open >/dev/null && xdg-open "$URL") || (command -v open >/dev/null && open "$URL") || true ) >/dev/null 2>&1 &
.venv/bin/python app.py
