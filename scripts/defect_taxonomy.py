"""Build and freeze the per-component defect taxonomy from TRAIN recalls only.

    python -m scripts.defect_taxonomy \
        --recalls /path/recalls.parquet \
        --recalls-zip /path/FLAT_RCL_POST_2010.zip \
        --out reports/defect/taxonomy.json

The taxonomy is derived from recall rows issued on or before 2020-12-31. Each
label is a (specific part, dominant failure mode) pair observed in those
recalls. Test-window recalls are never read here; the output is frozen with a
canonical SHA-256 before any test scoring. Every component also gets the
``other/unclear`` label.

This is deliberately deterministic: no model output is used to define the
taxonomy, so the taxonomy cannot inherit a model's mistakes. Muse Spark's job
is to map complaint narratives onto this frozen label set.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

TRAIN_END = "2020-12-31"
MIN_COMPONENT_RECALLS = 8
MIN_LEAF_SUPPORT = 2
MAX_LABELS_PER_COMPONENT = 6
OTHER_ID = "other_unclear"
OTHER_LABEL = "other/unclear"

# Ordered: first match wins. Keep the vocabulary broad enough that a specific
# part label does not become a dozen near-duplicate modes.
MODES: list[tuple[str, str]] = [
    ("fire", r"\bfire\b|\bburn|\bsmok|\bflame"),
    ("leak", r"\bleak|\bseep|\bdrip"),
    ("crack_or_fracture", r"\bcrack|\bfractur|\bruptur|\bsplit|\bbreak|\bbroken"),
    ("corrosion", r"\bcorros|\brust"),
    ("detachment", r"\bdetach|\bseparat|\bloose\b|\bfall off|\bcame off|\bdislodg"),
    ("stall", r"\bstall|\bshut down|\bshuts down|\bloss of power|\bengine stop"),
    ("electrical", r"\bshort circuit|\bshort\b|\bcircuit|\bwiring|\bwire\b|\belectrical|\bbattery|\balternator|\bfuse\b|\bconnector"),
    ("software", r"\bsoftware|\bcalibrat|\balgorithm|\blogic\b|\bprogram|\bcode\b"),
    ("sensor_or_signal", r"\bsensor|\bsignal|\bfalse\b|\binaccurate|\bincorrect (reading|display)|\bdisplay"),
    ("binding_or_drag", r"\bbind|\bdrag|\bstick|\bstuck|\bseiz"),
    ("overheat", r"\boverheat|\btoo hot|\btemperature|\bthermal"),
    ("wear", r"\bwear|\bworn|\bpremature"),
    ("noise_or_vibration", r"\bnoise|\brattle|\bvibrat|\bgrind"),
    ("compliance_or_label", r"\blabel|\bplacard|\bfmvss|\bfederal motor vehicle safety standard|\bfail to comply"),
    ("missing_or_wrong_part", r"\bmissing|\bincorrect|\bwrong|\bimproper|\bnot installed"),
    ("loss_of_control", r"\bloss of control|\bsteer|\bhandling"),
]
MODE_RE = [(name, re.compile(pat, re.I)) for name, pat in MODES]

# Leaves that are a category rather than a part. For these, keep the parent
# segment too, so "ELECTRICAL SYSTEM:SOFTWARE" does not become "SOFTWARE /
# SOFTWARE".
GENERIC_LEAVES = {
    "OTHER", "GENERAL", "EQUIPMENT", "STRUCTURE", "ENGINE", "SYSTEM", "SOFTWARE",
    "BODY", "VEHICLE", "UNKNOWN", "ASSEMBLY", "MODULE", "CONTROL MODULE",
}


def _norm_space(s: str) -> str:
    return " ".join(re.sub(r"[^A-Za-z0-9 /]+", " ", (s or "").upper()).split())


def leaf_part(compdesc: str, component: str) -> str:
    """Extract the most specific part name from NHTSA's COMPNAME hierarchy."""
    raw = " ".join(str(compdesc or "").upper().split())
    if not raw:
        return "GENERAL"
    parts = [
        " ".join(re.sub(r"[^A-Za-z0-9 /]+", " ", p).split())
        for p in raw.split(":")
        if p.strip()
    ]
    if not parts:
        return "GENERAL"
    leaf = parts[-1]
    if leaf in GENERIC_LEAVES and len(parts) >= 2:
        leaf = f"{parts[-2]} {leaf}"
    # Drop a leading make-up word that adds nothing.
    leaf = re.sub(r"^(OTHER|MISC|MISCELLANEOUS)\s+", "", leaf).strip()
    return leaf or component


def defect_mode(text: str) -> str:
    for name, rx in MODE_RE:
        if rx.search(text or ""):
            return name
    return "failure"


def _mode_display(mode: str) -> str:
    return mode.replace("_", " ")


