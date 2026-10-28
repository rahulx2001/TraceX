"""Environment-driven configuration for the optional Meta AI layer.  [AI-LAYER]

Every endpoint, model id and limit is env-configurable. Defaults follow the
public Meta Model API docs at https://dev.meta.ai/docs (read 2026-10-21) but
have NOT been exercised against the live API from this repo: no key exists in
this project. See HACKATHON.md "What is unverified".

Env vars (all optional):

  META_API_KEY / MODEL_API_KEY   bearer token. Absent -> mode "deterministic".
  FRONTLINE_AI_LAYER             "auto" (default) | "off". "off" forces the
                                 deterministic path even when a key is set.
  BASETEN_API_KEY                Bearer key for Baseten-hosted Muse Spark Open
                                 (OpenAI-compatible). Never logged, never committed.
  META_BACKEND                   "auto" (default) | "meta" | "baseten". "auto"
                                 prefers Baseten when BASETEN_API_KEY is set.
  META_API_BASE                  default https://api.meta.ai/v1 (Meta backend only;
                                 the Baseten base URL and model are pinned)
  META_MODEL_TEXT                default muse-spark-1.3   (chat completions)
  META_MODEL_VISION              default muse-spark-1.3   (image understanding)
  META_MODEL_SAM                 default sam-3.1          (Responses API)
  META_MODEL_IMAGE               default muse-image-1.0   (images/generations)
  META_CHAT_PATH                 default /chat/completions
  META_SAM_ENDPOINT              default <META_API_BASE>/responses
  META_IMAGE_ENDPOINT            default <META_API_BASE>/images/generations
  META_ALLOWED_HOSTS             extra comma-separated hosts that may receive
                                 the key (e.g. a self-hosted Muse Spark Open /
                                 Muse Glimmer vLLM gateway). api.meta.ai is
                                 always allowed.
  META_TIMEOUT_S                 default 8 (per HTTP attempt)
  META_INTAKE_TIMEOUT_S          default 4 (live-call turn budget)
  META_RETRIES                   default 1 (extra attempts on 429/5xx/network)
  META_MIN_CONFIDENCE            default 0.7 (AI slot/category floor)
  META_DAILY_CALL_CAP            default 300 (cross-run hard stop; retries count)
  META_CAP_PATH                  default ~/.cache/skewai/meta_calls.json
                                 (shared counter, so throwaway eval DBs cannot
                                 reset the daily cap)
  AI_EVIDENCE_MAX_BYTES          default 8 MiB
  AI_EVIDENCE_DIR                default <repo>/data/ai_evidence
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

DEFAULT_API_BASE = "https://api.meta.ai/v1"
OFFICIAL_HOST = "api.meta.ai"
DEFAULT_MODEL_TEXT = "muse-spark-1.3"
DEFAULT_MODEL_VISION = "muse-spark-1.3"
DEFAULT_MODEL_SAM = "sam-3.1"
DEFAULT_MODEL_IMAGE = "muse-image-1.0"

# Baseten-hosted Muse Spark Open (OpenAI-compatible chat completions).
# Pinned: hackathon keys only work with this host and model, so there is no
# env override for either. Responses API (SAM) and images/generations do not
# exist here; those entry points fail fast on this backend.
BASETEN_API_BASE = "https://inference.baseten.co/v1"
BASETEN_HOST = "inference.baseten.co"
BASETEN_MODEL = "meta-models/muse-spark-open-1026"


def _env(name: str, default: str = "") -> str:
    return (os.getenv(name) or default).strip()


def _env_float(name: str, default: float) -> float:
    try:
        return float(_env(name, str(default)))
    except ValueError:
        return default


def _env_int(name: str, default: int) -> int:
    try:
        return int(_env(name, str(default)))
    except ValueError:
        return default


def meta_api_key() -> str:
    """Bearer token. ``META_API_KEY`` wins; ``MODEL_API_KEY`` is the name used
    by the official docs and is accepted as an alias. Never logged."""
    return _env("META_API_KEY") or _env("MODEL_API_KEY")


def baseten_api_key() -> str:
    """Bearer key for the Baseten backend. Never logged."""
    return _env("BASETEN_API_KEY")


def backend() -> str:
    """Active backend: ``"baseten"``, ``"meta"``, or ``"none"`` (no key).

    ``META_BACKEND=baseten|meta`` pins one (missing key -> ``"none"``, fail
    closed). ``auto`` prefers Baseten when its key is set, else Meta.
    """
    want = _env("META_BACKEND", "auto").lower()
    has_baseten = bool(baseten_api_key())
    has_meta = bool(meta_api_key())
    if want == "baseten":
        return "baseten" if has_baseten else "none"
    if want == "meta":
        return "meta" if has_meta else "none"
    if has_baseten:
        return "baseten"
    if has_meta:
        return "meta"
    return "none"


def active_api_key() -> str:
    """Key for the active backend (empty when none). Never logged."""
    which = backend()
    if which == "baseten":
        return baseten_api_key()
    if which == "meta":
        return meta_api_key()
    return ""


def layer_switch() -> str:
    raw = _env("FRONTLINE_AI_LAYER", "auto").lower()
    if raw in {"0", "off", "false", "no", "deterministic"}:
        return "off"
    return "auto"


def meta_enabled() -> bool:
    """True only when a backend key is configured and the layer is not switched off."""
    return layer_switch() != "off" and backend() != "none"


def ai_mode() -> str:
    return "enhanced" if meta_enabled() else "deterministic"


def api_base() -> str:
    if backend() == "baseten":
        return BASETEN_API_BASE
    return _env("META_API_BASE", DEFAULT_API_BASE).rstrip("/")


def model_text() -> str:
    if backend() == "baseten":
        return BASETEN_MODEL
    return _env("META_MODEL_TEXT", DEFAULT_MODEL_TEXT)


def model_vision() -> str:
    if backend() == "baseten":
        return BASETEN_MODEL
    return _env("META_MODEL_VISION", DEFAULT_MODEL_VISION)


def max_tokens() -> int:
    """Completion budget. Baseten default is higher: the reasoning model spends
    tokens thinking before it answers. ``META_MAX_TOKENS`` overrides either."""
    default = 8000 if backend() == "baseten" else 2000
    try:
        return max(256, min(32000, int(_env("META_MAX_TOKENS", str(default)))))
    except ValueError:
        return default


def model_sam() -> str:
    return _env("META_MODEL_SAM", DEFAULT_MODEL_SAM)


def model_image() -> str:
    return _env("META_MODEL_IMAGE", DEFAULT_MODEL_IMAGE)


def chat_url() -> str:
    path = _env("META_CHAT_PATH", "/chat/completions")
    if not path.startswith("/"):
        path = "/" + path
    return api_base() + path


def sam_url() -> str:
    return _env("META_SAM_ENDPOINT") or (api_base() + "/responses")


def image_url() -> str:
    return _env("META_IMAGE_ENDPOINT") or (api_base() + "/images/generations")


def allowed_hosts() -> set[str]:
    hosts = {OFFICIAL_HOST}
    if baseten_api_key():
        hosts.add(BASETEN_HOST)
    for raw in _env("META_ALLOWED_HOSTS").split(","):
        host = raw.strip().lower()
        if host:
            hosts.add(host)
    return hosts


def timeout_s() -> float:
    return max(0.5, min(60.0, _env_float("META_TIMEOUT_S", 8.0)))


def intake_timeout_s() -> float:
    return max(0.5, min(30.0, _env_float("META_INTAKE_TIMEOUT_S", 20.0)))


def retries() -> int:
    return max(0, min(3, _env_int("META_RETRIES", 1)))


def min_confidence() -> float:
    return max(0.0, min(1.0, _env_float("META_MIN_CONFIDENCE", 0.7)))


def daily_call_cap() -> int:
    return max(1, _env_int("META_DAILY_CALL_CAP", 300))


def evidence_max_bytes() -> int:
    return max(1024, _env_int("AI_EVIDENCE_MAX_BYTES", 8 * 1024 * 1024))


def _host(url: str) -> str:
    return (urlparse(url).hostname or "").lower()


def _live_verified(current_host: str) -> bool:
    """True only when a recorded live smoke succeeded on this same host."""
    from src.ai_layer.live_proof import verified_features
    return current_host == _host(api_base()) and any(verified_features().values())


def ai_status() -> dict[str, Any]:
    """Public, secret-free status for GET /api/ai/status and the UI badge."""
    enabled = meta_enabled()
    from src.ai_layer.live_proof import verified_features
    base_host = _host(api_base())
    return {
        "mode": ai_mode(),
        "provider": backend() if enabled else None,
        "key_configured": bool(active_api_key()),
        "layer_switch": layer_switch(),
        "api_host": base_host,
        "api_host_allowed": base_host in allowed_hosts(),
        "models": {
            "text": model_text(),
            "vision": model_vision(),
            "segmentation": model_sam(),
            "image": model_image(),
        },
        "features": {
            "enhanced_intake": enabled,
            "hindi_hinglish_normalisation": enabled,
            "grounded_brief": enabled,
            "severity_sentiment_raise_only": enabled,
            "photo_evidence_upload": True,
            "photo_evidence_analysis": enabled,
        },
        "fallback": "deterministic regex/gazetteer/rules path (always on)",
        "verified_against_live_api": _live_verified(base_host),
        "verified_features": verified_features(),
        "budget_limit_usd": 30,
    }


__all__ = [
    "active_api_key",
    "ai_mode",
    "ai_status",
    "allowed_hosts",
    "api_base",
    "backend",
    "baseten_api_key",
    "chat_url",
    "daily_call_cap",
    "evidence_max_bytes",
    "image_url",
    "intake_timeout_s",
    "max_tokens",
    "meta_api_key",
    "meta_enabled",
    "min_confidence",
    "model_image",
    "model_sam",
    "model_text",
    "model_vision",
    "retries",
    "sam_url",
    "timeout_s",
]
