"""Human-run, one-shot frozen baseline replication; no real-data execution now."""
from __future__ import annotations

import argparse
import csv
from datetime import date
import json
import os
from pathlib import Path
import shlex

import numpy as np
import pandas as pd

from src.eval.defect_prediction import candidates,alert_episodes,evaluate,join_labels
from src.eval.improvement_detection import RECALL
from src.eval.improvement_metrics import rate
from src.eval.improvement_protocol import digest,write_once,canonical
from src.eval.prospective_io import (PHASE,CUSTODY,load,now,today,git,blob,safe_id,external_root,external_file,
                                    manifest_chain,verify_freeze,check_attestation,check_collection_log)

ROOT=Path(__file__).resolve().parents[1]


def load_raw(custody,manifest,protocol):
    """Use original parsers. Earliest archived versions win; all scope rows retained."""
    from scripts.defect_prepare_inputs import _iter_complaint_rows,_iter_recall_rows
    complaints=[];recalls=[];quality=[]
    for snapshot in manifest["snapshots"]:
        sid=safe_id(snapshot["snapshot_id"])
        meta=external_file(custody,sid+"/snapshot.json")
        if digest(meta)!=snapshot["snapshot_sha256"]:raise ValueError("Snapshot metadata hash mismatch")
        expected={k:v for k,v in snapshot.items() if k!="snapshot_sha256"}
        if load(meta)!=expected:raise ValueError("Snapshot metadata differs from committed manifest")
        for entry in snapshot["files"]:
            path=external_file(custody,sid+"/"+entry["file"])
            if digest(path)!=entry["sha256"]:raise ValueError("Snapshot raw file hash mismatch")
            if entry["source_id"]=="complaints":
                rows,tally=_iter_complaint_rows(path,start=protocol["prospective"]["flag_start"],end=protocol["prospective"]["flag_end"],limit=0)
                complaints.extend(rows)
            elif entry["source_id"]=="recalls":
                rows,tally=_iter_recall_rows(path,limit=0,preserve_scopes=True);recalls.extend(rows)
            else:raise ValueError("Unknown snapshot source")
            quality.append(dict(snapshot_id=sid,source=entry["source_id"],parser_counts=tally))
    c=pd.DataFrame(complaints,columns=["datea","odino","cmplid","make","model","year","component","text"])
    r=pd.DataFrame(recalls,columns=["campno","component","desc_defect","rcdate","make","model","year","rcl_type"])
    scope=protocol["scope"]
    def scoped(df):
        return df[df.make.isin(scope["makes"]) & df.year.between(*scope["model_years"]) & df.component.eq("FUEL SYSTEM")].copy()
    c=scoped(c).drop_duplicates(["odino","component"],keep="first")
    r=scoped(r);r=r[r.rcl_type.eq("V") & r.rcdate.between(protocol["prospective"]["flag_start"],protocol["prospective"]["outcome_cutoff"])]
    r=r.drop_duplicates(["campno","make","model","year","component"],keep="first")
    return c,r,quality


def apply_labels(c,r,custody,manifest,protocol):
    required={"complaint_labels","recall_labels"};inputs=manifest.get("analysis_inputs",{})
    if not required<=inputs.keys():raise ValueError("Complete pinned-model classification inputs are required; no imputation or paid call")
    frames={}
    for name in required:
        spec=inputs[name];path=external_file(custody,spec["file"])
        if digest(path)!=spec["sha256"]:raise ValueError("Classification input hash mismatch")
        frames[name]=pd.read_parquet(path)
    version=protocol["classifier"]
    return join_labels(c,r,frames["complaint_labels"],frames["recall_labels"],model=version["model"],prompt=version["prompt_version"],taxonomy=version["taxonomy_sha256"])


def estimate(alerts,recalls,window):
    recall=evaluate(alerts,recalls,start=window["flag_start"],end=window["flag_end"])
    precision=evaluate(alerts,recalls,start=window["flag_start"],end=window["outcome_cutoff"])
    leads=np.asarray(list(recall["campaign_hits"].values()),dtype=float)/7
    ci=None
    if len(leads)>1:
        rng=np.random.default_rng(17)
        ci=np.quantile(np.median(rng.choice(leads,size=(2000,len(leads)),replace=True),axis=1),[.025,.975]).tolist()
    return dict(recall=rate(recall["hits"],recall["campaigns"],"eligible campaigns issued in 2027-2028"),
                precision=rate(precision["confirmed_mature_alerts"],precision["mature_alerts"],"full-follow-up alert episodes issued in 2027-2028"),
                median_lead_weeks=dict(value=recall["median_lead_weeks"],numerator=None,denominator=recall["hits"],ci95=ci,unit="weeks among detected campaigns",note="median is not a ratio; descriptive campaign bootstrap"),
                total_alerts=len(alerts),mature_alerts=precision["mature_alerts"],censored_alerts=precision["censored_alerts"]),recall,precision


