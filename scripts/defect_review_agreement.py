"""Compare preserved human reviews before adjudication; never score a model.

python -m scripts.defect_review_agreement

The later selected 50-row assignment is reported descriptively and is not
represented as preregistered before Manish's review began.
"""
from collections import Counter
from datetime import datetime, timezone
import json
from pathlib import Path
import random

import numpy as np

from scripts.defect_accuracy import file_sha, immutable_sample_hash, load_sample
from scripts.defect_review import SAMPLE
from scripts.public_replay import ROOT

ROUND = ROOT / "reports/improvement/human_reviews/round1"
SEED = 20261102
DRAWS = 10000


def read_review(path, sample):
    data = json.loads(path.read_text())
    if data.get("sample_hash") != immutable_sample_hash(sample):
        raise ValueError("Review belongs to a different sample")
    if data.get("annotation_source") != "human" or data.get("attestation") is not True:
        raise ValueError("Explicit human-review attestation is required")
    if not str(data.get("reviewer") or "").strip():
        raise ValueError("Reviewer name is required")
    by_id = sample.set_index("sample_id")
    reviews = {}
    for row in data.get("reviews", []):
        sid = row.get("sample_id")
        if sid not in by_id.index or sid in reviews:
            raise ValueError("Unknown or duplicate review identity")
        if row.get("label") not in by_id.loc[sid, "allowed_label_ids"].split(";"):
            raise ValueError("Review label is outside the frozen taxonomy")
        reviews[sid] = row
    return data, reviews


def statistics(pairs):
    n = len(pairs)
    a = Counter(left for left, _ in pairs)
    b = Counter(right for _, right in pairs)
    agreements = sum(left == right for left, right in pairs)
    observed = agreements / n
    expected = sum(a[label] * b[label] for label in set(a) | set(b)) / (n * n)
    kappa = (observed - expected) / (1 - expected) if expected < 1 else None
    return agreements, observed, expected, kappa


def interval(values):
    return [float(v) for v in np.quantile(values, [0.025, 0.975], method="linear")] if values else None


def compare(ids, a, b, labels, *, design):
    if not ids or any(sid not in a or sid not in b for sid in ids):
        raise ValueError("Every comparison ID must have both original human reviews")
    pairs = [(a[sid]["label"], b[sid]["label"]) for sid in ids]
    n = len(pairs)
    agreements, observed, expected, kappa = statistics(pairs)
    rng = random.Random(SEED)
    raw_draws, kappa_draws = [], []
    for _ in range(DRAWS):
        resampled = [pairs[rng.randrange(n)] for _ in range(n)]
        _, raw, _, coefficient = statistics(resampled)
        raw_draws.append(raw)
        if coefficient is not None:
            kappa_draws.append(coefficient)
    prevalence = {"primary": [], "second": []}
    disagreement = []
    for label in labels:
        left_count = sum(left == label for left, _ in pairs)
        right_count = sum(right == label for _, right in pairs)
        for reviewer, count in (("primary", left_count), ("second", right_count)):
            prevalence[reviewer].append({"label": label, "numerator": count, "denominator": n, "value": count / n})
        union = sum(left == label or right == label for left, right in pairs)
        differing = sum(left != right and (left == label or right == label) for left, right in pairs)
        disagreement.append({
            "label": label,
            "numerator": differing,
            "denominator": union,
            "value": differing / union if union else None,
            "denominator_definition": "Paired rows where either reviewer chose this label",
            "primary_label_disagreements": {
                "numerator": sum(left == label and left != right for left, right in pairs),
                "denominator": left_count,
            },
            "second_label_disagreements": {
                "numerator": sum(right == label and left != right for left, right in pairs),
                "denominator": right_count,
            },
        })
    differences = [
        {"sample_id": sid, "primary_review": a[sid], "second_review": b[sid]}
        for sid in ids if a[sid]["label"] != b[sid]["label"]
    ]
    return {
        "design": design,
        "sample_ids": ids,
        "paired_rows": n,
        "raw_agreement": {"numerator": agreements, "denominator": n, "value": observed, "ci95": interval(raw_draws)},
        "cohens_kappa": {
            "value": kappa, "paired_rows": n, "expected_chance_agreement": expected,
            "ci95": interval(kappa_draws),
        },
        "bootstrap": {
            "method": "Paired-row resampling with replacement, preserving each original review pair",
            "interval": "95% percentile; linear quantile interpolation",
            "seed": SEED,
            "draws": DRAWS,
            "rows_per_draw": n,
            "raw_valid_draws": {"numerator": len(raw_draws), "denominator": DRAWS},
            "kappa_valid_draws": {"numerator": len(kappa_draws), "denominator": DRAWS},
            "undefined_kappa_draws": {"numerator": DRAWS - len(kappa_draws), "denominator": DRAWS},
        },
        "label_prevalence": prevalence,
        "per_label_disagreement": disagreement,
        "disagreement_count": {"numerator": len(differences), "denominator": n},
        "disagreements": differences,
        "identical_notes": {"numerator": sum(a[sid].get("notes") == b[sid].get("notes") for sid in ids), "denominator": n},
    }


