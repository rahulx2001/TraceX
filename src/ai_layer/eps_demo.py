"""Canonical fictional LotGuard EPS walkthrough, using real intake/campaign services.

Origin markers and campaign request IDs make a interrupted run resumable. Reuse
preserves operator edits; this seed never deletes saved cases or campaigns.
"""
from __future__ import annotations

import asyncio
import csv
import hashlib
import io
import json
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

from src.data.warehouse import domain_con, ops_con, ops_in_thread

VERSION = "lotguard-eps-b14-v1"
CLUSTER_ID = 9014
ADVISORY_ID = "SYN-EPS-B14-ADVISORY"
PACK_ID = "automotive_nhtsa"
SUPPLIER = "SYN-EPSWORKS"
PART = "SYN-EPS-21"
LOT = "B14"
_seed_lock = asyncio.Lock()


def origin_fields(summary) -> dict:
    try:
        origin = json.loads(summary) if isinstance(summary, str) else (summary or {})
    except (ValueError, TypeError):
        origin = {}
    if not isinstance(origin, dict):
        origin = {}
    return {"synthetic_demo": origin.get("synthetic_demo") is True,
            "demo_hero": origin.get("hero") is True,
            "demo_scenario": origin.get("scenario"), "interaction_origin": origin}


def _domain_fixture():
    from src.ai_layer.lotguard import _assignment_distances
    from src.frontline.supplier import attach_supply, lot_trace
    from src.frontline.live_intercept import open_or_link_investigation

    now = datetime.now(timezone.utc)
    # Eleven current complaints plus separately labelled prior-week history.
    rows = []
    for i in range(11):
        text = f"Fictional intake {i + 1}: Honda City EPS batch B14 intermittent heavy steering, steering warning light at parking speed. Vehicle parked for review."
        rows.append((f"EPS-B14-{i:02}", "SERVICE", "High" if i in (1, 2) else "Medium", "MH", i % 6, text))
    for week, count in ((1, 6), (2, 3), (3, 1)):
        for i in range(count):
            rows.append((f"EPS-B14-H{week}-{i}", "WARRANTY", "Medium", "MH", week * 7 + i,
                         "Fictional prior-week history: Honda City EPS B14 heavy steering and steering warning light."))
    with domain_con(PACK_ID, read_only=False) as con:
        for rid, source, severity, region, ago, text in rows:
            year = "2021" if rid.startswith("EPS-B14-H") or int(rid[-2:]) < 6 else "2022"
            con.execute("""INSERT INTO records
                (record_id, occurred_at, received_at, entity_1, entity_2, entity_3,
                 category, text, severity_label, region, source, entity_key, provenance)
                VALUES (?, ?, ?, ?, 'HONDA', 'CITY', 'STEERING', ?, ?, ?, ?, ?, 'synthetic_demo')
                ON CONFLICT DO NOTHING""",
                [rid, now - timedelta(days=ago), now - timedelta(days=ago), year,
                 text, severity, region, source, f"{year}|HONDA|CITY"])
        con.execute("""INSERT INTO clusters
            (cluster_id, pack_id, top_terms, category, record_count, first_seen, last_seen)
            VALUES (?, ?, ?, 'STEERING', ?, ?, ?) ON CONFLICT DO NOTHING""",
            [CLUSTER_ID, PACK_ID, json.dumps(["EPS", "heavy steering", "warning", "B14"]), len(rows), now - timedelta(days=21), now])
        have = {r[0] for r in con.execute("SELECT record_id FROM cluster_assignments WHERE cluster_id = ?", [CLUSTER_ID]).fetchall()}
        for rid, distance in _assignment_distances(rows):
            if rid not in have:
                con.execute("INSERT INTO cluster_assignments VALUES (?, ?, ?)", [rid, CLUSTER_ID, distance])
        con.execute("""INSERT INTO advisories VALUES (?, ?, NULL, 'HONDA', 'CITY', 'STEERING', ?, ?, ?, 'synthetic_demo') ON CONFLICT DO NOTHING""",
                    [ADVISORY_ID, now, "FICTIONAL DEMO advisory: Honda City 2021–22 steering complaints; EPS B14 applicability requires installation review.",
                     "DEMO: keep abnormal-steering vehicles parked, arrange workshop inspection. C0035 is an ABS wheel-speed clue, not EPS confirmation.",
                     "https://example.invalid/fictional-eps-b14"])
    for rid, *_ in rows:
        if lot_trace(rid) is None:
            attach_supply(record_id=rid, pack_id=PACK_ID, supplier=SUPPLIER, lot_id=LOT,
                          lot_start="2021-01-01", lot_end="2022-12-31")
    return open_or_link_investigation(pack_id=PACK_ID, cluster_id=CLUSTER_ID,
            title="LotGuard DEMO · Honda City · EPS B14", category="STEERING", entity_2="HONDA", entity_3="CITY")


