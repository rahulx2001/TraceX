"""Synthetic fixtures test evidence gates; they are never human study results."""
import copy
import json

import pytest

from scripts import evidence_benchmark as eb, investigation_study as live, reviewer_study as prepared
from src.eval import evidence_review as er


PROFILE = {"role": "Synthetic test engineer", "experience": "Fixture only; not a participant"}


def save(path, value):
    path.write_text(json.dumps(value))
    return path


def test_field_grading_keeps_negation_error_and_empty_output_omissions():
    source = [{"record_id": "r", "text": "No fire. Model year 2018."}]
    reference = [{"record_id": "r", "field_review_complete": True, "observations": [
        {"field": "negation", "value": "No fire", "quote": "No fire.", "polarity": "denied"}]}]
    predictions = {"bad": {"r": {"observations": [{"field": "negation", "polarity": "affirmed", "value": "Fire occurred", "evidence": {"quote": "No fire."}}]}},
                   "empty": {"r": {"mode": "failed", "observations": []}}}
    pack, mapping = er.field_grading_pack(source, reference, predictions)
    with pytest.raises(ValueError, match="human"):
        er.score_field_grading(pack, mapping)
    pack.update(grader="Synthetic grader", reviewer_profile=PROFILE, annotation_source="human", attestation=True)
    for item in pack["items"]:
        item["review_complete"] = True
        for grade in item["grades"]:
            grade.update(supported=False, citation_entails_claim=False, error_types=["negation_reversed"])
    result = er.score_field_grading(pack, mapping)
    assert result["methods"]["bad"]["diagnostics"]["negation_reversed"] == 1
    assert result["methods"]["bad"]["fields"]["negation"]["citation_entailment_rate"] == 0
    assert result["methods"]["empty"]["fields"]["negation"]["omitted_reference_observations"] == 1
    assert result["methods"]["empty"]["diagnostics"]["empty_outputs"] == 1
    pack["annotation_source"] = "model"
    with pytest.raises(ValueError, match="human"):
        er.score_field_grading(pack, mapping)


@pytest.fixture
def frozen_fixture(tmp_path, monkeypatch):
    monkeypatch.setattr(eb, "OUT", tmp_path)
    data = tmp_path/"data"; data.mkdir(); monkeypatch.setattr(eb, "DATA", data)
    (data/"held.parquet").write_bytes(b"synthetic input bytes, not real reserved data")
    protocol = {"input_hashes": {"held": eb.file_sha256(data/"held.parquet")}, "policy": {"detector": "count"}}
    save(tmp_path/"protocol.json", protocol)
    hashes = {"model": "synthetic-v1"}
    monkeypatch.setattr(eb, "frozen_hashes", lambda: dict(hashes))
    reviews = {}
    for name in eb.PACKS:
        pack = {"name": name, "rows": [{"record_id": "1", "text": "No fire."}, {"record_id": "2", "text": "Pump failed."}], "labels": {"other_unclear": "uncertain"}}
        pack["sample_hash"] = eb.digest(pack)
        save(tmp_path/f"{name}.json", pack)
        doc = {"pack": name, "sample_hash": pack["sample_hash"], "annotation_source": "human", "attestation": True,
               "reviewer": f"Synthetic {name}", "review_schema_version": 2, "reviewer_profile": PROFILE,
               "reviews": [{"record_id": str(i), "label_id": "other_unclear", "observations": [], "field_review_complete": True} for i in (1, 2)]}
        reviews[name] = save(tmp_path/f"fixture-{name}.json", doc)
    return tmp_path, reviews, hashes


def test_review_expertise_fields_and_partial_second_review(frozen_fixture):
    _, reviews, _ = frozen_fixture
    path = reviews["development_review"]
    doc = json.loads(path.read_text()); doc["reviews"] = doc["reviews"][:1]; save(path, doc)
    with pytest.raises(ValueError, match="Incomplete"):
        eb.complete_review(path, "development_review", fields=True)
    assert eb.complete_review(path, "development_review", fields=True, allow_partial=True) == {"1": "other_unclear"}
    doc["reviews"][0]["field_review_complete"] = False; save(path, doc)
    with pytest.raises(ValueError, match="every extraction field"):
        eb.complete_review(path, "development_review", fields=True, allow_partial=True)
    doc["reviews"][0]["field_review_complete"] = True; doc["reviewer_profile"] = {}; save(path, doc)
    with pytest.raises(ValueError, match="experience"):
        eb.complete_review(path, "development_review", fields=True, allow_partial=True)


