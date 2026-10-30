"""Public replay and commit-manifest integrity, using temporary directories only."""
import json
from pathlib import Path
import shutil
import subprocess
import zipfile

import pytest

from scripts import package_public_replay as bundle, public_replay as replay, submission_manifest as manifest


def test_allowlisted_bundle_replays_without_application_dependencies(tmp_path):
    destination = tmp_path/"replay.zip"
    result = bundle.package(destination)
    assert result["bytes"] < 1_000_000
    with zipfile.ZipFile(destination) as archive:
        assert not any(name.startswith(("data/", ".env", "models/")) for name in archive.namelist())
        archive.extractall(tmp_path/"fresh")
    result = replay.validate(tmp_path/"fresh")
    assert result["ok"] and result["model_calls"] == 0
    target = tmp_path/"fresh/reports/hackathon/investigation_live_smoke.json"
    value = json.loads(target.read_text())
    value["initial"]["sources"][0]["text"] += " changed"
    target.write_text(json.dumps(value))
    with pytest.raises(AssertionError, match="Artifact changed"):
        replay.validate(tmp_path/"fresh")


def test_manifest_pins_commit_excludes_self_and_rejects_worktree_drift(tmp_path):
    def git(*args):
        return subprocess.check_output(["git", "-c", "user.name=Manifest test", "-c", "user.email=test@example.invalid", *args], cwd=tmp_path).decode().strip()
    git("init", "--quiet")
    (tmp_path/"source.py").write_text("value = 1\n")
    (tmp_path/".env").write_text("NOT_A_REAL_SECRET=fixture\n")
    (tmp_path/manifest.OUTPUT).parent.mkdir(parents=True)
    (tmp_path/manifest.OUTPUT).write_text("{}")
    git("add", ".")
    git("commit", "--quiet", "-m", "Temporary baseline")
    baseline = git("rev-parse", "HEAD")
    (tmp_path/"source.py").write_text("value = 2\n")
    git("add", "source.py")
    git("commit", "--quiet", "-m", "Temporary event delta")
    result = manifest.create("HEAD", baseline, tmp_path)
    assert [f["path"] for f in result["files"]] == ["source.py"]
    assert result["event_delta"] == [{"status": "M", "path": "source.py"}]
    assert manifest.verify(result, root=tmp_path, worktree=True)["ok"]
    (tmp_path/"source.py").write_text("value = 3\n")
    with pytest.raises(AssertionError, match="Working source changed"):
        manifest.verify(result, root=tmp_path, worktree=True)


def test_historical_citation_validation_is_not_just_nonempty_output():
    proof = replay.read("reports/hackathon/investigation_followup_smoke.json")
    assert replay.validate_proof(proof)
    proof["followup"]["brief"]["claims"][0]["evidence"][0]["quote"] = "An unsupported invented quotation"
    with pytest.raises(AssertionError):
        replay.validate_proof(proof)
