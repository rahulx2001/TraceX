"""Baseten backend for Muse Spark Open (text + reasoning + vision).  [AI-LAYER]

Every network call is faked; the key here is an obviously fake placeholder.
Covers backend selection, pinned host/model routing, the json_schema ->
json_object fallback, reasoning tolerance, Meta-only entry points failing
fast, secret-free status, and the Tier-2 narrator provider.
"""

from __future__ import annotations

import json

import pytest

from src.ai_layer import config, meta_client
from src.ai_layer.meta_client import MetaError, chat_json

SCHEMA = {
    "type": "object",
    "properties": {"x": {"type": "integer", "minimum": 0}},
    "required": ["x"],
}

FAKE_BASETEN_KEY = "test-baseten-not-a-real-key"
BASETEN_URL = "https://inference.baseten.co/v1/chat/completions"
BASETEN_MODEL = "meta-models/muse-spark-open-1026"


@pytest.fixture
def baseten_env(monkeypatch, tmp_path):
    monkeypatch.setenv("BASETEN_API_KEY", FAKE_BASETEN_KEY)
    monkeypatch.delenv("META_API_KEY", raising=False)
    monkeypatch.delenv("MODEL_API_KEY", raising=False)
    monkeypatch.delenv("META_BACKEND", raising=False)
    monkeypatch.delenv("FRONTLINE_AI_LAYER", raising=False)
    monkeypatch.setenv("META_RETRIES", "0")
    monkeypatch.setenv("META_CAP_PATH", str(tmp_path / "meta_calls.json"))
    monkeypatch.setenv("META_BUDGET_PATH", str(tmp_path / "meta_budget.sqlite"))
    meta_client.reset_call_cap()
    meta_client._SIMPLE_FORMAT_HOSTS.clear()
    yield
    meta_client.reset_call_cap()
    meta_client._SIMPLE_FORMAT_HOSTS.clear()


@pytest.fixture
def capture_transport(monkeypatch, tmp_path):
    """Raw capture transport with a scripted (status, body) queue."""
    from src.ai_layer.meta_client import HttpResponse

    calls: list[dict] = []
    queue: list[tuple] = []

    def _transport(url, body, headers, timeout):
        calls.append({"url": url, "payload": json.loads(body.decode()),
                      "headers": dict(headers), "timeout": timeout})
        if queue:
            status, payload = queue.pop(0)
            return HttpResponse(status=status, body=json.dumps(payload).encode(),
                                content_type="application/json")
        env = {"choices": [{"message": {"role": "assistant", "content": '{"x": 1}'}}]}
        return HttpResponse(status=200, body=json.dumps(env).encode(),
                            content_type="application/json")

    monkeypatch.setenv("META_RETRIES", "0")
    monkeypatch.setenv("META_CAP_PATH", str(tmp_path / "meta_calls.json"))
    monkeypatch.setenv("META_BUDGET_PATH", str(tmp_path / "meta_budget.sqlite"))
    meta_client.reset_call_cap()
    meta_client._SIMPLE_FORMAT_HOSTS.clear()
    meta_client.set_transport(_transport)
    yield calls, queue
    meta_client.set_transport(None)
    meta_client.reset_call_cap()
    meta_client._SIMPLE_FORMAT_HOSTS.clear()


def _chat(calls, queue, **kw):
    return chat_json(system="s", user="u", schema=SCHEMA, schema_name="t", **kw)


# ── backend selection ────────────────────────────────────────────────


def test_backend_matrix(monkeypatch):
    monkeypatch.delenv("FRONTLINE_AI_LAYER", raising=False)
    monkeypatch.delenv("META_BACKEND", raising=False)
    monkeypatch.delenv("META_API_KEY", raising=False)
    monkeypatch.delenv("MODEL_API_KEY", raising=False)
    monkeypatch.delenv("BASETEN_API_KEY", raising=False)
    assert config.backend() == "none"
    assert not config.meta_enabled()

    monkeypatch.setenv("META_API_KEY", "m")
    assert config.backend() == "meta"
    assert config.meta_enabled()

    monkeypatch.setenv("BASETEN_API_KEY", "b")
    assert config.backend() == "baseten"  # auto prefers Baseten

    monkeypatch.setenv("META_BACKEND", "meta")
    assert config.backend() == "meta"

    monkeypatch.setenv("META_BACKEND", "baseten")
    monkeypatch.delenv("BASETEN_API_KEY", raising=False)
    assert config.backend() == "none"  # pinned but keyless: fail closed
    assert not config.meta_enabled()

    monkeypatch.delenv("META_BACKEND", raising=False)
    monkeypatch.setenv("FRONTLINE_AI_LAYER", "off")
    assert not config.meta_enabled()


def test_baseten_pins_host_model_and_allows_host(baseten_env):
    assert config.api_base() == "https://inference.baseten.co/v1"
    assert config.chat_url() == BASETEN_URL
    assert config.model_text() == BASETEN_MODEL
    assert config.model_vision() == BASETEN_MODEL
    assert "inference.baseten.co" in config.allowed_hosts()
    assert config.max_tokens() == 8000


def test_meta_defaults_unchanged(fake_meta):
    assert config.backend() == "meta"
    assert config.chat_url() == "https://api.meta.ai/v1/chat/completions"
    assert config.model_text() == "muse-spark-1.3"
    assert config.max_tokens() == 2000


def test_status_names_backend_without_key(baseten_env):
    st = config.ai_status()
    assert st["provider"] == "baseten"
    assert st["key_configured"] is True
    assert st["models"]["text"] == BASETEN_MODEL
    assert FAKE_BASETEN_KEY not in json.dumps(st)


# ── routing + payload ────────────────────────────────────────────────


