"""LotGuard workshop close-out: locked queue, outcomes, yield, packet.  [AI-LAYER]"""

from __future__ import annotations

import pytest


async def _approved_iid(owners=4):
    from src.ai_layer.lotguard import (decide_approval, notify_lot_owners,
                                       seed_lotguard_scenario)

    out = await seed_lotguard_scenario(owners=owners, with_contact=False)
    notify_lot_owners(out["investigation_id"])
    decide_approval(investigation_id=out["investigation_id"], decision="approve",
                    lane="inspect_7d", decided_by="sup1", decided_role="supervisor")
    return out


async def test_outcomes_locked_until_approved(reset_ops_db, seed_automotive_pack, tmp_path, monkeypatch):
    monkeypatch.setenv("AI_EVIDENCE_DIR", str(tmp_path / "ev"))
    from src.ai_layer.lotguard import (ApprovalError, record_outcome, seed_lotguard_scenario,
                                       workshop_queue)

    out = await seed_lotguard_scenario(owners=2, with_contact=False)
    iid = out["investigation_id"]
    queue = workshop_queue(iid)
    assert queue["locked"] is True
    assert queue["count"] == 2  # visible for review, recording locked
    with pytest.raises(ApprovalError):
        record_outcome(investigation_id=iid, owner_id=out["owner_ids"][0],
                       outcome="crack_found", recorded_by="mech")


async def test_reject_locks_outcomes(reset_ops_db, seed_automotive_pack, tmp_path, monkeypatch):
    monkeypatch.setenv("AI_EVIDENCE_DIR", str(tmp_path / "ev"))
    from src.ai_layer.lotguard import (ApprovalError, decide_approval, record_outcome,
                                       seed_lotguard_scenario, workshop_queue)

    out = await seed_lotguard_scenario(owners=2, with_contact=False)
    iid = out["investigation_id"]
    decide_approval(investigation_id=iid, decision="reject", decided_by="sup1",
                    decided_role="supervisor")
    assert workshop_queue(iid)["locked"] is True
    with pytest.raises(ApprovalError):
        record_outcome(investigation_id=iid, owner_id=out["owner_ids"][0],
                       outcome="no_issue", recorded_by="mech")


async def test_outcomes_and_yield(reset_ops_db, seed_automotive_pack, tmp_path, monkeypatch):
    monkeypatch.setenv("AI_EVIDENCE_DIR", str(tmp_path / "ev"))
    from src.ai_layer.lotguard import (ApprovalError, campaign_yield, record_outcome,
                                       workshop_queue)

    out = await _approved_iid(owners=4)
    iid = out["investigation_id"]
    assert workshop_queue(iid)["locked"] is False
    assert workshop_queue(iid)["lane"] == "inspect_7d"
    assert campaign_yield(iid)["yield"] is None

    owners = out["owner_ids"]
    record_outcome(investigation_id=iid, owner_id=owners[0], outcome="crack_found",
                   recorded_by="mech")
    record_outcome(investigation_id=iid, owner_id=owners[1], outcome="crack_found",
                   recorded_by="mech")
    record_outcome(investigation_id=iid, owner_id=owners[2], outcome="wear_only",
                   recorded_by="mech")
    record_outcome(investigation_id=iid, owner_id=owners[3], outcome="no_issue",
                   recorded_by="mech")

    y = campaign_yield(iid)
    assert y["inspected"] == 4
    assert y["crack_found"] == 2
    assert y["yield"] == pytest.approx(0.5)

    dup = record_outcome(investigation_id=iid, owner_id=owners[0], outcome="no_issue",
                         recorded_by="mech")
    assert dup["duplicate"] is True
    assert campaign_yield(iid)["crack_found"] == 2

    with pytest.raises(ApprovalError):
        record_outcome(investigation_id=iid, owner_id=owners[0], outcome="fixed",
                       recorded_by="mech")
    with pytest.raises(ApprovalError):
        record_outcome(investigation_id=iid, owner_id="own_nobody", outcome="no_issue",
                       recorded_by="mech")


async def test_queue_ranks_matched_first(reset_ops_db, seed_automotive_pack, tmp_path, monkeypatch):
    monkeypatch.setenv("AI_EVIDENCE_DIR", str(tmp_path / "ev"))
    from src.ai_layer.lotguard import notify_lot_owners, record_owner_reply, workshop_queue
    from src.ai_layer.lotguard import decide_approval, seed_lotguard_scenario

    out = await seed_lotguard_scenario(owners=3, with_contact=False)
    iid = out["investigation_id"]
    notices = notify_lot_owners(iid)
    record_owner_reply(investigation_id=iid, owner_id=notices["notices"][0]["owner_id"],
                       symptoms=["clunk"])
    record_owner_reply(investigation_id=iid, owner_id=notices["notices"][1]["owner_id"],
                       symptoms=["none"])
    decide_approval(investigation_id=iid, decision="approve", lane="inspect_7d",
                    decided_by="sup1", decided_role="supervisor")

    queue = workshop_queue(iid)["queue"]
    assert [q["owner_id"] for q in queue] == [
        notices["notices"][0]["owner_id"],
        notices["notices"][2]["owner_id"],
        notices["notices"][1]["owner_id"],
    ]
    assert queue[0]["score"] == 25
    assert any("clunk" in r for r in queue[0]["reasons"])


async def test_evidence_packet(reset_ops_db, seed_automotive_pack, tmp_path, monkeypatch):
    monkeypatch.setenv("AI_EVIDENCE_DIR", str(tmp_path / "ev"))
    from src.ai_layer.lotguard import evidence_packet, record_outcome

    out = await _approved_iid(owners=2)
    iid = out["investigation_id"]
    record_outcome(investigation_id=iid, owner_id=out["owner_ids"][0], outcome="crack_found",
                   recorded_by="mech")

    packet = evidence_packet(iid)
    assert packet["packet"] == "lotguard-evidence-v1"
    assert packet["lot"]["lot_id"] == "LOT-SYN-2023-03-A"
    assert packet["seed_record"] == "LGD-SEED-001"
    assert packet["approval"]["decision"] == "approve"
    assert packet["yield"]["inspected"] == 1
    assert packet["verification"]["notified"] == 2
    assert "No accident" in packet["method"]


def test_workshop_routes(reset_ops_db, seed_automotive_pack, tmp_path, monkeypatch):
    import asyncio

    monkeypatch.setenv("AI_EVIDENCE_DIR", str(tmp_path / "ev"))
    monkeypatch.delenv("FRONTLINE_API_KEY", raising=False)
    from fastapi.testclient import TestClient

    from src.api.main import app

    out = asyncio.run(_approved_iid(owners=2))
    iid = out["investigation_id"]
    client = TestClient(app)

    r = client.get(f"/api/ai/lotguard/{iid}/workshop")
    assert r.status_code == 200
    assert r.json()["locked"] is False
    assert r.json()["count"] == 2

    r = client.post(f"/api/ai/lotguard/{iid}/outcomes",
                    json={"owner_id": out["owner_ids"][0], "outcome": "wear_only"})
    assert r.status_code == 200, r.text
    assert r.json()["yield"]["inspected"] == 1

    r = client.post(f"/api/ai/lotguard/{iid}/outcomes",
                    json={"owner_id": out["owner_ids"][1], "outcome": "bogus"})
    assert r.status_code == 400

    r = client.get(f"/api/ai/lotguard/{iid}/packet")
    assert r.status_code == 200
    assert r.json()["packet"] == "lotguard-evidence-v1"

    r = client.get("/api/ai/lotguard/inv_nope/workshop")
    assert r.status_code == 404
