"""Persisted execution events, with a separate ordered Telegram delivery queue."""
import json
import queue
import threading
import time
from datetime import datetime, timezone
from pathlib import Path

import httpx


def chunks(text, size=1800):
    # At most 3600 UTF-16 units, including astral characters.
    return [text[i:i + size] for i in range(0, len(text), size)] or [""]


class Telegram:
    def __init__(self, token, chat_id, client=None, sleep=time.sleep):
        self.token, self.chat_id = token, chat_id
        self.client = client or httpx.Client(timeout=15)
        self.sleep = sleep

    def send(self, text):
        for part in chunks(text):
            for attempt in range(4):
                try:
                    response = self.client.post(
                        f"https://api.telegram.org/bot{self.token}/sendMessage",
                        json={"chat_id": self.chat_id, "text": part},
                    )
                    data = response.json()
                except (httpx.HTTPError, ValueError):
                    # Never surface request URLs: Telegram puts the token in the URL.
                    raise RuntimeError("Telegram connection failed; delivery unconfirmed.") from None
                if response.status_code == 429:
                    delay = data.get("parameters", {}).get("retry_after", 2)
                    self.sleep(min(float(delay), 60))
                    continue
                if response.status_code >= 500 and attempt < 3:
                    self.sleep(2 ** attempt)
                    continue
                if not response.is_success or not data.get("ok"):
                    raise RuntimeError("Telegram rejected the message. Check bot token, chat ID, and Start.")
                self.sleep(1.1)
                break
            else:
                raise RuntimeError("Telegram rate limit persisted. Delivery incomplete.")


class EventLog:
    def __init__(self, run_id, directory, telegram=None):
        self.run_id = run_id
        self.path = Path(directory) / run_id
        self.path.mkdir(parents=True, exist_ok=True)
        self.events = []
        self.lock = threading.Lock()
        self.telegram = telegram
        self.outbox = queue.Queue()
        self.delivery = {"queued": 0, "sent": 0, "failed": 0}
        if telegram:
            threading.Thread(target=self._deliver, daemon=True).start()

    def emit(self, kind, agent, text, target=None):
        with self.lock:
            event = dict(id=len(self.events) + 1, run_id=self.run_id,
                         time=datetime.now(timezone.utc).isoformat(),
                         kind=kind, agent=agent, target=target, text=str(text))
            self.events.append(event)
            with (self.path / "events.jsonl").open("a", encoding="utf-8") as handle:
                handle.write(json.dumps(event, ensure_ascii=False) + "\n")
            if self.telegram and kind != "delivery_error":
                self.delivery["queued"] += 1
                self.outbox.put(event)
        return event

    def snapshot(self):
        with self.lock:
            return list(self.events), dict(self.delivery)

    def close(self):
        if self.telegram:
            self.outbox.put(None)

    def _deliver(self):
        while True:
            event = self.outbox.get()
            if event is None:
                return
            target = f" → {event['target']}" if event['target'] else ""
            try:
                self.telegram.send(f"[{event['agent']}{target}] {event['kind']}\n"
                                   f"Run {self.run_id} · Update {event['id']}\n\n{event['text']}")
                with self.lock:
                    self.delivery["sent"] += 1
            except Exception:
                with self.lock:
                    self.delivery["failed"] += 1
                self.emit("delivery_error", "SYSTEM",
                          f"Telegram delivery unconfirmed for update {event['id']}. Local update is saved.")

