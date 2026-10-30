"""Deepgram speech provider — server STT (Nova) + TTS (Aura).

The browser Call Widget does STT/TTS locally (Chrome-only Web Speech). This
module gives the server its own ears and voice so any browser with a
microphone can hold the call; the orchestrator stays the brain — Deepgram
only transcribes customer audio and speaks agent text.

Hermetic by default: the provider is available only when ``DEEPGRAM_ENABLED=1``
**and** ``DEEPGRAM_API_KEY`` is set (mirrors the ``FRONTLINE_LLM_ENABLED``
gate in ``src/ai/``). Without both, ``ServerSpeechStack`` keeps its offline
pilot behavior and claims nothing.

No new dependency: prerecorded REST (``/v1/listen``, ``/v1/speak``) over
urllib with an injectable transport for tests — the same pattern as
``src.ai_layer.meta_client``. The key is sent only to the fixed official
host; there is no base-URL override.

Wire shapes (api.deepgram.com):
* STT: ``POST /v1/listen?model=<m>&smart_format=true`` with raw audio bytes
  and ``Authorization: Token <key>``. Transcript at
  ``results.channels[0].alternatives[0]``.
* TTS: ``POST /v1/speak?model=<m>&encoding=mp3`` with JSON ``{"text": ...}``.
  The response body is playable MP3 bytes.
"""

from __future__ import annotations

import base64
import binascii
import json
import os
import re
import struct
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from typing import Any, Callable

DEEPGRAM_HOST = "https://api.deepgram.com"
DEFAULT_STT_MODEL = "nova-3"
DEFAULT_TTS_MODEL = "aura-2-thalia-en"

_MODEL_RE = re.compile(r"^[A-Za-z0-9._-]{1,64}$")

# Client audio containers accepted on the wire. The base type (before any
# ";codecs=..." suffix) must be one of these; anything else fails closed.
_AUDIO_MIME_ALLOWLIST = frozenset({
    "audio/webm",
    "audio/wav",
    "audio/x-wav",
    "audio/mpeg",
    "audio/mp3",
    "audio/ogg",
    "audio/opus",
    "audio/flac",
})


class DeepgramError(Exception):
    """Any reason Deepgram output must not be used. ``reason`` is log-safe."""

    def __init__(self, reason: str) -> None:
        super().__init__(reason)
        self.reason = reason


class DeepgramNoSpeech(DeepgramError):
    """The provider answered but heard no speech (silence, not a failure)."""


def _env_bool(name: str, default: bool = False) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def deepgram_enabled() -> bool:
    return _env_bool("DEEPGRAM_ENABLED", False)


def deepgram_api_key() -> str:
    return (os.getenv("DEEPGRAM_API_KEY") or "").strip()


def deepgram_available() -> bool:
    """True only when explicitly enabled AND a key is configured."""
    return bool(deepgram_enabled() and deepgram_api_key())


def stt_model() -> str:
    raw = (os.getenv("DEEPGRAM_STT_MODEL") or "").strip() or DEFAULT_STT_MODEL
    return raw if _MODEL_RE.match(raw) else DEFAULT_STT_MODEL


def tts_model() -> str:
    raw = (os.getenv("DEEPGRAM_TTS_MODEL") or "").strip() or DEFAULT_TTS_MODEL
    return raw if _MODEL_RE.match(raw) else DEFAULT_TTS_MODEL


def request_timeout_s() -> float:
    try:
        return min(60.0, max(3.0, float(os.getenv("DEEPGRAM_TIMEOUT_S", "20") or 20)))
    except (TypeError, ValueError):
        return 20.0


def max_audio_bytes() -> int:
    try:
        return min(20_000_000, max(4096, int(os.getenv("DEEPGRAM_MAX_AUDIO_BYTES", "2000000") or 2000000)))
    except (TypeError, ValueError):
        return 2_000_000


def max_tts_chars() -> int:
    try:
        return min(20_000, max(280, int(os.getenv("DEEPGRAM_MAX_TTS_CHARS", "5000") or 5000)))
    except (TypeError, ValueError):
        return 5000


@dataclass
class HttpResponse:
    status: int
    body: bytes
    content_type: str = ""


Transport = Callable[[str, bytes, dict[str, str], float], HttpResponse]


class _NoRedirectHandler(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):  # noqa: ANN001,ANN202
        # Never follow redirects on requests carrying the API key.
        return None


_opener = urllib.request.build_opener(_NoRedirectHandler)


def _urllib_transport(url: str, body: bytes, headers: dict[str, str], timeout: float) -> HttpResponse:
    req = urllib.request.Request(url, data=body, headers=headers, method="POST")
    try:
        with _opener.open(req, timeout=timeout) as resp:  # noqa: S310 - fixed official host
            return HttpResponse(
                status=int(getattr(resp, "status", 200) or 200),
                body=resp.read(),
                content_type=str(resp.headers.get("Content-Type") or ""),
            )
    except urllib.error.HTTPError as e:
        try:
            payload = e.read()
        except Exception:
            payload = b""
        return HttpResponse(status=int(e.code), body=payload, content_type="")


_transport: Transport = _urllib_transport


def set_transport(fn: Transport | None) -> None:
    """Swap the HTTP transport (tests inject a fake; ``None`` restores urllib)."""
    global _transport
    _transport = fn or _urllib_transport


