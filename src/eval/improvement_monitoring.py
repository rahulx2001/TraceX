"""Offline monitoring summaries; no production action or automatic promotion."""
from __future__ import annotations

from collections import Counter
import numpy as np
from src.eval.improvement_metrics import rate


def categorical_drift(reference, current):
    a,b=Counter(reference),Counter(current)
    if not reference or not current:return dict(total_variation=None,reference_n=len(reference),current_n=len(current))
    keys=sorted(set(a)|set(b))
    distance=.5*sum(abs(a[k]/len(reference)-b[k]/len(current)) for k in keys)
    return dict(total_variation=distance,reference_n=len(reference),current_n=len(current),
                new_values=sorted(set(b)-set(a)),counts={k:dict(reference=a[k],current=b[k]) for k in keys})


def monitoring(reference, current, alerts, *, outcome_end, detected_campaigns=None, all_campaigns=None,
               reference_window=None, current_window=None):
    from datetime import date,timedelta
    def weekly_count(n,window):
        if window is None:return None
        days=(date.fromisoformat(window[1])-date.fromisoformat(window[0])).days+1
        if days<=0:raise ValueError("Invalid observation window")
        return dict(numerator=n,denominator=days/7,value=n/(days/7),unit="count per calendar week, including quiet days")
    end=date.fromisoformat(outcome_end)
    mature=[a for a in alerts if date.fromisoformat(a["available_at"])+timedelta(days=364)<=end]
    unresolved=[a for a in mature if a.get("confirmed") is None]
    observed=[a for a in mature if a.get("confirmed") is not None]
    precision=rate(sum(bool(a["confirmed"]) for a in observed),len(observed),"mature alerts with outcomes recorded")
    if unresolved:
        precision["reason"]="Incomplete mature outcomes; available-case estimate is not the deployment gate"
    recall=None
    if all_campaigns is not None:
        if detected_campaigns is None or not set(detected_campaigns).issubset(set(all_campaigns)):
            raise ValueError("Missing or out-of-scope campaign outcomes")
        recall=rate(len(set(detected_campaigns)),len(set(all_campaigns)),"all eligible campaigns including misses")
    drift={field:categorical_drift([r.get(field,"__missing__") for r in reference],[r.get(field,"__missing__") for r in current])
           for field in ["make","component","model_year","predicted_label"]}
    signals=[]
    if unresolved:signals.append("mature outcomes incomplete: review needed")
    if any(v["total_variation"] is not None and v["total_variation"]>=.2 for v in drift.values()):signals.append("categorical distribution shift: investigate")
    if len(observed)>=30 and not unresolved and precision["ci95"][1]<.8:signals.append("precision below target: human review required")
    return dict(records=len(current),alerts=len(alerts),mature_alerts=len(mature),unresolved_mature_alerts=len(unresolved),
                reference_records_per_week=weekly_count(len(reference),reference_window),
                current_records_per_week=weekly_count(len(current),current_window),
                alerts_per_week=weekly_count(len(alerts),current_window),
                censored_alerts=len(alerts)-len(mature),precision=precision,recall=recall,
                abstention=rate(sum(r.get("predicted_label") in [None,"other_unclear"] for r in current),len(current),"received complaints"),
                drift=drift,signals=signals,action="review only; no automatic deployment or threshold change")
