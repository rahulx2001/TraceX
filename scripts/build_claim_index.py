"""Index immutable public evidence; no new labels, measurements or model calls."""
from datetime import datetime, timezone
import json

from scripts.public_replay import ROOT, sha

HUMAN_REVIEW_STATUS = "reports/improvement/human_reviews/round1/review_status.json"
HUMAN_REVIEW_PROVENANCE = "reports/improvement/human_reviews/round1/human_review_provenance.json"
GROUNDED_CANDIDATE_DIR = "reports/improvement/defect_grounded_v1"
GROUNDED_CANDIDATE_COMPARISON = f"{GROUNDED_CANDIDATE_DIR}/comparison.json"
WITHDRAWAL = "reports/improvement/human_reviews/REJECTED_fabricated_rounds.md"
CURRENT_REVIEW = "reports/improvement/human_reviews/round4"

ARTIFACTS = [
    "reports/defect/fuel_holdout/holdout_results.json",
    "reports/defect/fuel_holdout/protocol.json",
    "reports/defect/evidence_v1/development_comparison.json",
    HUMAN_REVIEW_STATUS,
    "reports/hackathon/reviewer_study/results.json",
    "reports/hackathon/investigation_live_smoke.json",
    "reports/hackathon/investigation_followup_smoke.json",
    "reports/defect/repair/human_validation_status.json",
    HUMAN_REVIEW_PROVENANCE,
]


def grounded_candidate_claim():
    """Index the separate saved candidate only after its final comparison exists."""
    if not (ROOT / GROUNDED_CANDIDATE_COMPARISON).is_file():
        return None, []
    comparison = json.loads((ROOT / GROUNDED_CANDIDATE_COMPARISON).read_text())
    score_path = f"{GROUNDED_CANDIDATE_DIR}/accuracy.json"
    score = json.loads((ROOT / score_path).read_text())
    candidate = comparison["candidate_accuracy"]
    baseline = comparison["baseline_accuracy"]
    missing = comparison["missing_predictions"]["candidate"]
    target = comparison["target"]
    rejected = not target["met"] or candidate["value"] <= baseline["value"]
    outcome = "rejected" if rejected else "evaluated"
    ci = candidate["ci95"]
    target_outcome = "met" if target["met"] else "not met"
    claim_text = (
        f"Grounded candidate {outcome}: {candidate['numerator']}/{candidate['denominator']} = {candidate['value']:.1%} "
        f"(95% CI {ci[0]:.1%}–{ci[1]:.1%}); baseline {baseline['numerator']}/{baseline['denominator']} = {baseline['value']:.1%}; "
        f"missing predictions {missing['numerator']}/{missing['denominator']}; "
        f"target {target['required_correct']}/{target['denominator']} {target_outcome}"
    )
    artifacts = [
        score_path, GROUNDED_CANDIDATE_COMPARISON,
        f"{GROUNDED_CANDIDATE_DIR}/protocol.json",
        f"{GROUNDED_CANDIDATE_DIR}/row_validation_plan.json",
        f"{GROUNDED_CANDIDATE_DIR}/row_validation_manifest.json",
        f"{GROUNDED_CANDIDATE_DIR}/retry_plan.json",
        f"{GROUNDED_CANDIDATE_DIR}/evaluation_contract_check.json",
        f"{GROUNDED_CANDIDATE_DIR}/pre_claim_update/build_claim_index.py",
        "scripts/defect_grounded_candidate.py", "scripts/defect_grounded_row_validation.py",
        "scripts/defect_grounding.py", "scripts/defect_candidate_compare.py", "scripts/defect_accuracy.py",
    ]
    for filename in ("EVALUATION.md", "status.json", "verification.json", "common_macro_interval.json"):
        path = f"{GROUNDED_CANDIDATE_DIR}/{filename}"
        if (ROOT / path).is_file():
            artifacts.append(path)
    classifier = score["classifier"]
    claim = {
        "id": "grounded-human-review-candidate", "claim": claim_text,
        "status": "evaluated_rejected" if rejected else "evaluated",
        "deployment_status": "not_deployed",
        "artifact": GROUNDED_CANDIDATE_COMPARISON,
        "additional_artifacts": [path for path in artifacts if path != GROUNDED_CANDIDATE_COMPARISON],
        "pointers": ["/candidate_accuracy/numerator", "/candidate_accuracy/denominator", "/candidate_accuracy/value",
                     "/candidate_accuracy/ci95", "/baseline_accuracy", "/missing_predictions/candidate",
                     "/paired_accuracy_difference", "/target", "/common_label_macro_f1"],
        "recorded_at": comparison["generated_at"],
        "model_version": "; ".join(classifier["models"] + classifier["prompt_versions"]),
        "limits": "Separate candidate evaluation on the opened 300-record historical sample. Missing predictions count as wrong. "
                  "Human-review independence and prior full-sample assignment retain the user-attested provenance limits. "
                  "The candidate is not deployed. Evaluation-only; no fitting, calibration, feature selection or dashboard accuracy.",
    }
    return claim, artifacts


