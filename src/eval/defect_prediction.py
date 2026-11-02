"""Causal sparse-count alerts and bounded-horizon retrospective evaluation.

Defect labels are model outputs, not ground truth. The predictive tail is a
ranking heuristic; it is not a calibrated probability of a physical defect.
"""
from __future__ import annotations

from datetime import timedelta
import math
import numpy as np
import pandas as pd

KEY = ["make", "component", "label_id"]
COOLDOWN_DAYS = 91
HORIZON_DAYS = 364


def predictive_tail(count: int, shape: float, probability: float) -> float:
    """P(N >= count) for the Gamma-Poisson predictive distribution.

Log PMFs avoid underflow propagating through a recurrence. Tiny tails are
rounded to zero; thresholds are >=.05, so this cannot affect alert decisions.
"""
    cdf = math.fsum(math.exp(math.lgamma(k + shape) - math.lgamma(shape) - math.lgamma(k + 1)
                             + shape * math.log(probability) + k * math.log1p(-probability))
                    for k in range(count))
    return min(1.0, max(0.0, 1.0 - cdf))


def candidates(complaints: pd.DataFrame, *, window: int, end: str) -> list[dict]:
    """Score completed weeks using a disjoint, prior-only 26-week baseline.

Only weeks with a new specific-defect complaint can alert. Start each slice
when it is first observed; never use a future observation to extend history.
"""
    rows = []
    df = complaints[complaints.label_id.ne("other_unclear")].copy()
    df["day"] = pd.to_datetime(df.datea)
    df = df[df.day <= pd.Timestamp(end)]
    df["week"] = df.day - pd.to_timedelta(df.day.dt.dayofweek, unit="D")
    for key, part in df.groupby(KEY, sort=True):
        counts = part.groupby("week").size()
        stop = pd.Timestamp(end) - pd.Timedelta(days=pd.Timestamp(end).dayofweek)
        weeks = pd.date_range(counts.index.min(), stop, freq="W-MON")
        values = counts.reindex(weeks, fill_value=0).to_numpy()
        prefix = np.r_[0, np.cumsum(values)]
        for i, week in enumerate(weeks):
            available = week + pd.Timedelta(days=7)
            if not values[i] or i + 1 < window + 4 or available > pd.Timestamp(end):
                continue
            boundary = i + 1 - window
            lo = max(0, boundary - 26)
            prior_n = boundary - lo
            prior_sum = int(prefix[boundary] - prefix[lo])
            recent = int(prefix[i + 1] - prefix[boundary])
            # Jeffreys Gamma(1/2, 0) posterior, with >=4 observed prior weeks.
            tail = predictive_tail(recent, prior_sum + 0.5, prior_n / (prior_n + window))
            rows.append(dict(zip(KEY, key)) | {
                "available_at": available.date().isoformat(), "week": week.date().isoformat(),
                "record_count": recent, "new_complaints": int(values[i]), "window_weeks": window,
                "prior_count": prior_sum, "prior_weeks": prior_n,
                "expected_count": (prior_sum + 0.5) * window / prior_n,
                "tail_score": tail,
            })
    return sorted(rows, key=lambda r: (r["available_at"], tuple(r[k] for k in KEY)))


def key(row):
    return tuple(row[k] for k in KEY)


def alert_episodes(rows: list[dict], *, min_count: int, max_tail: float, start: str, end: str) -> list[dict]:
    selected, last = [], {}
    for row in sorted(rows, key=lambda r: (r["available_at"], key(r))):
        day = pd.Timestamp(row["available_at"])
        if not start <= row["available_at"] <= end or row["record_count"] < min_count or row["tail_score"] > max_tail:
            continue
        if key(row) in last and (day - last[key(row)]).days < COOLDOWN_DAYS:
            continue
        selected.append(row)
        last[key(row)] = day
    return selected


