"""Deepgram speech provider: opt-in STT/TTS behind ServerSpeechStack.

Hermetic by default — without DEEPGRAM_ENABLED=1 **and** DEEPGRAM_API_KEY the
stack keeps its offline pilot behavior (no network, no claims). All live-path
tests below inject a fake transport; the suite never calls api.deepgram.com.
"""

from __future__ import annotations

import base64
import json

import pytest


@pytest.fixture
def deepgram_env(monkeypatch):
    """Opt in to Deepgram with a fake key (transport still must be faked)."""
    monkeypatch.setenv("DEEPGRAM_ENABLED", "1")
    monkeypatch.setenv("DEEPGRAM_API_KEY", "test-key-not-real")
    monkeypatch.delenv("DEEPGRAM_STT_MODEL", raising=False)
    monkeypatch.delenv("DEEPGRAM_TTS_MODEL", raising=False)
    return monkeypatch


@pytest.fixture
def fake_deepgram():
    """Canned listen/speak transport. Restored after the test."""
    from src.channels import deepgram as dg

    calls: list[dict] = []

    def _transport(url: str, body: bytes, headers: dict, timeout: float):
        calls.append({"url": url, "body": body, "headers": dict(headers), "timeout": timeout})
        if "/v1/listen" in url:
            payload = {
                "results": {
                    "channels": [
                        {"alternatives": [{"transcript": "my brakes are grinding", "confidence": 0.94}]}
                    ]
                }
            }
            return dg.HttpResponse(status=200, body=json.dumps(payload).encode(), content_type="application/json")
        if "/v1/speak" in url:
            return dg.HttpResponse(status=200, body=b"ID3\x04fake-mp3-bytes", content_type="audio/mpeg")
        return dg.HttpResponse(status=404, body=b"{}", content_type="application/json")

    dg.set_transport(_transport)
    try:
        yield calls
    finally:
        dg.set_transport(None)


def test_deepgram_off_by_default(monkeypatch):
    from src.channels import deepgram as dg

    monkeypatch.delenv("DEEPGRAM_ENABLED", raising=False)
    monkeypatch.delenv("DEEPGRAM_API_KEY", raising=False)
    assert dg.deepgram_available() is False


def test_deepgram_key_alone_does_not_enable(monkeypatch):
    """A stray exported key must not flip hermetic suites to live behavior."""
    from src.channels import deepgram as dg

    monkeypatch.delenv("DEEPGRAM_ENABLED", raising=False)
    monkeypatch.setenv("DEEPGRAM_API_KEY", "test-key-not-real")
    assert dg.deepgram_available() is False


def test_deepgram_enabled_without_key_is_unavailable(monkeypatch):
    from src.channels import deepgram as dg

    monkeypatch.setenv("DEEPGRAM_ENABLED", "1")
    monkeypatch.delenv("DEEPGRAM_API_KEY", raising=False)
    assert dg.deepgram_available() is False


def test_transcribe_audio_returns_text_and_confidence(deepgram_env, fake_deepgram):
    from src.channels import deepgram as dg

    out = dg.transcribe_audio(b"\x1a\x45\xdf\xa3fake-webm", mime="audio/webm;codecs=opus")
    assert out["text"] == "my brakes are grinding"
    assert out["confidence"] == pytest.approx(0.94)
    # Key goes to the official host only, as a Token header.
    assert fake_deepgram[0]["url"].startswith("https://api.deepgram.com/v1/listen")
    assert fake_deepgram[0]["headers"]["Authorization"] == "Token test-key-not-real"


def test_transcribe_empty_result_is_no_speech(deepgram_env, monkeypatch):
    from src.channels import deepgram as dg

    def _empty(url: str, body: bytes, headers: dict, timeout: float):
        payload = {"results": {"channels": [{"alternatives": [{"transcript": "", "confidence": 0.0}]}]}}
        return dg.HttpResponse(status=200, body=json.dumps(payload).encode(), content_type="application/json")

    dg.set_transport(_empty)
    try:
        with pytest.raises(dg.DeepgramNoSpeech):
            dg.transcribe_audio(b"webm-bytes", mime="audio/webm")
    finally:
        dg.set_transport(None)


def test_transcribe_http_error_raises_log_safe(deepgram_env):
    from src.channels import deepgram as dg

    def _denied(url: str, body: bytes, headers: dict, timeout: float):
        return dg.HttpResponse(status=401, body=b'{"err_msg":"bad key"}', content_type="application/json")

    dg.set_transport(_denied)
    try:
        with pytest.raises(dg.DeepgramError) as exc:
            dg.transcribe_audio(b"webm-bytes", mime="audio/webm")
        assert "test-key-not-real" not in str(exc.value)
    finally:
        dg.set_transport(None)


