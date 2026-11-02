"""Human evidence grading. Source overlap is never treated as semantic truth."""
from __future__ import annotations

from collections import Counter
from datetime import datetime
import hashlib
import json
import math
import statistics

FIELDS = ("vehicle", "part", "symptom", "failure_mode", "timing", "negation", "uncertainty")
ERRORS = ("wrong_part", "wrong_timing", "negation_reversed", "uncertainty_lost",
          "changed_number_or_identifier", "unsupported_cause", "other_unsupported")


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def validate_observations(row, source, *, require_complete=False):
    observations = row.get("observations", [])
    if not isinstance(observations, list):
        raise ValueError("Human observations must be a list")
    for observation in observations:
        quote = observation.get("quote")
        if (observation.get("field") not in FIELDS
                or observation.get("polarity") not in {"affirmed", "denied", "uncertain"}
                or not isinstance(quote, str) or not quote or quote not in source
                or not isinstance(observation.get("value"), str) or not observation["value"].strip()):
            raise ValueError("Human observations require a reviewed interpretation and exact source quote")
    if require_complete and row.get("field_review_complete") is not True:
        raise ValueError("Explicit review of every extraction field is required; absent fields may remain empty")
    return [{**observation, "observation_id": f"{row['record_id']}:gold:{i}"}
            for i, observation in enumerate(observations)]


def require_expertise(review):
    profile = review.get("reviewer_profile") or {}
    if not str(profile.get("role", "")).strip() or not str(profile.get("experience", "")).strip():
        raise ValueError("Actual reviewer role and relevant experience are required")


def field_grading_pack(source_rows, reference_rows, predictions):
    """Prepare unfilled human grading; the method mapping stays outside the pack.

    predictions is {method: {record_id: extractor result}}. All methods need the
    same records, including empty/fallback results. No method is scored here.
    """
    sources = {row["record_id"]: row for row in source_rows}
    gold = {row["record_id"]: validate_observations(row, sources[row["record_id"]]["text"], require_complete=True)
            for row in reference_rows}
    if not gold or not predictions or any(set(rows) != set(gold) for rows in predictions.values()):
        raise ValueError("Every method must cover the same nonempty human-reviewed sample")
    items, mapping = [], {}
    for method, outputs in sorted(predictions.items()):
        for rid, output in sorted(outputs.items()):
            blind_id = digest([method, rid, output])[:24]
            mapping[blind_id] = {"method": method, "record_id": rid}
            observations = output.get("observations", [])
            items.append({"item_id": blind_id, "source": sources[rid]["text"], "reference_observations": gold[rid],
                          "predicted_observations": [{"prediction_id": f"{blind_id}:{i}", "field": o.get("field"),
                              "polarity": o.get("polarity"), "value": o.get("value"),
                              "quote": (o.get("evidence") or {}).get("quote", "")}
                              for i, o in enumerate(observations)],
                          "grades": [{"prediction_id": f"{blind_id}:{i}", "supported": None,
                              "citation_entails_claim": None, "matched_reference_ids": [], "error_types": [], "note": ""}
                              for i in range(len(observations))],
                          "review_complete": False, "note": ""})
    # Condition is concealed; preserve a private mapping for scoring.
    items.sort(key=lambda item: item["item_id"])
    body = {"version": 1, "kind": "independent_field_grading", "items": items,
            "instructions": "Grade every interpretation against the original text. Quote existence alone is not support. Link only semantically matching reference observations. Missing reference facts are retained as omissions. Empty model outputs still need review_complete. Do not infer the method.",
            "allowed_errors": list(ERRORS), "grader": "", "reviewer_profile": {"role": "", "experience": ""},
            "annotation_source": "human", "attestation": False}
    immutable = field_grading_identity(body)
    body["pack_hash"] = digest(immutable)
    return body, {"pack_hash": body["pack_hash"], "methods": sorted(predictions), "items": mapping}


def field_grading_identity(pack):
    return {"version": pack.get("version"), "kind": pack.get("kind"), "items": [
        {k: item.get(k) for k in ("item_id", "source", "reference_observations", "predicted_observations")}
        for item in pack.get("items", [])]}


