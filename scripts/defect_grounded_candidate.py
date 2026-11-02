"""Freeze and run one grounded classifier candidate without fitting.

Preparation reads the original blank evaluation CSV and train-only taxonomy.
It never reads human answers. Predictions and scores are saved separately from
the baseline. The existing daily/lifetime API limits are never reset or raised.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import time

import pandas as pd

from scripts.defect_accuracy import file_sha, immutable_sample_hash, load_sample
from scripts.defect_classify import allowed_labels, load_taxonomy
from scripts.defect_grounding import PROMPT_VERSION, SYSTEM_PROMPT, make_prompt, make_schema, validate_grounded_output
from scripts.public_replay import ROOT
from src.security.pii import redact_pii

OUT = ROOT / "reports/improvement/defect_grounded_v1"
SAMPLE = ROOT / "reports/defect/defect_label_sample_300.csv"
TAXONOMY = ROOT / "reports/defect/taxonomy.json"
MODEL = "meta-models/muse-spark-open-1026"
BATCH_SIZE = 8
MAX_TOKENS = 5000
RPM = 20


def now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def write_new(path, data):
    with path.open("x") as f:
        f.write(json.dumps(data, indent=2, ensure_ascii=False) + "\n")


def prepare():
    if OUT.exists():
        raise ValueError("Candidate already prepared; preserve its frozen recipe and results")
    sample = load_sample(SAMPLE)
    manifest = json.loads((ROOT / "reports/defect/sample_manifest.json").read_text())
    taxonomy = load_taxonomy(TAXONOMY)
    if file_sha(SAMPLE) != manifest["csv_sha256"] or len(sample) != 300:
        raise ValueError("Frozen evaluation sample changed")
    if sample.label.ne("").any() or sample.notes.ne("").any():
        raise ValueError("Preparation requires the original blank sample, not a human review")
    if taxonomy["body"]["train_window"][1] > "2020-12-31":
        raise ValueError("Taxonomy is not train-only")
    records = [{"sample_id": row.sample_id, "record_id": f"{row.odino}|{row.component}",
                "component": row.component, "text": redact_pii(row.narrative)}
               for row in sample.itertuples()]
    source = ROOT.parent / "v2_ai_rca_tool/data/defect/complaints.parquet"
    dev = pd.read_parquet(source, columns=["datea", "odino", "component", "text"])
    dev = dev[dev.datea.astype(str).between("2015-01-01", "2020-12-31")].copy()
    dev["record_id"] = dev.odino.astype(str) + "|" + dev.component
    evaluation_ids = {r["record_id"] for r in records}
    dev = dev[~dev.record_id.isin(evaluation_ids)]
    eligible_components = sorted({r["component"] for r in records
                                  if len(allowed_labels(taxonomy, r["component"])) > 1})[:8]
    development = []
    for component in eligible_components:
        group = dev[dev.component == component].sort_values(["datea", "odino"])
        row = group.iloc[0]
        development.append({"record_id": row.record_id, "component": component,
                            "datea": str(row.datea), "text": redact_pii(str(row.text))})
    OUT.mkdir(parents=True)
    write_new(OUT / "evaluation_inputs.json", {"role": "evaluation_only", "records": records})
    write_new(OUT / "development_inputs.json", {
        "role": "pre_2021_software_contract_sanity_check_only", "human_accuracy_available": False,
        "selection": "Earliest source complaint in each of the first eight sorted non-singleton evaluation components; fixed before any candidate calls",
        "source_path": str(source), "source_sha256": file_sha(source), "records": development,
    })
    protocol = {
        "schema_version": 1, "frozen_at": now(), "candidate": PROMPT_VERSION,
        "target": {"overall_accuracy": 0.90, "evaluation_denominator": 300, "aspiration_not_achieved_result": True},
        "model": MODEL, "batch_size": BATCH_SIZE, "max_tokens": MAX_TOKENS,
        "reasoning_effort": "low", "rpm": RPM, "transport_retries": 0,
        "taxonomy_sha256": taxonomy["sha256"], "taxonomy_file_sha256": file_sha(TAXONOMY),
        "frozen_sample_sha256": file_sha(SAMPLE), "immutable_rows_sha256": immutable_sample_hash(sample),
        "system_prompt_sha256": hashlib.sha256(SYSTEM_PROMPT.encode()).hexdigest(),
        "frozen_files": {str(path.relative_to(ROOT)): file_sha(path) for path in (
            Path(__file__), ROOT / "scripts/defect_grounding.py",
            OUT / "evaluation_inputs.json", OUT / "development_inputs.json")},
        "training": "No fitting, calibration or feature selection. Prompt definitions/part/mode come only from the existing frozen pre-2021 taxonomy. No human evaluation answers or synthetic_review_v1 fixtures are read by preparation or inference.",
        "development": "Unlabelled pre-2021 complaints check transport and source-quote contracts only; no human development accuracy or supervised improvement claimed.",
        "evaluation": "One frozen candidate evaluated once against the existing human sample after predictions. Opened historical benchmark; not a fresh holdout. Preserve every missing prediction in the denominator. No candidate changes based on its evaluation errors.",
        "singleton_rule": "If the frozen taxonomy supplies only other_unclear, emit that sole allowed label without a model call; all rows remain in the evaluation.",
        "budget": "Use the existing server-side key and unchanged daily/lifetime reservation ledger; reduce retries to zero for this bounded candidate process; no cap reset or increase.",
    }
    write_new(OUT / "protocol.json", protocol)
    print(f"Frozen one candidate for {len(records)}/300 evaluation records; {len(development)}/{len(eligible_components)} pre-2021 software sanity-check rows")


def verify():
    protocol = json.loads((OUT / "protocol.json").read_text())
    for path, digest in protocol["frozen_files"].items():
        if file_sha(ROOT / path) != digest:
            raise ValueError(f"Frozen candidate input or code changed: {path}")
    if file_sha(SAMPLE) != protocol["frozen_sample_sha256"] or file_sha(TAXONOMY) != protocol["taxonomy_file_sha256"]:
        raise ValueError("Frozen sample or taxonomy changed")
    return protocol


def batches(phase):
    taxonomy = load_taxonomy(TAXONOMY)
    records = json.loads((OUT / f"{phase}_inputs.json").read_text())["records"]
    groups = {}
    for record in records:
        groups.setdefault(record["component"], []).append(record)
    result, singleton = [], []
    for component, rows in sorted(groups.items()):
        labels = allowed_labels(taxonomy, component)
        if len(labels) == 1:
            singleton += rows
            continue
        for start in range(0, len(rows), BATCH_SIZE):
            chunk = rows[start:start + BATCH_SIZE]
            allowed = [label["id"] for label in labels]
            user, schema = make_prompt(component, labels, chunk), make_schema(len(chunk), allowed)
            key = hashlib.sha256(json.dumps({"system": SYSTEM_PROMPT, "user": user, "schema": schema,
                                            "model": MODEL, "version": PROMPT_VERSION}, sort_keys=True).encode()).hexdigest()
            result.append({"key": key, "records": chunk, "allowed_ids": allowed, "user": user, "schema": schema})
    return records, result, singleton


def environment(path):
    from dotenv import load_dotenv
    load_dotenv(path, override=False)
    # Fewer retries reduce reservations; the existing call and spend caps stay intact.
    os.environ["META_RETRIES"] = "0"
    from src.ai_layer import config
    if not config.meta_enabled() or config.model_text() != MODEL:
        raise ValueError("The configured candidate backend/model is unavailable; no calls made")


def validated_cache(path, batch):
    if not path.exists():
        return None
    cached = json.loads(path.read_text())
    if cached.get("status") != "ok":
        return None
    items, reason = validate_grounded_output(cached.get("raw"), items=batch["records"], allowed_ids=batch["allowed_ids"])
    return items if reason is None else None


def preflight(phase, limit, env_file):
    verify()
    environment(env_file)
    from src.ai_layer import budget, config
    from src.ai_layer.meta_client import calls_today
    records, all_batches, singleton = batches(phase)
    pending = []
    for batch in all_batches:
        path = OUT / "cache" / f"{phase}-{batch['key']}.json"
        if validated_cache(path, batch) is None:
            pending.append(batch)
    selected = pending[:limit] if limit else pending
    current = budget.status()
    estimated = 0
    for batch in selected:
        schema_system = SYSTEM_PROMPT + "\nReturn only a JSON object matching this JSON schema:\n" + json.dumps(batch["schema"])
        payload = {"model": MODEL, "messages": [{"role": "system", "content": schema_system},
                   {"role": "user", "content": batch["user"]}], "temperature": 0, "max_tokens": MAX_TOKENS,
                   "response_format": {"type": "json_schema", "json_schema": {"name": "defect_grounded_batch", "schema": batch["schema"], "strict": False}},
                   "reasoning_effort": "low"}
        # Bound both possible schema-format attempts; add padding for redaction/encoding.
        estimated += 2 * budget.bound(payload) + 10000
    estimate = {"phase": phase, "records": len(records), "api_batches_total": len(all_batches),
                "pending_batches": len(pending), "selected_batches": len(selected), "singleton_records": len(singleton),
                "maximum_transport_attempts": 2 * len(selected), "calls_today": calls_today(),
                "daily_call_cap": config.daily_call_cap(), "reservation_upper_bound_usd": estimated / 1e6,
                "remaining_reservation_budget_usd": current["limit_usd"] - current["reserved_upper_bound_usd"],
                "budget_snapshot": current, "no_cap_change": True, "actual_billed_cost_usd": None}
    if estimate["maximum_transport_attempts"] + estimate["calls_today"] > estimate["daily_call_cap"]:
        raise ValueError("Candidate exceeds the remaining unchanged daily call cap")
    if estimate["reservation_upper_bound_usd"] > estimate["remaining_reservation_budget_usd"]:
        raise ValueError("Candidate exceeds the remaining unchanged spend reservation cap")
    return estimate, records, selected, singleton


def export_predictions(phase, records, singleton):
    by_id = {}
    _, all_batches, _ = batches(phase)
    for batch in all_batches:
        path = OUT / "cache" / f"{phase}-{batch['key']}.json"
        predictions = validated_cache(path, batch)
        if predictions is not None:
            for record, prediction in zip(batch["records"], predictions):
                by_id[record["record_id"]] = {**prediction, "status": "ok", "decision_method": "grounded_model"}
    for record in singleton:
        by_id[record["record_id"]] = {"label_id": "other_unclear", "confidence": None, "status": "ok",
                                       "evidence": "insufficient detail", "decision_method": "only_allowed_taxonomy_label"}
    rows = []
    for record in records:
        prediction = by_id.get(record["record_id"], {"label_id": "", "status": "missing", "confidence": None})
        rows.append({**prediction, "record_id": record["record_id"], "component": record["component"],
                     "model": MODEL, "prompt_version": PROMPT_VERSION,
                     "taxonomy_sha256": json.loads((OUT / "protocol.json").read_text())["taxonomy_sha256"]})
    pd.DataFrame(rows).to_parquet(OUT / f"{phase}_classifications.parquet", index=False)
    return sum(row["status"] == "ok" for row in rows)


def run(phase, limit, env_file):
    if limit < 1:
        raise ValueError("Live calls require an explicit positive --limit batch count")
    if phase == "evaluation":
        ready = OUT / "development_contract_check.json"
        if not ready.exists() or not json.loads(ready.read_text())["complete"]:
            raise ValueError("Complete the pre-2021 source-contract sanity check before evaluation")
        if (OUT / "accuracy.json").exists():
            raise ValueError("Candidate evaluation is already scored; do not iterate against human labels")
    estimate, records, selected, singleton = preflight(phase, limit, env_file)
    print(json.dumps(estimate, indent=2), flush=True)
    (OUT / "cache").mkdir(exist_ok=True)
    from src.ai_layer.meta_client import MetaError, chat_json
    failures = 0
    for index, batch in enumerate(selected, 1):
        started = now()
        try:
            raw = chat_json(system=SYSTEM_PROMPT, user=batch["user"], schema=batch["schema"],
                            schema_name="defect_grounded_batch", model=MODEL, timeout=90,
                            max_tokens=MAX_TOKENS, reasoning_effort="low")
            items, reason = validate_grounded_output(raw, items=batch["records"], allowed_ids=batch["allowed_ids"])
            result = {"status": "ok" if reason is None else "invalid", "error": reason,
                      "items": items, "raw": raw}
        except MetaError as error:
            result = {"status": "failed", "error": error.reason, "items": []}
        result.update({"batch_key": batch["key"], "phase": phase, "started_at": started, "completed_at": now()})
        with (OUT / "attempts.jsonl").open("a") as f:
            f.write(json.dumps(result, ensure_ascii=False) + "\n")
        (OUT / "cache" / f"{phase}-{batch['key']}.json").write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n")
        print(json.dumps({"completed_batch": index, "selected_batches": len(selected), "status": result["status"], "error": result.get("error")}), flush=True)
        if result["status"] != "ok":
            failures += 1
            error = str(result.get("error") or "")
            if any(marker in error for marker in ("budget_", "daily_call_cap", "meta_url_blocked", "meta_network:",
                                                     "meta_disabled", "meta_http_401", "meta_http_403", "meta_http_404")):
                break
        if index < len(selected):
            time.sleep(60 / RPM)
    ok = export_predictions(phase, records, singleton)
    summary = {"phase": phase, "completed_at": now(), "valid_predictions": ok, "records": len(records),
               "complete": ok == len(records), "failed_batches_this_run": failures,
               "human_accuracy_measured": False, "protocol_sha256": file_sha(OUT / "protocol.json")}
    (OUT / f"{phase}_contract_check.json").write_text(json.dumps(summary, indent=2) + "\n")
    print(json.dumps(summary, indent=2), flush=True)
    return 0 if failures == 0 else 2


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("operation", choices=["prepare", "preflight", "run"])
    parser.add_argument("--phase", choices=["development", "evaluation"], default="development")
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--env-file", type=Path, default=ROOT.parent / "v2_ai_rca_tool/.env")
    args = parser.parse_args()
    if args.operation == "prepare":
        prepare()
        return 0
    if args.operation == "preflight":
        estimate, _, _, _ = preflight(args.phase, args.limit, args.env_file)
        print(json.dumps(estimate, indent=2))
        return 0
    return run(args.phase, args.limit, args.env_file)


if __name__ == "__main__":
    raise SystemExit(main())
