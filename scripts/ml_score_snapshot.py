"""Read-only score inventory; creates a new report and refuses replacement.

No fitting, selection, replay, or change to any historical evaluation rule.
Run after verify_ml_pipeline with its --out under reports/improvement.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]


def digest(path):
    with (ROOT / path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def read(path):
    return json.loads((ROOT / path).read_text())


def wilson(k, n):
    if not n:
        return None
    z = 1.959963984540054
    p = k / n
    den = 1 + z * z / n
    center = (p + z * z / (2 * n)) / den
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / den
    return [max(0.0, center - half), min(1.0, center + half)]


def snapshot():
    commit = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    report = {
        "status": "baseline_only_no_improvement_claim",
        "code_commit": commit,
        "snapshot_command": ".venv-hackathon/bin/python -m scripts.ml_score_snapshot",
        "snapshot_script_sha256": digest("scripts/ml_score_snapshot.py"),
        "baseline_comparison": "Fresh category diagnostics agree with saved scores; frozen defect/fuel replays match exactly. Safety/OOS are saved results, not newly replayed.",
        "confidence_interval_note": "Wilson intervals are descriptive binomial intervals. Campaign dependence, repeated alerts, authored templates and clustered scope rows invalidate a simple independent-sample generalization interpretation. No causal or production claim follows.",
        "metrics": [],
        "provenance_note": "code_commit identifies the current verification checkout. Historical training commits not present in source reports remain unknown; they are not inferred from this checkout.",
    }
    metrics = report["metrics"]

    def add(name, k, n, *, source, key, split, labels, scope, command, config, data, value=None, ci=True, note="", seed=None):
        val = k / n if value is None and k is not None and n else value
        metrics.append(dict(metric=name, numerator=k, denominator=n, value=val,
                            confidence_interval_95=wilson(k, n) if ci and k is not None and n else None,
                            confidence_interval_method="descriptive Wilson" if ci and k is not None and n else "not applicable or not estimated; see note",
                            split=split, label_source=labels, scope=scope, baseline_comparison="baseline; no candidate model evaluated",
                            exact_command=command, config_hash=config, data_hash=data, code_commit=commit,
                            original_experiment_code_commit=None, seed=seed,
                            source=source, source_key=key, source_sha256=digest(source), note=note))

    source = "reports/improvement/pipeline_recheck.json"
    pipeline = read(source)
    settings = {"model_sha256": pipeline["model_sha256"], "floor": .35, "margin": .05, "timeout_ms": 25, "records": 76}
    report["category_config"] = settings
    conf = hashlib.sha256(json.dumps(settings, sort_keys=True).encode()).hexdigest()
    for profile, d in pipeline["category_diagnostics"].items():
        rows = d["rows"]
        correct = sum(r["prediction"] == r["gold"] for r in rows)
        accepted = sum(bool(r["prediction"]) for r in rows)
        data_hash = hashlib.sha256(json.dumps([(r["text"], r["gold"]) for r in rows], sort_keys=True).encode()).hexdigest()
        common = dict(source=source, split="authored development diagnostic; not held out", labels=d["label_source"],
                      scope={"pack": "automotive_nhtsa", "authored_rows": len(rows), "makes_years_campaigns": "not applicable"},
                      command="FRONTLINE_TEST_ISOLATION=1 .venv-hackathon/bin/python -m scripts.verify_ml_pipeline --records 76 --out reports/improvement/pipeline_recheck.json",
                      config=conf, data=data_hash)
        for name, k, n in [("accuracy", correct, len(rows)), ("accepted_precision", correct, accepted), ("coverage", accepted, len(rows))]:
            add(f"category.{profile}.{name}", k, n, key=f"category_diagnostics.{profile}.{name}", **common)
    report["category_per_class_support"] = {p: d["per_category"] for p, d in pipeline["category_diagnostics"].items()}
    report["pair_diagnostic_verbatim"] = pipeline["pair_diagnostic"]
    report["pair_diagnostic_caveat"] = "The 12 authored pairs are development fixtures. ONNX hard_negative_same_category: n=3, positives=0, P@5=0; novel_true: n=2, positives=0, P@5=0; paraphrase_positive: n=6, positives=6, P@5=1. Per-class, per-query candidate partitioning and absence of positive controls prevent these figures from establishing novel-match retrieval quality. Do not change these frozen scores; build an independent mixed-candidate benchmark after approval. A confidence interval for novel-true recall is undefined with zero positives."

    repair_source = "reports/defect/repair/prediction_results.json"
    repair = read(repair_source)
    protocol = read("reports/defect/repair/protocol.json")
    frozen = read("reports/defect/repair/prediction_config.json")
    def strategy(prefix, m, common, key):
        add(prefix + ".recall", m["hits"], m["campaigns"], key=key + ".hits/campaigns", **common)
        add(prefix + ".mature_episode_precision", m["confirmed_mature_alerts"], m["mature_alerts"], key=key + ".confirmed_mature_alerts/mature_alerts", **common)
        recall, prec = m["campaign_recall"], m["episode_precision"]
        add(prefix + ".harmonic_objective", 2 * recall * prec if prec is not None else None, recall + prec if prec is not None else None,
            value=m["objective"], ci=False, key=key + ".objective", note="Harmonic mean of campaign recall and episode precision (different units), not ordinary per-example F1. No joint cluster-bootstrap interval estimated.", **common)
        add(prefix + ".median_lead_weeks", None, m["hits"], value=m["median_lead_weeks"], ci=False, key=key + ".median_lead_weeks",
            note="Median over detected campaigns only; numerator is not applicable. No median confidence interval estimated.", **common)
        for field in ["alerts", "mature_alerts", "confirmed_mature_alerts", "censored_alerts"]:
            if field in m:
                add(prefix + "." + field, m[field], m["alerts"], value=m[field], ci=False, key=key + "." + field,
                    note="Count, not a rate; denominator is total alert episodes. Census count has no sampling CI.", **common)

    for block in ["all_reports", "excluding_explicit_recall_reports"]:
        common = dict(source=repair_source, split="2021-2024 inspected historical reanalysis", labels="model complaint and recall labels + official recall dates",
                      scope=protocol["scope"], command="FRONTLINE_TEST_ISOLATION=1 .venv-hackathon/bin/python -m scripts.defect_verify",
                      config=frozen["sha256"], data={k:v["sha256"] for k,v in protocol["inputs"].items()})
        for name in ["rolling_defect", "count_reference", "original_weekly_on_repaired_data"]:
            strategy("defect." + block + "." + name, repair[block][name], common, block + "." + name)
        r = repair[block]["random"]
        draws = r["draws"]
        add("defect." + block + ".random_mean_recall", sum(d["hits"] for d in draws), sum(d["campaigns"] for d in draws),
            ci=False, value=r["mean_campaign_recall"], key=block + ".random.mean_campaign_recall", seed=[d["seed"] for d in draws],
            note=f"Repeated draws over the same campaigns. Empirical 95% reference interval {r['campaign_recall_95_percentile_interval']}; this is not a confidence interval for effectiveness.", **common)
        add("defect." + block + ".random_at_least_detector", sum(d["campaign_recall"] >= repair[block]["rolling_defect"]["campaign_recall"] for d in draws), len(draws),
            key=block + ".random.fraction_at_least_detector_recall", note="Monte Carlo fraction conditional on this historical candidate pool, not a prospective superiority test.", **common)

    source = "reports/defect/fuel_holdout/holdout_results.json"
    h = read(source)
    hp = read("reports/defect/fuel_holdout/protocol.json")
    common = dict(source=source, split="2025 previously opened holdout; outcome cutoff 2026-09-30", labels="student model complaint labels + model recall labels + recall dates",
                  scope=h["scope"], command="FRONTLINE_TEST_ISOLATION=1 .venv-hackathon/bin/python -m scripts.fuel_holdout verify",
                  config=h["selection_sha256"], data={k:v["sha256"] for k,v in hp["inputs"].items()})
    for name in ["method", "count_baseline"]:
        strategy("fuel_holdout." + name, h[name], common, name)
    draws = h["random_reference"]["draws"]
    add("fuel_holdout.random_mean_recall", sum(d["hits"] for d in draws), sum(d["campaigns"] for d in draws),
        value=h["random_reference"]["mean_recall"], ci=False, key="random_reference.mean_recall", note="Mean over repeated draws on the same eight campaigns. No prospective confidence interval.", **common)
    add("fuel_holdout.random_at_least_method", sum(d["campaign_recall"] >= h["method"]["campaign_recall"] for d in draws), len(draws),
        key="random_reference.fraction_at_least_method", **common)
    report["holdout_gate"] = {k:h[k] for k in ["target_met", "human_validation", "promoted_to_production"]}

    for kind in ["safety", "oos"]:
        source = "reports/nhtsa/backtest_safety.json" if kind == "safety" else "reports/oos/oos_test_results.json"
        d = read(source)
        config = read("reports/oos/oos_config.json")
        common = dict(source=source, split="full historical retrospective backtest including 2026 recalls" if kind == "safety" else "2021-2024 previously opened OOS test",
                      labels="NHTSA component and official recall scope/date, not human physical-defect labels",
                      scope={"makes": protocol["scope"]["makes"], "model_years": [2015, 2024], "components": "all ingested components; not fuel-only"},
                      command=d["meta"]["command"] if kind == "safety" else "Original exact test invocation not recorded in results JSON; no new OOS test run performed",
                      config=None if kind == "safety" else d["config_sha256"],
                      data="Historical raw input hash not recorded in this result; not freshly verified" if kind == "safety" else config["body"]["data"]["flat_cmpl"]["sha256"])
        for block in (["summary", "summary.recent"] if kind == "safety" else ["first_flag", "actionable_52w"]):
            m = d
            for part in block.split("."):
                m = m[part]
            add(kind + "." + block + ".scope_recall", m["hits"], m["recalls_scored"], key=block + ".hits/recalls_scored", **common)
            c = m["campaign_level"]
            add(kind + "." + block + ".campaign_recall", c["hits"], c["campaigns"], key=block + ".campaign_level.hits/campaigns", **common)
            for grain, obj, n in [("scope",m,m["hits"]),("campaign",c,c["hits"])]:
                add(kind + "." + block + "." + grain + "_median_lead_weeks", None, n, value=obj["lead_weeks_median"], ci=False,
                    key=block + (".campaign_level" if grain == "campaign" else "") + ".lead_weeks_median", note="Median over detected units only; no median confidence interval estimated.", **common)
        for name,k,n in [("slice_week_precision","confirmed_slice_weeks","flagged_slice_weeks"),("episode_precision","confirmed_episodes","flag_episodes")]:
            add(kind + "." + name, d["precision"][k], d["precision"][n], key="precision." + k + "/" + n, **common)
    source = "reports/defect/defect_label_sample_300.csv"
    with (ROOT / source).open() as stream:
        rows = list(csv.DictReader(stream))
    human_log = (ROOT / "reports/improvement/logs/human_accuracy.txt").read_text()
    human_check, _ = json.JSONDecoder().raw_decode(human_log[human_log.index("{"):])
    report["human_validation"] = {"labelled": sum(bool(r["label"].strip()) for r in rows), "sample_size": len(rows),
        "model_ok": human_check["model_ok"], "model_ok_source": "reports/improvement/logs/human_accuracy.txt", "accuracy": None, "confidence_interval_95": None,
        "reason": "No valid human labels; accuracy is undefined, not zero.", "split": "2021-2024 evaluation sample; never training data",
        "sample_sha256": digest(source), "classification_sha256": digest("reports/defect/repair/classifications.parquet")}
    report["calibration"] = {"ece": None, "brier_score": None, "reliability_diagram": None, "reason": "Not measured; ranking scores are not calibrated defect probabilities."}
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", default="reports/improvement/baseline.json")
    args = parser.parse_args()
    result = snapshot()
    dest = ROOT / args.out
    dest.parent.mkdir(parents=True, exist_ok=True)
    with dest.open("x") as stream:
        json.dump(result, stream, indent=2)
        stream.write("\n")
    print(f"Saved {len(result['metrics'])} baseline metrics to {dest}")


if __name__ == "__main__":
    main()
