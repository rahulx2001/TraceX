#!/usr/bin/env python3
"""Local, consent-gated real microphone evaluation; never records or calls a provider.

init creates an empty private collection. analyze checks linked evidence and emits
aggregates only. An attestation cannot establish that a person really participated;
retain the private source records for an independent review.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import re


VERSION = "voice-validation-v1"
CONSENT_TEXT = """TraceX voice evaluation — version voice-validation-v1
Participation is voluntary. This is a software evaluation, not a repair service.
Use a fictional vehicle identifier and omit names, phone numbers, VINs and plates.
I agree to the local recording of my microphone and the device's audible response,
and to independent human review of the recording, transcript and turn timing.
The collector must identify the speech path before I agree: browser speech may
send audio to the browser vendor; Deepgram server speech sends audio to Deepgram.
Only the providers listed in my consent record may receive my audio or transcript.
I may instead choose local-only recording and transcription with no provider.
The private recordings and exact transcripts stay outside the public repository.
Only aggregate results will be shared. I may stop before submitting and request
deletion later using my anonymous participant code. The collector must provide
a contact and retention/deletion date before collection. No benefit is promised.
"""
CONSENT_HASH = hashlib.sha256(CONSENT_TEXT.encode()).hexdigest()
FIELDS = {"negation", "date", "model_year", "vehicle_name", "part", "correction", "other"}
EVENTS = ("end_of_speech_ms", "first_audible_response_ms")
OUTCOMES = ("completed", "fallback", "failed")


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def checked_file(root: Path, item: dict) -> Path:
    name, expected = item.get("path"), item.get("sha256")
    if not isinstance(name, str) or not name or not isinstance(expected, str):
        raise ValueError("each source file needs a relative path and sha256")
    path = (root / name).resolve()
    if Path(name).is_absolute() or not path.is_relative_to(root.resolve()):
        raise ValueError("source file must remain within the private collection")
    if not path.is_file() or digest(path) != expected:
        raise ValueError(f"source file missing or changed: {name}")
    return path


def required_text(obj: dict, *keys: str) -> None:
    for key in keys:
        if not isinstance(obj.get(key), str) or not obj[key].strip():
            raise ValueError(f"missing {key}")


def number(value) -> bool:
    return isinstance(value, (float, int)) and not isinstance(value, bool) and math.isfinite(value) and value >= 0


def validate_turn(root: Path, turn: dict, seen: set) -> dict:
    required_text(turn, "id", "session_id", "participant_code", "language", "device", "browser_version", "audio_path", "noise_condition", "captured_at", "code_revision")
    if not re.fullmatch(r"[A-Za-z0-9_-]{1,80}", turn["id"]) or turn["id"] in seen:
        raise ValueError("turn id must be unique and contain only letters, numbers, underscores or hyphens")
    seen.add(turn["id"])
    if turn.get("source_kind") != "real_microphone" or turn.get("synthetic") is not False:
        raise ValueError("real-audio analysis rejects synthetic, replayed and unspecified microphone origin")
    if turn.get("language") not in {"English", "Hindi", "Hinglish"}:
        raise ValueError("language must describe the actual utterance")
    if turn.get("audio_path") not in {"headset", "laptop_speakers", "bluetooth", "other"}:
        raise ValueError("unknown hardware audio path")
    recording = checked_file(root, turn.get("recording", {}))
    if recording.stat().st_size <= 44:
        raise ValueError("recording has no measurable audio")
    # Timing evidence and actual output are retained even on failures; an observer
    # may use a loopback recording or a synchronized recording of speaker output.
    trace_path = checked_file(root, turn.get("timing_evidence", {}))
    trace = json.loads(trace_path.read_text())
    if trace.get("turn_id") != turn["id"] or trace.get("source_kind") not in {"observed_playback", "loopback_audio"}:
        raise ValueError("timing must identify this turn and observed audible playback, not simulated/request timing")
    required_text(trace, "observer", "clock_basis")
    if trace.get("clock_basis") not in {"same_recording_timeline", "single_monotonic_clock"}:
        raise ValueError("timing events must share one clock")
    if trace.get("source_kind") == "loopback_audio":
        checked_file(root, trace.get("playback_recording", {}))
    consent_path = checked_file(root, turn.get("consent", {}))
    consent = json.loads(consent_path.read_text())
    if consent.get("accepted") is not True or consent.get("version") != VERSION or consent.get("text_sha256") != CONSENT_HASH:
        raise ValueError("missing matching, affirmative voice-provider consent; text-only consent is insufficient")
    required_text(consent, "participant_code", "agreed_at", "collector", "collector_contact", "delete_after")
    if consent["participant_code"] != turn["participant_code"]:
        raise ValueError("consent belongs to another participant")
    try:
        agreed = datetime.fromisoformat(consent["agreed_at"].replace("Z", "+00:00"))
        captured = datetime.fromisoformat(turn["captured_at"].replace("Z", "+00:00"))
        if agreed.tzinfo is None or captured.tzinfo is None or agreed > captured:
            raise ValueError("consent must precede capture with timezone-aware timestamps")
    except (TypeError, ValueError) as exc:
        raise ValueError("invalid consent/capture order or timestamp") from exc
    providers = turn.get("providers", {})
    if not isinstance(consent.get("allowed_providers"), list) or not providers:
        raise ValueError("the actual providers and permitted provider list are required")
    for stage in ("stt", "reply", "tts"):
        provider = providers.get(stage, {})
        required_text(provider, "name", "model", "version_evidence")
        if provider["name"] not in consent["allowed_providers"]:
            raise ValueError(f"{stage} provider was not covered by consent")
    checked_file(root, turn.get("provider_evidence", {}))
    # A first-party/browser model may be undisclosed: record that explicitly in
    # model/version_evidence instead of inventing a version identifier.
    outcome = turn.get("outcome")
    if outcome not in OUTCOMES:
        raise ValueError("outcome must be completed, fallback or failed")
    if outcome != "completed":
        required_text(turn, "failure_category")
    events = trace.get("events", {})
    end, audible = (events.get(key) for key in EVENTS)
    if end is not None and not number(end) or audible is not None and not number(audible):
        raise ValueError("timing events must be nonnegative measured milliseconds or null")
    if audible is not None and (end is None or audible < end):
        raise ValueError("audible response must follow end of speech on the same clock")
    latency = audible - end if audible is not None else None
    grade_ref = turn.get("human_grade")
    grade = None
    if grade_ref is not None:
        grade = json.loads(checked_file(root, grade_ref).read_text())
        required_text(grade, "reviewer", "expertise", "graded_at", "reference_transcript", "recognized_transcript")
        if grade.get("turn_id") != turn["id"] or grade.get("human_attested") is not True or grade.get("reference_source") != "listened_to_recording":
            raise ValueError("grading requires a human attestation and independently heard reference")
        for field in ("correction_success", "interruption_success", "repetition", "endpointing_error", "agent_echo"):
            if grade.get(field) is not None and not isinstance(grade[field], bool):
                raise ValueError(f"{field} must be true, false or null (not exercised/ungraded)")
        entities = grade.get("critical_entities")
        if not isinstance(entities, list):
            raise ValueError("critical_entities must be an independently graded list")
        for entity in entities:
            if entity.get("field") not in FIELDS or entity.get("result") not in {"correct", "incorrect", "omitted", "unknown"}:
                raise ValueError("invalid critical entity field/result")
            required_text(entity, "expected", "observed")
    return {**turn, "latency_ms": latency, "grade": grade}


def latency_summary(values: list[float]) -> dict:
    values = sorted(values)
    def quantile(p):
        at = (len(values) - 1) * p
        low = math.floor(at)
        return round(values[low] + (values[math.ceil(at)] - values[low]) * (at - low), 1)
    return {"n": len(values), "p50_ms": quantile(.5) if len(values) >= 5 else None,
            "p95_ms": quantile(.95) if len(values) >= 40 else None,
            "suppression_rule": "p50 needs >=5 audible turns; p95 needs >=40. These thresholds do not establish representativeness."}


def analyze(manifest_path: Path) -> dict:
    manifest = json.loads(manifest_path.read_text())
    if manifest.get("schema_version") != VERSION or not isinstance(manifest.get("turns"), list):
        raise ValueError("unsupported or missing manifest schema")
    seen = set()
    rows = [validate_turn(manifest_path.parent, turn, seen) for turn in manifest["turns"]]
    outcomes = Counter(r["outcome"] for r in rows)
    groups = defaultdict(list)
    entity = Counter()
    by_field = defaultdict(Counter)
    graded = [r for r in rows if r["grade"] is not None]
    for row in rows:
        groups[f'{row["language"]} / {row["audio_path"]}'].append(row)
        for item in (row["grade"] or {}).get("critical_entities", []):
            entity[item["result"]] += 1
            by_field[item["field"]][item["result"]] += 1
    def measurements(items):
        values = [r["latency_ms"] for r in items if r["latency_ms"] is not None]
        return {**latency_summary(values), "missing_or_no_audible_response": len(items) - len(values)}
    observed = {}
    for field in ("correction_success", "interruption_success", "repetition", "endpointing_error", "agent_echo"):
        known = [r["grade"][field] for r in graded if r["grade"].get(field) is not None]
        observed[field] = {"true": sum(known), "false": len(known) - sum(known), "denominator": len(known), "not_exercised_or_ungraded": len(rows) - len(known)}
    return {"schema_version": VERSION, "generated_at": datetime.now(timezone.utc).isoformat(),
            "status": "pending_real_audio" if not rows else "observed_sample_only",
            "scope": "Consented microphone recordings and human attestations, not simulated timing; independent audit still required.",
            "manifest_sha256": digest(manifest_path), "turns": len(rows),
            "participants": len({r["participant_code"] for r in rows}), "sessions": len({r["session_id"] for r in rows}),
            "outcomes": {key: outcomes[key] for key in OUTCOMES},
            "failure_categories": dict(Counter(r["failure_category"] for r in rows if r["outcome"] != "completed")),
            "end_of_speech_to_first_audible_response": measurements(rows),
            "groups": {key: {"turns": len(items), **measurements(items)} for key, items in sorted(groups.items())},
            "human_graded_turns": len(graded), "ungraded_turns": len(rows) - len(graded),
            "critical_entities": {"results": dict(entity), "denominator": sum(entity.values()), "by_field": {key: dict(value) for key, value in by_field.items()}},
            "observations": observed,
            "limits": ["No recording or reviewer is created by this tool.", "Provider timestamps/HTTP completion are not audible response timing.", "Failures and ungraded turns remain in denominators.", "Repeating one participant or fixture cannot establish device/language population performance."]}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    subs = parser.add_subparsers(dest="command", required=True)
    init = subs.add_parser("init")
    init.add_argument("directory", type=Path)
    analysis = subs.add_parser("analyze")
    analysis.add_argument("manifest", type=Path)
    analysis.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.command == "init":
        args.directory.mkdir(parents=True, exist_ok=True)
        source = {"path": "", "sha256": ""}
        templates = {
            "manifest.json": {"schema_version": VERSION, "turns": []},
            "turn.template.json": {
                "id": "", "session_id": "", "participant_code": "", "source_kind": "", "synthetic": None,
                "language": "", "device": "", "browser_version": "", "audio_path": "", "noise_condition": "", "captured_at": "", "code_revision": "",
                "recording": source, "timing_evidence": source, "consent": source, "provider_evidence": source,
                "providers": {stage: {"name": "", "model": "", "version_evidence": ""} for stage in ("stt", "reply", "tts")},
                "outcome": "", "failure_category": "", "human_grade": None},
            "consent.template.json": {"accepted": False, "version": VERSION, "text_sha256": CONSENT_HASH,
                "participant_code": "", "agreed_at": "", "collector": "", "collector_contact": "", "delete_after": "", "allowed_providers": []},
            "timing.template.json": {"turn_id": "", "source_kind": "", "observer": "", "clock_basis": "", "events": {key: None for key in EVENTS}},
            "grade.template.json": {"turn_id": "", "reviewer": "", "expertise": "", "graded_at": "", "human_attested": False,
                "reference_source": "", "reference_transcript": "", "recognized_transcript": "", "critical_entities": [],
                **{key: None for key in ("correction_success", "interruption_success", "repetition", "endpointing_error", "agent_echo")}},
        }
        contents = {name: json.dumps(obj, indent=2) + "\n" for name, obj in templates.items()}
        contents["consent.txt"] = CONSENT_TEXT
        for name, content in contents.items():
            with (args.directory / name).open("x") as handle:
                handle.write(content)
        print(f"Empty collection created; consent text SHA-256: {CONSENT_HASH}")
    else:
        result = analyze(args.manifest)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(result, indent=2) + "\n")
        print(f'{result["status"]}: {result["turns"]} turns, {result["human_graded_turns"]} human-graded')


if __name__ == "__main__":
    main()
