"""Publish a small dashboard summary from verified experiment artifacts only."""
import json

from scripts.ai_oos_backtest import canonical_hash
from scripts.defect_accuracy import load_sample, resolve_human_label
from scripts.defect_prepare_inputs import file_sha256
from scripts.defect_repair import OUT, ROOT, write_json


def main():
    results = json.loads((OUT / "prediction_results.json").read_text())
    frozen = json.loads((OUT / "prediction_config.json").read_text())
    if canonical_hash(frozen["body"]) != frozen["sha256"] or results["config_sha256"] != frozen["sha256"]:
        raise ValueError("Prediction result/configuration mismatch")
    sample_path = OUT / "human_labelled.csv"
    if not sample_path.exists():
        sample_path = ROOT / "reports/defect/defect_label_sample_300.csv"
    sample = load_sample(sample_path)
    human = sum(resolve_human_label(r.label, r.allowed_label_ids, r.allowed_label_text)[1] == 'ok'
                for r in sample.itertuples())
    blocks = {}
    for name in ("all_reports", "excluding_explicit_recall_reports"):
        b = results[name]
        random = b["random"]
        blocks[name] = {"detector": {k: v for k, v in b["rolling_defect"].items() if k not in {"alert_details", "campaign_hits"}},
                        "count": {k: v for k, v in b["count_reference"].items() if k not in {"alert_details", "campaign_hits"}},
                        "random_mean_recall": random["mean_campaign_recall"],
                        "random_draws": len(random["draws"]),
                        "random_interval": random["campaign_recall_95_percentile_interval"],
                        "random_at_least_detector": random["fraction_at_least_detector_recall"]}
    summary = {"status": results["status"], "coverage": results["coverage"], "blocks": blocks,
               "human_review": {"reviewed": human, "total": len(sample)},
               "source": "reports/defect/repair/prediction_results.json", "source_sha256": file_sha256(OUT / "prediction_results.json"),
               "scope": "Five makes · model years 2015–2024 · fuel system · 2021–2024 evaluation",
               "note": "Training-selected thresholds on a previously examined historical window. Recall descriptions are model-labelled. Matches do not establish physical defect identity or accidents prevented. Human classification accuracy awaits review."}
    holdout_path = ROOT / "reports/defect/fuel_holdout/holdout_results.json"
    if holdout_path.exists():
        held = json.loads(holdout_path.read_text())
        selection = json.loads((holdout_path.parent / "selection.json").read_text())
        if canonical_hash(selection["body"]) != selection["sha256"] or held["selection_sha256"] != selection["sha256"]:
            raise ValueError("Held-out result/selection hash mismatch")
        summary["temporal_holdout"] = {
            "period": held["holdout"], "target_met": held["target_met"],
            "method": {k: v for k, v in held["method"].items() if k not in {"alert_details", "campaign_hits"}},
            "count_baseline": {k: v for k, v in held["count_baseline"].items() if k not in {"alert_details", "campaign_hits"}},
            "random_mean_recall": held["random_reference"]["mean_recall"],
            "random_draws": len(held["random_reference"]["draws"]),
            "random_at_least_method": held["random_reference"]["fraction_at_least_method"],
            "outcome_end": held["outcome_end"],
            "source": str(holdout_path.relative_to(ROOT)),
            "note": held["interpretation"], "source_sha256": file_sha256(holdout_path),
            "protocol_qualified": selection["body"]["protocol_qualified"],
        }
    write_json(ROOT / "dashboard/src/ai/defectPrediction.json", summary)
    print(json.dumps({"human_review": summary["human_review"], "source_sha256": summary["source_sha256"]}))


if __name__ == '__main__':
    main()
