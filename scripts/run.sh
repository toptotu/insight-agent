#!/usr/bin/env bash
set -euo pipefail

source .venv/bin/activate
if [ -f .env ]; then
  set -a
  source .env
  set +a
fi
uvicorn app.main:app --host 0.0.0.0 --port 8000
