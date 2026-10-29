"""Assign a frozen per-component defect label to NHTSA complaint narratives.

The taxonomy in ``reports/defect/taxonomy.json`` is built from TRAIN recalls
only and frozen with a SHA-256. This script applies that taxonomy with Muse
Spark; it never edits the taxonomy and never uses test-window labels.

    # Dry run: build the prompts, print counts and the first prompt. No network.
    python -m scripts.defect_classify --input both --dry-run --limit 1

    # Live run. This process loads the repo .env. A shell export wins.
    # --limit is required. The run is refused when pending batches exceed
    # META_DAILY_CALL_CAP (default 300) or the remaining $30 Meta budget.
    python -m scripts.defect_classify --input both --workers 1 --rpm 20 --limit 1 \
        --complaints data/defect/complaints.parquet \
        --recalls data/defect/recall_descriptions.parquet

Every successful batch is cached in SQLite before the next batch starts, keyed
by model + prompt version + taxonomy SHA + exact prompt. Re-running the same
command skips completed batches. Failed batches are recorded and retried on the
next invocation; no label is invented for a failed call.

Inputs
    complaints.parquet        one row per (ODINO, model year, make, model, component)
    recall_descriptions.parquet  one row per (campaign, component, defect description)

Outputs
    reports/defect/classifications.parquet
    reports/defect/recall_labels.parquet
    reports/defect/classification_manifest.json
    reports/defect/cache/classifications.sqlite   (raw cache; not a report)
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import sqlite3
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

PROMPT_VERSION = "defect-cls-v2"
DEFAULT_MODEL = "muse-spark-1.3-contributor"
OTHER_ID = "other_unclear"
OTHER_LABEL = {
    "id": OTHER_ID,
    "label": "other/unclear",
    "definition": "No specific label fits, or the narrative is too vague.",
}

SYSTEM_PROMPT = """You are a vehicle defect analyst. Each request contains one or more NHTSA \
narratives (complaint text or a recall's defect description) that share the same vehicle \
component. Assign each narrative exactly one label from the allowed list for that component.

Rules:
- Use only the narrative text. Do not infer a defect from the component name alone.
- The labels describe a specific part and failure mode observed in historical recalls for this \
component.
- If the narrative is too vague, describes normal operation, or does not support a specific \
label, choose other_unclear.
- Do not choose a label just because it is the most common in the list.
- evidence must be a short verbatim quote from that narrative that supports the label, at most \
200 characters. For other_unclear, quote the vague text or use "insufficient detail".
- Return only the JSON object, with one item per narrative, in the same order."""

USER_TEMPLATE = """Component: {component}

Allowed labels:
{labels}

Narratives:
{narratives}

Return exactly one JSON object, nothing else, with this shape:
{{"items": [{{"record_id": "c1", "label_id": "<one allowed id>", "confidence": <0 to 1>, "evidence": "<verbatim quote, at most 200 characters>"}}]}}
One item per narrative in order, record_id "c1" through "c{n}". label_id must be one of the allowed ids above; confidence is your certainty from 0 to 1."""


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def canonical_hash(body: dict[str, Any]) -> str:
    return hashlib.sha256(
        json.dumps(body, sort_keys=True, separators=(",", ":"), default=str).encode()
    ).hexdigest()


def file_sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def load_taxonomy(path: Path) -> dict[str, Any]:
    raw = json.loads(path.read_text())
    body = raw.get("body")
    if not isinstance(body, dict) or canonical_hash(body) != raw.get("sha256"):
        raise SystemExit(f"taxonomy hash does not verify: {path}")
    return raw


def allowed_labels(taxonomy: dict[str, Any], component: str) -> list[dict[str, Any]]:
    comp = (taxonomy.get("body", {}).get("components") or {}).get(component)
    labels = list((comp or {}).get("labels") or [])
    if not any(x.get("id") == OTHER_ID for x in labels):
        labels.append(OTHER_LABEL)
    return labels


def label_block(labels: list[dict[str, Any]]) -> str:
    return "\n".join(f"- {x['id']}: {x['label']} — {x['definition']}" for x in labels)


def make_prompt(component: str, labels: list[dict[str, Any]], items: list[dict[str, Any]]) -> str:
    chunks = []
    for i, item in enumerate(items, 1):
        chunks.append(f"[c{i}]\n{item['text'].strip()}")
    return USER_TEMPLATE.format(component=component, labels=label_block(labels),
                                narratives="\n\n".join(chunks), n=len(items))


def make_schema(n_items: int, allowed_ids: list[str]) -> dict[str, Any]:
    return {
        "type": "object",
        "properties": {
            "items": {
                "type": "array",
                "minItems": n_items,
                "maxItems": n_items,
                "items": {
                    "type": "object",
                    "properties": {
                        "record_id": {"type": "string", "enum": [f"c{i}" for i in range(1, n_items + 1)]},
                        "label_id": {"type": "string", "enum": allowed_ids},
                        "confidence": {"type": "number", "minimum": 0, "maximum": 1},
                        "evidence": {"type": "string", "maxLength": 1000},
                    },
                    "required": ["record_id", "label_id", "confidence", "evidence"],
                    "additionalProperties": False,
                },
            }
        },
        "required": ["items"],
        "additionalProperties": False,
    }


def normalize_space(text: str) -> str:
    return " ".join(str(text or "").split()).lower()


def validate_output(value: Any, *, items: list[dict[str, Any]], allowed_ids: list[str]) -> tuple[list[dict[str, Any]], str | None]:
    """Return one result per input item, or (None, reason) if the batch is unusable."""
    if not isinstance(value, dict) or not isinstance(value.get("items"), list):
        return [], "output_missing_items"
    rows = value["items"]
    if len(rows) != len(items):
        return [], f"wrong_item_count:{len(rows)}!={len(items)}"
    by_local: dict[str, dict[str, Any]] = {}
    for row in rows:
        if not isinstance(row, dict):
            return [], "item_not_object"
        local = str(row.get("record_id") or "")
        if local in by_local:
            return [], f"duplicate_record_id:{local}"
        if not local.startswith("c") or not local[1:].isdigit():
            return [], f"bad_record_id:{local}"
        idx = int(local[1:])
        if not (1 <= idx <= len(items)):
            return [], f"record_id_out_of_range:{local}"
        label_id = str(row.get("label_id") or "")
        if label_id not in allowed_ids:
            return [], f"label_not_allowed:{label_id}"
        try:
            conf = float(row.get("confidence"))
        except (TypeError, ValueError):
            return [], "bad_confidence"
        if not math.isfinite(conf) or conf < 0 or conf > 1:
            return [], "bad_confidence_range"
        evidence = str(row.get("evidence") or "").strip()
        by_local[local] = {
            "label_id": label_id,
            "confidence": conf,
            "evidence": evidence,
        }
    expected = {f"c{i}" for i in range(1, len(items) + 1)}
    if set(by_local) != expected:
        return [], "missing_record_id"
    out = []
    for i, item in enumerate(items, 1):
        row = by_local[f"c{i}"]
        quote = normalize_space(row["evidence"])[:120]
        row["evidence_verbatim"] = bool(quote) and quote in normalize_space(item["text"])
        out.append(row)
    return out, None


class RateLimiter:
    """Space request starts at ``rpm``; shared by all workers."""

    def __init__(self, rpm: float):
        self.interval = 60.0 / max(1.0, float(rpm))
        self.lock = threading.Lock()
        self.next_at = time.monotonic()

    def wait(self) -> None:
        with self.lock:
            now = time.monotonic()
            if self.next_at > now:
                time.sleep(self.next_at - now)
                now = time.monotonic()
            self.next_at = max(now, self.next_at) + self.interval


def open_cache(path: Path) -> sqlite3.Connection:
    path.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(str(path), timeout=120)
    con.execute("PRAGMA journal_mode=WAL")
    con.execute("PRAGMA synchronous=NORMAL")
    con.execute(
        """
        CREATE TABLE IF NOT EXISTS batches (
            batch_key TEXT PRIMARY KEY,
            model TEXT NOT NULL,
            prompt_version TEXT NOT NULL,
            taxonomy_sha256 TEXT NOT NULL,
            input_type TEXT NOT NULL,
            component TEXT NOT NULL,
            record_ids TEXT NOT NULL,
            status TEXT NOT NULL,
            error TEXT,
            response_json TEXT,
            attempts INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL
        )
        """
    )
    con.execute(
        """
        CREATE TABLE IF NOT EXISTS classifications (
            record_id TEXT NOT NULL,
            input_type TEXT NOT NULL,
            model TEXT NOT NULL,
            prompt_version TEXT NOT NULL,
            taxonomy_sha256 TEXT NOT NULL,
            odino TEXT,
            cmplid TEXT,
            datea TEXT,
            make TEXT,
            vehicle_model TEXT,
            year INTEGER,
            component TEXT,
            label_id TEXT,
            confidence REAL,
            evidence TEXT,
            evidence_verbatim INTEGER,
            status TEXT NOT NULL,
            error TEXT,
            batch_key TEXT,
            created_at TEXT NOT NULL,
            PRIMARY KEY (record_id, input_type, model, prompt_version, taxonomy_sha256)
        )
        """
    )
    con.execute("CREATE INDEX IF NOT EXISTS idx_batches_status ON batches(status)")
    con.commit()
    return con


def load_complaints(path: Path, start: str, end: str) -> list[dict[str, Any]]:
    if not path.is_file():
        raise SystemExit(
            f"Missing input: {path}. Run "
            "`python -m scripts.defect_prepare_inputs --out-dir data/defect` "
            "to build it from the official NHTSA flat files, or pass --complaints "
            "explicitly. Required columns: datea, odino, cmplid, make, model, year, "
            "component, text. The default data/defect/complaints.parquet is not shipped."
        )
    df = pd.read_parquet(path)
    df = df[(df["datea"] >= start) & (df["datea"] <= end)].copy()
    df = df.sort_values(["component", "datea", "odino"]).reset_index(drop=True)
    records = []
    seen: set[str] = set()
    for r in df.itertuples():
        record_id = f"{r.odino}|{r.component}"
        if record_id in seen:
            raise SystemExit(f"duplicate record_id in complaints: {record_id}")
        seen.add(record_id)
        records.append({
            "record_id": record_id,
            "input_type": "complaint",
            "odino": str(r.odino),
            "cmplid": str(r.cmplid),
            "datea": str(r.datea),
            "make": str(r.make),
            "vehicle_model": str(r.model),
            "year": int(r.year),
            "component": str(r.component),
            "text": str(r.text or ""),
        })
    return records


def load_recalls(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        raise SystemExit(
            f"Missing input: {path}. Run "
            "`python -m scripts.defect_prepare_inputs --out-dir data/defect` "
            "to build it from the official NHTSA flat files, or pass --recalls "
            "explicitly. Required columns: campno, component, desc_defect, rcdate, "
            "make, model, year. The default data/defect/recall_descriptions.parquet "
            "is not shipped."
        )
    df = pd.read_parquet(path).sort_values(["component", "rcdate", "campno"]).reset_index(drop=True)
    records = []
    seen: set[str] = set()
    for r in df.itertuples():
        desc = str(r.desc_defect or "")
        digest = hashlib.sha256(desc.encode("utf-8", errors="replace")).hexdigest()[:12]
        record_id = f"{r.campno}|{r.component}|{digest}"
        if record_id in seen:
            raise SystemExit(f"duplicate record_id in recall descriptions: {record_id}")
        seen.add(record_id)
        records.append({
            "record_id": record_id,
            "input_type": "recall_description",
            "odino": "",
            "cmplid": str(r.campno),
            "campno": str(r.campno),
            "desc_defect": desc,
            "datea": str(r.rcdate),
            "make": str(r.make),
            "vehicle_model": str(r.model),
            "year": int(r.year) if r.year is not None and not pd.isna(r.year) else None,
            "component": str(r.component),
            "text": desc,
            "campno": str(r.campno),
        })
    return records


def build_batches(records: list[dict[str, Any]], taxonomy: dict[str, Any], *, batch_size: int,
                  model: str, taxonomy_sha: str, input_type: str) -> list[dict[str, Any]]:
    by_component: dict[str, list[dict[str, Any]]] = {}
    for r in records:
        by_component.setdefault(r["component"], []).append(r)
    batches = []
    for component in sorted(by_component):
        rows = by_component[component]
        labels = allowed_labels(taxonomy, component)
        allowed_ids = [x["id"] for x in labels]
        for start in range(0, len(rows), batch_size):
            chunk = rows[start:start + batch_size]
            user = make_prompt(component, labels, chunk)
            schema = make_schema(len(chunk), allowed_ids)
            body = {
                "model": model,
                "prompt_version": PROMPT_VERSION,
                "taxonomy_sha256": taxonomy_sha,
                "input_type": input_type,
                "system": SYSTEM_PROMPT,
                "user": user,
                "schema": schema,
            }
            key = hashlib.sha256(
                json.dumps(body, sort_keys=True, separators=(",", ":"), default=str).encode()
            ).hexdigest()
            batches.append({
                "batch_key": key,
                "component": component,
                "input_type": input_type,
                "records": chunk,
                "allowed_ids": allowed_ids,
                "user": user,
                "schema": schema,
                "max_tokens": max(1200, 220 * len(chunk)),
            })
    return batches


def call_batch(batch: dict[str, Any], *, model: str, limiter: RateLimiter) -> dict[str, Any]:
    from src.ai_layer.meta_client import MetaError, chat_json

    last_error = "unknown"
    for attempt in range(1, 3):
        limiter.wait()
        try:
            value = chat_json(
                system=SYSTEM_PROMPT,
                user=batch["user"],
                schema=batch["schema"],
                schema_name="defect_label_batch",
                model=model,
                timeout=60.0,
                max_tokens=batch["max_tokens"],
            )
        except MetaError as e:
            last_error = e.reason
            if e.reason in {"daily_call_cap", "budget_exceeded", "budget_unavailable", "budget_unpriced_model"}:
                return {"status": "cap", "error": e.reason, "attempts": attempt}
            if e.reason in {"meta_disabled", "meta_url_must_be_https"} or e.reason.startswith("meta_host_not_allowlisted"):
                return {"status": "fatal", "error": e.reason, "attempts": attempt}
            if e.reason.startswith("meta_http_4") and e.reason != "meta_http_429":
                return {"status": "failed", "error": e.reason, "attempts": attempt}
            if attempt == 2:
                return {"status": "failed", "error": e.reason, "attempts": attempt}
            time.sleep(1.0)
            continue
        parsed, reason = validate_output(value, items=batch["records"], allowed_ids=batch["allowed_ids"])
        if reason is None:
            return {"status": "ok", "items": parsed, "raw": value, "attempts": attempt}
        last_error = reason
        if attempt == 2:
            return {"status": "failed", "error": reason, "attempts": attempt}
        time.sleep(1.0)
    return {"status": "failed", "error": last_error, "attempts": 2}


def store_batch(con: sqlite3.Connection, batch: dict[str, Any], result: dict[str, Any], *,
                model: str, taxonomy_sha: str) -> None:
    now = utc_now()
    status = result["status"]
    error = result.get("error")
    raw = result.get("raw")
    con.execute(
        """
        INSERT INTO batches (batch_key, model, prompt_version, taxonomy_sha256, input_type, component,
                             record_ids, status, error, response_json, attempts, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(batch_key) DO UPDATE SET status=excluded.status, error=excluded.error,
            response_json=excluded.response_json, attempts=excluded.attempts, created_at=excluded.created_at
        """,
        [batch["batch_key"], model, PROMPT_VERSION, taxonomy_sha, batch["input_type"], batch["component"],
         json.dumps([r["record_id"] for r in batch["records"]]), status, error,
         json.dumps(raw, sort_keys=True) if raw is not None else None, int(result.get("attempts", 0)), now],
    )
    for i, rec in enumerate(batch["records"]):
        item = result.get("items", [None] * len(batch["records"]))[i] if status == "ok" else None
        con.execute(
            """
            INSERT INTO classifications (record_id, input_type, model, prompt_version, taxonomy_sha256,
                odino, cmplid, datea, make, vehicle_model, year, component, label_id, confidence, evidence,
                evidence_verbatim, status, error, batch_key, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(record_id, input_type, model, prompt_version, taxonomy_sha256) DO UPDATE SET
                label_id=excluded.label_id, confidence=excluded.confidence, evidence=excluded.evidence,
                evidence_verbatim=excluded.evidence_verbatim, status=excluded.status, error=excluded.error,
                batch_key=excluded.batch_key, created_at=excluded.created_at
            """,
            [rec["record_id"], batch["input_type"], model, PROMPT_VERSION, taxonomy_sha,
             rec.get("odino"), rec.get("cmplid"), rec.get("datea"), rec.get("make"),
             rec.get("vehicle_model"), rec.get("year"), rec.get("component"),
             item["label_id"] if item else None, item["confidence"] if item else None,
             item["evidence"] if item else None, int(item["evidence_verbatim"]) if item else None,
             status, error, batch["batch_key"], now],
        )
    con.commit()


def existing_batch_status(con: sqlite3.Connection, keys: list[str]) -> dict[str, str]:
    if not keys:
        return {}
    out: dict[str, str] = {}
    for start in range(0, len(keys), 900):
        chunk = keys[start:start + 900]
        marks = ",".join("?" for _ in chunk)
        for key, status in con.execute(f"SELECT batch_key, status FROM batches WHERE batch_key IN ({marks})", chunk):
            out[key] = status
    return out


def export(con: sqlite3.Connection, *, model: str, taxonomy_sha: str, complaints_in: list[dict[str, Any]],
           recalls_in: list[dict[str, Any]], out_dir: Path) -> dict[str, Any]:
    def frame(input_type: str, source: list[dict[str, Any]]) -> pd.DataFrame:
        if not source:
            return pd.DataFrame(columns=[
                "record_id", "input_type", "odino", "cmplid", "datea", "make", "vehicle_model", "year",
                "component", "text", "label_id", "confidence", "evidence", "evidence_verbatim", "status",
                "error", "batch_key", "campno", "model", "prompt_version", "taxonomy_sha256",
            ])
        rows = con.execute(
            """
            SELECT record_id, label_id, confidence, evidence, evidence_verbatim, status, error, batch_key
            FROM classifications
            WHERE input_type=? AND model=? AND prompt_version=? AND taxonomy_sha256=?
            """,
            [input_type, model, PROMPT_VERSION, taxonomy_sha],
        ).fetchall()
        labels = {r[0]: {"label_id": r[1], "confidence": r[2], "evidence": r[3],
                          "evidence_verbatim": r[4], "status": r[5], "error": r[6], "batch_key": r[7]}
                  for r in rows}
        out = []
        for rec in source:
            lab = labels.get(rec["record_id"], {})
            out.append({
                **rec,
                "model": model,
                "prompt_version": PROMPT_VERSION,
                "taxonomy_sha256": taxonomy_sha,
                "label_id": lab.get("label_id"),
                "confidence": lab.get("confidence"),
                "evidence": lab.get("evidence"),
                "evidence_verbatim": lab.get("evidence_verbatim"),
                "status": lab.get("status") or "missing",
                "error": lab.get("error"),
                "batch_key": lab.get("batch_key"),
            })
        return pd.DataFrame(out)

    cdf = frame("complaint", complaints_in)
    rdf = frame("recall_description", recalls_in)
    # The exported report does not need the full narrative; the cache and the
    # sample CSV already hold the input text. Keeping it out of the report
    # avoids copying free-text complaint narratives into a committed artifact.
    cdf = cdf.drop(columns=["text"], errors="ignore")
    rdf = rdf.drop(columns=["text"], errors="ignore")
    out_dir.mkdir(parents=True, exist_ok=True)
    cpath = out_dir / "classifications.parquet"
    rpath = out_dir / "recall_labels.parquet"
    cdf.to_parquet(cpath, index=False)
    rdf.to_parquet(rpath, index=False)

    def dist(df: pd.DataFrame) -> dict[str, int]:
        ok = df[df["status"] == "ok"]
        return {str(k): int(v) for k, v in ok["label_id"].value_counts(dropna=False).items()}

    manifest = {
        "created_at": utc_now(),
        "model": model,
        "prompt_version": PROMPT_VERSION,
        "taxonomy_sha256": taxonomy_sha,
        "system_prompt_sha256": hashlib.sha256(SYSTEM_PROMPT.encode()).hexdigest(),
        "complaints": {
            "inputs": int(len(cdf)),
            "ok": int((cdf["status"] == "ok").sum()),
            "failed": int((cdf["status"] != "ok").sum()),
            "other_unclear": int(((cdf["status"] == "ok") & (cdf["label_id"] == OTHER_ID)).sum()),
            "label_counts": dist(cdf),
            "sha256": file_sha(cpath),
        },
        "recalls": {
            "inputs": int(len(rdf)),
            "ok": int((rdf["status"] == "ok").sum()),
            "failed": int((rdf["status"] != "ok").sum()),
            "other_unclear": int(((rdf["status"] == "ok") & (rdf["label_id"] == OTHER_ID)).sum()),
            "label_counts": dist(rdf),
            "sha256": file_sha(rpath),
        },
    }
    (out_dir / "classification_manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return manifest


def dry_run(batches: list[dict[str, Any]], *, taxonomy: dict[str, Any], limit: int,
            model: str, batch_size: int) -> dict[str, Any]:
    try:
        import tiktoken
        enc = tiktoken.get_encoding("cl100k_base")
        count = lambda s: len(enc.encode(s))
        token_note = "cl100k_base"
    except Exception:
        count = lambda s: max(1, len(s) // 4)
        token_note = "chars/4 fallback"
    shown = 0
    total_in = total_out = 0
    selected = batches[:limit] if limit else batches
    for b in selected:
        total_in += count(SYSTEM_PROMPT) + count(b["user"])
        total_out += 70 * len(b["records"])
        if shown < 1:
            print("=" * 78)
            print(f"batch key: {b['batch_key']}")
            print(f"component: {b['component']}  records: {len(b['records'])}")
            print("-" * 78)
            print(b["user"][:6000])
            print("=" * 78)
            shown += 1
    records_total = sum(len(b["records"]) for b in batches)
    records_estimated = sum(len(b["records"]) for b in selected)
    pricing = {"standard_input": 1.25, "standard_output": 4.25,
               "contributor_input": 0.10, "contributor_output": 0.20}
    est = {
        "created_at": utc_now(),
        "model": model,
        "prompt_version": PROMPT_VERSION,
        "batch_size": batch_size,
        "taxonomy_sha256": taxonomy.get("sha256"),
        "batches_total": len(batches),
        "batches_estimated": len(selected),
        "records_total": records_total,
        "records_estimated": records_estimated,
        "estimated_input_tokens": total_in,
        "output_tokens_per_record_assumed": 70,
        "estimated_output_tokens_at_70": total_out,
        "tokenizer": token_note,
        "pricing_usd_per_mtok": pricing,
        "estimated_cost_usd_at_70_output": {
            "standard": round(total_in / 1e6 * pricing["standard_input"]
                              + total_out / 1e6 * pricing["standard_output"], 4),
            "contributor": round(total_in / 1e6 * pricing["contributor_input"]
                                 + total_out / 1e6 * pricing["contributor_output"], 4),
        },
        "sensitivity_output_tokens_per_record": {
            "60": round(total_in / 1e6 * pricing["contributor_input"]
                        + records_total * 60 / 1e6 * pricing["contributor_output"], 4),
            "120": round(total_in / 1e6 * pricing["contributor_input"]
                         + records_total * 120 / 1e6 * pricing["contributor_output"], 4),
        },
        "sensitivity_note": "cost sensitivity uses Contributor input/output prices and the exact input-token estimate",
        "note": "dry run only; no network call was made; token counts are a local estimate, not a bill",
    }
    print(json.dumps(est, indent=2))
    return est


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Classify NHTSA narratives into the frozen defect taxonomy")
    p.add_argument("--input", choices=["complaints", "recalls", "both"], default="both")
    p.add_argument("--complaints", default=str(REPO_ROOT / "data/defect/complaints.parquet"))
    p.add_argument("--recalls", default=str(REPO_ROOT / "data/defect/recall_descriptions.parquet"))
    p.add_argument("--taxonomy", default=str(REPO_ROOT / "reports/defect/taxonomy.json"))
    p.add_argument("--cache", default=str(REPO_ROOT / "reports/defect/cache/classifications.sqlite"))
    p.add_argument("--out-dir", default=str(REPO_ROOT / "reports/defect"))
    p.add_argument("--model", default=DEFAULT_MODEL)
    p.add_argument("--batch-size", type=int, default=8)
    p.add_argument("--workers", type=int, default=1)
    p.add_argument("--rpm", type=float, default=140.0)
    p.add_argument("--limit", type=int, default=0, help="first N batches; required for live runs. The 18,998-batch dry-run plan exceeds the default 300/day cap; start with 1, one worker, 20 RPM, and remaining $30 budget")
    p.add_argument("--start", default="2015-01-01")
    p.add_argument("--end", default="2024-12-31")
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--export-only", action="store_true")
    p.add_argument("--no-export", action="store_true")
    args = p.parse_args(argv)

    if args.batch_size < 1 or args.workers < 1 or args.rpm <= 0 or args.limit < 0:
        p.error("batch-size, workers and rpm must be positive; limit must be nonnegative")
    if not args.dry_run and not args.export_only and args.limit == 0:
        p.error("Live runs require an explicit --limit batch count; start with --dry-run --limit 1")
    taxonomy_path = Path(args.taxonomy)
    taxonomy = load_taxonomy(taxonomy_path)
    taxonomy_sha = taxonomy["sha256"]
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    cache_path = Path(args.cache)

    complaints_in = load_complaints(Path(args.complaints), args.start, args.end) if args.input in {"complaints", "both"} else []
    recalls_in = load_recalls(Path(args.recalls)) if args.input in {"recalls", "both"} else []

    batches: list[dict[str, Any]] = []
    if complaints_in:
        batches += build_batches(complaints_in, taxonomy, batch_size=args.batch_size, model=args.model,
                                 taxonomy_sha=taxonomy_sha, input_type="complaint")
    if recalls_in:
        batches += build_batches(recalls_in, taxonomy, batch_size=args.batch_size, model=args.model,
                                 taxonomy_sha=taxonomy_sha, input_type="recall_description")
    if args.limit:
        batches = batches[: args.limit]

    if args.dry_run:
        est = dry_run(batches, taxonomy=taxonomy, limit=args.limit, model=args.model,
                      batch_size=args.batch_size)
        if not args.limit:
            (out_dir / "classification_estimate.json").write_text(
                json.dumps(est, indent=2), encoding="utf-8")
            print(f"wrote {out_dir / 'classification_estimate.json'}")
        return 0

    con = open_cache(cache_path)
    if args.export_only:
        manifest = export(con, model=args.model, taxonomy_sha=taxonomy_sha, complaints_in=complaints_in,
                          recalls_in=recalls_in, out_dir=out_dir)
        print(json.dumps(manifest, indent=2))
        return 0

    from dotenv import load_dotenv
    load_dotenv(REPO_ROOT / ".env", override=False)
    if not (os.getenv("META_API_KEY") or os.getenv("MODEL_API_KEY")):
        print("REFUSED: no META_API_KEY or MODEL_API_KEY in the environment; source .env first", file=sys.stderr)
        return 2
    from src.ai_layer import config
    if args.model != config.model_text():
        print(f"note: script model {args.model!r} overrides META_MODEL_TEXT {config.model_text()!r}")

    statuses = existing_batch_status(con, [b["batch_key"] for b in batches])
    pending = [b for b in batches if statuses.get(b["batch_key"]) != "ok"]
    cap = config.daily_call_cap()
    if len(pending) > cap:
        print(
            f"REFUSED: {len(pending)} pending batches exceed META_DAILY_CALL_CAP={cap}. "
            "Pass a smaller --limit. The full classification plan is not authorized on the default cap.",
            file=sys.stderr,
        )
        return 2
    from src.ai_layer.budget import status as budget_status
    try:
        ledger = budget_status()
    except Exception as e:
        print(f"REFUSED: Meta spend ledger is unreadable ({type(e).__name__}). No live calls were made.", file=sys.stderr)
        return 2
    remaining = float(ledger["limit_usd"]) - float(ledger["reserved_upper_bound_usd"])
    # Conservative standard-rate bound: 8k input tokens and 70 output tokens per record.
    est_usd = len(pending) * ((8000 * 1.25) + (70 * args.batch_size * 4.25)) / 1_000_000
    if est_usd > remaining:
        print(
            f"REFUSED: estimated ${est_usd:.2f} exceeds the remaining ${remaining:.2f} "
            f"of the ${ledger['limit_usd']:.0f} Meta cap. Lower --limit. No live calls were made.",
            file=sys.stderr,
        )
        return 2
    done_count = len(batches) - len(pending)
    print(json.dumps({
        "model": args.model,
        "prompt_version": PROMPT_VERSION,
        "taxonomy_sha256": taxonomy_sha,
        "batches": len(batches),
        "already_ok": done_count,
        "pending": len(pending),
        "records": len(complaints_in) + len(recalls_in),
        "workers": args.workers,
        "rpm": args.rpm,
        "daily_call_cap": config.daily_call_cap(),
    }, indent=2), flush=True)

    if not pending:
        manifest = export(con, model=args.model, taxonomy_sha=taxonomy_sha, complaints_in=complaints_in,
                          recalls_in=recalls_in, out_dir=out_dir)
        print(json.dumps(manifest, indent=2))
        return 0

    limiter = RateLimiter(args.rpm)
    started = time.time()
    ok = failed = 0
    stop = False

    def work(batch: dict[str, Any]) -> dict[str, Any]:
        return call_batch(batch, model=args.model, limiter=limiter)

    with ThreadPoolExecutor(max_workers=max(1, args.workers)) as pool:
        futures = {pool.submit(work, b): b for b in pending}
        try:
            for n, fut in enumerate(as_completed(futures), 1):
                batch = futures[fut]
                try:
                    result = fut.result()
                except Exception as e:  # a worker bug must not kill the cache
                    result = {"status": "failed", "error": f"worker:{type(e).__name__}", "attempts": 0}
                store_batch(con, batch, result, model=args.model, taxonomy_sha=taxonomy_sha)
                if result["status"] == "ok":
                    ok += 1
                else:
                    failed += 1
                if result["status"] in {"cap", "fatal"}:
                    stop = True
                if n % 25 == 0 or n == len(pending) or stop:
                    elapsed = time.time() - started
                    rate = n / elapsed * 60 if elapsed > 0 else 0
                    eta = (len(pending) - n) / (n / elapsed) if n > 0 and elapsed > 0 else 0
                    print(json.dumps({
                        "done": n, "ok": ok, "failed": failed, "total": len(pending),
                        "rate_per_min": round(rate, 1), "eta_min": round(eta / 60, 1),
                        "last_status": result["status"], "last_error": result.get("error"),
                    }), flush=True)
                if stop:
                    for f in futures:
                        f.cancel()
                    break
        except KeyboardInterrupt:
            print("interrupted; completed batches are cached", file=sys.stderr)
            for f in futures:
                f.cancel()

    elapsed = time.time() - started
    print(json.dumps({
        "elapsed_s": round(elapsed, 1),
        "ok_batches": ok,
        "failed_batches": failed,
        "calls_today": __import__("src.ai_layer.meta_client", fromlist=["calls_today"]).calls_today(),
    }, indent=2), flush=True)
    if not args.no_export:
        manifest = export(con, model=args.model, taxonomy_sha=taxonomy_sha, complaints_in=complaints_in,
                          recalls_in=recalls_in, out_dir=out_dir)
        print(json.dumps(manifest, indent=2))
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
