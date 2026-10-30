"""Train, freeze and reanalyse the repaired historical defect experiment.

python -m scripts.defect_prediction_eval tune
python -m scripts.defect_prediction_eval test

The known 2021-2024 window is explicitly a reanalysis, never a fresh holdout.
No model calls, no overwrite of the original experiment, no production change.
"""
from __future__ import annotations

import argparse
import itertools
import json
from pathlib import Path

import numpy as np
import pandas as pd

from scripts.defect_repair import DATA, OUT, ROOT, write_json
from scripts.defect_prepare_inputs import file_sha256
from scripts.ai_oos_backtest import canonical_hash, gate
from scripts.defect_backtest import score_series, complaint_records, _validate_label_set
from src.eval.defect_prediction import candidates, alert_episodes, reference_alerts, evaluate, join_labels

GRID = {"window": [4, 8, 13], "min_count": [2, 3, 5], "max_tail": [0.05, 0.1, 0.2]}


def inputs():
    protocol = json.loads((OUT / "protocol.json").read_text())
    for spec in protocol["inputs"].values():
        if file_sha256(ROOT / spec["path"]) != spec["sha256"]:
            raise ValueError("Prepared input differs from the pinned protocol")
    clf = pd.read_parquet(OUT / "classifications.parquet")
    labels = pd.read_parquet(OUT / "recall_labels.parquet")
    version = protocol["classifier"]
    c, r = join_labels(pd.read_parquet(DATA / "complaints.parquet"),
                       pd.read_parquet(DATA / "recall_scopes.parquet"), clf, labels,
                       model=version["model"], prompt=version["prompt_version"], taxonomy=version["taxonomy_sha256"])
    tax = json.loads((ROOT / "reports/defect/taxonomy.json").read_text())
    if tax["sha256"] != version["taxonomy_sha256"] or canonical_hash(tax["body"]) != tax["sha256"]:
        raise ValueError("Frozen taxonomy changed")
    for name, frame in (("complaints", c), ("recalls", r)):
        _validate_label_set(frame, tax, component_col="component", label_col="label_id", what=name)
    hashes = {"protocol": file_sha256(OUT / "protocol.json"),
              "classifications": file_sha256(OUT / "classifications.parquet"),
              "recall_labels": file_sha256(OUT / "recall_labels.parquet"),
              "scorer": file_sha256(ROOT / "src/eval/defect_prediction.py"),
              "runner": file_sha256(Path(__file__))}
    return protocol, c, r, hashes


def compact(result):
    return {k: v for k, v in result.items() if k not in {"alert_details", "campaign_hits"}}


def without_known_recalls(c):
    # Explicit recall/campaign narratives can be reporting/parts-availability
    # reactions, rather than discovery signals. Frozen sensitivity, not labels.
    return c[~c.text.str.contains(r"\brecall\w*\b|\bcampaign\b", case=False, regex=True, na=False)].copy()


def tune():
    dest = OUT / "prediction_config.json"
    if dest.exists():
        raise ValueError("Configuration already frozen; refusing outcome-driven retuning")
    p, c, r, hashes = inputs()
    start, end = p["train_window"]
    c = c[c.datea.between(start, end)]
    r = r[r.rcdate.between(start, end)]
    trials = []
    for w in GRID["window"]:
        rows = candidates(c, window=w, end=end)
        for minimum, tail in itertools.product(GRID["min_count"], GRID["max_tail"]):
            cfg = {"window": w, "min_count": minimum, "max_tail": tail}
            alerts = alert_episodes(rows, min_count=minimum, max_tail=tail, start=start, end=end)
            trials.append({"config": cfg, "metrics": compact(evaluate(alerts, r, start=start, end=end))})
    best = max(trials, key=lambda x: (x["metrics"]["objective"], x["metrics"]["episode_precision"] or 0,
                                      -x["metrics"]["alerts"], -x["config"]["window"], -x["config"]["max_tail"]))
    body = {"config": best["config"], "grid": GRID, "selection": "training harmonic mean of campaign recall and mature episode precision; ties: precision, fewer alerts, shorter window, stricter tail",
            "train_window": p["train_window"], "evaluation_window": p["evaluation_window"],
            "hashes": hashes, "train": best["metrics"], "trials": trials,
            "sensitivity": "also evaluate identical frozen parameters after excluding explicit recall/campaign mentions; never select between the two using test results"}
    write_json(dest, {"sha256": canonical_hash(body), "body": body})
    print(json.dumps({"config": best["config"], "training": best["metrics"]}, indent=2))


def old_alerts(c, start, end):
    cfg = json.loads((ROOT / "reports/defect/defect_config.json").read_text())["body"]["thresholds"]
    series = score_series(complaint_records(c[c.label_id.ne("other_unclear")], True), True, end)
    rows = []
    for r in series:
        if gate(r, cfg):
            y, w = r["iso_week"].split("-W")
            available = pd.Timestamp.fromisocalendar(int(y), int(w), 1) + pd.Timedelta(days=7)
            rows.append({"make": r["entity_2"], "component": r["category"], "label_id": r["entity_3"],
                         "available_at": available.date().isoformat(), "record_count": r["record_count"],
                         "tail_score": 0})
    return alert_episodes(rows, min_count=0, max_tail=1, start=start, end=end)


