"""Regression checks for evaluation integrity, not tests that assert better scores."""
from datetime import date
import numpy as np
import pandas as pd
import pytest

from src.eval.improvement_metrics import (rate,classification,calibration,precision_coverage,retrieval,paired_campaign_difference)
from src.eval.improvement_protocol import (check_development,require_disjoint,require_final_test,write_once)
from src.eval.improvement_detection import feature_rows,scored_alerts,error_inventory,slices
from src.eval.improvement_monitoring import monitoring


def test_zero_support_is_unavailable_not_perfect_or_zero():
    assert rate(0,0,"campaigns")["value"] is None
    assert rate(0,100,"campaigns")["ci95"][0]==0
    assert rate(100,100,"campaigns")["ci95"][1]==1
    assert rate(5,8,"campaigns")["ci95"]==pytest.approx([.30574239460262737,.8631557141764026])


def test_missing_predictions_and_abstention_cannot_shrink_accuracy_denominator():
    result=classification(["pump","pump","hose"],["pump",None,"other_unclear"])
    assert result["accuracy"]["numerator"]==1
    assert result["accuracy"]["denominator"]==3
    assert result["accepted_precision"]["value"]==1
    assert result["coverage"]["value"]==1/3
    assert result["per_label"]["hose"]["recall"]["value"]==0


def test_reliability_includes_probability_one_and_preserves_brier_denominator():
    report=calibration([0,1,0,1],[0,1,1,0],reference_probability=.5)
    assert report["brier"]==.5
    assert report["brier_numerator"]==2 and report["brier_denominator"]==4
    assert sum(b["n"] for b in report["reliability"])==4
    assert report["ece"]==.5
    with pytest.raises(ValueError):calibration([0],[1.1],reference_probability=.5)


def test_precision_coverage_cannot_accept_unclear_as_a_specific_answer():
    curve=precision_coverage(["pump","other_unclear"],["pump","other_unclear"],[[.9,.1],[.1,.9]],[.5,.95])
    assert curve[0]["coverage"]["value"]==.5
    assert curve[1]["coverage"]["value"]==0
    assert curve[1]["accepted_precision"]["value"] is None


def query(labels):
    return dict(query_id="q",eval_class="novel_true",candidates=[dict(candidate_id=str(i),relevant=y,score=10-i) for i,y in enumerate(labels)])


def test_retrieval_requires_real_positive_and_negative_controls_and_fixed_k():
    with pytest.raises(ValueError,match="positive AND negative"):retrieval([query([0]*6)])
    with pytest.raises(ValueError,match="positive AND negative"):retrieval([query([1]*6)])
    with pytest.raises(ValueError,match="k distinct"):retrieval([query([1,0])])
    report=retrieval([query([0,1,0,0,0,1])])
    assert report["queries"][0]["precision"]["value"]==1/5
    assert report["queries"][0]["recall"]["value"]==1/2


def test_paired_recall_difference_keeps_baseline_misses():
    r=paired_campaign_difference(["a"],["a","b"],["a","b","c","d"])
    assert r["value"]==.25 and r["denominator"]==4
    with pytest.raises(ValueError):paired_campaign_difference(["foreign"],[],["a"])


def test_opened_windows_and_overlapping_calibration_fail_closed():
    with pytest.raises(ValueError,match="Opened"):check_development(pd.DataFrame({"day":["2021-01-01"]}),"day")
    with pytest.raises(ValueError):check_development(pd.DataFrame({"day":["2019-99-31"]}),"day")
    with pytest.raises(ValueError,match="overlap"):require_disjoint(["a"],["b"],["a"])
    require_disjoint(["a"],["b"],["c"])


def test_test_reservation_is_not_a_completed_test(tmp_path):
    with pytest.raises(ValueError,match="not a frozen"):require_final_test({"status":"reserved"})
    with pytest.raises(ValueError,match="incomplete"):
        require_final_test(dict(status="data_frozen",data_hashes={"x":"hash"},outcome_end="2028-12-30"),today="2027-12-31")
    p=tmp_path/"result.json";write_once(p,{"score":0})
    with pytest.raises(FileExistsError):write_once(p,{"score":1})
    assert '"score": 0' in p.read_text()