def score_field_grading(pack, mapping, *, reference_reviewers=()):
    if (pack.get("annotation_source") != "human" or pack.get("attestation") is not True
            or not str(pack.get("grader", "")).strip() or pack["grader"] in reference_reviewers):
        raise ValueError("Independent named human field grader and attestation required")
    require_expertise(pack)
    if pack.get("pack_hash") != mapping.get("pack_hash") or digest(field_grading_identity(pack)) != pack.get("pack_hash"):
        raise ValueError("Field grading sources or predictions changed")
    if {item["item_id"] for item in pack["items"]} != set(mapping["items"]) or len(pack["items"]) != len(mapping["items"]):
        raise ValueError("Incomplete or duplicate grading items")
    counts = {method: {field: Counter() for field in FIELDS} for method in mapping["methods"]}
    diagnostics = {method: Counter() for method in mapping["methods"]}
    for item in pack["items"]:
        if item.get("review_complete") is not True:
            raise ValueError("Every field-grading item, including fallback outputs, needs human review")
        method = mapping["items"][item["item_id"]]["method"]
        preds = {p["prediction_id"]: p for p in item["predicted_observations"]}
        gold = {g["observation_id"]: g for g in item["reference_observations"]}
        grades = item.get("grades", [])
        if len(grades) != len(preds) or {g.get("prediction_id") for g in grades} != set(preds):
            raise ValueError("Every predicted observation requires one grade")
        covered = set()
        diagnostics[method]["reviewed_records"] += 1
        diagnostics[method]["empty_outputs"] += not bool(preds)
        for reference in gold.values(): counts[method][reference["field"]]["reference_observations"] += 1
        for grade in grades:
            prediction = preds[grade["prediction_id"]]
            field = prediction.get("field")
            if field not in FIELDS or type(grade.get("supported")) is not bool or type(grade.get("citation_entails_claim")) is not bool:
                raise ValueError("Actual support and citation-entailment judgments required")
            matched = grade.get("matched_reference_ids", [])
            errors = grade.get("error_types", [])
            if (not isinstance(matched, list) or len(matched) != len(set(matched))
                    or any(r not in gold or gold[r]["field"] != field for r in matched)
                    or not isinstance(errors, list) or len(errors) != len(set(errors)) or any(e not in ERRORS for e in errors)):
                raise ValueError("Invalid reference mapping or field error category")
            if matched and (not grade["supported"] or not grade["citation_entails_claim"]):
                raise ValueError("Unsupported or incorrectly cited claims cannot count as recovered facts")
            if grade["supported"] and errors:
                raise ValueError("A supported interpretation cannot simultaneously carry a material correctness error")
            bucket = counts[method][field]
            bucket["predicted_observations"] += 1
            bucket["supported_observations"] += grade["supported"]
            bucket["entailed_citations"] += grade["citation_entails_claim"]
            diagnostics[method].update(errors)
            covered.update(matched)
        for rid in covered: counts[method][gold[rid]["field"]]["recovered_reference_observations"] += 1
    result = {"status": "independently_human_graded_fields", "pack_hash": pack["pack_hash"], "grader": pack["grader"],
              "scope": "Observed field support and omissions on the stated reviewed sample; not mechanical truth or campaign accuracy.", "methods": {}}
    for method in mapping["methods"]:
        fields = {}
        for field, c in counts[method].items():
            fields[field] = {k: c[k] for k in ("reference_observations", "predicted_observations", "supported_observations", "entailed_citations", "recovered_reference_observations")}
            fields[field].update(supported_precision=c["supported_observations"]/c["predicted_observations"] if c["predicted_observations"] else None,
                                 citation_entailment_rate=c["entailed_citations"]/c["predicted_observations"] if c["predicted_observations"] else None,
                                 reference_recall=c["recovered_reference_observations"]/c["reference_observations"] if c["reference_observations"] else None,
                                 omitted_reference_observations=c["reference_observations"]-c["recovered_reference_observations"])
        result["methods"][method] = {"fields": fields, "diagnostics": dict(diagnostics[method])}
    return result


def review_disagreements(reviews):
    if len(reviews) < 2 or len({r["reviewer"] for r in reviews}) != len(reviews):
        raise ValueError("At least two distinct actual reviewers are required")
    if len({(r["pack"], r["sample_hash"]) for r in reviews}) != 1:
        raise ValueError("Reviewers must review the same frozen pack")
    indexed = {r["reviewer"]: {row["record_id"]: row for row in r["reviews"]} for r in reviews}
    all_ids = sorted(set().union(*(set(rows) for rows in indexed.values())))
    differences = []
    for rid in all_ids:
        rows = {name: values[rid] for name, values in indexed.items() if rid in values}
        labels = {r["label_id"] for r in rows.values()}
        fields = {digest(sorted(r.get("observations", []), key=lambda o: digest(o))) for r in rows.values()}
        if len(rows) != len(indexed) or len(labels) > 1 or len(fields) > 1:
            differences.append({"record_id": rid, "reviews": rows, "missing_reviewers": sorted(set(indexed)-set(rows)),
                                "label_disagreement": len(labels) > 1, "field_difference": len(fields) > 1,
                                "adjudicated_label": None, "adjudicated_observations": None, "rationale": ""})
    return {"status": "pending_independent_adjudication", "pack": reviews[0]["pack"], "sample_hash": reviews[0]["sample_hash"],
            "reviewers": list(indexed), "reviewed_record_union": len(all_ids), "differences": differences,
            "double_reviewed_records": len(set.intersection(*(set(rows) for rows in indexed.values()))),
            "coverage_only_differences": sum(bool(row["missing_reviewers"]) for row in differences),
            "adjudicator": "", "attestation": False, "annotation_source": "human",
            "note": "Field wording differences are flagged for human inspection, not automatically counted as semantic disagreement. No consensus labels are generated."}