def final_analysis(args, *, root=ROOT):
    if not args.final_analysis:raise ValueError("--final-analysis is required")
    # The prescribed order is intentional: no data access before code/time/custody gates.
    frozen,hashes,tag=verify_freeze(root)
    head=git(root,"rev-parse","HEAD")  # Identical frozen files permit later metadata-only commits.
    if git(root,"status","--porcelain"):raise ValueError("Dirty working tree; commit metadata first")
    protocol=load(root/PHASE/"protocol.json");window=protocol["prospective"]
    day=today()
    if args.today:
        if os.environ.get("FRONTLINE_TEST_ISOLATION")!="1" or load(root/CUSTODY).get("synthetic_fixture") is not True:
            raise ValueError("--today is only for synthetic test repositories")
        day=date.fromisoformat(args.today).isoformat()
    if day<window["outcome_cutoff"]:raise ValueError("Before outcome cutoff")
    custody=external_root(root,args.custody_root)
    manifest,chain=manifest_chain(root,args.manifest_ref)
    if manifest["status"]!="data_frozen":raise ValueError("Manifest is not data_frozen")
    attestation=check_attestation(root,args.manifest_ref,manifest)
    check_collection_log(root,args.manifest_ref,manifest,chain)
    if manifest.get("outcomes_complete_through")!=window["outcome_cutoff"] or not manifest["snapshots"] or max(s["snapshot_date"] for s in manifest["snapshots"])<window["outcome_cutoff"]:
        raise ValueError("Complete outcome follow-up has not been committed")
    if manifest.get("final_analysis") is not None and not (args.rerun and args.deviation_id):
        raise ValueError("A final analysis is already committed; rerun requires a deviation")
    output=Path(args.out).absolute()
    if output.is_symlink() or any(p.is_symlink() for p in output.parents):raise ValueError("Symlinked output directory")
    if output==custody or custody in output.parents:raise ValueError("Outputs must not modify the custody volume")
    if (output/"run_manifest.json").exists():
        if not args.rerun or not args.deviation_id:raise ValueError("Second run requires --rerun --deviation-id")
    elif args.rerun and not args.deviation_id:raise ValueError("Rerun requires deviation ID")
    if args.rerun:
        deviation=safe_id(args.deviation_id);output=output/"reruns"/deviation
        log=root/"reports/improvement/prospective/DEVIATIONS.md";log.parent.mkdir(parents=True,exist_ok=True)
        with log.open("a") as f:f.write(f"\n- {now()} | {deviation} | Explicit operator rerun; original outputs preserved. Claims require human deviation review.\n")
    output.mkdir(parents=True,exist_ok=True)
    # Reserve before any outcome parsing, so failed attempts cannot be silently replaced.
    command=".venv-hackathon/bin/python -m scripts.final_prospective_eval --final-analysis --custody-root <human-mounted-volume> --manifest-ref "+shlex.quote(args.manifest_ref)+" --out <output-directory>"
    run=dict(status="started",started_at=now(),code_commit=head,frozen_tag_commit=tag,freeze_commit=hashes["freeze_commit"],config_hash=hashes["protocol_sha256"],
             data_hash=chain[-1]["sha256"],seed=[17,29,43,71,101],split="prospective-sealed",label_source="model classifications and official recall outcomes; no human semantic truth",scope=protocol["scope"],
             exact_command_template=command,command_note="Custody/output paths intentionally omitted; marker UUID and hashes identify data without recording personal paths",attestation=attestation,
             manifest_chain=chain,mode=frozen["mode"],is_candidate_result=False,custody_limitation=protocol["custody"]["threat_model"])
    write_once(output/"run_manifest.json",run)
    try:
        c,r,quality=load_raw(custody,manifest,protocol)
        eligible=r[r.rcdate.between(window["flag_start"],window["flag_end"])];count=int(eligible.campno.nunique())
        if count<window["min_campaigns"]:
            result=dict(status="INCONCLUSIVE_SAMPLE",eligible_campaigns=count,minimum_campaigns=window["min_campaigns"],metrics=None,is_candidate_result=False,split="prospective-sealed")
            write_once(output/"final_analysis.json",result)
            write_once(output/"completion.json",dict(status="INCONCLUSIVE_SAMPLE",ended_at=now(),exit_code=2))
            return 2
        if frozen["mode"]!="baseline_replication":raise ValueError("This frozen release is Mode B; changing mode requires a new preregistered freeze")
        c,r=apply_labels(c,r,custody,manifest,protocol)
        model=load(root/frozen["candidate"]["path"])
        variants={};campaign_rows=[];alert_rows=[]
        for name,frame in [("all_reports",c),("excluding_explicit_recall_reports",c[~c.text.map(lambda x:bool(RECALL.search(str(x))))])]:
            rows=candidates(frame,window=model["window"],end=window["flag_end"])
            alerts=alert_episodes(rows,min_count=model["min_count"],max_tail=model["max_tail"],start=window["flag_start"],end=window["flag_end"])
            metrics,rec,prec=estimate(alerts,r,window)
            metrics["per_make"]={make:estimate([a for a in alerts if a["make"]==make],r[r.make.eq(make)],window)[0] for make in protocol["scope"]["makes"]}
            # Paired differences are inapplicable to Mode B; no improvement test is fabricated.
            variants[name]=metrics
            for camp in sorted(set(eligible.campno)):
                campaign_rows.append(dict(variant=name,campaign=camp,detected=camp in rec["campaign_hits"],lead_days=rec["campaign_hits"].get(camp)))
            for a in prec["alert_details"]:
                alert_rows.append(dict(variant=name,available_at=a["available_at"],make=a["make"],component=a["component"],label_id=a["label_id"],full_followup=a["full_followup"],matched_campaigns=";".join(a["matched_campaigns"])))
        result=dict(status="BASELINE_REPLICATION",mode="baseline_replication",metrics=variants,eligible_campaigns=count,improvement_claim=None,is_candidate_result=False,
                    split="prospective-sealed",label_source=run["label_source"],scope=run["scope"],provenance=run,baseline_comparison="Prospective replication; historical-opened estimates are context only",parser_quality=quality,
                    calibration="Not applicable: Gamma-Poisson tail is a ranking heuristic, not a calibrated probability",paired_difference="Not applicable to baseline-only replication")
        write_once(output/"final_analysis.json",result)
        lines=["# Prospective baseline replication","","No improved score is claimed. Model labels + official recalls; prospective-sealed split.","",protocol["custody"]["threat_model"],"","| Variant | Metric | Numerator / denominator | Value | Descriptive 95% CI |","|---|---|---|---|---|"]
        for name,m in variants.items():
            for key in ["recall","precision"]:
                x=m[key];lines.append(f"| {name} | {key} | {x['numerator']}/{x['denominator']} | {x['value']} | {x['ci95']} |")
        with (output/"final_analysis.md").open("x") as f:f.write("\n".join(lines)+"\n")
        for filename,rows,fields in [("campaigns.csv",campaign_rows,["variant","campaign","detected","lead_days"]),("alerts.csv",alert_rows,["variant","available_at","make","component","label_id","full_followup","matched_campaigns"])]:
            with (output/filename).open("x",newline="") as f:
                writer=csv.DictWriter(f,fieldnames=fields);writer.writeheader();writer.writerows(rows)
        write_once(output/"completion.json",dict(status="completed",ended_at=now(),exit_code=0,outputs={p.name:digest(p) for p in output.iterdir() if p.is_file()}))
        return 0
    except BaseException:
        write_once(output/"completion.json",dict(status="failed",ended_at=now(),exit_code=1));raise


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--final-analysis",action="store_true");p.add_argument("--custody-root",required=True)
    p.add_argument("--manifest-ref",default="ml-score-improvement");p.add_argument("--out",required=True)
    p.add_argument("--today",help="Synthetic test repositories only")
    p.add_argument("--rerun",action="store_true");p.add_argument("--deviation-id")
    try:raise SystemExit(final_analysis(p.parse_args()))
    except (ValueError,OSError) as exc:p.exit(2,str(exc)+"\n")


if __name__=="__main__":main()