async def _contact(index: int) -> str:
    from src.agents.orchestrator import create_interaction, OrchestratorHooks
    with ops_con(read_only=True) as con:
        existing = con.execute("""SELECT c.case_id FROM cases c JOIN interactions i USING(interaction_id)
            WHERE json_extract_string(i.summary, '$.scenario') = ?
            AND json_extract_string(i.summary, '$.index') = ?""", [VERSION, str(index)]).fetchall()
    if len(existing) > 1:
        raise RuntimeError("Duplicate canonical intake markers; manual review required")
    if existing:
        with ops_con(read_only=True) as con:
            match = con.execute("SELECT cluster_match_id, advisory_match_id FROM cases WHERE case_id = ?", [existing[0][0]]).fetchone()
        if match != (CLUSTER_ID, ADVISORY_ID):
            raise RuntimeError(f"Saved demo intake {index} cannot reproduce the canonical match; review before refresh")
        return existing[0][0]
    last = [""]
    async def said(text, meta):
        last[0] = text
    orch, _ = await create_interaction(channel="simulated", pack_id=PACK_ID,
        hooks=OrchestratorHooks(emit_customer_turn=said), locale="en-IN",
        synthetic_origin={"scenario": VERSION, "index": index, "hero": index == 0,
                          "owner_ref": f"eps-owner-{index:03}@example.invalid",
                          "contact_consent": True, "channel": "email", "batch": LOT})
    year = "2021" if index < 6 else "2022"
    description = f"My {year} Honda City has intermittent heavy steering and a steering warning light at parking speed. It is parked safely at home."
    if index in (0, 1):
        description += " The mechanic's scan tool showed fault code C0035; please record the code exactly."
    if index == 0:
        description += " It started three days ago, happens twice each morning and is worse after rain. The wheel becomes heavy while turning left. Workshop invoice lists EPS batch B14. I have a photo of that label."
    await orch.handle_customer_turn(description)
    for _ in range(10):
        if orch.ctx.state in {"DONE", "ABANDONED", "SUPERVISED", "CLOSING"}:
            break
        question = last[0].lower()
        if any(k in question for k in ("year", "model", "make", "vehicle")):
            reply = f"It is a {year} Honda City. The problem is heavy steering with a warning light."
        elif any(k in question for k in ("hurt", "injur")):
            reply = "Nobody is hurt. The vehicle is parked safely at home."
        elif any(k in question for k in ("safe", "park")):
            reply = "Yes, I am safe and the car is parked at home."
        elif any(k in question for k in ("correct", "right", "confirm")):
            reply = "Yes, that is correct. Please complete my steering report."
        else:
            reply = "The steering becomes heavy while turning at parking speed; the steering warning light appears."
        await orch.handle_customer_turn(reply)
    if orch.ctx.state != "DONE":
        await orch.hangup()
    if not orch.ctx.case_id:
        raise RuntimeError(f"Canonical intake {index} did not create a case")
    # Fail visibly if the normal matcher cannot reproduce the judged scenario.
    if (orch.ctx.investigation_brief or {}).get("cluster_id") != CLUSTER_ID or (orch.ctx.advisory_match or {}).get("advisory_id") != ADVISORY_ID:
        raise RuntimeError(f"Canonical intake {index} did not reproduce its cluster/advisory")
    return orch.ctx.case_id


