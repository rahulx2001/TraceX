"""Pre-registered development only; the historical matching code is reused."""
from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
import subprocess

import numpy as np
import pandas as pd

from src.eval.defect_prediction import KEY, candidates, alert_episodes, evaluate, reference_alerts
from src.eval.improvement_detection import labelled_candidates, scored_alerts, summarize, slices, error_inventory, RECALL
from src.eval.improvement_protocol import Run, check_development, require_disjoint, digest, write_once

NOTICE = "Development-only evidence; not a candidate result and not a prospective estimate."
FEATURES = ["complaints_30d", "complaints_90d", "complaints_365d", "same_make_365d"]


def structured_rows(complaints, *, end):
    check_development(complaints, "datea")
    c = complaints[complaints.datea.le(end)].copy()
    if c.odino.astype(str).duplicated().any():
        raise ValueError("Duplicate complaint identity")
    dates = pd.to_datetime(c.datea)
    rows = candidates(c, window=13, end=end)
    for row in rows:
        available = pd.Timestamp(row["available_at"])
        same = c.make.eq(row["make"]) & c.component.eq(row["component"])
        specific = same & c.label_id.eq(row["label_id"])
        for days in [30, 90, 365]:
            past = dates.ge(available-pd.Timedelta(days=days)) & dates.lt(available)
            row[f"complaints_{days}d"] = int((past & specific).sum())
        row["same_make_365d"] = int((past & c.make.eq(row["make"])).sum())
        evidence = c[specific & dates.ge(available-pd.Timedelta(weeks=13)) & dates.lt(available)]
        row["evidence_ids"] = sorted(evidence.odino.astype(str))
    return rows


def matrix(rows):
    return np.asarray([[r[f] for f in FEATURES] for r in rows], dtype=float).reshape(len(rows), len(FEATURES))


def fit_logistic(rows, *, threshold=.5):
    y = np.array([r["outcome"] for r in rows], dtype=float)
    if len(y) < 10 or len(set(y)) < 2:
        raise ValueError("insufficient_training_support")
    x = matrix(rows); mean = x.mean(axis=0); scale = x.std(axis=0)
    scale[scale == 0] = 1
    x = (x-mean)/scale; coef = np.zeros(x.shape[1]); intercept = 0.
    for _ in range(1000):
        p = 1/(1+np.exp(-np.clip(x@coef+intercept, -40, 40)))
        coef -= .1*(x.T@(p-y)/len(y)+coef/len(y))
        intercept -= .1*float((p-y).mean())
    return dict(type="logistic", feature_order=FEATURES, means=mean.tolist(), scales=scale.tolist(),
                coefficients=coef.tolist(), intercept=intercept, threshold=threshold, calibrated=False)


def predict_json(model, rows):
    if model["feature_order"] != FEATURES:
        raise ValueError("Frozen feature order mismatch")
    x = (matrix(rows)-np.asarray(model["means"]))/np.asarray(model["scales"])
    return 1/(1+np.exp(-np.clip(x@np.asarray(model["coefficients"])+model["intercept"], -40, 40)))


