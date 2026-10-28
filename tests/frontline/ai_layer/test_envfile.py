"""The documented server start must see values from the repo .env file."""

from __future__ import annotations

import os

from src.config import load_repo_env


def test_server_loader_reads_repo_env_without_overriding_the_process(tmp_path, monkeypatch):
    env_path = tmp_path / ".env"
    env_path.write_text("FRONTLINE_ENV_PROBE=from-file\n", encoding="utf-8")
    monkeypatch.setattr("src.config.REPO_ROOT", tmp_path)
    monkeypatch.setenv("FRONTLINE_ENV_PROBE", "from-process")
    load_repo_env(force=True)
    assert os.environ["FRONTLINE_ENV_PROBE"] == "from-process"
    monkeypatch.delenv("FRONTLINE_ENV_PROBE")
    load_repo_env(force=True)
    assert os.environ["FRONTLINE_ENV_PROBE"] == "from-file"


def test_isolated_tests_never_load_local_credentials(tmp_path, monkeypatch):
    (tmp_path / ".env").write_text("FRONTLINE_ENV_PROBE=private\n")
    monkeypatch.setattr("src.config.REPO_ROOT", tmp_path)
    monkeypatch.setenv("FRONTLINE_TEST_ISOLATION", "1")
    monkeypatch.delenv("FRONTLINE_ENV_PROBE", raising=False)
    load_repo_env()
    assert "FRONTLINE_ENV_PROBE" not in os.environ
