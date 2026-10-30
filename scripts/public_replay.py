"""Credit-free public validation of saved counts, source quotations and claim hashes.

Python standard library only. This rechecks published artifacts, not inference,
the full historical experiment, human accuracy or investigator productivity.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INDEX = "reports/hackathon/claim_index.json"


def read(path, root=ROOT):
    return json.loads((root/path).read_text())


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def validate_proof(proof):
    assert proof["synthetic"] is True and proof["live_transport"] is True
    result = []
    for phase in ("initial", "followup"):
        run = proof[phase]
        assert run["status"] == "complete" and run["synthetic_demo"] is True
        citations = {}
        for source in run["sources"]:
            assert hashlib.sha256(source["text"].encode()).hexdigest() == source["sha256"]
            for sentence in source["sentences"]:
                assert source["text"][sentence["start"]:sentence["end"]] == sentence["quote"]
                assert sentence["sentence_id"] not in citations
                citations[sentence["sentence_id"]] = sentence["quote"]
        quotes = [o["evidence"] for o in run["extraction"]["observations"]]
        quotes += [ev for claim in run["brief"]["claims"] for ev in claim["evidence"]]
        assert quotes, "The saved proof has no sourced evidence"
        assert all(citations.get(q["sentence_id"]) == q["quote"] for q in quotes)
        assert len(run["tool_trace"]) <= 2 and all(t["read_only"] for t in run["tool_trace"])
        result.append({"phase": phase, "run_id": run["run_id"], "recorded_at": run["started_at"],
                       "model_id": run["extraction"]["model_id"], "extractor_version": run["extraction"].get("version"),
                       "checked_citations": len(quotes), "recorded_elapsed_ms": run["elapsed_ms"]})
    return result


def validate(root=ROOT):
    index = read(INDEX, root)
    checked = []
    for artifact in index["artifacts"]:
        path = root/artifact["path"]
        assert path.is_relative_to(root) and path.is_file(), f"Missing public artifact: {artifact['path']}"
        assert sha(path) == artifact["sha256"], f"Artifact changed: {artifact['path']}"
        checked.append(artifact["path"])
    holdout = read("reports/defect/fuel_holdout/holdout_results.json", root)
    for name in ("method", "count_baseline"):
        metrics = holdout[name]
        assert metrics["hits"] + metrics["misses"] == metrics["campaigns"]
        assert metrics["campaign_recall"] == metrics["hits"] / metrics["campaigns"]
        assert metrics["episode_precision"] == metrics["confirmed_mature_alerts"] / metrics["mature_alerts"]
        assert len(metrics["alert_details"]) == metrics["alerts"]
        assert sum(a["full_followup"] for a in metrics["alert_details"]) == metrics["mature_alerts"]
        assert sum(bool(a["matched_campaigns"]) and a["full_followup"] for a in metrics["alert_details"]) == metrics["confirmed_mature_alerts"]
    method = holdout["method"]
    assert (method["hits"], method["campaigns"], method["confirmed_mature_alerts"], method["mature_alerts"]) == (5, 8, 6, 18)
    draws = holdout["random_reference"]["draws"]
    at_least = sum(d["campaign_recall"] >= method["campaign_recall"] for d in draws)
    assert len(draws) == 100 and at_least == 19
    assert at_least / len(draws) == holdout["random_reference"]["fraction_at_least_method"]
    comparison = read("reports/defect/evidence_v1/development_comparison.json", root)
    assert comparison["rows"] == 8 and comparison["meta_successes"] == 8 and comparison["label_agreements"] == 4
    assert comparison["accuracy"] is None and comparison["human_reviewed"] == 0
    human = read("reports/defect/repair/human_validation_status.json", root)
    assert human["human_labels"] == 0 and human["sample_size"] == 300 and human["accuracy"] is None
    study = read("reports/hackathon/reviewer_study/results.json", root)
    assert study["participants"] == 0 and study["completed_tasks"] == 0 and study["time_saved_percent"] is None
    proofs = {name: validate_proof(read("reports/hackathon/"+name+".json", root))
              for name in ("investigation_live_smoke", "investigation_followup_smoke")}
    return {"ok": True, "validation": "saved-artifact arithmetic, source fidelity and hashes only",
            "model_calls": 0, "new_human_labels": 0, "new_participants": 0,
            "historical_counts": {"campaign_hits": 5, "campaigns": 8, "matching_mature_alerts": 6,
                                  "mature_alerts": 18, "random_runs_at_least_method": at_least, "random_runs": len(draws)},
            "artifacts_checked": checked, "recorded_synthetic_runs": proofs,
            "limits": "No inference, full-data retraining, semantic grading, live-audio validation or productivity measurement was performed."}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT, help="A clean checkout or packaged replay root")
    args = parser.parse_args()
    print(json.dumps(validate(args.root.resolve()), indent=2))


if __name__ == "__main__":
    main()
