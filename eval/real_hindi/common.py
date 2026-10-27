"""Shared constants and formatting for the REAL complaint eval.  [REAL-DATA]"""

from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
DEFAULT_DATA_DIR = ROOT / "data" / "real_hindi"
DEFAULT_OUT_DIR = ROOT / "reports" / "real_hindi"

#: Human labels accepted by ``eval.real_hindi.labels``.  ``mixed`` is a real
#: category for code-mixed speech, not a catch-all for "unclear".
LANGS = ("hindi", "hinglish", "english", "mixed")

#: Sample-size floor, not a significance test.  Every table marks n below this.
SMALL_N = 30

MODES = ("rules_only", "rules_plus_hindi", "rules_plus_meta")
MODE_TITLES = {
    "rules_only": "Rules only",
    "rules_plus_hindi": "Rules + hindi_safety",
    "rules_plus_meta": "Rules + Meta",
}
SEVERITY_ORDER = {"Low": 0, "Medium": 1, "High": 2, "Critical": 3}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def display_path(path: Path, root: Path = ROOT) -> str:
    try:
        return str(path.expanduser().resolve().relative_to(root.resolve()))
    except ValueError:
        return str(path.expanduser().resolve())


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def safe_error(value: Any) -> str | None:
    """Keep only an exception *type* so a report cannot echo story text."""
    if not value:
        return None
    head = str(value).split(":", 1)[0].strip()
    if not head or " " in head or len(head) > 80:
        return "Error"
    return head


def empty_summary() -> dict[str, Any]:
    return {
        "n": 0,
        "severity_counts": {},
        "triage_skipped": 0,
        "pipeline_errors": 0,
        "kill_switch_expected": 0,
        "kill_switch_hits": 0,
        "kill_switch_misses": 0,
        "kill_switch_false_alarms": 0,
        "category_expected": 0,
        "category_correct": 0,
        "category_wrong": 0,
    }


def ordered_summary(summary: dict[str, Any]) -> dict[str, Any]:
    """Add zero rows for languages with no records, then keep ``all`` last."""
    out: dict[str, Any] = {}
    for lang in LANGS:
        out[lang] = summary.get(lang) or empty_summary()
    for key, value in summary.items():
        if key not in out and key != "all":
            out[key] = value
    out["all"] = summary.get("all") or empty_summary()
    return out


def sample_label(n: int) -> str:
    if n == 0:
        return f"no records; too small to conclude (n<{SMALL_N})"
    if n < SMALL_N:
        return f"too small to conclude (n<{SMALL_N})"
    return f"n>={SMALL_N}; still not a significance test"


def fmt_severity(counts: dict[str, int]) -> str:
    if not counts:
        return "none"
    ordered = sorted(counts.items(), key=lambda kv: SEVERITY_ORDER.get(kv[0], 9))
    return ", ".join(f"{k} {v}" for k, v in ordered)


def md_cell(value: Any) -> str:
    return str(value if value is not None else "").replace("|", "\\|").replace("\n", " ").strip()


__all__ = [
    "DEFAULT_DATA_DIR",
    "DEFAULT_OUT_DIR",
    "LANGS",
    "MODE_TITLES",
    "MODES",
    "ROOT",
    "SEVERITY_ORDER",
    "SMALL_N",
    "display_path",
    "empty_summary",
    "fmt_severity",
    "md_cell",
    "ordered_summary",
    "safe_error",
    "sample_label",
    "sha256_bytes",
    "sha256_file",
    "sha256_text",
    "utc_now",
]
