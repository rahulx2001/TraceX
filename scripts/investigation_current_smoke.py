"""Bounded live integration on fictional stored turns; never a human/audio study.

The default is a cost preflight. --execute makes at most four logical model
calls, using the existing lifetime/daily ledgers and an additional $1.60
reservation ceiling. Outputs (including failures) and isolated state persist.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--state-directory", type=Path, default=Path("data/hackathon/current-proof-2026-10-30"))
    parser.add_argument("--output", type=Path, default=Path("reports/hackathon/investigation_current_smoke.json"))
    args = parser.parse_args()
    # Load configured credentials/unchanged budget paths, then isolate only data.
    import src.config  # noqa: F401
    from src.ai_layer import budget, config
    before = budget.status()
    max_attempts, request_ceiling, total_ceiling = 8, 200_000, 1_600_000
    plan = {"synthetic": True, "model": config.model_text(), "logical_calls_max": 4,
            "transport_attempts_max": max_attempts, "per_request_reservation_ceiling_usd": request_ceiling/1e6,
            "additional_reservation_ceiling_usd": total_ceiling/1e6,
            "budget_before": before, "enabled": config.meta_enabled(),
            "note": "Conservative configured-rate reservation estimate, not billed cost. Existing lifetime and daily ledgers are unchanged."}
    print(json.dumps(plan, indent=2), flush=True)
    if not args.execute:
        return
    if args.output.exists() or (args.state_directory/"frontline.duckdb").exists():
        raise SystemExit("Existing proof/state preserved. Choose a new explicit output and isolated state directory.")
    if not config.meta_enabled() or before["reserved_upper_bound_usd"]+total_ceiling/1e6 > before["limit_usd"]:
        raise SystemExit("Unavailable model or insufficient existing reservation capacity; no calls made.")
    directory = args.state_directory.resolve()
    directory.mkdir(parents=True, exist_ok=True)
    os.environ.update(FRONTLINE_DB_PATH=str(directory/"frontline.duckdb"), DOMAIN_DB_PATH=str(directory/"domains"),
                      FRONTLINE_OPEN_MODE="1", FRONTLINE_LLM_ENABLED="0", META_RETRIES="0")
    from src.ai_layer import campaign_investigator as ci, meta_client, report_sources as rs, safety_campaigns as sc
    from src.data.turns import persist_turn
    from src.data.timeutil import utc_now
    from src.data.warehouse import ops_con
    original_reserve = budget.reserve
    reservations = []

    def bounded_reserve(payload):
        amount = budget.bound(payload)
        if len(reservations) >= max_attempts or amount > request_ceiling or sum(reservations)+amount > total_ceiling:
            raise meta_client.MetaError("synthetic_proof_reservation_ceiling")
        reservation = original_reserve(payload)
        reservations.append(amount)
        return reservation

    budget.reserve = bounded_reserve
    out = {**plan, "recorded_at": sc.now(), "state_directory": str(directory), "live_transport": False,
           "human_review": "pending", "real_audio": False, "independent_accuracy": "not measured",
           "fixture_reviews": "Scripted fictional workflow actions, not independent reviewer judgments",
           "note": "Current-code live integration using synthetic text stored as web-voice turns. No microphone, participant, real repair or external outreach evidence."}
    c = sc.prepared_demo_campaign("synthetic-fixture-operator", "agent")
    out["campaign_id"] = c["campaign_id"]
    interaction = "synthetic-current-report-2026-10-30"
    vid = "DEMO-CAR-010"
    turns = [(1, "customer", "Meri 2019 gaadi speed breaker par khat-khat karti hai aur kabhi steering left khinchti hai. Mujhe part ka naam nahi pata."),
             (2, "agent", "Please confirm the year and what you observed."),
             (3, "customer", "No, I said 2018. No smoke or fire. Khat-khat last Monday se hai. Installation record abhi mere paas nahi hai.")]
    with ops_con() as con:
        con.execute("INSERT INTO interactions (interaction_id,pack_id,pack_version,started_at,ended_at,channel,status) VALUES (?, 'automotive_nhtsa', 'synthetic-current-proof', ?, NULL, 'web_voice', 'active')", [interaction, utc_now()])
    for seq, speaker, text in turns:
        persist_turn(interaction, {"turn_id": f"{interaction}-turn-{seq}", "seq": seq, "speaker": speaker, "text": text})
    with ops_con() as con:
        con.execute("UPDATE interactions SET ended_at=?, status='completed' WHERE interaction_id=?", [utc_now(), interaction])
    out["source_interaction"] = {"interaction_id": interaction, "synthetic": True,
                                 "turns": [{"turn_id": f"{interaction}-turn-{seq}", "speaker": speaker, "seq": seq, "text": text} for seq, speaker, text in turns],
                                 "resolved_report": rs.interaction_report(interaction)}
    try:
        first = ci.investigate(c["campaign_id"], {"vehicle_id": vid, "revision": c["revision"], "request_id": "current-proof-initial",
            "source_ref": out["source_interaction"]["resolved_report"]["source_ref"], "source_reviewed": True,
            "vehicle_association_confirmed": True}, "synthetic-fixture-operator", "agent")
        out["initial"] = first
        if not first.get("extraction", {}).get("mode", "").startswith("meta") or not first.get("brief", {}).get("mode", "").startswith("meta"):
            raise RuntimeError("Initial draft fell back; retained without automatic rerun.")
        out["initial"] = ci.review(c["campaign_id"], first["run_id"], {"decision": "needs_correction", "attestation": True,
            "note": "SCRIPTED FICTIONAL REVIEW: keep the 2018 correction and fire denial; resolve the installation evidence before an engineer decides action."}, "synthetic-fixture-engineer", "agent")
        c = sc.apply_action(c["campaign_id"], "trace_review", {"vehicle_id": vid, "supplier": "SYN-AXLEWORKS", "part_number": "SYN-CA-2301", "lot_id": "SYN-LOT-A",
            "source_ref": "SYN-CURRENT-INSTALLATION-010", "note": "SCRIPTED FICTIONAL REVIEW: installation fixture, not a real vehicle or independent assessment.",
            "evidence_text": "FICTIONAL INSTALLATION RECORD. DEMO-CAR-010 received part SYN-CA-2301 from supplier SYN-AXLEWORKS, lot SYN-LOT-A. Reference SYN-CURRENT-INSTALLATION-010. Demonstration only."},
            "synthetic-fixture-engineer", "agent", c["revision"], "current-proof-trace")
        c = sc.apply_action(c["campaign_id"], "reply", {"vehicle_id": vid, "symptoms": ["clunk", "steering_pull"],
            "text": "Fictional operator follow-up: installation record SYN-CURRENT-INSTALLATION-010 is now attached and reviewed. The owner corrected the year to 2018 and denied smoke or fire. No workshop diagnosis is available for this report."},
            "synthetic-fixture-operator", "agent", c["revision"], "current-proof-followup-source")
        reply = next(v for v in c["vehicles"] if v["vehicle_id"] == vid)["replies"][-1]
        out["followup_source"] = rs.reply_report(c["campaign_id"], vid, reply["reply_id"])
        out["followup"] = ci.investigate(c["campaign_id"], {"vehicle_id": vid, "revision": c["revision"], "request_id": "current-proof-followup",
            "parent_run_id": first["run_id"], "source_ref": out["followup_source"]["source_ref"], "source_reviewed": True,
            "vehicle_association_confirmed": True}, "synthetic-fixture-operator", "agent")
    except Exception as exc:
        out["failure"] = f"{type(exc).__name__}: {exc}"
    finally:
        budget.reserve = original_reserve
        out["packet"] = sc.get_campaign(c["campaign_id"], packet=True)
        out["packet"]["investigation_drafts"] = ci.list_runs(c["campaign_id"])
        out["budget_after"] = budget.status()
        out["reservation_count"] = len(reservations)
        out["reserved_this_proof_usd"] = sum(reservations)/1e6
        operations = [op for phase in ("initial", "followup") for op in out.get(phase, {}).get("operations", [])]
        out["live_transport"] = any(op.get("live_transport") and op.get("status") == "response_received" for op in operations)
        out["ok"] = "failure" not in out and all(out.get(phase, {}).get("brief", {}).get("mode", "").startswith("meta") for phase in ("initial", "followup"))
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(out, ensure_ascii=False, indent=2)+"\n")
        print(json.dumps({"ok": out["ok"], "artifact": str(args.output), "reserved_usd": out["reserved_this_proof_usd"],
                          "attempts": out["reservation_count"], "failure": out.get("failure"),
                          "initial_tools": [t["tool"] for t in out.get("initial", {}).get("tool_trace", [])],
                          "followup_tools": [t["tool"] for t in out.get("followup", {}).get("tool_trace", [])]}, indent=2))
    if not out["ok"]:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
