"""Current report-to-packet contracts; isolated encrypted turns and fake inference."""
import csv
import io
import json
from datetime import datetime, timedelta, timezone

import pytest

from src.ai_layer import campaign_investigator as ci, complaint_evidence as ce, config, meta_client
from src.ai_layer import report_sources as rs, safety_campaigns as sc
from src.data.turns import persist_turn
from src.data.warehouse import ops_con


@pytest.fixture
def scenario(reset_ops_db, monkeypatch):
    from src.frontline import dsr
    from src.security.pii import SubjectKeyStore
    # Mirror the fresh test warehouse in process-local erasure/key caches.
    monkeypatch.setattr(dsr, "_erasure_barrier", set())
    monkeypatch.setattr(SubjectKeyStore, "_keys", {})
    monkeypatch.setattr(SubjectKeyStore, "_shredded", set())
    monkeypatch.setattr(config, "meta_enabled", lambda: False)
    monkeypatch.setattr(meta_client, "chat_json", lambda **_: pytest.fail("No live inference in handoff tests"))
    c = sc.demo_campaign("fixture-operator", "agent")
    with ops_con() as con:
        con.execute("INSERT INTO interactions (interaction_id,pack_id,pack_version,started_at,ended_at,channel,status) VALUES ('voice-source','automotive_nhtsa','test',now(),now(),'web_voice','completed')")
    for seq, speaker, text in [(1, "customer", "My 2019 car knocks. owner@example.com"),
                               (2, "agent", "Was there a fire?"),
                               (3, "customer", "No fire. No, I said 2018.")]:
        persist_turn("voice-source", {"turn_id": f"turn-{seq}", "seq": seq, "speaker": speaker, "text": text})
    return c


def investigate(c, **extra):
    return ci.investigate(c["campaign_id"], {"vehicle_id": "DEMO-CAR-003", "revision": c["revision"],
        "request_id": "handoff", "source_ref": rs.interaction_report("voice-source")["source_ref"],
        "source_reviewed": True, "vehicle_association_confirmed": True, **extra}, "operator", "agent")


def test_stored_turns_reach_packet_with_lineage_and_redaction(scenario):
    preview = rs.interaction_report("voice-source")
    assert preview["source_ref"]["turn_ids"] == ["turn-1", "turn-3"]
    assert "owner@example.com" not in json.dumps(preview)
    assert "Was there a fire?" not in preview["source"]["text"]
    before = sc.get_campaign(scenario["campaign_id"])
    draft = investigate(scenario)
    source = draft["report_sources"][0]
    assert source["text"] == preview["source"]["text"]
    assert source["provenance"]["sha256"] == preview["source_ref"]["sha256"]
    assert source["vehicle_association"]["confirmed_by"] == "operator"
    assert source["vehicle_association"]["vehicle_id"] == "DEMO-CAR-003"
    citation = next(c for c in ce.citations([source]).values() if c["quote"] == "No fire.")
    assert citation["source_turn"]["turn_id"] == "turn-3"
    assert citation["source_turn"]["at"]
    assert citation["provenance"]["url"].endswith("/voice-source")
    assert ci.list_runs(scenario["campaign_id"])[0] == draft
    assert sc.get_campaign(scenario["campaign_id"]) == before


def test_unpunctuated_multilingual_turns_remain_citable_through_revision(scenario):
    # Browser/STT transcripts need not add terminal punctuation. Every stored
    # owner turn must remain available to the model, including denials/corrections.
    reports = ["No fire", "नहीं, मैंने 2018 कहा", "Meri Toyota Camry bumps par khat khat karti hai"]
    for seq, text in enumerate(reports, start=4):
        persist_turn("voice-source", {"turn_id": f"turn-{seq}", "seq": seq, "speaker": "customer", "text": text})
    preview = rs.interaction_report("voice-source")
    draft = investigate(scenario)
    source = draft["report_sources"][0]
    citations = ce.citations([source])
    for seq, text in enumerate(reports, start=4):
        matches = [c for c in citations.values() if c["quote"] == text]
        assert len(matches) == 1, f"Owner turn omitted or duplicated in citable evidence: {text}"
        citation = matches[0]
        assert citation["source_turn"]["turn_id"] == f"turn-{seq}"
        assert source["text"][citation["start"]:citation["end"]] == text
        assert citation["source_turn"]["at"]
    reviewed = ci.review(scenario["campaign_id"], draft["run_id"], {
        "decision": "needs_correction", "attestation": True,
        "note": "Fixture operator correction: keep the denial and model year 2018 explicit.",
    }, "fixture-engineer", "agent")
    revision = investigate(scenario, source_ref=None, request_id="unpunctuated-revision", parent_run_id=draft["run_id"])
    assert revision["report_sources"] == draft["report_sources"]
    assert revision["report_sources"][0]["source_ref"] == preview["source_ref"]
    assert revision["correction_context"]["review"] == reviewed["review"]
    assert ce.citations(revision["report_sources"]) == citations
    assert ci.list_runs(scenario["campaign_id"])[0] == reviewed


