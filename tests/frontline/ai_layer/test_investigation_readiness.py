"""Critical claim, retrieval and operational contracts with isolated fake transport."""
import json

import pytest

from src.ai_layer import claim_support, complaint_evidence as ce, campaign_investigator as ci
from src.ai_layer import config, meta_client, report_sources as rs, safety_campaigns as sc


@pytest.mark.parametrize("text,quote,polarity,reason", [
    ("Fire occurred", "No fire.", "affirmed", "denial_reversed:fire"),
    ("Fire occurred", "No fire.", "denied", "denial_reversed:fire"),
    ("आग लगी", "आग नहीं लगी।", "affirmed", "denial_reversed:fire"),
    ("Model year 2019", "My car is a 2018 model.", "affirmed", "number_or_identifier_not_in_citation:2019"),
    ("Installed SYN-PART-23", "Installed SYN-PART-22.", "affirmed", "number_or_identifier_not_in_citation:syn-part-23"),
])
def test_critical_transformations_are_withheld(text, quote, polarity, reason):
    assert reason in claim_support.support_issues(text, [quote], polarity=polarity)
    proposal = {"observations": [{"field": "symptom", "value": text, "polarity": polarity, "sentence_id": "report:1"}]}
    result = ce.validate_extraction(proposal, [ce.source("report", quote)], ["other_unclear"])
    assert not result["observations"] and result["withheld_observations"][0]["support_issues"]


def test_negation_and_equivalent_hindi_digits_are_retained():
    assert not claim_support.support_issues("Owner denied fire", ["No fire."], polarity="denied")
    assert not claim_support.support_issues("Model year 2018", ["मॉडल वर्ष २०१८"], polarity="affirmed")
    assert not claim_support.support_issues("A no-symptom reply", ["No symptoms reported."])


@pytest.fixture
def campaign(reset_ops_db, monkeypatch):
    monkeypatch.setattr(config, "meta_enabled", lambda: True)
    def provider(**kw):
        if kw["schema_name"] == "complaint_evidence_v1":
            return {"observations": [{"field": "symptom", "value": "Knocking", "polarity": "affirmed", "sentence_id": "report-1:1"}], "unknown_fields": ["part"], "defect_label_id": "other_unclear", "label_sentence_ids": [], "lookups": ["installed_part"], "followup_field": "part"}
        return {"claims": [{"interpretation": "Reported knocking; cause unknown", "relationship": "unresolved", "sentence_ids": ["report-1:1"]}], "next_step": "review_trace", "followup_field": "part"}
    monkeypatch.setattr(meta_client, "chat_json", provider)
    return sc.demo_campaign("fixture", "agent")


def run(c, **kw):
    return ci.investigate(c["campaign_id"], {"vehicle_id": "DEMO-CAR-003", "revision": c["revision"], "request_id": "contract", "text": "Knocking over bumps.", **kw}, "fixture", "agent")


def test_every_interpretation_needs_review_and_conditions_do_not_cross(campaign):
    draft = run(campaign)
    data = {"decision": "accepted_for_investigation", "attestation": True, "note": "Read original"}
    with pytest.raises(sc.CampaignError, match="every"):
        ci.review(campaign["campaign_id"], draft["run_id"], data, "fixture", "agent")
    reviewed = ci.review(campaign["campaign_id"], draft["run_id"], {**data,
        "corrections": [{"claim_index": 0, "decision": "accept"}],
        "observation_corrections": [{"observation_index": 0, "decision": "accept"}]}, "fixture", "agent")
    assert reviewed["review"]["observation_corrections"][0]["original_observation"]["value"] == "Knocking"
    extraction = run(campaign, request_id="extraction", assistance_mode="extraction_only")
    assert extraction["model_calls"] == 1 and extraction["tool_trace"] == [] and extraction["brief"]["claims"] == []
    with pytest.raises(sc.CampaignError, match="comparison condition"):
        run(campaign, request_id="wrong-condition", parent_run_id=extraction["run_id"])


