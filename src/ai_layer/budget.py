"""Cross-process, lifetime Meta spend reservations. Never refund uncertain calls.

Published rates checked 2026-10-28: https://dev.meta.ai/docs/pricing-rate-limits
Text input is bounded conservatively by UTF-8 request bytes + 4096 tokens;
output includes the request's hard completion cap. No search/tools or videos.
This ledger covers this client, not unrelated use of the same Meta account.
"""
from __future__ import annotations

import json
import math
import os
import sqlite3
from pathlib import Path

RATES = {**{f"muse-spark-{v}": (1.25, 4.25) for v in ("1.1", "1.2", "1.3")},
         **{f"muse-spark-{v}-contributor": (0.10, 0.20) for v in ("1.2", "1.3")}}


def path() -> Path:
    return Path(os.getenv("META_BUDGET_PATH") or "~/.cache/skewai/meta_budget.sqlite").expanduser()


def limit_micros() -> int:
    value = float(os.getenv("META_BUDGET_USD", "30"))
    if not math.isfinite(value) or value <= 0:
        raise ValueError("invalid budget")
    return int(min(value, 30.0) * 1_000_000)


def connect():
    p = path()
    p.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(p, timeout=10)
    os.chmod(p, 0o600)
    con.execute("CREATE TABLE IF NOT EXISTS reservations (id INTEGER PRIMARY KEY, model TEXT, micros INTEGER, usage_json TEXT, live_success INTEGER DEFAULT 0, created_at TEXT DEFAULT CURRENT_TIMESTAMP)")
    return con


def bound(payload: dict) -> int:
    model = payload.get("model", "")
    if payload.get("tools") or payload.get("background"):
        raise ValueError("unpriced request")
    if model in RATES:
        # Text and still-image chat only. Long media requires a separate bound.
        raw = json.dumps(payload, ensure_ascii=False).encode()
        if b"video_url" in raw or b"audio" in raw or b"data:video" in raw:
            raise ValueError("unpriced media")
        cap = payload.get("max_completion_tokens", payload.get("max_tokens"))
        if not isinstance(cap, int) or cap < 1 or cap > 10000:
            raise ValueError("missing completion cap")
        inp, out = RATES[model]
        return math.ceil((len(raw) + 4096) * inp + cap * out)
    if model == "muse-image-1.0":
        n = payload.get("n", 1)
        if not isinstance(n, int) or not 1 <= n <= 4:
            raise ValueError("image count")
        return n * 10000
    if model == "sam-3.1":
        raw = json.dumps(payload)
        if "video" in raw:
            raise ValueError("unpriced video")
        count = raw.count('"input_image"')
        if not 1 <= count <= 4:
            raise ValueError("image count")
        return count * 2500
    raise ValueError("unpriced model")


def reserve(payload: dict) -> int:
    from src.ai_layer.meta_client import MetaError
    try:
        cost = bound(payload)
    except (ValueError, TypeError):
        raise MetaError("budget_unpriced_model") from None
    try:
        with connect() as con:
            con.execute("BEGIN IMMEDIATE")
            used = con.execute("SELECT COALESCE(SUM(micros),0) FROM reservations").fetchone()[0]
            if used + cost > limit_micros():
                raise MetaError("budget_exceeded")
            row = con.execute("INSERT INTO reservations(model,micros) VALUES (?,?)", [payload["model"], cost])
            return int(row.lastrowid)
    except MetaError:
        raise
    except Exception:
        raise MetaError("budget_unavailable") from None


def complete(reservation: int, body: bytes, *, live: bool) -> None:
    try:
        data = json.loads(body)
        usage = data.get("usage", {})
        with connect() as con:
            con.execute("UPDATE reservations SET usage_json=?, live_success=? WHERE id=?",
                        [json.dumps(usage), int(live), reservation])
    except Exception:
        pass  # reservation remains charged at its conservative upper bound


def status() -> dict:
    with connect() as con:
        used, successes = con.execute("SELECT COALESCE(SUM(micros),0), COALESCE(SUM(live_success),0) FROM reservations").fetchone()
        rows = con.execute("SELECT model, usage_json FROM reservations WHERE live_success=1").fetchall()
    observed = 0.0
    unknown = 0
    for model, raw in rows:
        usage = json.loads(raw or "{}")
        if model in RATES and isinstance(usage.get("prompt_tokens"), int) and isinstance(usage.get("completion_tokens"), int):
            i, o = RATES[model]
            observed += (usage["prompt_tokens"] * i + usage["completion_tokens"] * o) / 1e6
        else:
            unknown += 1
    return {"limit_usd": limit_micros() / 1e6, "reserved_upper_bound_usd": used / 1e6,
            "observed_token_cost_usd": observed, "unmetered_successes": unknown,
            "live_successful_requests": successes, "pricing_checked": "2026-10-28",
            "scope": "this client; excludes unrelated account activity; reservations include failed attempts"}