def synthetic_eps_png() -> bytes:
    from PIL import Image, ImageDraw
    img = Image.new("RGB", (720, 420), "#eef2f6")
    draw = ImageDraw.Draw(img)
    draw.text((24, 20), "LOTGUARD - FICTIONAL DEMO IMAGE", fill="#15283c")
    draw.rounded_rectangle((120, 140, 610, 280), radius=24, fill="#586777")
    draw.rectangle((340, 154, 560, 245), fill="white")
    draw.text((354, 168), "SYN-EPSWORKS / SYN-EPS-21", fill="black")
    draw.text((354, 194), "EPS batch B14 / Honda City", fill="black")
    draw.text((354, 220), "SYNTHETIC LABEL", fill="#a12323")
    draw.text((24, 330), "Batch label illustration only. No crack diagnosis from this image.", fill="#15283c")
    out = io.BytesIO(); img.save(out, format="PNG")
    return out.getvalue()


def _hero_evidence(case_id: str):
    from src.ai_layer.evidence import list_for_case, store_evidence
    from src.frontline.ops import add_case_note, list_case_notes
    if not list_for_case(case_id):
        store_evidence(data=synthetic_eps_png(), filename="FICTIONAL_eps_B14_label.png", declared_mime="image/png", case_id=case_id)
    if not list_case_notes(case_id):
        add_case_note(case_id, "FICTIONAL DEMO reviewer assessment: 11 current-week Honda City steering intakes linked to B14 through synthetic installation records. Photo is a batch-label illustration, not crack evidence. C0035 indicates a left-front wheel-speed/ABS circuit; investigate the code/steering mismatch separately. Two scoped severe parent reports raise review priority to High; this caller's reported symptoms remain Medium. Workshop must inspect EPS, connections and ABS wiring before any part decision. Owner destination collected in synthetic origin with consent; follow-up delivery is a stub.", author="Demo reviewer (scripted)")


