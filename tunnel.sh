#!/bin/bash
cd "$(dirname "$0")"
PY=".venv/bin/python"
if [ ! -x "$PY" ]; then
  PY="python3"
fi
exec "$PY" tunnel_runner.py

