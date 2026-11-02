"""Prepare a counterbalanced human task study; never synthesize participants or timings."""
from __future__ import annotations

import argparse
import json
import math
import statistics
from datetime import datetime
from pathlib import Path

from scripts.defect_repair import ROOT, write_json
from scripts.evidence_benchmark import OUT as BENCH, digest, load_pack
from src.eval.evidence_review import material_fact_rubric, require_expertise, validate_material_fact_rubric

OUT = ROOT/"reports/hackathon/reviewer_study"


def prepare():
    if (OUT/"study.json").exists():
        raise ValueError("Study tasks already frozen; do not replace after participants begin")
    comparison = json.loads((BENCH/"development_comparison.json").read_text())
    folder = ROOT/comparison["predictions_directory"]
    source_rows = {r["record_id"]: r for r in load_pack("development_review")["rows"]}
    tasks = []
    # Include all bounded development attempts, including fallbacks; no success-only selection.
    for path in sorted(folder.glob("*.json")):
        pred = json.loads(path.read_text()); row = source_rows[pred["record_id"]]
        if pred["input_hash"] != digest(row):
            raise ValueError("Task source does not match the model input")
        tasks.append({"task_id": row["record_id"], "source": row, "assistance": pred["meta"],
                      "instruction": "Prepare a short evidence packet: identify the reported part/symptom and timing, distinguish denial and uncertainty, quote supporting words, and state what remains unknown. Do not diagnose or invent a repair."})
    if len(tasks) < 4:
        raise ValueError("At least four distinct task inputs are required")
    body = {"version": 1, "tasks": tasks, "design": "Each participant reviews each task once; alternating conditions with participant-hash counterbalancing and reversed order for half of assignments.",
            "scope": "Complaint-to-evidence-packet task using public historical reports, not a full field repair study.",
            "timing": "Browser monotonic elapsed time including time in hidden tabs; self-recorded, not independent observation.",
            "quality": "Independent named human grading required before productivity claims; failures and corrections retained.",
            "participants": 0, "results_status": "pending_real_participants", "prediction_accuracy": None}
    body["study_hash"] = digest(body)
    write_json(OUT/"study.json", body)
    template = (ROOT/"scripts/templates/reviewer_study.html").read_text()
    (OUT/"study.html").write_text(template.replace("__STUDY_DATA__", json.dumps(body, ensure_ascii=False).replace("<", "\\u003c")))
    write_json(OUT/"results.json", {"status": "pending_real_participants_and_independent_grading", "participants": 0,
                                  "completed_tasks": 0, "time_saved_percent": None, "quality_score": None})
    print(f"Prepared {len(tasks)} tasks; 0 participants; no measured benefit. {OUT/'study.html'}")


def validate_session(data, study):
    if (data.get("study_hash") != study["study_hash"] or data.get("annotation_source") != "human"
            or data.get("attestation") is not True or not str(data.get("participant", "")).strip()):
        raise ValueError("Matching study and named participant's human attestation required")
    if data.get("session_schema_version", 1) >= 2:
        require_expertise(data)
    assignment = assign(study, data["participant"])
    if data.get("assignment") != assignment:
        raise ValueError("Task assignment was altered; counterbalancing cannot be reconstructed")
    tasks = {t["task_id"] for t in study["tasks"]}; seen = set()
    for row in data.get("results", []):
        ms = row.get("elapsed_ms")
        if row.get("task_id") not in tasks or row["task_id"] in seen or row.get("condition") not in {"manual", "assisted"}:
            raise ValueError("Invalid, duplicate or unknown task")
        if not isinstance(ms, (int,float)) or isinstance(ms, bool) or not math.isfinite(ms) or ms <= 0:
            raise ValueError("A real positive elapsed duration is required")
        if not isinstance(row.get("answer"), str) or not row["answer"].strip() or not row.get("started_at") or not row.get("finished_at"):
            raise ValueError("Task answer and recorded start/end times required")
        if data.get("session_schema_version", 1) >= 2 and row.get("task_outcome") not in {"completed", "failed", "incomplete"}:
            raise ValueError("Retain the actual completed, failed or incomplete task outcome")
        expected = assignment[len(seen)]
        if row["task_id"] != expected["task_id"] or row["condition"] != expected["condition"]:
            raise ValueError("Completed task order differs from the recorded assignment")
        try:
            elapsed = (datetime.fromisoformat(row["finished_at"].replace("Z", "+00:00"))-datetime.fromisoformat(row["started_at"].replace("Z", "+00:00"))).total_seconds()*1000
        except (TypeError, ValueError) as exc:
            raise ValueError("Invalid task timestamps") from exc
        if elapsed <= 0 or abs(elapsed-ms)>5000:
            raise ValueError("Elapsed time and start/end timestamps disagree; investigate the original recording")
        seen.add(row["task_id"])
    if not seen:
        raise ValueError("Session has no actual completed tasks")


