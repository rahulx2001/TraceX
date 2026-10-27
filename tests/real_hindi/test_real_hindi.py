"""Tests for the REAL complaint pipeline.  [REAL-DATA]

Fixtures here are synthetic test records marked ``"synthetic": false`` only to
exercise the real-data contract in a temp directory.  They are never written
under the repository's ``data/real_hindi/`` and no result is claimed from them.
"""

from __future__ import annotations

import csv
import json
import re
import shutil
import subprocess
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from eval.real_hindi.common import sha256_text
from eval.real_hindi.consent import CONSENT_SHA256, CONSENT_TEXT, CONSENT_VERSION
from eval.real_hindi.labels import (
    EXPORT_COLUMNS,
    TEMPLATE_COLUMNS,
    DataError,
    check_labels,
    export_labels,
)
from scripts.real_hindi_collect import (
    _tags_present,
    audio_support,
    create_app,
    ensure_layout,
    load_records,
    probe_audio,
    transcode_audio,
    write_json_atomic,
)

ID1 = "rh_20261026_aaaaaaaa"
ID2 = "rh_20261026_bbbbbbbb"


def _record(data_dir: Path, rid: str, narrative: str = "The brakes failed on the highway.",
            **overrides) -> dict:
    record = {
        "id": rid,
        "schema_version": 1,
        "collection": "local_consent_page_v1",
        "created_at": "2026-10-26T10:00:00+00:00",
        "synthetic": False,
        "consent": True,
        "consent_version": CONSENT_VERSION,
        "consent_text_sha256": CONSENT_SHA256,
        "consent_at": "2026-10-26T10:00:00+00:00",
        "ai_processing_consent": True,
        "no_identifiers_confirmed": True,
        "reported_language": "hindi",
        "input_type": "text",
        "narrative": narrative,
        "narrative_chars": len(narrative),
        "narrative_sha256": sha256_text(narrative),
        "transcript_source": "typed",
        "audio_file": None,
        "audio_seconds": None,
        "audio_sha256": None,
        "audio_format": None,
        "audio_sample_rate": None,
        "audio_channels": None,
        "audio_metadata_stripped": None,
    }
    record.update(overrides)
    if "narrative" in overrides:
        record["narrative_chars"] = len(record["narrative"])
        record["narrative_sha256"] = sha256_text(record["narrative"])
    write_json_atomic(data_dir / "records" / f"{rid}.json", record)
    return record


def _labels_file(data_dir: Path, rows: list[dict[str, str]]) -> Path:
    path = data_dir / "labels.csv"
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=TEMPLATE_COLUMNS, lineterminator="\n")
        writer.writeheader()
        for row in rows:
            writer.writerow({key: row.get(key, "") for key in TEMPLATE_COLUMNS})
    return path


def _label(rid: str = ID1, language: str = "hindi", safety: str = "yes",
           component: str = "SERVICE BRAKES", notes: str = "") -> dict[str, str]:
    return {"id": rid, "language": language, "is_safety_critical": safety,
            "component": component, "notes": notes}


def _valid_set(tmp_path: Path, narrative: str = "The brakes failed on the highway.") -> tuple[Path, Path]:
    data_dir = tmp_path / "data"
    ensure_layout(data_dir)
    _record(data_dir, ID1, narrative)
    labels = _labels_file(data_dir, [_label()])
    return data_dir, labels


def _mp3_with_tags(path: Path) -> bool:
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        return False
    proc = subprocess.run(
        [ffmpeg, "-nostdin", "-y", "-f", "lavfi", "-i", "sine=frequency=440:duration=1.2",
         "-c:a", "libmp3lame", "-metadata", "title=SECRET_TITLE", "-metadata", "artist=SECRET_ARTIST",
         str(path)],
        capture_output=True, text=True, check=False,
    )
    return proc.returncode == 0


# ── Consent page / collector ─────────────────────────────────────────────────


