"""Markdown reports for the REAL complaint eval.  [REAL-DATA]

The renderers use aggregate counters only.  They never receive a story string,
so a report cannot accidentally publish one.  Per-call ids/labels/results live
in the JSON next to the report, also without story text.
"""

from __future__ import annotations

import json
from typing import Any

from eval.real_hindi.common import (
    LANGS,
    MODE_TITLES,
    MODES,
    SMALL_N,
    fmt_severity,
    md_cell,
    sample_label,
)


def _metric_table(summary: dict[str, Any]) -> list[str]:
    lines = [
        "| Language | n | Severity counts | Triage skipped | Safety-critical hits / expected | Misses | False alarms | Component correct / expected | Component wrong | Pipeline errors | Sample |",
        "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for lang, r in summary.items():
        lines.append(
            f"| {lang} | {r['n']} | {fmt_severity(r['severity_counts'])} | {r['triage_skipped']} | "
            f"{r['kill_switch_hits']} / {r['kill_switch_expected']} | {r['kill_switch_misses']} | "
            f"{r['kill_switch_false_alarms']} | {r['category_correct']} / {r['category_expected']} | "
            f"{r['category_wrong']} | {r['pipeline_errors']} | {sample_label(r['n'])} |"
        )
    return lines


def _compare_table(compare: dict[str, Any]) -> list[str]:
    lines = [
        "| Language | n | n both scored | Severity agreement | Raises | Lowers (must be 0) | Meta calls | Meta failures (fell back) | Pipeline errors |",
        "| --- | --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for lang, c in compare.items():
        agreement = "n/a" if c["severity_agreement"] is None else f"{c['severity_agreement']} ({c['agree']}/{c['n_both_scored']})"
        lines.append(
            f"| {lang} | {c['n']} | {c['n_both_scored']} | {agreement} | {c['raises']} | {c['lowers']} | "
            f"{c['meta_calls']} | {c['meta_failures_fallback_to_rules']} | {c['pipeline_errors']} |"
        )
    return lines


def _sample_section(out: dict[str, Any]) -> list[str]:
    summary = ((out.get("modes") or {}).get("rules_only") or {}).get("summary") or {}
    lines = [
        "## Sample size",
        "",
        "| Language | n | Warning |",
        "| --- | --- | --- |",
    ]
    for lang in (*LANGS, "all"):
        n = int((summary.get(lang) or {}).get("n") or 0)
        lines.append(f"| {lang} | {n} | {sample_label(n)} |")
    lines += [
        "",
        f"`n < {SMALL_N}` is a sample-size floor, not a significance test. No confidence interval is computed and no row is an accuracy claim.",
        "",
    ]
    return lines


def _held_out_section(out: dict[str, Any]) -> list[str]:
    cfg = out.get("config") or {}
    lines = ["## Held-out status", ""]
    if cfg.get("held_out"):
        if cfg.get("first_run"):
            lines.append("**Held-out: yes.** This is the first real run for this configuration.")
        else:
            lines.append("**Held-out: yes.** The configuration hash matches the previous real run.")
    else:
        lines.append("**Held-out: NO.** This set is no longer held-out.")
        approval = cfg.get("approval") or {}
        if approval:
            lines += [
                "",
                f"An approved configuration change was recorded after earlier results:",
                "",
                f"- old config: `{approval.get('old_hash', '?')}`",
                f"- new config: `{approval.get('new_hash', '?')}`",
                f"- reason: {md_cell(approval.get('reason', ''))}",
            ]
        else:
            lines.append("A prior approved change is recorded in `RUNS.md`.")
        lines += ["", "Before and after numbers remain visible in `RUNS.md` and in each run directory.", ""]
    return lines


def _meta_not_run_table(out: dict[str, Any]) -> list[str]:
    summary = ((out.get("modes") or {}).get("rules_only") or {}).get("summary") or {}
    lines = [
        "| Language | n | Status |",
        "| --- | --- | --- |",
    ]
    for lang in (*LANGS, "all"):
        n = int((summary.get(lang) or {}).get("n") or 0)
        lines.append(f"| {lang} | {n} | not run |")
    return lines


def _config_section(out: dict[str, Any]) -> list[str]:
    cfg = out.get("config") or {}
    lines = [
        "## Configuration fingerprint",
        "",
        f"`sha256:{cfg.get('hash', '?')}`",
        "",
        "Files hashed for this fingerprint:",
        "",
        "```",
    ]
    for path, digest in sorted((cfg.get("files") or {}).items()):
        lines.append(f"{digest}  {path}")
    lines += ["```", "", "Model settings (no API key is read or written):", "", "```json"]
    lines.append(json.dumps(cfg.get("settings") or {}, indent=2, sort_keys=True))
    lines += ["```", ""]
    return lines


def render_report(out: dict[str, Any]) -> str:
    if out.get("synthetic") is not False:
        raise ValueError("refusing to render a real-data report for a non-real record set")
    ds = out.get("dataset") or {}
    labels = out.get("labels") or {}
    meta = out.get("meta") or {}
    modes = out.get("modes") or {}
    run_id = out.get("run_id") or "(pending)"
    L = [
        "# Real Hindi / Hinglish / English complaints: rules-only vs rules + hindi_safety vs rules + Meta",
        "",
        "**REAL human-collected data. Not synthetic.** This file is kept separate from every synthetic eval",
        "(`eval/enhanced/`, `eval/hindi_fresh/`, `reports/hindi_safety/`, `reports/eval_modes/`).",
        "",
        "## Run",
        "",
        f"- Run id: `{run_id}`",
        f"- Generated: {out.get('generated_at', '?')}",
        f"- Source: `{ds.get('source_dir', '?')}`",
        f"- Records: {ds.get('records', 0)} ({ds.get('text_records', 0)} text, {ds.get('audio_records', 0)} audio)",
        f"- Audio seconds stored: {ds.get('audio_seconds_total', 0)}",
        f"- Consent versions verified: {', '.join(ds.get('consent_versions') or []) or 'none'}",
        f"- Reported-language vs label mismatch: {ds.get('reported_language_mismatch', 0)}",
        f"- Label sheet: `{labels.get('path', '?')}`",
        f"- Label sheet sha256: `{labels.get('sha256', '?')}`",
        f"- Human labels: {labels.get('usable', 0)} / {labels.get('rows', 0)} usable",
        "",
    ]
    if labels.get("changed_since_previous"):
        L += [
            "> **Label sheet changed since the previous run.** The numbers below are a new run, not a",
            "> continuation of the earlier numbers. Compare them in `RUNS.md` with that difference in mind.",
            "",
        ]
    L += _sample_section(out)
    L += _held_out_section(out)

    L += ["## Rules only", ""]
    L += _metric_table(modes.get("rules_only", {}).get("summary") or {})
    L += [""]

    L += ["## Rules + hindi_safety", ""]
    L += _metric_table(modes.get("rules_plus_hindi", {}).get("summary") or {})
    lowers = modes.get("rules_plus_hindi", {}).get("lowers", 0)
    L += ["", f"Severity lowers vs rules-only (must be 0): **{lowers}**", ""]

    L += ["## Rules + Meta", ""]
    meta_mode = modes.get("rules_plus_meta") or {}
    if meta_mode.get("status") == "run":
        L += [
            f"Meta ran with model `{meta.get('model', '?')}`. The text sent to Meta is the story after the existing",
            "regex PII redaction; audio is never sent. This is the enhanced path without the deterministic hindi_safety",
            "layer, so the three rows differ by one addition at a time.",
            "",
        ]
        L += _metric_table(meta_mode.get("summary") or {})
        L += ["", "Rules + Meta vs rules-only:", ""]
        L += _compare_table(meta_mode.get("compare") or {})
    else:
        L += [
            f"**NOT RUN.** {meta.get('reason') or 'Meta is not configured.'}",
            "",
            "No Meta number is reported or estimated. Coverage for this mode:",
            "",
        ]
        L += _meta_not_run_table(out)
    L += [""]
    L += _config_section(out)
    L += [
        "## What this does and does not measure",
        "",
        "- The human `is_safety_critical` label is the reference for the kill-switch hits, misses and false alarms.",
        "  It is a participant-level judgment, not an engineering safety assessment.",
        "- The human `component` label is the reference for the category column. `Component wrong` counts a",
        "  non-empty predicted category that differs from it; missing predictions are in neither correct nor wrong.",
        "- There is no human severity label in the sheet, so no severity accuracy is claimed. Severity counts are",
        "  descriptive only.",
        "- The eval calls intake and triage directly; it does not execute the orchestrator's escalation fast path.",
        "- Labels are one person's judgment. There is no inter-annotator agreement and no confidence interval.",
        "- This is a convenience sample, not production traffic. `n < 30` is flagged as too small to conclude.",
        "- Reports contain no story text. Raw stories and audio stay under the gitignored `data/real_hindi/`.",
        "",
        f"Generated by `eval/real_hindi/run_eval.py`. Raw per-call metrics (no story text) are in "
        f"`runs/{run_id}/real_hindi_eval.json`.",
        "",
    ]
    return "\n".join(L)


def _run_metrics_table(doc: dict[str, Any]) -> list[str]:
    lines = [
        "| Mode | Language | n | Safety hits / expected | Misses | False alarms | Component correct / expected | Errors |",
        "| --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    modes = doc.get("modes") or {}
    for mode in MODES:
        m = modes.get(mode) or {}
        title = MODE_TITLES[mode]
        if m.get("status") != "run":
            lines.append(f"| {title} | all | not run | not run | not run | not run | not run | not run |")
            continue
        summary = m.get("summary") or {}
        for lang, r in summary.items():
            n = f"{r['n']} (too small to conclude)" if r["n"] < SMALL_N else str(r["n"])
            lines.append(
                f"| {title} | {lang} | {n} | {r['kill_switch_hits']} / {r['kill_switch_expected']} | "
                f"{r['kill_switch_misses']} | {r['kill_switch_false_alarms']} | "
                f"{r['category_correct']} / {r['category_expected']} | {r['pipeline_errors']} |"
            )
    return lines


def render_runs_index(docs: list[dict[str, Any]], state: dict[str, Any] | None) -> str:
    L = [
        "# Real complaint eval: run history",
        "",
        "**REAL human-collected data only.** Synthetic results are not included here and are never combined with these numbers.",
        "",
    ]
    if state:
        L += [
            "## Current held-out state",
            "",
            f"- Current config: `{state.get('config_hash', '?')}`",
            f"- Held-out: **{'yes' if state.get('held_out') else 'NO'}**",
            f"- Last run: `{state.get('last_run_id') or '(none)'}`",
            f"- Label sheet sha256: `{state.get('last_labels_sha256') or '(none)'}`",
        ]
        approvals = state.get("approvals") or []
        if approvals:
            L += ["", "Approved configuration changes:"]
            for approval in approvals:
                L.append(
                    f"- {approval.get('at', '?')}: {md_cell(approval.get('reason', ''))} "
                    f"(`{str(approval.get('old_hash', '?'))[:12]}...` -> `{str(approval.get('new_hash', '?'))[:12]}...`)"
                )
        L += [""]
    else:
        L += ["No eval state is present. No held-out status is claimed.", ""]

    if not docs:
        L += ["No real eval runs have been recorded.", ""]
        return "\n".join(L)

    L += [
        "## Runs",
        "",
        "| Run | Generated | Records | Config | Held-out | Labels sha256 | Meta | Report |",
        "| --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for doc in docs:
        cfg = doc.get("config") or {}
        labels = doc.get("labels") or {}
        meta = doc.get("meta") or {}
        run_id = doc.get("run_id")
        L.append(
            f"| `{run_id}` | {doc.get('generated_at', '?')} | {(doc.get('dataset') or {}).get('records', 0)} | "
            f"`{str(cfg.get('hash', '?'))[:12]}...` | {'yes' if cfg.get('held_out') else 'NO'} | "
            f"`{str(labels.get('sha256', '?'))[:12]}...` | "
            f"{'run' if meta.get('status') == 'run' else 'NOT RUN'} | "
            f"[report](runs/{run_id}/REAL_HINDI_EVAL.md) |"
        )
    L += [""]

    L += ["## Per-run metrics", ""]
    previous_labels: str | None = None
    for doc in docs:
        cfg = doc.get("config") or {}
        labels = doc.get("labels") or {}
        labels_sha = labels.get("sha256")
        L += [f"### `{doc.get('run_id')}`", ""]
        if cfg.get("approval"):
            approval = cfg["approval"]
            L += [
                f"Approved change: {md_cell(approval.get('reason', ''))} "
                f"(`{str(approval.get('old_hash', '?'))[:12]}...` -> `{str(approval.get('new_hash', '?'))[:12]}...`).",
                "",
            ]
        if previous_labels and labels_sha and labels_sha != previous_labels:
            L += [
                "> **Label sheet differs from the previous run.** These numbers are not directly comparable to it.",
                "",
            ]
        previous_labels = labels_sha or previous_labels
        L += _run_metrics_table(doc)
        meta = doc.get("meta") or {}
        if meta.get("status") != "run":
            reason = str(meta.get("reason") or "not configured").rstrip(".")
            L += ["", f"Meta: NOT RUN — {reason}."]
        hindi = (doc.get("modes") or {}).get("rules_plus_hindi") or {}
        if hindi.get("status") == "run":
            L += ["", f"Hindi lowers vs rules-only (must be 0): **{hindi.get('lowers', 0)}**."]
        L += [""]

    L += [
        "Reports and run JSON contain ids, labels and outputs only; no story text. Raw stories stay under `data/real_hindi/`.",
        "",
    ]
    return "\n".join(L)


__all__ = ["render_report", "render_runs_index"]
