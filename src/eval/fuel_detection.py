"""Experimental local student classifiers and causal, workload-limited alerts.

Student targets are dated Muse Spark labels, not human ground truth. Neither
classifier receives recall descriptions, campaign numbers or future outcomes.
"""
from __future__ import annotations

import math
from collections import defaultdict
from datetime import date, timedelta

import numpy as np
import pandas as pd

from src.eval.defect_prediction import predictive_tail

OTHER = "other_unclear"
KEY = ["make", "component", "label_id"]


def clean_reports(frame):
    return frame[~frame.text.str.contains(r"\brecall\w*\b|\bcampaign\b", case=False, regex=True, na=False)].copy()


def deduplicate_fuel(frame):
    """A complaint filed under both fuel codes counts once, never twice."""
    df = frame[frame.component.isin(["FUEL SYSTEM", "FUEL/PROPULSION SYSTEM"])].copy()
    df["source_component"] = df.component
    df["text_length"] = df.text.str.len()
    df = df.sort_values(["odino", "text_length", "datea", "component"], ascending=[True, False, True, True])
    df = df.drop_duplicates("odino").drop(columns="text_length")
    df["component"] = "FUEL SYSTEM"
    return df.sort_values(["datea", "odino"]).reset_index(drop=True)


def fit_student(vectors, labels, *, method):
    classes = sorted(set(labels))
    if OTHER not in classes:
        raise ValueError("Training requires an explicit abstention/other class")
    y = np.array([classes.index(x) for x in labels])
    x = np.asarray(vectors, dtype=np.float64)
    if x.ndim != 2 or len(y) != len(x) or not np.isfinite(x).all():
        raise ValueError("Invalid training features")
    if method == "centroid":
        weights = np.array([x[y == i].mean(axis=0) for i in range(len(classes))]).T
        weights /= np.maximum(np.linalg.norm(weights, axis=0), 1e-12)
    elif method == "ridge":
        # Fixed regularisation and square-root balancing; no holdout tuning.
        frequency = np.bincount(y, minlength=len(classes))
        sample_weight = np.sqrt(len(y) / (len(classes) * frequency[y]))
        target = np.eye(len(classes))[y]
        design = np.c_[x, np.ones(len(x))]
        weights = np.linalg.solve(design.T @ (design * sample_weight[:, None]) + np.eye(design.shape[1]),
                                  design.T @ (target * sample_weight[:, None]))
    else:
        raise ValueError("Unknown student method")
    return {"classes": classes, "method": method, "weights": weights}


def predict_student(model, vectors):
    x = np.asarray(vectors, dtype=np.float64)
    if model['method'] == 'ridge':
        x = np.c_[x, np.ones(len(x))]
    scores = x @ model['weights']
    ranked = np.argsort(scores, axis=1)
    best, second = ranked[:, -1], ranked[:, -2]
    margin = scores[np.arange(len(x)), best] - scores[np.arange(len(x)), second]
    threshold = .05 if model['method'] == 'ridge' else .03
    labels = [model['classes'][int(i)] if m >= threshold else OTHER for i, m in zip(best, margin)]
    return labels, margin


def features(complaints, *, end):
    """Complete-week counts with 26 prior weeks and fixed 4/13/26-week windows.

Zero history begins at the make's first observed complaint, not at the first
occurrence of a particular defect. The allowed label set was frozen earlier.
"""
    all_dates = pd.to_datetime(complaints.datea)
    frame = complaints[all_dates <= pd.Timestamp(end)].copy()
    frame['day'] = pd.to_datetime(frame.datea)
    frame['week'] = frame.day - pd.to_timedelta(frame.day.dt.dayofweek, unit='D')
    first = frame.groupby('make').week.min().to_dict()
    frame = frame[frame.label_id.ne(OTHER)]
    records = []
    for values, part in frame.groupby(KEY, sort=True):
        counts = part.groupby('week').size()
        weeks = pd.date_range(first[values[0]], end, freq='W-MON')
        series = counts.reindex(weeks, fill_value=0).to_numpy()
        prefix = np.r_[0, series.cumsum()]
        cusum = 0.0
        for i, week in enumerate(weeks):
            available = (week + pd.Timedelta(days=7)).date().isoformat()
            if available > end:
                continue
            before = max(0, i-26)
            expected = (float(prefix[i]-prefix[before])+.5) / max(1, i-before)
            cusum = max(0.0, cusum + series[i] - expected - .25)
            if not series[i]:
                continue
            row = dict(zip(KEY, values)) | {'available_at': available, 'new_count': int(series[i]), 'cusum': cusum}
            for w in (4,13,26):
                boundary = max(0,i+1-w)
                prior_start = max(0,boundary-26)
                history = boundary-prior_start
                recent = int(prefix[i+1]-prefix[boundary])
                prior = int(prefix[boundary]-prefix[prior_start])
                row[f'count_{w}'] = recent
                row[f'tail_{w}'] = predictive_tail(recent, prior+.5, history/(history+w)) if history>=4 else 1.0
            records.append(row)
    return sorted(records,key=lambda x:(x['available_at'],tuple(x[k] for k in KEY)))