def test_page_shows_consent_and_does_not_precheck_checkboxes(tmp_path: Path):
    app = create_app(tmp_path / "data", csrf_token="tok", audio_ok=False)
    client = TestClient(app)
    response = client.get("/")
    assert response.status_code == 200
    assert "Describe a real problem you or your family had with a car or bike" in response.text
    assert CONSENT_TEXT.split("\n\n")[0] in response.text
    assert not re.search(r'<input[^>]*name="consent"[^>]*checked', response.text)
    assert not re.search(r'<input[^>]*name="no_identifiers"[^>]*checked', response.text)
    assert 'name="consent"' in response.text and 'name="no_identifiers"' in response.text
    assert response.headers["cache-control"] == "no-store"
    assert response.headers["x-frame-options"] == "DENY"
    assert "default-src 'none'" in response.headers["content-security-policy"]


def test_consent_text_endpoint_matches_registry(tmp_path: Path):
    app = create_app(tmp_path / "data", csrf_token="tok", audio_ok=False)
    response = TestClient(app).get("/consent.txt")
    assert response.status_code == 200
    assert CONSENT_VERSION in response.text
    assert CONSENT_SHA256 in response.text
    assert "Describe a real problem" not in response.text  # consent text, not instructions


def test_submission_with_bad_csrf_is_refused(tmp_path: Path):
    data_dir = tmp_path / "data"
    app = create_app(data_dir, csrf_token="tok", audio_ok=False)
    response = TestClient(app).post("/submit", data={
        "csrf": "wrong", "reported_language": "hindi", "text": "The brakes failed on the highway.",
        "consent": "yes", "no_identifiers": "yes",
    })
    assert response.status_code == 403
    assert load_records(data_dir) == []


def test_submission_without_consent_is_refused(tmp_path: Path):
    data_dir = tmp_path / "data"
    app = create_app(data_dir, csrf_token="tok", audio_ok=False)
    response = TestClient(app).post("/submit", data={
        "csrf": "tok", "reported_language": "hindi", "text": "The brakes failed on the highway.",
        "no_identifiers": "yes",
    })
    assert response.status_code == 400
    assert load_records(data_dir) == []


def test_submission_without_no_identifiers_confirmation_is_refused(tmp_path: Path):
    data_dir = tmp_path / "data"
    app = create_app(data_dir, csrf_token="tok", audio_ok=False)
    response = TestClient(app).post("/submit", data={
        "csrf": "tok", "reported_language": "hindi", "text": "The brakes failed on the highway.",
        "consent": "yes",
    })
    assert response.status_code == 400
    assert load_records(data_dir) == []


def test_valid_text_submission_stores_consent_and_no_identifying_fields(tmp_path: Path):
    data_dir = tmp_path / "data"
    app = create_app(data_dir, csrf_token="tok", audio_ok=False)
    story = "The brakes failed on the highway and the pedal went to the floor."
    response = TestClient(app).post("/submit", data={
        "csrf": "tok", "reported_language": "hinglish", "text": story,
        "consent": "yes", "no_identifiers": "yes",
    })
    assert response.status_code == 200
    assert "Your story was saved" in response.text
    records = load_records(data_dir)
    assert len(records) == 1
    record = records[0]
    assert record["synthetic"] is False
    assert record["consent"] is True
    assert record["consent_version"] == CONSENT_VERSION
    assert record["consent_text_sha256"] == CONSENT_SHA256
    assert record["ai_processing_consent"] is True
    assert record["no_identifiers_confirmed"] is True
    assert record["narrative"] == story
    assert record["narrative_sha256"] == sha256_text(story)
    assert record["input_type"] == "text"
    assert record["audio_file"] is None
    assert not ({"name", "phone", "number_plate", "plate", "ip"} & set(record))
    record_path = data_dir / "records" / f"{record['id']}.json"
    assert oct(record_path.stat().st_mode & 0o777) == "0o600"
    assert oct((data_dir / "records").stat().st_mode & 0o777) == "0o700"