def test_synthesize_speech_returns_audio_bytes(deepgram_env, fake_deepgram):
    from src.channels import deepgram as dg

    audio = dg.synthesize_speech("Are you in a safe location?")
    assert audio.startswith(b"ID3")
    assert fake_deepgram[0]["url"].startswith("https://api.deepgram.com/v1/speak")


def test_synthesize_blank_text_raises(deepgram_env, fake_deepgram):
    from src.channels import deepgram as dg

    with pytest.raises(dg.DeepgramError):
        dg.synthesize_speech("   ")
    assert fake_deepgram == []


def test_decode_user_audio_frame_ok():
    from src.channels import deepgram as dg

    raw = base64.b64encode(b"fake-opus-audio").decode()
    data, mime = dg.decode_user_audio({"audio": raw, "mime": "audio/webm;codecs=opus"})
    assert data == b"fake-opus-audio"
    assert mime == "audio/webm"


def test_decode_user_audio_frame_rejects_shape():
    from src.channels import deepgram as dg

    with pytest.raises(ValueError):
        dg.decode_user_audio({"audio": 123})
    with pytest.raises(ValueError):
        dg.decode_user_audio({"audio": "!!!not-base64!!!"})
    with pytest.raises(ValueError):
        dg.decode_user_audio({"audio": base64.b64encode(b"x").decode(), "mime": "video/mp4"})


def test_decode_user_audio_frame_rejects_oversize(monkeypatch):
    from src.channels import deepgram as dg

    monkeypatch.setenv("DEEPGRAM_MAX_AUDIO_BYTES", "4096")
    big = base64.b64encode(b"x" * 5000).decode()
    with pytest.raises(ValueError):
        dg.decode_user_audio({"audio": big, "mime": "audio/webm"})


def test_speech_stack_wires_deepgram_when_opted_in(deepgram_env, fake_deepgram):
    from src.channels.stt_tts import ServerSpeechStack

    s = ServerSpeechStack()
    assert s.server_stt_available is True
    assert s.playable_tts_available() is True
    assert s.transcribe_pcm(b"\x00\x01" * 8000) == "my brakes are grinding"
    assert s.synthesize_audio("hello") == b"ID3\x04fake-mp3-bytes"
    meta = s.synthesize_meta("hello")
    assert meta["provider"] == "deepgram"
    assert meta["playable"] is True
    assert meta["audio_ref"]
    caps = s.capabilities()
    assert caps["server_stt"] is True
    assert caps["server_tts"] is True


def test_speech_stack_transcribe_audio_helpers(deepgram_env, fake_deepgram):
    from src.channels.stt_tts import ServerSpeechStack

    s = ServerSpeechStack()
    out = s.transcribe_audio(b"webm-bytes", mime="audio/webm")
    assert out is not None and out["text"] == "my brakes are grinding"


def test_speech_stack_fails_closed_on_provider_error(deepgram_env):
    from src.channels import deepgram as dg
    from src.channels.stt_tts import ServerSpeechStack

    def _boom(url: str, body: bytes, headers: dict, timeout: float):
        raise dg.DeepgramError("network down")

    dg.set_transport(_boom)
    try:
        s = ServerSpeechStack()
        assert s.transcribe_pcm(b"\x00\x01" * 100) is None
        assert s.transcribe_audio(b"webm", mime="audio/webm") is None
        assert s.synthesize_audio("hello") is None
    finally:
        dg.set_transport(None)


def test_speech_stack_stays_pilot_without_opt_in(monkeypatch):
    from src.channels.stt_tts import ServerSpeechStack

    monkeypatch.delenv("DEEPGRAM_ENABLED", raising=False)
    monkeypatch.delenv("DEEPGRAM_API_KEY", raising=False)
    s = ServerSpeechStack()
    assert s.server_stt_available is False
    assert s.playable_tts_available() is False
    assert s.synthesize_audio("hello") is None
    assert s.capabilities()["server_tts"] is False


def test_server_voice_capabilities_helper(monkeypatch):
    from src.channels import stt_tts

    monkeypatch.delenv("DEEPGRAM_ENABLED", raising=False)
    monkeypatch.delenv("DEEPGRAM_API_KEY", raising=False)
    capabilities = stt_tts.server_voice_capabilities()
    assert capabilities["server_stt"] is False and capabilities["server_tts"] is False
    assert "audio/wav" in capabilities["accepted_audio_mime"] and "audio/mp4" not in capabilities["accepted_audio_mime"]


