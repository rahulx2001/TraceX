"""Held-out protection for the REAL complaint eval.  [REAL-DATA]

Every real run hashes the code that can change a result: the deterministic
Hindi lexicon, the Meta prompts/rules, the intake/triage agents, the domain
pack, the PII redactor, and the eval summariser.  Model ids and limits are
hashed too.  The API key is never hashed or written.

If the hash changes after a prior run, the runner refuses to score unless the
operator passes an explicit approval reason.  An approved change keeps every
older run directory and marks the set ``held_out=false`` for all later runs.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from eval.real_hindi.common import ROOT, sha256_bytes, sha256_file, utc_now
from scripts.real_hindi_collect import DataError, write_json_atomic

#: Relative paths hashed into the config fingerprint.  This is a focused
#: dependency set, not a full lockfile; unknown files are listed in the report.
CONFIG_FILES = (
    "src/ai_layer/config.py",
    "src/ai_layer/hindi_safety.py",
    "src/ai_layer/intake_enhancer.py",
    "src/ai_layer/severity.py",
    "src/ai_layer/meta_client.py",
    "src/ai_layer/language.py",
    "src/security/pii.py",
    "src/agents/base.py",
    "src/agents/intake.py",
    "src/agents/triage.py",
    "src/domains/loader.py",
    "domains/automotive_nhtsa/gazetteers/categories.csv",
    "domains/automotive_nhtsa/models/severity_rules.json",
    "domains/automotive_nhtsa/pack.yaml",
    "domains/automotive_nhtsa/taxonomy.yaml",
    "eval/enhanced/run_eval_modes.py",
    "eval/hindi_fresh/run_hindi_eval.py",
    "eval/real_hindi/labels.py",
    "eval/real_hindi/run_eval.py",
)


class ConfigChanged(RuntimeError):
    """A held-out configuration changed without explicit approval."""


def model_settings() -> dict[str, Any]:
    """Model ids/limits that affect a result.  Never includes the API key."""
    from src.ai_layer import config

    return {
        "api_base": config.api_base(),
        "chat_url": config.chat_url(),
        "model_text": config.model_text(),
        "model_vision": config.model_vision(),
        "model_sam": config.model_sam(),
        "model_image": config.model_image(),
        "layer_switch": config.layer_switch(),
        "timeout_s": config.timeout_s(),
        "intake_timeout_s": config.intake_timeout_s(),
        "retries": config.retries(),
        "min_confidence": config.min_confidence(),
        "daily_call_cap": config.daily_call_cap(),
    }


def config_manifest(root: Path = ROOT) -> dict[str, Any]:
    files: dict[str, str] = {}
    missing: list[str] = []
    for rel in CONFIG_FILES:
        path = Path(root) / rel
        if not path.is_file():
            missing.append(rel)
            continue
        files[rel] = sha256_file(path)
    if missing:
        raise DataError(f"configuration fingerprint is missing source file(s): {', '.join(missing)}")
    settings = model_settings()
    payload = json.dumps({"files": files, "settings": settings}, sort_keys=True, separators=(",", ":"))
    return {"hash": sha256_bytes(payload.encode("utf-8")), "files": files, "settings": settings}


def load_state(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as e:
        raise DataError(f"cannot read eval state {path}: {type(e).__name__}") from e
    if not isinstance(value, dict):
        raise DataError(f"eval state {path} is not a JSON object")
    return value


def guard_config(state: dict[str, Any] | None, config_hash: str,
                 approve_reason: str | None) -> dict[str, Any]:
    """Decide whether this config may be scored, without writing anything."""
    old_hash = (state or {}).get("config_hash")
    if not old_hash:
        return {"first_run": True, "held_out": True, "approval": None, "previous_hash": None}
    if old_hash == config_hash:
        return {"first_run": False, "held_out": bool((state or {}).get("held_out", True)),
                "approval": None, "previous_hash": None}
    reason = " ".join(str(approve_reason or "").split())
    if not reason:
        raise ConfigChanged(
            f"configuration changed since the last real run (old {old_hash[:16]}..., new {config_hash[:16]}...). "
            "The set is held-out, so scoring is refused. If you changed the lexicon, prompts, rules or eval "
            "sources after seeing results, rerun with --approve-change \"what changed and why\". "
            "That keeps prior runs and marks the set no longer held-out."
        )
    return {
        "first_run": False,
        "held_out": False,
        "approval": {
            "at": utc_now(),
            "old_hash": old_hash,
            "new_hash": config_hash,
            "reason": reason[:500],
        },
        "previous_hash": old_hash,
    }


def save_state(path: Path, *, config_hash: str, held_out: bool, approval: dict[str, Any] | None,
               run_id: str, labels_sha256: str) -> dict[str, Any]:
    existing = load_state(path) or {}
    approvals = list(existing.get("approvals") or [])
    if approval:
        entry = dict(approval)
        entry["run_id"] = run_id
        if entry not in approvals:
            approvals.append(entry)
    state = {
        "schema": 1,
        "config_hash": config_hash,
        "held_out": bool(held_out),
        "first_run_at": existing.get("first_run_at") or utc_now(),
        "updated_at": utc_now(),
        "last_run_id": run_id,
        "last_labels_sha256": labels_sha256,
        "approvals": approvals,
    }
    write_json_atomic(path, state)
    return state


def load_run_docs(out_dir: Path) -> list[dict[str, Any]]:
    runs_dir = out_dir.expanduser().resolve() / "runs"
    if not runs_dir.is_dir():
        return []
    docs: list[dict[str, Any]] = []
    for path in sorted(runs_dir.glob("*/run.json")):
        try:
            value = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError) as e:
            raise DataError(f"cannot read run file {path}: {type(e).__name__}") from e
        if not isinstance(value, dict) or not value.get("run_id"):
            raise DataError(f"run file {path} is not a valid run summary")
        for key in ("generated_at", "dataset", "labels", "config", "modes"):
            if key not in value:
                raise DataError(f"run file {path} is missing {key}")
        docs.append(value)
    docs.sort(key=lambda d: str(d.get("run_id") or ""))
    return docs


def state_from_runs(runs: list[dict[str, Any]]) -> dict[str, Any]:
    latest = runs[-1]
    approvals: list[dict[str, Any]] = []
    for run in runs:
        approval = (run.get("config") or {}).get("approval")
        if approval:
            approvals.append(approval)
    config = latest.get("config") or {}
    labels = latest.get("labels") or {}
    return {
        "schema": 1,
        "config_hash": config.get("hash"),
        "held_out": bool(config.get("held_out", True)),
        "first_run_at": runs[0].get("generated_at"),
        "updated_at": latest.get("generated_at"),
        "last_run_id": latest.get("run_id"),
        "last_labels_sha256": labels.get("sha256"),
        "approvals": approvals,
        "recovered_from_runs": True,
    }


def recover_state(state_path: Path, out_dir: Path) -> tuple[dict[str, Any] | None, bool]:
    """Use run history if the local state file is missing or behind."""
    state = load_state(state_path)
    runs = load_run_docs(out_dir)
    if not runs:
        return state, False
    latest = runs[-1]
    if state and state.get("last_run_id") == latest.get("run_id"):
        return state, False
    recovered = state_from_runs(runs)
    if state:
        approvals = list(recovered.get("approvals") or [])
        for approval in state.get("approvals") or []:
            if approval not in approvals:
                approvals.append(approval)
        recovered["approvals"] = approvals
        # If either the state or run history says the set is no longer
        # held-out, keep it that way.
        recovered["held_out"] = bool(state.get("held_out", True)) and bool(recovered.get("held_out", True))
        recovered["first_run_at"] = state.get("first_run_at") or recovered.get("first_run_at")
    return recovered, True


__all__ = [
    "CONFIG_FILES",
    "ConfigChanged",
    "config_manifest",
    "guard_config",
    "load_run_docs",
    "load_state",
    "model_settings",
    "recover_state",
    "save_state",
    "state_from_runs",
]
