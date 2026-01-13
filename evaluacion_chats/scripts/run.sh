#!/usr/bin/env bash
set -euo pipefail

if [ -f ".env" ]; then
  set -a
  # shellcheck disable=SC1091
  source .env
  set +a
fi

python src/eval_chats.py --input "${INPUT_SRC:-}" --output "${OUTPUT_PATH:-outputs/chats_evaluados.xlsx}"
