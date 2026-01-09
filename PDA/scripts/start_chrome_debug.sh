#!/usr/bin/env bash
set -euo pipefail

PORT="${PORT:-9222}"
PROFILE_DIR="${PROFILE_DIR:-$HOME/selenium/chrome-profile}"
mkdir -p "$PROFILE_DIR"

# Ajusta la ruta de Chrome si aplica (linux/mac)
CHROME_BIN="${CHROME_BIN:-google-chrome}"

"$CHROME_BIN"   --remote-debugging-port="$PORT"   --user-data-dir="$PROFILE_DIR"   --disable-popup-blocking   --no-first-run >/dev/null 2>&1 &

echo "✅ Chrome iniciado en DevTools: 127.0.0.1:$PORT"
echo "👉 Inicia sesión y deja el navegador abierto."
