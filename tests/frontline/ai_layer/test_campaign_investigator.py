import json

import pytest

from src.ai_layer import campaign_investigator as investigator, complaint_evidence as ce, config, meta_client, safety_campaigns as sc


def extraction(sid="report-1:1"):
    return {"observations": [{"field": "symptom", "value": "Knocking", "polarity": "affirmed", "sentence_id": sid}],
            "unknown_fields": ["part", "failure_mode"], "defect_label_id": "other_unclear", "label_sentence_ids": [],
            "lookups": ["installed_part", "workshop_history"], "followup_field": "timing"}


def fake_provider(**kwargs):
    if kwargs["schema_name"] == "complaint_evidence_v1":
        return extraction()
    return {"claims": [{"interpretation": "A knocking symptom was reported; the cause remains unverified.",
                        "relationship": "unresolved", "sentence_ids": ["report-1:1"]}],
            "next_step": "review_inspection", "followup_field": "timing"}


@pytest.fixture
def prepared(reset_ops_db, monkeypatch):
    monkeypatch.setattr(config, "meta_enabled", lambda: True)
    monkeypatch.setattr(meta_client, "chat_json", fake_provider)
    return sc.prepared_demo_campaign("operator", "agent")


def run(c, **kwargs):
    return investigator.investigate(c["campaign_id"], {"vehicle_id": "DEMO-CAR-003", "text": "Knocking over bumps.",
               "revision": c["revision"], "request_id": "run-1", **kwargs}, "operator", "agent")


def test_citations_are_attached_from_redacted_source_not_model():
    sources = [ce.source("report-1", "No fuel leak. My email is owner@example.com.")]
    data = extraction()
    data["observations"][0].update(value="Fuel leak denied", polarity="denied")
    accepted = ce.validate_extraction(data, sources, ["other_unclear"])
    assert accepted["observations"][0]["evidence"]["quote"] == "No fuel leak."
    assert "owner@example.com" not in json.dumps(sources)
    invalid = extraction("not-a-source")
    invalid.update(defect_label_id="fuel_pump_failure", label_sentence_ids=["not-a-source"])
    rejected = ce.validate_extraction(invalid, sources, ["other_unclear", "fuel_pump_failure"])
    assert rejected["observations"] == [] and rejected["defect_label_id"] == "other_unclear"
    data.update(defect_label_id="fuel_pump_failure", label_sentence_ids=["report-1:1"])
    assert ce.validate_extraction(data, sources, ["other_unclear", "fuel_pump_failure"])["defect_label_id"] == "other_unclear"


def test_full_readonly_loop_preserves_campaign_state_and_history(prepared):
    before = sc.get_campaign(prepared["campaign_id"])
    result = run(prepared)
    assert result["status"] == "complete" and result["model_calls"] == 2
    assert [r["tool"] for r in result["tool_trace"]] == ["installed_part", "workshop_history"]
    assert result["brief"]["claims"][0]["evidence"][0]["quote"] == "Knocking over bumps."
    assert result["review"] is None
    assert sc.get_campaign(prepared["campaign_id"]) == before
    assert investigator.list_runs(prepared["campaign_id"])[0] == result


def test_idempotent_retry_does_not_call_provider_again(prepared, monkeypatch):
    result = run(prepared)
    monkeypatch.setattr(meta_client, "chat_json", lambda **_: pytest.fail("Retry spent another model call"))
    assert run(prepared) == result
    with pytest.raises(sc.CampaignError) as exc:
        run(prepared, text="Changed report")
    assert exc.value.status == 409


def test_cross_campaign_parent_and_turn_limits(prepared):
    parent = run(prepared)
    other = sc.demo_campaign("operator", "agent")
    with pytest.raises(sc.CampaignError, match="parent"):
        run(other, parent_run_id=parent["run_id"])
    child = run(prepared, parent_run_id=parent["run_id"], request_id="run-2", text="It started before repair.")
    assert child["turn"] == 2 and len(child["report_sources"]) == 2
    third = run(prepared, parent_run_id=child["run_id"], request_id="run-3", text="I have a workshop record.")
    with pytest.raises(sc.CampaignError, match="limit"):
        run(prepared, parent_run_id=third["run_id"], request_id="run-4")


def test_unconfigured_fallback_keeps_evidence_but_makes_no_ai_claim(prepared, monkeypatch):
    monkeypatch.setattr(config, "meta_enabled", lambda: False)
    result = run(prepared)
    assert result["model_calls"] == 0 and result["extraction"]["mode"] == "manual"
    assert result["brief"]["claims"] == [] and result["tool_trace"] == []
    assert result["report_sources"][0]["text"] == "Knocking over bumps."


