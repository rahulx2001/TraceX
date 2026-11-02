"""Recover independently valid rows with the unchanged frozen validator.

Freeze this output-handling plan before gold scoring, then recover after all
scheduled evaluation batches and their exact-prompt retries finish. No labels,
gold scores, new inference, quote rewriting, or relaxed guards are used.
"""
from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

import pandas as pd

from scripts import defect_grounded_candidate as runner
from scripts.defect_grounding import validate_grounded_output

VERSION = "defect-cls-v3-grounded-row-validation"
EXPECTED_ROWS = 300
MAX_BATCH_ATTEMPTS = 2
PLAN = runner.OUT / "row_validation_plan.json"
OUTPUT = runner.OUT / "evaluation_row_validated.parquet"
MANIFEST = runner.OUT / "row_validation_manifest.json"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_new(path, data):
    with path.open("x") as handle:
        handle.write(json.dumps(data, indent=2, ensure_ascii=False) + "\n")


def recover_batch(raw, *, items, allowed_ids):
    expected = [f"c{i}" for i in range(1, len(items) + 1)]

    def reject(reason):
        return {"items": [], "row_errors": {local: reason for local in expected}, "batch_error": reason}

    if not expected:
        return reject("empty_source_batch")
    if not isinstance(raw, dict) or not isinstance(raw.get("items"), list):
        return reject("output_missing_items")
    rows = raw["items"]
    if len(rows) != len(items):
        return reject(f"wrong_item_count:{len(rows)}!={len(items)}")
    by_id = {}
    for row in rows:
        if not isinstance(row, dict):
            return reject("item_not_object")
        local = row.get("record_id")
        if not isinstance(local, str) or local not in expected:
            return reject(f"bad_record_id:{local}")
        if local in by_id:
            return reject(f"duplicate_record_id:{local}")
        by_id[local] = row
    if set(by_id) != set(expected):
        return reject("missing_record_id")
    accepted, errors = [], {}
    for index, local in enumerate(expected):
        # Copy only the local identity; quotes and every guard remain unchanged.
        copied = {**by_id[local], "record_id": "c1"}
        validated, reason = validate_grounded_output(
            {"items": [copied]}, items=[items[index]], allowed_ids=allowed_ids)
        if reason is not None:
            errors[local] = reason
        else:
            accepted.append({**validated[0], "record_id": local})
    return {"items": accepted, "row_errors": errors, "batch_error": None}


def first_valid_predictions(attempts, batches):
    """Select the chronological first strictly valid row, never by its label."""
    schedule = {batch["key"]: batch for batch in batches}
    selected, errors, count = {}, {}, Counter()
    for line_number, attempt in attempts:
        if attempt.get("phase") != "evaluation":
            continue
        key = attempt.get("batch_key")
        if key not in schedule:
            raise ValueError("Evaluation attempt does not belong to the frozen batch schedule")
        count[key] += 1
        if count[key] > MAX_BATCH_ATTEMPTS:
            raise ValueError("More than initial plus one exact-prompt retry was recorded")
        batch = schedule[key]
        recovered = recover_batch(attempt.get("raw"), items=batch["records"], allowed_ids=batch["allowed_ids"])
        by_local = {row["record_id"]: row for row in recovered["items"]}
        for index, record in enumerate(batch["records"], 1):
            local, rid = f"c{index}", record["record_id"]
            if local in by_local and rid not in selected:
                selected[rid] = {
                    **by_local[local], "raw_record_id": local,
                    "source_attempt_line": line_number, "source_batch_key": key,
                    "source_started_at": attempt.get("started_at"),
                    "source_completed_at": attempt.get("completed_at"),
                }
            if local in recovered["row_errors"]:
                errors.setdefault(rid, []).append({
                    "attempt_line": line_number, "raw_record_id": local,
                    "error": recovered["row_errors"][local], "transport_error": attempt.get("error"),
                })
    return selected, errors, count