@pytest.mark.parametrize("text,quotes", [
    ("No fire\nModel year 2018\nKnocking", ["No fire", "Model year 2018", "Knocking"]),
    ("No fire\r\n\r\n  मॉडल वर्ष २०१८  \n", ["No fire", "मॉडल वर्ष २०१८"]),
    ("No smoke. No fire!\nसुधार: 2018।\nPart unknown", ["No smoke.", "No fire!", "सुधार: 2018।", "Part unknown"]),
])
def test_report_line_boundaries_preserve_exact_quotes(text, quotes):
    source = ce.source("line-boundaries", text)
    assert [s["quote"] for s in source["sentences"]] == quotes
    assert all(source["text"][s["start"]:s["end"]] == s["quote"] for s in source["sentences"])


def test_unreviewed_forged_changed_and_live_sources_are_refused(scenario):
    for kwargs in ({"source_reviewed": False}, {"vehicle_association_confirmed": False}, {"text": "Fabricated quote"}):
        with pytest.raises(sc.CampaignError):
            investigate(scenario, **kwargs)
    preview = rs.interaction_report("voice-source")
    wrong = {**preview["source_ref"], "turn_ids": ["turn-1"]}
    with pytest.raises(sc.CampaignError, match="selection"):
        investigate(scenario, source_ref=wrong)
    with ops_con() as con:
        con.execute("UPDATE interaction_turns SET text='Changed owner words' WHERE turn_id='turn-3'")
    with pytest.raises(sc.CampaignError, match="changed"):
        investigate(scenario, source_ref=preview["source_ref"])
    assert ci.list_runs(scenario["campaign_id"]) == []
    with ops_con() as con:
        con.execute("UPDATE interactions SET status='active', ended_at=NULL WHERE interaction_id='voice-source'")
    with pytest.raises(sc.CampaignError, match="End the report"):
        rs.interaction_report("voice-source")


def test_erased_source_blocks_reuse_and_review(scenario):
    draft = investigate(scenario)
    with ops_con() as con:
        con.execute("UPDATE interaction_turns SET erased=TRUE WHERE turn_id='turn-3'")
    with pytest.raises(sc.CampaignError) as exc:
        rs.interaction_report("voice-source")
    assert exc.value.status == 410
    with pytest.raises(sc.CampaignError, match="no longer"):
        ci.review(scenario["campaign_id"], draft["run_id"], {"decision": "accepted_for_investigation", "note": "Read sources", "attestation": True}, "operator", "agent")


def test_recorded_reply_keeps_author_date_and_vehicle_scope(scenario):
    c = sc.apply_action(scenario["campaign_id"], "reply", {"vehicle_id": "DEMO-CAR-003", "text": "No smoke.", "symptoms": ["none"]}, "report-author", "agent", scenario["revision"], "reply")
    reply = next(v for v in c["vehicles"] if v["vehicle_id"] == "DEMO-CAR-003")["replies"][0]
    preview = rs.reply_report(c["campaign_id"], "DEMO-CAR-003", reply["reply_id"])
    draft = investigate(c, source_ref=preview["source_ref"])
    provenance = draft["report_sources"][0]["provenance"]
    assert provenance["author"] == "report-author" and provenance["at"] == reply["at"]
    assert provenance["reply_id"] == reply["reply_id"]
    with pytest.raises(sc.CampaignError, match="not found"):
        investigate(c, request_id="wrong-vehicle", vehicle_id="DEMO-CAR-004", source_ref=preview["source_ref"])


