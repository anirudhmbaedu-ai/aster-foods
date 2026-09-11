"""Interactive Telegram Bot Daemon for Aster Foods · Live Agent Room.
Enables full bidirectional control via Telegram:
- Auto-detects chat ID and syncs to .env
- Runs multi-agent missions (/mission, /preset budget, /preset delay, /preset launch)
- Streams specialist delegations and reports to Telegram
- Answers executive inquiries directly via J.A.R.V.I.S.
- Reports status and latest briefs (/status, /brief)
"""
import json
import os
import re
import sys
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
import httpx
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent
load_dotenv(ROOT / ".env")

TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
TELEGRAM_API = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}"

PRESETS = {
    "budget": (
        "Our launch budget has been cut by 25%. Coordinate all five specialists, "
        "resolve conflicts, and give me a revised launch plan. "
        "Have ATLAS revise its proposal after LEDGER reviews the cost."
    ),
    "delay": (
        "Our packaging supplier is delayed by 14 days. Coordinate all five specialists to protect the launch. "
        "Have LEDGER challenge the recovery costs and ATLAS revise the plan."
    ),
    "launch": (
        "Review our readiness to launch 30,000 beverage units in 84 days with a ₹24 lakh budget. "
        "Consult all five specialists. Identify missing evidence, resolve conflicts, and assign next steps."
    )
}

ACTIVE_MISSION_LOCK = threading.Lock()
IS_MISSION_RUNNING = False


def sync_chat_id_to_env(chat_id: int):
    """Ensure TELEGRAM_CHAT_ID in .env is set so web server outbound updates also deliver to this chat."""
    env_path = ROOT / ".env"
    str_id = str(chat_id)
    if os.getenv("TELEGRAM_CHAT_ID") == str_id:
        return
    os.environ["TELEGRAM_CHAT_ID"] = str_id
    try:
        content = env_path.read_text(encoding="utf-8") if env_path.exists() else ""
        if "TELEGRAM_CHAT_ID=" in content:
            content = re.sub(r"TELEGRAM_CHAT_ID=.*", f"TELEGRAM_CHAT_ID={str_id}", content)
        else:
            content += f"\nTELEGRAM_CHAT_ID={str_id}\n"
        env_path.write_text(content, encoding="utf-8")
        print(f"[Telegram Bot] Synced TELEGRAM_CHAT_ID={str_id} to .env", flush=True)
    except Exception as e:
        print(f"[Telegram Bot] Notice: could not write chat_id to .env: {e}", flush=True)


def send_chat_action(client: httpx.Client, chat_id: int, action: str = "typing"):
    try:
        client.post(f"{TELEGRAM_API}/sendChatAction", json={"chat_id": chat_id, "action": action}, timeout=5)
    except Exception:
        pass


def send_message(client: httpx.Client, chat_id: int, text: str):
    max_len = 4000
    chunks = [text[i:i + max_len] for i in range(0, len(text), max_len)] or [""]
    for part in chunks:
        for attempt in range(3):
            try:
                res = client.post(f"{TELEGRAM_API}/sendMessage", json={"chat_id": chat_id, "text": part, "parse_mode": "HTML"}, timeout=15)
                if res.status_code == 429:
                    retry_after = res.json().get("parameters", {}).get("retry_after", 2)
                    time.sleep(min(float(retry_after), 30))
                    continue
                if not res.is_success and res.status_code == 400:
                    # Fallback to plain text if HTML tags were malformed
                    res = client.post(f"{TELEGRAM_API}/sendMessage", json={"chat_id": chat_id, "text": part}, timeout=15)
                if res.is_success:
                    break
            except Exception as e:
                time.sleep(1)
        time.sleep(0.5)


def get_latest_brief() -> str:
    runs_dir = ROOT / "runs"
    if not runs_dir.exists():
        return "No missions have been completed yet."
    run_folders = sorted([d for d in runs_dir.iterdir() if d.is_dir()], key=lambda d: d.stat().st_mtime, reverse=True)
    for folder in run_folders:
        brief_file = folder / "brief.md"
        if brief_file.exists():
            return brief_file.read_text(encoding="utf-8")
    return "No brief found in existing runs."