def test_uploaded_audio_is_stored_as_metadata_free_mono_wav(tmp_path: Path):
    if not audio_support():
        pytest.skip("ffmpeg/ffprobe not installed")
    data_dir = tmp_path / "data"
    source = tmp_path / "secret-name.mp3"
    if not _mp3_with_tags(source):
        pytest.skip("ffmpeg cannot encode an mp3 with tags on this machine")
    before = probe_audio(source)
    assert _tags_present(before), "test source did not carry tags; cannot prove stripping"
    app = create_app(data_dir, csrf_token="tok", audio_ok=True)
    with source.open("rb") as fh:
        response = TestClient(app).post("/submit", data={
            "csrf": "tok", "reported_language": "hindi", "text": "",
            "consent": "yes", "no_identifiers": "yes",
        }, files={"audio": ("secret-name.mp3", fh, "audio/mpeg")})
    assert response.status_code == 200
    record = load_records(data_dir)[0]
    assert record["input_type"] == "audio"
    assert record["transcript_source"] == "none"
    assert record["narrative"] == ""
    assert record["audio_metadata_stripped"] is True
    assert record["audio_format"] == "wav"
    assert record["audio_sample_rate"] == 16000
    assert record["audio_channels"] == 1
    assert record["audio_file"].endswith(".wav")
    assert "secret-name" not in json.dumps(record)
    stored = data_dir / record["audio_file"]
    assert stored.is_file()
    assert oct(stored.stat().st_mode & 0o777) == "0o600"
    after = probe_audio(stored)
    assert not _tags_present(after)
    assert after["streams"][0]["sample_rate"] == "16000"
    assert after["streams"][0]["channels"] == 1


def test_too_short_audio_is_refused(tmp_path: Path):
    if not audio_support():
        pytest.skip("ffmpeg/ffprobe not installed")
    ffmpeg = shutil.which("ffmpeg")
    source = tmp_path / "short.wav"
    proc = subprocess.run(
        [ffmpeg, "-nostdin", "-y", "-f", "lavfi", "-i", "sine=frequency=440:duration=0.1",
         "-ar", "16000", "-ac", "1", str(source)],
        capture_output=True, text=True, check=False,
    )
    if proc.returncode != 0:
        pytest.skip("ffmpeg could not build the short fixture")
    from scripts.real_hindi_collect import AudioError

    with pytest.raises(AudioError):
        transcode_audio(source, tmp_path / "out.wav")


# ── Human label sheet ───────────────────────────────────────────────────────


def _write_rows(path: Path, rows: list[dict[str, str]], fields: list[str]) -> None:
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def _read_rows(path: Path) -> tuple[list[dict[str, str]], list[str]]:
    with path.open(encoding="utf-8-sig", newline="") as fh:
        reader = csv.DictReader(fh)
        return [dict(row) for row in reader], list(reader.fieldnames or [])


def test_labels_template_is_header_only():
    path = Path(__file__).resolve().parents[2] / "eval" / "real_hindi" / "labels_template.csv"
    assert path.read_text(encoding="utf-8").splitlines() == [
        "id,language,is_safety_critical,component,notes"
    ]


def test_export_writes_blank_labels_and_refuses_to_overwrite_filled_sheet(tmp_path: Path):
    data_dir, labels_path = _valid_set(tmp_path, narrative="The brakes failed on the highway.")
    labels_path.unlink()  # a fresh collection has records but no working label sheet yet
    result = export_labels(data_dir)
    assert result["labels_prefilled"] is False
    rows, fields = _read_rows(data_dir / "labels.csv")
    assert fields == EXPORT_COLUMNS
    assert len(rows) == 1
    assert rows[0]["narrative"] == "The brakes failed on the highway."
    assert rows[0]["language"] == ""
    assert rows[0]["is_safety_critical"] == ""
    assert rows[0]["component"] == ""
    assert rows[0]["notes"] == ""

    rows[0]["language"] = "hindi"
    rows[0]["is_safety_critical"] = "yes"
    rows[0]["component"] = "SERVICE BRAKES"
    rows[0]["notes"] = "human note"
    _write_rows(data_dir / "labels.csv", rows, fields)

    with pytest.raises(DataError, match="already contains labels"):
        export_labels(data_dir)
    unchanged, _ = _read_rows(data_dir / "labels.csv")
    assert unchanged[0]["component"] == "SERVICE BRAKES"

    export_labels(data_dir, force=True)
    backups = sorted(data_dir.glob("labels.backup.*.csv"))
    assert len(backups) == 1
    backup_rows, _ = _read_rows(backups[0])
    assert backup_rows[0]["component"] == "SERVICE BRAKES"
    fresh, _ = _read_rows(data_dir / "labels.csv")
    assert fresh[0]["language"] == ""


