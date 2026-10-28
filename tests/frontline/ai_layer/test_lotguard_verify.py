"""LotGuard owner verification loop: mock notices + structured replies.  [AI-LAYER]

Nothing is sent anywhere: notices and replies are warehouse rows only, and
every payload carries the mock label. Recommendations are computed from
counts; investigation state is never changed here.
"""

from __future__ import annotations

import pytest


async def _seeded(owners=6):
    from src.ai_layer.lotguard import notify_lot_owners, seed_lotguard_scenario

    out = await seed_lotguard_scenario(owners=owners, with_contact=False)
    notices = notify_lot_owners(out["investigation_id"])
    return out, notices


async def test_notify_records_mock_notices(reset_ops_db, seed_automotive_pack, tmp_path, monkeypatch):
    monkeypatch.setenv("AI_EVIDENCE_DIR", str(tmp_path / "ev"))
    out, notices = await _seeded(owners=5)

    assert notices["mock"] is True
    assert "SIMULATED" in notices["mock_label"]
    assert notices["count"] == 5
    assert notices["investigation_id"] == out["investigation_id"]


async def test_matched_replies_escalate(reset_ops_db, seed_automotive_pack, tmp_path, monkeypatch):
    monkeypatch.setenv("AI_EVIDENCE_DIR", str(tmp_path / "ev"))
    from src.ai_layer.lotguard import record_owner_reply, verification_status

    out, notices = await _seeded(owners=4)
    iid = out["investigation_id"]
    assert verification_status(iid)["recommendation"] == "collecting"

    for n in notices["notices"][:3]:
        record_owner_reply(investigation_id=iid, owner_id=n["owner_id"],
                           symptoms=["clunk", "uneven_wear"])
    status = verification_status(iid)
    assert status["notified"] == 4
    assert status["replied"] == 3
    assert status["matched"] == 3
    assert status["recommendation"] == "escalate"


async def test_none_majority_de_escalates(reset_ops_db, seed_automotive_pack, tmp_path, monkeypatch):
    monkeypatch.setenv("AI_EVIDENCE_DIR", str(tmp_path / "ev"))
    from src.ai_layer.lotguard import record_owner_reply, verification_status

    out, notices = await _seeded(owners=6)
    iid = out["investigation_id"]

    for n in notices["notices"][:5]:
        record_owner_reply(investigation_id=iid, owner_id=n["owner_id"], symptoms=["none"])
    status = verification_status(iid)
    assert status["replied"] == 5
    assert status["none_count"] == 5
    assert status["recommendation"] == "de_escalate"
    # Investigation state itself is untouched: the supervisor applies this.
    from src.data.warehouse import ops_con

    with ops_con(read_only=True) as con:
        row = con.execute("SELECT status FROM investigations WHERE investigation_id = ?",
                          [iid]).fetchone()
    assert row[0] in ("open", "monitoring")


async def test_reply_validation_fails_closed(reset_ops_db, seed_automotive_pack, tmp_path, monkeypatch):
    monkeypatch.setenv("AI_EVIDENCE_DIR", str(tmp_path / "ev"))
    from src.ai_layer.lotguard import VerificationError, record_owner_reply

    out, notices = await _seeded(owners=2)
    iid = out["investigation_id"]
    owner = notices["notices"][0]["owner_id"]

    with pytest.raises(VerificationError):
        record_owner_reply(investigation_id=iid, owner_id=owner, symptoms=["smoke"])
    with pytest.raises(VerificationError):
        record_owner_reply(investigation_id=iid, owner_id=owner, symptoms=["none", "clunk"])
    with pytest.raises(VerificationError):
        record_owner_reply(investigation_id=iid, owner_id=owner, symptoms=["clunk"],
                           photo_ref="ev_does_not_exist")
    with pytest.raises(VerificationError):
        record_owner_reply(investigation_id=iid, owner_id="own_nobody", symptoms=["clunk"])
    with pytest.raises(VerificationError):
        record_owner_reply(investigation_id=iid, owner_id=owner, symptoms=[])

    first = record_owner_reply(investigation_id=iid, owner_id=owner, symptoms=["clunk"])
    assert first["duplicate"] is False
    again = record_owner_reply(investigation_id=iid, owner_id=owner, symptoms=["none"])
    assert again["duplicate"] is True
    assert again["reply_id"] == first["reply_id"]


async def test_photo_reply_counts(reset_ops_db, seed_automotive_pack, tmp_path, monkeypatch):
    monkeypatch.setenv("AI_EVIDENCE_DIR", str(tmp_path / "ev"))
    from src.ai_layer.lotguard import record_owner_reply, seed_lotguard_scenario, verification_status

    out = await seed_lotguard_scenario(owners=1, with_contact=True)
    from src.ai_layer.lotguard import notify_lot_owners

    notices = notify_lot_owners(out["investigation_id"])
    assert out["evidence"] is not None
    record_owner_reply(investigation_id=out["investigation_id"],
                       owner_id=notices["notices"][0]["owner_id"],
                       symptoms=["clunk"], photo_ref=out["evidence"]["evidence_id"])
    status = verification_status(out["investigation_id"])
    assert status["photo_count"] == 1
    assert status["matched"] == 1


def test_verification_routes(reset_ops_db, seed_automotive_pack, tmp_path, monkeypatch):
    import asyncio

    monkeypatch.setenv("AI_EVIDENCE_DIR", str(tmp_path / "ev"))
    monkeypatch.delenv("FRONTLINE_API_KEY", raising=False)
    from fastapi.testclient import TestClient

    from src.api.main import app

    out, _ = asyncio.run(_seeded(owners=3))
    iid = out["investigation_id"]
    client = TestClient(app)

    r = client.post(f"/api/ai/lotguard/{iid}/notify")
    assert r.status_code == 200
    assert r.json()["mock"] is True
    owner = r.json()["notices"][0]["owner_id"]

    r = client.post(f"/api/ai/lotguard/{iid}/replies",
                    json={"owner_id": owner, "symptoms": ["steering_pull"]})
    assert r.status_code == 200
    assert r.json()["status"]["matched"] == 1

    r = client.post(f"/api/ai/lotguard/{iid}/replies",
                    json={"owner_id": owner, "symptoms": ["bogus"]})
    assert r.status_code == 400

    r = client.get(f"/api/ai/lotguard/{iid}/verification")
    assert r.status_code == 200
    assert r.json()["notified"] >= 3

    r = client.get("/api/ai/lotguard/inv_nope/verification")
    assert r.status_code == 404