def get_provider_config():
    load_dotenv(ROOT / ".env", override=True)
    openai_key = os.getenv("OPENAI_API_KEY", "").strip()
    google_key = (os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY") or "").strip()

    if openai_key:
        return {
            "provider": "openai",
            "api_key": openai_key,
            "model": os.getenv("OPENAI_MODEL") or "gpt-4o-mini",
            "ready": True
        }
    if google_key:
        return {
            "provider": "google",
            "api_key": google_key,
            "model": os.getenv("GEMINI_MODEL") or "gemini-2.5-flash",
            "ready": True
        }
    return {
        "provider": "none",
        "api_key": "",
        "model": "",
        "ready": False
    }


def get_public_url() -> str:
    tunnel_file = ROOT / "tunnel_url.txt"
    if tunnel_file.exists():
        try:
            url = tunnel_file.read_text(encoding="utf-8").strip()
            if url.startswith("http"):
                return url
        except Exception:
            pass
    return "http://localhost:8766"


def run_mission_async(client: httpx.Client, chat_id: int, prompt: str):
    global IS_MISSION_RUNNING
    with ACTIVE_MISSION_LOCK:
        if IS_MISSION_RUNNING:
            send_message(client, chat_id, "⚠️ A mission is already in progress. Please wait for it to complete.")
            return
        IS_MISSION_RUNNING = True

    def _worker():
        global IS_MISSION_RUNNING
        try:
            from aster_live.engine import Team
            from aster_live.events import EventLog, Telegram

            config = get_provider_config()
            if not config["ready"]:
                send_message(client, chat_id, "❌ Error: Neither OPENAI_API_KEY nor GOOGLE_API_KEY is configured in .env")
                return

            api_key = config["api_key"]
            model = config["model"]
            provider = config["provider"]

            run_id = f"tg_{int(time.time())}"
            send_message(
                client,
                chat_id,
                f"🚀 <b>JARVIS Mission Started</b> (Run: <code>{run_id}</code>)\n\n"
                f"📋 <b>Briefing:</b> {prompt}\n\n"
                f"🧠 <b>Provider:</b> {provider.upper()} (<code>{model}</code>)\n"
                f"Delegating across specialists: LEDGER, ATLAS, PULSE, PRISM, NOVA..."
            )

            telegram_notifier = Telegram(TELEGRAM_TOKEN, str(chat_id), client=client)
            log = EventLog(run_id, ROOT / "runs", telegram=telegram_notifier)

            team = Team(ROOT, log, api_key, model, limit=10, provider=provider)
            result = team.run(prompt)
            log.close()

            send_message(
                client,
                chat_id,
                f"✅ <b>JARVIS Final Coordinated Brief</b> (Run: <code>{run_id}</code>):\n\n{result}"
            )
        except Exception as err:
            send_message(client, chat_id, f"❌ Mission stopped or encountered an error:\n{err}")
        finally:
            with ACTIVE_MISSION_LOCK:
                IS_MISSION_RUNNING = False

    threading.Thread(target=_worker, daemon=True).start()


def answer_inquiry_with_jarvis(client: httpx.Client, chat_id: int, query: str):
    try:
        config = get_provider_config()
        if not config["ready"]:
            send_message(client, chat_id, "❌ Neither OPENAI_API_KEY nor GOOGLE_API_KEY is configured in .env.")
            return

        persona_path = ROOT / "agents" / "JARVIS.md"
        persona = persona_path.read_text(encoding="utf-8") if persona_path.exists() else "You are JARVIS, chief of staff for Aster Foods."

        if config["provider"] == "google":
            from langchain_google_genai import ChatGoogleGenerativeAI
            llm = ChatGoogleGenerativeAI(
                model=config["model"],
                google_api_key=config["api_key"],
                vertexai=False,
                temperature=0.3,
                max_output_tokens=1000,
                timeout=45
            )
        else:
            from langchain_openai import ChatOpenAI
            llm = ChatOpenAI(
                model=config["model"],
                api_key=config["api_key"],
                temperature=0.3,
                max_tokens=1000,
                timeout=45
            )

        prompt = (
            f"{persona}\n\n"
            "You are responding directly in Telegram to the Founder. "
            "Keep the response concise, authoritative, executive, and structured.\n\n"
            f"Founder inquiry: {query}"
        )

        send_chat_action(client, chat_id, "typing")
        res = llm.invoke(prompt)
        text = res.content
        if isinstance(text, list):
            text = "\n".join(b.get("text", "") for b in text if isinstance(b, dict) and b.get("type") == "text")
        send_message(client, chat_id, f"🤖 <b>J.A.R.V.I.S.:</b>\n\n{text}")
    except Exception as e:
        send_message(client, chat_id, f"⚠️ J.A.R.V.I.S. error: {e}")


def handle_message(client: httpx.Client, message: dict):
    chat = message.get("chat", {})
    chat_id = chat.get("id")
    if not chat_id:
        return

    sync_chat_id_to_env(chat_id)

    text = message.get("text", "").strip()
    sender = message.get("from", {}).get("first_name", "Founder")

    if not text:
        return

    print(f"[{sender} -> Bot]: {text}", flush=True)

    # Command: /start or hello
    if text.lower() in ["/start", "start", "hello", "hi", "/help", "help"]:
        config = get_provider_config()
        public_url = get_public_url()
        welcome = (
            f"👋 <b>Welcome {sender}! J.A.R.V.I.S. Executive Link Online.</b>\n\n"
            f"I am your Chief of Staff for <b>Aster Foods · Live Agent Room</b>.\n"
            f"🌐 <b>Web Interface:</b> {public_url}\n"
            f"🧠 <b>LLM Provider:</b> {config['provider'].upper()} (<code>{config['model']}</code>)\n"
            f"Connected Telegram Chat ID: <code>{chat_id}</code> (synced with web server).\n\n"
            "<b>Team of Specialists:</b>\n"
            "• <b>LEDGER:</b> Finance & Treasury Control\n"
            "• <b>ATLAS:</b> Operations & Manufacturing (30k units)\n"
            "• <b>PULSE:</b> Marketing & Demand Acquisition\n"
            "• <b>PRISM:</b> Decision Analytics & Statistical Audit\n"
            "• <b>NOVA:</b> People, Capacity & Compliance\n\n"
            "<b>Available Commands:</b>\n"
            "🚀 <b>/mission &lt;prompt&gt;</b> — Brief JARVIS to coordinate all 5 specialists with live stream\n"
            "📊 <b>/preset budget</b> — Launch the 25% budget cut mission\n"
            "📦 <b>/preset delay</b> — Launch the 14-day packaging supplier delay mission\n"
            "🎯 <b>/preset launch</b> — Launch the 30,000 units launch readiness mission\n"
            "📋 <b>/status</b> — Check local server, public URL and model status\n"
            "📄 <b>/brief</b> — View the latest synthesized brief\n\n"
            "💡 <i>Or simply ask me any question directly!</i>"
        )
        send_message(client, chat_id, welcome)
        return

    # Command: /preset
    if text.startswith("/preset"):
        parts = text.split(maxsplit=1)
        preset_name = parts[1].strip().lower() if len(parts) > 1 else ""
        if preset_name in PRESETS:
            send_chat_action(client, chat_id, "typing")
            run_mission_async(client, chat_id, PRESETS[preset_name])
        else:
            send_message(client, chat_id, "Available presets: <code>/preset budget</code>, <code>/preset delay</code>, <code>/preset launch</code>")
        return

    # Command: /mission
    if text.startswith("/mission"):
        prompt = text[len("/mission"):].strip()
        if len(prompt) < 10:
            send_message(client, chat_id, "Please provide a mission prompt of at least 10 characters: e.g. <code>/mission Review launch readiness...</code>")
            return
        send_chat_action(client, chat_id, "typing")
        run_mission_async(client, chat_id, prompt)
        return

    # Command: /status
    if text.lower() in ["/status", "status"]:
        config = get_provider_config()
        public_url = get_public_url()
        status_msg = (
            f"ℹ️ <b>Aster Foods · System Status</b>\n\n"
            f"• <b>Web UI (Public):</b> {public_url}\n"
            f"• <b>Local Host:</b> http://127.0.0.1:8766\n"
            f"• <b>LLM Provider:</b> {config['provider'].upper()} (<code>{config['model']}</code>)\n"
            f"• <b>Active Mission:</b> {'RUNNING' if IS_MISSION_RUNNING else 'IDLE'}\n"
            f"• <b>Telegram Chat ID:</b> <code>{chat_id}</code>\n"
            f"• <b>Specialists Ready:</b> 5 (LEDGER, ATLAS, PULSE, PRISM, NOVA)\n"
            f"• <b>Status:</b> All systems operational ✅"
        )
        send_message(client, chat_id, status_msg)
        return

    # Command: /brief
    if text.lower() in ["/brief", "brief"]:
        send_chat_action(client, chat_id, "typing")
        brief = get_latest_brief()
        send_message(client, chat_id, f"📄 <b>Latest Executive Brief:</b>\n\n{brief}")
        return

    # Direct consultation with JARVIS
    send_chat_action(client, chat_id, "typing")
    answer_inquiry_with_jarvis(client, chat_id, text)


def main():
    if not TELEGRAM_TOKEN:
        print("ERROR: TELEGRAM_BOT_TOKEN not found in .env", flush=True)
        sys.exit(1)

    client = httpx.Client(timeout=30)

    # Test bot connection
    try:
        res = client.get(f"{TELEGRAM_API}/getMe")
        data = res.json()
        if not data.get("ok"):
            print(f"ERROR: Telegram API returned error: {data}", flush=True)
            sys.exit(1)
        bot_info = data["result"]
        print("==================================================", flush=True)
        print(f"🤖 Telegram Bot Online: @{bot_info.get('username')} ({bot_info.get('first_name')})", flush=True)
        print("Listening for incoming commands & inquiries...", flush=True)
        print("==================================================", flush=True)
    except Exception as e:
        print(f"ERROR: Could not reach Telegram API: {e}", flush=True)
        sys.exit(1)

    offset = 0
    while True:
        try:
            res = client.get(f"{TELEGRAM_API}/getUpdates", params={"offset": offset, "timeout": 15})
            if res.status_code == 200:
                data = res.json()
                for update in data.get("result", []):
                    offset = update["update_id"] + 1
                    msg = update.get("message") or update.get("channel_post")
                    if msg:
                        handle_message(client, msg)
            elif res.status_code == 409:
                time.sleep(2)
            else:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\nShutting down Telegram Bot.", flush=True)
            break
        except Exception as e:
            time.sleep(2)


if __name__ == "__main__":
    main()
