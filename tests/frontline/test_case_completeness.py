"""Case completeness: honest reasons for empty drawer panels."""

from __future__ import annotations

from datetime import datetime, timezone

from src.frontline.case_completeness import completeness_for_case, draft_operator_note


def _case(con, cid="case_comp", adv=None):
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    con.execute(
        "INSERT INTO interactions (interaction_id, pack_id, pack_version, started_at, channel, status, entity_1, entity_2, entity_3) "
        "VALUES (?, 'automotive_nhtsa', 'v', ?, 'web_text', 'closed', '2019', 'HONDA', 'CR-V')",
        ["int_" + cid, now],
    )
    con.execute(
        "INSERT INTO cases (case_id, interaction_id, pack_id, created_at, category, severity, severity_source, priority, "
        "safety_flags, status, case_kind, advisory_match_id, followup_draft) VALUES (?, ?, 'automotive_nhtsa', ?, 'STEERING', 'Critical', 'rules', 1, '{}', 'open', 'customer', ?, 'Subject: x')",
        [cid, "int_" + cid, now, adv],
    )
    return cid


def test_empty_panels_explain_themselves(reset_ops_db):
    from src.data.warehouse import ops_con

    with ops_con() as con:
        _case(con)
    info = completeness_for_case("case_comp")
    assert info["case_found"] and not info["complete"]
    assert info["advisory"]["status"] == "no_match"
    assert "HONDA" in info["advisory"]["reason"]
    assert info["fault_codes"]["status"] == "not_supplied"
    assert info["photos"]["status"] == "not_supplied"
    assert set(info["missing"]) == {"fault_codes", "photos", "operator_notes"}
    assert info["unavailable"] == []
    assert info["reported_vehicle"] == {"year": "2019", "make": "HONDA", "model": "CR-V"}
    assert info["vehicle_details_missing"] == []
    assert "without a recall match" in info["advisory"]["reason"]
    assert "STEERING" in info["draft_operator_note"]


def test_matched_advisory_is_complete_for_that_field(reset_ops_db):
    from src.data.warehouse import ops_con

    with ops_con() as con:
        _case(con, adv="adv_123")
    info = completeness_for_case("case_comp")
    assert info["advisory"]["status"] == "matched"
    assert "advisory" not in info["missing"]


def test_draft_note_uses_only_case_facts():
    note = draft_operator_note(
        {"category": "STEERING", "severity": "Critical", "priority": 1, "status": "open",
         "safety_flags": {"steering_locked": True}, "advisory_match_id": None},
        fault_codes=["C0035"], photo_count=1)
    assert "C0035" in note and "Photos attached: 1" in note


def test_lookup_failures_do_not_claim_customer_supplied_nothing(reset_ops_db, monkeypatch):
    from src.data.warehouse import ops_con
    from src.ai_layer import evidence, fault_codes
    from src.frontline import ops

    with ops_con() as con:
        _case(con)

    def failed(*args, **kwargs):
        raise RuntimeError("temporary read failure")

    monkeypatch.setattr(fault_codes, "for_case", failed)
    monkeypatch.setattr(evidence, "list_for_case", failed)
    monkeypatch.setattr(ops, "list_case_notes", failed)
    info = completeness_for_case("case_comp")
    assert set(info["unavailable"]) == {"fault_codes", "photos", "operator_notes"}
    assert info["missing"] == []
    assert not info["complete"]
    assert all(info[field]["status"] == "unavailable" for field in info["unavailable"])
    assert all(info[field]["count"] is None for field in info["unavailable"])
    assert "No fault codes supplied" not in info["draft_operator_note"]
    assert "Photos attached: 0" not in info["draft_operator_note"]


def test_no_recall_match_does_not_leave_an_evidenced_case_incomplete(reset_ops_db, monkeypatch):
    from src.data.warehouse import ops_con
    from src.ai_layer import evidence, fault_codes
    from src.frontline import ops

    with ops_con() as con:
        _case(con)
    monkeypatch.setattr(fault_codes, "for_case", lambda *_: {"codes": [{"code": "C0035"}]})
    monkeypatch.setattr(evidence, "list_for_case", lambda *_: [{"evidence_id": "fixture-photo"}])
    monkeypatch.setattr(ops, "list_case_notes", lambda *_: [{"body": "Reviewed"}])
    info = completeness_for_case("case_comp")
    assert info["advisory"]["status"] == "no_match"
    assert info["complete"] and info["missing"] == [] and info["unavailable"] == []


def test_case_detail_remains_reviewable_when_notes_store_is_unavailable(reset_ops_db, monkeypatch):
    from fastapi.testclient import TestClient
    from src.api.main import app
    from src.data.warehouse import ops_con
    from src.frontline import ops

    with ops_con() as con:
        _case(con)
    monkeypatch.setenv("FRONTLINE_OPEN_MODE", "1")
    monkeypatch.setenv("FRONTLINE_AUTH_REQUIRED", "0")
    monkeypatch.setenv("FRONTLINE_API_KEY", "")
    def failed(*args, **kwargs):
        raise RuntimeError("fictional notes-store outage")
    monkeypatch.setattr(ops, "list_case_notes", failed)
    with TestClient(app) as client:
        response = client.get("/api/frontline/cases/case_comp")
    assert response.status_code == 200
    body = response.json()
    assert body["notes_unavailable"] is True
    assert "operator_notes" in body["completeness"]["unavailable"]
    assert body["completeness"]["operator_notes"]["count"] is None
