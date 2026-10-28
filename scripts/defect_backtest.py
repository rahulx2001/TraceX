"""Defect-level out-of-sample backtest: tune on 2015-2020, freeze, test once on 2021-2024.

The detector is the existing weekly quasi-Poisson z-score
(``src.ml_runtime.anomalies.score_weekly_slices``) applied to
``make + component + defect`` slices. The defect label on each complaint comes
from the frozen train-only taxonomy and the Muse Spark classifier
(``scripts/defect_classify.py``). Recalls are labelled by the same classifier
on their defect descriptions.

Phases
    tune   Score the 2015-2020 complaint history once, evaluate the same 36
           configs as ``scripts/ai_oos_backtest.py``, choose by the same
           objective, freeze ``reports/defect/defect_config.json`` with a
           SHA-256. Refuses to re-tune unless ``--force-retune`` (logged).
    test   Verify the frozen config, score the 2021-2024 window once, and
           evaluate the frozen config plus the component-level baseline, the
           count baseline and the random baseline. Refuses a second test run
           unless ``--force-retest`` (logged).
    render Write ``reports/oos/DEFECT_LEVEL.md`` from the saved JSON only.

    python -m scripts.defect_backtest --phase tune
    python -m scripts.defect_backtest --phase test
    python -m scripts.defect_backtest --phase render

The component baseline uses the frozen ``abs3`` config in
``reports/oos/oos_config.json`` on the SAME complaint subset that has a defect
label, so the comparison is not distorted by classifier failures.
"""
from __future__ import annotations

import argparse
import bisect
import hashlib
import json
import math
import os
import subprocess
import sys
import time
from collections import defaultdict
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from src.backtest.engine import _weeks_between  # noqa: E402
from src.backtest.recall_lead import _first_flag, _norm, _slice_match  # noqa: E402
from src.ml_runtime.anomalies import (  # noqa: E402
    _week_monday,
    count_weekly_slices,
    iso_week_label,
    score_weekly_slices,
)
from scripts.ai_oos_backtest import (  # noqa: E402
    GRID,
    OBJECTIVE,
    PROD,
    Refused,
    build_report,
    canonical_hash,
    cfg_id,
    choose,
    gate,
    grid_configs,
    log_run,
    objective,
    recent_campaign_recall,
)
from scripts.ai_safety_backtest import RECENT_WINDOW_WEEKS  # noqa: E402

DEFECT_DIR = REPO_ROOT / "reports" / "defect"
OOS_DIR = REPO_ROOT / "reports" / "oos"
TAXONOMY_PATH = DEFECT_DIR / "taxonomy.json"
CONFIG_PATH = DEFECT_DIR / "defect_config.json"
TEST_RESULTS_PATH = DEFECT_DIR / "defect_test_results.json"
COMPONENT_RESULTS_PATH = DEFECT_DIR / "component_baseline_results.json"
BASELINE_RESULTS_PATH = DEFECT_DIR / "baseline_results.json"
EXAMPLES_PATH = DEFECT_DIR / "example_flags.json"
ACCURACY_PATH = DEFECT_DIR / "accuracy.json"
RUN_LOG = DEFECT_DIR / "run_log.jsonl"
TEST_MARKER = DEFECT_DIR / ".defect_test_run_marker"
DASHBOARD_JSON = REPO_ROOT / "dashboard" / "src" / "ai" / "defectFlags.json"
TRAIN = ("2015-01-01", "2020-12-31")
TEST = ("2021-01-01", "2024-12-31")
SEED = 20261026
RANDOM_DRAWS = 20
OTHER_ID = "other_unclear"


# ── small helpers ───────────────────────────────────────────────────────────


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _dt(raw: str, *, end: bool = False) -> datetime:
    d = date.fromisoformat(str(raw))
    return datetime(d.year, d.month, d.day, 23, 59, 59) if end else datetime(d.year, d.month, d.day)


def _monday(label: Any) -> datetime | None:
    return _week_monday(str(label or ""))


def _key(cat: Any, e2: Any, e3: Any, model_grain: bool) -> tuple:
    base = (_norm(cat), _norm(e2))
    return base + ((_norm(e3),) if model_grain else ())


def _row_key(row: dict[str, Any], model_grain: bool) -> tuple:
    return _key(row.get("category"), row.get("entity_2"), row.get("entity_3"), model_grain)


def _adv_key(adv: dict[str, Any], model_grain: bool) -> tuple:
    return _key(adv.get("scope_category"), adv.get("scope_entity_2"),
                adv.get("scope_entity_3"), model_grain)


def file_sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _git_head() -> str:
    try:
        return subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=REPO_ROOT, capture_output=True,
                              text=True, timeout=10).stdout.strip()
    except Exception:
        return ""


def _taxonomy() -> dict[str, Any]:
    return json.loads(TAXONOMY_PATH.read_text())


def _label_text(taxonomy: dict[str, Any], component: str, label_id: str) -> str:
    comp = (taxonomy.get("body", {}).get("components") or {}).get(component) or {}
    for lab in comp.get("labels") or []:
        if lab.get("id") == label_id:
            return str(lab.get("label") or label_id)
    return str(label_id)