def test_freeze_precedes_gold_and_attachment_keeps_candidate_hash(frozen_fixture):
    folder, reviews, hashes = frozen_fixture
    with pytest.raises(ValueError, match="No frozen candidate"):
        eb.import_review(reviews["fuel_complaint_review"])
    eb.freeze(reviews["development_review"])
    with pytest.raises(ValueError, match="sealed/unattached"):
        eb.checked_freeze()
    before = (folder/"candidate_freeze.json").read_bytes()
    eb.attach_reviews(reviews["fuel_complaint_review"], reviews["recall_review"], "Synthetic custodian", True)
    frozen, _ = eb.checked_freeze()
    assert frozen["sha256"] == eb.digest(frozen["body"])
    assert len(frozen["human_reviews"]) == 3
    assert (folder/"candidate_freeze.json").read_bytes() == before
    hashes["model"] = "changed"
    with pytest.raises(ValueError, match="changed"):
        eb.checked_freeze()


def test_frozen_inputs_and_human_labels_cannot_change(frozen_fixture):
    folder, reviews, _ = frozen_fixture
    eb.freeze(reviews["development_review"])
    original = (folder/"data/held.parquet").read_bytes()
    (folder/"data/held.parquet").write_bytes(b"changed")
    with pytest.raises(ValueError, match="inputs changed"):
        eb.checked_candidate()
    (folder/"data/held.parquet").write_bytes(original)
    reviews["development_review"].write_text("{}")
    with pytest.raises(ValueError, match="labels changed"):
        eb.checked_candidate()


def test_partial_double_review_retains_coverage_and_adjudication(frozen_fixture):
    _, reviews, _ = frozen_fixture
    first = json.loads(reviews["development_review"].read_text())
    second = copy.deepcopy(first); second["reviewer"] = "Synthetic second"; second["reviews"] = second["reviews"][:1]
    pending = er.review_disagreements([first, second])
    assert pending["double_reviewed_records"] == 1 and pending["coverage_only_differences"] == 1
    completed = {"adjudicator": "Synthetic independent", "annotation_source": "human", "attestation": True,
                 "reviewer_profile": PROFILE, "source_disagreements_sha256": er.digest(pending),
                 "decisions": [{"record_id": "2", "resolution": "unresolved", "rationale": "Second review pending"}]}
    result = er.adjudicate_reviews(pending, completed, original_reviews=[first, second])
    assert result["unresolved_records"] == ["2"] and result["original_reviews"] == [first, second]


def test_workload_zero_months_abstention_and_cost_preflight(monkeypatch):
    from src.ai_layer import budget, config
    alerts = [{"available_at": "2025-02-03"}]
    result = eb.workload_summary(alerts, "2025-01-01", "2025-03-31")
    assert result["monthly_counts"] == {"2025-01": 0, "2025-02": 1, "2025-03": 0}
    assert result["original_alerts"] == alerts
    assert eb.label_metrics(["other_unclear"], ["__abstained__"])["accuracy"] == 0
    monkeypatch.setattr(config, "model_text", lambda: "synthetic-model")
    monkeypatch.setattr(config, "retries", lambda: 2)
    monkeypatch.setattr(config, "backend", lambda: "meta")
    monkeypatch.setitem(budget.RATES, "synthetic-model", (1, 2))
    monkeypatch.setattr(eb, "labels", lambda: {"other_unclear": "unknown"})
    snapshot = {"limit_usd": 10, "reserved_upper_bound_usd": 9}
    result = eb.cost_preflight([{"text": "No fire"}]*10, [{"text": "No fire"}], status=snapshot)
    assert result["remaining_reservation_budget_usd"] == 1
    assert result["maximum_transport_attempts_per_row"] == 3
    assert result["full_estimated_reservation_upper_bound_usd"] == pytest.approx(10*result["batch_estimated_reservation_upper_bound_usd"])
    assert result["actual_billed_cost_usd"] is None
    assert snapshot == {"limit_usd": 10, "reserved_upper_bound_usd": 9}
    monkeypatch.setattr(config, "backend", lambda: "baseten")
    baseten = eb.cost_preflight([{"text": "No fire"}], [{"text": "No fire"}], status=snapshot)
    assert baseten["maximum_transport_attempts_per_row"] == 6
    assert baseten["completion_token_cap_per_attempt"] == 4000
    assert baseten["batch_estimated_reservation_upper_bound_usd"] > 2*result["batch_estimated_reservation_upper_bound_usd"]