def main():
    destination = ROUND / "agreement_before_adjudication.json"
    if destination.exists():
        raise ValueError("Agreement artifact already exists; preserve the original pre-adjudication result")
    sample = load_sample(SAMPLE)
    if file_sha(SAMPLE) != "7b0bf958b8756b51e3a3d550b8611f8182b56839b20e922b35abcc67e3aba1a4":
        raise ValueError("Frozen sample changed")
    primary_path = ROUND / "primary_review_export.json"
    second_path = ROUND / "second_review/manish/original_review_export.json"
    primary, a = read_review(primary_path, sample)
    second, b = read_review(second_path, sample)
    if primary["reviewer"] == second["reviewer"]:
        raise ValueError("Two distinct named reviewers are required")
    ids = sorted(sample.sample_id.tolist())
    if set(a) != set(ids) or set(b) != set(ids):
        raise ValueError("Full-sample comparison requires both complete original reviews")
    assignment_path = ROUND / "second_review/preregistered_ids.json"
    assignment = json.loads(assignment_path.read_text())
    labels = sorted({row["label"] for row in list(a.values()) + list(b.values())})
    result = {
        "schema_version": 1,
        "computed_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "stage": "before_adjudication",
        "evaluation_only": True,
        "model_accuracy_computed": False,
        "source_reviews": [
            {"role": role, "reviewer": data["reviewer"], "exported_at": data.get("exported_at"),
             "path": str(path.relative_to(ROOT)), "sha256": file_sha(path)}
            for role, data, path in (("primary", primary, primary_path), ("second", second, second_path))
        ],
        "full_sample": compare(ids, a, b, labels, design="All 300 frozen sample IDs; user reports assigning the entire set before Manish began; contemporaneous second-review assignment record unavailable."),
        "later_selected_50": compare(assignment["sample_ids"], a, b, labels, design="Descriptive only: these 50 IDs were recorded on 2 November after Manish reportedly began on 1 November; not prospectively preregistered for his review."),
        "subset_manifest": {"path": str(assignment_path.relative_to(ROOT)), "sha256": file_sha(assignment_path), "registered_at": assignment["registered_at"]},
        "review_arrays_identical": primary["reviews"] == second["reviews"],
        "limits": [
            "Identical exported labels and notes do not independently establish blinded review or correctness.",
            "The user confirms a blank independent review and an assignment of all 300 records; this is recorded as user-reported provenance.",
            "Bootstrap intervals condition on the supplied review pairs and do not capture copying, shared interpretation errors, or uncertainty about review independence.",
            "No consensus or adjudicated labels are generated by this comparison.",
        ],
    }
    with destination.open("x") as f:
        f.write(json.dumps(result, indent=2, ensure_ascii=False) + "\n")
    for name in ("full_sample", "later_selected_50"):
        value = result[name]
        raw = value["raw_agreement"]
        kappa = value["cohens_kappa"]
        print(f"{name}: raw agreement {raw['numerator']}/{raw['denominator']} = {raw['value']:.1%}, 95% paired-bootstrap CI {raw['ci95']}; Cohen's kappa {kappa['value']} on {value['paired_rows']} paired rows, 95% CI {kappa['ci95']}")
    print(f"Saved pre-adjudication agreement: {destination.relative_to(ROOT)}; no model accuracy scoring")


if __name__ == "__main__":
    main()