def test_review_correction_reaches_both_model_stages_without_rewriting_history(scenario, monkeypatch):
    monkeypatch.setattr(config, "meta_enabled", lambda: True)
    contexts = []
    denial_id = next(c["sentence_id"] for c in ce.citations([rs.interaction_report("voice-source")["source"]]).values() if c["quote"] == "No fire.")
    def provider(**kw):
        body = json.loads(kw["user"])
        if kw["schema_name"] == "complaint_evidence_v1":
            contexts.append(body["planning_context"]["correction_context"])
            return {"observations": [], "unknown_fields": ["part"], "defect_label_id": "other_unclear", "label_sentence_ids": [], "lookups": [], "followup_field": "none"}
        contexts.append(body["correction_context"])
        return {"claims": [{"interpretation": "The report needs clarification" if not body["correction_context"] else "Owner denied fire", "relationship": "unresolved", "sentence_ids": [denial_id]}], "next_step": "review_only", "followup_field": "none"}
    monkeypatch.setattr(meta_client, "chat_json", provider)
    draft = investigate(scenario)
    review = {"decision": "needs_correction", "note": "Make the owner's denial explicit", "attestation": True,
              "corrections": [{"claim_index": 0, "decision": "correct", "correction": "Owner said no fire; retain the denial. Contact owner@example.com."}]}
    reviewed = ci.review(scenario["campaign_id"], draft["run_id"], review, "engineer", "agent")
    updated = investigate(scenario, request_id="revision", parent_run_id=draft["run_id"], source_ref=None)
    assert updated["turn"] == 2 and updated["report_sources"] == draft["report_sources"]
    assert updated["brief"]["claims"][0]["interpretation"] == "Owner denied fire"
    assert all(c["review"]["corrections"][0]["correction"].startswith("Owner said no fire") for c in contexts[-2:])
    assert "owner@example.com" not in json.dumps(contexts)
    assert ci.list_runs(scenario["campaign_id"])[0] == reviewed
    assert reviewed["brief"]["claims"][0]["interpretation"] == "The report needs clarification"


@pytest.mark.parametrize("dead_process", [True, False])
def test_interrupted_reservation_is_recoverable_without_automatic_spend(scenario, dead_process):
    draft = investigate(scenario)
    with ops_con() as con:
        draft.update(status="running", process_id="old-process" if dead_process else ci.PROCESS_ID,
                     started_at=(datetime.now(timezone.utc)-timedelta(seconds=ci.RUN_LEASE_SECONDS+1)).isoformat())
        con.execute("UPDATE safety_investigation_runs SET status='running', result=? WHERE run_id=?", [json.dumps(draft), draft["run_id"]])
    recovered = ci.list_runs(scenario["campaign_id"])[0]
    assert recovered["status"] == "interrupted" and recovered["retry_requires_new_request"]
    assert investigate(scenario) == recovered
    assert investigate(scenario, request_id="explicit-retry")["status"] == "complete"


def test_csv_verified_is_only_an_assertion_until_documented_review(scenario):
    buf = io.StringIO(); writer = csv.writer(buf); writer.writerow(sc.CSV_COLUMNS)
    writer.writerow(["NEW-CAR", "OWNER", "Model", "SYN-AXLEWORKS", "SYN-CA-2301", "SYN-LOT-A", "verified", "DOC-1", "yes", "sms"])
    c = sc.apply_action(scenario["campaign_id"], "import", {"csv": buf.getvalue()}, "importer", "agent", scenario["revision"], "import-new")
    row = next(v for v in c["vehicles"] if v["vehicle_id"] == "NEW-CAR")
    assert row["match"] == "possible" and row["trace_status"] == "unverified"
    assert row["source_asserted_trace_status"] == "verified" and row["import_provenance"]["sha256"]
    data = {k: row[k] for k in ("vehicle_id", "supplier", "part_number", "lot_id", "source_ref")}
    with pytest.raises(sc.CampaignError, match="evidence_text"):
        sc.apply_action(c["campaign_id"], "trace_review", {**data, "note": "Reviewed"}, "engineer", "agent", c["revision"], "missing-document")
    reviewed = sc.apply_action(c["campaign_id"], "trace_review", {**data, "note": "Reviewed fictional installation", "evidence_text": "FICTIONAL RECORD: NEW-CAR received SYN-CA-2301 from SYN-LOT-A, SYN-AXLEWORKS."}, "engineer", "agent", c["revision"], "review-document")
    row = next(v for v in reviewed["vehicles"] if v["vehicle_id"] == "NEW-CAR")
    assert row["match"] == "exact"
    assert row["trace_review"]["by"] == "engineer" and row["trace_review"]["at"]
    assert row["trace_review"]["source_sha256"] == row["installation_evidence"]["sha256"]
    with ops_con() as con:
        state = sc._load(con, c["campaign_id"])
        state["vehicles"]["NEW-CAR"]["installation_evidence"]["text"] = "Changed document"
        con.execute("UPDATE safety_campaigns SET state=? WHERE campaign_id=?", [json.dumps(state), c["campaign_id"]])
    changed = sc.get_campaign(c["campaign_id"])
    assert next(v for v in changed["vehicles"] if v["vehicle_id"] == "NEW-CAR")["match"] == "possible"