# ── WS integration (real socket, fake Deepgram transport) ───────────────────


@pytest.fixture
def audio_client(reset_ops_db):
    from fastapi.testclient import TestClient

    from scripts.seed_domains import build as build_auto
    from src.api.main import app
    from src.api.routes.interactions import _active

    build_auto("automotive_nhtsa")
    _active.clear()
    with TestClient(app) as client:
        yield client
    _active.clear()


def _drain_until(ws, stop_types: set[str], cap: int = 12) -> list[dict]:
    frames: list[dict] = []
    for _ in range(cap):
        try:
            msg = ws.receive_json()
        except Exception:
            break
        frames.append(msg)
        if msg.get("type") in stop_types:
            break
    return frames


def test_ws_ready_advertises_voice_off_by_default(audio_client, monkeypatch):
    monkeypatch.delenv("DEEPGRAM_ENABLED", raising=False)
    monkeypatch.delenv("DEEPGRAM_API_KEY", raising=False)
    r = audio_client.post("/api/interactions/start?channel=web_text")
    with audio_client.websocket_connect(r.json()["ws_url"]) as ws:
        ready = ws.receive_json()
        assert ready["type"] == "ready"
        assert ready["voice"]["server_stt"] is False and ready["voice"]["server_tts"] is False
        ws.send_json({"type": "hangup"})


def test_ws_user_audio_end_to_end(audio_client, deepgram_env, fake_deepgram):
    r = audio_client.post("/api/interactions/start?channel=web_text")
    iid = r.json()["interaction_id"]
    payload = base64.b64encode(b"\x1a\x45\xdf\xa3fake-webm-utterance").decode()
    with audio_client.websocket_connect(r.json()["ws_url"]) as ws:
        ready = ws.receive_json()
        assert ready["voice"]["server_stt"] is True and ready["voice"]["server_tts"] is True
        ws.send_json({
            "type": "user_audio",
            "audio": payload,
            "mime": "audio/webm;codecs=opus",
            "turn_id": "t-audio-1",
            "turn_seq": 1,
        })
        frames = _drain_until(ws, {"turn_result"})
    by_type = {}
    for f in frames:
        by_type.setdefault(f.get("type"), []).append(f)
    assert "heard_turn" in by_type, frames
    assert by_type["heard_turn"][0]["text"] == "my brakes are grinding"
    assert by_type["heard_turn"][0]["turn_id"] == "t-audio-1"
    assert "agent_turn" in by_type, frames
    assert "turn_result" in by_type, frames
    assert "agent_audio" in by_type, frames
    audio_frame = by_type["agent_audio"][0]
    assert audio_frame["mime"] == "audio/mpeg"
    assert base64.b64decode(audio_frame["audio"]).startswith(b"ID3")
    assert not [f for f in frames if f.get("type") == "error"], frames
    # The transcript flowed through the real turn pipeline into the record.
    detail = audio_client.get(f"/api/interactions/{iid}").json()
    texts = [t.get("text", "") for t in detail.get("turns", [])]
    assert any("my brakes are grinding" in t for t in texts)


def test_selected_hindi_locale_reaches_server_recognition_and_rejects_mid_report_switch(audio_client, deepgram_env, fake_deepgram):
    from urllib.parse import parse_qs, urlparse
    assert audio_client.post("/api/interactions/start?channel=web_text&locale=fr-FR").status_code == 422
    response = audio_client.post("/api/interactions/start?channel=web_text&locale=hi-IN")
    assert response.status_code == 200
    assert response.json()["locale"] == "hi-IN"
    assert response.json()["speech_support"]["reply_locale"] == "en-US"
    with audio_client.websocket_connect(response.json()["ws_url"]) as ws:
        ready = ws.receive_json()
        assert ready["locale"] == "hi-IN" and "hi-IN" in ready["voice"]["stt_locales"]
        ws.send_json({"type": "user_audio", "audio": base64.b64encode(b"fixture-audio").decode(), "mime": "audio/wav", "turn_id": "language-turn", "turn_seq": 1})
        frames = _drain_until(ws, {"turn_result"})
        assert any(f.get("type") == "heard_turn" for f in frames)
        assert parse_qs(urlparse(fake_deepgram[0]["url"]).query)["language"] == ["hi"]
        ws.send_json({"type": "user_audio", "audio": base64.b64encode(b"fixture-audio").decode(), "mime": "audio/wav", "locale": "en-US", "turn_id": "language-switch"})
        refused = _drain_until(ws, {"error"})[-1]
        assert refused["code"] == "bad_audio" and "selected language" in refused["detail"]
        ws.send_json({"type": "hangup"})


