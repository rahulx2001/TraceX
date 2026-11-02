"""Explicit evaluation units for new experiments; historical scorers stay frozen."""
from __future__ import annotations

from collections import Counter
import math
import numpy as np


def rate(numerator: int, denominator: int, unit: str) -> dict:
    if not 0 <= numerator <= denominator:
        raise ValueError("Invalid numerator/denominator")
    if not denominator:
        return dict(numerator=numerator, denominator=0, value=None, ci95=None, unit=unit)
    p, z = numerator / denominator, 1.959963984540054
    scale = 1 + z*z/denominator
    center = (p + z*z/(2*denominator))/scale
    radius = z*math.sqrt(p*(1-p)/denominator + z*z/(4*denominator**2))/scale
    return dict(numerator=numerator, denominator=denominator, value=p,
                ci95=[0.0 if numerator == 0 else max(0., center-radius),
                      1.0 if numerator == denominator else min(1., center+radius)],
                unit=unit, interval_method="descriptive Wilson; correlated units limit inference")


def bootstrap_mean(values, *, seed=17, draws=2000):
    a = np.asarray(values, dtype=float)
    if len(a) < 2:
        return None
    rng = np.random.default_rng(seed)
    boot = [float(rng.choice(a, len(a), replace=True).mean()) for _ in range(draws)]
    return np.quantile(boot, [.025, .975]).tolist()


def classification(gold, predicted, *, abstain="other_unclear"):
    gold, predicted = list(gold), list(predicted)
    if len(gold) != len(predicted) or any(x is None or x == "" for x in gold):
        raise ValueError("Gold labels must exist for every scored row")
    classes = sorted(set(gold) | {p for p in predicted if p is not None})
    accepted = [p is not None and p != abstain for p in predicted]
    correct = [g == p for g, p in zip(gold, predicted)]
    per_label = {}
    for label in classes:
        tp = sum(g == p == label for g, p in zip(gold, predicted))
        support, called = gold.count(label), predicted.count(label)
        per_label[label] = dict(precision=rate(tp, called, "predictions"), recall=rate(tp, support, "gold examples"),
                                f1=2*tp/(support+called) if support+called else None, support=support)
    specific = [g != abstain for g in gold]
    confusion = Counter((g, p if p is not None else "__abstain__") for g,p in zip(gold,predicted))
    return dict(accuracy=rate(sum(correct), len(gold), "all gold examples; missing predictions count wrong"),
                specific_accuracy=rate(sum(c and s for c,s in zip(correct,specific)), sum(specific), "specific-label gold examples"),
                accepted_precision=rate(sum(c and a for c,a in zip(correct,accepted)), sum(accepted), "accepted predictions"),
                coverage=rate(sum(accepted), len(gold), "all gold examples"), per_label=per_label,
                confusion=[dict(gold=g,predicted=p,n=n) for (g,p),n in sorted(confusion.items())],
                macro_f1=float(np.mean([v["f1"] for v in per_label.values() if v["support"]])) if gold else None,
                macro_f1_label_count=sum(v["support"]>0 for v in per_label.values()))


def calibration(y, probabilities, *, reference_probability: float, bins=10, seed=17):
    y, p = np.asarray(y, dtype=float), np.asarray(probabilities, dtype=float)
    if y.shape != p.shape or y.ndim != 1 or not np.isin(y, [0,1]).all():
        raise ValueError("Binary outcomes and probabilities must align")
    if not np.isfinite(p).all() or not ((p >= 0) & (p <= 1)).all() or not 0 <= reference_probability <= 1 or bins < 1:
        raise ValueError("Invalid probabilities or bins")
    if not len(y):
        return dict(n=0, positives=0, ece=None, brier=None, reliability=[], reason="no mature outcomes")
    bucket = np.minimum((p*bins).astype(int), bins-1)
    reliability, ece = [], 0.
    for i in range(bins):
        mask = bucket == i
        if not mask.any():
            reliability.append(dict(lower=i/bins, upper=(i+1)/bins, n=0, mean_probability=None, observed=None))
            continue
        observed = rate(int(y[mask].sum()), int(mask.sum()), "mature labelled outcomes")
        mean = float(p[mask].mean())
        ece += mask.sum()/len(y)*abs(mean-observed["value"])
        reliability.append(dict(lower=i/bins,upper=(i+1)/bins,n=int(mask.sum()),mean_probability=mean,observed=observed))
    errors = (p-y)**2
    reference_errors = (reference_probability-y)**2
    rng = np.random.default_rng(seed)
    eces = []
    if len(y) >= 2:
        for _ in range(1000):
            idx = rng.integers(0,len(y),len(y)); e = 0.
            for i in range(bins):
                mask = bucket[idx] == i
                if mask.any(): e += mask.mean()*abs(p[idx][mask].mean()-y[idx][mask].mean())
            eces.append(e)
    return dict(n=len(y), positives=int(y.sum()), ece=float(ece),
                ece_ci95=np.quantile(eces,[.025,.975]).tolist() if eces else None,
                brier=float(errors.mean()), brier_numerator=float(errors.sum()), brier_denominator=len(y),
                brier_ci95=bootstrap_mean(errors,seed=seed), reference_probability=reference_probability,
                reference_brier=float(reference_errors.mean()),
                brier_difference=float((errors-reference_errors).mean()),
                brier_difference_ci95=bootstrap_mean(errors-reference_errors,seed=seed),
                reliability=reliability, interval_note="row bootstrap; temporal/episode dependence requires caution")


