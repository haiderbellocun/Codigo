\
#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

rm -rf .build dist
mkdir -p .build dist

python -m pip install -U pip
python -m pip install -r requirements.txt -t .build

# Copiar código
cp -r src/* .build/

# Zip
(cd .build && zip -r ../dist/lambda.zip . >/dev/null)

echo "✅ ZIP creado: dist/lambda.zip"
