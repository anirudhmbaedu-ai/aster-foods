import json
from pathlib import Path

import httpx
import pytest
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage
from langchain_core.outputs import ChatGeneration, ChatResult
from pydantic import PrivateAttr

from aster_live.engine import RunStopped, SPECIALISTS, Team
from aster_live.events import EventLog, Telegram, chunks


class ScriptModel(BaseChatModel):
    _responses: list = PrivateAttr()
    _seen: list = PrivateAttr()

    def __init__(self, responses):
        super().__init__()
        self._responses = list(responses)
        self._seen = []

    @property
    def _llm_type(self):
        return "scripted-test-model"

    def bind_tools(self, tools, **kwargs):
        return self

    def _generate(self, messages, stop=None, run_manager=None, **kwargs):
        self._seen.append(messages)
        return ChatResult(generations=[ChatGeneration(message=self._responses.pop(0))])


def call(name, idx):
    return AIMessage(content="", tool_calls=[dict(name="delegate", args={"agent": name,
                     "assignment": f"Review and revise {name}"}, id=f"call-{idx}", type="tool_call")])


def build(tmp_path, supervisor=None, limit=10):
    responses = supervisor or [call(n, i) for i, n in enumerate(SPECIALISTS)] + [call("ATLAS", 6), AIMessage(content="Joint plan")]
    models = {n: ScriptModel([AIMessage(content=n + " finding"), AIMessage(content=n + " revised")]) for n in SPECIALISTS}
    models["JARVIS"] = ScriptModel(responses)
    log = EventLog("test", tmp_path)
    team = Team(Path(__file__).parents[1], log, "unused", "unused", limit=limit,
                model_factory=lambda name: models[name])
    return team, log, models


def test_real_langchain_delegation_context_and_revision(tmp_path):
    team, log, models = build(tmp_path)
    assert team.run("Reduce our budget by 25%") == "Joint plan"
    assert set(team.board) == set(SPECIALISTS)
    assert team.board["ATLAS"] == "ATLAS revised"
    assert "LEDGER finding" in models["ATLAS"]._seen[0][-1].content
    assert "ATLAS finding" in models["ATLAS"]._seen[1][-1].content
    assert "NOVA finding" in models["ATLAS"]._seen[1][-1].content
    assert [e["agent"] for e in log.events if e["kind"] == "result"] == list(SPECIALISTS) + ["ATLAS"]
    assert (log.path / "brief.md").read_text() == "Joint plan"
    assert len((log.path / "events.jsonl").read_text().splitlines()) == len(log.events)


def test_governance_rejects_fabricated_team_completion(tmp_path):
    team, log, models = build(tmp_path, [AIMessage(content="All done"), AIMessage(content="All done again")])
    with pytest.raises(RuntimeError, match="all five"):
        team.run("Review launch readiness")
    assert not any(e["kind"] == "complete" for e in log.events)


def test_limit_stops_revision_loop(tmp_path):
    team, log, models = build(tmp_path, limit=5)
    with pytest.raises(RunStopped, match="limit"):
        team.run("Review launch readiness")
    assert team.calls == 5


def test_cancel_before_model_call(tmp_path):
    team, log, models = build(tmp_path)
    team.stop.set()
    with pytest.raises(RunStopped, match="Stopped"):
        team.run("Review launch readiness")
    assert not models["JARVIS"]._seen


def test_telegram_chunks_and_rate_limit():
    bodies, delays = [], []
    def handler(request):
        bodies.append(json.loads(request.content))
        if len(bodies) == 1:
            return httpx.Response(429, json={"ok": False, "parameters": {"retry_after": 2}})
        return httpx.Response(200, json={"ok": True})
    telegram = Telegram("SECRET", "123", httpx.Client(transport=httpx.MockTransport(handler)), delays.append)
    telegram.send("🚀" * 4000)
    assert len(bodies) == 4  # Three chunks plus the retry.
    assert all(len(b["text"].encode("utf-16-le")) // 2 <= 4096 for b in bodies)
    assert delays[0] == 2


def test_telegram_error_redacts_secret():
    def handler(request):
        raise httpx.ConnectError("https://api.telegram.org/botSECRET", request=request)
    telegram = Telegram("SECRET", "123", httpx.Client(transport=httpx.MockTransport(handler)), lambda _: None)
    with pytest.raises(RuntimeError) as error:
        telegram.send("hello")
    assert "SECRET" not in str(error.value)


def test_delivery_failure_does_not_recurse(tmp_path):
    class Broken:
        def send(self, text):
            raise RuntimeError("SECRET")
    import time
    log = EventLog("broken", tmp_path, Broken())
    log.emit("result", "ATLAS", "Proposal")
    log.close()
    for _ in range(100):
        if log.delivery["failed"]:
            break
        time.sleep(.01)
    events, delivery = log.snapshot()
    assert delivery == {"queued": 1, "sent": 0, "failed": 1}
    assert len(events) == 2
    assert "SECRET" not in json.dumps(events)


def test_api_missing_key_and_mutation_guard(monkeypatch):
    from fastapi.testclient import TestClient
    from aster_live import server
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
    client = TestClient(server.app)
    assert client.get("/").status_code == 200
    cfg = client.get("/api/config").json()
    assert cfg["gemini_ready"] is False
    assert "GOOGLE_API_KEY" not in cfg
    assert client.post("/api/runs", json={"prompt": "Review the launch"}).status_code == 403
    result = client.post("/api/runs", headers={"x-session-token": cfg["session_token"]},
                         json={"prompt": "Review the launch"})
    assert result.status_code == 400