def test_export_neutralises_spreadsheet_formulas_in_stories(tmp_path: Path):
    data_dir, labels_path = _valid_set(tmp_path, narrative='=HYPERLINK("http://example.invalid","x")')
    labels_path.unlink()
    export_labels(data_dir)
    rows, _ = _read_rows(data_dir / "labels.csv")
    assert rows[0]["narrative"].startswith("'=")


def test_check_labels_reports_invalid_component(tmp_path: Path):
    data_dir, _ = _valid_set(tmp_path)
    labels = _labels_file(data_dir, [_label(component="BRAKES")])
    result = check_labels(data_dir, labels)
    assert result["usable"] == 0
    assert any("invalid component" in p["reason"] for p in result["problems"])


def test_check_labels_rejects_unknown_id(tmp_path: Path):
    data_dir, _ = _valid_set(tmp_path)
    labels = _labels_file(data_dir, [_label(rid="rh_20261026_cccccccc")])
    with pytest.raises(DataError, match="not in the collection"):
        check_labels(data_dir, labels)


def test_check_labels_reports_records_with_no_label_row(tmp_path: Path):
    data_dir, _ = _valid_set(tmp_path)
    labels = _labels_file(data_dir, [])
    result = check_labels(data_dir, labels)
    assert result["missing"] == [ID1]
    assert result["missing_count"] == 1


def test_check_labels_reports_duplicate_id(tmp_path: Path):
    data_dir, _ = _valid_set(tmp_path)
    labels = _labels_file(data_dir, [_label(), _label()])
    result = check_labels(data_dir, labels)
    assert any("duplicate id" in p["reason"] for p in result["problems"])


# ── Real-set loading and refusal ────────────────────────────────────────────


def test_load_real_set_accepts_a_valid_consenting_record(tmp_path: Path):
    from eval.real_hindi.run_eval import load_real_set

    data_dir, labels = _valid_set(tmp_path)
    loaded = load_real_set(data_dir, labels)
    assert loaded["n_records"] == 1
    assert loaded["labels"]["usable"] == 1
    assert loaded["reported_language_mismatch"] == 0
    call = loaded["calls"][0]
    assert call["lang"] == "hindi"
    assert call["kill_switch"] is True
    assert call["expect_category"] == "SERVICE BRAKES"


def test_load_real_set_refuses_synthetic_record(tmp_path: Path):
    from eval.real_hindi.run_eval import load_real_set

    data_dir = tmp_path / "data"
    ensure_layout(data_dir)
    _record(data_dir, ID1, synthetic=True)
    labels = _labels_file(data_dir, [_label()])
    with pytest.raises(DataError, match="synthetic is not false"):
        load_real_set(data_dir, labels)


def test_load_real_set_refuses_consent_hash_mismatch(tmp_path: Path):
    from eval.real_hindi.run_eval import load_real_set

    data_dir = tmp_path / "data"
    ensure_layout(data_dir)
    _record(data_dir, ID1, consent_text_sha256="0" * 64)
    labels = _labels_file(data_dir, [_label()])
    with pytest.raises(DataError, match="consent text hash"):
        load_real_set(data_dir, labels)


