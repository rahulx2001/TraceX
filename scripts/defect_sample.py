"""Export a fixed, component-stratified sample of test-window complaints for
human labelling. No model output is used.

    python -m scripts.defect_sample \
        --complaints /path/complaints.parquet \
        --taxonomy reports/defect/taxonomy.json \
        --out reports/defect/defect_label_sample_300.csv \
        --manifest reports/defect/sample_manifest.json

Sampling frame: complaints received 2021-01-01 .. 2024-12-31 (the frozen test
window), five makes, MY2015-2024. The seed is fixed. Each row carries the
labels allowed for its component; the ``label`` and ``notes`` columns are
blank for the human.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

SEED = 20261026
N = 300
TEST_START = "2021-01-01"
TEST_END = "2024-12-31"
MIN_PER_COMPONENT = 3


def allocate(counts: dict[str, int], total: int, minimum: int) -> dict[str, int]:
    """Proportional allocation with a per-component floor, exact total."""
    comps = sorted(counts)
    n_total = sum(counts.values())
    if n_total <= 0:
        return {}
    raw = {c: total * counts[c] / n_total for c in comps}
    alloc = {c: min(counts[c], max(minimum, int(raw[c]))) for c in comps}
    # If the floor overshoots, take back from the largest allocations first.
    while sum(alloc.values()) > total:
        c = max((c for c in comps if alloc[c] > min(minimum, counts[c])), key=lambda x: alloc[x], default=None)
        if c is None:
            break
        alloc[c] -= 1
    # Distribute the remainder by largest fractional part, respecting counts.
    while sum(alloc.values()) < total:
        candidates = [c for c in comps if alloc[c] < counts[c]]
        if not candidates:
            break
        c = max(candidates, key=lambda x: (raw[x] - int(raw[x]), counts[x], x))
        alloc[c] += 1
    return alloc


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Export stratified 300-complaint hand-labelling sample")
    p.add_argument("--complaints", required=True)
    p.add_argument("--taxonomy", default="reports/defect/taxonomy.json")
    p.add_argument("--out", default="reports/defect/defect_label_sample_300.csv")
    p.add_argument("--manifest", default="reports/defect/sample_manifest.json")
    p.add_argument("--n", type=int, default=N)
    p.add_argument("--seed", type=int, default=SEED)
    args = p.parse_args(argv)

    taxonomy = json.loads(Path(args.taxonomy).read_text())
    tbody = taxonomy["body"]
    comps = tbody["components"]

    df = pd.read_parquet(args.complaints)
    frame = df[(df["datea"] >= TEST_START) & (df["datea"] <= TEST_END)].copy()
    counts = frame["component"].value_counts().to_dict()
    alloc = allocate(counts, args.n, MIN_PER_COMPONENT)
    rng = np.random.default_rng(args.seed)

    rows: list[pd.DataFrame] = []
    for component in sorted(alloc):
        n = alloc[component]
        if n <= 0:
            continue
        part = frame[frame["component"] == component]
        take = part.sample(n=min(n, len(part)), random_state=int(rng.integers(0, 2**31 - 1)))
        rows.append(take)
    sample = pd.concat(rows, ignore_index=True) if rows else frame.iloc[0:0].copy()
    sample = sample.sort_values(["component", "datea", "cmplid"]).reset_index(drop=True)

    label_map = {
        c: [(x["id"], x["label"]) for x in comps[c]["labels"]]
        for c in comps
    }
    # Components with too few train recalls have no specific taxonomy; they
    # can still be labelled, but only as other/unclear.
    fallback = [("other_unclear", "other/unclear")]
    out = pd.DataFrame({
        "sample_id": [f"S{i:03d}" for i in range(1, len(sample) + 1)],
        "cmplid": sample["cmplid"],
        "odino": sample["odino"],
        "datea": sample["datea"],
        "make": sample["make"],
        "model": sample["model"],
        "year": sample["year"],
        "component": sample["component"],
        "allowed_label_ids": [";".join(x[0] for x in label_map.get(c, fallback)) for c in sample["component"]],
        "allowed_label_text": ["; ".join(f"{i}={t}" for i, t in label_map.get(c, fallback)) for c in sample["component"]],
        "narrative": sample["text"],
        "label": "",
        "notes": "",
    })
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(out_path, index=False)

    manifest = {
        "created_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "seed": args.seed,
        "requested": args.n,
        "written": int(len(out)),
        "frame": {
            "window": [TEST_START, TEST_END],
            "makes": sorted(frame["make"].unique().tolist()),
            "year_min": int(frame["year"].min()),
            "year_max": int(frame["year"].max()),
            "components": int(frame["component"].nunique()),
            "complaints": int(len(frame)),
        },
        "allocation": alloc,
        "taxonomy_sha256": taxonomy["sha256"],
        "csv_sha256": hashlib.sha256(out_path.read_bytes()).hexdigest(),
        "note": "Human labels are blank. Model output was not used to choose or label this sample.",
    }
    Path(args.manifest).write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(json.dumps(manifest, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
