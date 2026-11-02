"""Validation contracts only. All files below are synthetic fixtures, never study data."""
import copy
import json

import pytest

from scripts import voice_validation as vv


def write_json(path, value):
    path.write_text(json.dumps(value))
    return {"path": path.name, "sha256": vv.digest(path)}


@pytest.fixture
def collection(tmp_path):
    # An explicit test-only attestation exercises validation; it is not a real person.
    (tmp_path / "test.raw").write_bytes(b"synthetic-test-audio" * 20)
    consent = {"accepted": True, "version": vv.VERSION, "text_sha256": vv.CONSENT_HASH,
               "participant_code": "fixture", "agreed_at": "2026-10-30T08:00:00Z", "collector": "test fixture",
               "collector_contact": "not a real study", "delete_after": "after test", "allowed_providers": ["fixture"]}
    timing = {"turn_id": "test-turn", "source_kind": "observed_playback", "observer": "test fixture",
              "clock_basis": "single_monotonic_clock", "events": {"end_of_speech_ms": 1000, "first_audible_response_ms": 1800}}
    turn = {"id": "test-turn", "session_id": "fixture", "participant_code": "fixture", "source_kind": "real_microphone", "synthetic": False,
            "language": "Hindi", "device": "fixture", "browser_version": "fixture", "audio_path": "headset", "noise_condition": "fixture",
            "captured_at": "2026-10-30T08:01:00Z", "code_revision": "fixture",
            "recording": {"path": "test.raw", "sha256": vv.digest(tmp_path / "test.raw")},
            "consent": write_json(tmp_path / "consent.json", consent), "timing_evidence": write_json(tmp_path / "timing.json", timing),
            "provider_evidence": write_json(tmp_path / "provider.json", {"synthetic_fixture": True}),
            "providers": {stage: {"name": "fixture", "model": "fake", "version_evidence": "fixture"} for stage in ("stt", "reply", "tts")},
            "outcome": "completed", "human_grade": None}
    return tmp_path, turn


def analyze_fixture(root, turns):
    manifest = root / "manifest.json"
    write_json(manifest, {"schema_version": vv.VERSION, "turns": turns})
    return vv.analyze(manifest)


def test_empty_manifest_does_not_invent_real_audio_results(tmp_path):
    result = analyze_fixture(tmp_path, [])
    assert result["status"] == "pending_real_audio"
    assert result["participants"] == result["human_graded_turns"] == 0
    assert result["end_of_speech_to_first_audible_response"]["p50_ms"] is None


def test_rejects_synthetic_stale_sources_and_text_only_consent(collection):
    root, turn = collection
    for value in (True, None):
        with pytest.raises(ValueError, match="synthetic"):
            analyze_fixture(root, [{**turn, "synthetic": value}])
    with pytest.raises(ValueError, match="missing or changed"):
        analyze_fixture(root, [{**turn, "recording": {"path": "test.raw", "sha256": "stale"}}])
    consent = json.loads((root / "consent.json").read_text())
    consent["version"] = "real-hindi-v1"
    turn["consent"] = write_json(root / "consent.json", consent)
    with pytest.raises(ValueError, match="text-only consent"):
        analyze_fixture(root, [turn])


def test_timing_must_be_audible_and_failures_stay_in_denominator(collection):
    root, turn = collection
    trace = json.loads((root / "timing.json").read_text())
    trace["source_kind"] = "offline_simulated"
    turn["timing_evidence"] = write_json(root / "timing.json", trace)
    with pytest.raises(ValueError, match="observed audible"):
        analyze_fixture(root, [turn])
    trace["source_kind"] = "observed_playback"
    trace["events"]["first_audible_response_ms"] = None
    turn["timing_evidence"] = write_json(root / "timing.json", trace)
    turn.update(outcome="failed", failure_category="stt_timeout")
    result = analyze_fixture(root, [turn])
    assert result["outcomes"]["failed"] == 1
    assert result["ungraded_turns"] == 1
    assert result["end_of_speech_to_first_audible_response"]["missing_or_no_audible_response"] == 1


def test_provider_scope_and_path_escape_are_rejected(collection, tmp_path_factory):
    root, turn = collection
    unconsented = copy.deepcopy(turn)
    unconsented["providers"]["stt"]["name"] = "unconsented-provider"
    with pytest.raises(ValueError, match="not covered"):
        analyze_fixture(root, [unconsented])
    outside = tmp_path_factory.mktemp("elsewhere") / "private.raw"
    outside.write_bytes(b"private" * 10)
    with pytest.raises(ValueError, match="within the private"):
        analyze_fixture(root, [{**turn, "recording": {"path": str(outside), "sha256": vv.digest(outside)}}])


def test_small_samples_do_not_emit_tail_latency_or_accuracy(collection):
    root, turn = collection
    result = analyze_fixture(root, [turn])
    assert result["end_of_speech_to_first_audible_response"]["p50_ms"] is None
    assert result["critical_entities"]["denominator"] == 0
    assert vv.latency_summary([800] * 5)["p50_ms"] == 800
    assert vv.latency_summary([800] * 39)["p95_ms"] is None
    assert vv.latency_summary([800] * 40)["p95_ms"] == 800
