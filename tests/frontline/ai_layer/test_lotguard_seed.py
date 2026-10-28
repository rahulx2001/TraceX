"""LotGuard seed: lot + investigation + owners from synthetic demo data.  [AI-LAYER]

Runs against the isolated test warehouses (see conftest). Asserts the Step 1
acceptance: seed resolves to a real lot_id, an open investigation, counted
records, and a registered owner batch — and re-runs do not duplicate rows.
"""

from __future__ import annotations


async def test_seed_creates_lot_investigation_and_owners(reset_ops_db, seed_automotive_pack,
                                                         tmp_path, monkeypatch):
    monkeypatch.setenv("AI_EVIDENCE_DIR", str(tmp_path / "ev"))
    from src.ai_layer.lotguard import CLUSTER_ID, LOT, PROVENANCE, seed_lotguard_scenario

    out = await seed_lotguard_scenario(owners=6, with_contact=False)

    assert out["lot"]["lot_id"] == LOT["lot_id"]
    assert out["cluster_id"] == CLUSTER_ID
    assert out["owner_count"] == 6
    assert len(out["inserted_records"]) == 9  # 8 slice + 1 decoy

    from src.data.warehouse import domain_con, ops_con
    from src.frontline.supplier import lot_trace

    trace = lot_trace("LGD-SEED-001")
    assert trace is not None
    assert trace["lot_id"] == LOT["lot_id"]
    assert trace["supplier"] == LOT["supplier"]

    with ops_con(read_only=True) as con:
        inv = con.execute(
            "SELECT cluster_id, status, slice_category, slice_entity_2, slice_entity_3"
            " FROM investigations WHERE investigation_id = ?",
            [out["investigation_id"]]).fetchone()
        owners = con.execute(
            "SELECT count(*) FROM owner_contacts WHERE cluster_id = ?", [CLUSTER_ID]).fetchone()[0]
    assert inv is not None
    assert inv[0] == CLUSTER_ID
    assert inv[1] in ("open", "monitoring")
    assert (inv[2], inv[3], inv[4]) == ("SUSPENSION", "HONDA", "CR-V")
    assert owners == 6

    with domain_con("automotive_nhtsa", read_only=True) as con:
        counted = con.execute(
            "SELECT count(*) FROM records WHERE provenance = ?", [PROVENANCE]).fetchone()[0]
    assert counted == 9

    # The seeded slice must surface on the safety board as elevated risk
    # (elevated-tier component + hazard-mention share above 0.05).
    from src.ai_layer.safety_board import safety_board

    board = safety_board(limit=50)
    rows = [r for r in board["investigations"] if r["investigation_id"] == out["investigation_id"]]
    assert rows, "seeded investigation missing from safety board"
    assert rows[0]["safety_risk"]["level"] == "elevated"


async def test_seed_rerun_does_not_duplicate(reset_ops_db, seed_automotive_pack,
                                             tmp_path, monkeypatch):
    monkeypatch.setenv("AI_EVIDENCE_DIR", str(tmp_path / "ev"))
    from src.ai_layer.lotguard import PROVENANCE, seed_lotguard_scenario
    from src.data.warehouse import domain_con

    first = await seed_lotguard_scenario(owners=2, with_contact=False)
    second = await seed_lotguard_scenario(owners=2, with_contact=False)

    assert second["investigation_id"] == first["investigation_id"]
    assert second["inserted_records"] == []
    with domain_con("automotive_nhtsa", read_only=True) as con:
        counted = con.execute(
            "SELECT count(*) FROM records WHERE provenance = ?", [PROVENANCE]).fetchone()[0]
    assert counted == 9


async def test_lot_context_card(reset_ops_db, seed_automotive_pack, tmp_path, monkeypatch):
    monkeypatch.setenv("AI_EVIDENCE_DIR", str(tmp_path / "ev"))
    from src.ai_layer.lotguard import LOT, lot_context, seed_lotguard_scenario

    out = await seed_lotguard_scenario(owners=4, with_contact=False)
    card = lot_context(out["investigation_id"])

    assert card["lot"]["lot_id"] == LOT["lot_id"]
    assert card["lot"]["supplier"] == LOT["supplier"]
    assert card["fallback_slice_only"] is False
    assert card["owners_registered"] == 4
    assert card["risk"]["level"] == "elevated"
    assert card["synthetic_demo"] is True
    assert any("LOT-SYN-2023-03-A" in line for line in card["rationale"])
    assert card["seed_record"] == "LGD-SEED-001"


async def test_lot_context_missing_investigation(reset_ops_db):
    from src.ai_layer.lotguard import lot_context

    try:
        lot_context("inv_does_not_exist")
    except LookupError:
        pass
    else:
        raise AssertionError("expected LookupError")


def test_lotguard_route_and_board_lot(reset_ops_db, seed_automotive_pack, tmp_path, monkeypatch):
    import asyncio

    monkeypatch.setenv("AI_EVIDENCE_DIR", str(tmp_path / "ev"))
    monkeypatch.delenv("FRONTLINE_API_KEY", raising=False)
    from fastapi.testclient import TestClient

    from src.ai_layer.lotguard import LOT, seed_lotguard_scenario
    from src.api.main import app

    out = asyncio.run(seed_lotguard_scenario(owners=3, with_contact=False))
    client = TestClient(app)

    r = client.get(f"/api/ai/lotguard/{out['investigation_id']}")
    assert r.status_code == 200
    body = r.json()
    assert body["lot"]["lot_id"] == LOT["lot_id"]
    assert body["owners_registered"] == 3

    r = client.get("/api/ai/lotguard/inv_does_not_exist")
    assert r.status_code == 404

    r = client.get("/api/ai/lotguard/latest")
    assert r.status_code == 200
    assert r.json()["lotguard"]["investigation_id"] == out["investigation_id"]

    r = client.get("/api/ai/early-warning/safety")
    assert r.status_code == 200
    rows = [i for i in r.json()["investigations"] if i["investigation_id"] == out["investigation_id"]]
    assert rows and rows[0]["lot"] == {"lot_id": LOT["lot_id"], "supplier": LOT["supplier"]}


async def test_seed_contact_and_photo(reset_ops_db, seed_automotive_pack, tmp_path, monkeypatch):
    monkeypatch.setenv("AI_EVIDENCE_DIR", str(tmp_path / "ev"))
    from src.ai_layer.lotguard import seed_lotguard_scenario

    out = await seed_lotguard_scenario(owners=1, with_contact=True)

    contact = out["contact"]
    assert contact is not None
    assert contact["interaction_id"]
    assert len(contact["transcript"]) >= 2
    assert out["evidence"] is not None
    assert out["evidence"]["evidence_id"]
