"""Prepare and assemble a bounded, reproducible repair of the partial experiment.

No model calls. Classify the emitted pending inputs using defect_classify, then
assemble. The original experiment and human label sheet are never overwritten.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import pandas as pd

from scripts.defect_prepare_inputs import _iter_recall_rows, file_sha256
from scripts.defect_classify import PROMPT_VERSION, load_complaints, load_recalls, export, open_cache

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data/defect/repair"
OUT = ROOT / "reports/defect/repair"
MAKES = ["FORD", "HONDA", "HYUNDAI", "KIA", "TOYOTA"]
MODEL = "meta-models/muse-spark-open-1026"


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n")


def scope(df):
    return df[df.make.isin(MAKES) & df.year.between(2015, 2024) & df.component.eq("FUEL SYSTEM")].copy()


def prepare(recall_zip: Path):
    protocol_path = OUT / "protocol.json"
    if protocol_path.exists():
        raise ValueError("Repair protocol already exists; use its pinned inputs, do not silently replace it")
    DATA.mkdir(parents=True, exist_ok=True)
    original = ROOT / "reports/defect"
    tax = json.loads((original / "taxonomy.json").read_text())
    source_manifest = json.loads((ROOT / "data/defect/defect_input_manifest.json").read_text())
    if file_sha256(recall_zip) != source_manifest["sources"]["recalls"]["sha256"]:
        raise ValueError("Recall ZIP differs from the original frozen source")
    all_c = pd.read_parquet(ROOT / "data/defect/complaints.parquet")
    all_c["record_id"] = all_c.odino.astype(str) + "|" + all_c.component
    complaints = scope(all_c)
    recalls_raw, _ = _iter_recall_rows(recall_zip, limit=0, preserve_scopes=True)
    recalls = scope(pd.DataFrame(recalls_raw))
    recalls = recalls[recalls.rcl_type.eq("V") & recalls.rcdate.between("2015-01-01", "2024-12-31")]
    sample = pd.read_csv(original / "defect_label_sample_300.csv", dtype=str, keep_default_na=False)
    sample_ids = set(sample.odino + "|" + sample.component)
    if not sample_ids <= set(all_c.record_id):
        raise ValueError("Human sample contains records absent from the source snapshot")
    model_inputs = all_c[all_c.record_id.isin(set(complaints.record_id) | sample_ids)].copy()
    known = pd.read_parquet(original / "classifications.parquet")
    good = known[(known.status == "ok") & (known.model == MODEL)
                 & (known.prompt_version == PROMPT_VERSION) & (known.taxonomy_sha256 == tax["sha256"])]
    pending = model_inputs[~model_inputs.record_id.isin(good.record_id)]
    inputs = {"complaints": complaints.drop(columns="record_id"),
              "recall_scopes": recalls,
              "classification_inputs": model_inputs.drop(columns="record_id"),
              "pending_complaints": pending.drop(columns="record_id")}
    for name, df in inputs.items():
        df.to_parquet(DATA / f"{name}.parquet", index=False)
    protocol = {
        "version": 2,
        "status": "retrospective_reanalysis_after_inspecting_original_test_results",
        "scope": {"makes": MAKES, "model_years": [2015, 2024], "components": ["FUEL SYSTEM"],
                  "recall_type": "V", "complaint_window": ["2015-01-01", "2024-12-31"]},
        "scope_reason": "Restore the originally documented five-make/model-year scope. Fuel system is the only component with existing classifier coverage; scope was chosen for completion cost, not recall outcomes.",
        "train_window": ["2015-01-01", "2020-12-31"],
        "evaluation_window": ["2021-01-01", "2024-12-31"],
        "classifier": {"model": MODEL, "prompt_version": PROMPT_VERSION, "taxonomy_sha256": tax["sha256"]},
        "counts": {"complaints": len(complaints), "recall_scope_rows": len(recalls),
                   "campaigns": recalls.campno.nunique(), "classification_inputs": len(model_inputs),
                   "pending_classification": len(pending), "human_sample": len(sample)},
        "inputs": {name: {"path": str((DATA / f"{name}.parquet").relative_to(ROOT)),
                           "sha256": file_sha256(DATA / f"{name}.parquet")} for name in inputs},
        "original_sources": {"recall_zip_sha256": file_sha256(recall_zip),
                             "complaints_sha256": file_sha256(ROOT / "data/defect/complaints.parquet"),
                             "classifications_sha256": file_sha256(original / "classifications.parquet"),
                             "recall_labels_sha256": file_sha256(original / "recall_labels.parquet")},
        "comparison": {"matching": "make + component + specific defect; other_unclear never establishes a defect match",
                       "availability": "weekly counts become available on the next Monday; minimum actionable lead 7 days",
                       "confirmation_horizon_days": 364,
                       "baselines": ["original weekly thresholds", "rolling count", "seeded random"],
                       "budget": "same number of alert episodes, with the same per-slice cooldown",
                       "random_draws": 100,
                       "selection": "tune only on 2015-2020; freeze configuration and hashes before reanalysis",
                       "limitations": ["2021-2024 was already examined; this is not a fresh holdout",
                                       "model-labelled recalls are not independent human truth",
                                       "matching is at make/defect level, not proof of physical defect identity",
                                       "2026 model may know historical recalls; retrospective lead time is not prospective prediction",
                                       "human classification accuracy stays unavailable until human review"]}}
    write_json(protocol_path, protocol)
    print(json.dumps(protocol["counts"], indent=2))


def assemble():
    p = json.loads((OUT / "protocol.json").read_text())
    for spec in p["inputs"].values():
        if file_sha256(ROOT / spec["path"]) != spec["sha256"]:
            raise ValueError("Prepared input changed after protocol freeze")
    con = open_cache(ROOT / "reports/defect/cache/classifications.sqlite")
    complaints = load_complaints(DATA / "classification_inputs.parquet", "2015-01-01", "2024-12-31")
    # Model calls are deduplicated by description; keep complete scope elsewhere.
    scopes = pd.read_parquet(DATA / "recall_scopes.parquet")
    descriptions = scopes.drop_duplicates(["campno", "component", "desc_defect"])
    desc_path = DATA / "recall_descriptions.parquet"
    descriptions.to_parquet(desc_path, index=False)
    result = export(con, model=MODEL, taxonomy_sha=p["classifier"]["taxonomy_sha256"],
                    complaints_in=complaints, recalls_in=load_recalls(desc_path), out_dir=OUT)
    con.close()
    print(json.dumps(result, indent=2))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("phase", choices=["prepare", "assemble"])
    parser.add_argument("--recalls-zip", type=Path)
    args = parser.parse_args()
    if args.phase == "prepare":
        if not args.recalls_zip:
            parser.error("prepare requires the original --recalls-zip")
        prepare(args.recalls_zip)
    else:
        assemble()


if __name__ == "__main__":
    main()
