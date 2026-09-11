@echo off
setlocal
cd /d "%~dp0"

:: 1. Auto-detect Python: active virtualenv, Conda, local .venv, or system Python
set "PY_CMD="

if defined VIRTUAL_ENV (
    if exist "%VIRTUAL_ENV%\Scripts\python.exe" set "PY_CMD=%VIRTUAL_ENV%\Scripts\python.exe"
)
if not defined PY_CMD if defined CONDA_PREFIX (
    if exist "%CONDA_PREFIX%\python.exe" set "PY_CMD=%CONDA_PREFIX%\python.exe"
)
if not defined PY_CMD if exist ".venv\Scripts\python.exe" (
    set "PY_CMD=.venv\Scripts\python.exe"
)
if not defined PY_CMD (
    where python >nul 2>&1
    if %ERRORLEVEL% equ 0 set "PY_CMD=python"
)
if not defined PY_CMD (
    where py >nul 2>&1
    if %ERRORLEVEL% equ 0 set "PY_CMD=py"
)

if not defined PY_CMD (
    echo [ERROR] No Python installation found.
    echo Please install Python 3.11+ from https://www.python.org/ or install uv.
    pause
    exit /b 1
)

:: 2. Auto-create .env from .env.example if missing
if not exist ".env" (
    if exist ".env.example" (
        echo [.env not found - creating from .env.example]
        copy .env.example .env >nul
    )
)

:: 3. Check for dependencies, auto-install if missing
"%PY_CMD%" -c "import fastapi, uvicorn" >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo Installing dependencies from requirements.txt...
    where uv >nul 2>&1
    if %ERRORLEVEL% equ 0 (
        uv pip install -r requirements.txt
    ) else (
        "%PY_CMD%" -m pip install -r requirements.txt
    )
)

:: 4. Launch the application
echo Starting Aster Foods server on http://127.0.0.1:8766 ...
"%PY_CMD%" -m uvicorn aster_live.server:app --host 127.0.0.1 --port 8766 --no-access-log