def reference_alerts(rows: list[dict], *, budget: int, start: str, end: str, seed: int | None) -> list[dict]:
    """Retrospective references with identical alert count and cooldown.

Ranking uses complaint counts or a fixed random seed, never recall outcomes.
These whole-window references are not online deployable policies.
"""
    pool = [r for r in rows if start <= r["available_at"] <= end]
    if seed is None:
        pool.sort(key=lambda r: (-r["record_count"], r["available_at"], key(r)))
    else:
        np.random.default_rng(seed).shuffle(pool)
    selected = []
    for row in pool:
        if len(selected) == budget:
            break
        if all(key(row) != key(other) or abs((pd.Timestamp(row["available_at"]) - pd.Timestamp(other["available_at"])).days) >= COOLDOWN_DAYS for other in selected):
            selected.append(row)
    if len(selected) != budget:
        raise ValueError(f"Reference could supply only {len(selected)} of {budget} equal-budget alerts")
    return sorted(selected, key=lambda r: (r["available_at"], key(r)))


def evaluate(alerts: list[dict], recalls: pd.DataFrame, *, start: str, end: str) -> dict:
    """One credit per campaign; unknown defect labels never match each other.

Primary precision includes only alerts with a full 52-week follow-up, even
when a censored alert already has a known match. This avoids outcome-dependent
denominators. All campaigns remain in recall, including unknown labels.
"""
    r = recalls[recalls.rcdate.between(start, end)].copy()
    campaigns = sorted(set(r.campno))
    hits = {}
    details = []
    for a in alerts:
        issued = pd.Timestamp(a["available_at"])
        sub = r[(r.make == a["make"]) & (r.component == a["component"])
                & (r.label_id == a["label_id"]) & r.label_id.ne("other_unclear")]
        leads = (pd.to_datetime(sub.rcdate) - issued).dt.days
        matches = sub[leads.between(7, HORIZON_DAYS)]
        for campaign, group in matches.groupby("campno"):
            lead = (pd.Timestamp(group.rcdate.min()) - issued).days
            hits[campaign] = max(hits.get(campaign, 0), lead)
        mature = issued + timedelta(days=HORIZON_DAYS) <= pd.Timestamp(end)
        details.append(a | {"matched_campaigns": sorted(set(matches.campno)), "full_followup": mature})
    mature = [x for x in details if x["full_followup"]]
    confirmed = sum(bool(x["matched_campaigns"]) for x in mature)
    recall = len(hits) / len(campaigns) if campaigns else 0.0
    precision = confirmed / len(mature) if mature else None
    f1 = 2 * recall * precision / (recall + precision) if precision is not None and recall + precision else 0.0
    return {
        "campaigns": len(campaigns), "hits": len(hits), "misses": len(campaigns) - len(hits),
        "campaign_recall": recall, "median_lead_weeks": float(np.median(list(hits.values())) / 7) if hits else None,
        "alerts": len(alerts), "mature_alerts": len(mature), "confirmed_mature_alerts": confirmed,
        "censored_alerts": len(details) - len(mature), "episode_precision": precision, "objective": f1,
        "campaign_hits": hits, "alert_details": details,
    }


def join_labels(complaints, recalls, classification, recall_labels, *, model, prompt, taxonomy):
    """Require complete, version-consistent labels; never silently drop failures."""
    for name, df in (("complaints", classification), ("recalls", recall_labels)):
        for col, expected in (("model", model), ("prompt_version", prompt), ("taxonomy_sha256", taxonomy)):
            if not df[col].eq(expected).all():
                raise ValueError(f"{name}: mixed {col} provenance")
        if df.record_id.duplicated().any():
            raise ValueError(f"{name}: duplicate label identities")
    c = complaints.copy()
    c["record_id"] = c.odino.astype(str) + "|" + c.component
    c = c.merge(classification[["record_id", "label_id", "status"]], on="record_id", how="left", validate="one_to_one")
    r = recalls.merge(recall_labels[["campno", "component", "desc_defect", "label_id", "status"]],
                      on=["campno", "component", "desc_defect"], how="left", validate="many_to_one")
    for name, df in (("complaints", c), ("recalls", r)):
        if not df.status.eq("ok").all() or df.label_id.isna().any():
            raise ValueError(f"{name}: incomplete classifier coverage ({int(df.status.eq('ok').sum())}/{len(df)})")
    return c, r
