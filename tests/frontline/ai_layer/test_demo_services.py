"""The demo must retain configured providers after its reproducible seed."""
import os

import pytest

from scripts.run_lotguard_demo import PROVIDER_KEYS, configure_services, offline_seed


@pytest.fixture
def clean_services(monkeypatch):
    for name in (*PROVIDER_KEYS, "FRONTLINE_AI_LAYER", "FRONTLINE_LLM_ENABLED",
                 "DEEPGRAM_ENABLED", "FRONTLINE_TEST_ISOLATION",
                 "FRONTLINE_DISABLE_INLINE_WORKER", "META_BACKEND", "META_TIMEOUT_S"):
        # delenv alone records no undo for an absent variable. The launcher
        # writes directly to os.environ, so reserve an undo before deleting.
        monkeypatch.setenv(name, os.environ.get(name, ""))
        monkeypatch.delenv(name, raising=False)


def test_live_demo_loads_credentials_and_restores_them_after_seed(tmp_path, clean_services):
    (tmp_path / ".env").write_text("BASETEN_API_KEY=fictional-file-key\nFRONTLINE_AI_LAYER=off\nFRONTLINE_LLM_ENABLED=0\n")
    configure_services(tmp_path, offline=False)
    assert os.environ["BASETEN_API_KEY"] == "fictional-file-key"
    assert os.environ["FRONTLINE_AI_LAYER"] == "auto"
    assert os.environ["FRONTLINE_LLM_ENABLED"] == "1"
    with offline_seed():
        assert all(not os.environ[key] for key in PROVIDER_KEYS)
        assert os.environ["FRONTLINE_AI_LAYER"] == "off"
    assert os.environ["BASETEN_API_KEY"] == "fictional-file-key"
    assert os.environ["FRONTLINE_AI_LAYER"] == "auto"
    assert "FRONTLINE_TEST_ISOLATION" not in os.environ
    assert os.environ["FRONTLINE_DISABLE_INLINE_WORKER"] == "0"


def test_shell_key_wins_over_dotenv(tmp_path, clean_services, monkeypatch):
    (tmp_path / ".env").write_text("META_API_KEY=fictional-file-key\n")
    monkeypatch.setenv("META_API_KEY", "fictional-shell-key")
    configure_services(tmp_path, offline=False)
    assert os.environ["META_API_KEY"] == "fictional-shell-key"


def test_server_speech_requires_its_own_credential(tmp_path, clean_services):
    (tmp_path / ".env").write_text("META_API_KEY=fictional-key\nDEEPGRAM_ENABLED=1\n")
    configure_services(tmp_path, offline=False)
    assert os.environ["DEEPGRAM_ENABLED"] == "0"
    os.environ["DEEPGRAM_API_KEY"] = "fictional-speech-key"
    configure_services(tmp_path, offline=False)
    assert os.environ["DEEPGRAM_ENABLED"] == "1"


def test_offline_replay_never_imports_local_credentials(tmp_path, clean_services, monkeypatch):
    (tmp_path / ".env").write_text("META_API_KEY=fictional-file-key\n")
    monkeypatch.setenv("BASETEN_API_KEY", "fictional-shell-key")
    configure_services(tmp_path, offline=True)
    assert all(not os.environ[key] for key in PROVIDER_KEYS)
    assert os.environ["FRONTLINE_LLM_ENABLED"] == "0"
    assert os.environ["FRONTLINE_TEST_ISOLATION"] == "1"


def test_seed_failure_restores_serving_configuration(clean_services, monkeypatch):
    monkeypatch.setenv("META_API_KEY", "fictional-serving-key")
    monkeypatch.setenv("FRONTLINE_AI_LAYER", "auto")
    with pytest.raises(RuntimeError), offline_seed():
        raise RuntimeError("canonical matcher did not reproduce")
    assert os.environ["META_API_KEY"] == "fictional-serving-key"
    assert os.environ["FRONTLINE_AI_LAYER"] == "auto"
    assert "FRONTLINE_TEST_ISOLATION" not in os.environ
