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
    if "PYTEST_CURRENT_TEST" not in os.environ:
        load_dotenv(ROOT / ".env", override=True)
    return {key: os.getenv(key, "").strip() for key in
            ("OPENAI_API_KEY", "OPENAI_MODEL", "GOOGLE_API_KEY", "GEMINI_MODEL", "TELEGRAM_BOT_TOKEN", "TELEGRAM_CHAT_ID")}


def get_provider_config():
    env = settings()
    openai_key = env.get("OPENAI_API_KEY", "")
    google_key = env.get("GOOGLE_API_KEY", "")
    
    if openai_key:
        return {
            "provider": "openai",
            "api_key": openai_key,
            "model": env.get("OPENAI_MODEL") or "gpt-4o-mini",
            "ready": True
        }
    if google_key:
        return {
            "provider": "google",
            "api_key": google_key,
            "model": env.get("GEMINI_MODEL") or "gemini-2.5-flash",
            "ready": True
        }
    return {
        "provider": "openai",
        "api_key": "",
        "model": env.get("OPENAI_MODEL") or "gpt-4o-mini",
        "ready": False
    }


@app.middleware("http")
async def local_only(request: Request, call_next):
    # Enforce session token validation on state-mutating POST requests
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
    active = get_provider_config()
    tunnel_url = ""
    tunnel_file = ROOT / "tunnel_url.txt"
    if tunnel_file.exists():
        try:
            tunnel_url = tunnel_file.read_text(encoding="utf-8").strip()
        except Exception:
            pass
    return {"gemini_ready": active["ready"],
            "ready": active["ready"],
            "provider": active["provider"],
            "telegram_ready": bool(env["TELEGRAM_BOT_TOKEN"] and env["TELEGRAM_CHAT_ID"]),
            "model": active["model"],
            "public_url": tunnel_url,
            "session_token": SESSION_TOKEN}


class Mission(BaseModel):
    prompt: str = Field(min_length=10, max_length=6000)
    telegram: bool = True
    delegation_limit: int = Field(default=10, ge=5, le=15)


def safe_error(error):
    if isinstance(error, RunStopped):
        return str(error)
    err_msg = str(error)
    print(f"[ERROR] Mission execution failure: {type(error).__name__}: {err_msg}")
    err_lower = err_msg.lower()
    
    if "invalid_api_key" in err_lower or "incorrect api key" in err_lower or "authentication" in err_lower:
        return "Authentication Error: Invalid API key. Please check your OPENAI_API_KEY in .env and restart."
    if "insufficient_quota" in err_lower:
        return "Billing Error: Your OpenAI account has exceeded its current quota or lacks credits. Check https://platform.openai.com/account/billing."
    if "prepayment credits are depleted" in err_lower or "depleted" in err_lower:
        return ("Billing Error: Your Google AI Studio prepayment credits are depleted. "
                "Please add funds to your project at https://ai.studio/projects or create a key in a project with active quota.")
    if "resource_exhausted" in err_lower or "rate_limit" in err_lower or "429" in err_msg:
        return "Quota / Rate Limit Exceeded (429): Check your account quota and billing limits."
    if "not_found" in err_lower or "model_not_found" in err_lower or "404" in err_msg:
        return "Model Not Found (404): The selected model is not available for this API key. Try gpt-4o-mini."
    
    return ("Execution failed. Check the API key, selected model, quota and connection. "
            "Completed specialist findings remain available. No successful completion is claimed.")


@app.post("/api/runs")
def start(body: Mission):
    env = settings()
    active = get_provider_config()
    if not active["ready"]:
        raise HTTPException(400, "Add OPENAI_API_KEY (or GOOGLE_API_KEY) to .env and restart the server.")
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
            team = Team(ROOT, log, active["api_key"], active["model"],
                        limit=body.delegation_limit, provider=active["provider"])
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