def test_source_routes_require_authenticated_read_and_ignore_client_authority(scenario, monkeypatch):
    from fastapi.testclient import TestClient
    from src.api.main import app
    client = TestClient(app)
    monkeypatch.setenv("FRONTLINE_OPEN_MODE", "1")
    path = "/api/safety-campaigns/report-sources/interactions/voice-source"
    assert client.get(path).status_code == 200
    body = {"vehicle_id": "DEMO-CAR-003", "revision": scenario["revision"], "request_id": "api-source", **rs.interaction_report("voice-source")}
    body.pop("source"); body.pop("status"); body.pop("channel")
    base = f"/api/safety-campaigns/{scenario['campaign_id']}"
    assert client.post(base+"/investigations", json=body).status_code == 400
    body.update(source_reviewed=True, vehicle_association_confirmed=True)
    response = client.post(base+"/investigations", json=body)
    assert response.status_code == 200, response.text
    packet = client.get(base+"/packet").json()
    assert packet["investigation_drafts"][0]["report_sources"][0]["provenance"]["interaction_id"] == "voice-source"
    monkeypatch.setenv("FRONTLINE_OPEN_MODE", "0")
    monkeypatch.setenv("FRONTLINE_AUTH_REQUIRED", "1")
    monkeypatch.setenv("FRONTLINE_API_KEY", "isolated-handoff-test-key")
    assert client.get(path).status_code == 401
    assert client.post(base+"/investigations", json=body).status_code == 401


@pytest.mark.parametrize("mode", ["tombstone", "erase", "crypto_shred"])
def test_contact_erasure_purges_derived_sources_and_packet_content(scenario, mode):
    from src.frontline.dsr import delete_interaction
    draft = investigate(scenario)
    child = investigate(scenario, source_ref=None, request_id="child", parent_run_id=draft["run_id"], text="Additional fictional symptom details.")
    result = delete_interaction("voice-source", mode=mode)
    assert result["ok"], result
    runs = ci.list_runs(scenario["campaign_id"])
    assert len(runs) == 2 and all(r["status"] == "erased" for r in runs)
    assert all(r["report_sources"] == [] and r["sources"] == [] for r in runs)
    assert "Additional fictional symptom" not in json.dumps(runs)
    assert "My 2019 car" not in json.dumps(runs)
    with ops_con() as con:
        stored = con.execute("SELECT result FROM safety_investigation_runs WHERE run_id=?", [child["run_id"]]).fetchone()[0]
    assert "No fire" not in stored and "correction_context" not in stored


@pytest.mark.parametrize("stop", ["expire", "erase", "expire_then_erase"])
def test_stopped_worker_cannot_start_second_call_or_revive_content(scenario, monkeypatch, stop):
    monkeypatch.setattr(config, "meta_enabled", lambda: True)
    if stop == "expire_then_erase":
        read_saved = ci.stored_run
        def erase_after_interruption(con, run_id):
            saved = read_saved(con, run_id)
            if saved["status"] == "interrupted":
                from src.frontline.dsr import delete_interaction
                assert delete_interaction("voice-source", mode="tombstone")["ok"]
            return saved
        monkeypatch.setattr(ci, "stored_run", erase_after_interruption)
    calls = []
    def provider(**kw):
        calls.append(kw["schema_name"])
        if len(calls) > 1:
            pytest.fail("Stopped run started another model call")
        if stop == "erase":
            from src.frontline.dsr import delete_interaction
            assert delete_interaction("voice-source", mode="tombstone")["ok"]
        else:
            with ops_con() as con:
                row = con.execute("SELECT run_id,result FROM safety_investigation_runs WHERE status='running'").fetchone()
                saved = json.loads(row[1])
                saved["started_at"] = (datetime.now(timezone.utc)-timedelta(seconds=ci.RUN_LEASE_SECONDS+1)).isoformat()
                con.execute("UPDATE safety_investigation_runs SET result=? WHERE run_id=?", [json.dumps(saved), row[0]])
        return {"observations": [], "unknown_fields": ["part"], "defect_label_id": "other_unclear", "label_sentence_ids": [], "lookups": [], "followup_field": "none"}
    monkeypatch.setattr(meta_client, "chat_json", provider)
    result = investigate(scenario)
    assert result["status"] == ("interrupted" if stop == "expire" else "erased")
    assert len(calls) == 1
    assert ci.list_runs(scenario["campaign_id"])[0] == result
    if stop != "expire":
        assert "My 2019 car" not in json.dumps(result)
    else:
        assert result["model_calls"] is None and result["inference_outcome_uncertain"]
