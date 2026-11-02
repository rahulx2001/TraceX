"""Compare frozen classifier score artifacts after prediction and scoring.

No model design, fitting, calibration, or prediction is performed. Every one
of the 300 gold records remains paired, including missing model predictions.
"""
from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_BASELINE = ROOT / "reports/improvement/human_reviews/round1/accuracy.json"
DEFAULT_CANDIDATE = ROOT / "reports/improvement/defect_grounded_v1/accuracy.json"
DEFAULT_OUT = ROOT / "reports/improvement/defect_grounded_v1/comparison.json"
EXPECTED_ROWS = 300
BOOTSTRAP_SEED = 20261102
BOOTSTRAP_DRAWS = 10000


def prediction(row):
    label = row.get("model_label")
    return label if row.get("model_status") == "ok" and isinstance(label, str) and label.strip() else None


def checked_rows(score, name):
    rows = score.get("rows")
    if not isinstance(rows, list) or len(rows) != EXPECTED_ROWS:
        raise ValueError(f"{name} must preserve exactly {EXPECTED_ROWS} evaluation rows")
    if score.get("sample_size") != EXPECTED_ROWS or score.get("labelled") != EXPECTED_ROWS:
        raise ValueError(f"{name} must contain {EXPECTED_ROWS}/{EXPECTED_ROWS} gold labels")
    if score.get("invalid_human_labels") != 0:
        raise ValueError(f"{name} has invalid or unverified human labels")
    by_id, record_ids = {}, set()
    for row in rows:
        if not isinstance(row, dict):
            raise ValueError(f"{name} contains a non-object row")
        sid, rid = row.get("sample_id"), row.get("record_id")
        if not isinstance(sid, str) or not sid or sid in by_id:
            raise ValueError(f"{name} has missing or duplicate sample identities")
        if not isinstance(rid, str) or not rid or rid in record_ids:
            raise ValueError(f"{name} has missing or duplicate complaint identities")
        human = row.get("human_label")
        if not isinstance(human, str) or not human.strip() or row.get("human_reason") != "ok":
            raise ValueError(f"{name} contains an incomplete gold label: {sid}")
        by_id[sid] = row
        record_ids.add(rid)
    correct = sum(prediction(row) == row["human_label"] for row in rows)
    missing = sum(prediction(row) is None for row in rows)
    if score.get("correct") != correct or score.get("model_missing") != missing:
        raise ValueError(f"{name} score totals disagree with preserved rows")
    if score.get("accuracy_denominator") != EXPECTED_ROWS:
        raise ValueError(f"{name} accuracy excludes evaluation rows")
    if not isinstance(score.get("accuracy"), (int, float)) or not math.isclose(score["accuracy"], correct / EXPECTED_ROWS):
        raise ValueError(f"{name} accuracy disagrees with its all-row denominator")
    return by_id


def macro(rows, labels):
    """Use one fixed observed label union, with zero for absent classes."""
    support = Counter(row["human_label"] for row in rows)
    predicted = Counter(prediction(row) for row in rows if prediction(row) is not None)
    true_positive = Counter(row["human_label"] for row in rows if prediction(row) == row["human_label"])
    per_label = []
    for label in labels:
        tp, human_n, predicted_n = true_positive[label], support[label], predicted[label]
        denominator = human_n + predicted_n
        f1 = 2 * tp / denominator if denominator else 0.0
        per_label.append({"label_id": label, "support": human_n, "predicted": predicted_n,
                          "tp": tp, "fp": predicted_n - tp, "fn": human_n - tp,
                          "f1_numerator": 2 * tp, "f1_denominator": denominator, "f1": f1})
    numerator = sum(row["f1"] for row in per_label)
    return {"value": numerator / len(labels), "numerator": numerator,
            "denominator": len(labels), "denominator_unit": "labels", "per_label": per_label}


