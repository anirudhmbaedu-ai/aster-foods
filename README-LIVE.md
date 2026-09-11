# Aster Foods: the live agent room

JARVIS is the chief of staff. Five distinct LangChain agents use Gemini and their existing persona files. JARVIS chooses their assignments, receives their actual responses, shares findings, requests revisions, and produces a final coordinated brief. Every public execution update can be delivered to one Telegram chat and is displayed in the local UI.

## Start on macOS

Requirements: Python 3.11+ (3.12 recommended), `uv`, a Gemini API key, and optionally a Telegram bot token/chat ID.

```sh
cd /Users/arthiram/aster-foods
uv venv --python 3.12
uv pip install -r requirements.lock
cp .env.example .env
```

Edit `.env` privately. Add `GOOGLE_API_KEY` from https://aistudio.google.com/apikey. The default model is `gemini-2.5-flash`; set `GEMINI_MODEL` to a Gemini model supporting tool calling that your account can access. The API key and selected model must be usable under your account's current quota. Restart after editing environment settings. No keys are accepted by or returned to the browser.

```sh
sh start.sh
```

Open http://127.0.0.1:8766. The app also works with Telegram disabled. Model calls need internet; local UI assets require no build step. Fonts have system fallbacks.

Windows: `uv venv --python 3.12`, `uv pip install -r requirements.lock`, copy `.env.example` to `.env`, then `.venv\Scripts\python -m uvicorn aster_live.server:app --host 127.0.0.1 --port 8766`. Windows has not been tested on a Windows computer.

## Connect each student's Telegram

1. Open Telegram's official `@BotFather`, use `/newbot`, and copy the token into `TELEGRAM_BOT_TOKEN` in `.env`.
2. Open the new bot chat, press **Start**, and send `hello`.
3. With the environment active, run `python telegram_setup.py` (or `.venv/bin/python telegram_setup.py` on macOS).
4. Copy the ID for your own chat into `TELEGRAM_CHAT_ID` in `.env` and restart the server.
5. Select **Send every update to Telegram** before briefing JARVIS. This enables real outbound messages to that configured chat.

One bot serves all six agents. Message prefixes identify the speaker and recipient. Each student should use a separate bot/configuration; never paste tokens into a classroom chat. A bot can also post to a group when added with permission, using that group's ID. This app sends updates outward; it does not listen for Telegram commands. The setup helper only reads recent bot updates, and does not reset webhooks or consume them with an offset.

## Demonstrate real collaboration

Use the prefilled budget-cut mission. Watch JARVIS assign work, specialists report, and ATLAS revise after LEDGER's cost review. The sequence depends on Gemini's actual decisions. The backend passes a board of latest reports into every specialist invocation; specialists do not have hidden shared memory. Previous versions remain in the event log. Each new mission starts with an empty board.

An application governance check requires all five specialists to contribute before a successful final brief. JARVIS has a bounded delegation budget (default 10), allowing repeat assignments. If the model fails to consult all five, a correction is issued; if it still fails, the run is marked failed rather than presenting success. Independent tool calls are serialized so later agents see earlier reports. Stop takes effect at the next boundary; it cannot retract Telegram messages or cancel a provider request already in flight.

The original `simulate_launch.py` and `tools/` modules are preserved. Their simulated hiring, advertising and disbursement tools are deliberately not registered as real actions. The live specialists provide proposals; the actual external action currently implemented is Telegram delivery. No payment, hiring, advertising or compliance verification is performed.

## Files and classroom teaching order

1. `aster_live/engine.py`: load persona files and construct Gemini-backed `create_agent` instances.
2. The `delegate` LangChain tool exposes the five specialists to JARVIS. It also passes the shared findings and publishes events.
3. `aster_live/events.py`: save events and deliver them through Telegram's real `sendMessage` API.
4. `aster_live/server.py` and `web/`: loopback API and visual activity room.
5. `runs/<run-id>/events.jsonl` and `brief.md`: actual persisted outputs for reviewing and presenting.

The feed contains public assignments, progress statuses, completed specialist findings, failures, and the final brief. It does not expose hidden model reasoning or send individual text tokens. Telegram messages are queued in order, split for size, paced, and retried for rate limits/server failures. Delivery counters show sent and unconfirmed events. Network errors are not blindly retried because delivery may have occurred. Failed delivery remains visible locally. The queue is in memory: keep the process open until it drains; restarting does not replay pending messages. Saved run files remain on disk, but the UI run registry resets on restart.

## Verification and limits

```sh
.venv/bin/python -m pytest -q
```

Tests use scripted chat models through the real LangChain runtime; they do not incur API charges or send Telegram messages. They verify actual delegation, cross-agent context, revision, governance, bounded execution, cancellation, Telegram chunking/rate-limit recovery, and failure reporting. Live Gemini responses and actual Telegram receipt require a configured `.env` and a real mission. Settings labels indicate configuration presence, not a verified connection.

Troubleshooting: a model/quota error stops the mission and preserves completed results. Check key access, `GEMINI_MODEL`, quota and internet, then start a fresh mission. A Telegram error does not stop the agents: verify bot Start, token and chat ID. The server intentionally binds to localhost and permits only one active mission. It is a personal classroom application, not a multi-user hosted service.

Architecture sources: [LangChain supervisor/subagents](https://docs.langchain.com/oss/python/langchain/multi-agent/subagents), [Gemini integration](https://docs.langchain.com/oss/python/integrations/chat/google_generative_ai), [Telegram sendMessage](https://core.telegram.org/bots/api#sendmessage).