def test_authenticated_second_operator_takes_queued_report_with_context(audio_client, monkeypatch):
    from src.api.rbac import issue_session
    from src.data.warehouse import ops_con
    monkeypatch.setenv("FRONTLINE_OPEN_MODE", "0")
    monkeypatch.setenv("FRONTLINE_AUTH_REQUIRED", "1")
    monkeypatch.setenv("FRONTLINE_API_KEY", "voice-auth-test-key")
    def headers(actor, role):
        return {"X-API-Key": "voice-auth-test-key", "X-Frontline-Session": issue_session(actor, role, issuer_role="admin")["token"]}
    operator = headers("first-operator", "agent")
    specialist = headers("second-operator", "supervisor")
    other = headers("third-operator", "supervisor")
    response = audio_client.post("/api/interactions/start?channel=web_text", headers=operator)
    assert response.status_code == 200
    iid = response.json()["interaction_id"]
    with audio_client.websocket_connect(response.json()["ws_url"], headers=operator) as ws:
        assert ws.receive_json()["type"] == "ready"
        ws.send_json({"type": "user_turn", "text": "My vehicle makes a knocking sound.", "turn_id": "handoff-context", "turn_seq": 1})
        _drain_until(ws, {"turn_result"})
        queued = audio_client.post(f"/api/interactions/{iid}/handoff/accept", json={"force": True}, headers=operator)
        assert queued.status_code == 200 and queued.json()["accepted"] is True
        with ops_con() as con:
            assert con.execute("SELECT status FROM handoff_requests WHERE interaction_id=?", [iid]).fetchone()[0] == "pending"
        detail = audio_client.get(f"/api/interactions/{iid}", headers=specialist).json()
        assert any(t["speaker"] == "customer" and "knocking" in t["text"] for t in detail["turns"])
        assert audio_client.post(f"/api/interactions/{iid}/takeover", headers=operator).status_code == 403
        taken = audio_client.post(f"/api/interactions/{iid}/takeover", headers=specialist)
        assert taken.status_code == 200 and taken.json()["claimed_by"] == "second-operator"
        with ops_con() as con:
            status, actor = con.execute("SELECT status, claimed_by FROM handoff_requests WHERE interaction_id=?", [iid]).fetchone()
        assert status == "claimed" and actor == "second-operator"
        assert audio_client.post(f"/api/interactions/{iid}/takeover", headers=other).status_code == 409
        assert audio_client.post(f"/api/interactions/{iid}/release", headers=other).status_code == 403
        assert audio_client.post(f"/api/interactions/{iid}/release", headers=specialist).status_code == 200
        audio_client.post(f"/api/interactions/{iid}/end", headers=operator)


def test_ws_user_audio_without_opt_in_is_recoverable_error(audio_client, monkeypatch):
    monkeypatch.delenv("DEEPGRAM_ENABLED", raising=False)
    monkeypatch.delenv("DEEPGRAM_API_KEY", raising=False)
    r = audio_client.post("/api/interactions/start?channel=web_text")
    payload = base64.b64encode(b"fake-audio").decode()
    with audio_client.websocket_connect(r.json()["ws_url"]) as ws:
        assert ws.receive_json()["type"] == "ready"
        ws.send_json({"type": "user_audio", "audio": payload, "mime": "audio/webm"})
        err = ws.receive_json()
        assert err["type"] == "error"
        assert err["code"] == "server_stt_unavailable"
        assert err["recoverable"] is True
        ws.send_json({"type": "hangup"})


def test_ws_user_audio_bad_shape_is_recoverable_error(audio_client, deepgram_env, fake_deepgram):
    r = audio_client.post("/api/interactions/start?channel=web_text")
    with audio_client.websocket_connect(r.json()["ws_url"]) as ws:
        assert ws.receive_json()["type"] == "ready"
        ws.send_json({"type": "user_audio", "audio": "!!!not-base64!!!"})
        err = ws.receive_json()
        assert err["type"] == "error"
        assert err["code"] == "bad_audio"
        assert err["recoverable"] is True
        ws.send_json({"type": "hangup"})
