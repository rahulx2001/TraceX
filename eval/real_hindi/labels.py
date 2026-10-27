"""Export and validate the human labelling sheet for the REAL complaint set.

    python -m eval.real_hindi.labels export
    python -m eval.real_hindi.labels check

The export writes ``data/real_hindi/labels.csv`` with the story text and blank
``language``, ``is_safety_critical``, ``component`` and ``notes`` cells. It does
not infer or pre-fill any label. It refuses to overwrite a sheet that already
contains labels unless ``--force`` is passed, and it makes a backup first.

The committed ``labels_template.csv`` is the schema only: a header and no rows.
The working CSV lives under the gitignored data directory because it contains
the raw stories.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from scripts.real_hindi_collect import DataError, load_records, utc_now

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
TEMPLATE_PATH = Path(__file__).resolve().parent / "labels_template.csv"
CATEGORIES_PATH = REPO_ROOT / "domains" / "automotive_nhtsa" / "gazetteers" / "categories.csv"
DEFAULT_DATA_DIR = REPO_ROOT / "data" / "real_hindi"

TEMPLATE_COLUMNS = ["id", "language", "is_safety_critical", "component", "notes"]
EXPORT_COLUMNS = [
    "id", "created_at", "reported_language", "input_type", "audio_file", "has_transcript",
    "narrative", "language", "is_safety_critical", "component", "notes",
]
LANGUAGES = {"hindi", "hinglish", "english", "mixed"}
LANGUAGE_ALIASES = {
    "hindi": "hindi", "hi": "hindi", "हिंदी": "hindi",
    "hinglish": "hinglish", "hing": "hinglish",
    "english": "english", "en": "english",
    "mixed": "mixed", "mix": "mixed",
}
SAFETY_ALIASES = {
    "yes": True, "y": True, "true": True, "1": True,
    "no": False, "n": False, "false": False, "0": False,
}


def load_categories(path: Path = CATEGORIES_PATH) -> dict[str, str]:
    if not path.exists():
        raise DataError(f"category gazetteer not found: {path}")
    out: dict[str, str] = {}
    with path.open(encoding="utf-8", newline="") as fh:
        for row in csv.DictReader(fh):
            value = " ".join(str(row.get("value") or "").strip().split())
            if value:
                out[value.upper()] = value.upper()
    if not out:
        raise DataError(f"category gazetteer is empty: {path}")
    return out


def canonical_language(value: Any) -> str | None:
    return LANGUAGE_ALIASES.get(" ".join(str(value or "").strip().lower().split()))


def canonical_safety(value: Any) -> bool | None:
    key = " ".join(str(value or "").strip().lower().split())
    return SAFETY_ALIASES.get(key)


def canonical_component(value: Any, categories: dict[str, str]) -> str | None:
    key = " ".join(str(value or "").strip().upper().split())
    return categories.get(key)


def _csv_safe(value: Any) -> str:
    """Prevent a story/notes cell from executing as a spreadsheet formula."""
    text = str(value if value is not None else "")
    return "'" + text if text[:1] in ("=", "+", "-", "@") else text


def _cell_nonblank(row: dict[str, Any], columns: tuple[str, ...]) -> bool:
    return any(str(row.get(c) or "").strip() for c in columns)


def _read_csv(path: Path) -> tuple[list[dict[str, str]], list[str]]:
    with path.open(encoding="utf-8-sig", newline="") as fh:
        reader = csv.DictReader(fh)
        fields = list(reader.fieldnames or [])
        rows = [{k: (v if v is not None else "") for k, v in row.items()} for row in reader]
    return rows, fields


def export_labels(data_dir: Path, out_path: Path | None = None, *, force: bool = False) -> dict[str, Any]:
    data_dir = data_dir.expanduser().resolve()
    out_path = (out_path or (data_dir / "labels.csv")).expanduser().resolve()
    records = load_records(data_dir)
    if not records:
        raise DataError(f"no records in {data_dir / 'records'}; nothing to export")
    if out_path.exists():
        try:
            existing, _ = _read_csv(out_path)
        except OSError as e:
            raise DataError(f"cannot read existing {out_path}: {type(e).__name__}") from e
        if any(_cell_nonblank(row, ("language", "is_safety_critical", "component", "notes"))
               for row in existing) and not force:
            raise DataError(
                f"{out_path} already contains labels; refusing to overwrite. "
                "Back it up and rerun with --force if you really mean to replace it."
            )
        if force:
            backup = out_path.with_name(f"{out_path.stem}.backup.{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}.csv")
            shutil.copy2(out_path, backup)
            try:
                backup.chmod(0o600)
            except OSError:
                pass
            print(f"Backed up the existing sheet to {backup}")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    tmp = out_path.with_name(out_path.name + ".tmp")
    with tmp.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=EXPORT_COLUMNS, lineterminator="\n")
        writer.writeheader()
        for r in records:
            narrative = str(r.get("narrative") or "")
            writer.writerow({
                "id": r.get("id") or "",
                "created_at": r.get("created_at") or "",
                "reported_language": r.get("reported_language") or "",
                "input_type": r.get("input_type") or "",
                "audio_file": r.get("audio_file") or "",
                "has_transcript": "yes" if narrative.strip() else "no",
                "narrative": _csv_safe(narrative),
                "language": "",
                "is_safety_critical": "",
                "component": "",
                "notes": "",
            })
    try:
        tmp.chmod(0o600)
    except OSError:
        pass
    tmp.replace(out_path)
    missing = sum(1 for r in records if not str(r.get("narrative") or "").strip())
    return {
        "out": str(out_path),
        "records": len(records),
        "audio_without_transcript": missing,
        "columns": EXPORT_COLUMNS,
        "labels_prefilled": False,
        "sha256": hashlib.sha256(out_path.read_bytes()).hexdigest(),
    }


def load_labels(path: Path, *, categories: dict[str, str] | None = None) -> dict[str, Any]:
    """Read and validate a filled sheet. Returns canonical rows plus problems.

    A row is usable only when language, is_safety_critical and component are
    all valid. Blank or invalid rows are reported, never guessed.
    """
    categories = categories or load_categories()
    rows, fields = _read_csv(path)
    missing_cols = [c for c in TEMPLATE_COLUMNS if c not in fields]
    if missing_cols:
        raise DataError(f"{path} is missing columns: {missing_cols}")
    out: dict[str, dict[str, Any]] = {}
    problems: list[dict[str, Any]] = []
    for line_no, row in enumerate(rows, start=2):
        rid = str(row.get("id") or "").strip()
        if not rid:
            problems.append({"line": line_no, "id": "", "reason": "missing id"})
            continue
        if rid in out:
            problems.append({"line": line_no, "id": rid, "reason": "duplicate id"})
            continue
        lang_raw = row.get("language")
        safety_raw = row.get("is_safety_critical")
        comp_raw = row.get("component")
        lang = canonical_language(lang_raw)
        safety = canonical_safety(safety_raw)
        component = canonical_component(comp_raw, categories)
        reasons = []
        if lang is None:
            reasons.append("missing language" if not str(lang_raw or "").strip() else "invalid language")
        if safety is None:
            reasons.append("missing is_safety_critical" if not str(safety_raw or "").strip() else "invalid is_safety_critical")
        if component is None:
            reasons.append("missing component" if not str(comp_raw or "").strip() else "invalid component")
        item = {
            "id": rid,
            "language": lang,
            "is_safety_critical": safety,
            "component": component,
            "notes": str(row.get("notes") or "").strip(),
            "usable": not reasons,
            "reasons": reasons,
            "line": line_no,
        }
        out[rid] = item
        if reasons:
            problems.append({"line": line_no, "id": rid, "reason": "; ".join(reasons)})
    return {
        "path": str(path),
        "rows": out,
        "problems": problems,
        "usable": sum(1 for r in out.values() if r["usable"]),
        "total": len(out),
        "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
    }


def check_labels(data_dir: Path, labels_path: Path) -> dict[str, Any]:
    records = load_records(data_dir)
    ids = {str(r.get("id") or "") for r in records}
    labels = load_labels(labels_path)
    unknown = sorted(set(labels["rows"]) - ids)
    if unknown:
        raise DataError(
            f"{labels_path} contains {len(unknown)} id(s) that are not in the collection "
            f"(first: {', '.join(unknown[:3])}). Re-export the sheet or remove the stale rows."
        )
    missing = sorted(ids - set(labels["rows"]))
    return {**labels, "records": len(records), "missing": missing, "missing_count": len(missing)}


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Export/check the REAL complaint labelling sheet")
    p.add_argument("--data-dir", default=str(DEFAULT_DATA_DIR))
    sub = p.add_subparsers(dest="cmd", required=True)
    ex = sub.add_parser("export", help="write data/real_hindi/labels.csv with blank label cells")
    ex.add_argument("--out")
    ex.add_argument("--force", action="store_true", help="overwrite a sheet that already has labels (backup is made)")
    ck = sub.add_parser("check", help="validate a filled sheet; never prints stories")
    ck.add_argument("--labels")
    args = p.parse_args(argv)
    data_dir = Path(args.data_dir)
    try:
        if args.cmd == "export":
            res = export_labels(data_dir, Path(args.out) if args.out else None, force=args.force)
            print(f"Wrote {res['out']}")
            print(f"{res['records']} records; {res['audio_without_transcript']} audio without a transcript")
            print(f"labels_prefilled={res['labels_prefilled']} sha256={res['sha256']}")
            print("Fill language, is_safety_critical, component and notes yourself. No label was prefilled.")
            return 0
        labels_path = Path(args.labels) if args.labels else data_dir / "labels.csv"
        res = check_labels(data_dir, labels_path)
        print(f"{res['usable']}/{res['total']} label row(s) usable across {res['records']} record(s)")
        if res["problems"]:
            print(f"{len(res['problems'])} row(s) need attention:")
            for problem in res["problems"][:20]:
                print(f"  line {problem['line']} id={problem['id'] or '-'}: {problem['reason']}")
            if len(res["problems"]) > 20:
                print(f"  ... and {len(res['problems']) - 20} more")
        if res.get("missing"):
            print(f"{len(res['missing'])} record(s) have no label row:")
            for rid in res["missing"][:20]:
                print(f"  {rid}")
            if len(res["missing"]) > 20:
                print(f"  ... and {len(res['missing']) - 20} more")
        if res["problems"] or res.get("missing"):
            return 3
        print("All records have a valid language, is_safety_critical and component label.")
        return 0
    except DataError as e:
        print(f"REFUSED: {e}", file=sys.stderr)
        return 3


if __name__ == "__main__":
    raise SystemExit(main())
