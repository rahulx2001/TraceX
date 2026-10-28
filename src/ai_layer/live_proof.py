"""Versioned, feature-specific evidence from real calls; never a key-presence flag."""
from __future__ import annotations

import json
from pathlib import Path

from src.ai_layer import config


def proof_path() -> Path:
    return Path(__file__).resolve().parents[2] / "reports/hackathon/meta_live_smoke.json"


def save_proof(checks: list[dict], *, live: bool) -> dict:
    from datetime import datetime, timezone
    from src.ai_layer.budget import status
    out = {"schema_version": 1, "ok": bool(live and checks and all(c.get("ok") for c in checks)),
           "live_transport": live, "api_host": config._host(config.api_base()),
           "api_base": config.api_base(), "recorded_at": datetime.now(timezone.utc).isoformat(),
           "checks": checks, "budget": status()}
    path = proof_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(out, indent=2, ensure_ascii=False, default=str) + "\n")
    tmp.replace(path)
    return out


def verified_features() -> dict[str, bool]:
    expected = {"text": config.model_text(), "vision": config.model_vision(),
                "segmentation": config.model_sam(), "image": config.model_image()}
    found = {k: False for k in expected}
    import os
    if os.getenv("FRONTLINE_TEST_ISOLATION") == "1":
        return found
    try:
        data = json.loads(proof_path().read_text())
        if not data.get("live_transport") or data.get("api_base") != config.api_base():
            return found
        for c in data.get("checks", []):
            kind = c.get("feature")
            if kind in expected and c.get("ok") and c.get("model_id") == expected[kind]:
                found[kind] = True
    except (OSError, ValueError, TypeError):
        pass
    return found