def assign(study, participant):
    h = 2166136261
    for char in participant:
        n = ord(char)
        if n > 65535: n = 0xD800+((n-0x10000)>>10)
        h = ((h^n)*16777619)&0xffffffff
    rows = [{"task_id": t["task_id"], "condition": "assisted" if (i+h%2)%2 else "manual"} for i,t in enumerate(study["tasks"])]
    return list(reversed(rows)) if (h>>1)%2 else rows


def analyze(paths, grading_path, rubric_path=None):
    study = json.loads((OUT/"study.json").read_text())
    if study["study_hash"] != digest({k:v for k,v in study.items() if k != "study_hash"}):
        raise ValueError("Frozen study tasks changed")
    sessions = [json.loads(p.read_text()) for p in paths]
    for s in sessions: validate_session(s, study)
    if len({s["participant"] for s in sessions}) != len(sessions):
        raise ValueError("Duplicate participant exports; explicitly merge their actual tasks first")
    rows = [{**r, "participant": s["participant"]} for s in sessions for r in s["results"]]
    out = {"participants": len(sessions), "completed_tasks": len(rows), "assigned_tasks": len(sessions)*len(study["tasks"]),
           "scope": "Prepared-draft review; excludes live inference waiting and the full investigation workflow.",
           "participant_roles": [s.get("reviewer_profile", {"status": "not_recorded_in_legacy_export"}) for s in sessions],
           "recorded_task_outcomes": {outcome: sum(r.get("task_outcome", "legacy_unspecified") == outcome for r in rows)
                                      for outcome in ("completed", "failed", "incomplete", "legacy_unspecified")},
           "unfinished_tasks": len(sessions)*len(study["tasks"])-len(rows), "study_hash": study["study_hash"],
           "status": "timings_recorded_quality_pending", "time_saved_percent": None,
           "conditions": {mode: {"tasks": sum(r["condition"]==mode for r in rows),
                         "median_seconds": statistics.median([r["elapsed_ms"]/1000 for r in rows if r["condition"]==mode]) if any(r["condition"]==mode for r in rows) else None}
                         for mode in ["manual", "assisted"]},
           "note": "Observed sample timings only. Task difficulty, order and small samples limit conclusions. No field effectiveness or accuracy claim."}
    tasks = {t["task_id"]: t for t in study["tasks"]}
    rubric = json.loads(rubric_path.read_text()) if rubric_path else None
    material = validate_material_fact_rubric(rubric, study["tasks"], participants={s["participant"] for s in sessions}) if rubric else None
    if not grading_path:
        # Grader sees source and answer, but neither condition nor task duration.
        write_json(OUT/f"grading-pack-{digest(rows)[:12]}.json", {"study_hash": study["study_hash"],
            "grader": "", "annotation_source": "human", "attestation": False,
            "reviewer_profile": {"role": "", "experience": ""},
            "rubric_sha256": digest(rubric) if rubric else None,
            "instructions": "An independently completed task-specific material-fact rubric is required before scoring. Judge each submitted packet against that rubric and original source. Condition and timing are hidden. Preserve failures and disagreements.",
            "grades": [{"participant": r["participant"], "task_id": r["task_id"], "source": tasks[r["task_id"]]["source"]["text"],
                        "answer": r["answer"], "rubric": material[r["task_id"]] if material else None,
                        "acceptable_packet": None, "covered_fact_ids": [], "unsupported_claim_details": [],
                        "missed_facts": None, "unsupported_claims": None, "corrections": None} for r in rows]})
    if grading_path:
        if not material:
            raise ValueError("Independent task-specific --rubric is required before quality scoring")
        grades = json.loads(grading_path.read_text())
        if (grades.get("study_hash") != study["study_hash"] or grades.get("attestation") is not True
                or grades.get("annotation_source") != "human" or not str(grades.get("grader", "")).strip()
                or grades["grader"] in {s["participant"] for s in sessions}):
            raise ValueError("Independent named human grader and attestation required")
        require_expertise(grades)
        if grades.get("rubric_sha256") != digest(rubric):
            raise ValueError("Grading must use the unchanged task-specific material-fact rubric")
        indexed = {}
        original_answers = {(r["participant"], r["task_id"]): r["answer"] for r in rows}
        for g in grades.get("grades", []):
            key = (g.get("participant"), g.get("task_id"))
            if key in indexed or not isinstance(g.get("acceptable_packet"), bool):
                raise ValueError("Duplicate or invalid task grade")
            if (key not in original_answers or g.get("answer") != original_answers[key]
                    or g.get("source") != tasks[key[1]]["source"]["text"] or g.get("rubric") != material[key[1]]):
                raise ValueError("Grading must retain the original participant answer, task source and rubric")
            for field in ["missed_facts", "unsupported_claims", "corrections"]:
                if type(g.get(field)) is not int or g[field] < 0:
                    raise ValueError("Actual nonnegative quality counts required")
            reference = material.get(g.get("task_id"))
            if not reference:
                raise ValueError("Unknown rubric task")
            facts = {f["fact_id"] for f in reference["material_facts"]}
            covered = g.get("covered_fact_ids", [])
            unsupported = g.get("unsupported_claim_details", [])
            if (not isinstance(covered, list) or len(covered) != len(set(covered)) or set(covered)-facts
                    or g["missed_facts"] != len(facts-set(covered)) or not isinstance(unsupported, list)
                    or any(not isinstance(item, str) or not item.strip() for item in unsupported)
                    or len(unsupported) != g["unsupported_claims"]):
                raise ValueError("Quality counts must be grounded in material-fact IDs and explicit unsupported claims")
            consequential = {f["fact_id"] for f in reference["material_facts"] if f["consequential"]}
            if g["acceptable_packet"] and (consequential-set(covered) or unsupported):
                raise ValueError("Consequential omissions or unsupported claims cannot form an acceptable packet")
            indexed[key] = g
        if set(indexed) != {(r["participant"],r["task_id"]) for r in rows}:
            raise ValueError("Grade all recorded tasks, including failures")
        for mode in ["manual", "assisted"]:
            selected = [indexed[(r["participant"],r["task_id"])] for r in rows if r["condition"]==mode]
            out["conditions"][mode].update({"acceptable_packets": sum(g["acceptable_packet"] for g in selected),
                 **{f: sum(g[f] for g in selected) for f in ["missed_facts", "unsupported_claims", "corrections"]}})
        out["status"] = "observed_timings_and_independently_graded_sample"
        out["grader"] = grades["grader"]
        out["rubric_sha256"] = digest(rubric)
        # Keep raw conditions: an unbalanced small sample does not justify a single productivity percentage.
    write_json(OUT/f"results-{digest(out)[:16]}.json", out)
    print(json.dumps(out, indent=2))


def main():
    p=argparse.ArgumentParser(description=__doc__); p.add_argument("phase",choices=["prepare","prepare-rubric","analyze"])
    p.add_argument("--sessions",nargs="*",type=Path);p.add_argument("--grading",type=Path);p.add_argument("--rubric",type=Path);a=p.parse_args()
    if a.phase=="prepare":prepare()
    elif a.phase=="prepare-rubric":
        study=json.loads((OUT/"study.json").read_text())
        destination=OUT/"material-fact-rubric-template.json"
        with destination.open("x") as f:json.dump(material_fact_rubric(study["tasks"]),f,indent=2)
        print("Prepared an unfilled independent task rubric. No grading or outcome was created.")
    elif not a.sessions:p.error("Provide real participant exports with --sessions")
    else:analyze(a.sessions,a.grading,a.rubric)


if __name__ == "__main__": main()