def _campaign(investigation_id: str, hero_id: str) -> dict:
    from src.ai_layer import safety_campaigns as sc
    candidates = [c for c in sc.list_campaigns() if c.get("demo_version") == VERSION]
    c = sc.get_campaign(candidates[0]["campaign_id"]) if candidates else sc.create_campaign({
        "title": "LotGuard DEMO · Honda City EPS B14", "supplier": SUPPLIER, "part_number": PART,
        "lot_id": LOT, "component_name": "EPS assembly", "seed_evidence": f"FICTIONAL source case {hero_id}; cluster {CLUSTER_ID}; illustration is not a diagnosis.",
        "investigation_id": investigation_id, "demo_context": {"version": VERSION, "hero_case_id": hero_id,
        "vehicle_scope": "2021–22 Honda City", "inbound_vehicle_ids": [f"EPS-CITY-{i:03}" for i in range(11)]}},
        "Demo setup", "agent", demo=True)
    def step(key: str, kind: str, data: dict):
        nonlocal c
        with ops_con(read_only=True) as con:
            if con.execute("SELECT 1 FROM safety_campaign_events WHERE campaign_id = ? AND request_id = ?", [c["campaign_id"], f"eps-{key}"]).fetchone():
                return
        c = sc.apply_action(c["campaign_id"], kind, data, "Demo reviewer (scripted)", "agent", c["revision"], f"eps-{key}")
    if not c["vehicles"]:
        buf = io.StringIO(); writer = csv.writer(buf); writer.writerow(sc.CSV_COLUMNS)
        for i in range(213):
            writer.writerow([f"EPS-CITY-{i:03}", f"eps-owner-{i:03}@example.invalid", "2021 Honda City" if i < 107 else "2022 Honda City", SUPPLIER, PART, LOT, "unverified", f"SYN-INSTALL-{i:03}", "yes", "email"])
        step("import", "import", {"csv": buf.getvalue()})
    for i in range(213):
        vid = f"EPS-CITY-{i:03}"
        step(f"trace-{i}", "trace_review", {"vehicle_id": vid, "supplier": SUPPLIER, "part_number": PART,
            "lot_id": LOT, "source_ref": f"SYN-INSTALL-{i:03}", "evidence_text": f"FICTIONAL installation record {vid}: {SUPPLIER}, {PART}, EPS batch B14 installed. Demo fixture, not a manufacturer record.", "note": "Simulated reviewer verified the fictional installed-part scope."})
    # Prepared outcome replay is scripted reviewer approval, never an AI approval.
    step("approve", "approve", {"lane": "inspect", "note": "FICTIONAL scripted reviewer approval: installation scope and English/Hindi owner notices checked. This decision is simulated."})
    step("outreach", "outreach", {})
    warned = [f"EPS-CITY-{i:03}" for i in range(11, 213)]
    step("delivered", "simulate_receipt", {"status": "delivered", "vehicle_ids": warned})
    step("opened", "simulate_receipt", {"status": "opened", "vehicle_ids": warned[:68]})
    for i in range(11, 79):
        step(f"reply-{i}", "reply", {"vehicle_id": f"EPS-CITY-{i:03}", "text": "YES, please offer a workshop inspection slot." if i < 52 else "No symptoms noticed; please route this to the workshop for advice.", "symptoms": ["none"]})
    for i in range(11, 52):
        step(f"booking-{i}", "appointment", {"vehicle_id": f"EPS-CITY-{i:03}", "workshop": "Fictional City Workshop", "due_date": (date.today() + timedelta(days=2)).isoformat(), "reference": f"SYN-SLOT-{i:03}"})
    step("remedy", "remedy", {"replacement_part": "SYN-EPS-22", "procedure_ref": "FICTIONAL-EPS-PROCEDURE", "approval_ref": "FICTIONAL-ENGINEERING-REVIEW", "note": "Demo only: replace exact assembly after confirmed inspection; do not use this specification on a real vehicle."})
    for i in range(11, 20):
        vid = f"EPS-CITY-{i:03}"
        step(f"inspect-{i}", "inspection", {"vehicle_id": vid, "outcome": "crack_found", "technician": "Fictional technician", "evidence_ref": f"SYN-INSPECTION-{i}", "note": "FICTIONAL finding: EPS housing crack found during preventive inspection after warning; no prior failure reported. This record is a simulated technician finding, not image AI output."})
        step(f"repair-{i}", "repair", {"vehicle_id": vid, "replacement_part": "SYN-EPS-22", "replacement_lot": "SYN-B15", "work_order": f"SYN-WO-{i}", "technician": "Fictional technician"})
        step(f"verify-{i}", "verify_repair", {"vehicle_id": vid, "technician": "Fictional verifier", "evidence_ref": f"SYN-VERIFY-{i}", "note": "Simulated post-repair checks against fictional procedure."})
        step(f"followup-{i}", "followup", {"vehicle_id": vid, "outcome": "no_symptoms", "note": "Simulated owner reports no symptoms after repair."})
        step(f"resolve-{i}", "resolve", {"vehicle_id": vid, "evidence_ref": f"SYN-RESOLUTION-{i}", "note": "Simulated reviewer checked inspection, repair verification and follow-up."})
    step("supplier", "supplier_action", {"owner": "Fictional supplier quality lead", "due_date": (date.today() + timedelta(days=7)).isoformat(), "status": "contained", "evidence_ref": "SYN-8D-B14", "note": "Simulated B14 stock containment; root cause and corrective-action effectiveness remain open."})
    return c


def _investigation(campaign: dict, hero_id: str) -> dict:
    from src.ai_layer import campaign_investigator as ci, report_sources
    runs = [r for r in ci.list_runs(campaign["campaign_id"]) if r.get("request_id") == "eps-hero-investigation"]
    if runs:
        if runs[0]["status"] != "complete":
            raise RuntimeError("Canonical investigation cannot be refreshed; review its failed run")
        return runs[0]
    with ops_con(read_only=True) as con:
        iid = con.execute("SELECT interaction_id FROM cases WHERE case_id = ?", [hero_id]).fetchone()[0]
    source = report_sources.interaction_report(iid)
    run = ci.investigate(campaign["campaign_id"], {"vehicle_id": "EPS-CITY-000",
        "source_ref": source["source_ref"], "source_reviewed": True, "vehicle_association_confirmed": True,
        "revision": campaign["revision"], "request_id": "eps-hero-investigation"}, "Demo reviewer (scripted)", "agent")
    if run["status"] != "complete":
        raise RuntimeError("Canonical investigation failed; original evidence is preserved")
    return run