def complaints():
    return pd.DataFrame([dict(datea=d.date().isoformat(),odino=str(i),make="FORD",model="F 150",year=2017,
                              component="FUEL SYSTEM",label_id="pump",text="Engine stalled; no diagnosis.",severe=False,severity_known=True)
                         for i,d in enumerate(pd.date_range("2017-01-02",periods=30,freq="7D"))])


def test_future_complaints_cannot_change_prior_features():
    c=complaints();before=feature_rows(c,end="2017-07-01")
    future=c.iloc[:1].copy();future["datea"]="2019-01-01";future["odino"]="future";future["severe"]=True
    after=feature_rows(pd.concat([c,future],ignore_index=True),end="2017-07-01")
    assert before==after and before
    for row in before:assert max(row["evidence_dates"])<row["available_at"]
    with pytest.raises(ValueError,match="Duplicate"):feature_rows(pd.concat([c,c]),end="2017-07-01")


def test_scored_alerts_preserve_cooldown_and_boundary():
    rows=feature_rows(complaints(),end="2018-01-01")
    chosen=scored_alerts(rows,[1.]*len(rows),threshold=.5,start="2017-01-01",end="2018-01-01")
    assert chosen
    assert all((date.fromisoformat(b["available_at"])-date.fromisoformat(a["available_at"])).days>=91 for a,b in zip(chosen,chosen[1:]))


def test_monitoring_censors_late_alerts_and_does_not_silently_drop_unresolved():
    report=monitoring([],[],[dict(available_at="2020-01-01",confirmed=None),dict(available_at="2020-12-31",confirmed=False)],outcome_end="2020-12-31")
    assert report["mature_alerts"]==1 and report["censored_alerts"]==1
    assert report["unresolved_mature_alerts"]==1
    assert report["precision"]["value"] is None
    assert report["signals"]


def test_operating_point_cannot_promote_failed_gates_or_test_tuning():
    from src.eval.improvement_models import choose_operating_point
    row=dict(split="development_validation",precision=.4,recall=.9,mature_alerts=20,utility=100,threshold=.5)
    assert choose_operating_point([row]) is None
    with pytest.raises(ValueError):choose_operating_point([dict(row,split="test")])


def test_local_models_and_calibration_on_disjoint_toy_groups(monkeypatch):
    # Optional research dependencies are isolated from production requirements.
    from pathlib import Path
    dependency_dir=Path(__file__).resolve().parents[3]/".ml-deps"
    monkeypatch.syspath_prepend(str(dependency_dir))
    from src.eval.improvement_models import binary_model,fit_calibrator
    x=np.arange(40,dtype=float).reshape(-1,1);y=(x[:,0]>=20).astype(int)
    for kind in ["logistic","gradient_boosting"]:
        fitted=binary_model(kind,17).fit(x,y)
        p=fitted.predict_proba([[0],[39]])[:,1]
        assert 0<=p[0]<p[1]<=1
    fit=fit_calibrator(np.arange(20),[0]*10+[1]*10,method="platt",fit_ids=["fit"],calibration_ids=["cal"],evaluation_ids=["eval"])
    probs=fit([0,19]);assert 0<=probs[0]<probs[1]<=1
    with pytest.raises(ValueError,match="overlap"):
        fit_calibrator([0,1],[0,1],method="platt",fit_ids=["x"],calibration_ids=["x"],evaluation_ids=[])
    with pytest.raises(ValueError,match="support"):
        fit_calibrator([0,1],[0,1],method="platt",fit_ids=[],calibration_ids=["cal"],evaluation_ids=[])


def test_monitoring_volume_includes_zero_report_days():
    m=monitoring([],[],[],outcome_end="2020-12-31",current_window=["2020-01-01","2020-01-14"])
    assert m["alerts_per_week"]["denominator"]==2
    assert m["alerts_per_week"]["value"]==0


def test_dashboard_rejects_hand_edited_scores_and_promotion_claims():
    from scripts import ml_improvement_report as publisher
    import copy,json
    path=publisher.ROOT/"reports/improvement/results.json"
    report=json.loads(path.read_text())
    original=publisher.dashboard_payload(report,path)
    assert original["source_sha256"]==publisher.digest(path)
    changed=copy.deepcopy(report);changed["historical_baseline"][0]["value"]=1.
    with pytest.raises(ValueError,match="values"):publisher.dashboard_payload(changed,path)
    changed=copy.deepcopy(report);changed["promoted"]=True
    with pytest.raises(ValueError,match="unpromoted"):publisher.dashboard_payload(changed,path)
