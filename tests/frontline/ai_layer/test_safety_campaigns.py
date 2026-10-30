"""Safety boundaries and a complete campaign on isolated warehouses; no live AI or delivery."""
import csv
import io
import json
from concurrent.futures import ThreadPoolExecutor

import pytest

from src.ai_layer import safety_campaigns as sc


@pytest.fixture
def campaign(reset_ops_db):
    return sc.demo_campaign("demo-operator", "agent")


def act(c, kind, data=None, role="agent", request_id=None):
    return sc.apply_action(c["campaign_id"], kind, data or {}, "reviewer" if role == "supervisor" else "demo-operator",
                           role, c["revision"], request_id or f"test-{c['revision']}-{kind}")


def vehicle(c, vid="DEMO-CAR-001"):
    return next(v for v in c["vehicles"] if v["vehicle_id"] == vid)


def test_traceability_and_approved_simulation(campaign):
    c = campaign
    m = c["metrics"]
    assert (m["exact"], m["possible"], m["unknown"], m["excluded"], m["unresolved"]) == (7, 2, 1, 2, 10)
    assert m["inspection_yield"] is None
    assert all(v["safety_hold"] for v in c["vehicles"] if v["match"] in {"exact", "possible"})
    with pytest.raises(sc.CampaignError, match="approve"):
        act(c, "outreach")
    with pytest.raises(sc.CampaignError, match="recovery is required"):
        act(c, "approve", {"lane": "inspect", "note": "Reviewed"})
    c = act(c, "approve", {"lane": "recovery", "note": "Check critical seed and installed part records"})
    assert c["approval"]["simulated"] is True
    assert c["approval"]["message"] == c["notice_previews"]["recovery"]
    c = act(c, "outreach")
    assert c["metrics"]["outreach_simulated"] == 8  # exact + possible, excluding one without consent
    assert c["metrics"]["delivered"] == 0
    assert "notice" not in vehicle(c, "DEMO-CAR-007")
    assert "notice" not in vehicle(c, "DEMO-CAR-010")
    assert "notice" not in vehicle(c, "DEMO-CAR-011")
    assert all(v["notice"]["status"] == "simulated" for v in c["vehicles"] if v.get("notice"))
    c = act(c, "outreach")
    assert c["metrics"]["outreach_simulated"] == 8


def test_real_review_cannot_be_impersonated(campaign):
    c = sc.create_campaign({"title": "Workshop investigation", "supplier": "Supplier", "part_number": "Part-1", "lot_id": "Lot-A",
                            "component_name": "Control arm", "seed_evidence": "Inspection record 1"}, "operator", "agent")
    for kind in ("approve", "remedy", "close", "trace_review"):
        with pytest.raises(sc.CampaignError) as exc:
            act(c, kind, {})
        assert exc.value.status == 403


def test_replies_never_clear_and_new_symptoms_reopen(campaign):
    c = act(campaign, "reply", {"vehicle_id": "DEMO-CAR-001", "text": "No symptoms so far", "symptoms": ["none"]})
    assert vehicle(c)["safety_hold"]
    with pytest.raises(sc.CampaignError, match="inspection"):
        act(c, "resolve", {"vehicle_id": "DEMO-CAR-001", "note": "Owner says fine", "evidence_ref": "reply"})
    c = act(c, "reply", {"vehicle_id": "DEMO-CAR-001", "text": "Now I see a crack", "symptoms": ["crack"]})
    c = act(c, "reply", {"vehicle_id": "DEMO-CAR-001", "text": "No noise today", "symptoms": ["none"]})
    assert len(vehicle(c)["replies"]) == 3
    assert vehicle(c)["hazard"] and vehicle(c)["safety_hold"]
    assert c["metrics"]["replied"] == 1
    assert c["metrics"]["symptom_reports"] == 1
    for symptoms in ([], ["bogus"], ["none", "clunk"], "clunk"):
        with pytest.raises(sc.CampaignError):
            act(c, "reply", {"vehicle_id": "DEMO-CAR-001", "text": "Report", "symptoms": symptoms})


