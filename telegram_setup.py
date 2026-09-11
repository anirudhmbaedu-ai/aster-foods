"""Find the student's chat ID without printing the bot token or sending messages."""
import os
from pathlib import Path
import httpx
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent / ".env")
token = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
if not token:
    raise SystemExit("Add TELEGRAM_BOT_TOKEN to .env first.")
try:
    response = httpx.get(f"https://api.telegram.org/bot{token}/getUpdates", timeout=15)
    data = response.json()
    if not data.get("ok"):
        raise ValueError()
except Exception:
    raise SystemExit("Could not read bot updates. Check the token, network, and whether a webhook is active.") from None
chats = {}
for update in data.get("result", []):
    message = update.get("message", {}) or update.get("channel_post", {})
    chat = message.get("chat", {})
    if "id" in chat:
        chats[chat["id"]] = chat.get("title") or chat.get("first_name") or chat.get("type")
if not chats:
    print("Open your bot in Telegram, press Start, send 'hello', then run this command again.")
else:
    for chat_id, label in chats.items():
        print(f"{label}: TELEGRAM_CHAT_ID={chat_id}")
    print("Copy your own chat ID into .env, then restart the app.")
