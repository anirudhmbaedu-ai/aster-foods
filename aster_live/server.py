"""Loopback-only classroom server. Credentials stay in .env, never API responses."""
import os
import secrets
import threading
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from .engine import RunStopped, Team
from .events import EventLog, Telegram

ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / ".env")
app = FastAPI(title="Aster Foods · Agent Room")
app.mount("/web", StaticFiles(directory=ROOT / "web"), name="web")
RUNS = {}
RUN_LOCK = threading.Lock()
SESSION_TOKEN = secrets.token_urlsafe(32)


def settings():
    return {key: os.getenv(key, "").strip() for key in
            ("GOOGLE_API_KEY", "GEMINI_MODEL", "TELEGRAM_BOT_TOKEN", "TELEGRAM_CHAT_ID")}


@app.middleware("http")
async def local_only(request: Request, call_next):
    # Prevent DNS rebinding and cross-origin requests from initiating paid model runs.
    if request.url.hostname not in ("127.0.0.1", "localhost", "testserver"):
        from fastapi.responses import JSONResponse
        return JSONResponse({"detail": "Use localhost."}, status_code=403)
    if request.method == "POST" and request.headers.get("x-session-token") != SESSION_TOKEN:
        from fastapi.responses import JSONResponse
        return JSONResponse({"detail": "Refresh the local app."}, status_code=403)
    response = await call_next(request)
    response.headers["Cache-Control"] = "no-store"
    response.headers["X-Content-Type-Options"] = "nosniff"
    return response


@app.get("/")
def index():
    return FileResponse(ROOT / "web" / "index.html")


@app.get("/api/config")
def config():
    env = settings()
    return {"gemini_ready": bool(env["GOOGLE_API_KEY"]),
            "telegram_ready": bool(env["TELEGRAM_BOT_TOKEN"] and env["TELEGRAM_CHAT_ID"]),
            "model": env["GEMINI_MODEL"] or "gemini-2.5-flash",
            "session_token": SESSION_TOKEN}


class Mission(BaseModel):
    prompt: str = Field(min_length=10, max_length=6000)
    telegram: bool = True
    delegation_limit: int = Field(default=10, ge=5, le=15)


def safe_error(error):
    if isinstance(error, RunStopped):
        return str(error)
    # Provider errors may embed API keys or request URLs. Keep raw exceptions out of logs/UI.
    return ("Execution failed. Check the Gemini key, selected model, quota and connection. "
            "Completed specialist findings remain available. No successful completion is claimed.")


@app.post("/api/runs")
def start(body: Mission):
    env = settings()
    if not env["GOOGLE_API_KEY"]:
        raise HTTPException(400, "Add GOOGLE_API_KEY to .env and restart the server.")
    if body.telegram and not (env["TELEGRAM_BOT_TOKEN"] and env["TELEGRAM_CHAT_ID"]):
        raise HTTPException(400, "Configure Telegram in .env or turn off Telegram for this run.")
    with RUN_LOCK:
        if any(run["status"] == "running" for run in RUNS.values()):
            raise HTTPException(409, "A mission is already running. Stop it or wait for completion.")
        run_id = secrets.token_hex(5)
        telegram = Telegram(env["TELEGRAM_BOT_TOKEN"], env["TELEGRAM_CHAT_ID"]) if body.telegram else None
        log = EventLog(run_id, ROOT / "runs", telegram)
        run = {"status": "running", "log": log, "team": None, "cancel": threading.Event()}
        RUNS[run_id] = run

    def work():
        try:
            team = Team(ROOT, log, env["GOOGLE_API_KEY"], env["GEMINI_MODEL"] or "gemini-2.5-flash",
                        limit=body.delegation_limit)
            run["team"] = team
            if run["cancel"].is_set():
                team.stop.set()
            team.run(body.prompt)
            run["status"] = "complete"
        except Exception as error:
            run["status"] = "stopped" if isinstance(error, RunStopped) else "failed"
            log.emit(run["status"], "SYSTEM", safe_error(error))
        finally:
            log.close()
    threading.Thread(target=work, daemon=True).start()
    return {"id": run_id}


def get_run(run_id):
    if run_id not in RUNS:
        raise HTTPException(404, "Run not found in this server session. Saved logs are in runs/.")
    return RUNS[run_id]


@app.get("/api/runs/{run_id}")
def snapshot(run_id: str):
    run = get_run(run_id)
    events, delivery = run["log"].snapshot()
    return {"id": run_id, "status": run["status"], "events": events, "delivery": delivery,
            "telegram": bool(run["log"].telegram)}


@app.post("/api/runs/{run_id}/stop")
def stop(run_id: str):
    run = get_run(run_id)
    run["cancel"].set()
    if run["team"]:
        run["team"].stop.set()
    return {"message": "Stop requested. The current model call may finish before stopping."}
