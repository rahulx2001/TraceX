"""Record one real Meta intake workflow. Optional --vision/--sam/--image checks.

Run with the server-side .env or exported key. Synthetic input only. Default
output: reports/hackathon/meta_live_smoke.json. A skipped/unaccepted workflow
is never recorded as verified. Uses the existing lifetime $30 spend guard.
"""
from __future__ import annotations

import argparse
import asyncio
import base64
import time
from pathlib import Path


def run_checks(*, vision=False, sam=False, image=False):
    from src.config import load_repo_env
    load_repo_env()
    from src.ai_layer import config, meta_client
    from src.ai_layer.demo import run_meta_workflow, synthetic_rotor_png
    from src.ai_layer.live_proof import save_proof
    if not config.meta_enabled():
        return {"ok": False, "skipped": "no configured Meta key or layer switched off", "checks": []}

    checks = []
    def check(feature, model, fn):
        start = time.monotonic()
        try:
            result = fn()
            ok = result.get("ok", True)
            item = {"feature": feature, "model_id": model, "ok": bool(ok), "result": result}
        except Exception as e:
            item = {"feature": feature, "model_id": model, "ok": False,
                    "reason": getattr(e, "reason", type(e).__name__)}
        item["ms"] = round((time.monotonic() - start) * 1000)
        checks.append(item)

    check("text", config.model_text(), lambda: asyncio.run(run_meta_workflow()))
    data_url = "data:image/png;base64," + base64.b64encode(synthetic_rotor_png(240, 180)).decode()
    if vision:
        schema = {"type": "object", "properties": {"description": {"type": "string"}}, "required": ["description"]}
        check("vision", config.model_vision(), lambda: meta_client.chat_json(system="Describe only visible features. JSON only.",
              user="Describe this synthetic image.", schema=schema, schema_name="smoke_vision", model=config.model_vision(), images=[data_url]))
    if sam:
        def segment():
            boxes = meta_client.sam_segment(concept="brake disc", image_data_url=data_url)
            return {"ok": bool(boxes), "boxes": boxes}
        check("segmentation", config.model_sam(), segment)
    if image:
        def generate():
            result = meta_client.image_generate(prompt="Synthetic brake disc illustration, no text", size="512x512")
            return {"ok": bool(result), "returned_keys": sorted(result)}
        check("image", config.model_image(), generate)
    return save_proof(checks, live=meta_client._transport is meta_client._urllib_transport)


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--vision", action="store_true")
    p.add_argument("--sam", action="store_true")
    p.add_argument("--image", action="store_true")
    args = p.parse_args(argv)
    # Every execution gets its own fixture warehouse; no pilot reset or reuse.
    import os, tempfile
    from src.config import REPO_ROOT
    root = Path(tempfile.mkdtemp(prefix="tracex-meta-proof-"))
    os.environ["FRONTLINE_DB_PATH"] = str(root / "frontline.duckdb")
    os.environ["DOMAIN_DB_PATH"] = str(root / "domains")
    os.environ["FRONTLINE_LLM_ENABLED"] = "0"
    from src.data.warehouse import init_ops_db
    from scripts.seed_domains import build
    init_ops_db()
    build("automotive_nhtsa", force=True)
    out = run_checks(**vars(args))
    if out.get("skipped"):
        print("Meta proof skipped:", out["skipped"])
        print("checks: [] (no live verification recorded)")
        return 0
    # The full safe synthetic evidence is in the artifact, not raw provider logs.
    print("Meta proof:", "verified" if out.get("ok") else "not verified")
    for c in out.get("checks", []):
        print(c["feature"], c["model_id"], "accepted" if c.get("ok") else c.get("reason") or c.get("result", {}).get("fallback_reason", "not accepted"))
    print("Artifact: reports/hackathon/meta_live_smoke.json")
    return 0 if out.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