def main():
    human_review = json.loads((ROOT / HUMAN_REVIEW_STATUS).read_text())
    human_review_artifacts = human_review.get("additional_artifacts", [HUMAN_REVIEW_PROVENANCE])
    artifacts = list(dict.fromkeys(ARTIFACTS + human_review_artifacts))
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
        {"id": "original-human-review", "claim": human_review["claim"], "status": human_review["status"],
         "artifact": HUMAN_REVIEW_STATUS, "additional_artifacts": human_review_artifacts,
         "pointers": ["/human_labels", "/sample_size", "/notes_present", "/second_review/reviewed_ids",
                      "/second_review/minimum_preregistered_ids", "/accuracy", "/accuracy_interval", "/status"],
         "recorded_at": human_review["verified_at"], "model_version": human_review.get("model_version", "not applicable; classifier accuracy unscored"),
         "limits": human_review.get("limits", "Primary review only. Independent blinded review, agreement and source-evidence adjudication remain pending. Evaluation-only; no fitting, calibration, feature selection or dashboard accuracy.")},
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
    withdrawn = (ROOT / WITHDRAWAL).is_file()
    if withdrawn:
        claims = [c for c in claims if c["id"] != "original-human-review"]
        claims.append({
            "id": "review-provenance-withdrawal",
            "claim": "Earlier second-review and timed-review claims were withdrawn; Rahul's original labels remain attested single-reviewer evidence",
            "status": "withdrawn_review_claims", "artifact": WITHDRAWAL, "pointers": [],
            "recorded_at": "Withdrawal recorded before the round-4 evaluation",
            "model_version": "Provenance audit; no model inference",
            "limits": "No independent review validation, kappa or 85% accuracy claim is supported by the withdrawn rounds. Archived files remain available for audit.",
        })
        artifacts.append(WITHDRAWAL)
    current_status_path = f"{CURRENT_REVIEW}/review_status.json"
    if (ROOT / current_status_path).is_file():
        current = json.loads((ROOT / current_status_path).read_text())
        score = json.loads((ROOT / CURRENT_REVIEW / "accuracy_v2.json").read_text())
        challenger = json.loads((ROOT / CURRENT_REVIEW / "candidate_accuracy_v2.json").read_text())
        current_artifacts = [f"{CURRENT_REVIEW}/{name}" for name in (
            "accuracy_v2.json", "candidate_accuracy_v2.json", "comparison_v2.json", "EVALUATION.md",
            "adjudication/adjudicated_labels_v2.csv", "adjudication/decision_trail.json")]
        claims.append({
            "id": "round4-evaluation",
            "claim": f"Current historical evaluation: {score['accuracy_numerator']}/{score['accuracy_denominator']} = {score['accuracy']:.1%} accuracy, macro-F1 {score['macro_f1']:.3f} over {score['macro_f1_label_count']} labels; challenger {challenger['accuracy_numerator']}/{challenger['accuracy_denominator']} = {challenger['accuracy']:.1%}, rejected",
            "status": current["status"], "artifact": current_status_path,
            "additional_artifacts": current_artifacts,
            "pointers": ["/status", "/adjudicator", "/limits"],
            "recorded_at": current["verified_at"],
            "model_version": "; ".join(score["classifier"]["models"] + score["classifier"]["prompt_versions"]),
            "limits": "AI-assisted adjudication; human countersignature pending. Blinding is unconfirmed; statistical agreement does not establish independence. Opened 300-record historical evaluation only; no accident prediction accuracy or demonstrated improvement.",
        })
        artifacts.extend([current_status_path, *current_artifacts])
    candidate_claim, candidate_artifacts = grounded_candidate_claim()
    if candidate_claim is not None:
        if withdrawn:
            candidate_claim["limits"] = "Separate candidate evaluation against the original attested single-reviewer labels. Second-review independence claims were withdrawn. Missing predictions count as wrong; candidate rejected and not deployed. Historical evaluation only; no fitting or calibration."
        claims.append(candidate_claim)
        artifacts = list(dict.fromkeys(artifacts + candidate_artifacts))
    revision_path = "reports/improvement/human_reviews/round1/revisions/manish_export4/status.json"
    finalized_revision_path = "reports/improvement/human_reviews/round1/revisions/manish_export4/finalized/status.json"
    if (ROOT / finalized_revision_path).is_file():
        revision_path = finalized_revision_path
    if not withdrawn and (ROOT / revision_path).is_file():
        revision = json.loads((ROOT / revision_path).read_text())
        revision_artifacts = revision.get("additional_artifacts", [])
        claims.append({
            "id": "human-review-revision-export4", "claim": revision["claim"],
            "status": revision["status"], "artifact": revision_path,
            "additional_artifacts": revision_artifacts,
            "pointers": ["/human_labels", "/sample_size", "/notes_present", "/disagreements",
                         "/adjudicated_disagreements", "/accuracy", "/accuracy_interval", "/status"],
            "recorded_at": revision["verified_at"],
            "model_version": revision.get("model_version", "revised labels unscored"),
            "limits": revision["limits"],
        })
        artifacts = list(dict.fromkeys(artifacts + [revision_path] + revision_artifacts))
    artifacts = list(dict.fromkeys(artifacts))
    index = {"schema_version": 1, "indexed_at": datetime.now(timezone.utc).isoformat(), **common,
             "claims": claims, "artifacts": [{"path": p, "sha256": sha(ROOT/p)} for p in artifacts],
             "full_reproduction": "Full experiment replay needs frozen gitignored inputs, source ZIPs, embeddings and weights listed by reports/defect/fuel_holdout/protocol.json. A new public download can differ. The small replay checks published arithmetic and citations only."}
    (ROOT/"reports/hackathon/claim_index.json").write_text(json.dumps(index, indent=2)+"\n")
    lines = ["# TraceX claim-to-artifact index", "", "Every number in the short submission pitch should resolve here. These are saved scoped results, not new measurements.", "",
             "Run `python -m scripts.public_replay` from a clean checkout with Python 3.10+; only the standard library is used. No API key, private cache, model weights or network is needed.", "",
             "| Claim | Source and date | Model/version and scope |", "|---|---|---|"]
    for c in claims:
        lines.append(f"| {c['claim']} | [{c['id']}](../../{c['artifact']}) · {c['recorded_at']} | {c['model_version']}. {c['limits']} |")
    lines += ["", "The machine-readable [index](claim_index.json) pins SHA-256 hashes and JSON pointers for each artifact. The source hashes detect changes to these recorded files; this does not sign the campaign evidence packet.", "", "## Full-data replay", "", index["full_reproduction"], "",
              "See [the frozen experiment instructions](../defect/fuel_holdout/README.md) and [input/source hashes](../defect/fuel_holdout/protocol.json). Keep opened evaluation data distinct from fresh holdouts. Do not tune against the published result or reuse its upper confidence endpoint as an achieved score.", "",
              "## Current implementation checks", "", "`PLAYWRIGHT_CHANNEL=chrome npm run test:signin` in `dashboard/` builds current assets and exercises real local entry/auth and text-report-to-packet behavior, plus clearly labelled UI fixtures. It makes no model call. Source version and acceptance details are in [entry validation](../../docs/entry-auth-validation.md). A saved historical video or model output does not validate a new build.", "",
              "The [30 October container execution](container_validation/README.md) records",
              "clean image and Compose/browser checks, public CI, exact image/source versions,",
              "60 focused Python tests and failed attempts. Reproduce with",
              "`python3 -m scripts.docker_readiness --image IMAGE --expected-revision SHA --compose --browser --output /tmp/result.json`",
              "after [building the image](../../docs/container-validation.md). These are",
              "fictional text/software checks with zero inference, not participant or audio",
              "quality results. [Real-audio status](../voice_validation/results.json) remains",
              "zero captures, zero participants and no latency percentiles.", ""]
    (ROOT/"reports/hackathon/CLAIM_INDEX.md").write_text("\n".join(lines))
    print(f"Indexed {len(claims)} scoped claims and immutable public artifacts; no new measurement.")


if __name__ == "__main__":
    main()