def detect(rows, config, *, start, end):
    """Online selection: max 1 alert/week, 2/month, 13-week per-slice cooldown."""
    weekly = defaultdict(list)
    for row in rows:
        if not start <= row['available_at'] <= end:
            continue
        window = config['window']
        count,tail = row[f'count_{window}'],row[f'tail_{window}']
        if config['detector']=='bayes':
            qualifies = count>=config['minimum'] and tail<=config['threshold']
            score = -math.log(max(tail,1e-15))
        elif config['detector']=='count':
            qualifies=count>=config['minimum']; score=float(count)
        elif config['detector']=='cusum':
            qualifies=count>=config['minimum'] and row['cusum']>=config['threshold']; score=row['cusum']
        else:
            raise ValueError('Unknown detector')
        if qualifies:
            weekly[row['available_at']].append(row | {'score':score,'record_count':count})
    last,monthly,alerts={},defaultdict(int),[]
    for day,possible in sorted(weekly.items()):
        if monthly[day[:7]]>=2:
            continue
        possible.sort(key=lambda x:(-x['score'],tuple(x[k] for k in KEY)))
        for row in possible:
            k=tuple(row[n] for n in KEY); stamp=date.fromisoformat(day)
            if k in last and (stamp-last[k]).days<91:
                continue
            alerts.append(row);last[k]=stamp;monthly[day[:7]]+=1;break
    return alerts


def evaluate_period(alerts, recalls, *, start, end, outcome_end):
    """Campaign recall targets start..end; precision follows to outcome_end."""
    targets=recalls[recalls.rcdate.between(start,end)]
    future=recalls[recalls.rcdate.between(start,outcome_end)]
    campaigns=set(targets.campno);hits={};details=[]
    for a in alerts:
        if not start<=a['available_at']<=end:
            raise ValueError('Alert lies outside evaluation window')
        candidates=future[(future.make==a['make'])&(future.component==a['component'])
                          &(future.label_id==a['label_id'])&future.label_id.ne(OTHER)]
        available=date.fromisoformat(a['available_at']);matched=set()
        for r in candidates.itertuples():
            lead=(date.fromisoformat(r.rcdate)-available).days
            if 7<=lead<=364:
                matched.add(r.campno)
                if r.campno in campaigns:
                    hits[r.campno]=max(hits.get(r.campno,0),lead)
        details.append(a|{'matched_campaigns':sorted(matched),
                          'full_followup':available+timedelta(days=364)<=date.fromisoformat(outcome_end)})
    mature=[x for x in details if x['full_followup']]
    confirmed=sum(bool(x['matched_campaigns']) for x in mature)
    recall=len(hits)/len(campaigns) if campaigns else 0.0
    precision=confirmed/len(mature) if mature else None
    return {'campaigns':len(campaigns),'hits':len(hits),'misses':len(campaigns)-len(hits),
            'campaign_recall':recall,'alerts':len(alerts),'mature_alerts':len(mature),
            'confirmed_mature_alerts':confirmed,'episode_precision':precision,
            'median_lead_weeks':float(np.median(list(hits.values()))/7) if hits else None,
            'objective':2*recall*precision/(recall+precision) if precision is not None and recall+precision else 0,
            'campaign_hits':hits,'alert_details':details}


def wilson_interval(hits,total):
    """Descriptive binomial interval; campaigns need not be independent."""
    if not total:return [0.0,1.0]
    z=1.959963984540054;p=hits/total;den=1+z*z/total
    centre=(p+z*z/(2*total))/den
    radius=z*math.sqrt(p*(1-p)/total+z*z/(4*total*total))/den
    return [max(0.0,centre-radius),min(1.0,centre+radius)]


def random_reference(rows,alerts,*,seed):
    """Reference with identical per-month alert counts and cooldown rules.

This conditional historical reference sees the month's candidate set, not
recall outcomes. Refuse a draw if the workload cannot be matched exactly.
"""
    quotas=defaultdict(int)
    for a in alerts:quotas[a['available_at'][:7]]+=1
    rng=np.random.default_rng(seed)
    for _ in range(100):
        selected=[];last={};ok=True
        for month,n in sorted(quotas.items()):
            pool=[r for r in rows if r['available_at'].startswith(month)]
            rng.shuffle(pool);taken=[]
            for row in pool:
                day=date.fromisoformat(row['available_at']);key=tuple(row[k] for k in KEY)
                if key in last and (day-last[key]).days<91:continue
                if any(t['available_at']==row['available_at'] or tuple(t[k] for k in KEY)==key for t in taken):continue
                taken.append(row)
                if len(taken)==n:break
            if len(taken)!=n:ok=False;break
            for row in taken:last[tuple(row[k] for k in KEY)]=date.fromisoformat(row['available_at'])
            selected.extend(taken)
        if ok:return sorted(selected,key=lambda r:(r['available_at'],tuple(r[k] for k in KEY)))
    raise ValueError('Unable to match reference workload; do not compare unequal alert budgets')


def opportunity_bound(complaints,recalls,*,start,end,match_label=True):
    """Diagnostic ceiling for evidence-triggered alerts; never a model score."""
    c=complaints.copy();d=pd.to_datetime(c.datea)
    c['available_at']=(d-pd.to_timedelta(d.dt.dayofweek,unit='D')+pd.Timedelta(days=7)).dt.strftime('%Y-%m-%d')
    target=recalls[recalls.rcdate.between(start,end)];rows=[]
    for campaign,group in target.groupby('campno'):
        ids=set()
        for r in group.itertuples():
            date_of_recall=date.fromisoformat(r.rcdate)
            mask=(c.make==r.make)&c.available_at.between((date_of_recall-timedelta(days=364)).isoformat(),(date_of_recall-timedelta(days=7)).isoformat())
            if match_label:
                mask &= (c.label_id==r.label_id)&c.label_id.ne(OTHER)
            ids.update(c[mask].odino.astype(str))
        rows.append({'campaign':campaign,'prior_complaints':len(ids)})
    reached=sum(x['prior_complaints']>0 for x in rows)
    return {'campaigns':len(rows),'with_prior_evidence':reached,'ceiling':reached/len(rows) if rows else 0,
            'matching':'make+specific_defect' if match_label else 'make+any_fuel_complaint_not_defect_evidence',
            'diagnostic_only':True,'rows':rows}