def test_load_real_set_refuses_audio_without_transcript(tmp_path: Path):
    from eval.real_hindi.run_eval import load_real_set

    data_dir = tmp_path / "data"
    ensure_layout(data_dir)
    _record(
        data_dir, ID1, narrative="", input_type="audio", transcript_source="none",
        audio_file="audio/missing.wav", audio_seconds=1.0, audio_sha256="0" * 64,
        audio_format="wav", audio_sample_rate=16000, audio_channels=1,
        audio_metadata_stripped=True,
    )
    labels = _labels_file(data_dir, [_label()])
    with pytest.raises(DataError, match="transcript"):
        load_real_set(data_dir, labels)


def test_load_real_set_refuses_missing_label_row(tmp_path: Path):
    from eval.real_hindi.run_eval import load_real_set

    data_dir, _ = _valid_set(tmp_path)
    labels = _labels_file(data_dir, [])
    with pytest.raises(DataError, match="no row in the label sheet"):
        load_real_set(data_dir, labels)


def test_load_real_set_refuses_invalid_component(tmp_path: Path):
    from eval.real_hindi.run_eval import load_real_set

    data_dir, _ = _valid_set(tmp_path)
    labels = _labels_file(data_dir, [_label(component="BRAKES")])
    with pytest.raises(DataError, match="invalid component"):
        load_real_set(data_dir, labels)


def test_load_real_set_refuses_duplicate_label(tmp_path: Path):
    from eval.real_hindi.run_eval import load_real_set

    data_dir, _ = _valid_set(tmp_path)
    labels = _labels_file(data_dir, [_label(), _label()])
    with pytest.raises(DataError, match="duplicate id"):
        load_real_set(data_dir, labels)


def test_load_real_set_refuses_unknown_label_id(tmp_path: Path):
    from eval.real_hindi.run_eval import load_real_set

    data_dir, _ = _valid_set(tmp_path)
    labels = _labels_file(data_dir, [_label(rid="rh_20261026_cccccccc")])
    with pytest.raises(DataError, match="not in the collection"):
        load_real_set(data_dir, labels)


def test_load_real_set_refuses_empty_collection(tmp_path: Path):
    from eval.real_hindi.run_eval import load_real_set

    data_dir = tmp_path / "data"
    ensure_layout(data_dir)
    with pytest.raises(DataError, match="no records"):
        load_real_set(data_dir, data_dir / "labels.csv")


# ── Held-out guard ──────────────────────────────────────────────────────────


def test_guard_refuses_changed_config_and_records_approval(tmp_path: Path):
    from eval.real_hindi.guard import ConfigChanged, guard_config, load_state, save_state

    state_path = tmp_path / "eval_state.json"
    state = save_state(state_path, config_hash="a" * 64, held_out=True, approval=None,
                       run_id="run-1", labels_sha256="l" * 64)
    assert state["held_out"] is True
    assert load_state(state_path)["config_hash"] == "a" * 64

    same = guard_config(state, "a" * 64, None)
    assert same["held_out"] is True and same["first_run"] is False
    with pytest.raises(ConfigChanged):
        guard_config(state, "b" * 64, None)
    with pytest.raises(ConfigChanged):
        guard_config(state, "b" * 64, "   ")

    approved = guard_config(state, "b" * 64, "changed lexicon after review")
    assert approved["held_out"] is False
    assert approved["approval"]["reason"] == "changed lexicon after review"
    state2 = save_state(state_path, config_hash="b" * 64, held_out=approved["held_out"],
                        approval=approved["approval"], run_id="run-2", labels_sha256="l" * 64)
    assert state2["held_out"] is False
    assert len(state2["approvals"]) == 1
    assert state2["approvals"][0]["run_id"] == "run-2"
    again = guard_config(state2, "b" * 64, None)
    assert again["held_out"] is False


def test_config_manifest_hashes_known_files_without_the_key():
    from eval.real_hindi.guard import CONFIG_FILES, config_manifest

    manifest = config_manifest()
    assert set(manifest["files"]) == set(CONFIG_FILES)
    assert len(manifest["hash"]) == 64
    assert "META_API_KEY" not in json.dumps(manifest)
    assert "MODEL_API_KEY" not in json.dumps(manifest)


# ── Report / run history ────────────────────────────────────────────────────