def _post(path: str, body: bytes, content_type: str) -> HttpResponse:
    """POST to the fixed official host. Bounded retries on 429/5xx/network."""
    key = deepgram_api_key()
    if not key:
        raise DeepgramError("deepgram key not configured")
    url = DEEPGRAM_HOST + path
    headers = {"Authorization": f"Token {key}", "Content-Type": content_type}
    timeout = request_timeout_s()
    last_error = "request failed"
    for attempt in range(2):
        try:
            resp = _transport(url, body, headers, timeout)
        except DeepgramError:
            raise
        except Exception as exc:  # network error — one retry, then fail
            last_error = f"{type(exc).__name__}"
            if attempt == 0:
                time.sleep(0.4)
                continue
            raise DeepgramError(f"deepgram unreachable ({last_error})") from None
        if resp.status == 200:
            return resp
        if resp.status in (429, 500, 502, 503, 504) and attempt == 0:
            time.sleep(0.4)
            continue
        raise DeepgramError(_status_reason(resp.status, resp.body))
    raise DeepgramError(f"deepgram unreachable ({last_error})")


def _status_reason(status: int, body: bytes) -> str:
    """Log-safe one-liner: status plus the provider's err_msg, never the key."""
    detail = ""
    try:
        payload = json.loads((body or b"")[:2000].decode("utf-8", "replace"))
        if isinstance(payload, dict):
            detail = str(payload.get("err_msg") or payload.get("error") or "")
    except Exception:
        detail = ""
    detail = re.sub(r"\s+", " ", detail).strip()[:160]
    return f"deepgram http {status}" + (f": {detail}" if detail else "")


def normalize_audio_mime(mime: str | None) -> str:
    """Base container type, allowlisted. Raises ValueError when rejected."""
    base = (mime or "audio/webm").split(";", 1)[0].strip().lower() or "audio/webm"
    if base not in _AUDIO_MIME_ALLOWLIST:
        raise ValueError(f"unsupported audio type: {base}")
    return base


def decode_user_audio(msg: dict[str, Any]) -> tuple[bytes, str]:
    """Validate a ``user_audio`` WS frame. Returns (audio bytes, mime).

    Raises ValueError with a client-safe message on any shape/size failure.
    Never returns partial or undecoded input.
    """
    raw = (msg or {}).get("audio")
    if not isinstance(raw, str) or not raw.strip():
        raise ValueError("audio must be a base64 string")
    cap = max_audio_bytes()
    if len(raw) > cap * 2:
        raise ValueError("audio frame too large")
    try:
        data = base64.b64decode(raw.strip(), validate=True)
    except (binascii.Error, ValueError):
        raise ValueError("audio is not valid base64") from None
    if not data:
        raise ValueError("audio is empty")
    if len(data) > cap:
        raise ValueError("audio frame too large")
    mime = normalize_audio_mime((msg or {}).get("mime"))
    return data, mime


def transcription_language(locale: str | None) -> str:
    """Validated UI locales map to the provider's language codes, never a query fragment."""
    values = {None: "en", "": "en", "en-US": "en", "en-IN": "en", "hi-IN": "hi"}
    if locale not in values:
        raise DeepgramError("unsupported speech language")
    return values[locale]


def transcribe_audio(data: bytes, *, mime: str = "audio/webm", locale: str | None = None) -> dict[str, Any]:
    """Transcribe one utterance. Returns {"text", "confidence"}.

    Raises DeepgramNoSpeech when the provider heard silence, DeepgramError
    on any other failure. Never invents text.
    """
    if not data:
        raise DeepgramError("no audio to transcribe")
    content_type = normalize_audio_mime(mime)
    query = urllib.parse.urlencode({"model": stt_model(), "smart_format": "true", "language": transcription_language(locale)})
    resp = _post(f"/v1/listen?{query}", bytes(data), content_type)
    try:
        payload = json.loads((resp.body or b"").decode("utf-8", "replace"))
    except Exception:
        raise DeepgramError("deepgram returned invalid JSON") from None
    try:
        channels = (payload.get("results") or {}).get("channels") or []
        alternatives = (channels[0].get("alternatives") or []) if channels else []
        best = alternatives[0] if alternatives else {}
        text = str(best.get("transcript") or "").strip()
        conf = best.get("confidence")
        confidence = float(conf) if conf is not None else None
    except (AttributeError, IndexError, TypeError, ValueError):
        raise DeepgramError("deepgram returned an unexpected shape") from None
    if not text:
        raise DeepgramNoSpeech("no speech detected")
    return {"text": text, "confidence": confidence}


def synthesize_speech(text: str) -> bytes:
    """Speak agent text. Returns playable MP3 bytes. Raises DeepgramError."""
    clean = (text or "").strip()
    if not clean:
        raise DeepgramError("no text to speak")
    if len(clean) > max_tts_chars():
        raise DeepgramError("text exceeds TTS length cap")
    query = urllib.parse.urlencode({"model": tts_model(), "encoding": "mp3"})
    body = json.dumps({"text": clean}).encode("utf-8")
    resp = _post(f"/v1/speak?{query}", body, "application/json")
    ctype = (resp.content_type or "").split(";", 1)[0].strip().lower()
    if not ctype.startswith("audio/"):
        raise DeepgramError(_status_reason(resp.status, resp.body))
    if not resp.body:
        raise DeepgramError("deepgram returned empty audio")
    return bytes(resp.body)


def pcm16k_mono_to_wav(pcm: bytes) -> bytes:
    """Wrap 16-bit mono 16kHz PCM in a minimal WAV header for /v1/listen."""
    data = bytes(pcm or b"")
    header = struct.pack(
        "<4sI4s4sIHHIIHH4sI",
        b"RIFF", 36 + len(data), b"WAVE", b"fmt ", 16,
        1, 1, 16000, 32000, 2, 16, b"data", len(data),
    )
    return header + data
