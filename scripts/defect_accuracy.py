"""Score the Muse Spark defect classifier against the human 300-row sample.

The 300-row CSV (``reports/defect/defect_label_sample_300.csv``) was exported
with blank ``label`` cells and frozen with a SHA-256. A human fills the
``label`` column with one of the row's ``allowed_label_ids``. This script joins
those labels to the classifier output and reports:

* overall accuracy on rows that have both a valid human label and a model label;
* accuracy on rows whose human label is a specific defect (not ``other/unclear``);
* per-label precision, recall, F1 and support;
* a human-label x model-label confusion matrix;
* how many rows are unlabelled, invalid, or have no model output.

It never fills a human label and never treats model output as ground truth.
Missing model output is counted separately, not silently dropped from the
denominator without a note.

    python -m scripts.defect_accuracy
    python -m scripts.defect_accuracy --require-complete   # final run
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

DEFECT_DIR = REPO_ROOT / "reports" / "defect"
DEFAULT_CSV = DEFECT_DIR / "defect_label_sample_300.csv"
DEFAULT_CLASSIFICATIONS = DEFECT_DIR / "classifications.parquet"
DEFAULT_MANIFEST = DEFECT_DIR / "sample_manifest.json"
DEFAULT_OUT = DEFECT_DIR / "accuracy.json"
OTHER_ID = "other_unclear"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def file_sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def norm_label(value: Any) -> str:
    return " ".join(str(value or "").strip().split()).lower()


def load_sample(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path, dtype=str, keep_default_na=False, encoding="utf-8-sig")
    required = {"sample_id", "odino", "component", "allowed_label_ids", "allowed_label_text", "label"}
    missing = required - set(df.columns)
    if missing:
        raise SystemExit(f"sample CSV is missing columns: {sorted(missing)}")
    for col in required:
        df[col] = df[col].astype(str).str.strip()
    if df.sample_id.duplicated().any() or df.duplicated(["odino", "component"]).any():
        raise SystemExit("sample CSV contains duplicate sample or complaint identities")
    return df


def immutable_sample_hash(df: pd.DataFrame) -> str:
    frozen = df.drop(columns=["label", "notes"], errors="ignore").sort_values("sample_id")
    return hashlib.sha256(json.dumps(frozen.to_dict("records"), sort_keys=True,
                                    ensure_ascii=False, separators=(",", ":")).encode()).hexdigest()


def label_lookup(allowed_ids: str, allowed_text: str) -> tuple[dict[str, str], dict[str, str]]:
    ids = [x.strip() for x in str(allowed_ids or "").split(";") if x.strip()]
    by_id = {x: x for x in ids}
    by_text: dict[str, str] = {}
    for chunk in str(allowed_text or "").split(";"):
        if "=" not in chunk:
            continue
        left, right = (x.strip() for x in chunk.split("=", 1))
        # The exporter writes id=display text. Accept legacy display=id too,
        # but never allow arbitrary text to introduce an out-of-taxonomy ID.
        label_id, text = (left, right) if left in by_id else (right, left)
        if label_id in by_id:
            by_text[norm_label(text)] = label_id
    # Accept the human spelling of the always-present fallback.
    if OTHER_ID in by_id:
        for alias in ("other/unclear", "other unclear", "other"):
            by_text.setdefault(alias, OTHER_ID)
    return by_id, by_text


def resolve_human_label(raw: str, allowed_ids: str, allowed_text: str) -> tuple[str | None, str]:
    """Return (label_id, reason). reason is 'blank', 'ok', or 'invalid'."""
    text = " ".join(str(raw or "").strip().split())
    if not text:
        return None, "blank"
    by_id, by_text = label_lookup(allowed_ids, allowed_text)
    if text in by_id:
        return by_id[text], "ok"
    low = norm_label(text)
    for label_id, canonical in by_id.items():
        if norm_label(label_id) == low or norm_label(canonical) == low:
            return label_id, "ok"
    if low in by_text:
        return by_text[low], "ok"
    return None, "invalid"


def ratio(num: int, den: int) -> float | None:
    return (num / den) if den else None


def safe_float(value: Any) -> float | None:
    try:
        out = float(value)
    except (TypeError, ValueError):
        return None
    return out if math.isfinite(out) else None


def load_classifications(path: Path) -> pd.DataFrame:
    df = pd.read_parquet(path)
    required = {"record_id", "label_id", "status", "component", "model", "prompt_version", "taxonomy_sha256"}
    missing = required - set(df.columns)
    if missing:
        raise SystemExit(f"classifications parquet is missing columns: {sorted(missing)}")
    df["record_id"] = df["record_id"].astype(str).str.strip()
    df["component"] = df["component"].astype(str).str.strip().str.upper()
    if df["record_id"].duplicated().any():
        dup = int(df["record_id"].duplicated().sum())
        raise SystemExit(f"classifications parquet has {dup} duplicate record_id rows; refusing to guess which is right")
    return df


def build_metrics(sample: pd.DataFrame, clf: pd.DataFrame, *, manifest: dict[str, Any], csv_path: Path,
                  clf_path: Path, manifest_path: Path) -> dict[str, Any]:
    c = clf.set_index("record_id", drop=False)
    rows: list[dict[str, Any]] = []
    invalid: list[dict[str, Any]] = []
    for r in sample.itertuples():
        record_id = f"{str(r.odino).strip()}|{r.component.strip()}"
        human, why = resolve_human_label(r.label, r.allowed_label_ids, r.allowed_label_text)
        model_row = c.loc[record_id] if record_id in c.index else None
        model_label = None
        model_status = "missing"
        model_confidence = None
        if model_row is not None:
            model_status = str(model_row.get("status") or "")
            if model_status == "ok":
                candidate = str(model_row.get("label_id") or "").strip()
                if candidate:
                    model_label = candidate
            model_confidence = safe_float(model_row.get("confidence"))
        item = {
            "sample_id": str(r.sample_id),
            "record_id": record_id,
            "component": r.component.strip(),
            "human_label": human,
            "human_reason": why,
            "model_label": model_label,
            "model_status": model_status,
            "model_confidence": model_confidence,
        }
        rows.append(item)
        if why == "invalid":
            invalid.append({"sample_id": item["sample_id"], "record_id": record_id,
                            "component": item["component"], "raw_label": str(r.label)})

    labelled = [x for x in rows if x["human_label"] is not None]
    scored = [x for x in labelled if x["model_label"] is not None]
    missing_model = [x for x in labelled if x["model_label"] is None]
    correct = sum(1 for x in scored if x["human_label"] == x["model_label"])
    specific = [x for x in scored if x["human_label"] != OTHER_ID]
    specific_correct = sum(1 for x in specific if x["human_label"] == x["model_label"])
    other = [x for x in scored if x["human_label"] == OTHER_ID]
    other_correct = sum(1 for x in other if x["human_label"] == x["model_label"])

    human_counts = Counter(x["human_label"] for x in labelled)
    model_counts = Counter(x["model_label"] for x in scored)
    labels = sorted(set(human_counts) | set(model_counts) | {OTHER_ID})
    labels = [x for x in labels if x != OTHER_ID] + [OTHER_ID]

    per_label = []
    for label in labels:
        support = sum(1 for x in scored if x["human_label"] == label)
        predicted = sum(1 for x in scored if x["model_label"] == label)
        tp = sum(1 for x in scored if x["human_label"] == label and x["model_label"] == label)
        fp = predicted - tp
        fn = support - tp
        precision = ratio(tp, predicted)
        recall = ratio(tp, support)
        f1 = (2 * tp / (2 * tp + fp + fn)) if 2 * tp + fp + fn else None
        per_label.append({
            "label_id": label,
            "support": support,
            "predicted": predicted,
            "tp": tp,
            "fp": fp,
            "fn": fn,
            "precision": precision,
            "recall": recall,
            "f1": f1,
        })
    per_label.sort(key=lambda x: (-x["support"], -x["predicted"], x["label_id"]))

    confusion: dict[str, dict[str, int]] = {h: {m: 0 for m in labels} for h in labels}
    for x in scored:
        confusion[x["human_label"]][x["model_label"]] += 1

    model_versions = sorted({str(x) for x in clf["model"].dropna().unique()})
    prompt_versions = sorted({str(x) for x in clf["prompt_version"].dropna().unique()})
    taxonomy_shas = sorted({str(x) for x in clf["taxonomy_sha256"].dropna().unique()})
    return {
        "generated_at": utc_now(),
        "sample_size": int(len(sample)),
        "labelled": int(len(labelled)),
        "invalid_human_labels": int(len(invalid)),
        "invalid_rows": invalid,
        "model_ok": int(sum(1 for x in rows if x["model_label"] is not None)),
        "model_missing": int(len(missing_model)),
        "model_missing_rows": [{"sample_id": x["sample_id"], "record_id": x["record_id"],
                                "model_status": x["model_status"]} for x in missing_model],
        "scored": int(len(scored)),
        "correct": int(correct),
        "accuracy": ratio(correct, len(scored)),
        "accuracy_all_labelled": ratio(correct, len(labelled)),
        "macro_f1": (sum(x["f1"] or 0 for x in per_label if x["support"]) /
                     sum(bool(x["support"]) for x in per_label)) if scored else None,
        "always_other_unclear_accuracy": ratio(len(other), len(scored)),
        "specific_n": int(len(specific)),
        "specific_correct": int(specific_correct),
        "specific_accuracy": ratio(specific_correct, len(specific)),
        "other_unclear_n": int(len(other)),
        "other_unclear_correct": int(other_correct),
        "other_unclear_accuracy": ratio(other_correct, len(other)),
        "human_label_counts": dict(sorted(human_counts.items())),
        "model_label_counts": dict(sorted(model_counts.items())),
        "per_label": per_label,
        "labels": labels,
        "confusion": confusion,
        "rows": rows,
        "sample": {
            "path": str(csv_path.relative_to(REPO_ROOT)) if csv_path.is_relative_to(REPO_ROOT) else str(csv_path),
            "csv_sha256": file_sha(csv_path),
            "blank_csv_sha256": manifest.get("csv_sha256"),
            "manifest_path": str(manifest_path.relative_to(REPO_ROOT))
            if manifest_path.is_relative_to(REPO_ROOT) else str(manifest_path),
            "seed": manifest.get("seed"),
            "requested": manifest.get("requested"),
            "frame": manifest.get("frame"),
            "taxonomy_sha256": manifest.get("taxonomy_sha256"),
        },
        "classifier": {
            "path": str(clf_path.relative_to(REPO_ROOT)) if clf_path.is_relative_to(REPO_ROOT) else str(clf_path),
            "parquet_sha256": file_sha(clf_path),
            "models": model_versions,
            "prompt_versions": prompt_versions,
            "taxonomy_sha256s": taxonomy_shas,
        },
        "definitions": {
            "accuracy": "correct / scored; scored = valid human label AND model status ok with a label",
            "accuracy_all_labelled": "correct / labelled; a missing model label counts as wrong",
            "specific_accuracy": "correct / specific_n; specific_n = scored rows whose human label is not other/unclear",
            "precision": "tp / predicted for that label among scored rows",
            "recall": "tp / support for that label among scored rows",
            "confusion": "rows = human label, columns = Muse Spark label, both restricted to scored rows",
        },
    }


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Score the defect classifier against the human 300-row sample")
    p.add_argument("--csv", default=str(DEFAULT_CSV))
    p.add_argument("--classifications", default=str(DEFAULT_CLASSIFICATIONS))
    p.add_argument("--manifest", default=str(DEFAULT_MANIFEST))
    p.add_argument("--out", default=str(DEFAULT_OUT))
    p.add_argument("--require-complete", action="store_true",
                   help="exit 3 unless all sample rows have a valid human label and a model label")
    args = p.parse_args(argv)

    csv_path = Path(args.csv)
    clf_path = Path(args.classifications)
    manifest_path = Path(args.manifest)
    out_path = Path(args.out)
    if not csv_path.exists():
        print(f"REFUSED: sample CSV not found: {csv_path}", file=sys.stderr)
        return 3
    if not clf_path.exists():
        print(f"REFUSED: classifications parquet not found: {clf_path}", file=sys.stderr)
        return 3
    manifest = json.loads(manifest_path.read_text()) if manifest_path.exists() else {}
    sample = load_sample(csv_path)
    expected_rows = manifest.get("immutable_rows_sha256")
    if expected_rows and immutable_sample_hash(sample) != expected_rows:
        print("REFUSED: narratives, IDs, taxonomy choices, or sample membership changed", file=sys.stderr)
        return 3
    clf = load_classifications(clf_path)
    result = build_metrics(sample, clf, manifest=manifest, csv_path=csv_path, clf_path=clf_path,
                           manifest_path=manifest_path)
    if result["labelled"] == 0:
        print(json.dumps({
            "sample_size": result["sample_size"],
            "labelled": 0,
            "invalid_human_labels": result["invalid_human_labels"],
            "model_ok": result["model_ok"],
            "note": "NOT RUN: no valid human labels exist, so no accuracy result was written.",
        }, indent=2, default=str))
        print("NOT RUN: fill the sample CSV label column with allowed label IDs, then rerun", file=sys.stderr)
        return 3
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(result, indent=2, default=str), encoding="utf-8")
    print(json.dumps({
        "sample_size": result["sample_size"],
        "labelled": result["labelled"],
        "invalid_human_labels": result["invalid_human_labels"],
        "model_missing": result["model_missing"],
        "scored": result["scored"],
        "correct": result["correct"],
        "accuracy": result["accuracy"],
        "specific_accuracy": result["specific_accuracy"],
        "other_unclear_accuracy": result["other_unclear_accuracy"],
        "out": str(out_path),
    }, indent=2, default=str))
    if args.require_complete and (result["labelled"] != result["sample_size"]
                                  or result["invalid_human_labels"]
                                  or result["model_missing"]):
        print("INCOMPLETE: human labels or model output are missing; see the counts above", file=sys.stderr)
        return 3
    if result["scored"] == 0:
        print("NOT RUN: no row has both a valid human label and a model label", file=sys.stderr)
        return 3
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
