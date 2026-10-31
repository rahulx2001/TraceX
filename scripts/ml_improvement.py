"""Offline, append-only improvement workflow. No paid calls or production changes.

Preparation and diagnostics do not authorize tuning. Development requires the
separate approved test-reservation record; final testing additionally requires
the actual frozen data, provenance and completed follow-up.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import sys
import shlex

ROOT=Path(__file__).resolve().parents[1]
if (ROOT/".ml-deps").exists():sys.path.insert(0,str(ROOT/".ml-deps"))

import numpy as np
import pandas as pd
from src.eval.improvement_protocol import (SEEDS,RANDOM_SEEDS,Run,canonical,digest,write_once,check_development)
from src.eval.improvement_detection import feature_rows,matrix,labelled_candidates,scored_alerts,summarize,slices,error_inventory
from src.eval.improvement_metrics import calibration,paired_campaign_difference,rate
from src.eval.improvement_models import binary_model,fit_calibrator,choose_operating_point
from src.eval.defect_prediction import evaluate,alert_episodes,reference_alerts,join_labels

OUT=ROOT/"reports/improvement"
DATA=ROOT/"data/ml_improvement"


def load(path):return json.loads(Path(path).read_text())


def invocation():
    return "FRONTLINE_TEST_ISOLATION=1 .venv-hackathon/bin/python -m scripts.ml_improvement " + shlex.join(sys.argv[1:])


def prepare(args):
    protocol=load(ROOT/"reports/defect/repair/protocol.json")
    paths=[ROOT/spec["path"] for spec in protocol["inputs"].values()]
    paths += [ROOT/"reports/defect/repair/classifications.parquet",ROOT/"reports/defect/repair/recall_labels.parquet"]
    run=Run(ROOT,args.run_id,{"phase":"prepare","cutoff":"2020-12-31","scope":protocol["scope"]},paths,invocation())
    try:
        if DATA.exists():raise FileExistsError("Development inputs already prepared; refusing replacement")
        for spec in protocol["inputs"].values():
            if digest(ROOT/spec["path"])!=spec["sha256"]:raise ValueError("Frozen repair input changed")
        ver=protocol["classifier"]
        c,r=join_labels(pd.read_parquet(ROOT/"data/defect/repair/complaints.parquet"),
                       pd.read_parquet(ROOT/"data/defect/repair/recall_scopes.parquet"),
                       pd.read_parquet(paths[-2]),pd.read_parquet(paths[-1]),
                       model=ver["model"],prompt=ver["prompt_version"],taxonomy=ver["taxonomy_sha256"])
        c=c[c.datea.le("2020-12-31")].copy();r=r[r.rcdate.le("2020-12-31")].copy()
        check_development(c,"datea");check_development(r,"rcdate")
        c["severity_known"]=False;c["severe"]=False
        severity_source=None
        if args.source_zip:
            source=Path(args.source_zip)
            expected=load(ROOT/"reports/defect/fuel_holdout/protocol.json")["sources"]["FLAT_CMPL.zip"]
            if digest(source)!=expected:raise ValueError("Severity source differs from original frozen snapshot")
            severity_source={"path":str(source),"sha256":expected}
            from scripts.ai_safety_backtest import iter_flat,_I,_int
            wanted=set(c.odino.astype(str));seen={}
            for p in iter_flat(source):
                oid=p[_I["ODINO"]].strip()
                if oid in wanted:
                    severe=p[_I["CRASH"]].strip().upper()=="Y" or p[_I["FIRE"]].strip().upper()=="Y" or _int(p[_I["INJURED"]])>0 or _int(p[_I["DEATHS"]])>0
                    seen[oid]=seen.get(oid,False) or severe
            c["severity_known"]=c.odino.astype(str).isin(seen)
            c["severe"]=c.odino.astype(str).map(seen).fillna(False).astype(bool)
        DATA.mkdir(parents=True)
        c.to_parquet(DATA/"complaints.parquet",index=False);r.to_parquet(DATA/"recalls.parquet",index=False)
        manifest={"scope":protocol["scope"],"label_source":"frozen model hypotheses, not human ground truth", "cutoff":"2020-12-31",
                  "complaints":len(c),"campaigns":int(r.campno.nunique()),"recall_scopes":len(r),"severity_source":severity_source,
                  "severity_coverage":rate(int(c.severity_known.sum()),len(c),"complaints"),
                  "inputs":{str(p.relative_to(ROOT)):digest(p) for p in [DATA/"complaints.parquet",DATA/"recalls.parquet"]}}
        write_once(OUT/"development_manifest.json",manifest)
        run.finish("prepared");print(json.dumps(manifest,indent=2))
    except BaseException:
        run.finish("failed",exit_code=1);raise


def data():
    manifest=load(OUT/"development_manifest.json")
    for path,expected in manifest["inputs"].items():
        if digest(ROOT/path)!=expected:raise ValueError("Development input hash mismatch")
    c=pd.read_parquet(DATA/"complaints.parquet");r=pd.read_parquet(DATA/"recalls.parquet")
    check_development(c,"datea");check_development(r,"rcdate")
    return c,r,manifest


def audit(args):
    c,r,manifest=data()
    run=Run(ROOT,args.run_id,{"phase":"audit","window":13},[DATA/"complaints.parquet",DATA/"recalls.parquet"],invocation())
    try:
        from src.eval.fuel_detection import opportunity_bound
        records={}
        for name,frame in [("all_reports",c),("excluding_explicit_recall_reports",c[~c.text.str.contains(r"\brecall\w*\b|\bcampaign\b",case=False,regex=True)])]:
            rows=feature_rows(frame,end="2020-12-31")
            alerts=alert_episodes(rows,min_count=2,max_tail=.2,start="2015-01-01",end="2020-12-31")
            result=evaluate(alerts,r,start="2015-01-01",end="2020-12-31")
            records[name]=dict(metrics=summarize(result),per_slice=slices(alerts,r,start="2015-01-01",end="2020-12-31"),
                               errors=error_inventory(result,r,frame,start="2015-01-01",end="2020-12-31"),
                               label_conditional_opportunity=opportunity_bound(frame,r,start="2015-01-01",end="2020-12-31"),
                               any_fuel_opportunity=opportunity_bound(frame,r,start="2015-01-01",end="2020-12-31",match_label=False),
                               candidates=len(rows),mature_candidate_outcomes=len(labelled_candidates(rows,r,start="2015-01-01",end="2020-12-31")))
        write_once(run.path/"results.json",dict(status="development_audit_not_held_out_improvement",manifest=manifest,blocks=records))
        run.finish("audited");print(run.path/"results.json")
    except BaseException:
        run.finish("failed",exit_code=1);raise


def develop(args):
    approval=load(OUT/"test_reservation.json")
    if not approval.get("development_authorized") or approval.get("approval_source")!="explicit_user":
        raise ValueError("Development requires explicit authorization for the untouched prospective window")
    protocol=load(OUT/"research_protocol.json")
    if protocol["sha256"]!=canonical(protocol["body"]):raise ValueError("Research protocol hash mismatch")
    c,r,manifest=data()
    command=invocation()
    run=Run(ROOT,args.run_id,protocol,[DATA/"complaints.parquet",DATA/"recalls.parquet",OUT/"test_reservation.json"],command)
    try:
        results=[]
        # Chronological development only. Frozen test windows are never loaded.
        for variant,frame in [("all_reports",c),("excluding_explicit_recall_reports",c[~c.text.str.contains(r"\brecall\w*\b|\bcampaign\b",case=False,regex=True)])]:
            for fold in protocol["body"]["folds"]:
                start,end=fold["validation"];fit_end=fold["fit_end"]
                fit_c=frame[frame.datea.le(fit_end)];fit_r=r[r.rcdate.le(fit_end)]
                fit_rows=feature_rows(fit_c,end=fit_end)
                labelled=labelled_candidates(fit_rows,fit_r,start="2015-01-01",end=fit_end)
                all_rows=feature_rows(frame,end=end)
                val=[x for x in all_rows if start<=x["available_at"]<=end]
                val_r=r[r.rcdate.between(start,end)]
                fixed=alert_episodes(val,min_count=2,max_tail=.2,start=start,end=end)
                baseline=evaluate(fixed,r,start=start,end=end)
                classifiers=[("gamma_poisson",None,None),("count",None,None)]
                y=np.array([x["outcome"] for x in labelled])
                for kind in ["logistic","gradient_boosting"]:
                    for seed in SEEDS:
                        if len(y)<10 or len(set(y))<2:
                            results.append(dict(variant=variant,fold=fold,model=kind,seed=seed,status="insufficient_training_support",
                                                rows=len(y),positives=int(y.sum()),metrics=None));continue
                        model=binary_model(kind,seed).fit(matrix(labelled),y)
                        classifiers.append((kind,seed,model))
                for kind,seed,model in classifiers:
                    thresholds=protocol["body"]["thresholds"] if model is not None else ([2,3,5] if kind=="count" else [.2])
                    probabilities=model.predict_proba(matrix(val))[:,1] if model is not None and val else np.array([])
                    for threshold in thresholds:
                        if kind=="gamma_poisson":alerts=fixed
                        else:
                            scores=probabilities if model is not None else [a["record_count"] for a in val]
                            alerts=scored_alerts(val,scores,threshold=threshold,start=start,end=end)
                        actual=evaluate(alerts,r,start=start,end=end)
                        row=dict(variant=variant,fold=fold,model=kind,seed=seed,threshold=threshold,status="evaluated",split="development_validation",
                                 metrics=summarize(actual),baseline=summarize(baseline),
                                 recall_difference=paired_campaign_difference(baseline["campaign_hits"],actual["campaign_hits"],val_r.campno),
                                 per_slice=slices(alerts,r,start=start,end=end))
                        # Every reference draw is preserved; inability to match is an explicit failure.
                        refs=[]
                        for ref_seed in RANDOM_SEEDS:
                            try:
                                ref=reference_alerts(val,budget=len(alerts),start=start,end=end,seed=ref_seed)
                                refs.append(dict(seed=ref_seed,status="evaluated",**summarize(evaluate(ref,r,start=start,end=end))))
                            except ValueError as exc:refs.append(dict(seed=ref_seed,status="failed",reason=str(exc)))
                        row["random_references"]=refs
                        ref=reference_alerts(val,budget=len(alerts),start=start,end=end,seed=None)
                        row["equal_budget_count_reference"]=summarize(evaluate(ref,r,start=start,end=end))
                        if model is not None:
                            matured=labelled_candidates(val,r,start=start,end=end)
                            if matured:
                                p=model.predict_proba(matrix(matured))[:,1]
                                row["uncalibrated_validation"]=calibration([a["outcome"] for a in matured],p,reference_probability=float(y.mean()),seed=seed)
                        results.append(row)
                print(variant,fold["name"],"training mature outcomes",len(y),"positives",int(y.sum()),flush=True)
        qualified=[x for x in results if x.get("metrics") and x["metrics"]["precision"]["value"] is not None
                   and x["metrics"]["precision"]["value"]>=.8 and x["metrics"]["recall"]["value"]>=.7 and x["metrics"]["mature_alerts"]>=10]
        write_once(run.path/"results.json",dict(status="development_only",trials=results,qualified_trial_count=len(qualified),
                   selected_model=None,note="No production selection. All folds, variants, thresholds and seeds retained. Final scores require untouched future data."))
        run.finish("completed_development");print(run.path/"results.json")
    except BaseException:
        run.finish("failed",exit_code=1);raise


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("phase",choices=["prepare","audit","develop"])
    parser.add_argument("--run-id",required=True)
    parser.add_argument("--source-zip")
    args=parser.parse_args()
    {"prepare":prepare,"audit":audit,"develop":develop}[args.phase](args)


if __name__=="__main__":main()
