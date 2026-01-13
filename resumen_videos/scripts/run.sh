#!/usr/bin/env bash
set -euo pipefail
if [ -f ".env" ]; then
  set -a
  # shellcheck disable=SC1091
  source .env
  set +a
fi
python src/resumen_videos.py --bucket "${S3_BUCKET:-}" --prefix "${S3_PREFIX_VIDEOS:-}"
