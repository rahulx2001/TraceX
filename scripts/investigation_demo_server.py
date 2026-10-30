"""Serve an isolated demo with provenance-labelled replay of real Meta outputs.

No model calls, external delivery, human labels or participant results are made.
"""
import argparse
import copy
import hashlib
import json
import os
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=8768)
    parser.add_argument("--scenario", default="v1", choices=["v1", "recording", "verification"], help="Separate isolated local demo datasets")
    parser.add_argument("--state-directory", type=Path, help="A separate rehearsal directory; existing pilot data is never reset")
    parser.add_argument("--without-recorded-proof", action="store_true", help="Serve only the current deterministic workflow")
    parser.add_argument("--existing-state-only", action="store_true", help="Serve an existing fixture database without seeding or importing/remapping model results")
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    directory = args.state_directory.resolve() if args.state_directory else root/f"data/hackathon/investigation-demo-v2-{args.scenario}"
    if args.existing_state_only and not (directory/"frontline.duckdb").is_file():
        parser.error("--existing-state-only requires a state directory containing frontline.duckdb")
    directory.mkdir(parents=True, exist_ok=True)
    os.environ.update(FRONTLINE_TEST_ISOLATION="1", FRONTLINE_DB_PATH=str(directory/"frontline.duckdb"),
                      DOMAIN_DB_PATH=str(directory/"domains"), FRONTLINE_OPEN_MODE="1", FRONTLINE_API_KEY="",
                      FRONTLINE_AI_LAYER="off", FRONTLINE_LLM_ENABLED="0", FRONTLINE_ENABLED="1")
    from src.ai_layer import campaign_investigator as ci, safety_campaigns as sc
    from src.data.warehouse import ops_con
    from scripts.seed_domains import build
    import uvicorn
    if not args.existing_state_only and not (directory/"domains/automotive_nhtsa.duckdb").exists():
        build("automotive_nhtsa")
    c = None if args.existing_state_only else sc.prepared_demo_campaign("demo-operator", "agent")
    replay_phases = [] if args.without_recorded_proof or args.existing_state_only else ["initial", "followup"]
    if replay_phases:
        source = root/"reports/hackathon/investigation_followup_smoke.json"
        proof = json.loads(source.read_text())
        if proof.get("live_transport") is not True or proof.get("synthetic") is not True:
            raise ValueError("A real, explicitly synthetic Meta proof is required")
    with ops_con() as con:
        con.execute(ci.DDL)
        for phase in replay_phases:
            run = copy.deepcopy(proof[phase])
            run["replay"] = {"source_artifact": str(source.relative_to(root)), "sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
                             "original_campaign_id": run["campaign_id"], "original_snapshot_revision": run["snapshot_revision"],
                             "original_status": run["status"],
                             "note": "Historical synthetic output for display only; original source IDs and snapshots are retained. This is not a new inference or a review of the current campaign evidence."}
            run["campaign_id"] = c["campaign_id"]
            run["status"] = "historical_replay"
            request_id = "recorded-"+run["run_id"]
            con.execute("INSERT INTO safety_investigation_runs VALUES (?, ?, ?, ?, ?, ?) ON CONFLICT DO NOTHING",
                        [run["run_id"], c["campaign_id"], request_id, hashlib.sha256(json.dumps(run,sort_keys=True).encode()).hexdigest(), "historical_replay", json.dumps(run)])
    print(f"Isolated demo, model calls disabled: http://127.0.0.1:{args.port}/ui/#demo", flush=True)
    uvicorn.run("src.api.main:app", host="127.0.0.1", port=args.port, log_level="warning")


if __name__ == "__main__": main()