def schedule():
    protocol = runner.verify()
    records, batches, singleton = runner.batches("evaluation")
    if len(records) != EXPECTED_ROWS or len({row["record_id"] for row in records}) != EXPECTED_ROWS:
        raise ValueError("Frozen evaluation source must preserve 300 unique records")
    if len({row["sample_id"] for row in records}) != EXPECTED_ROWS:
        raise ValueError("Frozen evaluation sample IDs are not unique")
    return protocol, records, batches, singleton


def prepare():
    if PLAN.exists():
        raise ValueError("Row-validation plan already exists; preserve its frozen policy")
    if (runner.OUT / "accuracy.json").exists():
        raise ValueError("Freeze row validation before any candidate gold scoring")
    protocol, records, batches, singleton = schedule()
    plan = {
        "schema_version": 1, "frozen_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "candidate_version": VERSION, "original_prompt_version": protocol["candidate"],
        "model": runner.MODEL, "taxonomy_sha256": protocol["taxonomy_sha256"],
        "records": EXPECTED_ROWS, "scheduled_batches": len(batches), "singleton_records": len(singleton),
        "protocol_path": str((runner.OUT / "protocol.json").relative_to(runner.ROOT)),
        "protocol_sha256": sha(runner.OUT / "protocol.json"),
        "implementation_hashes": {str(path.relative_to(runner.ROOT)): sha(path) for path in (
            Path(__file__).resolve(), runner.ROOT / "scripts/defect_grounded_candidate.py",
            runner.ROOT / "scripts/defect_grounding.py")},
        "batch_keys": [batch["key"] for batch in batches],
        "policy": {
            "identity_guard": "Full exact count and unique c1..cN identities must establish unambiguous mapping before any row recovery.",
            "row_guard": "Apply the unchanged validate_grounded_output to a copied single-row response with c1 and the corresponding sole source narrative. Retain only strictly valid rows; invalid rows stay missing.",
            "selection": "Append-only attempts.jsonl order: keep the FIRST strictly valid response for each record across the initial attempt and at most one exact-prompt retry; never replace an earlier valid row.",
            "max_attempts_per_batch": MAX_BATCH_ATTEMPTS,
            "retry": "No prompt, model, source input, schema, validator, quote or grounding-rule changes.",
            "forbidden": ["quote rewriting", "label guessing", "baseline fallback", "gold access", "row removal", "inference"],
            "singleton": "Retain the original only-allowed-taxonomy-label rule without a model call.",
        },
        "gold_answers_or_scores_read": False, "accuracy_computed": False,
        "output_path": str(OUTPUT.relative_to(runner.ROOT)),
    }
    write_new(PLAN, plan)
    print(f"Frozen row-validation policy for 300/300 records and {len(batches)}/{len(batches)} scheduled batches")