def test_baseten_routing_and_key(baseten_env, capture_transport, monkeypatch):
    monkeypatch.delenv("META_API_KEY", raising=False)
    calls, _ = capture_transport
    assert _chat(calls, _) == {"x": 1}
    assert calls[0]["url"] == BASETEN_URL
    assert calls[0]["headers"]["Authorization"] == f"Bearer {FAKE_BASETEN_KEY}"
    assert calls[0]["payload"]["model"] == BASETEN_MODEL
    assert calls[0]["payload"]["max_tokens"] == 8000
    assert calls[0]["payload"]["response_format"]["type"] == "json_schema"


def test_baseten_token_floor_for_reasoning(baseten_env, capture_transport, monkeypatch):
    monkeypatch.delenv("META_API_KEY", raising=False)
    calls, _ = capture_transport
    _chat(calls, _, max_tokens=1200)
    assert calls[0]["payload"]["max_tokens"] == 4000


def test_meta_explicit_budget_preserved(fake_meta):
    fake_meta.chat["t"] = lambda p: {"x": 1}
    chat_json(system="s", user="u", schema=SCHEMA, schema_name="t", max_tokens=16)
    assert fake_meta.calls[0]["payload"]["max_tokens"] == 16


def test_vision_images_ride_chat(baseten_env, capture_transport, monkeypatch):
    monkeypatch.delenv("META_API_KEY", raising=False)
    calls, _ = capture_transport
    chat_json(system="s", user="u", schema=SCHEMA, schema_name="t",
              images=["data:image/png;base64,AAAA"])
    content = calls[0]["payload"]["messages"][1]["content"]
    assert content[0] == {"type": "text", "text": "u"}
    assert content[1]["type"] == "image_url"
    assert calls[0]["payload"]["model"] == BASETEN_MODEL


# ── robustness ───────────────────────────────────────────────────────


def test_json_schema_fallback_then_remembered(baseten_env, capture_transport, monkeypatch):
    monkeypatch.delenv("META_API_KEY", raising=False)
    calls, queue = capture_transport
    ok = {"choices": [{"message": {"role": "assistant", "content": '{"x": 2}'}}]}
    queue.append((400, {"error": "unknown response_format"}))
    queue.append((200, ok))
    assert _chat(calls, queue) == {"x": 2}
    assert calls[0]["payload"]["response_format"]["type"] == "json_schema"
    assert calls[1]["payload"]["response_format"] == {"type": "json_object"}
    # Second call goes straight to the plain format (no wasted round trip).
    queue.append((200, ok))
    assert _chat(calls, queue) == {"x": 2}
    assert calls[2]["payload"]["response_format"] == {"type": "json_object"}


def test_no_fallback_on_auth_errors(baseten_env, capture_transport, monkeypatch):
    monkeypatch.delenv("META_API_KEY", raising=False)
    calls, queue = capture_transport
    queue.append((401, {"error": "bad key"}))
    with pytest.raises(MetaError) as e:
        _chat(calls, queue)
    assert e.value.reason == "meta_http_401"
    assert len(calls) == 1


def test_think_blocks_stripped():
    assert meta_client._parse_json_text("<think>hmm</think>\n```json\n{\"x\": 5}\n```") == {"x": 5}


def test_reasoning_channel_tolerated(baseten_env, capture_transport, monkeypatch):
    monkeypatch.delenv("META_API_KEY", raising=False)
    calls, queue = capture_transport
    queue.append((200, {"choices": [{"message": {
        "role": "assistant",
        "reasoning_content": "private thinking",
        "content": '{"x": 7}'}}]}))
    assert _chat(calls, queue) == {"x": 7}


def test_sam_and_image_fail_fast_on_baseten(baseten_env):
    with pytest.raises(MetaError) as e:
        meta_client.sam_segment(concept="brake disc", image_data_url="data:,x")
    assert e.value.reason == "model_unsupported_on_backend"
    with pytest.raises(MetaError) as e:
        meta_client.image_generate(prompt="a rotor")
    assert e.value.reason == "model_unsupported_on_backend"


# ── Tier-2 narrator ──────────────────────────────────────────────────


def test_narrator_baseten_fallback(monkeypatch):
    from src.ai import provider as prov

    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("CLAUDE_API_KEY", raising=False)
    monkeypatch.setenv("BASETEN_API_KEY", FAKE_BASETEN_KEY)
    assert prov.llm_provider() == "baseten"
    monkeypatch.setenv("OPENAI_API_KEY", "o")
    assert prov.llm_provider() == "openai"  # existing priority unchanged


def test_narrator_baseten_chat(monkeypatch):
    import urllib.request

    from src.ai import provider as prov

    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("CLAUDE_API_KEY", raising=False)
    monkeypatch.setenv("BASETEN_API_KEY", FAKE_BASETEN_KEY)
    seen: dict = {}

    class _Resp:
        def __enter__(self): return self
        def __exit__(self, *a): return False
        def read(self):
            return json.dumps({"choices": [{"message": {
                "content": "<think>draft</think>Found 2 similar cases."}}]}).encode()

    def _fake_open(req, timeout=None):
        seen["url"] = req.full_url
        seen["payload"] = json.loads(req.data.decode())
        seen["auth"] = req.headers.get("Authorization")
        return _Resp()

    monkeypatch.setattr(urllib.request, "urlopen", _fake_open)
    assert prov._http_chat_baseten("sys", "user") == "Found 2 similar cases."
    assert seen["url"] == BASETEN_URL
    assert seen["payload"]["model"] == BASETEN_MODEL
    assert seen["auth"] == f"Bearer {FAKE_BASETEN_KEY}"
    assert "temperature" not in seen["payload"]