def cluster_difference(baseline, candidate, campaigns, *, seeds, draws=2000):
    """Paired campaign-linked components; unmatched alerts retain denominator mass."""
    campaigns = sorted(set(campaigns))
    parent = {"c:"+c: "c:"+c for c in campaigns}
    def find(a):
        parent.setdefault(a, a)
        if parent[a] != a: parent[a] = find(parent[a])
        return parent[a]
    def union(a, b): parent[find(b)] = find(a)
    def identity(a): return "a:"+"|".join([a["available_at"]]+[str(a[k]) for k in KEY])
    for result in [baseline, candidate]:
        for a in result["alert_details"]:
            aid = identity(a); find(aid)
            for c in a["matched_campaigns"]:
                if c in campaigns: union(aid, "c:"+c)
    clusters = sorted({find(k) for k in parent}); index = {k:i for i,k in enumerate(clusters)}
    # campaigns, baseline hits, candidate hits, baseline TP/N, candidate TP/N
    values = np.zeros((len(clusters), 7))
    for c in campaigns:
        row = values[index[find("c:"+c)]]
        row[:3] += [1, c in baseline["campaign_hits"], c in candidate["campaign_hits"]]
    for offset, result in [(3,baseline),(5,candidate)]:
        for a in result["alert_details"]:
            if a["full_followup"]:
                values[index[find(identity(a))], offset:offset+2] += [bool(a["matched_campaigns"]),1]
    total = values.sum(axis=0)
    def delta(v, kind):
        with np.errstate(divide="ignore", invalid="ignore"):
            return (v[...,2]-v[...,1])/v[...,0] if kind=="recall" else v[...,5]/v[...,6]-v[...,3]/v[...,4]
    output = {}
    for kind in ["recall","precision"]:
        point = delta(total, kind); runs=[]
        for seed in seeds:
            if len(values):
                weights = np.random.default_rng(seed).multinomial(len(values), np.full(len(values),1/len(values)), size=draws)
                differences = delta(weights@values, kind)
            else: differences = np.full(draws,np.nan)
            valid = differences[np.isfinite(differences)]
            ci = np.quantile(valid,[.025,.975]).tolist() if len(valid)>=.95*draws else None
            runs.append(dict(seed=seed,draws=draws,valid_draws=len(valid),ci95=ci))
        output[kind] = dict(value=float(point) if np.isfinite(point) else None,
                            clusters=len(clusters),campaigns=len(campaigns),bootstrap=runs,
                            note="Paired campaign-linked clusters plus unmatched alert components; no failed draws replaced")
    return output


def select_mode(trials, order):
    for name in order:
        folds = [t for t in trials if t.get("model")==name and t["variant"]=="all_reports" and t["status"]=="evaluated"]
        if {t["fold"]["name"] for t in folds} != {"A","B"}: continue
        no_loss = all(t["metrics"][k]["value"] is not None and t["baseline"][k]["value"] is not None
                      and t["metrics"][k]["value"] >= t["baseline"][k]["value"] for t in folds for k in ["recall","precision"])
        same_improved = any(all(t["difference"][k]["value"] is not None and t["difference"][k]["value"]>0
                               and all(b["ci95"] is not None and b["ci95"][0]>0 for b in t["difference"][k]["bootstrap"])
                               for t in folds) for k in ["recall","precision"])
        if no_loss and same_improved: return "mode_a_candidate", name
    return "mode_b_baseline", "gamma_poisson"