def run():
    if OUTPUT.exists() or MANIFEST.exists():
        raise ValueError("Completed row-validation output already exists; no overwrite permitted")
    if (runner.OUT / "accuracy.json").exists():
        raise ValueError("Row recovery must finish before candidate gold scoring")
    plan = json.loads(PLAN.read_text())
    for path, digest in plan["implementation_hashes"].items():
        if sha(runner.ROOT / path) != digest:
            raise ValueError(f"Frozen row-validation implementation changed: {path}")
    if sha(runner.OUT / "protocol.json") != plan["protocol_sha256"]:
        raise ValueError("Original frozen candidate protocol changed")
    protocol, records, batches, singleton = schedule()
    contract_path = runner.OUT / "evaluation_contract_check.json"
    contract_bytes = contract_path.read_bytes()
    contract = json.loads(contract_bytes)
    if contract.get("phase") != "evaluation" or contract.get("records") != EXPECTED_ROWS:
        raise ValueError("Original evaluation schedule completion contract is unavailable")
    attempts_path = runner.OUT / "attempts.jsonl"
    attempts_bytes = attempts_path.read_bytes()
    attempts = [(index, json.loads(line)) for index, line in enumerate(attempts_bytes.decode().splitlines(), 1) if line.strip()]
    selected, errors, attempted = first_valid_predictions(attempts, batches)
    if set(attempted) != {batch["key"] for batch in batches}:
        raise ValueError("Every frozen scheduled evaluation batch must have an attempted response before recovery")
    latest = max((attempt.get("completed_at", "") for _, attempt in attempts if attempt.get("phase") == "evaluation"), default="")
    if not contract.get("completed_at") or contract["completed_at"] < latest:
        raise ValueError("Evaluation attempts continued after the latest completion contract")
    caches = [runner.OUT / "cache" / f"evaluation-{batch['key']}.json" for batch in batches]
    cache_hashes = {str(path): sha(path) for path in caches if path.exists()}
    original = runner.OUT / "evaluation_classifications.parquet"
    original_hash = sha(original)
    rows, trail = [], []
    singleton_ids = {row["record_id"] for row in singleton}
    for record in records:
        rid = record["record_id"]
        if rid in singleton_ids:
            value = {"label_id": "other_unclear", "confidence": None, "evidence": "insufficient detail",
                     "status": "ok", "decision_method": "only_allowed_taxonomy_label", "validation_error": None,
                     "raw_record_id": None, "source_attempt_line": None}
        elif rid in selected:
            value = {**selected[rid], "status": "ok", "decision_method": "unchanged_strict_row_validator",
                     "validation_error": None}
        else:
            value = {"label_id": "", "confidence": None, "status": "missing", "decision_method": "invalid_or_unavailable_model_row",
                     "validation_error": json.dumps(errors.get(rid, [])), "raw_record_id": None, "source_attempt_line": None}
        rows.append({**value, "sample_id": record["sample_id"], "record_id": rid,
                     "component": record["component"], "model": runner.MODEL,
                     "prompt_version": VERSION, "original_prompt_version": protocol["candidate"],
                     "taxonomy_sha256": protocol["taxonomy_sha256"]})
        trail.append({"sample_id": record["sample_id"], "record_id": rid, "status": value["status"],
                      "source_attempt_line": value.get("source_attempt_line"),
                      "raw_record_id": value.get("raw_record_id"), "validation_errors": errors.get(rid, [])})
    if attempts_path.read_bytes() != attempts_bytes or contract_path.read_bytes() != contract_bytes:
        raise ValueError("Model process has not finished; source attempts or completion contract changed")
    with OUTPUT.open("xb") as handle:
        pd.DataFrame(rows).to_parquet(handle, index=False)
    ok = sum(row["status"] == "ok" for row in rows)
    manifest = {
        "schema_version": 1, "created_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "plan_sha256": sha(PLAN), "original_protocol_sha256": plan["protocol_sha256"],
        "implementation_hashes": plan["implementation_hashes"],
        "source_attempts": {"path": str(attempts_path), "sha256": hashlib.sha256(attempts_bytes).hexdigest()},
        "source_contract": {"path": str(contract_path), "sha256": hashlib.sha256(contract_bytes).hexdigest()},
        "raw_cache_hashes": cache_hashes,
        "original_batch_output": {"path": str(original), "sha256": original_hash},
        "output": {"path": str(OUTPUT), "sha256": sha(OUTPUT)},
        "scheduled_batches_attempted": {"numerator": len(attempted), "denominator": len(batches)},
        "batch_attempt_counts": dict(attempted),
        "valid_predictions": {"numerator": ok, "denominator": EXPECTED_ROWS},
        "missing_predictions": {"numerator": EXPECTED_ROWS - ok, "denominator": EXPECTED_ROWS},
        "retained_evaluation_rows": {"numerator": len(rows), "denominator": EXPECTED_ROWS},
        "decision_trail": trail, "gold_answers_or_scores_read": False,
        "accuracy_computed": False, "new_inference": False,
    }
    write_new(MANIFEST, manifest)
    print(f"Strict row-valid predictions: {ok}/300; missing: {EXPECTED_ROWS-ok}/300; retained: {len(rows)}/300")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("operation", choices=["prepare", "run"])
    args = parser.parse_args()
    if args.operation == "prepare":
        prepare()
    else:
        run()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
