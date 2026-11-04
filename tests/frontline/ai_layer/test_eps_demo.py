"""Golden walkthrough and guardrails against fabricated readiness/outcomes."""
import pytest


@pytest.mark.timeout(240)
async def test_canonical_demo_replays_and_preserves_work(reset_ops_db, seed_automotive_pack, tmp_path, monkeypatch):
    monkeypatch.setenv("AI_EVIDENCE_DIR", str(tmp_path / "evidence"))
    from src.ai_layer.eps_demo import seed_eps_demo, lot_for_case, CLUSTER_ID, ADVISORY_ID
    from src.data.warehouse import ops_con
    from src.frontline.case_completeness import completeness_for_case
    from src.ai_layer.fault_codes import for_case
    from src.ai_layer.evidence import list_for_case
    from src.frontline.ops import add_case_note
    from src.frontline.demo_followup import send_demo_followup
    first = await seed_eps_demo()
    assert len(set(first["case_ids"])) == 11
    hero = first["hero_case_id"]
    assert completeness_for_case(hero)["complete"]
    with ops_con(read_only=True) as con:
        rows = con.execute("SELECT cluster_match_id, advisory_match_id, severity FROM cases WHERE case_id IN (" + ",".join("?" for _ in first["case_ids"]) + ")", first["case_ids"]).fetchall()
        assert all(r[0] == CLUSTER_ID and r[1] == ADVISORY_ID for r in rows)
        assert con.execute("SELECT count(*) FROM agent_actions WHERE action_type = 'case_created'").fetchone()[0] == 11
        assert con.execute("SELECT count(*) FROM interaction_turns WHERE speaker = 'customer'").fetchone()[0] >= 11
    assert sum(any(c["code"] == "C0035" for c in for_case(cid)["codes"]) for cid in first["case_ids"]) == 2
    photo = list_for_case(hero)[0]
    assert photo["size_bytes"] > 1000
    lot = lot_for_case(hero)
    assert (lot["lot_size"], lot["reported"], lot["initially_silent"], lot["contacted"]) == (213, 11, 202, 202)
    assert lot["outcomes"] == {"opened_or_routed": 68, "bookings": 41, "findings": 9, "resolved": 9}
    assert lot["vehicles_warned_before_failure"] == 9
    assert [p["reports"] for p in lot["failure_trend"]] == [1, 3, 6, 11]
    assert lot["evaluation"]["verified"]
    assert lot["evaluation"]["accuracy"] == .82
    assert lot["evaluation"]["macro_f1"] == pytest.approx(.5140943597465337)
    assert first["metrics"]["delivered"] == 0
    sent = send_demo_followup(hero, "demo reviewer")
    assert sent["status"] == "simulated_delivered"
    assert send_demo_followup(hero, "demo reviewer") == sent
    add_case_note(hero, "Operator edit that must survive demo reload", author="judge")
    second = await seed_eps_demo()
    assert second["case_ids"] == first["case_ids"]
    assert second["campaign_id"] == first["campaign_id"]
    with ops_con(read_only=True) as con:
        assert con.execute("SELECT count(*) FROM cases").fetchone()[0] == 11
        assert con.execute("SELECT count(*) FROM demo_case_followups").fetchone()[0] == 1
        assert con.execute("SELECT count(*) FROM case_notes WHERE author = 'judge'").fetchone()[0] == 1
    # The default queue includes canonical demo rows; ordinary simulations remain hidden.
    from fastapi.testclient import TestClient
    from src.api.main import app
    client = TestClient(app)
    response = client.get("/api/frontline/cases")
    assert response.status_code == 200
    assert len(response.json()["cases"]) == 11
    detail = client.get(f"/api/frontline/cases/{hero}").json()
    assert detail["synthetic_demo"] and detail["demo_hero"] and detail["parents"]
    assert detail["severity"] == "High"
    assert detail["severity_inheritance"]["own_severity"] == "Medium"
    from src.ai_layer.campaign_investigator import list_runs
    runs = list_runs(first["campaign_id"])
    assert len(runs) == 1 and runs[0]["status"] == "complete"
    assert runs[0]["report_sources"][0]["provenance"]["kind"] == "interaction"
    assert client.get(f"/api/frontline/cases/{hero}/lot").json()["vehicles_warned_before_failure"] == 9


def test_inheritance_caps_neighbour_critical_and_explains_medium():
    from src.frontline.case_parents import inherit_severity
    parents = [{"record_id": "high", "severity_label": "High"}, {"record_id": "critical", "severity_label": "Critical"}]
    result = inherit_severity("Medium", parents)
    assert result["effective_severity"] == "High" and result["own_severity"] == "Medium"
    assert result["cap"] == "High" and "not a diagnosis" in result["interpretation"]
    assert inherit_severity("Critical", parents)["effective_severity"] == "Critical"
    assert not inherit_severity("Medium", parents[:1])["raised"]


async def test_public_channel_cannot_set_synthetic_origin(reset_ops_db, seed_automotive_pack):
    from src.agents.orchestrator import create_interaction
    with pytest.raises(ValueError, match="simulated channel"):
        await create_interaction(channel="web_text", synthetic_origin={"scenario": "forged"})


def test_frozen_metrics_reject_changed_artifact(monkeypatch, tmp_path):
    from src.ai_layer.eps_demo import frozen_evaluation
    from src import config
    monkeypatch.setattr(config, "REPO_ROOT", tmp_path)
    result = frozen_evaluation()
    assert result["verified"] is False
    assert "accuracy" not in result
