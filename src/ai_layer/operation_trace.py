"""Per-request metadata observer. Never stores prompts, credentials or reasoning."""
from __future__ import annotations

from contextlib import contextmanager
from contextvars import ContextVar
from datetime import datetime, timezone
import hashlib
import json
import time
from uuid import uuid4

_capture = ContextVar("meta_operation_capture", default=None)


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def stamp():
    return datetime.now(timezone.utc).isoformat()


@contextmanager
def capture(callback):
    token = _capture.set({"callback": callback, "last": None})
    try:
        yield
    finally:
        _capture.reset(token)


def start(payload, host, reservation, *, live):
    context = _capture.get()
    if context is None:
        return None
    from src.ai_layer.budget import bound
    event = {"attempt_id": str(uuid4()), "reservation_id": reservation, "model": payload.get("model"),
             "host": host, "started_at": stamp(), "status": "reserved", "live_transport": live,
             "request_sha256": digest(payload), "prompt_sha256": digest(payload.get("messages", [])),
             "schema_sha256": digest(payload.get("response_format", {})), "validation": "pending",
             "reserved_upper_bound_usd": bound(payload)/1e6, "observed_token_cost_estimate_usd": None,
             "actual_billed_cost_usd": None, "pricing_basis": "configured token rates; estimate, not provider invoice"}
    context["last"] = event
    context["callback"](dict(event))  # Persist before outbound transport; may stop an expired run.
    return event, time.monotonic()


def finish(handle, *, status, http_status=None, body=None):
    if handle is None:
        return
    event, started = handle
    event.update(status=status, http_status=http_status, finished_at=stamp(), elapsed_ms=round((time.monotonic()-started)*1000))
    if body:
        try:
            usage = json.loads(body).get("usage") or {}
            for key in ("prompt_tokens", "completion_tokens"):
                if type(usage.get(key)) is int and usage[key] >= 0:
                    event[key] = usage[key]
            from src.ai_layer.budget import RATES
            if all(k in event for k in ("prompt_tokens", "completion_tokens")) and event["model"] in RATES:
                inp, out = RATES[event["model"]]
                event["observed_token_cost_estimate_usd"] = (event["prompt_tokens"]*inp + event["completion_tokens"]*out)/1e6
        except (TypeError, ValueError):
            pass
    _capture.get()["callback"](dict(event))


def validated(schema_name, schema, reason=None):
    context = _capture.get()
    if context is None or context["last"] is None:
        return
    event = context["last"]
    event.update(schema_name=schema_name, logical_schema_sha256=digest(schema),
                 validation="rejected" if reason else "accepted", validation_reason=reason)
    context["callback"](dict(event))


def summary(operations, *, elapsed_ms=None, model_calls=0, fallback=None, stage_events=(), finished_at=None):
    stages = {}
    events = list(stage_events)
    for index, event in enumerate(events):
        end = events[index+1]["at"] if index+1 < len(events) else finished_at
        if end:
            stages[event["stage"]] = stages.get(event["stage"], 0) + max(0, round((datetime.fromisoformat(end)-datetime.fromisoformat(event["at"])).total_seconds()*1000))
    measured = [op["observed_token_cost_estimate_usd"] for op in operations if op.get("observed_token_cost_estimate_usd") is not None]
    return {"transport_attempts": len(operations), "successful_responses": sum(op.get("status") == "response_received" for op in operations),
            "schema_rejections": sum(op.get("validation") == "rejected" for op in operations),
            "reserved_upper_bound_usd": sum(op.get("reserved_upper_bound_usd", 0) for op in operations),
            "observed_token_cost_estimate_usd": sum(measured) if measured else (0 if model_calls == 0 else None),
            "actual_billed_cost_usd": None, "unmetered_attempts": len(operations)-len(measured),
            "instrumentation": "per_transport_attempt" if operations else "no_model_call" if model_calls == 0 else "unavailable",
            "stage_latency_ms": stages, "total_latency_ms": elapsed_ms, "fallback": fallback,
            "note": "Reservations include failed attempts. Token-rate estimates are not billed cost; missing measurements remain unknown."}