def repair_vehicle(c):
    vid = {"vehicle_id": "DEMO-CAR-001"}
    c = act(c, "appointment", {**vid, "workshop": "Demo workshop", "due_date": "2030-01-02", "reference": "SYN-BOOK-1"})
    assert vehicle(c)["appointment"]["transport"] == "recovery"
    c = act(c, "recovery", {**vid, "reference": "SYN-TOW-1", "note": "Transport completed"})
    # Inspections record facts before approval of outreach.
    c = act(c, "inspection", {**vid, "outcome": "crack_found", "technician": "Demo technician", "evidence_ref": "SYN-REPORT-1", "note": "Crack in arm"})
    assert c["approval"] is None
    with pytest.raises(sc.CampaignError, match="reviewed part"):
        act(c, "repair", {**vid, "replacement_part": "SYN-CA-2302"})
    c = act(c, "remedy", {"replacement_part": "SYN-CA-2302", "procedure_ref": "SYN-MANUAL-2", "approval_ref": "SYN-ENG-1", "note": "Reviewed applicability"})
    with pytest.raises(sc.CampaignError, match="match"):
        act(c, "repair", {**vid, "replacement_part": "GUESSED-PART"})
    c = act(c, "repair", {**vid, "replacement_part": "SYN-CA-2302", "replacement_lot": "SYN-LOT-C", "work_order": "SYN-WO-2", "technician": "Demo technician"})
    with pytest.raises(sc.CampaignError, match="Verify"):
        act(c, "resolve", {**vid, "evidence_ref": "SYN-RELEASE", "note": "Review"})
    c = act(c, "verify_repair", {**vid, "technician": "Demo verifier", "evidence_ref": "SYN-TEST-2", "note": "Manufacturer checks completed"})
    assert vehicle(c)["safety_hold"]  # only reviewer disposition can release
    with pytest.raises(sc.CampaignError, match="follow-up"):
        act(c, "resolve", {**vid, "evidence_ref": "SYN-RELEASE", "note": "Review"})
    c = act(c, "followup", {**vid, "outcome": "no_symptoms", "note": "Owner contacted after repair"})
    return act(c, "resolve", {**vid, "evidence_ref": "SYN-RELEASE", "note": "Verified repair and follow-up reviewed"})


def test_complete_repair_and_reopened_evidence(campaign):
    c = repair_vehicle(campaign)
    assert c["metrics"]["repair_verified"] == 1
    assert c["metrics"]["resolved"] == 1
    assert c["metrics"]["unresolved"] == 9
    assert vehicle(c)["safety_hold"] is False
    c = act(c, "reply", {"vehicle_id": "DEMO-CAR-001", "text": "Knocking is back", "symptoms": ["clunk"]})
    assert c["metrics"]["resolved"] == 0
    assert vehicle(c)["safety_hold"]
    assert "inspection" not in vehicle(c)  # new episode needs a fresh inspection
    assert c["metrics"]["confirmed_cracks"] == 1  # historical finding preserved
    assert c["metrics"]["inspected"] == 1
    with pytest.raises(sc.CampaignError, match="repair first"):
        act(c, "verify_repair", {"vehicle_id": "DEMO-CAR-001"})
    packet = sc.get_campaign(c["campaign_id"], packet=True)
    assert packet["packet"] == "safety-campaign-v1"
    assert any(e["kind"] == "repair" for e in packet["events"])
    assert "recalls avoided are not measured" in packet["method"]


def test_idempotency_stale_revision_and_cross_campaign(campaign):
    data = {"vehicle_id": "DEMO-CAR-001", "text": "Clunking sound", "symptoms": ["clunk"]}
    c = act(campaign, "reply", data, request_id="stable-id")
    duplicate = act(campaign, "reply", data, request_id="stable-id")
    assert duplicate["revision"] == c["revision"]
    assert len(vehicle(duplicate)["replies"]) == 1
    with pytest.raises(sc.CampaignError) as exc:
        act(campaign, "reply", {**data, "text": "Different report"}, request_id="stable-id")
    assert exc.value.status == 409
    with pytest.raises(sc.CampaignError, match="Campaign changed"):
        act(campaign, "reply", data, request_id="new-request")
    other = sc.demo_campaign("other", "agent")
    assert vehicle(other)["replies"] == []
    with pytest.raises(sc.CampaignError) as exc:
        act(c, "inspection", {"vehicle_id": "UNKNOWN"})
    assert exc.value.status == 404


