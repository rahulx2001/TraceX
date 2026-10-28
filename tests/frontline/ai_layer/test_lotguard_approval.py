"""LotGuard approval gate: supervisor-only, ledgered, latest-wins.  [AI-LAYER]"""

from __future__ import annotations

import pytest

ADMIN_SECRET = "test-admin-secret-key-32-chars-auth!!"
SERVICE_KEY = "test-service-secret-key-32-chars-auth!"


@pytest.fixture
def auth_client(reset_ops_db, monkeypatch, no_meta):
    from fastapi.testclient import TestClient

    from src.api.main import app

    monkeypatch.setenv("FRONTLINE_AUTH_REQUIRED", "1")
    monkeypatch.setenv("FRONTLINE_API_KEY", SERVICE_KEY)
    monkeypatch.setenv("SESSION_SECRET", ADMIN_SECRET)
    monkeypatch.setenv("FRONTLINE_ENABLED", "1")
    monkeypatch.delenv("FRONTLINE_OPEN_MODE", raising=False)
    monkeypatch.delenv("FRONTLINE_SERVICE_IS_ADMIN", raising=False)
    with TestClient(app) as client:
        yield client


def _hdr(role: str | None):
    from src.api.rbac import issue_session

    h = {"X-API-Key": SERVICE_KEY}
    if role:
        h["X-Frontline-Session"] = issue_session(f"{role}_user", role, issuer_role="admin")["token"]
    return h


async def _seeded_iid(owners=4):
    from src.ai_layer.lotguard import notify_lot_owners, seed_lotguard_scenario

    out = await seed_lotguard_scenario(owners=owners, with_contact=False)
    notify_lot_owners(out["investigation_id"])
    return out["investigation_id"]


async def test_approve_with_lane_is_ledgered(reset_ops_db, seed_automotive_pack, tmp_path, monkeypatch):
    monkeypatch.setenv("AI_EVIDENCE_DIR", str(tmp_path / "ev"))
    from src.ai_layer.lotguard import decide_approval, latest_approval
    from src.data.warehouse import ops_con

    iid = await _seeded_iid()
    assert latest_approval(iid) is None

    out = decide_approval(investigation_id=iid, decision="approve", lane="inspect_7d",
                          decided_by="sup1", decided_role="supervisor", note="verified cluster")
    assert out["decision"] == "approve"
    assert out["lane"] == "inspect_7d"
    assert out["verification"]["notified"] == 4

    row = latest_approval(iid)
    assert row is not None and row["approval_id"] == out["approval_id"]
    assert row["decided_by"] == "sup1"

    with ops_con(read_only=True) as con:
        actions = con.execute(
            "SELECT agent, action_type, input_summary FROM agent_actions"
            " WHERE action_type = 'approval_decided'"
        ).fetchall()
    assert any(a[0] == "supervisor" and iid in a[2] for a in actions)


async def test_reject_and_latest_wins(reset_ops_db, seed_automotive_pack, tmp_path, monkeypatch):
    monkeypatch.setenv("AI_EVIDENCE_DIR", str(tmp_path / "ev"))
    from src.ai_layer.lotguard import decide_approval, latest_approval

    iid = await _seeded_iid()
    decide_approval(investigation_id=iid, decision="approve", lane="do_not_drive",
                    decided_by="sup1", decided_role="supervisor")
    assert latest_approval(iid)["decision"] == "approve"
    decide_approval(investigation_id=iid, decision="reject", decided_by="sup1",
                    decided_role="supervisor", note="false alarm")
    latest = latest_approval(iid)
    assert latest["decision"] == "reject"
    assert latest["lane"] is None


async def test_decision_validation(reset_ops_db, seed_automotive_pack, tmp_path, monkeypatch):
    monkeypatch.setenv("AI_EVIDENCE_DIR", str(tmp_path / "ev"))
    from src.ai_layer.lotguard import ApprovalError, decide_approval

    iid = await _seeded_iid()
    with pytest.raises(ApprovalError):
        decide_approval(investigation_id=iid, decision="maybe", decided_by="s", decided_role="supervisor")
    with pytest.raises(ApprovalError):
        decide_approval(investigation_id=iid, decision="approve", decided_by="s", decided_role="supervisor")
    with pytest.raises(ApprovalError):
        decide_approval(investigation_id=iid, decision="approve", lane="fly", decided_by="s",
                        decided_role="supervisor")
    with pytest.raises(ApprovalError):
        decide_approval(investigation_id=iid, decision="reject", lane="inspect_7d", decided_by="s",
                        decided_role="supervisor")
    with pytest.raises(LookupError):
        decide_approval(investigation_id="inv_nope", decision="reject", decided_by="s",
                        decided_role="supervisor")


async def test_decision_routes_supervisor_only(auth_client, seed_automotive_pack, tmp_path, monkeypatch):
    monkeypatch.setenv("AI_EVIDENCE_DIR", str(tmp_path / "ev"))
    iid = await _seeded_iid()

    for role in ("agent", "auditor", "admin", None):
        r = auth_client.post(f"/api/ai/lotguard/{iid}/decision",
                             json={"decision": "approve", "lane": "inspect_7d"}, headers=_hdr(role))
        assert r.status_code == 403, (role, r.status_code, r.text)
    r = auth_client.post(f"/api/ai/lotguard/{iid}/decision",
                         json={"decision": "approve", "lane": "inspect_7d"},
                         headers=_hdr("supervisor"))
    assert r.status_code == 200, r.text
    assert r.json()["decided_role"] == "supervisor"

    r = auth_client.post(f"/api/ai/lotguard/{iid}/decision", json={"decision": "approve"},
                         headers=_hdr("supervisor"))
    assert r.status_code == 400

    r = auth_client.get(f"/api/ai/lotguard/{iid}/approval", headers=_hdr("agent"))
    assert r.status_code == 200
    assert r.json()["approval"]["decision"] == "approve"

    r = auth_client.post("/api/ai/lotguard/inv_nope/decision",
                         json={"decision": "reject"}, headers=_hdr("supervisor"))
    assert r.status_code == 404


def test_open_mode_cannot_decide(reset_ops_db, seed_automotive_pack, tmp_path, monkeypatch, no_meta):
    import asyncio

    from fastapi.testclient import TestClient

    from src.api.main import app

    monkeypatch.setenv("AI_EVIDENCE_DIR", str(tmp_path / "ev"))
    monkeypatch.delenv("FRONTLINE_API_KEY", raising=False)
    monkeypatch.setenv("FRONTLINE_ENABLED", "1")
    iid = asyncio.run(_seeded_iid())
    with TestClient(app) as c:
        r = c.post(f"/api/ai/lotguard/{iid}/decision", json={"decision": "reject"},
                   headers={"X-Frontline-Role": "supervisor"})  # bare header never elevates
        assert r.status_code == 403