def _slug(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", s.lower()).strip("_")[:80] or "label"


def canonical_hash(body: dict[str, Any]) -> str:
    return hashlib.sha256(json.dumps(body, sort_keys=True, separators=(",", ":"), default=str).encode()).hexdigest()


def _zip_sha(path: Path | None) -> str | None:
    if not path:
        return None
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def build(recalls: pd.DataFrame, *, train_end: str = TRAIN_END) -> dict[str, Any]:
    train = recalls[recalls["rcdate"] <= train_end].copy()
    # The advisory table's identity, matching scripts/ingest_recalls.py.
    train = train.drop_duplicates(["campno", "year", "make", "model", "component"], keep="first")
    train["leaf"] = [leaf_part(c, comp) for c, comp in zip(train["compdesc"], train["component"])]
    train["mode"] = [defect_mode(t) for t in train["desc_defect"]]

    components: dict[str, Any] = {}
    for component, grp in train.groupby("component", sort=True):
        n = len(grp)
        if n < MIN_COMPONENT_RECALLS:
            components[component] = {
                "train_recalls": n,
                "labels": [{"id": OTHER_ID, "label": OTHER_LABEL, "definition": "No specific label fits, or the narrative is too vague.", "support": n, "examples": []}],
                "note": f"fewer than {MIN_COMPONENT_RECALLS} train recalls; no specific labels",
            }
            continue
        by_leaf: dict[str, list[pd.Series]] = defaultdict(list)
        for _, row in grp.iterrows():
            by_leaf[row["leaf"]].append(row)
        leaf_stats = []
        for leaf, rows in by_leaf.items():
            mode_counts = Counter(r["mode"] for r in rows)
            mode, _ = mode_counts.most_common(1)[0]
            leaf_stats.append((len(rows), leaf, mode, rows))
        leaf_stats.sort(key=lambda x: (-x[0], x[1]))
        labels = []
        for support, leaf, mode, rows in leaf_stats:
            if support < MIN_LEAF_SUPPORT:
                continue
            if len(labels) >= MAX_LABELS_PER_COMPONENT:
                break
            # One exemplar per distinct description, longest first.
            examples = sorted({str(r["desc_defect"]).strip() for r in rows}, key=lambda s: (-len(s), s))[:2]
            examples = [e[:280] for e in examples]
            label_id = _slug(f"{leaf}_{mode}")
            if any(x["id"] == label_id for x in labels):
                continue
            labels.append({
                "id": label_id,
                "label": f"{leaf} / {_mode_display(mode)}",
                "leaf": leaf,
                "mode": mode,
                "definition": f"A defect in the {leaf.lower()} whose train-window recalls are dominated by {_mode_display(mode)}.",
                "support": support,
                "examples": examples,
            })
        if not labels:
            labels = [{"id": OTHER_ID, "label": OTHER_LABEL, "definition": "No specific label fits, or the narrative is too vague.", "support": n, "examples": []}]
        else:
            labels.append({"id": OTHER_ID, "label": OTHER_LABEL, "definition": "No specific label fits, or the narrative is too vague.", "support": n - sum(x["support"] for x in labels), "examples": []})
        components[component] = {"train_recalls": n, "labels": labels}

    body = {
        "train_window": ["2015-01-01", train_end],
        "train_recalls_used": int(len(train)),
        "components": components,
        "label_count": sum(len(v["labels"]) for v in components.values()),
        "specific_label_count": sum(len([x for x in v["labels"] if x["id"] != OTHER_ID]) for v in components.values()),
        "rule": "per-component leaf part from COMPNAME plus dominant defect mode; top leaves by train support; other/unclear always included",
        "min_component_recalls": MIN_COMPONENT_RECALLS,
        "min_leaf_support": MIN_LEAF_SUPPORT,
        "max_labels_per_component": MAX_LABELS_PER_COMPONENT,
        "built_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }
    return body


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Build per-component defect taxonomy from TRAIN recalls")
    p.add_argument("--recalls", required=True, help="parquet of recall scope rows (rcdate, compdesc, desc_defect, ...)")
    p.add_argument("--recalls-zip", default=None, help="optional source ZIP for the recorded hash")
    p.add_argument("--out", default="reports/defect/taxonomy.json")
    p.add_argument("--train-end", default=TRAIN_END)
    args = p.parse_args(argv)

    recalls = pd.read_parquet(args.recalls)
    body = build(recalls, train_end=args.train_end)
    body["source"] = {
        "recalls_parquet": str(Path(args.recalls).resolve()),
        "recalls_zip": str(Path(args.recalls_zip).resolve()) if args.recalls_zip else None,
        "recalls_zip_sha256": _zip_sha(Path(args.recalls_zip)) if args.recalls_zip else None,
        "train_end": args.train_end,
    }
    frozen = {"sha256": canonical_hash(body), "body": body}
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(frozen, indent=2, default=str), encoding="utf-8")
    print(json.dumps({
        "out": str(out),
        "sha256": frozen["sha256"],
        "train_recalls": body["train_recalls_used"],
        "components": len(body["components"]),
        "labels": body["label_count"],
        "specific_labels": body["specific_label_count"],
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
