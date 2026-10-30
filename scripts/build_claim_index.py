"""Index immutable public evidence; no new labels, measurements or model calls."""
from datetime import datetime, timezone
import json

from scripts.public_replay import ROOT, sha

ARTIFACTS = [
    "reports/defect/fuel_holdout/holdout_results.json",
    "reports/defect/fuel_holdout/protocol.json",
    "reports/defect/evidence_v1/development_comparison.json",
    "reports/defect/repair/human_validation_status.json",
    "reports/hackathon/reviewer_study/results.json",
    "reports/hackathon/investigation_live_smoke.json",
    "reports/hackathon/investigation_followup_smoke.json",
]


def main():
    common = {"verification": "python -m scripts.public_replay", "scope": "saved public artifacts; no new inference or human grading"}
    claims = [
        {"id": "historical-campaign-recall", "claim": "5/8 campaigns matched (62.5%); count baseline also 5/8",
         "artifact": ARTIFACTS[0], "pointers": ["/method/hits", "/method/campaigns", "/count_baseline/hits"],
         "recorded_at": "2026-10-29T18:04:56.052354+00:00", "model_version": "ridge student with 13-week count policy; frozen selection in artifact",
         "limits": "Make/category historical association; model-labelled references; not exact part prediction, superiority or accidents prevented."},
        {"id": "historical-alert-precision", "claim": "6/18 mature alerts matched later campaigns (33.3%)",
         "artifact": ARTIFACTS[0], "pointers": ["/method/confirmed_mature_alerts", "/method/mature_alerts"],
         "recorded_at": "2026-10-29T18:04:56.052354+00:00", "model_version": "same frozen ridge/count method",
         "limits": "24 alerts total, 18 with full follow-up through 2026-09-30; no human mechanical-defect validation."},
        {"id": "random-reference", "claim": "19/100 workload-matched random runs reached or exceeded 62.5% recall",
         "artifact": ARTIFACTS[0], "pointers": ["/random_reference/draws", "/random_reference/fraction_at_least_method"],
         "recorded_at": "2026-10-29T18:04:56.052354+00:00", "model_version": "recorded retrospective random seeds",
         "limits": "Conditional historical reference, not an online policy or new experiment."},
        {"id": "development-agreement", "claim": "Eight valid direct-Meta development outputs; four label agreements with the student",
         "artifact": ARTIFACTS[2], "pointers": ["/rows", "/meta_successes", "/label_agreements", "/extractor_version"],
         "recorded_at": "2026-10-29 (development artifact)", "model_version": "recorded extractor fingerprint 9d39c1dc5af2",
         "limits": "Agreement is not accuracy; distinct from the reserved 100 complaints and five recall descriptions."},
        {"id": "original-human-review", "claim": "Original 300-example sample: 0 human labels; accuracy unavailable",
         "artifact": ARTIFACTS[3], "pointers": ["/human_labels", "/sample_size", "/accuracy"],
         "recorded_at": "Status snapshot indexed 2026-10-30", "model_version": "not applicable; pending human review",
         "limits": "A prepared review workflow is not a completed human evaluation."},
        {"id": "reviewer-study", "claim": "Prepared study: 0 participants, 0 completed tasks; time savings unavailable",
         "artifact": ARTIFACTS[4], "pointers": ["/participants", "/completed_tasks", "/time_saved_percent"],
         "recorded_at": "Status snapshot indexed 2026-10-30", "model_version": "prepared recorded-assistance study",
         "limits": "No participant, usefulness, quality or productivity result exists in this artifact."},
        {"id": "recorded-investigation", "claim": "Two saved synthetic scenarios, each with an initial and follow-up investigation",
         "artifact": ARTIFACTS[5], "additional_artifacts": [ARTIFACTS[6]], "pointers": ["/initial", "/followup", "/model_id", "/recorded_at"],
         "recorded_at": "2026-10-29T19:09:48.694663+00:00 and 2026-10-29T19:25:16.974209+00:00",
         "model_version": "meta-models/muse-spark-open-1026; complaint-evidence-v1",
         "limits": "Recorded real model transport on fictional data; quotation fidelity checks do not prove interpretation accuracy, new code validation or general reliability."},
    ]
    index = {"schema_version": 1, "indexed_at": datetime.now(timezone.utc).isoformat(), **common,
             "claims": claims, "artifacts": [{"path": p, "sha256": sha(ROOT/p)} for p in ARTIFACTS],
             "full_reproduction": "Full experiment replay needs frozen gitignored inputs, source ZIPs, embeddings and weights listed by reports/defect/fuel_holdout/protocol.json. A new public download can differ. The small replay checks published arithmetic and citations only."}
    (ROOT/"reports/hackathon/claim_index.json").write_text(json.dumps(index, indent=2)+"\n")
    lines = ["# TraceX claim-to-artifact index", "", "Every number in the short submission pitch should resolve here. These are saved scoped results, not new measurements.", "",
             "Run `python -m scripts.public_replay` from a clean checkout with Python 3.10+; only the standard library is used. No API key, private cache, model weights or network is needed.", "",
             "| Claim | Source and date | Model/version and scope |", "|---|---|---|"]
    for c in claims:
        lines.append(f"| {c['claim']} | [{c['id']}](../../{c['artifact']}) · {c['recorded_at']} | {c['model_version']}. {c['limits']} |")
    lines += ["", "The machine-readable [index](claim_index.json) pins SHA-256 hashes and JSON pointers for each artifact. The source hashes detect changes to these recorded files; this does not sign the campaign evidence packet.", "", "## Full-data replay", "", index["full_reproduction"], "",
              "See [the frozen experiment instructions](../defect/fuel_holdout/README.md) and [input/source hashes](../defect/fuel_holdout/protocol.json). Keep opened evaluation data distinct from fresh holdouts. Do not tune against the published result or reuse its upper confidence endpoint as an achieved score.", "",
              "## Current implementation checks", "", "`PLAYWRIGHT_CHANNEL=chrome npm run test:signin` in `dashboard/` builds current assets and exercises real local entry/auth and text-report-to-packet behavior, plus clearly labelled UI fixtures. It makes no model call. Source version and acceptance details are in [entry validation](../../docs/entry-auth-validation.md). A saved historical video or model output does not validate a new build.", ""]
    (ROOT/"reports/hackathon/CLAIM_INDEX.md").write_text("\n".join(lines))
    print("Indexed seven scoped claims and immutable public artifacts; no new measurement.")


if __name__ == "__main__":
    main()