def test_older_records_can_be_retrieved_without_cross_vehicle_access(campaign):
    c = campaign
    for i in range(7):
        c = sc.apply_action(c["campaign_id"], "reply", {"vehicle_id": "DEMO-CAR-003", "text": f"Report {i}.", "symptoms": ["other"]}, "fixture", "agent", c["revision"], f"reply-{i}")
    first = rs.vehicle_records(c["campaign_id"], "DEMO-CAR-003", "owner_history")
    older = rs.vehicle_records(c["campaign_id"], "DEMO-CAR-003", "owner_history", offset=first["next_offset"])
    assert first["total"] == 7 and len(first["sources"]) == 5 and len(older["sources"]) == 2
    assert older["next_offset"] is None and older["sources"][-1]["text"] == "Report 0."
    vehicle = next(v for v in c["vehicles"] if v["vehicle_id"] == "DEMO-CAR-003")
    lookup = ci.lookup("owner_history", c, vehicle)
    assert lookup[0]["retrieval"]["omitted_older_records"] == 2
    full = rs.vehicle_records(c["campaign_id"], "DEMO-CAR-003", "installed_part")["source"]
    snapshot = ci.lookup("installed_part", c, vehicle)[0]
    assert full["sha256"] == snapshot["full_sha256"]
    full_workshop = rs.vehicle_records(c["campaign_id"], "DEMO-CAR-003", "workshop_history")["source"]
    assert full_workshop["sha256"] == ci.lookup("workshop_history", c, vehicle)[0]["full_sha256"]
    with pytest.raises(sc.CampaignError):
        rs.vehicle_records(c["campaign_id"], "FOREIGN-VEHICLE", "owner_history")
    with pytest.raises(sc.CampaignError):
        rs.vehicle_records(c["campaign_id"], "DEMO-CAR-003", "owner_history", offset=-1)


def test_actual_adapter_attempt_metadata_has_hashes_usage_and_no_prompt_text(reset_ops_db, monkeypatch, tmp_path):
    for name, val in {"META_BUDGET_PATH": str(tmp_path/"budget.sqlite"), "META_CAP_PATH": str(tmp_path/"cap.json"), "META_RESOURCE_PATH": str(tmp_path/"host"), "META_BACKEND": "meta", "META_MODEL_TEXT": "muse-spark-1.3"}.items():
        monkeypatch.setenv(name, val)
    monkeypatch.setattr(config, "meta_enabled", lambda: True)
    monkeypatch.setattr(config, "active_api_key", lambda: "test-only-not-a-real-key")
    monkeypatch.setattr(config, "retries", lambda: 1)
    monkeypatch.setattr(meta_client, "guard_url", lambda url: url)
    monkeypatch.setattr(meta_client, "_cap_state", {})
    attempts = []
    def transport(url, body, headers, timeout):
        payload = json.loads(body); attempts.append(payload)
        if len(attempts) == 1:
            raise TimeoutError("synthetic timeout")
        name = payload["response_format"]["json_schema"]["name"]
        value = ({"observations": [], "unknown_fields": ["part"], "defect_label_id": "other_unclear", "label_sentence_ids": [], "lookups": [], "followup_field": "part"} if name == "complaint_evidence_v1" else {"claims": [], "next_step": "review_only", "followup_field": "part"})
        return meta_client.HttpResponse(200, json.dumps({"choices": [{"message": {"content": json.dumps(value)}}], "usage": {"prompt_tokens": 100, "completion_tokens": 50}}).encode())
    monkeypatch.setattr(meta_client, "_transport", transport)
    c = sc.demo_campaign("fixture", "agent")
    result = run(c)
    assert len(result["operations"]) == 3 and result["model_calls"] == 2
    summary = result["operational_summary"]
    assert summary["transport_attempts"] == 3 and summary["successful_responses"] == 2
    assert summary["reserved_upper_bound_usd"] > 0 and summary["actual_billed_cost_usd"] is None
    assert summary["unmetered_attempts"] == 1 and summary["stage_latency_ms"]
    assert all(len(op["prompt_sha256"]) == 64 and op["live_transport"] is False for op in result["operations"])
    assert "Knocking over bumps" not in json.dumps(result["operations"])
    assert "test-only-not-a-real-key" not in json.dumps(result)
