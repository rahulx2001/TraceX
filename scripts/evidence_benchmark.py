"""Prepare independent review packs and a gated, equal-workload comparison.

No claim of human accuracy is emitted before a complete attested review. The
new cohort was chosen by unused makes/date, not by inspecting model scores.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

from scripts.defect_prepare_inputs import _iso_date, _iter_complaints_from_zip, _iter_recall_rows, file_sha256
from scripts.defect_repair import ROOT, write_json
from scripts.ingest_nhtsa import flat_line_to_mapping_row
from src.ai_layer import complaint_evidence as ce
from src.eval.fuel_detection import clean_reports, deduplicate_fuel, predict_student, detect, evaluate_period, features
from src.eval.evidence_review import (adjudicate_reviews, field_grading_pack, operational_metrics, require_expertise,
                                      review_disagreements, score_field_grading, validate_observations)

DATA = ROOT / "data/defect/evidence_v1"
OUT = ROOT / "reports/defect/evidence_v1"
MAKES = ["CHEVROLET", "GMC", "NISSAN"]
PACKS = {"development_review", "fuel_complaint_review", "recall_review"}


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def labels():
    tax = json.loads((ROOT/"reports/defect/taxonomy.json").read_text())
    return {x["id"]: x["definition"] for x in tax["body"]["components"]["FUEL SYSTEM"]["labels"]}


def records(frame):
    return [{"record_id": str(r.odino), "kind": "complaint", "datea": r.datea,
             "make": r.make, "model": r.model, "year": int(r.year), "source_component": r.source_component,
             "text": ce.source("r", r.text)["text"]} for r in frame.itertuples()]


def order(row):
    return digest(["evidence-v1-20261030", row["record_id"]])


def write_pack(name, rows):
    pack = {"name": name, "labels": labels(), "rows": rows, "annotation_source": "pending_human",
            "model_predictions_included": False}
    pack["sample_hash"] = digest(pack)
    write_json(OUT/f"{name}.json", pack)
    template = (ROOT/"scripts/templates/evidence_review.html").read_text()
    (OUT/f"{name}.html").write_text(template.replace("__REVIEW_DATA__", json.dumps(pack, ensure_ascii=False).replace("<", "\\u003c")))


def prepare():
    if (OUT/"protocol.json").exists():
        raise ValueError("Review cohort already frozen; refusing replacement")
    DATA.mkdir(parents=True, exist_ok=True); OUT.mkdir(parents=True, exist_ok=True)
    # The scope and policies are committed to disk before scanning 2025 outcomes.
    scope = {"makes": MAKES, "model_years": [2015, 2024], "holdout": ["2025-01-01", "2025-12-31"],
             "outcome_end": "2026-09-30", "sources": ["FUEL SYSTEM", "FUEL/PROPULSION SYSTEM"],
             "reason": "These makes were outside the previously scored five-make 2025 cohort. No model scores used for selection.",
             "policy": {"detector": "count", "window": 13, "minimum": 2, "threshold": 0},
             "workload": "Same maximum: one alert/week, two/month, 91-day make/defect cooldown; also compare exact matched monthly quotas.",
             "freshness": "Locally unevaluated make/time cohort; historical data and model pretraining can still leak recall knowledge.",
             "holdout_status": "unopened; human review pending", "target_recall": 0.86, "minimum_precision": 0.5}
    with (OUT/"scope_reservation.json").open("x") as f:
        json.dump(scope, f, indent=2)
    raw = pd.read_parquet(ROOT/"data/defect/complaints.parquet")
    development = clean_reports(deduplicate_fuel(raw[raw.make.isin(MAKES)&raw.year.between(2015,2024)]))
    rows = []
    archive = ROOT/"data/defect/source_cache/FLAT_CMPL.zip"
    for line in _iter_complaints_from_zip(archive):
        fields = line.rstrip("\r\n").split("\t")
        if len(fields) < 20 or fields[3] not in MAKES or not fields[15].startswith("2025"):
            continue
        row = flat_line_to_mapping_row(line)
        if not row or row["COMPONENT"] not in scope["sources"]:
            continue
        try:
            year = int(row["MODEL_YR"])
        except ValueError:
            continue
        day = _iso_date(row["DATEA"])
        if not 2015 <= year <= 2024 or not day or not "2025-01-01" <= day <= "2025-12-31":
            continue
        rows.append(dict(odino=row["ODINO"], datea=day, make=row["MAKETXT"], model=row["MODELTXT"], year=year,
                         component=row["COMPONENT"], text=row["CDESC"]))
    holdout = clean_reports(deduplicate_fuel(pd.DataFrame(rows)))
    if set(development.odino)&set(holdout.odino):
        raise ValueError("Complaint identity overlaps partitions")
    # Exclude repeated narratives from development before selecting review examples.
    normal = lambda s: " ".join(str(s).casefold().split())
    held_texts = set(holdout.text.map(normal))
    development = development[~development.text.map(normal).isin(held_texts)]
    development.to_parquet(DATA/"development.parquet", index=False)
    holdout.to_parquet(DATA/"holdout.parquet", index=False)
    scopes, _ = _iter_recall_rows(ROOT/"data/defect/source_cache/FLAT_RCL_POST_2010.zip", limit=0, preserve_scopes=True)
    refs = pd.DataFrame(scopes)
    refs = refs[refs.make.isin(MAKES)&refs.year.between(2015,2024)&refs.component.eq("FUEL SYSTEM")&refs.rcl_type.eq("V")
                &refs.rcdate.between("2025-01-01", scope["outcome_end"])].copy()
    refs["reference_id"] = refs.apply(lambda r: digest([r.campno, r.component, r.desc_defect])[:20], axis=1)
    refs.to_parquet(DATA/"recalls.parquet", index=False)
    dev = sorted(records(development), key=order)[:32]
    review = sorted(records(holdout), key=order)[:100]
    recs = [{"record_id": r.reference_id, "kind": "recall", "datea": r.rcdate, "make": r.make,
             "model": "Campaign "+r.campno, "year": "", "text": ce.source("r", r.desc_defect)["text"]}
            for r in refs.drop_duplicates("reference_id").itertuples()]
    write_pack("development_review", dev)
    write_pack("fuel_complaint_review", review)
    write_pack("recall_review", recs)
    inputs = {name: file_sha256(DATA/f"{name}.parquet") for name in ["development", "holdout", "recalls"]}
    write_json(OUT/"protocol.json", {**scope, "input_hashes": inputs,
          "source_hashes": {"complaints": file_sha256(archive), "recalls": file_sha256(ROOT/"data/defect/source_cache/FLAT_RCL_POST_2010.zip")},
          "review_counts": {"development": len(dev), "holdout_complaints": len(review), "recall_descriptions": len(recs)},
          "complaint_counts": {"development": len(development), "holdout": len(holdout)},
          "human_review": {"completed": 0, "status": "pending"}})
    print(json.dumps({"status": "prepared; no model scores or human results", "development_review": len(dev),
                      "complaint_review": len(review), "recall_review": len(recs), "holdout_complaints": len(holdout)}))


def load_pack(name):
    if name not in PACKS:
        raise ValueError("Unknown review pack")
    pack = json.loads((OUT/f"{name}.json").read_text())
    if pack["sample_hash"] != digest({k:v for k,v in pack.items() if k != "sample_hash"}):
        raise ValueError("Review pack changed")
    return pack


def import_review(path):
    data = json.loads(path.read_text())
    name = data.get("pack")
    if name not in {"development_review", "fuel_complaint_review", "recall_review"}:
        raise ValueError("Unknown review pack")
    if name != "development_review":
        checked_candidate()
    pack = load_pack(name)
    if data.get("sample_hash") != pack["sample_hash"] or data.get("annotation_source") != "human" or data.get("attestation") is not True or not str(data.get("reviewer", "")).strip():
        raise ValueError("Matching sample and named, attested human review required")
    rows = {r["record_id"]: r for r in pack["rows"]}; seen = set()
    for item in data.get("reviews", []):
        rid = item.get("record_id")
        if rid not in rows or rid in seen or item.get("label_id") not in pack["labels"]:
            raise ValueError("Invalid, duplicate or unknown review")
        seen.add(rid)
        validate_observations(item, rows[rid]["text"])
    if data.get("review_schema_version", 1) >= 2:
        require_expertise(data)
    if not seen:
        raise ValueError("No completed human reviews")
    folder = OUT/"human_reviews"; folder.mkdir(exist_ok=True)
    dest = folder/f"{name}-{digest(data)[:16]}.json"
    with dest.open("x") as f:
        json.dump({**data, "reviewed": len(seen), "total": len(rows), "input_sha256": file_sha256(path)}, f, indent=2)
    print(f"Imported {len(seen)}/{len(rows)} human reviews; no automatic adjudication: {dest}")


def student_predictions(rows):
    from src.ml_runtime.onnx_embedder import OnnxSemanticEmbedder
    embedder = OnnxSemanticEmbedder(ROOT/"models/minilm", intra_op_threads=2, max_batch_size=32)
    vectors = np.array([v.values[:384] for v in embedder.embed_many([r["text"] for r in rows])])
    archive = np.load(ROOT/"data/defect/fuel_holdout/final_student.npz", allow_pickle=False)
    model = {"weights": archive["weights"], "classes": archive["classes"].tolist(), "method": str(archive["method"])}
    values, margins = predict_student(model, vectors)
    return dict(zip([r["record_id"] for r in rows], zip(values, margins.tolist())))


def measured_extraction(row, label_set):
    """Retain failed/abstained inputs without inventing classification evidence."""
    import time
    from src.ai_layer import operation_trace
    started = time.monotonic()
    attempts = {}
    try:
        with operation_trace.capture(lambda event: attempts.update({event["attempt_id"]: event})):
            result = ce.extract([ce.source("report-1", row["text"])], labels=label_set)
    except Exception as exc:
        result = {"version": ce.VERSION, "mode": "failed", "observations": [], "unknown_fields": list(ce.FIELDS),
                "defect_label_id": "other_unclear", "label_evidence": [], "rejected": [], "model_id": None,
                "model_calls": None, "actual_cost_usd": None, "elapsed_ms": round((time.monotonic()-started)*1000),
                "fallback_reason": f"benchmark_{type(exc).__name__}", "review_required": True,
                "note": "Attempt failed. Its classification is an abstention, not a correct unknown label. Billing and logical-call count are unknown; prior reservations remain unchanged."}
    result["operations"] = list(attempts.values())
    result["operational_summary"] = operation_trace.summary(result["operations"], elapsed_ms=result.get("elapsed_ms"),
        model_calls=result.get("model_calls"), fallback=result.get("fallback_reason"))
    return result


def prepare_development_analysis():
    """An unfilled worksheet for all development rows, never a human result."""
    pack = load_pack("development_review")
    rows = {row["record_id"]: row for row in pack["rows"]}
    refs = {rid: [] for rid in rows}
    for path in sorted((OUT/"development_predictions").glob("*/*.json")):
        result = json.loads(path.read_text())
        rid = result.get("record_id")
        if rid in rows:
            if result.get("input_hash") != digest(rows[rid]):
                raise ValueError("Saved development output does not match the frozen source")
            refs[rid].append({"path": str(path.relative_to(ROOT)), "sha256": file_sha256(path),
                              "extractor_sha256": result.get("extractor_sha256"),
                              "mode": result.get("meta", {}).get("mode")})
    body = {"status": "pending_actual_human_error_analysis", "pack": pack["name"], "sample_hash": pack["sample_hash"],
            "source_rows": len(rows), "reviewed_rows": 0, "annotation_source": "pending_human", "attestation": False,
            "reviewer": "", "reviewer_profile": {"role": "", "experience": ""},
            "instructions": "First complete independent development_review labels without seeing predictions. Then inspect linked recorded outputs to analyze support, omissions and critical errors. No model output is a human judgment. Every development row remains present, including those without a model output.",
            "rows": [{"record_id": rid, "source_input_sha256": digest(row), "source_text": row["text"],
                      "recorded_output_refs": refs[rid], "human_review_reference": None,
                      "support_errors": None, "material_omissions": None, "critical_errors": None,
                      "ambiguity_or_disagreement": None, "review_complete": False} for rid, row in rows.items()]}
    destination = OUT/"development_error_analysis_pending.json"
    with destination.open("x") as file:
        json.dump(body, file, indent=2, ensure_ascii=False)
    print(f"Prepared {len(rows)} development rows; 0 reviewed. This unfilled worksheet is not completed error analysis.")


def predict_development(limit):
    if not 1 <= limit <= 32:
        raise ValueError("Use a bounded limit of 1–32; cached calls are reused")
    pack = load_pack("development_review")
    version = file_sha256(ROOT/"src/ai_layer/complaint_evidence.py")[:12]
    folder = OUT/"development_predictions"/version; folder.mkdir(parents=True, exist_ok=True)
    subset = pack["rows"][:limit]; student = student_predictions(subset)
    for row in subset:
        dest = folder/f"{row['record_id']}.json"
        if dest.exists():
            old = json.loads(dest.read_text())
            if old["input_hash"] != digest(row) or old["extractor_sha256"] != file_sha256(ROOT/"src/ai_layer/complaint_evidence.py"):
                raise ValueError("Cached prediction has a different input or extractor")
            continue
        result = measured_extraction(row, pack["labels"])
        write_json(dest, {"record_id": row["record_id"], "input_hash": digest(row), "pack_hash": pack["sample_hash"],
                         "extractor_sha256": file_sha256(ROOT/"src/ai_layer/complaint_evidence.py"),
                         "student_label": student[row["record_id"]][0], "student_margin": student[row["record_id"]][1], "meta": result})
        print(f"{row['record_id']}: {result['mode']}; saved", flush=True)
    outputs = [json.loads(p.read_text()) for p in sorted(folder.glob("*.json"))]
    summary = {"status": "development only; no human accuracy result", "rows": len(outputs), "extractor_version": version,
               "predictions_directory": str(folder.relative_to(ROOT)),
               "meta_successes": sum(o["meta"]["mode"].startswith("meta") for o in outputs),
               "label_agreements": sum(o["meta"]["defect_label_id"] == o["student_label"] for o in outputs),
               "human_reviewed": 0, "accuracy": None, "campaign_recall": None,
               "note": "Agreement between models is not correctness. These examples are development diagnostics, not the reserved cohort."}
    summary["operations"] = operational_metrics(o["meta"] for o in outputs)
    old = OUT/"development_comparison.json"
    if old.exists():
        previous = json.loads(old.read_text())
        write_json(OUT/"development_comparisons"/f"{digest(previous)[:16]}.json", previous)
    write_json(old, summary)
    print(json.dumps(summary, indent=2))


def complete_review(path, expected_pack, *, fields=False, return_document=False, allow_partial=False):
    if expected_pack not in PACKS:
        raise ValueError("Unknown review pack")
    if path is None or not path.is_file():
        raise ValueError(f"Complete human {expected_pack} is required; no score can be invented")
    data = json.loads(path.read_text()); pack = load_pack(expected_pack)
    if (data.get("pack") != expected_pack or data.get("sample_hash") != pack["sample_hash"]
            or data.get("annotation_source") != "human" or data.get("attestation") is not True
            or not str(data.get("reviewer", "")).strip()):
        raise ValueError("Matching, named human review required")
    rows = data.get("reviews", [])
    ids = {r.get("record_id") for r in rows}; expected = {r["record_id"] for r in pack["rows"]}
    if (not rows or len(ids) != len(rows) or ids-expected
            or (not allow_partial and ids != expected)):
        raise ValueError("Incomplete or duplicated human labels; keep results pending")
    if any(r.get("label_id") not in pack["labels"] for r in rows):
        raise ValueError("Invalid human label")
    sources = {r["record_id"]: r["text"] for r in pack["rows"]}
    for row in rows:
        validate_observations(row, sources[row["record_id"]], require_complete=fields)
    if fields or data.get("review_schema_version", 1) >= 2:
        require_expertise(data)
    if return_document:
        return data
    return {r["record_id"]: r["label_id"] for r in rows}


def frozen_hashes():
    from src.ai_layer import config
    files = [ROOT/"src/ai_layer/complaint_evidence.py", ROOT/"src/ai_layer/claim_support.py", ROOT/"src/ai_layer/meta_client.py",
             ROOT/"src/ai_layer/config.py", ROOT/"src/ai_layer/budget.py", ROOT/"src/ai_layer/operation_trace.py", ROOT/"src/eval/evidence_review.py", Path(__file__),
             ROOT/"src/eval/fuel_detection.py", ROOT/"src/eval/defect_prediction.py", ROOT/"src/ml_runtime/onnx_embedder.py",
             ROOT/"data/defect/fuel_holdout/final_student.npz", OUT/"protocol.json", ROOT/"reports/defect/taxonomy.json"]
    files.extend(p for p in (ROOT/"models/minilm").rglob("*") if p.is_file() and p.suffix in {".onnx", ".json", ".txt"})
    return {"files": {str(p.relative_to(ROOT)): file_sha256(p) for p in files}, "model_id": config.model_text(),
            "runtime": {"backend": config.backend(), "api_base_sha256": digest(config.api_base()),
                        "meta_enabled": config.meta_enabled(), "retries": config.retries()}}


def freeze(dev_review, complaint_review=None, recall_review=None):
    """Freeze from development only; reserved human gold must remain sealed."""
    complete_review(dev_review, "development_review", fields=True)
    if complaint_review is not None or recall_review is not None:
        raise ValueError("Freeze the candidate using development only, then use attach-reviews for sealed independent gold")
    if (OUT/".comparison_opened").exists() or (OUT/"comparison_freeze.json").exists() or any((OUT/"holdout_predictions").glob("*.json")):
        raise ValueError("This holdout was already opened or frozen by the old protocol; use a new reservation")
    if any(p.name.startswith(("fuel_complaint_review-", "recall_review-")) for p in (OUT/"human_reviews").glob("*.json")):
        raise ValueError("Reserved gold was already imported before candidate freeze; do not call it sealed")
    protocol = json.loads((OUT/"protocol.json").read_text())
    for name, sha in protocol["input_hashes"].items():
        if file_sha256(DATA/f"{name}.parquet") != sha:
            raise ValueError("Frozen cohort inputs changed")
    body = {"hashes": frozen_hashes(), "created_at": datetime.now(timezone.utc).isoformat(),
        "human_reviews": {"development_review": {"path": str(dev_review.resolve()), "sha256": file_sha256(dev_review)}},
        "policy": protocol["policy"], "status": "candidate_frozen_before_reserved_gold_attachment",
        "gold_access_note": "Technical order and custodian attestation are recorded; the tool cannot police access outside this workflow."}
    with (OUT/"candidate_freeze.json").open("x") as f:
        json.dump({"body": body, "sha256": digest(body)}, f, indent=2)
    print("Candidate frozen from development. Reserved human gold remains unattached; no prediction score exists.")


def checked_candidate():
    path = OUT/"candidate_freeze.json"
    if not path.exists():
        raise ValueError("No frozen candidate: development human reviews are pending. Freeze before reserved gold attachment.")
    frozen = json.loads(path.read_text()); body = frozen["body"]
    if frozen["sha256"] != digest(body) or body["hashes"] != frozen_hashes():
        raise ValueError("Frozen code, model or configuration changed; do not retune this holdout")
    for name, spec in body["human_reviews"].items():
        path = Path(spec["path"])
        if file_sha256(path) != spec["sha256"]:
            raise ValueError("Frozen human labels changed")
        complete_review(path, name, fields=True)
    protocol = json.loads((OUT/"protocol.json").read_text())
    for name, sha in protocol["input_hashes"].items():
        if file_sha256(DATA/f"{name}.parquet") != sha:
            raise ValueError("Frozen evaluation inputs changed")
    return frozen, protocol


def attach_reviews(complaint_review, recall_review, custodian, attest_sealed=False):
    frozen, _ = checked_candidate()
    if not str(custodian or "").strip() or attest_sealed is not True:
        raise ValueError("Named independent custodian must attest reserved gold was not used for candidate selection")
    for path, name in [(complaint_review, "fuel_complaint_review"), (recall_review, "recall_review")]:
        complete_review(path, name, fields=True)
    body = {"candidate_sha256": frozen["sha256"], "attached_at": datetime.now(timezone.utc).isoformat(),
            "custodian": custodian.strip(), "sealed_gold_attestation": True,
            "human_reviews": {name: {"path": str(path.resolve()), "sha256": file_sha256(path)}
                for path, name in [(complaint_review, "fuel_complaint_review"), (recall_review, "recall_review")]}}
    with (OUT/"gold_attachment.json").open("x") as f:
        json.dump({"body": body, "sha256": digest(body)}, f, indent=2)
    print("Independent gold attached to the existing candidate. No model or scoring choices were changed.")


def checked_freeze():
    frozen, protocol = checked_candidate()
    path = OUT/"gold_attachment.json"
    if not path.exists():
        raise ValueError("Reserved human reviews remain sealed/unattached; attach-reviews is required before scoring")
    attachment = json.loads(path.read_text()); body = attachment["body"]
    if attachment.get("sha256") != digest(body) or body.get("candidate_sha256") != frozen["sha256"] or body.get("sealed_gold_attestation") is not True:
        raise ValueError("Independent gold attachment does not match the frozen candidate")
    for name, spec in body["human_reviews"].items():
        if file_sha256(Path(spec["path"])) != spec["sha256"]:
            raise ValueError("Attached human labels changed")
        complete_review(Path(spec["path"]), name, fields=True)
    # Keep the candidate body hash valid; attachment is a separately hashed
    # record, not a mutation of the frozen candidate's hash-identified content.
    frozen["human_reviews"] = {**frozen["body"]["human_reviews"], **body["human_reviews"]}
    frozen["gold_attachment_sha256"] = attachment["sha256"]
    return frozen, protocol


def evaluation_rows():
    # Include a year of prior evidence so January alerts do not start without history.
    before = pd.read_parquet(DATA/"development.parquet")
    held = pd.read_parquet(DATA/"holdout.parquet")
    frame = pd.concat([before[before.datea.ge("2024-01-01")], held], ignore_index=True)
    return frame, records(frame)


def predict_holdout(limit):
    if not 1 <= limit <= 32:
        raise ValueError("A bounded --limit of 1–32 is required")
    frozen, _ = checked_candidate()
    marker = OUT/".comparison_opened"
    if not marker.exists():
        with marker.open("x") as f: f.write(frozen["sha256"])
    if marker.read_text() != frozen["sha256"]:
        raise ValueError("Holdout reservation mismatch")
    _, rows = evaluation_rows()
    folder = OUT/"holdout_predictions"; folder.mkdir(exist_ok=True)
    pending = [r for r in rows if not (folder/f"{r['record_id']}.json").exists()][:limit]
    if not pending:
        print("All predictions recorded; evaluate once against the frozen reviews."); return
    estimate = cost_preflight(rows, pending)
    print(json.dumps(estimate, indent=2), flush=True)
    if estimate["batch_estimated_reservation_upper_bound_usd"] > estimate["remaining_reservation_budget_usd"]:
        raise ValueError("Estimated batch reservation exceeds the remaining unchanged budget; reduce the batch or stop")
    student = student_predictions(pending)
    for row in pending:
        result = measured_extraction(row, labels())
        dest = folder/f"{row['record_id']}.json"
        with dest.open("x") as f:
            json.dump({"record_id": row["record_id"], "input_hash": digest(row), "freeze_sha256": frozen["sha256"],
                       "student_label": student[row["record_id"]][0], "meta": result}, f)
        print(f"{row['record_id']}: saved {result['mode']}; errors/abstentions stay in the evaluation", flush=True)


def matched_workload(left, right):
    from collections import Counter
    a, b = Counter(x["available_at"][:7] for x in left), Counter(x["available_at"][:7] for x in right)
    quotas = {month: min(a[month], b[month]) for month in set(a)|set(b)}
    def keep(items):
        seen = Counter(); result = []
        for row in sorted(items, key=lambda r: r["available_at"]):
            month = row["available_at"][:7]
            if seen[month] < quotas[month]: result.append(row); seen[month] += 1
        return result
    return keep(left), keep(right)


def workload_summary(alerts, start, end):
    from collections import Counter
    months = pd.period_range(start, end, freq="M").astype(str).tolist()
    counts = Counter(a["available_at"][:7] for a in alerts)
    if set(counts) - set(months):
        raise ValueError("Alert lies outside the stated workload period")
    return {"alerts": len(alerts), "monthly_counts": {month: counts[month] for month in months},
            "no_alert_months": [month for month in months if not counts[month]], "original_alerts": alerts}


def cost_preflight(all_rows, pending_rows, *, status=None):
    """A conservative planning estimate, never a billing result or cap reset."""
    from src.ai_layer import budget, config
    current = status if status is not None else budget.status()
    model = config.model_text()
    if model not in budget.RATES:
        raise ValueError("The configured model has no bounded pricing estimate")
    # Include the serialized source and its sentence copies, not just raw text.
    # The source-file byte allowance bounds the fixed system prompt; schema is
    # budgeted twice because Baseten can repeat it in the json_object prompt.
    label_set = labels()
    overhead = 2*len((ROOT/"src/ai_layer/complaint_evidence.py").read_bytes()) + 2*len(json.dumps(ce.schema(list(label_set))).encode()) + 4096
    baseten = config.backend() == "baseten"
    cap = 4000 if baseten else 2400  # Mirrors the adapter's reasoning-token floor.
    # Baseten may make a second bounded _post after a schema-format 400/422.
    attempts = (1 + config.retries())*(2 if baseten else 1)
    def estimate(rows):
        inp, out = budget.RATES[model]
        total = 0
        for row in rows:
            user = json.dumps({"sources": [ce.source("report-1", row["text"])], "label_definitions": label_set,
                               "investigation": False, "planning_context": None}, ensure_ascii=False)
            # Account for JSON escaping when this user string is in a payload.
            user_bytes = len(json.dumps(user, ensure_ascii=False).encode())
            total += ((user_bytes + overhead + 4096)*inp + cap*out)/1e6 + .000001
        return attempts*total
    return {"kind": "preflight_estimate_only", "model_id": model, "full_rows_including_warmup": len(all_rows),
            "pending_batch_rows": len(pending_rows), "logical_calls_per_row": 1,
            "maximum_transport_attempts_per_row": attempts,
            "completion_token_cap_per_attempt": cap,
            "full_estimated_reservation_upper_bound_usd": estimate(all_rows),
            "batch_estimated_reservation_upper_bound_usd": estimate(pending_rows),
            "remaining_reservation_budget_usd": max(0, current["limit_usd"]-current["reserved_upper_bound_usd"]),
            "budget_snapshot": current, "actual_billed_cost_usd": None,
            "note": "Planning estimate includes serialized source sentences, the configured maximum transport retries, and Baseten's 4000-token floor and possible schema-format retry. The client still enforces daily and lifetime caps before every attempt. Baseten rates remain an estimate, not verified billing."}


def label_metrics(truth, predicted):
    """Report class imbalance explicitly; a dominant unknown class is not a win."""
    if not truth or len(truth) != len(predicted):
        raise ValueError("Complete nonempty paired labels required")
    classes = sorted(set(truth)|set(predicted))
    matrix = {label: {other: 0 for other in classes} for label in classes}
    for actual, guess in zip(truth, predicted): matrix[actual][guess] += 1
    per_label = {}
    for label in classes:
        tp = matrix[label][label]
        actual = sum(matrix[label].values()); guessed = sum(matrix[r][label] for r in classes)
        precision = tp/guessed if guessed else 0.0; recall = tp/actual if actual else 0.0
        per_label[label] = {"support": actual, "precision": precision, "recall": recall,
                            "f1": 2*precision*recall/(precision+recall) if precision+recall else 0.0}
    specific = [(a,p) for a,p in zip(truth,predicted) if a != "other_unclear"]
    return {"rows": len(truth), "correct": sum(a==p for a,p in zip(truth,predicted)),
            "accuracy": sum(a==p for a,p in zip(truth,predicted))/len(truth),
            "macro_f1": sum(x["f1"] for x in per_label.values())/len(classes),
            "specific_defect_rows": len(specific), "specific_defect_accuracy": sum(a==p for a,p in specific)/len(specific) if specific else None,
            "always_other_accuracy": sum(a=="other_unclear" for a in truth)/len(truth),
            "abstained_rows": sum(p == "__abstained__" for p in predicted),
            "abstention_rate": sum(p == "__abstained__" for p in predicted)/len(truth),
            "per_label": per_label, "confusion_matrix": matrix}


def evaluate():
    frozen, protocol = checked_freeze()
    frame, rows = evaluation_rows()
    outputs = {}
    for row in rows:
        path = OUT/"holdout_predictions"/f"{row['record_id']}.json"
        if not path.exists():
            raise ValueError("Prediction coverage incomplete; no partial recall score may be published")
        result = json.loads(path.read_text())
        if result["freeze_sha256"] != frozen["sha256"] or result["input_hash"] != digest(row):
            raise ValueError("Prediction provenance mismatch")
        outputs[row["record_id"]] = result
    refs = pd.read_parquet(DATA/"recalls.parquet")
    gold_refs = complete_review(Path(frozen["human_reviews"]["recall_review"]["path"]), "recall_review")
    refs["label_id"] = refs.reference_id.map(gold_refs)
    if refs.label_id.isna().any():
        raise ValueError("Recall label coverage incomplete")
    start, end = protocol["holdout"]
    alert_sets = {}
    for method in ["student", "meta"]:
        source_frame = frame.copy()
        source_frame["label_id"] = [outputs[str(r.odino)]["student_label"] if method == "student" else outputs[str(r.odino)]["meta"]["defect_label_id"] for r in frame.itertuples()]
        alert_sets[method] = detect(features(source_frame, end=end), protocol["policy"], start=start, end=end)
    left, right = matched_workload(alert_sets["student"], alert_sets["meta"])
    result = {"freeze_sha256": frozen["sha256"], "status": "one_shot_historical_comparison", "campaign_matching": "make + specific defect; not physical part identity",
              "workload_note": "Equal actual monthly alert counts by keeping the earliest common quota. This is a conditional retrospective comparison, not an online policy.",
              "student": evaluate_period(left, refs, start=start, end=end, outcome_end=protocol["outcome_end"]),
              "meta": evaluate_period(right, refs, start=start, end=end, outcome_end=protocol["outcome_end"])}
    result["gold_attachment_sha256"] = frozen["gold_attachment_sha256"]
    result["original_workload"] = {method: {**workload_summary(alerts, start, end),
        "evaluation": evaluate_period(alerts, refs, start=start, end=end, outcome_end=protocol["outcome_end"])} for method, alerts in alert_sets.items()}
    result["matched_workload"] = {method: workload_summary(alerts, start, end)
        for method, alerts in [("student", left), ("meta", right)]}
    result["association_levels"] = {"evaluated": "make + component + reported defect label within the lead-time window",
        "exact_vehicle_model_year_part_lot": {"status": "not_evaluated", "accuracy": None},
        "multiple_campaign_match_alerts": {method: sum(len(row["matched_campaigns"]) > 1 for row in result[method]["alert_details"])
            for method in ("student", "meta")},
        "note": "Broad alert detection is scored separately. Shared make/category/label is not exact vehicle, model-year, installed-part or lot prediction. Synthetic trace reviews are not prediction outcomes."}
    result["operations"] = operational_metrics(o["meta"] for o in outputs.values())
    result["field_quality"] = {"status": "pending_independent_field_grading", "note": "Classification accuracy is not field correctness. Use prepare-field-grading and score-fields; no automatic semantic score is invented."}
    gold = complete_review(Path(frozen["human_reviews"]["fuel_complaint_review"]["path"]), "fuel_complaint_review")
    meta_labels = {r: outputs[r]["meta"]["defect_label_id"] if str(outputs[r]["meta"].get("mode", "")).startswith("meta") else "__abstained__" for r in gold}
    result["human_classification"] = {"reviewed": len(gold), "student_correct": sum(outputs[r]["student_label"]==v for r,v in gold.items()),
                                      "meta_correct": sum(meta_labels[r]==v for r,v in gold.items()),
                                      "note": "Human label accuracy on the fixed review sample, not a percentage of accidents predicted."}
    result["human_classification"]["student"] = label_metrics(list(gold.values()), [outputs[r]["student_label"] for r in gold])
    result["human_classification"]["meta"] = label_metrics(list(gold.values()), [meta_labels[r] for r in gold])
    result["numeric_target_met"] = result["meta"]["campaign_recall"] > protocol["target_recall"] and (result["meta"]["episode_precision"] or 0) >= protocol["minimum_precision"]
    result["promoted_to_production"] = False
    result["qualification_note"] = "Diagnostic comparison only. Direct Meta campaign precision has not passed the separate two-fold development qualification gate. A numeric holdout threshold is not production qualification."
    with (OUT/"comparison_results.json").open("x") as f: json.dump(result, f, indent=2)
    print(json.dumps({"student": {k:v for k,v in result["student"].items() if k not in {"campaign_hits","alert_details"}},
                      "meta": {k:v for k,v in result["meta"].items() if k not in {"campaign_hits","alert_details"}}}, indent=2))


def prepare_field_grading(review_path, prediction_path):
    document = json.loads(review_path.read_text())
    name = document.get("pack")
    if name != "development_review":
        checked_freeze()
    reference = complete_review(review_path, name, fields=True, return_document=True)
    predictions = json.loads(prediction_path.read_text())
    pack, mapping = field_grading_pack(load_pack(name)["rows"], reference["reviews"], predictions)
    mapping.update(reference_reviewers=[reference["reviewer"]], reference_sha256=file_sha256(review_path),
                   predictions_sha256=file_sha256(prediction_path))
    folder = OUT/"field_grading"; folder.mkdir(exist_ok=True)
    stem = pack["pack_hash"][:16]
    for suffix, value in [("pack", pack), ("mapping", mapping)]:
        with (folder/f"{stem}-{suffix}.json").open("x") as f:
            json.dump(value, f, indent=2)
    print(f"Prepared ungraded field pack {stem}. No field score exists until an independent human grades every item.")


def score_fields(grading_path, mapping_path):
    mapping = json.loads(mapping_path.read_text())
    result = score_field_grading(json.loads(grading_path.read_text()), mapping, reference_reviewers=mapping["reference_reviewers"])
    result["grading_sha256"] = file_sha256(grading_path)
    result["mapping_sha256"] = file_sha256(mapping_path)
    dest = OUT/"field_grading"/f"result-{digest(result)[:16]}.json"
    with dest.open("x") as f: json.dump(result, f, indent=2)
    print(json.dumps(result, indent=2))


def compare_reviews(paths):
    documents = []
    for path in paths:
        doc = json.loads(path.read_text())
        if doc.get("pack") != "development_review": checked_candidate()
        documents.append(complete_review(path, doc.get("pack"), fields=True, return_document=True, allow_partial=True))
    result = review_disagreements(documents)
    result["input_hashes"] = {str(p): file_sha256(p) for p in paths}
    folder = OUT/"adjudication"; folder.mkdir(exist_ok=True)
    dest = folder/f"pending-{digest(result)[:16]}.json"
    with dest.open("x") as f: json.dump(result, f, indent=2)
    print(f"Prepared disagreement review: {dest}. No consensus labels were generated.")


def adjudicate(disagreements_path, completed_path):
    pending = json.loads(disagreements_path.read_text())
    name = pending.get("pack")
    if name != "development_review": checked_candidate()
    originals = []
    for path, sha in pending.get("input_hashes", {}).items():
        if file_sha256(Path(path)) != sha:
            raise ValueError("Original review changed before adjudication")
        originals.append(complete_review(Path(path), name, fields=True, return_document=True, allow_partial=True))
    completed = json.loads(completed_path.read_text())
    result = adjudicate_reviews(pending, completed, original_reviews=originals)
    pack = load_pack(name); sources = {r["record_id"]: r["text"] for r in pack["rows"]}
    for decision in completed["decisions"]:
        if decision["resolution"] == "adjudicated":
            if decision["label_id"] not in pack["labels"]:
                raise ValueError("Adjudication used a label outside the frozen taxonomy")
            validate_observations(decision, sources[decision["record_id"]])
    dest = OUT/"adjudication"/f"completed-{digest(result)[:16]}.json"
    with dest.open("x") as f: json.dump(result, f, indent=2)
    print(f"Stored independent adjudication with original disagreement retained: {dest}")


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("phase", choices=["prepare", "prepare-development-analysis", "predict-development", "import-review", "freeze", "attach-reviews", "predict-holdout", "preflight", "evaluate", "prepare-field-grading", "score-fields", "compare-reviews", "adjudicate"])
    p.add_argument("--limit", type=int); p.add_argument("--review", type=Path)
    p.add_argument("--complaint-review", type=Path); p.add_argument("--recall-review", type=Path)
    p.add_argument("--custodian"); p.add_argument("--attest-sealed", action="store_true")
    p.add_argument("--predictions", type=Path); p.add_argument("--grading", type=Path); p.add_argument("--mapping", type=Path)
    p.add_argument("--reviews", nargs="+", type=Path)
    p.add_argument("--disagreements", type=Path)
    args = p.parse_args()
    if args.phase == "prepare": prepare()
    elif args.phase == "prepare-development-analysis": prepare_development_analysis()
    elif args.phase == "predict-development":
        if args.limit is None: p.error("--limit is required before model calls")
        predict_development(args.limit)
    elif args.phase == "import-review":
        if not args.review: p.error("--review required")
        import_review(args.review)
    elif args.phase == "freeze": freeze(args.review, args.complaint_review, args.recall_review)
    elif args.phase == "attach-reviews": attach_reviews(args.complaint_review, args.recall_review, args.custodian, args.attest_sealed)
    elif args.phase == "prepare-field-grading":
        if not args.review or not args.predictions: p.error("--review and --predictions are required")
        prepare_field_grading(args.review, args.predictions)
    elif args.phase == "score-fields":
        if not args.grading or not args.mapping: p.error("--grading and --mapping are required")
        score_fields(args.grading, args.mapping)
    elif args.phase == "compare-reviews":
        if not args.reviews: p.error("--reviews requires actual human review exports")
        compare_reviews(args.reviews)
    elif args.phase == "adjudicate":
        if not args.disagreements or not args.grading: p.error("--disagreements and --grading are required")
        adjudicate(args.disagreements, args.grading)
    elif args.phase == "preflight":
        checked_candidate()
        _, rows = evaluation_rows()
        pending = [r for r in rows if not (OUT/"holdout_predictions"/f"{r['record_id']}.json").exists()]
        print(json.dumps(cost_preflight(rows, pending[:args.limit] if args.limit else pending), indent=2))
    elif args.phase == "predict-holdout":
        if args.limit is None: p.error("--limit is required")
        predict_holdout(args.limit)
    else: evaluate()


if __name__ == "__main__":
    main()
