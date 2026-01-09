#!/usr/bin/env bash
set -euo pipefail

python -m pip install -U jupyter

jupyter nbconvert --to notebook --execute   --ExecutePreprocessor.timeout=7200   --output executed_llamadas.ipynb   llamadas.ipynb