def compare(c, r, cfg, start, end):
    rows = candidates(c, window=cfg["window"], end=end)
    alerts = alert_episodes(rows, min_count=cfg["min_count"], max_tail=cfg["max_tail"], start=start, end=end)
    model = evaluate(alerts, r, start=start, end=end)
    count = evaluate(reference_alerts(rows, budget=len(alerts), start=start, end=end, seed=None), r, start=start, end=end)
    draws = []
    for i in range(100):
        ref = reference_alerts(rows, budget=len(alerts), start=start, end=end, seed=20261029 + i)
        draws.append({"seed": 20261029 + i, **compact(evaluate(ref, r, start=start, end=end))})
    recall_values = [d["campaign_recall"] for d in draws]
    old = evaluate(old_alerts(c, start, end), r, start=start, end=end)
    return {"rolling_defect": model, "count_reference": count, "original_weekly_on_repaired_data": old,
            "random": {"draws": draws, "mean_campaign_recall": float(np.mean(recall_values)),
                       "campaign_recall_95_percentile_interval": np.quantile(recall_values, [0.025, 0.975]).tolist(),
                       "fraction_at_least_detector_recall": sum(v >= model["campaign_recall"] for v in recall_values) / 100},
            "note": "Original weekly alerts use their own count. Count/random references use exactly the rolling detector's alert count and 13-week cooldown. Count/random are retrospective references, not online deployment policies."}


def render(result):
    lines = ["# Repaired defect prediction experiment", "", "**Retrospective reanalysis, not a new holdout or validated physical-defect prediction.**", "",
             "Scope: Ford, Honda, Hyundai, Kia and Toyota; model years 2015–2024; FUEL SYSTEM; vehicle recalls. The original 6/269 result is preserved in its original files. These denominators differ and must not be compared as a percentage-point improvement.", "",
             f"Complete model coverage: {result['coverage']['complaints']} complaints and {result['coverage']['recall_scope_rows']} recall scope rows. Human labels remain a separate requirement.", "",
             f"Frozen training-selected configuration: `{result['config']}`.", ""]
    for name in ("all_reports", "excluding_explicit_recall_reports"):
        block = result[name]
        lines += [f"## {name.replace('_', ' ').capitalize()}", "",
                  "| Strategy | Campaigns detected | Recall | Alert episodes | Mature episode precision | Median lead (weeks) |",
                  "|---|---:|---:|---:|---:|---:|"]
        for label in ("rolling_defect", "count_reference", "original_weekly_on_repaired_data"):
            m = block[label]
            precision = 'n/a' if m['episode_precision'] is None else f"{m['episode_precision']:.1%} ({m['confirmed_mature_alerts']}/{m['mature_alerts']})"
            lead = 'n/a' if m['median_lead_weeks'] is None else f"{m['median_lead_weeks']:.1f}"
            lines.append(f"| {label} | {m['hits']}/{m['campaigns']} | {m['campaign_recall']:.1%} | {m['alerts']} | {precision} | {lead} |")
        random = block['random']
        lines += ["", f"Equal-budget random reference: mean recall {random['mean_campaign_recall']:.1%}; 95% empirical percentile interval {random['campaign_recall_95_percentile_interval']}. Fraction of 100 seeded draws with recall at least the detector: {random['fraction_at_least_detector_recall']:.2f}. This is a reference distribution, not a confidence interval for prospective effectiveness.", ""]
    lines += ["## Interpretation", "",
              "- Count each recall campaign once, retain misses, and never match `other_unclear` as a defect.",
              "- A week's counts are available the following Monday. Matching requires 7–364 days of lead.",
              "- Primary precision uses only alerts with the entire 364-day follow-up, including known positives under the same rule; late alerts are censored, not assumed false.",
              "- All training choices are frozen before reanalysis. The 2021–2024 window was previously inspected; independent future validation is still required.",
              "- The recall/campaign-mention sensitivity removes obvious post-recall reporting, but cannot eliminate model pretraining leakage or all reporting bias.",
              "- The same model labels complaints and recalls; a make/component/defect match does not prove identical physical defects or vehicle applicability.",
              "- No accident-reduction, real-customer accuracy, or production superiority claim follows from this experiment.", ""]
    return "\n".join(lines)


def test():
    p, c, r, hashes = inputs()
    frozen = json.loads((OUT / "prediction_config.json").read_text())
    body = frozen["body"]
    if frozen["sha256"] != canonical_hash(body) or hashes != body["hashes"]:
        raise ValueError("Configuration, code, or inputs changed since training")
    # Exclusive reservation makes repeats visible, including incomplete runs.
    with (OUT / ".prediction_test_started").open("x") as f:
        f.write(frozen["sha256"] + "\n")
    start, end = p["evaluation_window"]
    result = {"status": p["status"], "config_sha256": frozen["sha256"], "config": body["config"],
              "coverage": {"complaints": len(c), "recall_scope_rows": len(r),
                           "model_labelled_complaints": len(c), "model_labelled_recall_scopes": len(r)},
              "all_reports": compare(c, r, body["config"], start, end),
              "excluding_explicit_recall_reports": compare(without_known_recalls(c), r, body["config"], start, end),
              "excluded_recall_mention_complaints": len(c) - len(without_known_recalls(c))}
    write_json(OUT / "prediction_results.json", result)
    (OUT / "PREDICTION_REPAIR.md").write_text(render(result))
    print(json.dumps({k: {"rolling": compact(v["rolling_defect"]), "count": compact(v["count_reference"]),
                         "random_mean_recall": v["random"]["mean_campaign_recall"]}
                      for k, v in result.items() if k in {"all_reports", "excluding_explicit_recall_reports"}}, indent=2))


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("phase", choices=["tune", "test"])
    args = p.parse_args()
    {"tune": tune, "test": test}[args.phase]()


if __name__ == "__main__":
    main()
