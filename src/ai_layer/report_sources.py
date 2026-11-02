"""Resolve reviewed reports from durable records, never from client-supplied quotes."""
from __future__ import annotations

import hashlib
import json
from datetime import timezone
from urllib.parse import quote

from src.ai_layer import complaint_evidence as evidence, safety_campaigns as sc
from src.data.turns import decrypt_turn_rows, ERASED_TURN
from src.data.warehouse import ops_con
from src.security.pii import redact_pii


def digest(value) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False, default=str).encode()).hexdigest()


def timestamp(value):
    if value is None:
        return None
    if hasattr(value, "isoformat"):
        return value.replace(tzinfo=value.tzinfo or timezone.utc).isoformat()
    return str(value)


def interaction_report(interaction_id: str) -> dict:
    with ops_con() as con:
        header = con.execute("SELECT status, channel, started_at, ended_at, erased, schema_version FROM interactions WHERE interaction_id=?", [interaction_id]).fetchone()
        if not header:
            raise sc.CampaignError("Stored interaction not found", 404)
        if header[4]:
            raise sc.CampaignError("The original report is no longer available", 410)
        if header[0] not in {"completed", "abandoned", "failed", "escalated"} or not header[3]:
            raise sc.CampaignError("End the report before reviewing its stored source; refresh after it is saved", 409)
        rows = con.execute("SELECT turn_id, seq, speaker, text, ts, erased FROM interaction_turns WHERE interaction_id=? AND speaker='customer' ORDER BY seq", [interaction_id]).fetchall()
    turns = decrypt_turn_rows(interaction_id, [dict(zip(("turn_id", "seq", "speaker", "text", "ts", "erased"), row)) for row in rows])
    if not turns:
        raise sc.CampaignError("No stored owner turns are available for this report", 409)
    if any(t["erased"] or t["text"] == ERASED_TURN or t["text"].startswith("enc:v1:") for t in turns):
        raise sc.CampaignError("An original source turn is no longer available", 410)
    if len(turns) > 100 or sum(len(t["text"]) + 1 for t in turns) > 8000:
        raise sc.CampaignError("This report exceeds the 8,000-character investigation limit. Review it in the contact record; no turns were silently omitted.")
    records = [{"turn_id": t["turn_id"], "seq": t["seq"], "speaker": t["speaker"], "at": timestamp(t["ts"]), "text": t["text"]} for t in turns]
    original_hash = digest({"interaction_id": interaction_id, "schema_version": header[5], "turns": records})
    ref = {"kind": "interaction", "interaction_id": interaction_id, "turn_ids": [t["turn_id"] for t in records], "sha256": original_hash}
    visible, offset = [], 0
    for t in records:
        text = redact_pii(t["text"])
        visible.append({**t, "text": text, "sha256": digest(t), "start": offset, "end": offset + len(text)})
        offset += len(text) + 1
    source = evidence.source("interaction-" + interaction_id, "\n".join(t["text"] for t in visible), "stored_owner_interaction")
    source.update(source_ref=ref, turns=visible, provenance={
        "kind": "interaction", "interaction_id": interaction_id, "version": header[5], "sha256": original_hash,
        "started_at": timestamp(header[2]), "ended_at": timestamp(header[3]), "channel": header[1],
        "url": "/api/safety-campaigns/report-sources/interactions/" + quote(interaction_id, safe=""),
        "redacted": True, "omitted_owner_turns": 0})
    return {"source_ref": ref, "source": source, "status": header[0], "channel": header[1]}


