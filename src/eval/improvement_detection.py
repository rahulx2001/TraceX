"""Causal features and diagnostic slices using unchanged repaired matching rules."""
from __future__ import annotations

from collections import Counter
from datetime import timedelta
import re
import numpy as np
import pandas as pd

from src.eval.defect_prediction import KEY, candidates, evaluate
from src.eval.improvement_metrics import rate

FEATURES = ["record_count","new_complaints","prior_count","expected_count","tail_score","count_4w",
            "acceleration","severity_count","severity_missing_fraction","recall_mention_fraction","specificity_fraction",
            "distinct_models","stall_fraction","leak_fraction","duplicate_fraction"]
RECALL = re.compile(r"\brecall\w*\b|\bcampaign\b",re.I)


def norm(v):return " ".join(str(v).upper().split())


def feature_rows(complaints, *, end, window=13):
    c=complaints.copy()
    if c.odino.astype(str).duplicated().any():raise ValueError("Duplicate complaint IDs must be resolved before feature extraction")
    # The scope and classifier identities already use canonical make/component.
    # Model normalization is used only for a count feature, never to relax matching.
    c=c[c.datea.le(end)].copy()
    c["day"]=pd.to_datetime(c.datea)
    c["normalized_text"]=c.text.map(lambda t:" ".join(re.findall(r"\w+",str(t).casefold())))
    c["recall_mention"]=c.text.map(lambda t:bool(RECALL.search(str(t))))
    rows=candidates(c,window=window,end=end)
    for row in rows:
        available=pd.Timestamp(row["available_at"])
        mask=pd.Series(True,index=c.index)
        for key in KEY:mask &= c[key].eq(row[key])
        part=c[mask & c.day.ge(available-pd.Timedelta(weeks=window)) & c.day.lt(available)]
        recent=part[part.day.ge(available-pd.Timedelta(weeks=4))]
        before=part[part.day.lt(available-pd.Timedelta(weeks=4))]
        n=len(part)
        known=part.get("severity_known",pd.Series(False,index=part.index)).fillna(False)
        severe=part.get("severe",pd.Series(False,index=part.index)).fillna(False)
        all_component=c[c.make.eq(row["make"]) & c.component.eq(row["component"]) & c.day.ge(available-pd.Timedelta(weeks=window)) & c.day.lt(available)]
        texts=part.text.astype(str)
        row.update(count_4w=len(recent),acceleration=len(recent)/4-len(before)/max(1,window-4),
                   severity_count=int(severe.sum()),severity_missing_fraction=1-float(known.mean()) if n else 1,
                   recall_mention_fraction=float(part.recall_mention.mean()) if n else 0,
                   specificity_fraction=n/max(1,len(all_component)),distinct_models=len(set(part.model.map(norm))),
                   stall_fraction=float(texts.str.contains(r"\bstall\w*\b|\bloss of power\b",case=False,regex=True).mean()) if n else 0,
                   leak_fraction=float(texts.str.contains(r"\bleak\w*\b|\bfuel odor\b",case=False,regex=True).mean()) if n else 0,
                   duplicate_fraction=1-part.normalized_text.nunique()/n if n else 0,
                   evidence_ids=sorted(part.odino.astype(str)),evidence_dates=sorted(set(part.datea)),
                   evidence_models=sorted(set(part.model.map(norm))))
    return rows


def matrix(rows):
    return np.array([[r[k] for k in FEATURES] for r in rows],dtype=float).reshape(len(rows),len(FEATURES))


def labelled_candidates(rows, recalls, *, start,end):
    r=recalls[recalls.rcdate.between(start,end)]
    result=evaluate(rows,r,start=start,end=end)
    return [dict(row,outcome=int(bool(row["matched_campaigns"]))) for row in result["alert_details"] if row["full_followup"]]


def scored_alerts(rows,scores,*,threshold,start,end):
    if len(rows)!=len(scores):raise ValueError("Scores and candidates must align")
    last,alerts={},[]
    for row,score in sorted(zip(rows,scores),key=lambda x:(x[0]["available_at"],tuple(x[0][k] for k in KEY))):
        if not np.isfinite(score):raise ValueError("Nonfinite score")
        day=pd.Timestamp(row["available_at"]);key=tuple(row[k] for k in KEY)
        if not start<=row["available_at"]<=end or score<threshold:continue
        if key in last and (day-last[key]).days<91:continue
        alerts.append(dict(row,ranking_score=float(score)));last[key]=day
    return alerts


