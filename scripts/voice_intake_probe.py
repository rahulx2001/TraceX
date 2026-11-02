"""One opt-in development text probe. No audio, labels, or budget/cap resets."""
from __future__ import annotations

import argparse
import asyncio
import json
import os
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]


async def run(output):
    # Private, durable development records; spend/cap keep their existing paths.
    os.environ["FRONTLINE_DB_PATH"] = str(ROOT / "data/hackathon/voice-intake-development.duckdb")
    from src.config import load_repo_env
    load_repo_env()
    from src.ai_layer import budget, config
    from src.ai_layer.intake_enhancer import maybe_enhance_intake
    from src.ai_layer.meta_client import calls_today
    from src.agents.base import InteractionContext
    from src.agents.intake import IntakeAgent
    from src.domains.loader import load_pack

    if config.backend() != "baseten" or not config.meta_enabled():
        raise SystemExit("Configured Baseten text endpoint is unavailable; no request sent.")
    before = budget.status()
    if before["limit_usd"] - before["reserved_upper_bound_usd"] < .15:
        raise SystemExit("Insufficient conservative reserve for this bounded probe; no request sent.")
    from src.data.warehouse import init_ops_db
    init_ops_db()
    text = "मेरी होंडा सिविक 2019 के ब्रेक से बहुत आवाज़ आ रही है"
    ctx = InteractionContext(interaction_id="synthetic-voice-text-development-2026-10-30",
                             pack=load_pack("automotive_nhtsa"), channel="web_voice", case_kind="simulated")
    ctx.record_turn("agent", "What is happening with your vehicle?")
    ctx.record_turn("customer", text)
    original = await IntakeAgent(ctx).run(customer_turn=text)
    deterministic = dict(original.get("extracted") or {})
    result = await maybe_enhance_intake(ctx, text, original)
    out = {"scope": "single synthetic text development probe through the shipped intake enhancer; not microphone/audio quality or human accuracy",
           "source_kind": "synthetic_text", "audio_uploaded": False,
           "human_grading": "pending", "code_revision": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
           "working_tree_diff_sha256": __import__("hashlib").sha256(subprocess.check_output(["git", "diff"], cwd=ROOT)).hexdigest(),
           "text": text, "deterministic_extraction": deterministic,
           "accepted_extraction": result.get("extracted"), "ai_layer": result.get("ai_layer"),
           "operation": result.get("voice_understanding"),
           "budget_before": before, "budget_after": budget.status(), "calls_after": calls_today()}
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({"evidence": str(output), "mode": (out["operation"] or {}).get("mode"),
                      "elapsed_ms": (out["operation"] or {}).get("elapsed_ms"), "budget": out["budget_after"]}))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--live", action="store_true", help="Explicitly authorize one guarded development probe")
    parser.add_argument("--output", type=Path, default=ROOT / "reports/hackathon/voice_repair_2026_10_30/meta_text_probe.json")
    args = parser.parse_args()
    if not args.live:
        print("No request sent. --live runs one synthetic text probe with the existing persistent budget and daily cap; reserve up to $0.15 under configured estimated rates.")
        return
    asyncio.run(run(args.output))


if __name__ == "__main__":
    main()
