import json

import pytest

from scripts import evidence_benchmark as eb, reviewer_study as study


@pytest.fixture
def pack(tmp_path, monkeypatch):
    monkeypatch.setattr(eb, "OUT", tmp_path)
    data = {"name": "development_review", "rows": [{"record_id": "1", "text": "No leak."}, {"record_id": "2", "text": "Pump failed."}],
            "labels": {"other_unclear": "uncertain", "fuel_pump_failure": "pump"}}
    data["sample_hash"] = eb.digest(data)
    (tmp_path/"development_review.json").write_text(json.dumps(data))
    return data, tmp_path


def test_no_human_review_cannot_freeze_or_score(pack):
    with pytest.raises(ValueError, match="human"):
        eb.freeze(None, None, None)
    with pytest.raises(ValueError, match="human reviews"):
        eb.evaluate()


def test_incomplete_and_machine_labels_refused(pack):
    data, path = pack
    r = {"pack": data["name"], "sample_hash": data["sample_hash"], "annotation_source": "human", "attestation": True,
         "reviewer": "Real reviewer", "reviews": [{"record_id": "1", "label_id": "other_unclear"}]}
    export = path/"review.json"; export.write_text(json.dumps(r))
    with pytest.raises(ValueError, match="Incomplete"):
        eb.complete_review(export, data["name"])
    r["reviews"].append({"record_id": "2", "label_id": "fuel_pump_failure"}); r["annotation_source"]="model"
    export.write_text(json.dumps(r))
    with pytest.raises(ValueError, match="human"):
        eb.complete_review(export, data["name"])
    r["annotation_source"]="human"; export.write_text(json.dumps(r))
    assert eb.complete_review(export, data["name"]) == {"1":"other_unclear", "2":"fuel_pump_failure"}


def test_human_import_rejects_invented_quotes(pack):
    data, path=pack
    r={"pack":data["name"],"sample_hash":data["sample_hash"],"annotation_source":"human","attestation":True,"reviewer":"Reviewer",
       "reviews":[{"record_id":"1","label_id":"other_unclear","observations":[{"field":"negation","polarity":"denied","quote":"Invented source"}]}]}
    export=path/"r.json";export.write_text(json.dumps(r))
    with pytest.raises(ValueError,match="quote"):
        eb.import_review(export)


def test_equal_monthly_workload_keeps_original_alert_order():
    a=[{"available_at":"2025-01-06"},{"available_at":"2025-01-13"},{"available_at":"2025-02-03"}]
    b=[{"available_at":"2025-01-20"},{"available_at":"2025-03-03"}]
    left,right=eb.matched_workload(a,b)
    assert left==a[:1] and right==b[:1]


def test_majority_unknown_baseline_cannot_hide_specific_defect_misses():
    result = eb.label_metrics(["other_unclear"]*9+["fuel_pump_failure"], ["other_unclear"]*10)
    assert result["accuracy"] == result["always_other_accuracy"] == .9
    assert result["specific_defect_accuracy"] == 0
    assert result["macro_f1"] < .5
    assert result["confusion_matrix"]["fuel_pump_failure"]["other_unclear"] == 1
    with pytest.raises(ValueError): eb.label_metrics([], [])


def session(st):
    assignment=study.assign(st,"Reviewer")
    return {"participant":"Reviewer","study_hash":"frozen","annotation_source":"human","attestation":True,"assignment":assignment,
            "results":[{**assignment[0],"answer":"Source reviewed","elapsed_ms":10000,"started_at":"2026-10-30T01:00:00Z","finished_at":"2026-10-30T01:00:10Z"}]}


def test_study_requires_actual_answers_durations_and_counterbalancing():
    st={"study_hash":"frozen","tasks":[{"task_id":"a"},{"task_id":"b"}]}
    s=session(st); study.validate_session(s,st)
    s["results"][0]["elapsed_ms"]=0
    with pytest.raises(ValueError,match="positive"):
        study.validate_session(s,st)
    s=session(st);s["assignment"][0]["condition"]="fabricated"
    with pytest.raises(ValueError,match="assignment"):
        study.validate_session(s,st)
    s=session(st);s["results"][0]["elapsed_ms"]=100000
    with pytest.raises(ValueError,match="disagree"):
        study.validate_session(s,st)
    s=session(st);s["annotation_source"]="model"
    with pytest.raises(ValueError,match="human"):
        study.validate_session(s,st)
