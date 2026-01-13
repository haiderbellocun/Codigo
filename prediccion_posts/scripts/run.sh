#!/usr/bin/env bash
set -euo pipefail

if [ -f ".env" ]; then
  set -a
  # shellcheck disable=SC1091
  source .env
  set +a
fi

python src/predict_posts.py   --input "${INPUT_PATH:-}"   --export-json "${EXPORT_JSON:-predicciones_posts.json}"   --intervals "${INTERVALS_JSON:-}"
