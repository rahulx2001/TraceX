"""Live Meta investigation on a new isolated synthetic campaign; bounded to four logical calls."""
from __future__ import annotations

import json
import os
import tempfile
import argparse
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--unknown-lot", action="store_true", help="Exercise the missing-record question and a separately simulated trace review")
    args = parser.parse_args()
    with tempfile.TemporaryDirectory(prefix="tracex-investigation-proof-") as directory:
        os.environ["FRONTLINE_DB_PATH"] = str(Path(directory)/"frontline.duckdb")
        os.environ["DOMAIN_DB_PATH"] = str(Path(directory)/"domains")
        os.environ["FRONTLINE_OPEN_MODE"] = "1"
        from src.ai_layer import budget, campaign_investigator as ci, config, safety_campaigns as sc
        if not config.meta_enabled():
            raise SystemExit("Meta is unavailable; no live proof written")
        before = budget.status()
        c = sc.prepared_demo_campaign("synthetic-smoke", "agent")
        vid = "DEMO-CAR-010" if args.unknown_lot else "DEMO-CAR-003"
        initial_revision = c["revision"]
        first = ci.investigate(c["campaign_id"], {"vehicle_id": vid, "revision": c["revision"], "request_id": "proof-start",
              "text": "Meri gaadi speed breaker par khat-khat karti hai aur kabhi steering left khinchti hai. Mujhe part ka naam nahi pata."}, "synthetic-smoke", "agent")
        if first["extraction"]["mode"] != "meta" or first["brief"]["mode"] != "meta":
            raise SystemExit("Live initial draft incomplete: "+str(first["extraction"].get("fallback_reason") or first["brief"].get("fallback_reason") or "rejected citations"))
        assert sc.get_campaign(c["campaign_id"])["revision"] == initial_revision
        followup_text = "Fictional owner clarification: The knocking started last Monday before the workshop visit. I did not see smoke or fire."
        if args.unknown_lot:
            c = sc.apply_action(c["campaign_id"], "trace_review", {"vehicle_id": vid, "supplier": "SYN-AXLEWORKS", "part_number": "SYN-CA-2301",
                "lot_id": "SYN-LOT-A", "source_ref": "SYN-INSTALLATION-REVIEW", "note": "SYNTHETIC DEMO: simulate a reviewer checking the fictional installation record.",
                "evidence_text": f"FICTIONAL INSTALLATION RECORD: {vid}, supplier SYN-AXLEWORKS, part SYN-CA-2301, lot SYN-LOT-A. Demo fixture only."},
                "synthetic-smoke", "agent", c["revision"], "simulated-trace-review")
            followup_text = "Fictional operator follow-up: installation record SYN-INSTALLATION-REVIEW has now been reviewed and recorded in the campaign. The knocking began last Monday. No smoke or fire was reported."
        second = ci.investigate(c["campaign_id"], {"vehicle_id": vid, "revision": c["revision"], "request_id": "proof-followup", "parent_run_id": first["run_id"],
              "text": followup_text}, "synthetic-smoke", "agent")
        if second["extraction"]["mode"] != "meta" or second["brief"]["mode"] != "meta":
            raise SystemExit("Live follow-up incomplete: "+str(second["extraction"].get("fallback_reason") or second["brief"].get("fallback_reason") or "rejected citations"))
        assert sc.get_campaign(c["campaign_id"])["revision"] == c["revision"]
        out = {"synthetic": True, "live_transport": True, "model_id": config.model_text(), "recorded_at": sc.now(),
               "human_review": "pending", "agent_changed_campaign": False, "simulated_trace_review": args.unknown_lot,
               "initial": first, "followup": second,
               "budget_before": before, "budget_after": budget.status(),
               "note": "Live integration proof on fictional input, not diagnostic accuracy or user-study evidence."}
        filename = "investigation_followup_smoke.json" if args.unknown_lot else "investigation_live_smoke.json"
        path = Path(__file__).resolve().parents[1]/"reports/hackathon"/filename
        if path.exists():
            import hashlib
            history = path.parent/"investigation_proof_history"
            history.mkdir(exist_ok=True)
            (history/f"{path.stem}-{hashlib.sha256(path.read_bytes()).hexdigest()[:16]}.json").write_bytes(path.read_bytes())
        path.write_text(json.dumps(out, ensure_ascii=False, indent=2)+"\n")
        print(json.dumps({"ok": True, "model_id": out["model_id"], "logical_calls": first["model_calls"]+second["model_calls"],
                          "initial_lookups": [x["tool"] for x in first["tool_trace"]], "followup_claims": len(second["brief"]["claims"]),
                          "agent_changed_campaign": False, "proof": str(path)}, indent=2))


if __name__ == "__main__": main()
