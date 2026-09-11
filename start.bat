@echo off
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
    echo Create the environment first:
    echo   uv venv --python 3.12
    echo   uv pip install -r requirements.lock
    echo   copy .env.example .env
    exit /b 1
)

.venv\Scripts\python.exe -m uvicorn aster_live.server:app --host 127.0.0.1 --port 8766 --no-access-log
