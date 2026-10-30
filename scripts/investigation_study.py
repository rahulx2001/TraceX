"""A separately frozen live investigation study. Never generates participants or gold."""
from __future__ import annotations

import argparse
import json
import math
import re
import statistics
from datetime import datetime
from pathlib import Path

from scripts.defect_repair import ROOT
from src.eval.evidence_review import digest, material_fact_rubric, require_expertise, validate_material_fact_rubric

CONDITIONS = ("deterministic_workflow", "extraction_only", "full_investigation")
PHASES = {"task_started", "workflow_opened", "reading", "waiting_for_model", "lookup", "correction", "review", "task_finished"}


def write_new(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x") as file:
        json.dump(data, file, indent=2, ensure_ascii=False)


def validate_tasks(body):
    tasks = body.get("tasks", [])
    if len(tasks) < 3 or len({t.get("task_id") for t in tasks}) != len(tasks):
        raise ValueError("At least three unique reviewed task candidates are required for three conditions")
    coverage = set()
    for task in tasks:
        if any(not str(task.get(key, "")).strip() for key in ("task_id", "campaign_id", "vehicle_id", "instruction")):
            raise ValueError("Each task needs a task ID, campaign, vehicle and instruction")
        source = task.get("source_ref") or {}
        if source.get("kind") not in {"interaction", "campaign_reply"} or not re.fullmatch(r"[0-9a-f]{64}", str(source.get("sha256", ""))):
            raise ValueError("Each task must identify the same durable source reference in every condition")
        if source["kind"] == "interaction":
            if not source.get("interaction_id") or not source.get("turn_ids") or len(source["turn_ids"]) != len(set(source["turn_ids"])):
                raise ValueError("Interaction references need the original interaction and distinct selected turn IDs")
        elif not source.get("reply_id"):
            raise ValueError("Reply references need the original recorded reply ID")
        documents = task.get("source_documents", [])
        if not documents or len({d.get("source_id") for d in documents}) != len(documents):
            raise ValueError("Task records need distinct source document IDs")
        if any(not isinstance(d.get("text"), str) or not d["text"].strip() or not d.get("source_id") for d in documents):
            raise ValueError("Record the original source text available through the existing workflow")
        if not task.get("deterministic_workflow_scope"):
            raise ValueError("Describe the full existing record/trace/workshop workflow available to the deterministic condition")
        flags = task.get("challenge_types", [])
        if not isinstance(flags, list) or any(f not in {"missing_record", "contradictory_records", "irrelevant_records"} for f in flags):
            raise ValueError("Use the predeclared missing, contradictory or irrelevant-record challenge types")
        coverage.update(flags)
    if coverage != {"missing_record", "contradictory_records", "irrelevant_records"}:
        raise ValueError("The task set must include missing, contradictory and irrelevant records before condition comparison")
    return tasks


def prepare(tasks_path, directory):
    body = json.loads(tasks_path.read_text()); tasks = validate_tasks(body)
    write_new(directory/"task-candidates.json", {"status": "pending_independent_task_rubric", "tasks": tasks, "task_set_hash": digest(tasks)})
    write_new(directory/"rubric-template.json", material_fact_rubric(tasks))
    print("Prepared task candidates and an unfilled independent rubric. No study is frozen and no participants exist.")


def freeze(tasks_path, rubric_path, directory):
    tasks = validate_tasks(json.loads(tasks_path.read_text()))
    rubric = json.loads(rubric_path.read_text())
    validate_material_fact_rubric(rubric, tasks)
    body = {"version": 1, "kind": "live_investigation_comparison", "tasks": tasks,
            "conditions": list(CONDITIONS), "rubric_sha256": digest(rubric), "rubric_author": rubric["author"],
            "scope": "End-to-end preparation of a reviewable investigation packet on the stated tasks, not OEM repair productivity or accident prevention.",
            "timing": "Starts before task reveal and opening the normal workflow; includes live waiting, lookups, correction, review and hidden-tab time.",
            "design": "Each participant sees each task once. Task-condition Latin-square rotation and reversed task order counterbalance conditions across participants. Deterministic uses the complete existing source/trace/workshop workflow, not an English-keyword substitute.",
            "participants": 0, "results_status": "pending_real_participants", "replay_allowed": False}
    body["study_hash"] = digest(body)
    write_new(directory/"study.json", body)
    template = (ROOT/"scripts/templates/investigation_study.html").read_text()
    with (directory/"study.html").open("x") as file:
        file.write(template.replace("__STUDY_DATA__", json.dumps(body, ensure_ascii=False).replace("<", "\\u003c")))
    print("Frozen live study from an independently attested task rubric. Participants and usefulness results remain pending.")


def assignment(study, participant):
    value = 2166136261
    for char in participant:
        value = ((value ^ ord(char)) * 16777619) & 0xffffffff
    rows = [{"task_id": task["task_id"], "condition": CONDITIONS[(index + value % 3) % 3]} for index, task in enumerate(study["tasks"])]
    return list(reversed(rows)) if (value // 3) % 2 else rows


def millis(timestamp):
    value = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
    if value.tzinfo is None:
        raise ValueError("An actual timezone-aware timestamp is required")
    return value.timestamp()*1000


def validate_session(session, study):
    if (session.get("study_hash") != study["study_hash"] or session.get("annotation_source") != "human"
            or session.get("attestation") is not True or not str(session.get("participant", "")).strip()):
        raise ValueError("A named participant's matching study and personal human attestation are required")
    require_expertise(session)
    plan = assignment(study, session["participant"])
    if session.get("assignment") != plan:
        raise ValueError("Condition assignment changed")
    results = session.get("results", [])
    if not results or len(results) > len(plan):
        raise ValueError("Retain actual attempted tasks; do not create participants with no work")
    for index, row in enumerate(results):
        if any(row.get(k) != plan[index][k] for k in ("task_id", "condition")):
            raise ValueError("Tasks must retain the recorded order and condition")
        elapsed = row.get("elapsed_ms")
        if type(elapsed) not in (int, float) or not math.isfinite(elapsed) or elapsed <= 0:
            raise ValueError("A measured positive end-to-end elapsed duration is required")
        try:
            actual = millis(row["finished_at"]) - millis(row["started_at"])
        except (ValueError, KeyError, TypeError) as exc:
            raise ValueError("Task start/end timestamps are required") from exc
        if actual <= 0 or abs(actual - elapsed) > 5000:
            raise ValueError("Task elapsed and wall-clock timestamps disagree")
        if row.get("task_outcome") not in {"completed", "failed", "incomplete"} or not str(row.get("answer", "")).strip():
            raise ValueError("Retain each actual packet or an explanation of its failure/incompletion")
        if row.get("protocol_deviation") and not str(row["protocol_deviation"]).strip():
            raise ValueError("Describe an actual protocol deviation explicitly")
        events = row.get("phase_events", [])
        if not events or events[0].get("phase") != "task_started" or events[0].get("elapsed_ms") != 0:
            raise ValueError("The recorded live timer must start before the task workflow")
        last = -1
        for event in events:
            ms = event.get("elapsed_ms")
            if event.get("phase") not in PHASES or type(ms) not in (int, float) or not math.isfinite(ms) or not last <= ms <= elapsed:
                raise ValueError("Invalid or reordered task phase telemetry")
            last = ms
        if events[-1].get("phase") != "task_finished" or events[-1]["elapsed_ms"] != elapsed:
            raise ValueError("Task completion must close the live timer")
    return results


def validate_runs(row, task, indexed):
    ids = row.get("run_ids", [])
    if not isinstance(ids, list) or len(ids) != len(set(ids)):
        raise ValueError("Use unique original run IDs")
    deviation = bool(str(row.get("protocol_deviation", "")).strip())
    if row["condition"] == "deterministic_workflow" and not deviation:
        if ids or row.get("used_model_assistance") is not False:
            raise ValueError("The deterministic condition cannot include model drafts; retain full record/workshop workflow access")
        return []
    if deviation and not ids:
        if row.get("task_outcome") == "completed" or not str(row.get("failure_note", "")).strip():
            raise ValueError("A deviation without original run evidence must retain a failed/incomplete outcome and explanation")
        return []
    if not ids:
        if row["task_outcome"] == "completed" or not str(row.get("failure_note", "")).strip():
            raise ValueError("Assisted tasks need recorded live run evidence, or a retained failure explanation")
        return []
    runs = []
    for rid in ids:
        run = indexed.get(rid)
        if not run or run.get("replay"):
            raise ValueError("Original live run evidence is required; recorded replays belong to the separate prepared-draft study")
        if run.get("campaign_id") != task["campaign_id"] or run.get("vehicle_id") != task["vehicle_id"]:
            raise ValueError("Run belongs to a different task's campaign or vehicle")
        if run.get("assistance_mode", "full_investigation") != row["condition"] and not deviation:
            raise ValueError("Recorded assistance mode differs from assigned study condition")
        refs = [s.get("source_ref") for s in run.get("report_sources", [])]
        if task["source_ref"] not in refs:
            raise ValueError("All conditions must use the same frozen original report source")
        if millis(run["started_at"]) < millis(row["started_at"])-1000 or millis(run.get("finished_at") or run["started_at"]) > millis(row["finished_at"])+1000:
            raise ValueError("Prepared or out-of-window drafts cannot be presented as a live waiting task")
        runs.append(run)
    return runs


def grading_pack(study, rows, rubric):
    material = validate_material_fact_rubric(rubric, study["tasks"], participants={r["participant"] for r in rows})
    mapping, items = {}, []
    for row in rows:
        blind_id = digest([study["study_hash"], row["participant"], row["task_id"]])[:24]
        mapping[blind_id] = {k: row[k] for k in ("participant", "task_id", "condition")}
        task = next(t for t in study["tasks"] if t["task_id"] == row["task_id"])
        items.append({"item_id": blind_id, "task_id": row["task_id"], "answer": row["answer"],
                      "source_documents": task["source_documents"], "rubric": material[row["task_id"]],
                      "acceptable_packet": None, "covered_fact_ids": [], "unsupported_claims": [], "corrections": None,
                      "review_complete": False, "note": ""})
    items.sort(key=lambda item: item["item_id"])
    identity = [{k: item[k] for k in ("item_id", "task_id", "answer", "source_documents", "rubric")} for item in items]
    pack = {"kind": "blind_live_study_grading", "study_hash": study["study_hash"], "rubric_sha256": digest(rubric), "items": items,
            "grader": "", "reviewer_profile": {"role": "", "experience": ""}, "annotation_source": "human", "attestation": False,
            "identity_sha256": digest(identity), "instructions": "Grade the answer against the task-specific independent rubric. Condition, time and participant are withheld. Keep failed/incomplete answers, material omissions and unsupported interpretations in the denominator."}
    return pack, {"study_hash": study["study_hash"], "identity_sha256": pack["identity_sha256"], "items": mapping}


def validate_grading(grading, expected, participants, *, allow_partial=False):
    if (grading.get("annotation_source") != "human" or grading.get("attestation") is not True
            or not str(grading.get("grader", "")).strip() or grading["grader"] in participants):
        raise ValueError("An independent named human grader is required")
    require_expertise(grading)
    if (grading.get("study_hash") != expected["study_hash"] or grading.get("rubric_sha256") != expected["rubric_sha256"]
            or grading.get("identity_sha256") != expected["identity_sha256"]):
        raise ValueError("Blind grading sources, answers or rubric changed")
    originals = {item["item_id"]: item for item in expected["items"]}
    items = grading.get("items", [])
    ids = [item.get("item_id") for item in items]
    if (not ids or len(ids) != len(set(ids)) or set(ids)-set(originals)
            or (not allow_partial and set(ids) != set(originals))):
        raise ValueError("Primary grader must cover every attempted task; additional graders may independently grade a subset")
    for item in items:
        if any(item.get(k) != originals[item["item_id"]].get(k) for k in ("task_id", "answer", "source_documents", "rubric")):
            raise ValueError("Blind grading sources, answers or rubric changed")
    values = {}
    for item in grading["items"]:
        facts = {f["fact_id"] for f in item["rubric"]["material_facts"]}
        covered = item.get("covered_fact_ids", [])
        if item.get("review_complete") is not True or type(item.get("acceptable_packet")) is not bool:
            raise ValueError("Every attempted packet needs an independent completion/acceptability judgment")
        if not isinstance(covered, list) or len(covered) != len(set(covered)) or set(covered)-facts:
            raise ValueError("Map covered facts only to the task rubric")
        unsupported = item.get("unsupported_claims", [])
        if not isinstance(unsupported, list) or any(not str(x).strip() for x in unsupported) or type(item.get("corrections")) is not int or item["corrections"] < 0:
            raise ValueError("Actual unsupported-claim descriptions and correction counts are required")
        consequential = {f["fact_id"] for f in item["rubric"]["material_facts"] if f["consequential"]}
        if item["acceptable_packet"] and (consequential-set(covered) or unsupported):
            raise ValueError("A packet with consequential omissions or unsupported claims cannot be marked acceptable")
        values[item["item_id"]] = {"acceptable_packet": item["acceptable_packet"], "material_omissions": len(facts-set(covered)),
            "consequential_omissions": len(consequential-set(covered)), "unsupported_claims": len(unsupported), "corrections": item["corrections"]}
    return values


def analyze(study_path, sessions, artifacts, rubric_path, directory, grading_paths=()):
    study = json.loads(study_path.read_text())
    if study.get("study_hash") != digest({k: v for k, v in study.items() if k != "study_hash"}):
        raise ValueError("Frozen live study changed")
    rubric = json.loads(rubric_path.read_text())
    if digest(rubric) != study["rubric_sha256"]:
        raise ValueError("Independent rubric changed after study freeze")
    participants, rows, used_runs = set(), [], set()
    indexed = {}
    for path in artifacts:
        body = json.loads(path.read_text())
        runs = body.get("investigation_drafts", body.get("runs", [body] if body.get("run_id") else []))
        for run in runs:
            if run["run_id"] in indexed and indexed[run["run_id"]] != run:
                raise ValueError("Conflicting copies of a recorded run")
            indexed[run["run_id"]] = run
    tasks = {t["task_id"]: t for t in study["tasks"]}
    for path in sessions:
        session = json.loads(path.read_text())
        if session.get("participant") in participants:
            raise ValueError("Duplicate participant exports require explicit merge, never double-counting")
        for row in validate_session(session, study):
            runs = validate_runs(row, tasks[row["task_id"]], indexed)
            ids = {r["run_id"] for r in runs}
            if ids & used_runs:
                raise ValueError("One recorded run cannot be counted for multiple study tasks")
            used_runs.update(ids)
            rows.append({**row, "participant": session["participant"], "reviewer_profile": session["reviewer_profile"], "runs": runs,
                         "comparison_eligible": not bool(str(row.get("protocol_deviation", "")).strip())})
        participants.add(session["participant"])
    if not rows:
        raise ValueError("Real attempted tasks are required")
    if millis(rubric["authored_at"]) > min(millis(row["started_at"]) for row in rows):
        raise ValueError("The independent task rubric must precede actual participation")
    pack, mapping = grading_pack(study, rows, rubric)
    output = {"study_hash": study["study_hash"], "scope": study["scope"], "participants": len(participants),
              "participant_roles": list({r["participant"]: r["reviewer_profile"] for r in rows}.values()),
              "attempted_tasks": len(rows), "assigned_tasks": len(participants)*len(tasks), "unstarted_tasks": len(participants)*len(tasks)-len(rows),
              "protocol_deviations": [{"participant": row["participant"], "task_id": row["task_id"], "condition": row["condition"],
                                       "note": row["protocol_deviation"]} for row in rows if not row["comparison_eligible"]],
              "status": "live_timings_recorded_independent_grading_pending", "time_saved_percent": None, "conditions": {},
              "note": "Small observational task sample. Report time and quality together. No population-level productivity, real repair effectiveness or accidents-prevented claim."}
    grades = []
    for path in grading_paths:
        document = json.loads(path.read_text())
        if document.get("grader") in {g[0] for g in grades}:
            raise ValueError("Duplicate grader exports cannot count as independent double grading")
        grades.append((document["grader"], validate_grading(document, pack, participants, allow_partial=bool(grades))))
    for condition in CONDITIONS:
        selected = [r for r in rows if r["condition"] == condition]
        ops = [run.get("operational_summary", {}) for row in selected for run in row["runs"]]
        actual = [o.get("actual_billed_cost_usd") for o in ops]
        have_billing = bool(ops) and all(type(x) in (int, float) and math.isfinite(x) and x >= 0 for x in actual)
        result = {"tasks": len(selected), "completed_tasks": sum(r["task_outcome"] == "completed" for r in selected),
                  "comparison_eligible_tasks": sum(r["comparison_eligible"] for r in selected),
                  "comparison_eligible_median_seconds": statistics.median([r["elapsed_ms"]/1000 for r in selected if r["comparison_eligible"]]) if any(r["comparison_eligible"] for r in selected) else None,
                  "failed_or_incomplete_tasks": sum(r["task_outcome"] != "completed" for r in selected),
                  "median_seconds": statistics.median([r["elapsed_ms"]/1000 for r in selected]) if selected else None,
                  "task_elapsed_seconds": [r["elapsed_ms"]/1000 for r in selected],
                  "recorded_runs": len(ops), "actual_billed_cost_usd": sum(actual) if have_billing else None,
                  "transport_attempts": sum(o["transport_attempts"] for o in ops) if ops and all(type(o.get("transport_attempts")) is int for o in ops) else None,
                  "fallback_runs": sum(bool(o.get("fallback")) for o in ops), "grading": []}
        ids = [item_id for item_id, meta in mapping["items"].items() if meta["condition"] == condition]
        for grader, values in grades:
            graded_ids = set(ids)&set(values)
            totals = {key: sum(values[i][key] for i in graded_ids) for key in ("acceptable_packet", "material_omissions", "consequential_omissions", "unsupported_claims", "corrections")}
            totals["actual_cost_per_acceptable_packet_usd"] = sum(actual)/totals["acceptable_packet"] if have_billing and totals["acceptable_packet"] and len(graded_ids) == len(ids) else None
            result["grading"].append({"grader": grader, "graded_tasks": len(graded_ids), **totals})
        output["conditions"][condition] = result
    if grades:
        output["status"] = "live_task_timings_and_independent_packet_grading_recorded"
        output["grading_disagreements"] = [{"item_id": i, "grades": {name: values[i] for name, values in grades if i in values}}
            for i in mapping["items"] if len({digest(values[i]) for _, values in grades if i in values}) > 1]
        output["double_graded_tasks"] = sum(sum(i in values for _, values in grades) > 1 for i in mapping["items"])
    stem = digest(output)[:16]
    write_new(directory/f"results-{stem}.json", output)
    if not grades:
        write_new(directory/f"grading-{stem}.json", pack)
        write_new(directory/f"private-mapping-{stem}.json", mapping)
    print(json.dumps(output, indent=2))
    return output


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("phase", choices=["prepare", "freeze", "analyze"])
    parser.add_argument("--tasks", type=Path); parser.add_argument("--rubric", type=Path); parser.add_argument("--study", type=Path)
    parser.add_argument("--sessions", nargs="+", type=Path); parser.add_argument("--artifacts", nargs="*", type=Path, default=[])
    parser.add_argument("--grading", nargs="*", type=Path, default=[]); parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    if args.phase == "prepare":
        if not args.tasks: parser.error("--tasks is required")
        prepare(args.tasks, args.out)
    elif args.phase == "freeze":
        if not args.tasks or not args.rubric: parser.error("--tasks and independently completed --rubric are required")
        freeze(args.tasks, args.rubric, args.out)
    else:
        if not args.study or not args.rubric or not args.sessions: parser.error("--study, --rubric and actual --sessions are required")
        analyze(args.study, args.sessions, args.artifacts, args.rubric, args.out, args.grading)


if __name__ == "__main__":
    main()