def test_concurrent_writes_do_not_overwrite(campaign):
    def submit(i):
        try:
            return act(campaign, "reply", {"vehicle_id": f"DEMO-CAR-00{i}", "text": "Clunk", "symptoms": ["clunk"]}, request_id=f"concurrent-{i}")["revision"]
        except sc.CampaignError as exc:
            return exc.status
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(submit, [1, 2]))
    assert sorted(results) == [campaign["revision"] + 1, 409]


def test_import_is_atomic_and_trace_review_reopens_approval(campaign):
    buf = io.StringIO(); w = csv.writer(buf); w.writerow(sc.CSV_COLUMNS)
    w.writerow(["NEW-CAR", "NEW-OWNER", "Test", "SYN-AXLEWORKS", "SYN-CA-2301", "SYN-LOT-A", "verified", "SYN-RECORD", "yes", "sms"])
    w.writerow(["BAD-CAR", "BAD-OWNER", "Test", "", "", "", "verified", "SYN-RECORD", "yes", "sms"])
    with pytest.raises(sc.CampaignError):
        act(campaign, "import", {"csv": buf.getvalue()})
    unchanged = sc.get_campaign(campaign["campaign_id"])
    assert unchanged["metrics"]["registered"] == 12
    assert unchanged["revision"] == campaign["revision"]
    c = act(campaign, "approve", {"lane": "recovery", "note": "Reviewed"})
    c = act(c, "trace_review", {"vehicle_id": "DEMO-CAR-010", "supplier": "SYN-AXLEWORKS", "part_number": "SYN-CA-2301", "lot_id": "SYN-LOT-A", "source_ref": "SYN-SERVICE-10", "note": "Installed part label checked", "evidence_text": "FICTIONAL: DEMO-CAR-010 installation of SYN-AXLEWORKS SYN-CA-2301 from SYN-LOT-A."})
    assert c["approval"] is None
    assert vehicle(c, "DEMO-CAR-010")["match"] == "exact"


def test_closure_requires_dispositions_trace_and_supplier(campaign):
    with pytest.raises(sc.CampaignError, match="outstanding"):
        act(campaign, "close", {"regulatory_ref": "SYN-REG", "note": "Demo"})
    c = campaign
    # Resolve trace uncertainty using current installation records; do not erase the vehicles.
    for vid in ("DEMO-CAR-008", "DEMO-CAR-009", "DEMO-CAR-010"):
        c = act(c, "trace_review", {"vehicle_id": vid, "supplier": "SYN-AXLEWORKS", "part_number": "SYN-CA-2301", "lot_id": "SYN-LOT-A", "source_ref": "SYN-RECHECK", "note": "Record verified", "evidence_text": f"FICTIONAL: {vid} installation of SYN-AXLEWORKS SYN-CA-2301 from SYN-LOT-A."})
    for i in range(1, 11):
        data = {"vehicle_id": f"DEMO-CAR-{i:03}"}
        c = act(c, "inspection", {**data, "outcome": "no_issue", "technician": "Tech", "evidence_ref": "SYN-REPORT", "note": "Full scoped inspection"})
        c = act(c, "followup", {**data, "outcome": "no_symptoms", "note": "Follow-up recorded"})
        c = act(c, "resolve", {**data, "evidence_ref": "SYN-RELEASE", "note": "Qualified review of complete scope"})
    with pytest.raises(sc.CampaignError, match="supplier"):
        act(c, "close", {"regulatory_ref": "SYN-REG", "note": "Demo"})
    c = act(c, "supplier_action", {"owner": "Demo quality lead", "due_date": "2030-01-02", "status": "verified", "evidence_ref": "SYN-8D", "note": "Containment and corrective action verified"})
    c = act(c, "close", {"regulatory_ref": "SYN-REG", "note": "Manufacturer review recorded"})
    assert c["status"] == "closed"
    c = act(c, "reply", {"vehicle_id": "DEMO-CAR-001", "text": "New steering failure", "symptoms": ["loss_of_control"]})
    assert c["status"] != "closed"
    assert c["metrics"]["unresolved"] == 1


def test_failed_audit_write_rolls_back_state(campaign, monkeypatch):
    def fail(*args, **kwargs):
        raise RuntimeError("Audit unavailable")
    monkeypatch.setattr(sc, "_event", fail)
    with pytest.raises(RuntimeError):
        act(campaign, "reply", {"vehicle_id": "DEMO-CAR-001", "text": "Clunk", "symptoms": ["clunk"]})
    after = sc.get_campaign(campaign["campaign_id"])
    assert after["revision"] == campaign["revision"]
    assert vehicle(after)["replies"] == []