async def _fake_runner(mode: str, call: dict) -> dict:
    return {
        "severity": "High",
        "triage_skipped": False,
        "kill_switch": True,
        "kill_switch_term": "brakes failed",
        "category": "SERVICE BRAKES",
        "error": None,
        "meta_calls": 0,
        "meta_failures": 0,
        "ms": 1.0,
    }


def test_report_and_index_contain_no_story_text_and_keep_before_after(tmp_path: Path):
    import asyncio

    from eval.real_hindi.guard import guard_config, load_run_docs, recover_state
    from eval.real_hindi.run_eval import build_run, evaluate, load_real_set, write_run
    from eval.real_hindi.reporting import render_runs_index

    marker = "UNIQUE_STORY_MARKER_DO_NOT_PUBLISH"
    data_dir, labels = _valid_set(tmp_path, narrative=f"{marker} the brakes failed.")
    loaded = load_real_set(data_dir, labels)
    evaluation = asyncio.run(evaluate(loaded["calls"], runner=_fake_runner, meta_status="not_run"))

    base_manifest = {
        "hash": "a" * 64,
        "files": {"eval/real_hindi/run_eval.py": "b" * 64},
        "settings": {"model_text": "muse-spark-1.3"},
    }
    decision1 = guard_config(None, base_manifest["hash"], None)
    out1 = build_run(
        loaded=loaded, manifest=base_manifest, decision=decision1, evaluation=evaluation,
        meta_status="not_run", meta_model="muse-spark-1.3", meta_reason="no key",
        previous_labels_sha256=None,
    )
    out_dir = tmp_path / "reports"
    run_id1, run_dir1, out1 = write_run(out_dir, out1)
    report1 = (run_dir1 / "REAL_HINDI_EVAL.md").read_text(encoding="utf-8")
    assert "too small to conclude" in report1
    assert "NOT RUN" in report1
    assert marker not in report1
    summary1 = json.loads((run_dir1 / "run.json").read_text(encoding="utf-8"))
    assert "per_call" not in summary1
    full1 = json.loads((run_dir1 / "real_hindi_eval.json").read_text(encoding="utf-8"))
    assert "text" not in full1["per_call"][0]
    assert marker not in json.dumps(full1)

    decision2 = guard_config({"config_hash": "a" * 64, "held_out": True}, "b" * 64,
                              "changed lexicon for test")
    out2 = build_run(
        loaded=loaded, manifest={**base_manifest, "hash": "b" * 64}, decision=decision2,
        evaluation=evaluation, meta_status="not_run", meta_model="muse-spark-1.3",
        meta_reason="no key", previous_labels_sha256=loaded["labels"]["sha256"],
    )
    run_id2, run_dir2, out2 = write_run(out_dir, out2)
    assert run_id2 != run_id1
    assert run_dir1.is_dir()
    report2 = (run_dir2 / "REAL_HINDI_EVAL.md").read_text(encoding="utf-8")
    assert "Held-out: NO" in report2
    assert "changed lexicon for test" in report2
    assert marker not in report2

    docs = load_run_docs(out_dir)
    assert len(docs) == 2
    index = render_runs_index(docs, {
        "config_hash": "b" * 64, "held_out": False, "last_run_id": run_id2,
        "last_labels_sha256": loaded["labels"]["sha256"],
        "approvals": [decision2["approval"]],
    })
    assert run_id1 in index and run_id2 in index
    assert "too small to conclude" in index
    assert "changed lexicon for test" in index
    assert marker not in index

    recovered, recovered_flag = recover_state(tmp_path / "missing_state.json", out_dir)
    assert recovered_flag is True
    assert recovered["last_run_id"] == run_id2
    assert recovered["held_out"] is False

    # The story does still exist in the local data record; it just must never
    # reach the report files.
    assert marker in (data_dir / "records" / f"{ID1}.json").read_text(encoding="utf-8")
    for path in out_dir.rglob("*"):
        if path.is_file():
            assert marker not in path.read_text(encoding="utf-8", errors="ignore")