async def seed_eps_demo() -> dict:
    async with _seed_lock:
        investigation_id = await ops_in_thread(_domain_fixture)
        ids = {}
        for i in [*range(1, 11), 0]:
            ids[i] = await _contact(i)
        await ops_in_thread(_hero_evidence, ids[0])
        campaign = await ops_in_thread(_campaign, investigation_id, ids[0])
        run = await ops_in_thread(_investigation, campaign, ids[0])
        return {"synthetic_demo": True, "message": "All records are fictional; your saved changes are preserved.",
                "scenario": VERSION, "hero_case_id": ids[0], "case_ids": [ids[i] for i in range(11)],
                "cluster_id": CLUSTER_ID, "advisory_id": ADVISORY_ID, "investigation_id": investigation_id,
                "campaign_id": campaign["campaign_id"], "metrics": campaign["metrics"],
                "investigation_run_id": run["run_id"],
                "case_url": f"#cases?id={ids[0]}", "campaign_url": f"#safety-campaigns?campaign={campaign['campaign_id']}"}


def lot_for_case(case_id: str) -> dict:
    from src.ai_layer import safety_campaigns as sc
    with ops_con(read_only=True) as con:
        row = con.execute("SELECT c.cluster_match_id, i.summary FROM cases c JOIN interactions i USING(interaction_id) WHERE c.case_id = ?", [case_id]).fetchone()
    if not row:
        raise LookupError("Case not found")
    meta = origin_fields(row[1])
    campaigns = [c for c in sc.list_campaigns() if c.get("demo_version") == meta["demo_scenario"]] if meta["demo_scenario"] else []
    if not campaigns:
        return {"available": False, "reason": "No linked lot campaign is recorded for this case."}
    c = sc.get_campaign(campaigns[0]["campaign_id"]); m = c["metrics"]
    inbound = c["demo_context"]["inbound_vehicle_ids"]
    with ops_con(read_only=True) as con:
        cases = [r[0] for r in con.execute("SELECT c.case_id FROM cases c JOIN interactions i USING(interaction_id) WHERE json_extract_string(i.summary, '$.scenario') = ? ORDER BY c.created_at DESC", [meta["demo_scenario"]]).fetchall()]
    with domain_con(PACK_ID, read_only=True) as con:
        rows = con.execute("SELECT record_id, received_at FROM records WHERE record_id LIKE 'EPS-B14-%'").fetchall()
    anchor = max(r[1] for r in rows)
    trend = [{"weeks_ago": week, "reports": sum(week * 7 <= (anchor - r[1]).days < (week + 1) * 7 for r in rows)} for week in (3, 2, 1, 0)]
    return {"available": True, "synthetic_demo": True, "delivery_mode": "simulation_only", "lot_id": LOT,
        "lot_size": m["registered"], "reported": len(cases), "inbound_owners": len(inbound),
        "initially_silent": m["registered"] - len(inbound), "contacted": m["simulated_delivered"],
        "silent_after_warning": m["awaiting_reply"], "failure_trend": trend,
        "trend_metric": "reported_symptoms_per_week", "outcomes": {"opened_or_routed": m["simulated_opened"], "bookings": m["booked"], "findings": m["confirmed_cracks"], "resolved": m["resolved"]},
        "vehicles_warned_before_failure": m["vehicles_warned_before_failure"],
        "supporting_vehicle_ids": m["vehicles_warned_before_failure_ids"], "sibling_case_ids": cases,
        "campaign_id": c["campaign_id"], "timeline": [{"kind": e["kind"], "at": e["at"], "revision": e["revision"]} for e in c["events"] if e["kind"] in {"approve", "outreach", "simulate_receipt", "supplier_action"}],
        "metric_definition": "Fictional vehicles with simulated warning delivered before a confirmed inspection finding, verified repair and resolution, with no prior failure reported. Accidents prevented are not measured.",
        "evaluation": frozen_evaluation()}


def frozen_evaluation() -> dict:
    from src.config import REPO_ROOT
    manifest = json.loads((Path(__file__).with_name("eps_demo_evaluation.json")).read_text())
    changed = [p for p, digest in manifest["sha256"].items() if not (REPO_ROOT / p).is_file() or hashlib.sha256((REPO_ROOT / p).read_bytes()).hexdigest() != digest]
    if changed:
        return {"verified": False, "reason": "Frozen evaluation artifacts changed; refresh and review the regression gate.", "changed": changed}
    return {**manifest["metrics"], "verified": True, "source": "reports/improvement/human_reviews/round4/accuracy_v2.json",
            "limitations": "Historical 300-record evaluation; AI-assisted adjudication, human-countersigned. This is classifier accuracy, not accident prediction accuracy."}