def develop(root, run_id, command):
    # This reader opens exactly two pinned pre-2021 parquet files, not opened evaluations.
    from scripts.ml_improvement import data, DATA
    out = root/"reports/improvement/phase1"
    protocol = json.loads((out/"protocol.json").read_text())
    hashes = json.loads((out/"HASHES.json").read_text())
    if digest(out/"protocol.json") != hashes["protocol_sha256"]: raise ValueError("Protocol changed")
    first_commit = subprocess.check_output(["git","log","--reverse","--format=%H","--",str(out/"protocol.json")],cwd=root,text=True).splitlines()[0]
    subprocess.run(["git","merge-base","--is-ancestor",first_commit,"HEAD"],cwd=root,check=True)
    c,r,manifest = data(); check_development(c,"datea"); check_development(r,"rcdate")
    run = Run(root,run_id,protocol,[DATA/"complaints.parquet",DATA/"recalls.parquet",out/"protocol.json"],command,split="development")
    try:
        trials=[];errors={};seeds=protocol["uncertainty"]["bootstrap_seeds"]
        for variant,frame in [("all_reports",c),("excluding_explicit_recall_reports",c[~c.text.map(lambda x:bool(RECALL.search(str(x))))])]:
            all_rows=structured_rows(frame,end="2020-12-31")
            original=alert_episodes(all_rows,min_count=2,max_tail=.2,start="2015-01-01",end="2020-12-31")
            errors[variant]=error_inventory(evaluate(original,r,start="2015-01-01",end="2020-12-31"),r,frame,start="2015-01-01",end="2020-12-31")
            for fold in protocol["development"]["folds"]:
                start,end=fold["validation"];cut=fold["fit_end"]
                fit_r=r[r.rcdate.le(cut)];val_r=r[r.rcdate.between(start,end)]
                require_disjoint(fit_r.campno,[],val_r.campno)
                fit_rows=structured_rows(frame[frame.datea.le(cut)],end=cut)
                training=labelled_candidates(fit_rows,fit_r,start="2015-01-01",end=cut)
                rows=[a for a in structured_rows(frame,end=end) if start<=a["available_at"]<=end]
                ident=lambda a:"|".join([a['available_at']]+[str(a[k]) for k in KEY])
                require_disjoint([ident(a) for a in training],[],[ident(a) for a in rows])
                baseline=evaluate(alert_episodes(rows,min_count=2,max_tail=.2,start=start,end=end),r,start=start,end=end)
                methods=[("gamma_poisson",None)]+[(f"count_{t}",t) for t in [2,3,5]]
                y=[a["outcome"] for a in training]
                if len(y)<10 or len(set(y))<2:
                    for seed in seeds:trials.append(dict(variant=variant,fold=fold,model="logistic",seed=seed,status="insufficient_training_support",training_rows=len(y),positives=sum(y),is_candidate_result=False))
                else: methods.append(("logistic",fit_logistic(training)))
                for name,model in methods:
                    if name=="gamma_poisson": alerts=baseline["alert_details"]
                    else:
                        scores=predict_json(model,rows) if name=="logistic" else [a["record_count"] for a in rows]
                        alerts=scored_alerts(rows,scores,threshold=.5 if name=="logistic" else model,start=start,end=end)
                    actual=evaluate(alerts,r,start=start,end=end)
                    references=[]
                    for seed in [None]+protocol["uncertainty"]["random_seeds"]:
                        try:
                            ref=reference_alerts(rows,budget=len(alerts),start=start,end=end,seed=seed)
                            references.append(dict(seed=seed,status="evaluated",metrics=summarize(evaluate(ref,r,start=start,end=end))))
                        except ValueError as exc:references.append(dict(seed=seed,status="failed",reason=str(exc)))
                    trials.append(dict(variant=variant,fold=fold,model=name,seed=None,status="evaluated",split="development",is_candidate_result=False,notice=NOTICE,
                        training_rows=len(y),training_positive_outcomes=sum(y),metrics=summarize(actual),baseline=summarize(baseline),
                        difference=cluster_difference(baseline,actual,val_r.campno,seeds=seeds),references=references,
                        per_slice=slices(alerts,r,start=start,end=end),model_json=model if name=="logistic" else None))
                print(variant,fold["name"],"fit outcomes",len(y),"positives",sum(y),flush=True)
        mode,selected=select_mode(trials,protocol["selection_details"]["model_order"])
        decision=dict(mode=mode,selected=selected,rule=protocol["phase2_selection_rule"],
                      reason="No method satisfies all fold, denominator and bootstrap conditions" if mode=="mode_b_baseline" else "Selected by preregistered order among methods satisfying every condition",
                      is_candidate_result=False,notice=NOTICE,preregistration_commit=first_commit)
        result=dict(status="development_only",notice=NOTICE,trials=trials,errors=errors,decision=decision,manifest=manifest,
                    provenance=run.meta,label_source="frozen model labels plus official recalls; no human truth",
                    scope={**protocol["scope"],"complaint_window":["2015-01-01","2020-12-31"]},
                    calibration="Not fitted; no independently supportable calibration subset",is_candidate_result=False)
        write_once(run.path/"results.json",result);write_once(out/"development_results.json",result);write_once(out/"phase2_decision.json",decision)
        run.finish("completed_development");return result
    except BaseException:
        run.finish("failed",exit_code=1);raise
