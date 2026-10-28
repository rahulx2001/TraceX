"""Prepare the portable parquet inputs the defect pipeline expects.

The defect classifier, taxonomy builder and human-sample exporter all read two
parquet files that are deliberately not committed:

    data/defect/complaints.parquet
    data/defect/recall_descriptions.parquet

This script builds them from the official NHTSA ODI flat files, either from
local ZIPs or by downloading the published URLs. It makes no model call and
spends no Meta credits.

    # Download both official flat files and write the parquet inputs.
    python -m scripts.defect_prepare_inputs --out-dir data/defect

    # Offline, from ZIPs already on disk.
    python -m scripts.defect_prepare_inputs --out-dir data/defect \
        --complaints-zip /path/FLAT_CMPL.zip \
        --recalls-zip /path/FLAT_RCL_POST_2010.zip

    # Small judge/demo sample (still deterministic).
    python -m scripts.defect_prepare_inputs --out-dir data/defect/hackathon \
        --complaints-limit 5000 --recalls-limit 5000

Outputs, all relative to ``--out-dir``:

    complaints.parquet             one row per (ODINO, component)
    recall_descriptions.parquet    one row per (campaign, component, description)
    defect_input_manifest.json     source URLs, SHA-256, row counts, settings

The classifier keys a complaint as ``ODINO|component``. NHTSA emits one line
per component and sometimes several vehicles for the same complaint, so this
script keeps one deterministic row per key (longest narrative, first wins on a
tie) and records how many lines were collapsed in the manifest.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scripts.ingest_nhtsa import (  # noqa: E402
    _download_flat_zip,
    _iter_flat_from_zip as _iter_complaints_from_zip,
    flat_line_to_mapping_row,
)
from scripts.ingest_recalls import (  # noqa: E402
    FLAT_RCL_FIELDS,
    NHTSA_RECALL_URL,
    _download as _download_recall_zip,
    _iter_flat_from_zip as _iter_recalls_from_zip,
)
from src.config import REPO_ROOT  # noqa: E402
from src.domains.mapping_ingest import _parse_ts  # noqa: E402
from src.domains.nhtsa_components import normalize_component  # noqa: E402

NHTSA_COMPLAINTS_URL = "https://static.nhtsa.gov/odi/ffdd/cmpl/FLAT_CMPL.zip"
DEFAULT_OUT_DIR = REPO_ROOT / "data/defect"
DEFAULT_START = "2015-01-01"
DEFAULT_END = "2024-12-31"


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _iso_date(value: str) -> str | None:
    parsed = _parse_ts(value)
    return parsed.strftime("%Y-%m-%d") if parsed is not None else None


def _iter_complaint_rows(zip_path: Path, *, start: str, end: str, limit: int) -> tuple[list[dict[str, Any]], dict[str, int]]:
    """Convert FLAT_CMPL lines to classifier rows, one per ODINO|component."""
    by_key: dict[str, dict[str, Any]] = {}
    tally = {
        "lines_read": 0,
        "skipped_unparseable": 0,
        "skipped_out_of_window": 0,
        "skipped_bad_year": 0,
        "collapsed": 0,
    }
    for line in _iter_complaints_from_zip(zip_path):
        tally["lines_read"] += 1
        row = flat_line_to_mapping_row(line)
        if row is None:
            tally["skipped_unparseable"] += 1
            continue
        datea = _iso_date(row["DATEA"])
        if datea is None or datea < start or datea > end:
            tally["skipped_out_of_window"] += 1
            continue
        try:
            year = int(str(row["MODEL_YR"]).strip())
        except ValueError:
            tally["skipped_bad_year"] += 1
            continue
        component = row["COMPONENT"]
        key = f"{row['ODINO']}|{component}"
        current = by_key.get(key)
        if current is not None:
            tally["collapsed"] += 1
            if len(row["CDESC"]) <= len(current["text"]):
                continue
        by_key[key] = {
            "datea": datea,
            "odino": row["ODINO"],
            "cmplid": row["CMPLID"],
            "make": row["MAKETXT"],
            "model": row["MODELTXT"],
            "year": year,
            "component": component,
            "text": row["CDESC"],
        }
        if limit and len(by_key) >= limit:
            break
    records = sorted(by_key.values(), key=lambda r: (r["component"], r["datea"], r["odino"]))
    return records, tally


def _iter_recall_rows(zip_path: Path, *, limit: int) -> tuple[list[dict[str, Any]], dict[str, int]]:
    """Convert FLAT_RCL lines to taxonomy/classifier rows, deduplicated."""
    by_key: dict[str, dict[str, Any]] = {}
    tally = {
        "lines_read": 0,
        "skipped_unparseable": 0,
        "skipped_bad_date": 0,
        "collapsed": 0,
    }
    for line in _iter_recalls_from_zip(zip_path):
        tally["lines_read"] += 1
        parts = line.rstrip("\n\r").split("\t")
        if len(parts) < 16:
            parts = line.rstrip("\n\r").split("|")
        if len(parts) < 16:
            tally["skipped_unparseable"] += 1
            continue
        raw = {name: (parts[i].strip() if i < len(parts) else "") for i, name in enumerate(FLAT_RCL_FIELDS)}
        campno = raw.get("CAMPNO") or ""
        rcdate = _iso_date(raw.get("RCDATE") or "")
        description = raw.get("DESC_DEFECT") or ""
        if not campno or rcdate is None or not description:
            tally["skipped_bad_date"] += 1
            continue
        component = normalize_component(raw.get("COMPNAME") or "")
        try:
            year = int(raw.get("YEARTXT") or "")
        except ValueError:
            year = None
        digest = hashlib.sha256(description.encode("utf-8", errors="replace")).hexdigest()[:12]
        key = f"{campno}|{component}|{digest}"
        if key in by_key:
            tally["collapsed"] += 1
            continue
        by_key[key] = {
            "campno": campno,
            "component": component,
            "compdesc": raw.get("COMPNAME") or "",
            "desc_defect": description,
            "rcdate": rcdate,
            "make": raw.get("MAKETXT") or "",
            "model": raw.get("MODELTXT") or "",
            "year": year,
        }
        if limit and len(by_key) >= limit:
            break
    records = sorted(by_key.values(), key=lambda r: (r["component"], r["rcdate"], r["campno"]))
    return records, tally


def _resolve_zip(*, supplied: str | None, url: str, cache: Path, downloader) -> tuple[Path, str]:
    if supplied:
        path = Path(supplied).expanduser()
        if not path.is_file():
            raise SystemExit(f"Missing input: {path}. Pass an existing ZIP or omit the flag to download {url}")
        return path, "local"
    cache.parent.mkdir(parents=True, exist_ok=True)
    if not cache.is_file():
        downloader(url, cache)
    return cache, "downloaded"


def prepare(
    *,
    out_dir: Path,
    complaints_zip: str | None = None,
    recalls_zip: str | None = None,
    start: str = DEFAULT_START,
    end: str = DEFAULT_END,
    complaints_limit: int = 0,
    recalls_limit: int = 0,
) -> dict[str, Any]:
    out_dir.mkdir(parents=True, exist_ok=True)
    cache_dir = Path(tempfile.mkdtemp(prefix="tracex-defect-inputs-"))
    cpath, corigin = _resolve_zip(
        supplied=complaints_zip,
        url=NHTSA_COMPLAINTS_URL,
        cache=cache_dir / "FLAT_CMPL.zip",
        downloader=_download_flat_zip,
    )
    rpath, rorigin = _resolve_zip(
        supplied=recalls_zip,
        url=NHTSA_RECALL_URL,
        cache=cache_dir / "FLAT_RCL_POST_2010.zip",
        downloader=_download_recall_zip,
    )

    complaints, ctally = _iter_complaint_rows(cpath, start=start, end=end, limit=complaints_limit)
    recalls, rtally = _iter_recall_rows(rpath, limit=recalls_limit)
    if not complaints:
        raise SystemExit(
            f"No complaint rows in {cpath} for {start}..{end}. "
            "Check --start/--end or use a FLAT_CMPL ZIP that covers that window."
        )
    if not recalls:
        raise SystemExit(f"No recall rows in {rpath}. Check the FLAT_RCL ZIP.")

    cdf = pd.DataFrame(complaints, columns=[
        "datea", "odino", "cmplid", "make", "model", "year", "component", "text",
    ])
    rdf = pd.DataFrame(recalls, columns=[
        "campno", "component", "compdesc", "desc_defect", "rcdate", "make", "model", "year",
    ])
    complaints_out = out_dir / "complaints.parquet"
    recalls_out = out_dir / "recall_descriptions.parquet"
    cdf.to_parquet(complaints_out, index=False)
    rdf.to_parquet(recalls_out, index=False)

    manifest = {
        "created_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "settings": {
            "start": start,
            "end": end,
            "complaints_limit": complaints_limit,
            "recalls_limit": recalls_limit,
        },
        "sources": {
            "complaints": {
                "url": NHTSA_COMPLAINTS_URL,
                "origin": corigin,
                "sha256": file_sha256(cpath),
            },
            "recalls": {
                "url": NHTSA_RECALL_URL,
                "origin": rorigin,
                "sha256": file_sha256(rpath),
            },
        },
        "complaints": {
            "path": str(complaints_out),
            "rows": int(len(cdf)),
            "sha256": file_sha256(complaints_out),
            "window": [start, end],
            "tally": ctally,
        },
        "recalls": {
            "path": str(recalls_out),
            "rows": int(len(rdf)),
            "sha256": file_sha256(recalls_out),
            "tally": rtally,
        },
        "note": "No model call was made. Complaint rows are unique on ODINO|component; longest narrative wins.",
    }
    (out_dir / "defect_input_manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return manifest


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Build the portable defect-pipeline parquet inputs from NHTSA flat files")
    p.add_argument("--out-dir", default=str(DEFAULT_OUT_DIR))
    p.add_argument("--complaints-zip", default=None, help="Local FLAT_CMPL ZIP (default: download)")
    p.add_argument("--recalls-zip", default=None, help="Local FLAT_RCL_POST_2010 ZIP (default: download)")
    p.add_argument("--start", default=DEFAULT_START)
    p.add_argument("--end", default=DEFAULT_END)
    p.add_argument("--complaints-limit", type=int, default=0, help="0 = all rows in the window")
    p.add_argument("--recalls-limit", type=int, default=0, help="0 = all rows")
    args = p.parse_args(argv)
    if args.complaints_limit < 0 or args.recalls_limit < 0:
        p.error("limits must be nonnegative")
    manifest = prepare(
        out_dir=Path(args.out_dir),
        complaints_zip=args.complaints_zip,
        recalls_zip=args.recalls_zip,
        start=args.start,
        end=args.end,
        complaints_limit=args.complaints_limit,
        recalls_limit=args.recalls_limit,
    )
    print(json.dumps(manifest, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