def _load_frozen(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise Refused(f"no frozen config at {path}")
    raw = json.loads(path.read_text())
    body = raw.get("body")
    if not isinstance(body, dict) or canonical_hash(body) != raw.get("sha256"):
        raise Refused(f"frozen config hash does not verify ({path})")
    return raw


def _load_component_config() -> dict[str, Any]:
    raw = _load_frozen(OOS_DIR / "oos_config.json")
    return raw["body"]["thresholds"]


def _validate_label_set(df: pd.DataFrame, taxonomy: dict[str, Any], *, component_col: str,
                        label_col: str, what: str) -> None:
    """Every model label must be allowed for its component in the frozen taxonomy."""
    components = taxonomy.get("body", {}).get("components") or {}
    bad = []
    for comp, label in zip(df[component_col].astype(str), df[label_col].astype(str)):
        allowed = {x.get("id") for x in (components.get(comp, {}) or {}).get("labels", [])}
        allowed = allowed or {OTHER_ID}
        if label not in allowed:
            bad.append((comp, label))
    if bad:
        sample = ", ".join(f"{c}:{l}" for c, l in bad[:5])
        raise Refused(f"{what} has {len(bad)} label(s) outside the frozen taxonomy: {sample}")


def _slice_period(rows: list[dict[str, Any]], start: datetime, end: datetime) -> list[dict[str, Any]]:
    out = []
    for r in rows:
        m = _monday(r.get("iso_week"))
        if m is not None and start <= m <= end:
            out.append(r)
    return out


# ── data loading ────────────────────────────────────────────────────────────


def load_complaints(path: Path, classifications: Path, labels_mode: str, start: str, end: str) -> tuple[pd.DataFrame, dict[str, int]]:
    df = pd.read_parquet(path)
    df = df[(df["datea"] >= start) & (df["datea"] <= end)].copy()
    df["record_id"] = df["odino"].astype(str) + "|" + df["component"].astype(str)
    inputs = int(len(df))
    if labels_mode == "matched":
        cl = pd.read_parquet(classifications)
        ok = cl[cl["status"] == "ok"][["record_id", "label_id"]].drop_duplicates("record_id")
        df = df.merge(ok, on="record_id", how="inner")
    elif labels_mode == "none":
        df["label_id"] = None
    else:
        raise Refused(f"unknown labels mode {labels_mode}")
    df = df.sort_values(["datea", "odino"]).reset_index(drop=True)
    stats = {"inputs": inputs, "used": int(len(df)), "dropped": inputs - int(len(df))}
    return df, stats


def complaint_records(df: pd.DataFrame, model_grain: bool) -> list[dict[str, Any]]:
    out = []
    for r in df.itertuples():
        rec = {
            "received_at": str(r.datea),
            "occurred_at": str(r.datea),
            "category": str(r.component),
            "entity_2": str(r.make),
            "event_count": 1,
            "source": "complaint",
        }
        if model_grain:
            rec["entity_3"] = str(r.label_id)
        out.append(rec)
    return out


def load_advisories(path: Path, recall_labels: Path, labels_mode: str, start: str, end: str,
                    model_grain: bool) -> tuple[list[dict[str, Any]], dict[str, int]]:
    df = pd.read_parquet(path)
    df = df.drop_duplicates(["campno", "year", "make", "model", "component"], keep="first")
    df = df[(df["rcdate"] >= start) & (df["rcdate"] <= end)].copy()
    inputs = int(len(df))
    if labels_mode == "matched":
        lab = pd.read_parquet(recall_labels)
        lab = lab[lab["status"] == "ok"][["campno", "component", "desc_defect", "label_id"]]
        lab = lab.drop_duplicates(["campno", "component", "desc_defect"])
        df = df.merge(lab, on=["campno", "component", "desc_defect"], how="inner")
    elif labels_mode == "none":
        df["label_id"] = ""
    else:
        raise Refused(f"unknown labels mode {labels_mode}")
    advisories = []
    seen: set[str] = set()
    for r in df.itertuples():
        year = "" if r.year is None or pd.isna(r.year) else str(int(r.year))
        aid = f"{r.campno}|{year}|{r.make}|{r.model}|{r.component}"
        if aid in seen:
            aid = f"{aid}|{len(seen)}"
        seen.add(aid)
        advisories.append({
            "advisory_id": aid,
            "issued_at": _dt(str(r.rcdate)),
            "scope_category": str(r.component),
            "scope_entity_2": str(r.make),
            "scope_entity_3": str(r.label_id) if model_grain else "",
            "campno": str(r.campno),
            "rcdate": str(r.rcdate),
            "desc_defect": str(r.desc_defect),
        })
    stats = {"inputs": inputs, "used": int(len(advisories)), "dropped": inputs - int(len(advisories))}
    return advisories, stats


# ── scoring and indexed evaluation ──────────────────────────────────────────


def score_series(records: list[dict[str, Any]], model_grain: bool, end: str) -> list[dict[str, Any]]:
    counts = count_weekly_slices(records, clock="received", as_of=_dt(end, end=True), model_grain=model_grain)
    return score_weekly_slices(counts, pack_id="automotive_nhtsa")


def build_flag_index(flags: list[dict[str, Any]], model_grain: bool) -> dict[tuple, list[dict[str, Any]]]:
    index: dict[tuple, list[dict[str, Any]]] = defaultdict(list)
    for row in flags:
        index[_row_key(row, model_grain)].append(row)
    for rows in index.values():
        rows.sort(key=lambda r: str(r.get("iso_week") or ""))
    return index


def first_flag_indexed(index: dict[tuple, list[dict[str, Any]]], adv: dict[str, Any],
                       model_grain: bool) -> dict[str, Any] | None:
    for row in index.get(_adv_key(adv, model_grain), []):
        m = _monday(row.get("iso_week"))
        if m is not None and m < adv["issued_at"]:
            return row
    return None


def recent_episode_indexed(index: dict[tuple, list[dict[str, Any]]], adv: dict[str, Any],
                           model_grain: bool) -> dict[str, Any] | None:
    issued = adv["issued_at"]
    rows = []
    for row in index.get(_adv_key(adv, model_grain), []):
        m = _monday(row.get("iso_week"))
        if m is not None and m < issued:
            rows.append((m, str(row["iso_week"])))
    if not rows:
        return None
    rows.sort()
    last_m, last_w = rows[-1]
    if _weeks_between(last_m, issued) > RECENT_WINDOW_WEEKS:
        return None
    start_m, start_w = last_m, last_w
    for m, w in reversed(rows[:-1]):
        if (start_m - m).days > 7:
            break
        start_m, start_w = m, w
    lead = _weeks_between(start_m, issued)
    if lead < 1:
        return None
    return {"episode_start_week": start_w, "last_flag_week": last_w, "lead_weeks": lead}


def build_recall_index(advisories: list[dict[str, Any]], model_grain: bool) -> dict[tuple, list[dict[str, Any]]]:
    index: dict[tuple, list[dict[str, Any]]] = defaultdict(list)
    for adv in advisories:
        if model_grain and not _norm(adv.get("scope_entity_3")):
            continue
        index[_adv_key(adv, model_grain)].append(adv)
    for rows in index.values():
        rows.sort(key=lambda a: a["issued_at"])
    return index


def later_recall_obj(index: dict[tuple, list[dict[str, Any]]], flag: dict[str, Any],
                     model_grain: bool) -> dict[str, Any] | None:
    start = _monday(flag.get("iso_week"))
    if start is None:
        return None
    after = start + timedelta(days=7)
    rows = index.get(_row_key(flag, model_grain), [])
    stamps = [a["issued_at"] for a in rows]
    pos = bisect.bisect_left(stamps, after)
    return rows[pos] if pos < len(rows) else None


def later_recall_bool(index: dict[tuple, list[dict[str, Any]]], flag: dict[str, Any], model_grain: bool) -> bool:
    return later_recall_obj(index, flag, model_grain) is not None


def precision_indexed(flags: list[dict[str, Any]], recall_index: dict[tuple, list[dict[str, Any]]],
                      start: datetime, end: datetime, model_grain: bool) -> dict[str, Any]:
    period_flags = _slice_period(flags, start, end)
    confirmed = [r for r in period_flags if later_recall_bool(recall_index, r, model_grain)]
    conf_keys = {(r.get("iso_week"), _row_key(r, model_grain)) for r in confirmed}
    by_slice: dict[tuple, list] = defaultdict(list)
    conf_slice_weeks: dict[tuple, set] = defaultdict(set)
    for r in period_flags:
        key = _row_key(r, model_grain)
        m = _monday(r.get("iso_week"))
        by_slice[key].append(m)
        if (r.get("iso_week"), key) in conf_keys:
            conf_slice_weeks[key].add(m)
    episodes = conf_eps = 0
    for key, weeks in by_slice.items():
        weeks.sort()
        prev = None
        ep_conf = False
        for w in weeks + [None]:
            if w is None or (prev is not None and (w - prev).days > 7):
                episodes += 1
                conf_eps += int(ep_conf)
                ep_conf = False
                if w is None:
                    break
            ep_conf = ep_conf or (w in conf_slice_weeks[key])
            prev = w
    return {
        "flagged_slice_weeks": len(period_flags),
        "confirmed_slice_weeks": len(confirmed),
        "false_alarm_slice_weeks": len(period_flags) - len(confirmed),
        "precision_slice_weeks": round(len(confirmed) / len(period_flags), 3) if period_flags else None,
        "flag_episodes": episodes,
        "confirmed_episodes": conf_eps,
        "precision_episodes": round(conf_eps / episodes, 3) if episodes else None,
        "unconfirmed_slice_weeks": len(period_flags) - len(confirmed),
    }


def precision_slow(flags: list[dict[str, Any]], advisories: list[dict[str, Any]], start: datetime,
                   end: datetime, model_grain: bool) -> dict[str, Any]:
    period_flags = _slice_period(flags, start, end)
    confirmed = []
    for r in period_flags:
        m = _monday(r.get("iso_week"))
        if m is None:
            continue
        after = m + timedelta(days=7)
        if any(_slice_match(r, a, model_grain=model_grain) and a["issued_at"] >= after for a in advisories):
            confirmed.append(r)
    conf_keys = {(r.get("iso_week"), _row_key(r, model_grain)) for r in confirmed}
    by_slice: dict[tuple, list] = defaultdict(list)
    conf_slice_weeks: dict[tuple, set] = defaultdict(set)
    for r in period_flags:
        key = _row_key(r, model_grain)
        m = _monday(r.get("iso_week"))
        by_slice[key].append(m)
        if (r.get("iso_week"), key) in conf_keys:
            conf_slice_weeks[key].add(m)
    episodes = conf_eps = 0
    for key, weeks in by_slice.items():
        weeks.sort()
        prev = None
        ep_conf = False
        for w in weeks + [None]:
            if w is None or (prev is not None and (w - prev).days > 7):
                episodes += 1
                conf_eps += int(ep_conf)
                ep_conf = False
                if w is None:
                    break
            ep_conf = ep_conf or (w in conf_slice_weeks[key])
            prev = w
    return {
        "flagged_slice_weeks": len(period_flags),
        "confirmed_slice_weeks": len(confirmed),
        "false_alarm_slice_weeks": len(period_flags) - len(confirmed),
        "precision_slice_weeks": round(len(confirmed) / len(period_flags), 3) if period_flags else None,
        "flag_episodes": episodes,
        "confirmed_episodes": conf_eps,
        "precision_episodes": round(conf_eps / episodes, 3) if episodes else None,
        "unconfirmed_slice_weeks": len(period_flags) - len(confirmed),
    }


def evaluate(series: list[dict[str, Any]], advisories: list[dict[str, Any]], cfg: dict[str, Any], *,
             model_grain: bool, start: str, end: str, validate: bool = False,
             keep_details: bool = False) -> dict[str, Any]:
    s, e = _dt(start), _dt(end, end=True)
    flagged = [dict(r, is_anomaly=True) for r in series if gate(r, cfg)]
    flag_index = build_flag_index(flagged, model_grain)
    recall_index = build_recall_index(advisories, model_grain)
    prec = precision_indexed(flagged, recall_index, s, e, model_grain)
    scored: dict[int, dict[str, Any]] = {}
    first_mismatch = ep_mismatch = 0
    if validate:
        from scripts.ai_safety_backtest import _recent_episode
    for i, adv in enumerate(advisories):
        flag = first_flag_indexed(flag_index, adv, model_grain)
        ep = recent_episode_indexed(flag_index, adv, model_grain)
        if validate:
            slow_flag = _first_flag(flagged, adv, model_grain=model_grain)
            slow_ep = _recent_episode(flagged, adv, adv["issued_at"], model_grain=model_grain)
            first_mismatch += int((flag is None) != (slow_flag is None) or
                                  (flag is not None and slow_flag is not None and flag.get("iso_week") != slow_flag.get("iso_week")))
            ep_mismatch += int(ep != slow_ep)
        lead = _weeks_between(_monday(flag.get("iso_week")), adv["issued_at"]) if flag is not None else 0
        scored[i] = {cfg_id(cfg): (str(flag["iso_week"]) if flag is not None else None, lead, ep)}
    if validate:
        slow_prec = precision_slow(flagged, advisories, s, e, model_grain)
        if slow_prec != prec:
            raise Refused(f"indexed precision mismatch: {prec} != {slow_prec}")
        if first_mismatch or ep_mismatch:
            raise Refused(f"indexed recall evaluation mismatch: first_flag={first_mismatch}, recent_episode={ep_mismatch}")
    report = build_report(advisories, scored, cfg_id(cfg), prec["unconfirmed_slice_weeks"])
    camp = recent_campaign_recall(report)
    out = {
        "config": cfg,
        "id": cfg_id(cfg),
        "recent_campaign": camp,
        "precision": prec,
        "precision_episodes": prec["precision_episodes"],
        "objective": objective(camp["recall_rate"], prec["precision_episodes"]),
        "recalls_scored": len(advisories),
        "validation": {"first_flag_mismatches": first_mismatch, "recent_episode_mismatches": ep_mismatch},
    }
    if keep_details:
        out["report"] = report
        out["flagged"] = flagged
        out["flag_index"] = flag_index
        out["recall_index"] = recall_index
    return out


def evaluate_selected(selected: list[dict[str, Any]], advisories: list[dict[str, Any]], *,
                      model_grain: bool, start: str, end: str, keep_details: bool = False) -> dict[str, Any]:
    s, e = _dt(start), _dt(end, end=True)
    flag_index = build_flag_index(selected, model_grain)
    recall_index = build_recall_index(advisories, model_grain)
    prec = precision_indexed(selected, recall_index, s, e, model_grain)
    scored: dict[int, dict[str, Any]] = {}
    for i, adv in enumerate(advisories):
        flag = first_flag_indexed(flag_index, adv, model_grain)
        ep = recent_episode_indexed(flag_index, adv, model_grain)
        lead = _weeks_between(_monday(flag.get("iso_week")), adv["issued_at"]) if flag is not None else 0
        scored[i] = {"selected": (str(flag["iso_week"]) if flag is not None else None, lead, ep)}
    report = build_report(advisories, scored, "selected", prec["unconfirmed_slice_weeks"])
    camp = recent_campaign_recall(report)
    out = {
        "recent_campaign": camp,
        "precision": prec,
        "precision_episodes": prec["precision_episodes"],
        "objective": objective(camp["recall_rate"], prec["precision_episodes"]),
        "recalls_scored": len(advisories),
        "selected_slice_weeks": len(selected),
    }
    if keep_details:
        out["report"] = report
    return out


# ── baselines ───────────────────────────────────────────────────────────────


def positive_universe(series: list[dict[str, Any]], start: str, end: str) -> list[dict[str, Any]]:
    s, e = _dt(start), _dt(end, end=True)
    return [r for r in series if (m := _monday(r.get("iso_week"))) is not None and s <= m <= e
            and int(r.get("record_count") or 0) > 0]


def count_baseline(series: list[dict[str, Any]], *, budget: int, model_grain: bool,
                   start: str, end: str) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    universe = positive_universe(series, start, end)
    universe.sort(key=lambda r: (-int(r.get("record_count") or 0), str(r.get("iso_week")), _row_key(r, model_grain)))
    selected = universe[:budget]
    return selected, {
        "grain": "make+component+defect" if model_grain else "make+component",
        "budget_slice_weeks": budget,
        "universe_positive_slice_weeks": len(universe),
        "selection": "highest raw weekly complaint count; ties -> earlier week, then slice key",
    }


def random_baseline(series: list[dict[str, Any]], *, budget: int, model_grain: bool,
                    start: str, end: str, seed: int) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    universe = positive_universe(series, start, end)
    rng = np.random.default_rng(seed)
    n = min(budget, len(universe))
    idx = rng.choice(len(universe), size=n, replace=False)
    selected = [universe[int(i)] for i in sorted(idx)]
    return selected, {
        "grain": "make+component+defect" if model_grain else "make+component",
        "budget_slice_weeks": budget,
        "universe_positive_slice_weeks": len(universe),
        "seed": seed,
        "selection": "uniform random slice-weeks without replacement, fixed seed",
    }


def baseline_block(series: list[dict[str, Any]], advisories: list[dict[str, Any]], flags: list[dict[str, Any]], *,
                   model_grain: bool, start: str, end: str) -> dict[str, Any]:
    budget = len(_slice_period(flags, _dt(start), _dt(end, end=True)))
    count_flags, count_def = count_baseline(series, budget=budget, model_grain=model_grain, start=start, end=end)
    random_flags, random_def = random_baseline(series, budget=budget, model_grain=model_grain, start=start, end=end, seed=SEED)
    count_eval = evaluate_selected(count_flags, advisories, model_grain=model_grain, start=start, end=end)
    random_eval = evaluate_selected(random_flags, advisories, model_grain=model_grain, start=start, end=end)
    draw_metrics = []
    for i in range(RANDOM_DRAWS):
        draw_flags, _ = random_baseline(series, budget=budget, model_grain=model_grain, start=start, end=end, seed=SEED + i + 1)
        ev = evaluate_selected(draw_flags, advisories, model_grain=model_grain, start=start, end=end)
        draw_metrics.append({"seed": SEED + i + 1, "campaign_recall": ev["recent_campaign"]["recall_rate"],
                             "median_lead": ev["recent_campaign"]["lead_weeks_median"],
                             "episode_precision": ev["precision_episodes"],
                             "episodes": ev["precision"]["flag_episodes"]})
    return {
        "budget_slice_weeks": budget,
        "count": {**count_def, "metrics": count_eval},
        "random": {**random_def, "metrics": random_eval, "draws": draw_metrics},
    }


# ── tune / test ─────────────────────────────────────────────────────────────


def check_tune_allowed(force: bool) -> None:
    if CONFIG_PATH.exists() and not force:
        raise Refused(f"frozen config exists at {CONFIG_PATH}; refusing to re-tune (pass --force-retune to override, which is logged)")


def check_test_allowed(force: bool) -> None:
    if TEST_RESULTS_PATH.exists() and not force:
        raise Refused(f"test results already exist at {TEST_RESULTS_PATH}; the out-of-sample test runs once "
                      "(pass --force-retest to override, which is logged)")
    if TEST_MARKER.exists() and not force:
        raise Refused(f"test evaluation already started or incomplete at {TEST_MARKER}; refusing repeat run")


def reserve_test_run(force: bool) -> None:
    if force and TEST_MARKER.exists():
        try:
            TEST_MARKER.unlink()
        except OSError:
            pass
    try:
        fd = os.open(str(TEST_MARKER), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        with os.fdopen(fd, "w") as fh:
            fh.write(f"started at {utc_now()}\n")
    except FileExistsError:
        if not force:
            raise Refused(f"concurrent or prior incomplete test evaluation detected at {TEST_MARKER}")


def data_profile(complaints_path: Path, classifications_path: Path, recalls_path: Path,
                 recall_labels_path: Path) -> dict[str, Any]:
    return {
        "complaints": str(complaints_path),
        "complaints_sha256": file_sha(complaints_path),
        "classifications": str(classifications_path),
        "classifications_sha256": file_sha(classifications_path),
        "recalls": str(recalls_path),
        "recalls_sha256": file_sha(recalls_path),
        "recall_labels": str(recall_labels_path),
        "recall_labels_sha256": file_sha(recall_labels_path),
        "taxonomy_sha256": _taxonomy().get("sha256"),
    }


def run_tune(args) -> dict[str, Any]:
    check_tune_allowed(args.force_retune)
    complaints_path = Path(args.complaints)
    classifications_path = Path(args.classifications)
    recalls_path = Path(args.recalls)
    recall_labels_path = Path(args.recall_labels)
    df, comp_stats = load_complaints(complaints_path, classifications_path, "matched", TRAIN[0], TRAIN[1])
    advisories, adv_stats = load_advisories(recalls_path, recall_labels_path, "matched", TRAIN[0], TRAIN[1],
                                            model_grain=True)
    if df.empty or not advisories:
        raise Refused(f"no matched train complaints/recalls (complaints={len(df)}, recalls={len(advisories)})")
    tax = _taxonomy()
    _validate_label_set(df, tax, component_col="component", label_col="label_id", what="train complaints")
    _validate_label_set(pd.DataFrame(advisories), tax, component_col="scope_category",
                        label_col="scope_entity_3", what="train recalls")
    records = complaint_records(df, model_grain=True)
    t0 = time.time()
    series = score_series(records, True, TRAIN[1])
    grid = grid_configs()
    results = []
    for cfg in grid:
        ev = evaluate(series, advisories, cfg, model_grain=True, start=TRAIN[0], end=TRAIN[1])
        results.append({k: ev[k] for k in ("config", "id", "recent_campaign", "precision", "precision_episodes", "objective")})
    best = choose(results)
    # Exactness check on the chosen config using the existing (slow) functions.
    evaluate(series, advisories, best["config"], model_grain=True, start=TRAIN[0], end=TRAIN[1], validate=True)
    prod = next(x for x in results if x["config"] == PROD)
    regate_mismatches = sum(1 for r in series if gate(r, PROD) != bool(r.get("is_anomaly")))
    body = {
        "thresholds": best["config"],
        "config_id": best["id"],
        "production_thresholds": PROD,
        "objective": OBJECTIVE,
        "grid": GRID,
        "train_window": list(TRAIN),
        "test_window": list(TEST),
        "grain": "make+component+defect",
        "detector": "src.ml_runtime.anomalies.score_weekly_slices (received clock, entity_3=defect), re-gated",
        "taxonomy_sha256": _taxonomy().get("sha256"),
        "classifier_model": args.model,
        "classifier_prompt_version": args.prompt_version,
        "complaints_used": comp_stats,
        "train_advisories": adv_stats,
        "train_recalls_used": len(advisories),
        "train_campaigns": best["recent_campaign"]["campaigns"],
        "data": data_profile(complaints_path, classifications_path, recalls_path, recall_labels_path),
        "validation": {"first_flag_mismatches": 0, "recent_episode_mismatches": 0,
                       "regate_mismatches_vs_scorer": regate_mismatches},
        "frozen_at": utc_now(),
    }
    if regate_mismatches:
        raise Refused(f"production re-gate mismatch on {regate_mismatches} rows; refusing to freeze")
    frozen = {"sha256": canonical_hash(body), "body": body}
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    CONFIG_PATH.write_text(json.dumps(frozen, indent=2, default=str), encoding="utf-8")
    tune = {
        "generated_at": utc_now(),
        "chosen": best["id"],
        "production": prod["id"],
        "config_sha256": frozen["sha256"],
        "grid_results": results,
        "score_rows": len(series),
        "elapsed_s": round(time.time() - t0, 1),
        "complaints_used": comp_stats,
        "advisories_used": adv_stats,
        "regate_mismatches_vs_scorer": regate_mismatches,
    }
    (DEFECT_DIR / "defect_tune_results.json").write_text(json.dumps(tune, indent=2, default=str), encoding="utf-8")
    log_run(DEFECT_DIR, {"phase": "tune", "mode": "defect", "forced": bool(args.force_retune),
                         "chosen": best["id"], "config_sha256": frozen["sha256"],
                         "elapsed_s": tune["elapsed_s"]})
    return tune


def run_component(args, *, labels_mode: str, out_path: Path) -> dict[str, Any]:
    complaints_path = Path(args.complaints)
    classifications_path = Path(args.classifications)
    recalls_path = Path(args.recalls)
    recall_labels_path = Path(args.recall_labels)
    # Score with the train window as baseline history, exactly as the defect
    # test does; evaluate only the 2021-2024 test window.
    df_all, _comp_stats_all = load_complaints(complaints_path, classifications_path, labels_mode, TRAIN[0], TEST[1])
    _, comp_stats = load_complaints(complaints_path, classifications_path, labels_mode, TEST[0], TEST[1])
    advisories, adv_stats = load_advisories(recalls_path, recall_labels_path, labels_mode, TEST[0], TEST[1],
                                            model_grain=False)
    records = complaint_records(df_all, model_grain=False)
    t0 = time.time()
    series = score_series(records, False, TEST[1])
    cfg = _load_component_config()
    ev = evaluate(series, advisories, cfg, model_grain=False, start=TEST[0], end=TEST[1], validate=True)
    result = {
        "generated_at": utc_now(),
        "mode": "component",
        "labels_mode": labels_mode,
        "config": cfg,
        "config_id": cfg_id(cfg),
        "config_sha256": _load_frozen(OOS_DIR / "oos_config.json")["sha256"],
        "test_window": list(TEST),
        "metrics": {k: ev[k] for k in ("recent_campaign", "precision", "precision_episodes", "objective",
                                        "recalls_scored", "validation")},
        "complaints": comp_stats,
        "complaints_scored": int(len(df_all)),
        "advisories": adv_stats,
        "score_rows": len(series),
        "elapsed_s": round(time.time() - t0, 1),
        "note": "component baseline on the same complaint/recall subset as the defect run"
                if labels_mode == "matched" else "component detector on the full corpus (no defect labels)",
    }
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(result, indent=2, default=str), encoding="utf-8")
    log_run(DEFECT_DIR, {"phase": "component", "labels_mode": labels_mode, "config_id": result["config_id"],
                         "config_sha256": result["config_sha256"], "elapsed_s": result["elapsed_s"]})
    return result


def _recall_other_stats(recall_labels_path: Path, recalls_path: Path) -> dict[str, Any]:
    if not recall_labels_path.exists():
        return {"status": "not run"}
    descriptions = pd.read_parquet(recall_labels_path)
    scope = pd.read_parquet(recalls_path)
    scope = scope.drop_duplicates(["campno", "year", "make", "model", "component"], keep="first")
    labels = descriptions[descriptions["status"] == "ok"][
        ["campno", "component", "desc_defect", "label_id"]
    ].drop_duplicates(["campno", "component", "desc_defect"])
    merged = scope.merge(labels, on=["campno", "component", "desc_defect"], how="left")
    out: dict[str, Any] = {}
    for name, lo, hi in (("train", "2015-01-01", "2020-12-31"), ("test", "2021-01-01", "2024-12-31")):
        desc = descriptions[(descriptions["datea"] >= lo) & (descriptions["datea"] <= hi)
                            & (descriptions["status"] == "ok")]
        desc_other = desc[desc["label_id"] == OTHER_ID]
        sub = merged[(merged["rcdate"] >= lo) & (merged["rcdate"] <= hi)]
        sub_lab = sub[sub["label_id"].notna()]
        sub_other = sub_lab[sub_lab["label_id"] == OTHER_ID]
        campaigns = sorted(set(sub["campno"].astype(str)))
        camp_lab = {c: g for c, g in sub_lab.groupby(sub_lab["campno"].astype(str))}
        camp_all_other = [c for c, g in camp_lab.items() if len(g) and (g["label_id"] == OTHER_ID).all()]
        camp_any_other = [c for c, g in camp_lab.items() if (g["label_id"] == OTHER_ID).any()]
        out[name] = {
            "labelled": int(len(desc)),
            "other_unclear": int(len(desc_other)),
            "rate": round(len(desc_other) / len(desc), 3) if len(desc) else None,
            "scope_rows": int(len(sub)),
            "scope_rows_labelled": int(len(sub_lab)),
            "scope_rows_other_unclear": int(len(sub_other)),
            "scope_rows_unlabelled": int(len(sub) - len(sub_lab)),
            "campaigns": int(len(campaigns)),
            "campaigns_labelled": int(len(camp_lab)),
            "campaigns_all_other_unclear": int(len(camp_all_other)),
            "campaigns_any_other_unclear": int(len(camp_any_other)),
            "campaigns_unlabelled": int(len(campaigns) - len(camp_lab)),
        }
    return out


def select_examples(defect_ev: dict[str, Any], test_df: pd.DataFrame, advisories: list[dict[str, Any]],
                    taxonomy: dict[str, Any]) -> dict[str, Any]:
    from src.security.pii import redact_pii

    series = defect_ev["flagged"]
    recall_index = build_recall_index(advisories, model_grain=True)
    candidates = []
    for flag in _slice_period(series, _dt(TEST[0]), _dt(TEST[1], end=True)):
        if int(flag.get("record_count") or 0) < 3:
            continue
        match = later_recall_obj(recall_index, flag, True)
        candidates.append((flag, match))
    # The selection rule is fixed before the outcome is read:
    #   * 3 confirmed + 2 unconfirmed flags (so false alarms are visible);
    #   * prefer specific defect labels over other/unclear, so the examples
    #     demonstrate the defect taxonomy rather than the fallback bucket;
    #   * within each group, largest record_count first, preferring a different
    #     test year and a different defect slice;
    #   * fill from all candidates only if a group is short.
    specific = [x for x in candidates if str(x[0].get("entity_3")) != OTHER_ID]

    def pick(pool: list[tuple[dict[str, Any], dict[str, Any] | None]], confirmed: bool,
             n: int) -> list[tuple[dict[str, Any], dict[str, Any] | None]]:
        rows = [x for x in pool if (x[1] is not None) == confirmed]
        rows.sort(key=lambda x: (-int(x[0].get("record_count") or 0), str(x[0].get("iso_week")),
                                 str(x[0].get("entity_2")), str(x[0].get("category")),
                                 str(x[0].get("entity_3"))))
        chosen: list[tuple[dict[str, Any], dict[str, Any] | None]] = []
        used_years: set[str] = set()
        used_slices: set[tuple[str, str]] = set()
        for x in rows:
            year = str(x[0].get("iso_week") or "")[:4]
            key = (str(x[0].get("category")), str(x[0].get("entity_3")))
            if year in used_years or key in used_slices:
                continue
            chosen.append(x)
            used_years.add(year)
            used_slices.add(key)
            if len(chosen) == n:
                break
        if len(chosen) < n:
            chosen += [x for x in rows if x not in chosen][:n - len(chosen)]
        return chosen

    selected = pick(specific, True, 3) + pick(specific, False, 2)

    def add(pool: list[tuple[dict[str, Any], dict[str, Any] | None]], confirmed: bool, need: int) -> None:
        if need <= 0:
            return
        for x in pick(pool, confirmed, need):
            if need <= 0:
                break
            if x not in selected:
                selected.append(x)
                need -= 1

    add(candidates, True, 3 - sum(1 for _, m in selected if m is not None))
    add(candidates, False, 2 - sum(1 for _, m in selected if m is None))
    if len(selected) < 5:
        selected += [x for x in candidates if x not in selected][:5 - len(selected)]
    selected = selected[:5]

    df = test_df.copy()
    df["week"] = [iso_week_label(str(x)) for x in df["datea"]]
    flags = []
    for flag, match in selected[:5]:
        sub = df[(df["week"] == flag.get("iso_week")) & (df["make"] == flag.get("entity_2"))
                 & (df["component"] == flag.get("category")) & (df["label_id"] == flag.get("entity_3"))]
        sub = sub.sort_values(["datea", "cmplid"]).head(3)
        excerpts = []
        for r in sub.itertuples():
            text = " ".join(str(r.text or "").split())
            try:
                text = redact_pii(text)
            except Exception:
                pass
            excerpts.append({
                "cmplid": str(r.cmplid),
                "date": str(r.datea),
                "make": str(r.make),
                "model": str(r.model),
                "year": int(r.year) if r.year is not None and not pd.isna(r.year) else None,
                "excerpt": text[:600],
            })
        recall = None
        if match is not None:
            recall = {
                "campno": str(match.get("campno")),
                "rcdate": str(match.get("rcdate")),
                "make": str(match.get("scope_entity_2")),
                "component": str(match.get("scope_category")),
                "defect_label_id": str(match.get("scope_entity_3")),
                "defect_label": _label_text(taxonomy, str(match.get("scope_category")), str(match.get("scope_entity_3"))),
                "desc_defect": " ".join(str(match.get("desc_defect") or "").split())[:400],
            }
        component = str(flag.get("category"))
        label_id = str(flag.get("entity_3"))
        flags.append({
            "flag_id": f"DF-{flag.get('iso_week')}-{flag.get('entity_2')}-{component}-{label_id}".replace(" ", "_"),
            "week": str(flag.get("iso_week")),
            "make": str(flag.get("entity_2")),
            "component": component,
            "defect_label_id": label_id,
            "defect_label": _label_text(taxonomy, component, label_id),
            "model_tag": "Muse Spark",
            "record_count": int(flag.get("record_count") or 0),
            "matched_recall": recall,
            "match": "recall" if recall else "no recall by 2024-12-31",
            "complaints": excerpts,
        })
    return {
        "generated_at": utc_now(),
        "model_tag": "Muse Spark",
        "note": "Five real defect-level test-window flags. Selection is fixed before the outcome is read: "
                "restrict to slice-weeks with at least 3 complaints, prefer specific defect labels over "
                "other/unclear, then take the largest record_count first while preferring a different test year "
                "and a different defect slice, for 3 confirmed and 2 unconfirmed flags. Excerpts are real "
                "complaint text, PII-redacted; the model saw PII-redacted text.",
        "selection": {
            "candidates": len(candidates),
            "specific_candidates": len(specific),
            "confirmed_candidates": sum(1 for _, m in candidates if m is not None),
            "unconfirmed_candidates": sum(1 for _, m in candidates if m is None),
            "selected_confirmed": sum(1 for _, m in selected if m is not None),
            "selected_unconfirmed": sum(1 for _, m in selected if m is None),
            "selected_specific": sum(1 for f, _ in selected if str(f.get("entity_3")) != OTHER_ID),
        },
        "flags": flags,
    }


def run_test(args) -> dict[str, Any]:
    frozen = _load_frozen(CONFIG_PATH)
    check_test_allowed(args.force_retest)
    reserve_test_run(args.force_retest)
    cfg = frozen["body"]["thresholds"]
    if frozen["body"].get("taxonomy_sha256") != _taxonomy().get("sha256"):
        raise Refused("frozen config taxonomy hash does not match the current taxonomy")
    complaints_path = Path(args.complaints)
    classifications_path = Path(args.classifications)
    recalls_path = Path(args.recalls)
    recall_labels_path = Path(args.recall_labels)
    frozen_data = frozen["body"].get("data") or {}
    for key, path in (("complaints", complaints_path), ("classifications", classifications_path),
                      ("recalls", recalls_path), ("recall_labels", recall_labels_path)):
        expected = frozen_data.get(f"{key}_sha256")
        if not expected:
            raise Refused(f"frozen config has no {key}_sha256; refusing a test whose inputs are not pinned")
        actual = file_sha(path)
        if actual != expected:
            raise Refused(f"{key} changed since tuning: frozen {expected}, now {actual}")
    df, comp_stats = load_complaints(complaints_path, classifications_path, "matched", TEST[0], TEST[1])
    # Test scoring includes pre-2021 complaint history as baseline, exactly as the
    # existing out-of-sample backtest does. The frame starts at 2015.
    df_all, _ = load_complaints(complaints_path, classifications_path, "matched", TRAIN[0], TEST[1])
    advisories, adv_stats = load_advisories(recalls_path, recall_labels_path, "matched", TEST[0], TEST[1],
                                            model_grain=True)
    if df_all.empty or not advisories:
        raise Refused(f"no matched test complaints/recalls (complaints={len(df_all)}, recalls={len(advisories)})")
    tax = _taxonomy()
    _validate_label_set(df_all, tax, component_col="component", label_col="label_id", what="test complaints")
    _validate_label_set(pd.DataFrame(advisories), tax, component_col="scope_category",
                        label_col="scope_entity_3", what="test recalls")
    records = complaint_records(df_all, model_grain=True)
    t0 = time.time()
    series = score_series(records, True, TEST[1])
    defect_ev = evaluate(series, advisories, cfg, model_grain=True, start=TEST[0], end=TEST[1],
                         validate=True, keep_details=True)
    defect_result = {
        "generated_at": utc_now(),
        "phase": "test",
        "config": cfg,
        "config_id": cfg_id(cfg),
        "config_sha256": frozen["sha256"],
        "test_window": list(TEST),
        "metrics": {k: defect_ev[k] for k in ("recent_campaign", "precision", "precision_episodes", "objective",
                                              "recalls_scored", "validation")},
        "complaints": comp_stats,
        "complaints_scored": int(len(df_all)),
        "advisories": adv_stats,
        "score_rows": len(series),
        "other_unclear_recalls": _recall_other_stats(recall_labels_path, recalls_path),
        "note": "single evaluation of the frozen config; no thresholds were changed after this run",
        "elapsed_s": round(time.time() - t0, 1),
    }
    # Component baseline on the same labelled complaint/recall subset.
    comp_records = complaint_records(df_all, model_grain=False)
    comp_series = score_series(comp_records, False, TEST[1])
    comp_cfg = _load_component_config()
    comp_ev = evaluate(comp_series, advisories, comp_cfg, model_grain=False, start=TEST[0], end=TEST[1],
                       validate=True)
    component_result = {
        "generated_at": utc_now(),
        "mode": "component",
        "labels_mode": "matched",
        "config": comp_cfg,
        "config_id": cfg_id(comp_cfg),
        "config_sha256": _load_frozen(OOS_DIR / "oos_config.json")["sha256"],
        "test_window": list(TEST),
        "metrics": {k: comp_ev[k] for k in ("recent_campaign", "precision", "precision_episodes", "objective",
                                             "recalls_scored", "validation")},
        "complaints": comp_stats,
        "complaints_scored": int(len(df_all)),
        "advisories": adv_stats,
        "score_rows": len(comp_series),
        "elapsed_s": None,
        "note": "component baseline on the same complaint/recall subset as the defect run",
    }

    # Defect-grain count and random baselines (table rows), plus component-grain
    # versions in the JSON appendix for readers who want the old grain.
    defect_defect_flags = defect_ev["flagged"]
    baseline = {
        "generated_at": utc_now(),
        "definitions": {
            "budget": "same number of slice-weeks as the detector under test, in the 2021-2024 test window",
            "count": "highest raw weekly complaint count; ties -> earlier week, then slice key",
            "random": f"uniform random slice-weeks without replacement, fixed seed {SEED}; "
                      f"{RANDOM_DRAWS} further draws are recorded for context",
        },
        "defect_grain": baseline_block(series, advisories, defect_defect_flags, model_grain=True,
                                       start=TEST[0], end=TEST[1]),
        "component_grain": baseline_block(comp_series, advisories,
                                          [dict(r, is_anomaly=True) for r in comp_series if gate(r, comp_cfg)],
                                          model_grain=False, start=TEST[0], end=TEST[1]),
    }

    examples = select_examples(defect_ev, df, advisories, _taxonomy())

    # Write only after every artifact has been built. A failure before this
    # point leaves the reserved marker in place and no claimed test result.
    TEST_RESULTS_PATH.write_text(json.dumps(defect_result, indent=2, default=str), encoding="utf-8")
    COMPONENT_RESULTS_PATH.write_text(json.dumps(component_result, indent=2, default=str), encoding="utf-8")
    BASELINE_RESULTS_PATH.write_text(json.dumps(baseline, indent=2, default=str), encoding="utf-8")
    EXAMPLES_PATH.write_text(json.dumps(examples, indent=2, default=str), encoding="utf-8")
    DASHBOARD_JSON.parent.mkdir(parents=True, exist_ok=True)
    DASHBOARD_JSON.write_text(json.dumps(examples, indent=2, default=str), encoding="utf-8")

    log_run(DEFECT_DIR, {"phase": "test", "forced": bool(args.force_retest), "config_sha256": frozen["sha256"],
                         "elapsed_s": defect_result["elapsed_s"]})
    return defect_result


# ── report ──────────────────────────────────────────────────────────────────


def _fmt(v: Any) -> str:
    return "n/a" if v is None else str(v)


def _metrics_row(name: str, metrics: dict[str, Any]) -> str:
    c = metrics.get("recent_campaign") or {}
    p = metrics.get("precision") or {}
    return (f"| {name} | {_fmt(c.get('recall_rate'))} | {_fmt(c.get('lead_weeks_median'))} | "
            f"{_fmt(p.get('precision_episodes'))} | {_fmt(p.get('flag_episodes'))} |")


def render_report() -> str:
    if not CONFIG_PATH.exists():
        sample = DEFECT_DIR / "defect_label_sample_300.csv"
        filled = 0
        if sample.exists():
            try:
                filled = int(pd.read_csv(sample)["label"].notna().sum())
            except Exception:
                filled = 0
        return "\n".join([
            "# Defect-level early warning: out-of-sample test",
            "",
            "**NOT RUN.** No frozen defect config exists yet, so there is no defect-level result to report.",
            "",
            f"- Taxonomy: `reports/defect/taxonomy.json` (frozen before test data was touched).",
            f"- Human sample: `reports/defect/defect_label_sample_300.csv`; {filled}/300 label cells are filled.",
            "- The test window is evaluated once after the classifier output and the frozen config exist.",
            "",
            "Do not treat a blank cell or a missing row as a zero.",
            "",
        ])
    frozen = _load_frozen(CONFIG_PATH)
    test = json.loads(TEST_RESULTS_PATH.read_text()) if TEST_RESULTS_PATH.exists() else None
    comp = json.loads(COMPONENT_RESULTS_PATH.read_text()) if COMPONENT_RESULTS_PATH.exists() else None
    base = json.loads(BASELINE_RESULTS_PATH.read_text()) if BASELINE_RESULTS_PATH.exists() else None
    examples = json.loads(EXAMPLES_PATH.read_text()) if EXAMPLES_PATH.exists() else None
    accuracy = json.loads(ACCURACY_PATH.read_text()) if ACCURACY_PATH.exists() else None
    tax = _taxonomy()
    L = [
        "# Defect-level early warning: out-of-sample test",
        "",
        "Generated by `scripts/defect_backtest.py --phase render` from the JSON files in `reports/defect/`.",
        "Every number below is copied from those files; nothing is estimated or rounded by hand.",
        "",
        f"- Frozen defect config: `{CONFIG_PATH.relative_to(REPO_ROOT)}`, sha256 `{frozen['sha256']}`",
        f"- Chosen thresholds: `{frozen['body']['config_id']}`",
        f"- Objective (fixed before tuning): {frozen['body']['objective']}",
        f"- Train window: {frozen['body']['train_window'][0]} .. {frozen['body']['train_window'][1]}",
        f"- Test window: {frozen['body']['test_window'][0]} .. {frozen['body']['test_window'][1]}",
        f"- Grain: `{frozen['body']['grain']}`",
        f"- Classifier: `{frozen['body']['classifier_model']}`, prompt version "
        f"`{frozen['body']['classifier_prompt_version']}`",
        f"- Taxonomy: `reports/defect/taxonomy.json`, sha256 `{tax.get('sha256')}` "
        f"({tax['body']['specific_label_count']} specific labels across {len(tax['body']['components'])} components, "
        "plus `other/unclear`)",
        "",
    ]
    if test is None:
        L += ["**Test phase not run.** No result is claimed.", ""]
        return "\n".join(L)
    L += [
        "The test window was evaluated once with the frozen config. The component-level baseline uses the frozen",
        "`abs3` config from `reports/oos/oos_config.json` on the same complaint and recall subset that has a defect",
        "label, so classifier failures cannot flatter the defect detector. The count and random baselines are at",
        "`make + component + defect` grain and are budget-matched to the defect detector's number of flagged",
        "slice-weeks. The table is the primary result.",
        "",
        "| Strategy | Campaign recall (52-wk) | Median lead (wk) | Episode precision | Episodes |",
        "| --- | --- | --- | --- | --- |",
    ]
    L.append(_metrics_row(f"Component-level detector (`{comp['config_id']}`)" if comp else "Component-level detector", (comp or {}).get("metrics") or {}))
    L.append(_metrics_row(f"Defect-level detector (`{test['config_id']}`)", test["metrics"]))
    if base:
        L.append(_metrics_row("Count baseline (defect grain)", base["defect_grain"]["count"]["metrics"]))
        L.append(_metrics_row(f"Random baseline (defect grain, seed {base['defect_grain']['random']['seed']})",
                              base["defect_grain"]["random"]["metrics"]))
    else:
        L.append(_metrics_row("Count baseline (defect grain)", {}))
        L.append(_metrics_row("Random baseline (defect grain)", {}))
    L += [""]
    if comp:
        L += [
            f"The component row scored {comp['metrics']['recent_campaign'].get('campaigns')} campaigns "
            f"({comp['metrics']['recalls_scored']} recall scope rows); the defect row scored "
            f"{test['metrics']['recent_campaign'].get('campaigns')} campaigns "
            f"({test['metrics']['recalls_scored']} scope rows). The component detector has fewer slices, so its",
            "Benjamini-Hochberg correction is less strict; that is part of the measured difference, not a bug.",
            "",
        ]
    if base:
        L += [
            f"Baseline budgets: {base['defect_grain']['budget_slice_weeks']} defect slice-weeks, selected from "
            f"{base['defect_grain']['random']['universe_positive_slice_weeks']} positive defect slice-weeks in the "
            f"test window. Random baseline definition: {base['definitions']['random']}.",
            "",
        ]
    # Honest comparison sentence.
    if comp and base:
        d = test["metrics"]["recent_campaign"].get("recall_rate")
        c = comp["metrics"]["recent_campaign"].get("recall_rate")
        dp = test["metrics"]["precision"].get("precision_episodes")
        cp = comp["metrics"]["precision"].get("precision_episodes")
        if d is not None and c is not None:
            better = (d > c) or (d == c and (dp or 0) > (cp or 0))
            L += [
                ("On this test window, the defect-level detector **beat** the component-level detector on the "
                 "52-week campaign recall/ episode-precision pair." if better else
                 "On this test window, the defect-level detector **did not beat** the component-level detector. "
                 "This null result is reported as measured; no threshold or taxonomy was changed after the test run."),
                "",
            ]
    # Recall labels in other/unclear.
    other = test.get("other_unclear_recalls") or {}
    if other.get("status") != "not run":
        L += ["## Recall descriptions in `other/unclear`", ""]
        for split in ("train", "test"):
            row = other.get(split) or {}
            L.append(f"- {split}, descriptions: {row.get('other_unclear', 'n/a')} of "
                     f"{row.get('labelled', 'n/a')} labelled descriptions ({row.get('rate', 'n/a')}).")
            L.append(f"  - {split}, scope rows: {row.get('scope_rows_other_unclear', 'n/a')} of "
                     f"{row.get('scope_rows_labelled', 'n/a')} labelled scope rows "
                     f"({row.get('scope_rows_unlabelled', 'n/a')} unlabelled).")
            L.append(f"  - {split}, campaigns: {row.get('campaigns_all_other_unclear', 'n/a')} of "
                     f"{row.get('campaigns_labelled', 'n/a')} labelled campaigns are all-`other/unclear`; "
                     f"{row.get('campaigns_any_other_unclear', 'n/a')} have at least one such row.")
        L += ["", "Recalls labelled `other/unclear` only match flags in the same component's `other/unclear` slice; "
              "they do not match a specific defect slice. This is the strict rule; it is why the count matters.", ""]
    # Classifier accuracy.
    L += ["## Classifier accuracy against the human 300-row sample", ""]
    if accuracy:
        sample = accuracy.get("sample") or {}
        L += [
            f"- Human labels: {accuracy.get('labelled', 'n/a')} of {accuracy.get('sample_size', 'n/a')} rows; "
            f"invalid labels: {accuracy.get('invalid_human_labels', 'n/a')}.",
            f"- Rows with both a valid human label and a model label (the accuracy denominator): "
            f"{accuracy.get('scored', 'n/a')}; model output missing: {accuracy.get('model_missing', 'n/a')}.",
            f"- Overall accuracy: {accuracy.get('accuracy', 'n/a')} "
            f"({accuracy.get('correct', 'n/a')}/{accuracy.get('scored', 'n/a')}).",
            f"- Accuracy with a missing model label counted as wrong: "
            f"{accuracy.get('accuracy_all_labelled', 'n/a')} "
            f"({accuracy.get('correct', 'n/a')}/{accuracy.get('labelled', 'n/a')}).",
            f"- Accuracy on rows whose human label is a specific defect (not `other/unclear`): "
            f"{accuracy.get('specific_accuracy', 'n/a')} "
            f"({accuracy.get('specific_correct', 'n/a')}/{accuracy.get('specific_n', 'n/a')}).",
            f"- Accuracy on human `other/unclear` rows: {accuracy.get('other_unclear_accuracy', 'n/a')} "
            f"({accuracy.get('other_unclear_correct', 'n/a')}/{accuracy.get('other_unclear_n', 'n/a')}).",
            f"- Sample: `reports/defect/defect_label_sample_300.csv`, seed {sample.get('seed', 'n/a')}, "
            f"CSV sha256 `{sample.get('csv_sha256', 'n/a')}` (blank export sha256 "
            f"`{sample.get('blank_csv_sha256', 'n/a')}`).",
            "",
            "Per-label precision / recall (human support > 0):",
            "",
        ]
        for row in accuracy.get("per_label", []):
            if not row.get("support"):
                continue
            L.append(f"- `{row['label_id']}`: precision {_fmt(row.get('precision'))}, "
                     f"recall {_fmt(row.get('recall'))}, support {row['support']}, "
                     f"predicted {row.get('predicted', 'n/a')}.")
        L += ["", "Confusion matrix (rows = human label, columns = Muse Spark; `other_unclear` included):", "", "```"]
        labels = accuracy.get("labels", [])
        L.append("human \\ model," + ",".join(labels))
        for human in labels:
            L.append(human + "," + ",".join(str(accuracy["confusion"].get(human, {}).get(m, 0)) for m in labels))
        L += ["```", ""]
    else:
        csv = DEFECT_DIR / "defect_label_sample_300.csv"
        filled = 0
        if csv.exists():
            try:
                filled = int(pd.read_csv(csv)["label"].notna().sum())
            except Exception:
                filled = 0
        L += [
            "**NOT RUN.** The human labels do not exist yet, so no accuracy, per-label precision/recall or",
            f"confusion matrix is reported. The 300-row CSV is `{csv.relative_to(REPO_ROOT)}`; "
            f"{filled}/300 label cells are filled. Do not treat the model labels as ground truth.",
            "",
        ]
    # Examples.
    L += ["## Five real example flags", ""]
    if examples:
        L += [examples.get("note", ""), ""]
        for f in examples.get("flags", []):
            L.append(f"- **{f['week']} · {f['make']} · {f['component']} · {f['defect_label']}** "
                     f"(`{f['defect_label_id']}`, {f['record_count']} complaints). Model tag: {f['model_tag']}.")
            ids = ", ".join(f"`{c['cmplid']}` ({c['date']})" for c in f.get("complaints", []))
            L.append(f"  - Complaint IDs/dates: {ids or 'none'}.")
            if f.get("matched_recall"):
                r = f["matched_recall"]
                L.append(f"  - Matched recall: `{r['campno']}` issued {r['rcdate']} — {r['desc_defect'][:240]}")
            else:
                L.append("  - Matched recall: **no recall by 2024-12-31** (false alarm under the test horizon).")
    else:
        L.append("**NOT RUN.** No example flags file exists.")
    L += [
        "",
        "## Limitations (read before quoting)",
        "",
        "- The taxonomy is built only from recalls issued on or before 2020-12-31 and frozen before any test run.",
        "  It is a train-window artifact, not a universal vehicle-defect ontology.",
        "- The classifier is zero-shot. Its labels are not ground truth; the 300-row human sample is the only",
        "  accuracy check, and it is reported above only when the human labels exist.",
        "- Recall descriptions are labelled by the same model and prompt. That recall labelling has no human",
        "  ground truth here; it is a measured input to matching, not a validated classifier.",
        "- Matching is strict on `make + component + defect`. A real recall whose description lands in",
        "  `other/unclear` cannot be matched by a specific defect slice. The count is reported above.",
        "- Right-censoring: flags in late 2023-2024 can only be confirmed by recalls issued by 2024-12-31. A",
        "  late flag with no recall is counted as a false alarm even if a recall is issued later.",
        "- The defect detector has many more slices than the component detector, so its weekly BH-FDR correction",
        "  is stricter. That is part of the measured capability, not a tuning choice.",
        "- Complaints are self-reported, unverified and subject to reporting bias. There is no exposure or",
        "  sales denominator, so this is raw complaint volume, not a rate.",
        "- Only five makes and model years 2015-2024 are included. The component baseline is run on the same",
        "  labelled subset as the defect detector, so classifier failures do not create a data advantage.",
        "- The test window was evaluated once with the frozen config. The count and random baselines are",
        "  reference strategies, not tuned detectors. The random baseline uses one fixed-seed draw for the table;",
        f"  {RANDOM_DRAWS} further draws are in `{BASELINE_RESULTS_PATH.relative_to(REPO_ROOT)}`.",
        "",
        f"Test run recorded in `{RUN_LOG.relative_to(REPO_ROOT)}` (config sha256 `{frozen['sha256']}`).",
        "",
    ]
    return "\n".join(L)


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    p.add_argument("--phase", choices=["tune", "test", "render", "component"], required=True)
    p.add_argument("--labels", choices=["matched", "none"], default="matched")
    p.add_argument("--complaints", default=str(REPO_ROOT / "data/research/complaints.parquet"))
    p.add_argument("--classifications", default=str(DEFECT_DIR / "classifications.parquet"))
    p.add_argument("--recalls", default=str(REPO_ROOT / "data/research/recalls.parquet"))
    p.add_argument("--recall-labels", default=str(DEFECT_DIR / "recall_labels.parquet"))
    p.add_argument("--model", default="muse-spark-1.3-contributor")
    p.add_argument("--prompt-version", default="defect-cls-v1")
    p.add_argument("--force-retune", action="store_true")
    p.add_argument("--force-retest", action="store_true")
    args = p.parse_args(argv)
    DEFECT_DIR.mkdir(parents=True, exist_ok=True)
    try:
        if args.phase == "tune":
            res = run_tune(args)
            print(json.dumps({"chosen": res["chosen"], "config_sha256": res["config_sha256"],
                              "elapsed_s": res["elapsed_s"]}, indent=2))
        elif args.phase == "test":
            res = run_test(args)
            print(json.dumps({"config_id": res["config_id"], "metrics": res["metrics"]}, indent=2, default=str))
        elif args.phase == "component":
            out = (DEFECT_DIR / "component_full_corpus_test.json") if args.labels == "none" else COMPONENT_RESULTS_PATH
            res = run_component(args, labels_mode=args.labels, out_path=out)
            print(json.dumps({"config_id": res["config_id"], "metrics": res["metrics"]}, indent=2, default=str))
        if args.phase in {"test", "render", "component"}:
            (OOS_DIR / "DEFECT_LEVEL.md").write_text(render_report(), encoding="utf-8")
            print(f"wrote {OOS_DIR / 'DEFECT_LEVEL.md'}")
    except Refused as e:
        log_run(DEFECT_DIR, {"phase": args.phase, "refused": str(e)})
        print(f"REFUSED: {e}", file=sys.stderr)
        return 3
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
