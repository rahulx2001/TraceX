"""Measure the frozen ranking heuristic on pre-2021 mature candidate outcomes.

No calibrator is fitted and no threshold is chosen. These candidate-level
diagnostics have different units from mature-alert episode precision.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import shlex
import sys
ROOT=Path(__file__).resolve().parents[1]
if (ROOT/".ml-deps").exists():sys.path.insert(0,str(ROOT/".ml-deps"))
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from scripts.ml_improvement import data,DATA,OUT
from src.eval.improvement_detection import feature_rows,labelled_candidates
from src.eval.improvement_metrics import calibration,rate
from src.eval.improvement_protocol import Run,write_once


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-id",default="baseline_calibration_v1",help="New immutable output directory for this attempt")
    args=parser.parse_args()
    command="FRONTLINE_TEST_ISOLATION=1 .venv-hackathon/bin/python -m scripts.ml_baseline_calibration"
    if sys.argv[1:]:command+=" "+shlex.join(sys.argv[1:])
    run=Run(ROOT,args.run_id,{"bins":10,"transform":"1 - frozen predictive tail","seed":17,"selection":"none"},
            [DATA/"complaints.parquet",DATA/"recalls.parquet"],
            command,seed=17)
    try:
        c,r,manifest=data();blocks={}
        for name,frame in [("all_reports",c),("excluding_explicit_recall_reports",c[~c.text.str.contains(r"\brecall\w*\b|\bcampaign\b",case=False,regex=True)])]:
            rows=feature_rows(frame,end="2020-12-31")
            labelled=labelled_candidates(rows,r,start="2015-01-01",end="2020-12-31")
            train=labelled_candidates(feature_rows(frame[frame.datea.le("2018-12-31")],end="2018-12-31"),r[r.rcdate.le("2018-12-31")],start="2015-01-01",end="2018-12-31")
            reference=float(np.mean([a["outcome"] for a in train])) if train else None
            val=[a for a in labelled if a["available_at"]>="2019-01-01"]
            y=[a["outcome"] for a in val];p=[1-a["tail_score"] for a in val]
            # An unavailable training prevalence is not filled from validation.
            metrics=calibration(y,p,reference_probability=reference if reference is not None else 0.,seed=17)
            if reference is None:
                metrics.update(reference_probability=None,reference_brier=None,brier_difference=None,brier_difference_ci95=None)
            curve=[]
            for threshold in sorted(set([0.,1.]+p)):
                selected=[i for i,v in enumerate(p) if v>=threshold];tp=sum(y[i] for i in selected)
                curve.append(dict(threshold=threshold,precision=rate(tp,len(selected),"selected mature candidate rows"),recall=rate(tp,sum(y),"positive mature candidate rows")))
            blocks[name]=dict(metrics=metrics,curve=curve,training_reference_rows=len(train),
                              calibration_fit_status="not fitted; no threshold selected",evaluation_window=["2019-01-01","2020-12-31"],
                              source_unit="mature candidate weeks, not deployed alert episodes",label_source="model labels + later official recalls")
            fig,axs=plt.subplots(1,2,figsize=(10,4),layout="constrained")
            axs[0].plot([0,1],[0,1],"--",color="gray",label="ideal reliability")
            points=[b for b in metrics["reliability"] if b["n"]]
            if points:
                axs[0].scatter([b["mean_probability"] for b in points],[b["observed"]["value"] for b in points],s=[25+4*b["n"] for b in points])
                axs[0].errorbar([b["mean_probability"] for b in points],[b["observed"]["value"] for b in points],
                               yerr=[[b["observed"]["value"]-b["observed"]["ci95"][0] for b in points],[b["observed"]["ci95"][1]-b["observed"]["value"] for b in points]],fmt="none",capsize=3)
            else:axs[0].text(.5,.5,"No mature validation candidates",ha="center")
            axs[0].set(xlim=(-.03,1.03),ylim=(-.03,1.03),xlabel="1 − predictive tail (uncalibrated)",ylabel="Fraction matching a later recall",title=f"Reliability diagnostic · n={len(y)}")
            valid=[x for x in curve if x["precision"]["value"] is not None and x["recall"]["value"] is not None]
            if valid:axs[1].step([x["recall"]["value"] for x in valid],[x["precision"]["value"] for x in valid],where="post")
            else:axs[1].text(.5,.5,"No positive validation support",ha="center")
            axs[1].set(xlim=(-.03,1.03),ylim=(-.03,1.03),xlabel="Candidate-level recall",ylabel="Candidate-level precision",title=f"Ranking diagnostic · positives={sum(y)}")
            fig.suptitle(name.replace("_"," ")+"\nPre-2021 model-labelled development; not final effectiveness",fontsize=10)
            fig.savefig(run.path/(name+".png"),dpi=150);plt.close(fig)
        write_once(run.path/"results.json",dict(status="uncalibrated_baseline_diagnostic",blocks=blocks,
                    note="ECE/Brier treat a heuristic as a probability solely to diagnose its unreliability. They do not establish calibrated physical-defect risk. No validation-set prevalence was substituted for a missing training reference."))
        run.finish("measured_baseline_diagnostic");print(run.path/"results.json")
    except BaseException:
        run.finish("failed",exit_code=1);raise


if __name__=="__main__":main()