def test_negative_reinspection_cannot_erase_confirmed_repair_need(campaign):
    evidence = {"vehicle_id": "DEMO-CAR-001", "technician": "Tech", "evidence_ref": "SYN-REPORT", "note": "Recorded finding"}
    c = act(campaign, "inspection", {**evidence, "outcome": "crack_found"})
    c = act(c, "inspection", {**evidence, "outcome": "no_issue"})
    c = act(c, "followup", {"vehicle_id": "DEMO-CAR-001", "outcome": "no_symptoms", "note": "Owner says no noise"})
    with pytest.raises(sc.CampaignError, match="Verify the repair"):
        act(c, "resolve", {"vehicle_id": "DEMO-CAR-001", "evidence_ref": "SYN-RELEASE", "note": "Review"})
    assert c["metrics"]["confirmed_cracks"] == 1
    assert len(vehicle(c)["inspection_history"]) == 2


def test_meta_draft_is_grounded_and_cannot_change_safety(campaign, monkeypatch):
    from src.ai_layer import config, meta_client
    monkeypatch.setattr(config, "meta_enabled", lambda: False)
    assert sc.analyze_reply("Meri gaadi se awaaz aati hai")["mode"] == "manual"
    monkeypatch.setattr(config, "meta_enabled", lambda: True)
    monkeypatch.setattr(meta_client, "chat_json", lambda **kwargs: {"suggestions": [{"symptom": "none", "quote": "invented"}]})
    assert sc.analyze_reply("There is a crack")["suggestions"] == []
    monkeypatch.setattr(meta_client, "chat_json", lambda **kwargs: {"suggestions": [{"symptom": "clunk", "quote": "Clunking over bumps"}]})
    draft = sc.analyze_reply("Clunking over bumps")
    assert draft["mode"] == "meta" and draft["review_required"]
    assert sc.get_campaign(campaign["campaign_id"])["revision"] == campaign["revision"]
    def offline(**kwargs):
        raise meta_client.MetaError("timeout")
    monkeypatch.setattr(meta_client, "chat_json", offline)
    assert sc.analyze_reply("Noise")["mode"] == "manual"


def test_meta_draft_keeps_complete_report_after_pii_redaction(campaign, fake_meta):
    original = "Clunking over bumps; steering pulls left. Email demo@example.com"

    def extract(payload):
        report = json.loads(payload["messages"][1]["content"])["report"]
        assert "demo@example.com" not in report
        assert "[EMAIL]" in report
        return {"suggestions": [{"symptom": s, "quote": report} for s in ("clunk", "steering_pull")]}

    fake_meta.chat["safety_reply"] = extract
    draft = sc.analyze_reply(original)
    assert draft["mode"] == "meta" and draft["review_required"]
    assert [s["symptom"] for s in draft["suggestions"]] == ["clunk", "steering_pull"]
    assert all(s["quote"] == original for s in draft["suggestions"])
    assert sc.get_campaign(campaign["campaign_id"])["revision"] == campaign["revision"]

    # A short quote loses context; a denial conflicts with a positive finding.
    fake_meta.chat["safety_reply"] = lambda p: {"suggestions": [{"symptom": "clunk", "quote": "Clunking over bumps"}]}
    assert sc.analyze_reply(original)["mode"] == "manual"
    fake_meta.chat["safety_reply"] = lambda p: {"suggestions": [{"symptom": s, "quote": "Clunk"} for s in ("clunk", "none")]}
    assert sc.analyze_reply("Clunk")["suggestions"] == []


