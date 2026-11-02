"""Freeze a 50-ID assignment and build an independent, offline review page.

python -m scripts.defect_second_review

Only the original blank sample is read. Primary answers and predictions are
never used to select the assignment or included in the page.
"""
from datetime import datetime, timezone
import json
from pathlib import Path
import random

from scripts.defect_accuracy import file_sha, immutable_sample_hash, load_sample
from scripts.defect_review import SAMPLE
from scripts.public_replay import ROOT
from src.security.pii import redact_pii

DESTINATION = ROOT / "reports/improvement/human_reviews/round1/second_review"
COUNT = 50
SEED = 20261102
DISPLAY_FIELDS = (
    "sample_id", "component", "year", "make", "model", "datea", "narrative",
    "allowed_label_ids", "allowed_label_text",
)


def build(destination: Path = DESTINATION):
    if destination.exists():
        raise ValueError("Second-review assignment already exists; preserve its preregistered IDs")
    before = SAMPLE.read_bytes()
    sample = load_sample(SAMPLE)
    frozen_manifest = json.loads((ROOT / "reports/defect/sample_manifest.json").read_text())
    if file_sha(SAMPLE) != frozen_manifest["csv_sha256"]:
        raise ValueError("Frozen sample differs from its manifest")
    if len(sample) != 300 or sample["label"].ne("").any() or sample["notes"].ne("").any():
        raise ValueError("Second-review page requires the original blank 300-row sample")
    template_path = ROOT / "scripts/templates/defect_second_review.html"
    template = template_path.read_text()
    if template.count("__REVIEW_DATA__") != 1:
        raise ValueError("Review template must have exactly one data placeholder")

    # Freeze IDs without reading primary labels or model predictions.
    ids = random.Random(SEED).sample(sorted(sample.sample_id.tolist()), COUNT)
    registered_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    manifest = {
        "schema_version": 1,
        "packet_id": "round1-second-review-v1",
        "status": "preregistered_before_second_review",
        "registered_at": registered_at,
        "reviewer_role": "second_blinded_review",
        "sample_size": len(sample),
        "assigned_count": COUNT,
        "sample_ids": ids,
        "selection": {
            "algorithm": "random.Random(seed).sample(sorted(sample_ids), assigned_count)",
            "seed": SEED,
            "inputs": ["sample_id only"],
            "primary_labels_used": False,
            "model_predictions_used": False,
            "note": "The recorded ID list and order are authoritative; do not reselect after review.",
        },
        "source": {
            "path": str(SAMPLE.relative_to(ROOT)),
            "csv_sha256": file_sha(SAMPLE),
            "immutable_rows_sha256": immutable_sample_hash(sample),
        },
        "evaluation_only": True,
        "prohibited_uses": ["fitting", "calibration", "feature selection", "dashboard accuracy"],
        "review_method": "Independent named human; primary answers and model outputs hidden; source narratives with common PII redacted.",
        "protocol": "reports/improvement/labeling_guide.md",
    }
    destination.mkdir(parents=True)
    manifest_path = destination / "preregistered_ids.json"
    with manifest_path.open("x") as f:
        f.write(json.dumps(manifest, indent=2) + "\n")

    by_id = sample.set_index("sample_id", drop=False)
    rows = by_id.loc[ids, list(DISPLAY_FIELDS)].to_dict("records")
    for row in rows:
        row["narrative"] = redact_pii(row["narrative"])
    data = {
        "packet_id": manifest["packet_id"],
        "sample_hash": manifest["source"]["immutable_rows_sha256"],
        "preregistration_hash": file_sha(manifest_path),
        "rows": rows,
    }
    page_path = destination / "second_review.html"
    with page_path.open("x") as f:
        f.write(template.replace("__REVIEW_DATA__", json.dumps(data, ensure_ascii=False).replace("<", "\\u003c")))
    hashes = {
        "registered_at": registered_at,
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "artifacts": {str(path.relative_to(ROOT)): file_sha(path) for path in (manifest_path, page_path, template_path)},
        "frozen_sample_unchanged": SAMPLE.read_bytes() == before,
    }
    if not hashes["frozen_sample_unchanged"]:
        raise ValueError("Frozen sample changed during page preparation")
    with (destination / "packet_hashes.json").open("x") as f:
        f.write(json.dumps(hashes, indent=2) + "\n")
    print(f"Pre-registered {COUNT}/{len(sample)} IDs for the second human review: {manifest_path.relative_to(ROOT)}")
    print(f"Prepared blank second-review page: {page_path.relative_to(ROOT)}")
    return page_path


if __name__ == "__main__":
    build()
