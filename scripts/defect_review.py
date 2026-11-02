"""Build a blind local human-review page, then validate its exported labels.

python -m scripts.defect_review build
python -m scripts.defect_review import --review /path/to/defect-review.json

The page contains no model predictions. Import never modifies the original
300-row sample and never accepts machine labels as human review.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from scripts.defect_accuracy import load_sample, immutable_sample_hash, file_sha
from scripts.defect_repair import ROOT, OUT, write_json

SAMPLE = ROOT / "reports/defect/defect_label_sample_300.csv"


def build():
    from src.security.pii import redact_pii
    sample = load_sample(SAMPLE)
    manifest = json.loads((ROOT / "reports/defect/sample_manifest.json").read_text())
    if file_sha(SAMPLE) != manifest["csv_sha256"]:
        raise ValueError("Original blank sample changed; review provenance before rebuilding")
    digest = immutable_sample_hash(sample)
    rows = sample.to_dict("records")
    for row in rows:
        row["narrative"] = redact_pii(row["narrative"])
    data = {"sample_hash": digest, "rows": rows}
    template = (ROOT / "scripts/templates/defect_review.html").read_text()
    html = template.replace("__REVIEW_DATA__", json.dumps(data, ensure_ascii=False).replace("<", "\\u003c"))
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "human_review.html").write_text(html)
    write_json(OUT / "review_manifest.json", manifest | {"immutable_rows_sha256": digest,
               "review_method": "blind human annotation; model predictions hidden; PII redacted on the review page"})
    print(OUT / "human_review.html")


def import_review(path: Path, *, destination: Path = OUT):
    sample = load_sample(SAMPLE)
    data = json.loads(path.read_text())
    if data.get("sample_hash") != immutable_sample_hash(sample):
        raise ValueError("Review belongs to a different sample")
    if data.get("annotation_source") != "human" or data.get("attestation") is not True:
        raise ValueError("Explicit human-review attestation is required")
    reviewer = str(data.get("reviewer") or "").strip()
    if not reviewer:
        raise ValueError("Reviewer name is required")
    by_id = sample.set_index("sample_id")
    seen = set()
    for row in data.get("reviews", []):
        sid, label = row.get("sample_id"), row.get("label")
        if sid not in by_id.index or sid in seen:
            raise ValueError("Unknown or duplicate review identity")
        if label not in by_id.loc[sid, "allowed_label_ids"].split(";"):
            raise ValueError("Review label is outside the frozen taxonomy")
        seen.add(sid)
        sample.loc[sample.sample_id == sid, "label"] = label
        sample.loc[sample.sample_id == sid, "notes"] = str(row.get("notes") or "")
    if not seen:
        raise ValueError("No reviewed labels supplied")
    dest = destination / "human_labelled.csv"
    destination.mkdir(parents=True, exist_ok=True)
    # Existing completed review is not silently replaced by a partial export.
    with dest.open("x") as f:
        sample.to_csv(f, index=False)
    write_json(destination / "human_review_provenance.json", {
        "reviewer": reviewer, "annotation_source": "human", "attestation": True,
        "reviewed": len(seen), "sample_size": len(sample), "input_sha256": file_sha(path),
        "output_sha256": file_sha(dest), "sample_hash": data["sample_hash"],
        "note": "Reviewer attestation records provenance; it does not independently verify expertise or correctness."})
    print(f"Imported {len(seen)}/{len(sample)} human labels into {dest}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("phase", choices=["build", "import"])
    parser.add_argument("--review", type=Path)
    args = parser.parse_args()
    if args.phase == "build":
        build()
    else:
        if not args.review:
            parser.error("import requires --review")
        import_review(args.review)


if __name__ == "__main__":
    main()