def reply_report(campaign_id: str, vehicle_id: str, reply_id: str) -> dict:
    campaign = sc.get_campaign(campaign_id)
    vehicle = next((v for v in campaign["vehicles"] if v["vehicle_id"] == vehicle_id), None)
    reply = next((r for r in vehicle["replies"] if r["reply_id"] == reply_id), None) if vehicle else None
    if not reply:
        raise sc.CampaignError("Original owner reply not found for this campaign and vehicle", 404)
    original_hash = digest(reply)
    ref = {"kind": "campaign_reply", "reply_id": reply_id, "sha256": original_hash}
    source = evidence.source("reply-" + reply_id, reply["text"], "recorded_operator_transcription")
    source.update(source_ref=ref, provenance={"kind": "campaign_reply", "campaign_id": campaign_id, "vehicle_id": vehicle_id,
        "reply_id": reply_id, "at": reply["at"], "author": reply["by"], "speaker": "owner_as_transcribed_by_operator",
        "version": 1, "sha256": original_hash, "synthetic_demo": campaign["synthetic_demo"], "redacted": True,
        "url": "/api/safety-campaigns/" + "/".join(quote(v, safe="") for v in (campaign_id, "report-sources", "replies", vehicle_id, reply_id))})
    return {"source_ref": ref, "source": source}


def resolve(ref: dict, campaign_id: str, vehicle_id: str) -> dict:
    if not isinstance(ref, dict):
        raise sc.CampaignError("A stored source reference is required")
    if ref.get("kind") == "interaction":
        result = interaction_report(sc.required(ref, "interaction_id", 160))
    elif ref.get("kind") == "campaign_reply":
        result = reply_report(campaign_id, vehicle_id, sc.required(ref, "reply_id", 160))
    else:
        raise sc.CampaignError("Unsupported report source")
    if ref != result["source_ref"]:
        raise sc.CampaignError("Original report changed or its source selection differs. Reload and review the stored report again.", 409)
    return result["source"]


def vehicle_records(campaign_id: str, vehicle_id: str, kind: str, offset: int = 0, limit: int = 5) -> dict:
    """Bounded pages of original records, scoped to an authorized campaign vehicle."""
    if kind not in {"owner_history", "installed_part", "workshop_history"}:
        raise sc.CampaignError("Unsupported vehicle record kind")
    if type(offset) is not int or offset < 0 or type(limit) is not int or not 1 <= limit <= 20:
        raise sc.CampaignError("Use a nonnegative offset and limit between 1 and 20")
    campaign = sc.get_campaign(campaign_id)
    vehicle = next((v for v in campaign["vehicles"] if v["vehicle_id"] == vehicle_id), None)
    if vehicle is None:
        raise sc.CampaignError("Vehicle is not registered in this campaign", 404)
    url = f"/api/safety-campaigns/{quote(campaign_id, safe='')}/vehicles/{quote(vehicle_id, safe='')}/records/{kind}?offset={offset}&limit={limit}"
    if kind == "owner_history":
        rows = list(reversed(vehicle.get("replies", [])))
        selected = rows[offset:offset+limit]
        sources = [reply_report(campaign_id, vehicle_id, row["reply_id"])["source"] for row in selected]
        return {"kind": kind, "vehicle_id": vehicle_id, "snapshot_revision": campaign["revision"], "sources": sources,
                "offset": offset, "total": len(rows), "returned": len(selected),
                "next_offset": offset+len(selected) if offset+len(selected) < len(rows) else None}
    if kind == "installed_part":
        row = {k: vehicle.get(k) for k in ("model", "supplier", "part_number", "lot_id", "trace_status", "source_ref", "match", "source_asserted_trace_status", "import_provenance", "installation_evidence", "trace_review")}
        total = 1
    else:
        history = list(reversed(vehicle.get("inspection_history", [])))
        total = len(history)
        row = {k: vehicle.get(k) for k in ("inspection_history", "repair", "repair_verification", "followup", "resolution")}
        row["inspection_history"] = history[offset:offset+limit]
    source = evidence.source(f"{kind}-page-{offset}", json.dumps(row, ensure_ascii=False, default=str), kind)
    source["provenance"] = {"kind": kind, "campaign_id": campaign_id, "vehicle_id": vehicle_id,
                            "snapshot_revision": campaign["revision"], "sha256": digest(row), "url": url}
    source["retrieval"] = {"total_records": total, "offset": offset, "returned_records": 1 if kind == "installed_part" else len(row["inspection_history"]),
                            "omitted_older_records": max(0, total-offset-limit) if kind == "workshop_history" else 0}
    return {"source": source, "kind": kind, "offset": offset, "total": total,
            "next_offset": offset+limit if kind == "workshop_history" and offset+limit < total else None}