def test_missing_billing_and_small_latency_sample_remain_unknown():
    result = er.operational_metrics([{"mode": "meta", "elapsed_ms": n, "model_calls": 1} for n in range(8)])
    assert result["latency_p95_ms"] is None and result["latency_measured_rows"] == 8
    assert result["actual_cost_usd"] is None and result["actual_cost_per_human_accepted_draft_usd"] is None
    assert result["logical_model_calls"] == 8


def test_failed_extraction_retained_without_a_call_or_correct_label(monkeypatch):
    monkeypatch.setattr(eb.ce, "extract", lambda *a, **kw: (_ for _ in ()).throw(RuntimeError("synthetic failure")))
    result = eb.measured_extraction({"text": "No fire"}, {})
    assert result["mode"] == "failed" and result["observations"] == []
    assert result["model_calls"] is None and result["operational_summary"]["actual_billed_cost_usd"] is None


def live_fixture():
    tasks = [{"task_id": f"t{i}", "campaign_id": "fixture", "vehicle_id": f"v{i}", "instruction": "Review the synthetic source",
              "source_ref": {"kind": "campaign_reply", "reply_id": f"reply{i}", "sha256": str(i)*64},
              "source_documents": [{"source_id": f"source{i}", "text": "No fire. Model year 2018."}],
              "deterministic_workflow_scope": "All owner, trace and workshop records",
              "challenge_types": [challenge]} for i, challenge in enumerate(("missing_record", "contradictory_records", "irrelevant_records"), 1)]
    rubric = er.material_fact_rubric(tasks)
    rubric.update(author="Synthetic rubric author", reviewer_profile=PROFILE, attestation=True,
                  authored_at="2026-10-29T00:00:00Z", authored_without_participant_answers=True)
    for row in rubric["tasks"]:
        i = row["task_id"][-1]
        row.update(material_facts=[{"fact_id": "denial", "field": "negation", "interpretation": "Owner denies fire",
                                    "source_id": f"source{i}", "quote": "No fire.", "consequential": True}],
                   acceptable_packet_requirements=["Preserve denial"], review_complete=True)
    study = {"tasks": tasks, "rubric_sha256": er.digest(rubric), "scope": "Synthetic test; never a result"}
    study["study_hash"] = er.digest(study)
    session = {"study_hash": study["study_hash"], "participant": "Synthetic participant", "reviewer_profile": PROFILE,
               "annotation_source": "human", "attestation": True, "assignment": live.assignment(study, "Synthetic participant")}
    rows, runs = [], []
    for i, assigned in enumerate(session["assignment"]):
        row = {**assigned, "answer": "No fire reported", "task_outcome": "completed", "elapsed_ms": 10000,
               "started_at": f"2026-10-30T01:0{i}:00Z", "finished_at": f"2026-10-30T01:0{i}:10Z",
               "phase_events": [{"phase": "task_started", "elapsed_ms": 0}, {"phase": "task_finished", "elapsed_ms": 10000}],
               "run_ids": [], "used_model_assistance": assigned["condition"] != "deterministic_workflow"}
        task = next(t for t in tasks if t["task_id"] == assigned["task_id"])
        if row["used_model_assistance"]:
            row["run_ids"] = [f"run{i}"]
            runs.append({"run_id": f"run{i}", "campaign_id": task["campaign_id"], "vehicle_id": task["vehicle_id"],
                         "assistance_mode": assigned["condition"], "report_sources": [{"source_ref": task["source_ref"]}],
                         "started_at": f"2026-10-30T01:0{i}:02Z", "finished_at": f"2026-10-30T01:0{i}:08Z",
                         "operational_summary": {"actual_billed_cost_usd": None, "transport_attempts": 1}})
        rows.append(row)
    session["results"] = rows
    return study, rubric, session, runs


def test_live_rubric_requires_human_and_exact_source_quote():
    study, rubric, _, _ = live_fixture()
    live.validate_tasks(study)
    with pytest.raises(ValueError, match="independent named human"):
        er.validate_material_fact_rubric(er.material_fact_rubric(study["tasks"]), study["tasks"])
    er.validate_material_fact_rubric(rubric, study["tasks"])
    rubric["tasks"][0]["material_facts"][0]["quote"] = "Fire occurred"
    with pytest.raises(ValueError, match="original task record"):
        er.validate_material_fact_rubric(rubric, study["tasks"])