def precision_coverage(gold, classes, probabilities, thresholds):
    p = np.asarray(probabilities)
    if p.ndim != 2 or p.shape != (len(gold),len(classes)) or not np.isfinite(p).all():
        raise ValueError("Invalid classification probabilities")
    if not ((p >= 0)&(p <= 1)).all() or not np.allclose(p.sum(axis=1),1):
        raise ValueError("Rows must be probability distributions")
    best = p.argmax(axis=1)
    return [dict(threshold=float(t), **classification(list(gold),[classes[b] if row[b]>=t else None for b,row in zip(best,p)])) for t in thresholds]


def retrieval(queries, *, k=5, seed=17):
    """Rank mixed candidates per query. Never partition a candidate pool by label."""
    if k < 1:
        raise ValueError("k must be positive")
    ids, rows = set(), []
    for q in queries:
        if q["query_id"] in ids:
            raise ValueError("Duplicate query")
        ids.add(q["query_id"])
        c = q["candidates"]
        if len(c) < k or len({r["candidate_id"] for r in c}) != len(c):
            raise ValueError("Every query needs k distinct candidates")
        if any(r["relevant"] not in (0,1) or not math.isfinite(r["score"]) for r in c):
            raise ValueError("Invalid relevance or score")
        positives = sum(r["relevant"] for r in c)
        if positives == 0 or positives == len(c):
            raise ValueError("Every query needs positive AND negative controls")
        ranked = sorted(c,key=lambda r:(-r["score"],r["candidate_id"]))
        hits = sum(r["relevant"] for r in ranked[:k])
        rows.append(dict(query_id=q["query_id"],eval_class=q["eval_class"],precision=rate(hits,k,"retrieved candidates"),
                         recall=rate(hits,positives,"relevant candidates in fixed pool"),
                         attainable_precision=min(k,positives)/k))
    by_class = {}
    for label in sorted({r["eval_class"] for r in rows}):
        subset = [r for r in rows if r["eval_class"]==label]
        vals = [r["precision"]["value"] for r in subset]
        by_class[label] = dict(queries=len(subset),mean_precision_at_k=float(np.mean(vals)),
                               precision_numerator=sum(r["precision"]["numerator"] for r in subset),
                               precision_denominator=k*len(subset),ci95=bootstrap_mean(vals,seed=seed))
    return dict(k=k,queries=rows,per_class=by_class,label_note="Label provenance must accompany this score; synthetic fixtures are never acceptance eligible")


def paired_campaign_difference(baseline_hits, candidate_hits, all_campaigns, *, seed=17):
    campaigns = sorted(set(all_campaigns))
    if not set(baseline_hits).issubset(campaigns) or not set(candidate_hits).issubset(campaigns):
        raise ValueError("Hits outside the declared denominator")
    diffs = [int(c in candidate_hits)-int(c in baseline_hits) for c in campaigns]
    return dict(numerator=sum(diffs),denominator=len(campaigns),value=float(np.mean(diffs)) if diffs else None,
                ci95=bootstrap_mean(diffs,seed=seed),unit="paired campaigns; shared physical defects may remain correlated")
