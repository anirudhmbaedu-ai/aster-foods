#!/bin/sh
set -eu
cd "$(dirname "$0")"
if [ ! -x .venv/bin/python ]; then
  echo 'Create the environment first: uv venv --python 3.12 && uv pip install -r requirements.lock'
  exit 1
fi
exec .venv/bin/python -m uvicorn aster_live.server:app --host 127.0.0.1 --port 8766 --no-access-log
