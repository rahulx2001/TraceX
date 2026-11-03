"""Consent-gated fictional follow-up outbox; never contacts a provider."""
import hashlib
import json
from src.data.warehouse import ops_con
from src.data.timeutil import utc_now
from src.ledger import AgentAction
from src.ledger.writer import record_action_on_con

DDL = """CREATE TABLE IF NOT EXISTS demo_case_followups (
 case_id VARCHAR, draft_sha256 VARCHAR, destination VARCHAR, channel VARCHAR,
 status VARCHAR, sent_at VARCHAR, PRIMARY KEY(case_id, draft_sha256))"""


def delivery_for_case(case_id: str) -> dict | None:
    with ops_con() as con:
        con.execute(DDL)
        row = con.execute("SELECT destination, channel, status, sent_at, draft_sha256 FROM demo_case_followups WHERE case_id = ? ORDER BY sent_at DESC LIMIT 1", [case_id]).fetchone()
    return dict(zip(("destination", "channel", "status", "sent_at", "draft_sha256"), row)) if row else None


def send_demo_followup(case_id: str, actor: str) -> dict:
    with ops_con() as con:
        con.execute(DDL)
        row = con.execute("SELECT c.followup_draft, i.summary, i.channel, i.interaction_id FROM cases c JOIN interactions i USING(interaction_id) WHERE c.case_id = ?", [case_id]).fetchone()
        if not row:
            raise LookupError("Case not found")
        origin = json.loads(row[1] or "{}")
        if row[2] != "simulated" or origin.get("synthetic_demo") is not True:
            raise ValueError("Customer delivery is not connected for live cases in this pilot")
        destination = origin.get("owner_ref", "")
        if not origin.get("contact_consent") or not destination.endswith("@example.invalid"):
            raise ValueError("A fictional destination and recorded consent are required")
        text = row[0] or ""
        if not text.strip():
            raise ValueError("Save a reviewed follow-up draft before sending")
        digest = hashlib.sha256(text.encode()).hexdigest()
        if not con.execute("SELECT 1 FROM demo_case_followups WHERE case_id = ? AND draft_sha256 = ?", [case_id, digest]).fetchone():
            con.execute("BEGIN TRANSACTION")
            try:
                con.execute("INSERT INTO demo_case_followups VALUES (?, ?, ?, ?, 'simulated_delivered', ?)", [case_id, digest, destination, origin.get("channel", "email"), utc_now().isoformat()])
                record_action_on_con(con, AgentAction(interaction_id=row[3], agent="supervisor", action_type="followup_simulated_delivered", case_id=case_id, input_summary=f"reviewed by {actor}; consent=true; draft_sha256={digest}", output_summary="Fictional outbox delivery; no provider contacted"))
                con.execute("COMMIT")
            except Exception:
                con.execute("ROLLBACK")
                raise
    return delivery_for_case(case_id)