def operational_metrics(outputs):
    """Aggregate measured fields only; missing accounting stays unknown."""
    rows = list(outputs)
    modes = Counter(row.get("mode", "unknown") for row in rows)
    times = [r["elapsed_ms"] for r in rows if isinstance(r.get("elapsed_ms"), (int, float))
             and not isinstance(r["elapsed_ms"], bool) and math.isfinite(r["elapsed_ms"]) and r["elapsed_ms"] >= 0]
    calls = [r["model_calls"] for r in rows if type(r.get("model_calls")) is int and r["model_calls"] >= 0]
    all_costs = [r.get("actual_cost_usd", (r.get("operational_summary") or {}).get("actual_billed_cost_usd")) for r in rows]
    costs = [v for v in all_costs if type(v) in (int, float) and math.isfinite(v) and v >= 0]
    attempts = [op for r in rows for op in r.get("operations", [])]
    accepted = sum(str(r.get("mode", "")).startswith("meta") for r in rows)
    human_accepted = sum((r.get("review") or {}).get("decision") == "accepted_for_investigation" for r in rows)
    return {"attempted_rows": len(rows), "modes": dict(modes), "accepted_model_outputs": accepted,
            "fallback_rows": sum(bool(r.get("fallback_reason")) for r in rows),
            "rejected_observations_or_labels": sum(len(r.get("rejected", [])) for r in rows),
            "fallback_reasons": dict(Counter(str(r["fallback_reason"]) for r in rows if r.get("fallback_reason"))),
            "latency_measured_rows": len(times), "latency_p50_ms": statistics.median(times) if times else None,
            "latency_p95_ms": sorted(times)[math.ceil(.95*len(times))-1] if len(times) >= 30 else None,
            "latency_p95_minimum_sample": 30, "latency_p95_status": "descriptive_sample_quantile" if len(times) >= 30 else "insufficient_sample",
            "logical_model_calls": sum(calls) if len(calls) == len(rows) else None,
            "cost_measured_rows": len(costs), "actual_cost_usd": sum(costs) if rows and len(costs) == len(rows) else None,
            "actual_cost_per_accepted_output_usd": sum(costs)/accepted if accepted and len(costs) == len(rows) else None,
            "human_accepted_drafts": human_accepted,
            "actual_cost_per_human_accepted_draft_usd": sum(costs)/human_accepted if human_accepted and len(costs) == len(rows) else None,
            "model_ids": sorted({r["model_id"] for r in rows if r.get("model_id")}),
            "instrumented_rows": sum("operations" in r for r in rows),
            "recorded_transport_attempts": len(attempts),
            "schema_rejected_attempts": sum(op.get("validation") == "rejected" for op in attempts),
            "reserved_upper_bound_usd": sum(op.get("reserved_upper_bound_usd", 0) for op in attempts) if attempts else None,
            "observed_token_cost_estimate_usd": sum(op["observed_token_cost_estimate_usd"] for op in attempts) if attempts and all(op.get("observed_token_cost_estimate_usd") is not None for op in attempts) else None,
            "note": "Empirical quantiles describe only these recorded attempts, including fallbacks; p95 is withheld below 30 measured rows and is never a population SLA. Logical calls exclude transport retries; unavailable actual billing is null, never zero or a token-cap estimate."}


def material_fact_rubric(tasks):
    """An unfilled contract for an independent domain grader, not an answer key."""
    return {"version": 1, "kind": "independent_material_fact_rubric", "task_set_hash": digest(tasks),
            "author": "", "reviewer_profile": {"role": "", "experience": ""}, "annotation_source": "human", "attestation": False,
            "authored_at": "", "authored_without_participant_answers": False,
            "instructions": "Define acceptable packets from original reports and records before seeing participant answers or conditions. Preserve symptoms versus suspected causes versus workshop findings, denial, unknowns, numbers and identifiers. Mark consequential errors explicitly. Do not use model drafts as gold.",
            "tasks": [{"task_id": t["task_id"], "original_sources": t.get("source_documents", [t.get("source", {})]), "material_facts": [], "consequential_errors": [],
                       "acceptable_packet_requirements": [], "ambiguities": [], "review_complete": False} for t in tasks]}


