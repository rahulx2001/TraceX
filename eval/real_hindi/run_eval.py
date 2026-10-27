"""Evaluate REAL, consenting human complaints: rules vs rules+hindi vs rules+Meta.  [REAL-DATA]

    python -m eval.real_hindi.run_eval [--data-dir data/real_hindi] \\
        [--labels data/real_hindi/labels.csv] [--out-dir reports/real_hindi]

This runner is separate from every synthetic eval.  It reads only records
written by ``scripts.real_hindi_collect`` with ``"synthetic": false``, a
consent version/hash that still matches ``eval.real_hindi.consent``, a
transcript, and a complete human label row.  Any ambiguity is refused.

Modes, one addition at a time:
* ``rules_only``      : existing IntakeAgent -> existing TriageAgent.
* ``rules_plus_hindi``: same, plus the deterministic ``hindi_safety`` hooks.
* ``rules_plus_meta`` : same as rules-only, plus ``maybe_enhance_intake`` and
  ``maybe_raise_severity``.  Only runs when a Meta key is configured; otherwise
  the report says NOT RUN and contains no Meta numbers.

Metrics come from ``eval.hindi_fresh.run_hindi_eval.summarise``, so the columns
match the synthetic Hindi eval.  There is no human severity label, so no
severity accuracy is claimed.  Reports contain no story text.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import shutil
import sys
import time
from pathlib import Path
from typing import Any, Awaitable, Callable

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
sys.path.insert(0, str(ROOT))

from eval.enhanced.run_eval_modes import _health_counts, _isolate  # noqa: E402
from eval.hindi_fresh.run_hindi_eval import lowers, run_call, summarise  # noqa: E402
from eval.real_hindi.common import (  # noqa: E402
    DEFAULT_DATA_DIR,
    DEFAULT_OUT_DIR,
    LANGS,
    SEVERITY_ORDER,
    SMALL_N,
    display_path,
    ordered_summary,
    safe_error,
    sample_label,
    sha256_file,
    sha256_text,
    utc_now,
)
from eval.real_hindi.consent import CONSENT_REGISTRY  # noqa: E402
from eval.real_hindi.guard import (  # noqa: E402
    ConfigChanged,
    config_manifest,
    guard_config,
    load_run_docs,
    recover_state,
    save_state,
)
from eval.real_hindi.labels import check_labels  # noqa: E402
from eval.real_hindi.reporting import render_report, render_runs_index  # noqa: E402
from scripts.real_hindi_collect import DataError, load_records, write_json_atomic  # noqa: E402

Runner = Callable[[str, dict[str, Any]], Awaitable[dict[str, Any]]]


def _record_problems(record: dict[str, Any], data_dir: Path) -> list[str]:
    """Return human-readable integrity problems; never includes story text."""
    out: list[str] = []
    if record.get("synthetic") is not False:
        out.append("synthetic is not false")
    if record.get("schema_version") != 1:
        out.append("schema_version is not 1")
    if record.get("collection") != "local_consent_page_v1":
        out.append("collection is not local_consent_page_v1")
    if record.get("consent") is not True:
        out.append("consent is not true")
    version = str(record.get("consent_version") or "")
    expected = CONSENT_REGISTRY.get(version)
    if not expected:
        out.append(f"unknown consent version {version!r}")
    elif record.get("consent_text_sha256") != expected:
        out.append("consent text hash does not match the registered version")
    if not str(record.get("consent_at") or "").strip():
        out.append("consent_at is missing")
    if record.get("ai_processing_consent") is not True:
        out.append("AI-processing consent is not true")
    if record.get("no_identifiers_confirmed") is not True:
        out.append("no-identifiers confirmation is not true")
    if record.get("reported_language") not in LANGS:
        out.append("reported_language is not hindi/hinglish/english/mixed")

    narrative = record.get("narrative")
    if not isinstance(narrative, str) or not narrative.strip():
        if record.get("audio_file"):
            out.append("audio has no transcript; run the transcribe command first")
        else:
            out.append("no story text")
    else:
        if record.get("narrative_sha256") != sha256_text(narrative):
            out.append("story hash does not match narrative_sha256")
        if record.get("narrative_chars") != len(narrative):
            out.append("narrative_chars does not match the story length")
        if record.get("transcript_source") not in ("typed", "manual"):
            out.append("transcript_source is not typed/manual")

    audio_rel = record.get("audio_file")
    if audio_rel is not None:
        if not isinstance(audio_rel, str) or not audio_rel.strip():
            out.append("audio_file is not a path")
        else:
            audio_root = (data_dir / "audio").resolve()
            audio_path = (data_dir / audio_rel).resolve()
            if audio_root not in audio_path.parents:
                out.append("audio path is outside the audio directory")
            elif not audio_path.is_file():
                out.append("audio file is missing")
            elif record.get("audio_sha256") != sha256_file(audio_path):
                out.append("audio hash does not match audio_sha256")
        if record.get("audio_metadata_stripped") is not True:
            out.append("audio_metadata_stripped is not true")
        if record.get("audio_format") != "wav":
            out.append("audio_format is not wav")
        if record.get("audio_sample_rate") != 16000:
            out.append("audio_sample_rate is not 16000")
        if record.get("audio_channels") != 1:
            out.append("audio_channels is not 1")
        seconds = record.get("audio_seconds")
        if not isinstance(seconds, (int, float)) or seconds <= 0 or seconds > 180.5:
            out.append("audio_seconds is missing or outside 0-180")
    return out


def load_real_set(data_dir: Path, labels_path: Path) -> dict[str, Any]:
    """Load records + human labels, refusing anything that cannot be scored."""
    data_dir = data_dir.expanduser().resolve()
    labels_path = labels_path.expanduser().resolve()
    records = load_records(data_dir)
    if not records:
        raise DataError(
            f"no records in {data_dir / 'records'}; collect real stories first "
            "(python -m scripts.real_hindi_collect serve)"
        )
    if not labels_path.is_file():
        raise DataError(
            f"label sheet not found: {display_path(labels_path)}; export it with "
            "python -m eval.real_hindi.labels export and fill it in yourself"
        )
    try:
        label_res = check_labels(data_dir, labels_path)
    except OSError as e:
        raise DataError(f"cannot read label sheet {display_path(labels_path)}: {type(e).__name__}") from e

    problems: list[str] = []
    for record in records:
        rid = str(record.get("id") or "?")
        problems += [f"{rid}: {reason}" for reason in _record_problems(record, data_dir)]
    problems += [
        f"label line {p['line']} id={p['id'] or '-'}: {p['reason']}"
        for p in label_res["problems"]
    ]
    problems += [
        f"{rid}: no row in the label sheet" for rid in (label_res.get("missing") or [])
    ]
    if problems:
        shown = "; ".join(problems[:10])
        more = f" (+{len(problems) - 10} more)" if len(problems) > 10 else ""
        raise DataError(f"refusing {len(problems)} invalid item(s): {shown}{more}")

    calls: list[dict[str, Any]] = []
    mismatches = 0
    audio_seconds = 0.0
    for record in records:
        rid = str(record.get("id") or "")
        label = label_res["rows"][rid]
        narrative = str(record.get("narrative") or "").strip()
        if record.get("reported_language") != label["language"]:
            mismatches += 1
        audio_seconds += float(record.get("audio_seconds") or 0)
        calls.append({
            "id": rid,
            "lang": label["language"],
            "text": narrative,
            "kill_switch": label["is_safety_critical"],
            "expect_category": label["component"],
            "reported_language": record.get("reported_language"),
        })
    return {
        "source_dir": display_path(data_dir),
        "records": records,
        "calls": calls,
        "n_records": len(records),
        "text_records": sum(1 for r in records if str(r.get("narrative") or "").strip()),
        "audio_records": sum(1 for r in records if r.get("audio_file")),
        "audio_seconds_total": round(audio_seconds, 3),
        "consent_versions": sorted({str(r.get("consent_version")) for r in records}),
        "reported_language_mismatch": mismatches,
        "labels": {
            "path": display_path(labels_path),
            "sha256": label_res["sha256"],
            "rows": label_res["total"],
            "usable": label_res["usable"],
        },
    }


def meta_availability() -> tuple[str, str, str | None]:
    from src.ai_layer import config

    model = config.model_text()
    if config.meta_enabled():
        return "run", model, None
    if config.layer_switch() == "off":
        reason = "FRONTLINE_AI_LAYER=off; Meta mode was disabled on this run."
    else:
        reason = "no META_API_KEY or MODEL_API_KEY is configured; Meta mode was not attempted."
    return "not_run", model, reason


def normalise_result(result: dict[str, Any] | None) -> dict[str, Any]:
    out = dict(result or {})
    out["severity"] = out.get("severity")
    out["triage_skipped"] = bool(out.get("triage_skipped"))
    out["kill_switch"] = out.get("kill_switch")
    out["category"] = out.get("category")
    out["error"] = safe_error(out.get("error"))
    out.setdefault("kill_switch_term", None)
    out["meta_calls"] = int(out.get("meta_calls") or 0)
    out["meta_failures"] = int(out.get("meta_failures") or 0)
    out.setdefault("ms", None)
    return out


async def run_call_meta(pack, call: dict[str, Any]) -> dict[str, Any]:
    """The existing enhanced path, without the deterministic hindi layer."""
    from src.agents.base import InteractionContext
    from src.agents.intake import IntakeAgent
    from src.agents.triage import TriageAgent
    from src.ai_layer.intake_enhancer import maybe_enhance_intake
    from src.ai_layer.severity import maybe_raise_severity

    ctx = InteractionContext(interaction_id=f"int_real_meta_{call['id']}", pack=pack, channel="web_text")
    ctx.record_turn("customer", call["text"])
    c0, f0 = _health_counts()
    t0 = time.perf_counter()
    out: dict[str, Any] = {"error": None}
    try:
        ires = await IntakeAgent(ctx).run(customer_turn=call["text"])
        ires = await maybe_enhance_intake(ctx, call["text"], ires)
        tres = await TriageAgent(ctx).run()
        rule_severity = None if tres.get("skipped") else tres.get("severity")
        tres = await maybe_raise_severity(ctx, tres)
        out.update({
            "severity": None if tres.get("skipped") else tres.get("severity"),
            "rule_severity_before_ai": rule_severity,
            "triage_skipped": bool(tres.get("skipped")),
            "kill_switch": bool(ires.get("kill_switch") or (ctx.safety_flags or {}).get("escalation")),
            "kill_switch_term": ires.get("kill_switch"),
            "category": ctx.slots.get("category"),
        })
    except Exception as e:  # counted, never hidden; only the type is kept
        out.update({"severity": None, "rule_severity_before_ai": None, "triage_skipped": False,
                    "kill_switch": None, "kill_switch_term": None, "category": None,
                    "error": type(e).__name__})
    c1, f1 = _health_counts()
    out["ms"] = round((time.perf_counter() - t0) * 1000, 1)
    out["meta_calls"] = c1 - c0
    out["meta_failures"] = f1 - f0
    return out


def make_runner() -> Runner:
    from src.data.warehouse import init_ops_db
    from src.domains.loader import load_pack

    init_ops_db()
    try:
        from scripts.seed_domains import build as build_domain

        build_domain("automotive_nhtsa")
    except Exception:
        pass
    pack = load_pack("automotive_nhtsa")

    async def runner(mode: str, call: dict[str, Any]) -> dict[str, Any]:
        if mode == "rules_plus_meta":
            return await run_call_meta(pack, call)
        if mode == "rules_only":
            return await run_call(pack, call, hindi=False, tag="real_rules")
        if mode == "rules_plus_hindi":
            return await run_call(pack, call, hindi=True, tag="real_hindi")
        raise ValueError(f"unknown mode {mode}")

    return runner


def compare_meta(calls: list[dict[str, Any]], rules: list[dict[str, Any]],
                 meta: list[dict[str, Any]]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for lang in (*LANGS, "all"):
        idx = [i for i, c in enumerate(calls) if lang == "all" or c["lang"] == lang]
        both = [i for i in idx if rules[i].get("severity") and meta[i].get("severity")]
        agree = sum(1 for i in both if rules[i]["severity"] == meta[i]["severity"])
        raises = sum(1 for i in both if SEVERITY_ORDER.get(meta[i]["severity"], -1) > SEVERITY_ORDER.get(rules[i]["severity"], -1))
        lowers_n = sum(1 for i in both if SEVERITY_ORDER.get(meta[i]["severity"], 9) < SEVERITY_ORDER.get(rules[i]["severity"], 9))
        out[lang] = {
            "n": len(idx),
            "n_both_scored": len(both),
            "severity_agreement": round(agree / len(both), 3) if both else None,
            "agree": agree,
            "raises": raises,
            "lowers": lowers_n,
            "meta_calls": sum(int(meta[i].get("meta_calls") or 0) for i in idx),
            "meta_failures_fallback_to_rules": sum(int(meta[i].get("meta_failures") or 0) for i in idx),
            "pipeline_errors": sum(1 for i in idx if meta[i].get("error")),
        }
    return out


def _slim(result: dict[str, Any]) -> dict[str, Any]:
    return {
        "severity": result.get("severity"),
        "triage_skipped": bool(result.get("triage_skipped")),
        "kill_switch": result.get("kill_switch"),
        "category": result.get("category"),
        "error": result.get("error"),
        "meta_calls": int(result.get("meta_calls") or 0),
        "meta_failures": int(result.get("meta_failures") or 0),
        "ms": result.get("ms"),
    }


async def evaluate(calls: list[dict[str, Any]], *, runner: Runner, meta_status: str) -> dict[str, Any]:
    rules = [normalise_result(await runner("rules_only", c)) for c in calls]
    hindi = [normalise_result(await runner("rules_plus_hindi", c)) for c in calls]
    meta = None
    if meta_status == "run":
        meta = [normalise_result(await runner("rules_plus_meta", c)) for c in calls]

    modes: dict[str, Any] = {
        "rules_only": {"status": "run", "summary": ordered_summary(summarise(calls, rules))},
        "rules_plus_hindi": {
            "status": "run",
            "summary": ordered_summary(summarise(calls, hindi)),
            "lowers": lowers(rules, hindi),
        },
    }
    if meta is not None:
        modes["rules_plus_meta"] = {
            "status": "run",
            "summary": ordered_summary(summarise(calls, meta)),
            "compare": compare_meta(calls, rules, meta),
        }
    else:
        modes["rules_plus_meta"] = {"status": "not_run", "summary": None, "compare": None}
    return {
        "n_by_language": {lang: sum(1 for c in calls if c["lang"] == lang) for lang in LANGS},
        "modes": modes,
        "per_call": [
            {
                "id": c["id"],
                "language": c["lang"],
                "reported_language": c.get("reported_language"),
                "is_safety_critical": c["kill_switch"],
                "component": c["expect_category"],
                "rules_only": _slim(rules[i]),
                "rules_plus_hindi": _slim(hindi[i]),
                "rules_plus_meta": _slim(meta[i]) if meta is not None else "not run",
            }
            for i, c in enumerate(calls)
        ],
    }

def build_run(*, loaded: dict[str, Any], manifest: dict[str, Any], decision: dict[str, Any],
              evaluation: dict[str, Any], meta_status: str, meta_model: str,
              meta_reason: str | None, previous_labels_sha256: str | None) -> dict[str, Any]:
    labels_sha = loaded["labels"]["sha256"]
    return {
        "schema": 1,
        "kind": "real_hindi_eval",
        "dataset_name": "real_hindi",
        "synthetic": False,
        "generated_at": utc_now(),
        "dataset": {
            "source_dir": loaded["source_dir"],
            "records": loaded["n_records"],
            "text_records": loaded["text_records"],
            "audio_records": loaded["audio_records"],
            "audio_seconds_total": loaded["audio_seconds_total"],
            "consent_versions": loaded["consent_versions"],
            "reported_language_mismatch": loaded["reported_language_mismatch"],
        },
        "labels": {
            **loaded["labels"],
            "changed_since_previous": bool(previous_labels_sha256 and previous_labels_sha256 != labels_sha),
            "previous_sha256": previous_labels_sha256,
        },
        "config": {
            **manifest,
            "held_out": bool(decision["held_out"]),
            "first_run": bool(decision["first_run"]),
            "previous_hash": decision.get("previous_hash"),
            "approval": decision.get("approval"),
        },
        "meta": {"status": meta_status, "model": meta_model, "reason": meta_reason},
        "modes": evaluation["modes"],
        "per_call": evaluation["per_call"],
    }


def _write_text_atomic(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(text, encoding="utf-8")
    try:
        os.chmod(tmp, 0o644)
    except OSError:
        pass
    os.replace(tmp, path)


def write_run(out_dir: Path, out: dict[str, Any]) -> tuple[str, Path, dict[str, Any]]:
    """Write one immutable run directory; never overwrite an older run."""
    out_dir = out_dir.expanduser().resolve()
    runs_dir = out_dir / "runs"
    runs_dir.mkdir(parents=True, exist_ok=True)
    base = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
    run_id = base
    for n in range(1, 100):
        run_id = base if n == 1 else f"{base}-{n}"
        if not (runs_dir / run_id).exists():
            break
    else:
        raise DataError("could not allocate a unique run id")
    out = dict(out)
    out["run_id"] = run_id
    tmp = out_dir / f".tmp-{run_id}"
    if tmp.exists():
        shutil.rmtree(tmp)
    try:
        tmp.mkdir(parents=True, mode=0o700)
        summary = {k: v for k, v in out.items() if k != "per_call"}
        write_json_atomic(tmp / "run.json", summary)
        write_json_atomic(tmp / "real_hindi_eval.json", out)
        report_path = tmp / "REAL_HINDI_EVAL.md"
        report_path.write_text(render_report(out), encoding="utf-8")
        try:
            os.chmod(report_path, 0o644)
        except OSError:
            pass
        final = runs_dir / run_id
        os.replace(tmp, final)
    except Exception:
        shutil.rmtree(tmp, ignore_errors=True)
        raise
    return run_id, final, out


def _mode_line(mode: dict[str, Any]) -> str:
    all_row = (mode.get("summary") or {}).get("all") or {}
    n = int(all_row.get("n") or 0)
    text = (
        f"n={n} safety-critical={all_row.get('kill_switch_hits', 0)}/{all_row.get('kill_switch_expected', 0)} "
        f"false-alarms={all_row.get('kill_switch_false_alarms', 0)} "
        f"component={all_row.get('category_correct', 0)}/{all_row.get('category_expected', 0)} "
        f"errors={all_row.get('pipeline_errors', 0)}"
    )
    return text + (f"  {sample_label(n)}" if n < SMALL_N else "")


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Evaluate REAL Hindi/Hinglish/English complaints")
    p.add_argument("--data-dir", default=str(DEFAULT_DATA_DIR))
    p.add_argument("--labels", help="filled label sheet (default: <data-dir>/labels.csv)")
    p.add_argument("--out-dir", default=str(DEFAULT_OUT_DIR))
    p.add_argument("--approve-change",
                   help="record an approved lexicon/prompt/rules/eval change; marks the set no longer held-out")
    args = p.parse_args(argv)

    _isolate()
    data_dir = Path(args.data_dir).expanduser().resolve()
    labels_path = Path(args.labels).expanduser().resolve() if args.labels else data_dir / "labels.csv"
    out_dir = Path(args.out_dir).expanduser().resolve()
    state_path = data_dir / "eval_state.json"

    try:
        prior_runs = load_run_docs(out_dir)
        prior_state, recovered = recover_state(state_path, out_dir)
        if recovered:
            print("NOTE: eval state was recovered from run history; do not delete reports/real_hindi/runs/.")
        loaded = load_real_set(data_dir, labels_path)
        manifest = config_manifest()
        decision = guard_config(prior_state, manifest["hash"], args.approve_change)
        previous_labels = (prior_state or {}).get("last_labels_sha256")
        if not previous_labels and prior_runs:
            previous_labels = (prior_runs[-1].get("labels") or {}).get("sha256")
        meta_status, meta_model, meta_reason = meta_availability()
        runner = make_runner()
        evaluation = asyncio.run(evaluate(loaded["calls"], runner=runner, meta_status=meta_status))
        out = build_run(
            loaded=loaded,
            manifest=manifest,
            decision=decision,
            evaluation=evaluation,
            meta_status=meta_status,
            meta_model=meta_model,
            meta_reason=meta_reason,
            previous_labels_sha256=previous_labels,
        )
        run_id, run_dir, out = write_run(out_dir, out)
        state = save_state(
            state_path,
            config_hash=manifest["hash"],
            held_out=decision["held_out"],
            approval=decision["approval"],
            run_id=run_id,
            labels_sha256=loaded["labels"]["sha256"],
        )
        docs = load_run_docs(out_dir)
        _write_text_atomic(out_dir / "RUNS.md", render_runs_index(docs, state))
    except (ConfigChanged, DataError) as e:
        print(f"REFUSED: {e}", file=sys.stderr)
        return 3

    print(f"REAL set: {loaded['n_records']} record(s) from {loaded['source_dir']}")
    print(f"Labels: {loaded['labels']['path']} sha256={loaded['labels']['sha256'][:16]}...")
    for lang in LANGS:
        n = int(evaluation["n_by_language"].get(lang) or 0)
        print(f"  {lang}: n={n}  {sample_label(n)}")
    print(f"Config: {manifest['hash'][:16]}... held_out={'yes' if decision['held_out'] else 'NO'}")
    if decision.get("approval"):
        print(f"APPROVED CONFIG CHANGE: {decision['approval']['reason']}")
    for key in ("rules_only", "rules_plus_hindi"):
        print(f"{key}: {_mode_line(evaluation['modes'][key])}")
    if meta_status == "run":
        print(f"rules_plus_meta: {_mode_line(evaluation['modes']['rules_plus_meta'])}")
    else:
        print(f"rules_plus_meta: NOT RUN — {meta_reason}")
    print(f"Wrote {display_path(run_dir)}/REAL_HINDI_EVAL.md")
    print(f"Run history: {display_path(out_dir / 'RUNS.md')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

