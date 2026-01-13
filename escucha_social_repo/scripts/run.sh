#!/usr/bin/env bash
set -euo pipefail

if [ -f ".env" ]; then
  set -a
  # shellcheck disable=SC1091
  source .env
  set +a
fi

python src/escucha_social.py --input "${INPUT_PATH:-}" --export "${EXPORT_XLSX:-analisis_escucha_social.xlsx}"