def compare_scores(baseline, candidate):
    left = checked_rows(baseline, "Baseline")
    right = checked_rows(candidate, "Candidate")
    if set(left) != set(right):
        raise ValueError("Baseline and candidate sample membership differs")
    ids = sorted(left)
    for sid in ids:
        a, b = left[sid], right[sid]
        if a["record_id"] != b["record_id"] or a.get("component") != b.get("component"):
            raise ValueError(f"Frozen record identity differs: {sid}")
        if a["human_label"] != b["human_label"]:
            raise ValueError(f"Gold human label differs: {sid}")
    a_rows, b_rows = [left[sid] for sid in ids], [right[sid] for sid in ids]
    a_correct = np.array([prediction(row) == row["human_label"] for row in a_rows], dtype=np.int8)
    b_correct = np.array([prediction(row) == row["human_label"] for row in b_rows], dtype=np.int8)
    differences = b_correct - a_correct
    rng = np.random.default_rng(BOOTSTRAP_SEED)
    indices = rng.integers(EXPECTED_ROWS, size=(BOOTSTRAP_DRAWS, EXPECTED_ROWS))
    draws = differences[indices].mean(axis=1)
    ci = [float(value) for value in np.quantile(draws, [0.025, 0.975], method="linear")]
    a_labels = {row["human_label"] for row in a_rows} | {prediction(row) for row in a_rows if prediction(row) is not None}
    b_labels = {row["human_label"] for row in b_rows} | {prediction(row) for row in b_rows if prediction(row) is not None}
    common_labels = sorted(a_labels | b_labels)
    a_common, b_common = macro(a_rows, common_labels), macro(b_rows, common_labels)
    a_own, b_own = macro(a_rows, sorted(a_labels)), macro(b_rows, sorted(b_labels))
    for own, original in ((a_own, baseline), (b_own, candidate)):
        own["recorded_value"] = original.get("macro_f1")
        own["recorded_label_count"] = original.get("macro_f1_label_count")
        own["recorded_ci95"] = original.get("macro_f1_ci95")
    counts = {
        "improved": int((differences == 1).sum()), "worsened": int((differences == -1).sum()),
        "tied_correct": int(((a_correct == 1) & (b_correct == 1)).sum()),
        "tied_incorrect": int(((a_correct == 0) & (b_correct == 0)).sum()),
    }
    counts["tied"] = counts["tied_correct"] + counts["tied_incorrect"]
    required = math.ceil(0.90 * EXPECTED_ROWS)
    return {
        "schema_version": 1,
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "evaluation_only": True,
        "paired_rows": EXPECTED_ROWS,
        "sample_ids": ids,
        "baseline_accuracy": {"numerator": int(a_correct.sum()), "denominator": EXPECTED_ROWS,
                              "value": float(a_correct.mean()), "ci95": baseline.get("accuracy_ci95")},
        "candidate_accuracy": {"numerator": int(b_correct.sum()), "denominator": EXPECTED_ROWS,
                               "value": float(b_correct.mean()), "ci95": candidate.get("accuracy_ci95")},
        "missing_predictions": {
            name: {"numerator": sum(prediction(row) is None for row in rows), "denominator": EXPECTED_ROWS}
            for name, rows in (("baseline", a_rows), ("candidate", b_rows))
        },
        "paired_accuracy_difference": {
            "direction": "candidate minus baseline", "numerator": int(differences.sum()),
            "denominator": EXPECTED_ROWS, "value": float(differences.mean()), "ci95": ci,
            "percentage_points": float(differences.mean()) * 100,
            "ci95_percentage_points": [value * 100 for value in ci],
        },
        "paired_counts": {name: {"numerator": count, "denominator": EXPECTED_ROWS} for name, count in counts.items()},
        "bootstrap": {"method": "Paired-row resampling with replacement, retaining each baseline/candidate pair",
                      "seed": BOOTSTRAP_SEED, "draws": BOOTSTRAP_DRAWS, "rows_per_draw": EXPECTED_ROWS,
                      "generator": "numpy.random.default_rng (PCG64)",
                      "interval": "95% percentile; linear quantile interpolation"},
        "target": {"accuracy": 0.90, "required_correct": required, "denominator": EXPECTED_ROWS,
                   "candidate_correct": int(b_correct.sum()), "met": int(b_correct.sum()) >= required,
                   "criterion": "Observed full-sample point estimate only; not a guarantee or generalization claim"},
        "common_label_macro_f1": {
            "labels": common_labels, "label_count": len(common_labels),
            "baseline": a_common, "candidate": b_common,
            "candidate_minus_baseline": b_common["value"] - a_common["value"],
            "definition": "Both models use the same fixed observed human/baseline/candidate label union. Missing predictions are false negatives; absent and prediction-only classes contribute zero F1.",
        },
        "own_union_macro_f1_diagnostics": {
            "baseline": a_own, "candidate": b_own,
            "limits": "Different label denominators; compare improvement using the common-label macro above.",
        },
        "limits": [
            "Opened historical benchmark, not a fresh holdout or prospective estimate.",
            "Human-review independence and correctness retain the limitations recorded with the original reviews.",
            "These results are produced after prediction and scoring; never feed them into candidate fitting, calibration, feature selection or dashboard accuracy.",
        ],
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baseline", type=Path, default=DEFAULT_BASELINE)
    parser.add_argument("--candidate", type=Path, default=DEFAULT_CANDIDATE)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = parser.parse_args(argv)
    if args.out.exists():
        raise ValueError("Comparison output already exists; preserve the original result")
    baseline_bytes, candidate_bytes = args.baseline.read_bytes(), args.candidate.read_bytes()
    result = compare_scores(json.loads(baseline_bytes), json.loads(candidate_bytes))
    result["source_artifacts"] = {
        name: {"path": str(path), "sha256": hashlib.sha256(content).hexdigest()}
        for name, path, content in (("baseline", args.baseline, baseline_bytes), ("candidate", args.candidate, candidate_bytes))
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("x") as handle:
        handle.write(json.dumps(result, indent=2, ensure_ascii=False) + "\n")
    for name in ("baseline", "candidate"):
        accuracy = result[f"{name}_accuracy"]
        print(f"{name}: {accuracy['numerator']}/{accuracy['denominator']} = {accuracy['value']:.1%}")
    delta = result["paired_accuracy_difference"]
    print(f"Paired difference: {delta['numerator']}/{delta['denominator']} = {delta['percentage_points']:+.2f} percentage points; 95% CI {delta['ci95_percentage_points']}")
    counts = result["paired_counts"]
    print("; ".join(f"{name}: {counts[name]['numerator']}/{EXPECTED_ROWS}" for name in ("improved", "worsened", "tied")))
    common = result["common_label_macro_f1"]
    print(f"Common-label macro F1 over {common['label_count']} labels: baseline {common['baseline']['value']:.6f}; candidate {common['candidate']['value']:.6f}")
    print(f"90% point-estimate target: {'met' if result['target']['met'] else 'not met'}; saved {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