def test_api_permissions_validation_and_demo(reset_ops_db, monkeypatch):
    from fastapi.testclient import TestClient
    from src.api.main import app

    monkeypatch.setenv("FRONTLINE_OPEN_MODE", "1")
    client = TestClient(app)
    assert client.get("/api/safety-campaigns").status_code == 200
    created = client.post("/api/safety-campaigns/demo", json={})
    assert created.status_code == 200, created.text
    c = created.json()
    path = f"/api/safety-campaigns/{c['campaign_id']}"
    assert "notice_preview" in client.get(path).json()
    assert client.get(path + "/packet").json()["packet"] == "safety-campaign-v1"
    assert client.post(path + "/actions/reply", json={"revision": -1}).status_code == 422
    assert client.get("/api/safety-campaigns/missing").status_code == 404
    monkeypatch.setenv("FRONTLINE_OPEN_MODE", "0")
    monkeypatch.setenv("FRONTLINE_AUTH_REQUIRED", "1")
    monkeypatch.setenv("FRONTLINE_API_KEY", "test-pilot-key")
    assert client.get(path).status_code == 401
    # An operator key can rehearse a synthetic campaign, but cannot modify a real one.
    service_headers = {"X-API-Key": "test-pilot-key"}
    assert client.post("/api/safety-campaigns/demo", headers=service_headers, json={}).status_code == 200
    rehearsed = client.post(path + "/actions/approve", headers=service_headers,
                            json={"revision": c["revision"], "request_id": "operator-demo", "data": {"lane": "recovery", "note": "Demo review"}})
    assert rehearsed.status_code == 200
    c = rehearsed.json()
    real = sc.create_campaign({"title": "Real investigation", "supplier": "Supplier", "part_number": "Part", "lot_id": "Lot",
                               "component_name": "Arm", "seed_evidence": "Report"}, "operator", "agent")
    response = client.post(f"/api/safety-campaigns/{real['campaign_id']}/actions/approve", headers=service_headers,
                           json={"revision": real["revision"], "request_id": "forged", "data": {"lane": "recovery", "note": "test", "role": "supervisor"}})
    assert response.status_code == 403
    from src.api.rbac import issue_session
    supervisor = {"X-Frontline-Session": issue_session("quality-lead", "supervisor", issuer_role="admin")["token"]}
    approved = client.post(path + "/actions/approve", headers=supervisor,
                           json={"revision": c["revision"], "request_id": "signed-review", "data": {"lane": "recovery", "note": "Reviewed synthetic scope"}})
    assert approved.status_code == 200, approved.text
    assert approved.json()["approval"]["by"] == "quality-lead"
    assert approved.json()["approval"]["simulated"] is True
    forged = client.post("/api/safety-campaigns", headers=supervisor, json={"synthetic_demo": True})
    assert forged.status_code == 422


def test_prepared_demo_is_complete_repeatable_and_preserves_edits(reset_ops_db):
    c = sc.prepared_demo_campaign("operator", "service")
    m = c["metrics"]
    assert c["demo_version"] == sc.PREPARED_DEMO_VERSION
    assert (m["registered"], m["outreach_simulated"], m["replied"], m["inspected"]) == (12, 8, 8, 5)
    assert (m["confirmed_cracks"], m["repair_recorded"], m["repair_verified"], m["resolved"], m["unresolved"]) == (3, 2, 2, 2, 8)
    assert m["delivered"] == 0
    assert c["supplier_action"]["status"] == "contained"
    assert vehicle(c)["resolution"]["simulated"]
    assert vehicle(c, "DEMO-CAR-002")["followup"]["outcome"] == "unreachable"
    assert "repair" not in vehicle(c, "DEMO-CAR-003")
    assert "notice" not in vehicle(c, "DEMO-CAR-007")
    c = act(c, "reply", {"vehicle_id": "DEMO-CAR-001", "text": "Noise returned", "symptoms": ["clunk"]})
    reused = sc.prepared_demo_campaign("another-operator", "agent")
    assert reused["campaign_id"] == c["campaign_id"]
    assert reused["revision"] == c["revision"]
    assert vehicle(reused)["replies"][-1]["text"] == "Noise returned"
    assert len(sc.list_campaigns()) == 1


def test_failed_prepared_demo_does_not_leave_partial_rows(campaign, monkeypatch):
    original = sc.apply_action
    def fail(campaign_id, kind, *args, **kwargs):
        if kind == "remedy":
            raise sc.CampaignError("Injected preparation failure")
        return original(campaign_id, kind, *args, **kwargs)
    monkeypatch.setattr(sc, "apply_action", fail)
    with pytest.raises(sc.CampaignError, match="preparation failure"):
        sc.prepared_demo_campaign("operator", "service")
    remaining = sc.list_campaigns()
    assert len(remaining) == 1
    assert remaining[0]["campaign_id"] == campaign["campaign_id"]
