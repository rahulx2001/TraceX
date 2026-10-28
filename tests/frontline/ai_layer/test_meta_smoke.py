"""Live smoke script: no key -> no network; fake Meta -> each check reported.  [AI-LAYER]"""

from __future__ import annotations


def test_smoke_skips_without_key(no_meta, capsys):
    from scripts.ai_meta_smoke import main

    assert main([]) == 0
    out = capsys.readouterr().out
    assert "skipped" in out and "checks" in out


def test_smoke_reports_each_check(fake_meta, reset_ops_db, seed_automotive_pack, monkeypatch, tmp_path):
    from scripts.ai_meta_smoke import run_checks

    from src.ai_layer import live_proof
    monkeypatch.setattr(live_proof, "proof_path", lambda: tmp_path / "proof.json")
    fake_meta.chat["intake_slots"] = lambda p: {
        "language": "hi", "normalized_en": "My 2019 Honda CR-V makes a grinding noise when pressing the brake at low speed.",
        "normalization_confidence": 0.95, "slots": [], "frustration": 0,
        "frustration_reason": "Neutral complaint",
    }
    fake_meta.chat["smoke_vision"] = lambda p: {"description": "A brake disc.", "confidence": 0.8}
    fake_meta.sam = lambda p: "0<|box;x1=10;y1=10;x2=50;y2=40;w=240;h=180|>"
    out = run_checks(vision=True, sam=True)
    names = [c["feature"] for c in out["checks"]]
    assert names == ["text", "vision", "segmentation"]
    assert all(c["ok"] for c in out["checks"]), [(c["feature"], c.get("reason"), c.get("result")) for c in out["checks"]]
    assert out["ok"] is False and out["live_transport"] is False
    assert out["checks"][0]["result"]["ledger"]["ok"] is True
    from src.ledger.chain import verify_chain
    import json
    saved = json.loads((tmp_path / "proof.json").read_text())
    assert verify_chain(saved["checks"][0]["result"]["ledger_actions"], allow_partial=True)["ok"] is True
    assert not out["checks"][0]["result"]["safety_flags"].get("fire")
    assert out["checks"][0]["result"]["case_id"], out["checks"][0]["result"]["transcript"]
    assert "test-placeholder-not-a-real-key" not in (tmp_path / "proof.json").read_text()


def test_smoke_reports_failure_reason(fake_meta, reset_ops_db, seed_automotive_pack, monkeypatch, tmp_path):
    from scripts.ai_meta_smoke import run_checks

    monkeypatch.setattr("src.ai_layer.live_proof.proof_path", lambda: tmp_path / "proof.json")
    fake_meta.status_queue = [401] * 20
    out = run_checks(vision=True, sam=True)
    assert out["ok"] is False
    assert all(not c["ok"] for c in out["checks"])
    assert out["checks"][0]["result"].get("fallback_reason")
    assert all(c.get("reason") for c in out["checks"][1:])


def test_proof_verifies_only_the_endpoint_and_model_run(monkeypatch, tmp_path):
    from src.ai_layer import config, live_proof
    import json

    monkeypatch.setenv("FRONTLINE_TEST_ISOLATION", "0")
    path = tmp_path / "proof.json"
    monkeypatch.setattr(live_proof, "proof_path", lambda: path)
    data = {"live_transport": True, "api_base": config.api_base(),
            "checks": [{"feature": "text", "ok": True, "model_id": config.model_text()}]}
    path.write_text(json.dumps(data))
    assert live_proof.verified_features() == {"text": True, "vision": False, "segmentation": False, "image": False}
    data["api_base"] = "https://another-endpoint.example/v1"
    path.write_text(json.dumps(data))
    assert not any(live_proof.verified_features().values())
    data["api_base"] = config.api_base()
    data["checks"][0]["model_id"] = "another-model"
    path.write_text(json.dumps(data))
    assert not any(live_proof.verified_features().values())
