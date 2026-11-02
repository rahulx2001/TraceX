"""Generate an honest evidence report/dashboard from hashed sources, without fitting."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
if (ROOT/".ml-deps").exists():sys.path.insert(0,str(ROOT/".ml-deps"))

from src.eval.improvement_protocol import digest,write_once,canonical


def load(path):return json.loads(Path(path).read_text())


def build(audit_path):
    out=ROOT/"reports/improvement"
    audit=load(audit_path);baseline=load(out/"baseline.json");protocol=load(out/"research_protocol.json")
    if canonical(protocol["body"])!=protocol["sha256"]:raise ValueError("Protocol hash mismatch")
    for row in baseline["metrics"]:
        if digest(ROOT/row["source"])!=row["source_sha256"]:raise ValueError("Baseline metric source changed")
    errors=[]
    for variant,b in audit["blocks"].items():
        inventory=b["errors"]
        errors += [f"## {variant}","",f"Unique mature false positives available: {inventory['available_fp']}; unique campaign misses available: {inventory['available_fn']}.",
                   "This is a machine evidence audit on pre-2021 development data. Human causal adjudication is unperformed. The requested 50+50 quota cannot be met within this corpus; rows are not duplicated and the scope is not expanded.","",
                   "| Error | Identity | Observed evidence |","|---|---|---|"]
        for x in inventory["false_positives"]:
            errors.append(f"| FP | {x['alert_id'].replace('|',' / ')} | {json.dumps(x['observations'])}; evidence IDs {', '.join(x['evidence_ids'])} |")
        for x in inventory["false_negatives"]:
            errors.append(f"| FN | {x['campaign']} | prior fuel complaints: {x['prior_any_fuel_complaints']}; matching-label complaints: {x['prior_matching_label_complaints']}; {json.dumps(x['observations'])} |")
        errors += [""]
    with (out/"error_analysis.md").open("x") as f:
        f.write("# Development error inventory\n\nSource: `"+str(audit_path.relative_to(ROOT))+"`. All unique errors are listed, including sparse and unknown-label cases. False positive means no qualifying later recall match; it does not establish absence of a physical defect.\n\n")
        f.write("Cause taxonomy: wrong category, recall mention, duplicate, weak evidence, wrong scope, timing/leakage, label ambiguity. Observations are flags for review, not human cause labels.\n\n"+"\n".join(errors))
    reservation=out/"test_reservation.json"
    reserved=load(reservation) if reservation.exists() else None
    sources=[out/"baseline.json",audit_path,out/"research_protocol.json",out/"development_manifest.json"]
    calibration_path=out/"runs/baseline_calibration_v1/results.json"
    baseline_calibration=load(calibration_path) if calibration_path.exists() else None
    if calibration_path.exists():sources.append(calibration_path)
    result=dict(schema_version=1,status="research_targets_not_demonstrated",promoted=False,
                notice="Retrospective, model-labelled, not production-validated",
                targets=protocol["body"]["targets"],
                human_validation=dict(status="annotation waived by user; accuracy unavailable",labelled=0,total=300,accuracy=None),
                untouched_test=dict(status="prospective reservation only; data unavailable" if reserved else "not frozen; authorization pending",reservation=reserved,metrics=None),
                historical_baseline=baseline["metrics"],development_audit=audit,
                improvement_claim=None,
                model_selection=dict(status="no candidate qualifies for production",selected=None,
                                     reason="Targets unproven; development evidence sparse; human labels and untouched final results unavailable"),
                calibration=dict(status="tooling tested; calibrated effectiveness unavailable",ece=None,brier=None,
                                 reason="No independently validated calibrated candidate"),
                baseline_calibration_diagnostic=baseline_calibration,
                retrieval=dict(status="mixed-candidate evaluator implemented; independent relevance labels unavailable",metrics=None,
                               old_diagnostic_issue=baseline["pair_diagnostic_caveat"]),
                source_hashes={str(p.relative_to(ROOT)):digest(p) for p in sources},
                validation=dict(status="see separately generated final_validation.json; no test suite count is an ML accuracy score"),
                limitations=["Opened 2021-2024 and 2025 results remain unchanged.","Development and historical test denominators differ; no before/after improvement is inferred.",
                             "No same-physical-part or vehicle-match claim follows from make/component/label matching.",
                             "Modern teacher pretraining and contemporary source revisions may contain historical recall knowledge.",
                             "Error review quota exceeds unique available development errors; human cause labels unfilled."])
    write_once(out/"results.json",result)
    return result


def dashboard_payload(result,path):
    for source,expected in result["source_hashes"].items():
        if digest(ROOT/source)!=expected:raise ValueError("Evidence source changed; refusing dashboard publication")
    baseline=load(ROOT/"reports/improvement/baseline.json")
    protocol=load(ROOT/"reports/improvement/research_protocol.json")
    if result["historical_baseline"]!=baseline["metrics"] or result["targets"]!=protocol["body"]["targets"]:
        raise ValueError("Result values do not match their hashed source reports")
    if result.get("promoted") or result.get("improvement_claim") is not None:
        raise ValueError("This publisher is for unpromoted research evidence only")
    if result["human_validation"]["accuracy"] is not None or result["human_validation"]["labelled"]!=baseline["human_validation"]["labelled"]:
        raise ValueError("Human accuracy lacks independent reviewed evidence")
    metrics={r["metric"]:r for r in result["historical_baseline"]}
    shown=["defect.all_reports.rolling_defect.recall","defect.all_reports.rolling_defect.mature_episode_precision",
           "defect.excluding_explicit_recall_reports.rolling_defect.recall","defect.excluding_explicit_recall_reports.rolling_defect.mature_episode_precision",
           "fuel_holdout.method.recall","fuel_holdout.method.mature_episode_precision",
           "category.labels.accuracy","category.descriptions.accuracy"]
    return dict(schema_version=1,status=result["status"],notice=result["notice"],targets=result["targets"],
                human_validation=result["human_validation"],untouched_test=result["untouched_test"]["status"],
                source=str(path.relative_to(ROOT)),source_sha256=digest(path),
                metrics=[{k:metrics[name][k] for k in ["metric","numerator","denominator","value","confidence_interval_95","split","label_source","source"]} for name in shown],
                development_ceiling={variant:{"eligible_campaigns":b["label_conditional_opportunity"]["campaigns"],
                                             "campaigns_with_matching_evidence":b["label_conditional_opportunity"]["with_prior_evidence"],
                                             "note":"Input opportunity under fixed labels, not achieved recall or universal model ceiling"}
                                     for variant,b in result["development_audit"]["blocks"].items()})


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("phase",choices=["build","publish","publish-prospective","check"])
    p.add_argument("--audit",default="reports/improvement/runs/audit_v1/results.json")
    args=p.parse_args();path=ROOT/"reports/improvement/results.json"
    if args.phase=="build":build(ROOT/args.audit);print(path);return
    expected=dashboard_payload(load(path),path);dest=ROOT/"dashboard/src/ai/mlImprovement.json"
    if (ROOT/"reports/improvement/phase1/FREEZE_HASHES.json").exists():
        expected=prospective_payload(expected)
    if args.phase=="check":
        if load(dest)!=expected:raise ValueError("Dashboard has drifted from verified results")
        print("Dashboard source hash and values verified")
    elif args.phase=="publish-prospective":
        publish_metadata(dest,expected);print(dest)
    else:
        write_once(dest,expected);print(dest)


def prospective_payload(payload):
    """Verified metadata overlay; frozen numerical evidence is never regenerated."""
    from src.eval.prospective_io import verify_freeze,manifest_chain,PHASE
    frozen,hashes,tag=verify_freeze(ROOT)
    protocol=load(ROOT/PHASE/"protocol.json")
    manifest,chain=manifest_chain(ROOT,"HEAD")
    if manifest["status"]!="reserved" or manifest["snapshots"] or manifest.get("final_analysis"):
        raise ValueError("This publication is only for a reservation with no collected data")
    if frozen["mode"]!="baseline_replication":raise ValueError("Expected verified baseline replication")
    w=protocol["prospective"]
    return payload | dict(
        status="prospective_reserved_no_improvement_demonstrated",
        notice="Prospective 2027-2028 test reserved. No improved score has been demonstrated. Human semantic validation remains pending.",
        custody_notice="Procedural custody is tamper-evident, not enforced access control. No-peeking is honor-system; public outcomes can be re-fetched.",
        historical_notice="Retrospective, model-labelled, not production-validated",
        untouched_test=f"reserved: {w['flag_start']} to {w['flag_end']}; outcome cutoff {w['outcome_cutoff']}; minimum {w['min_campaigns']} campaigns; no data collected yet",
        prospective_test=dict(status="reserved",flag_start=w["flag_start"],flag_end=w["flag_end"],outcome_cutoff=w["outcome_cutoff"],minimum_campaigns=w["min_campaigns"],
                             preregistration_path=PHASE+"/PREREGISTRATION.md",freeze_tag=frozen["freeze_tag"],data_collected=False,mode=frozen["mode"],
                             preregistration_sha256=hashes["preregistration_sha256"],protocol_sha256=hashes["protocol_sha256"],freeze_tag_commit=tag,manifest_sha256=chain[-1]["sha256"]))


def publish_metadata(dest,expected):
    from src.eval.prospective_io import atomic_json
    existing=load(dest)
    for field in ["metrics","targets","human_validation","source","source_sha256","development_ceiling"]:
        if existing[field]!=expected[field]:raise ValueError("Metadata publication would change verified scores or source")
    atomic_json(dest,expected)


if __name__=="__main__":main()