def summarize(result):
    return dict(recall=rate(result["hits"],result["campaigns"],"campaigns"),
                precision=rate(result["confirmed_mature_alerts"],result["mature_alerts"],"mature alert episodes"),
                harmonic_objective=result["objective"],
                harmonic_note="Different evaluation units; not per-example F1; no joint interval estimated",
                alerts=result["alerts"],mature_alerts=result["mature_alerts"],
                censored_alerts=result["censored_alerts"],median_lead_weeks=result["median_lead_weeks"],
                lead_support=result["hits"],
                utility=5*result["hits"]-2*(result["mature_alerts"]-result["confirmed_mature_alerts"])-.1*result["alerts"])


def slices(alerts,recalls,*,start,end):
    """Each stratum keeps its own explicit campaign and mature-alert denominator."""
    output={}
    for dimension in ["make","component","label_id"]:
        values=sorted(set(recalls[dimension]) | {a[dimension] for a in alerts})
        output[dimension]={str(v):summarize(evaluate([a for a in alerts if a[dimension]==v],recalls[recalls[dimension]==v],start=start,end=end)) for v in values}
    output["campaign_issue_year"]={}
    for year in sorted(set(recalls[recalls.rcdate.between(start,end)].rcdate.str[:4])):
        r=recalls[recalls.rcdate.str.startswith(year)]
        m=evaluate(alerts,r,start=start,end=end)
        output["campaign_issue_year"][year]={"recall":rate(m["hits"],m["campaigns"],"campaigns issued in year"),
                                               "note":"Alerts across the full evaluation period may lead this year's recalls; precision by alert year is separate."}
    output["alert_issue_year"]={}
    for year in sorted({a["available_at"][:4] for a in alerts}):
        m=evaluate([a for a in alerts if a["available_at"].startswith(year)],recalls,start=start,end=end)
        output["alert_issue_year"][year]={"precision":rate(m["confirmed_mature_alerts"],m["mature_alerts"],"mature alerts issued in year"),"alerts":m["alerts"]}
    return output


def error_inventory(result,recalls,complaints,*,start,end):
    """Machine evidence audit, not human causal adjudication. Never duplicate rows to hit a quota."""
    fp=[];fn=[]
    for a in result["alert_details"]:
        if a["full_followup"] and not a["matched_campaigns"]:
            evidence=complaints[complaints.odino.astype(str).isin(a.get("evidence_ids",[]))]
            fp.append(dict(alert_id="|".join([a["available_at"]]+[str(a[k]) for k in KEY]),make=a["make"],label_id=a["label_id"],
                           evidence_ids=a.get("evidence_ids",[]),
                           observations={"recall_mention":int(evidence.text.map(lambda t:bool(RECALL.search(str(t)))).sum()),
                                         "weak_evidence":len(evidence)<3,"duplicate":a.get("duplicate_fraction",0)>0},
                           review_status="machine_inspected; human cause unassigned",
                           cause_candidates=["wrong category","recall mention","duplicate","weak evidence","wrong scope","timing/leakage","label ambiguity"]))
    for campaign,part in recalls[recalls.rcdate.between(start,end)].groupby("campno"):
        if campaign in result["campaign_hits"]:continue
        usable=set();any_evidence=set()
        for r in part.itertuples():
            day=pd.Timestamp(r.rcdate)
            c=complaints[complaints.make.eq(r.make)&complaints.component.eq(r.component)]
            d=pd.to_datetime(c.datea)
            available=d-pd.to_timedelta(d.dt.dayofweek,unit="D")+pd.Timedelta(days=7)
            c=c[available.between(day-pd.Timedelta(days=364),day-pd.Timedelta(days=7))]
            any_evidence.update(c.odino.astype(str))
            usable.update(c[c.label_id.eq(r.label_id)&c.label_id.ne("other_unclear")].odino.astype(str))
        fn.append(dict(campaign=campaign,make=sorted(set(part.make)),labels=sorted(set(part.label_id)),
                       prior_any_fuel_complaints=len(any_evidence),prior_matching_label_complaints=len(usable),
                       observations={"no_prior_evidence":not any_evidence,"label_ambiguity":"other_unclear" in set(part.label_id),
                                     "matching_label_gap":bool(any_evidence) and not usable},
                       review_status="machine_inspected; human cause unassigned"))
    return dict(false_positives=fp,false_negatives=fn,requested_each=50,available_fp=len(fp),available_fn=len(fn),
                complete_50_each=len(fp)>=50 and len(fn)>=50,note="No unique errors were invented or repeated to meet the requested quota.")