def validate_material_fact_rubric(rubric, tasks, *, participants=()):
    if (rubric.get("kind") != "independent_material_fact_rubric" or rubric.get("task_set_hash") != digest(tasks)
            or rubric.get("annotation_source") != "human" or rubric.get("attestation") is not True
            or not rubric.get("authored_at") or rubric.get("authored_without_participant_answers") is not True
            or not str(rubric.get("author", "")).strip() or rubric["author"] in participants):
        raise ValueError("A task-matched rubric from an independent named human grader is required")
    require_expertise(rubric)
    try:
        authored = datetime.fromisoformat(rubric["authored_at"].replace("Z", "+00:00"))
        if authored.tzinfo is None:
            raise ValueError
    except (ValueError, TypeError, AttributeError) as exc:
        raise ValueError("Record the rubric's actual authored_at timestamp with timezone") from exc
    rows = rubric.get("tasks", [])
    if len(rows) != len(tasks) or {r.get("task_id") for r in rows} != {t["task_id"] for t in tasks}:
        raise ValueError("Every task needs exactly one material-fact rubric")
    task_index = {t["task_id"]: t for t in tasks}
    for row in rows:
        if row.get("review_complete") is not True or not row.get("acceptable_packet_requirements"):
            raise ValueError("Independently define an acceptable packet for every task")
        facts = row.get("material_facts", [])
        if not facts or len({f.get("fact_id") for f in facts}) != len(facts):
            raise ValueError("Each task needs uniquely identified material source facts")
        for fact in facts:
            if (not str(fact.get("fact_id", "")).strip() or not str(fact.get("interpretation", "")).strip()
                    or not str(fact.get("source_id", "")).strip() or not str(fact.get("quote", "")).strip()
                    or fact.get("field") not in FIELDS or type(fact.get("consequential")) is not bool):
                raise ValueError("Material facts need source identity, exact quote, field, interpretation and consequential status")
            task = task_index[row["task_id"]]
            documents = task.get("source_documents", [])
            if not documents and task.get("source"):
                source = task["source"]
                documents = [{"source_id": source.get("record_id", row["task_id"]), "text": source["text"]}]
            sources = {d["source_id"]: d["text"] for d in documents}
            if fact["source_id"] not in sources or fact["quote"] not in sources[fact["source_id"]]:
                raise ValueError("A material-fact quote must occur in the identified original task record")
        for key in ("acceptable_packet_requirements", "consequential_errors", "ambiguities"):
            if not isinstance(row.get(key), list) or any(not isinstance(x, str) or not x.strip() for x in row[key]):
                raise ValueError("Rubric requirements/errors/ambiguities must be explicit strings")
    return {row["task_id"]: row for row in rows}


def adjudicate_reviews(disagreements, completed, *, original_reviews):
    """Validate an independently resolved record while retaining all disagreement."""
    if (completed.get("annotation_source") != "human" or completed.get("attestation") is not True
            or not str(completed.get("adjudicator", "")).strip()
            or completed["adjudicator"] in disagreements["reviewers"]
            or completed.get("source_disagreements_sha256") != digest(disagreements)):
        raise ValueError("Independent named adjudicator and matching disagreement hash required")
    require_expertise(completed)
    expected = {r["record_id"]: r for r in disagreements["differences"]}
    decisions = completed.get("decisions", [])
    if len(decisions) != len(expected) or {r.get("record_id") for r in decisions} != set(expected):
        raise ValueError("Resolve or explicitly retain every disagreement; no dropped records")
    for decision in decisions:
        if decision.get("resolution") not in {"adjudicated", "unresolved"} or not str(decision.get("rationale", "")).strip():
            raise ValueError("Each adjudication needs a resolution and rationale")
        if decision["resolution"] == "adjudicated" and (not isinstance(decision.get("label_id"), str) or not isinstance(decision.get("observations"), list)):
            raise ValueError("Adjudicated judgments need a label and independently reviewed fields")
    return {"status": "independently_adjudicated_with_disagreement_retained", "source_disagreements": disagreements,
            "original_reviews": original_reviews, "adjudication": completed,
            "unresolved_records": [r["record_id"] for r in decisions if r["resolution"] == "unresolved"],
            "note": "Adjudication is a separate record. Original reviewers' labels and disagreement are never overwritten."}
