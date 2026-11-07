#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
mkdir -p work/npm-cache work/pip-cache
export npm_config_cache="$PWD/work/npm-cache"
export PIP_CACHE_DIR="$PWD/work/pip-cache"
if [ ! -d .venv ]; then python3 -m venv .venv; fi
.venv/bin/python -m pip install -r backend/requirements.txt
npm --prefix frontend ci
npm --prefix frontend run build
[ -f .env ] || cp .env.example .env
export PYTHONPATH="$PWD/backend"
export MPLCONFIGDIR="$PWD/work/matplotlib"
mkdir -p "$MPLCONFIGDIR"
exec .venv/bin/python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