def test_timeout_falls_back_and_invented_brief_citations_rejected(prepared, monkeypatch):
    def provider(**kw):
        if kw["schema_name"] == "complaint_evidence_v1":
            return extraction()
        return {"claims": [{"interpretation": "Invented", "relationship": "supports", "sentence_ids": ["foreign:1"]}],
                "next_step": "review_only", "followup_field": "none"}
    monkeypatch.setattr(meta_client, "chat_json", provider)
    result = run(prepared)
    assert result["brief"]["rejected_claims"] == 1 and not result["brief"]["claims"]
    def timeout(**_):
        raise meta_client.MetaError("meta_timeout")
    monkeypatch.setattr(meta_client, "chat_json", timeout)
    result = run(prepared, request_id="timeout")
    assert result["extraction"]["mode"] == "manual" and result["model_calls"] == 1


def test_review_attestation_staleness_and_immutable_decision(prepared):
    result = run(prepared)
    data = {"note": "Compared every claim with its source", "decision": "accepted_for_investigation", "attestation": True,
            "corrections": [{"claim_index": 0, "decision": "accept"}],
            "observation_corrections": [{"observation_index": 0, "decision": "accept"}]}
    with pytest.raises(sc.CampaignError, match="Confirm"):
        investigator.review(prepared["campaign_id"], result["run_id"], {**data, "attestation": False}, "operator", "agent")
    reviewed = investigator.review(prepared["campaign_id"], result["run_id"], data, "operator", "agent")
    assert reviewed["review"]["synthetic_demo"] is True
    with pytest.raises(sc.CampaignError, match="already"):
        investigator.review(prepared["campaign_id"], result["run_id"], data, "operator", "agent")
    next_run = run(prepared, request_id="another")
    sc.apply_action(prepared["campaign_id"], "reply", {"vehicle_id": "DEMO-CAR-003", "text": "More noise", "symptoms": ["clunk"]},
                    "operator", "agent", prepared["revision"], "reply-1")
    with pytest.raises(sc.CampaignError, match="changed"):
        investigator.review(prepared["campaign_id"], next_run["run_id"], data, "operator", "agent")


def test_real_campaign_review_requires_supervisor(prepared):
    c = sc.create_campaign({"title": "Real pilot", "supplier": "S", "part_number": "P", "lot_id": "L", "component_name": "Part",
                            "seed_evidence": "Workshop record"}, "operator", "agent")
    with pytest.raises(sc.CampaignError) as exc:
        investigator.review(c["campaign_id"], "anything", {"attestation": True, "note": "Checked", "decision": "needs_correction"}, "operator", "agent")
    assert exc.value.status == 403


def test_lookup_refuses_arbitrary_tools(prepared):
    with pytest.raises(sc.CampaignError):
        investigator.lookup("approve_campaign", prepared, prepared["vehicles"][0])


def test_api_routes_auth_packets_and_csp(prepared, monkeypatch):
    from fastapi.testclient import TestClient
    from src.api.main import app
    monkeypatch.setenv("FRONTLINE_OPEN_MODE", "1")
    client = TestClient(app)
    base = f"/api/safety-campaigns/{prepared['campaign_id']}"
    body = {"vehicle_id": "DEMO-CAR-003", "text": "Knocking over bumps.", "revision": prepared["revision"], "request_id": "api-run"}
    result = client.post(base+"/investigations", json=body)
    assert result.status_code == 200, result.text
    rid = result.json()["run_id"]
    assert client.get(base+"/packet").json()["investigation_drafts"][0]["run_id"] == rid
    assert client.post(base+"/investigations", json={**body, "role": "supervisor"}).status_code == 422
    page = client.get("/api/safety-campaigns/review-kit/fuel-complaints")
    assert page.status_code == 200 and 'src="/ui/review-scripts/evidence-review.js"' in page.text
    assert "script-src 'self'" in page.headers["content-security-policy"]
    assert "<script>" not in page.text
    assert client.get("/api/safety-campaigns/review-kit/not-a-file").status_code == 404
    monkeypatch.setenv("FRONTLINE_OPEN_MODE", "0")
    monkeypatch.setenv("FRONTLINE_AUTH_REQUIRED", "1")
    monkeypatch.setenv("FRONTLINE_API_KEY", "isolated-test-key")
    assert client.get(base+"/investigations").status_code == 401
    assert client.get("/api/safety-campaigns/review-kit/fuel-complaints").status_code == 401
    assert client.post(base+"/investigations", json=body).status_code == 401