def test_live_assignment_timer_source_mode_and_replay_gates():
    study, _, session, runs = live_fixture()
    live.validate_session(session, study)
    row = next(r for r in session["results"] if r["run_ids"])
    task = next(t for t in study["tasks"] if t["task_id"] == row["task_id"])
    indexed = {r["run_id"]: r for r in runs}
    live.validate_runs(row, task, indexed)
    run = indexed[row["run_ids"][0]]
    for field, value, match in [("replay", True, "replays"), ("assistance_mode", "wrong", "mode"),
                                 ("report_sources", [], "same frozen"), ("started_at", "2026-10-29T01:00:00Z", "out-of-window")]:
        changed = {**run, field: value}
        with pytest.raises(ValueError, match=match):
            live.validate_runs(row, task, {**indexed, run["run_id"]: changed})
    session["results"][0]["phase_events"][0]["elapsed_ms"] = 2
    with pytest.raises(ValueError, match="timer"):
        live.validate_session(session, study)


def test_live_failed_task_and_deviation_are_retained():
    study, _, session, _ = live_fixture()
    row = next(r for r in session["results"] if r["condition"] == "deterministic_workflow")
    task = next(t for t in study["tasks"] if t["task_id"] == row["task_id"])
    row.update(task_outcome="incomplete", used_model_assistance=True, protocol_deviation="Opened the wrong mode before stopping", failure_note="Stopped without a run")
    live.validate_session(session, study)
    assert live.validate_runs(row, task, {}) == []


def test_live_blind_grading_partial_double_review_and_unknown_cost(tmp_path):
    study, rubric, session, runs = live_fixture()
    study_path = save(tmp_path/"study.json", study); rubric_path = save(tmp_path/"rubric.json", rubric)
    session_path = save(tmp_path/"session.json", session); artifacts = save(tmp_path/"runs.json", {"runs": runs})
    out = tmp_path/"analysis"
    result = live.analyze(study_path, [session_path], [artifacts], rubric_path, out)
    assert result["attempted_tasks"] == 3 and result["time_saved_percent"] is None
    assert all(r["actual_billed_cost_usd"] is None for r in result["conditions"].values())
    grade_path = next(out.glob("grading-*.json")); grade = json.loads(grade_path.read_text())
    assert all("condition" not in i and "elapsed_ms" not in i and "participant" not in i for i in grade["items"])
    grade.update(grader="Synthetic independent grader", attestation=True, reviewer_profile=PROFILE)
    for item in grade["items"]:
        item.update(review_complete=True, acceptable_packet=True, covered_fact_ids=["denial"], corrections=0)
    primary = save(tmp_path/"primary.json", grade)
    second = copy.deepcopy(grade); second["grader"] = "Synthetic second grader"; second["items"] = second["items"][:1]
    second["items"][0].update(acceptable_packet=False, covered_fact_ids=[], corrections=1)
    secondary = save(tmp_path/"secondary.json", second)
    result = live.analyze(study_path, [session_path], [artifacts], rubric_path, tmp_path/"graded", [primary, secondary])
    assert result["double_graded_tasks"] == 1 and len(result["grading_disagreements"]) == 1
    assert all(g["actual_cost_per_acceptable_packet_usd"] is None for c in result["conditions"].values() for g in c["grading"])
    grade["items"][0]["answer"] = "changed"
    with pytest.raises(ValueError, match="changed"):
        live.validate_grading(grade, json.loads(grade_path.read_text()), {session["participant"]})


def test_prepared_study_new_exports_require_expertise_and_outcome():
    study, _, _, _ = live_fixture()
    plan = prepared.assign(study, "Synthetic participant")
    session = {"session_schema_version": 2, "study_hash": study["study_hash"], "participant": "Synthetic participant",
               "annotation_source": "human", "attestation": True, "assignment": plan,
               "results": [{**plan[0], "answer": "Stopped", "elapsed_ms": 10000, "task_outcome": "failed",
                            "started_at": "2026-10-30T01:00:00Z", "finished_at": "2026-10-30T01:00:10Z"}]}
    with pytest.raises(ValueError, match="experience"):
        prepared.validate_session(session, study)
    session["reviewer_profile"] = PROFILE
    prepared.validate_session(session, study)
    session["results"][0].pop("task_outcome")
    with pytest.raises(ValueError, match="actual"):
        prepared.validate_session(session, study)
