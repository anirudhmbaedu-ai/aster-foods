#!/bin/sh
set -eu
cd "$(dirname "$0")"

# 1. Auto-detect Python: active virtualenv, local .venv, python3, or python
PY_CMD=""
if [ -n "${VIRTUAL_ENV:-}" ] && [ -x "${VIRTUAL_ENV}/bin/python" ]; then
  PY_CMD="${VIRTUAL_ENV}/bin/python"
elif [ -x ".venv/bin/python" ]; then
  PY_CMD=".venv/bin/python"
elif command -v python3 >/dev/null 2>&1; then
  PY_CMD="python3"
elif command -v python >/dev/null 2>&1; then
  PY_CMD="python"
else
  echo "Error: Python 3 not found on system." >&2
  exit 1
fi

# 2. Auto-create .env from .env.example if missing
if [ ! -f .env ] && [ -f .env.example ]; then
  echo "Creating .env from .env.example..."
  cp .env.example .env
fi

# 3. Check for dependencies, auto-install if missing
if ! "$PY_CMD" -c "import fastapi, uvicorn" >/dev/null 2>&1; then
  echo "Installing dependencies from requirements.txt..."
  if command -v uv >/dev/null 2>&1; then
    uv pip install -r requirements.txt
  else
    "$PY_CMD" -m pip install -r requirements.txt
  fi
fi

# 4. Launch the application
exec "$PY_CMD" -m uvicorn aster_live.server:app --host 127.0.0.1 --port 8766 --no-access-log
