"""LotGuard seed: one verified cracked part → supplier lot → investigation.  [AI-LAYER]

Synthetic, labelled demo data only. Seed records use
``provenance='synthetic_demo'`` so they COUNT in analytics (unlike
``'fixture'``/``'inferred'``), and every surface must label them synthetic.
Nothing here invents metrics: counts, tiers and yields are computed from
these rows by the existing deterministic code.

Scenario: a workshop verifies a cracked front lower control arm on a 2023
Honda CR-V. The part traces to supplier lot ``LOT-SYN-2023-03-A``. History
rows put the slice on the safety board; registered owners feed the
verification loop (Step 3); an optional simulated Hinglish contact shows
Meta intake joining the same investigation.
"""

from __future__ import annotations

import json
import math
import struct
import zlib
from datetime import datetime, timedelta, timezone
from typing import Any

PACK_ID = "automotive_nhtsa"
PROVENANCE = "synthetic_demo"
CLUSTER_ID = 9001
SCENARIO_LABEL = "synthetic LotGuard demo lot (control-arm crack)"

LOT = {
    "supplier": "SYN-AXLEWORKS",
    "lot_id": "LOT-SYN-2023-03-A",
    "lot_start": "2023-03-01",
    "lot_end": "2023-04-15",
}

SLICE = {"category": "SUSPENSION", "entity_1": "2023", "entity_2": "HONDA", "entity_3": "CR-V"}

# (record_id, source, severity, region, days_ago, text)
SEED_RECORDS: tuple[tuple[str, str, str, str, int, str], ...] = (
    ("LGD-SEED-001", "SERVICE", "Critical", "MH",
     2, "Workshop verified: front left lower control arm hairline crack found during inspection; "
        "customer reported clunking over bumps for three weeks."),
    ("LGD-HIST-002", "NHTSA", "Medium", "CA",
     21, "Loud clunk from front left suspension over speed bumps; dealer found a cracked control arm."),
    ("LGD-HIST-003", "WARRANTY", "Medium", "TX",
     34, "Uneven front tyre wear and steering pull; control arm bushing torn, arm replaced under warranty."),
    ("LGD-HIST-004", "NHTSA", "High", "NY",
     48, "Front suspension collapsed at low speed after weeks of clunking; nearly caused an accident."),
    ("LGD-HIST-005", "SERVICE", "Medium", "MH",
     55, "Customer heard knocking from front suspension; inspection found a cracked lower control arm."),
    ("LGD-HIST-006", "NHTSA", "Medium", "FL",
     70, "Repeated clunking noise from front left wheel area on rough roads."),
    ("LGD-HIST-007", "WARRANTY", "High", "OH",
     83, "Steering wandered and the car briefly lost control on the highway; dealer replaced a cracked control arm."),
    ("LGD-HIST-008", "NHTSA", "Low", "WA",
     95, "Squeaking from front suspension when turning at parking speed."),
)

# One off-slice decoy so clustering/risk code sees contrast.
DECOY_RECORD = ("LGD-DECOY-009", "NHTSA", "Low", "MI", 40,
                "Power window stopped working on the driver side.")

LOTGUARD_TURNS = [
    "Namaste. Meri 2023 Honda CR-V mein speed breaker par aage se khat-khat ki awaaz aati hai, left side se.",
    "Steering thoda khinchta bhi hai aur tyre ek taraf se ghis raha hai.",
]
_FOLLOW_UPS = [
    (("safe location", "are you safe"), "Yes, I am safe. Gaadi ghar par park hai."),
    (("hurt", "injur"), "No, nobody is hurt."),
    (("year", "model", "make", "vehicle"), "It is a 2023 Honda CR-V."),
    (("right", "correct", "confirm", "did i get"), "Haan, sahi hai."),
]
_DEFAULT_REPLY = "Aage left suspension se khat-khat ki awaaz aati hai speed breaker par."


def synthetic_crack_png(width: int = 480, height: int = 360) -> bytes:
    """Deterministic synthetic 'cracked control arm' picture as PNG bytes."""
    rows = []
    for y in range(height):
        row = bytearray([0])
        for x in range(width):
            # dark arm bar across the middle with a jagged bright crack
            in_bar = height * 0.38 < y < height * 0.62
            crack_x = width * 0.5 + 26 * math.sin(y * 0.11)
            if in_bar and abs(x - crack_x) < 3:
                row += bytes((235, 235, 230))
            elif in_bar:
                g = 88 + int(10 * math.sin(x * 0.2 + y * 0.1))
                row += bytes((g, g, g + 6))
            else:
                bg = 34 + int(10 * (y / height))
                row += bytes((bg, bg + 2, bg + 4))
        rows.append(bytes(row))

    def chunk(tag: bytes, data: bytes) -> bytes:
        return struct.pack(">I", len(data)) + tag + data + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)

    ihdr = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)
    text = chunk(b"tEXt", b"Comment\x00LotGuard SYNTHETIC demo image - not a real vehicle photo")
    return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", ihdr) + text
            + chunk(b"IDAT", zlib.compress(b"".join(rows), 6)) + chunk(b"IEND", b""))


def _assignment_distances(rows: list[tuple]) -> list[tuple[str, float]]:
    """Real cosine distances to the seed centroid (never a constant per row)."""
    from src.ml_runtime.embeddings import cosine, embed_text, fit_idf

    texts = {r[0]: r[5] for r in rows}
    try:
        fit_idf(list(texts.values()))
    except Exception:
        pass
    try:
        vecs = {rid: embed_text(txt) for rid, txt in texts.items()}
        dim = len(next(iter(vecs.values())))
        centroid = [0.0] * dim
        for v in vecs.values():
            for d, x in enumerate(v):
                centroid[d] += x
        n = float(len(vecs))
        centroid = [x / n for x in centroid]
        norm = math.sqrt(sum(x * x for x in centroid)) or 1.0
        centroid = [x / norm for x in centroid]
        out = []
        for rid, v in vecs.items():
            try:
                dist = max(0.0, min(2.0, 1.0 - cosine(v, centroid)))
            except ValueError:
                dist = 1.0
            out.append((rid, dist))
        return out
    finally:
        try:
            from src.ml_runtime.embeddings import reset_idf

            reset_idf()
        except Exception:
            pass


def _insert_domain_rows(pack_id: str) -> dict[str, Any]:
    """Insert seed records + cluster + assignments. Re-run safe (skips existing)."""
    from src.data.warehouse import domain_con

    now = datetime.now(timezone.utc)
    inserted_records: list[str] = []
    with domain_con(pack_id, read_only=False) as con:
        have = {r[0] for r in con.execute("SELECT record_id FROM records").fetchall()}
        rows = [
            (rid, src, sev, reg, ago, txt, SLICE["entity_1"], SLICE["entity_2"],
             SLICE["entity_3"], SLICE["category"])
            for rid, src, sev, reg, ago, txt in SEED_RECORDS
        ]
        drid, dsrc, dsev, dreg, dago, dtxt = DECOY_RECORD
        rows.append((drid, dsrc, dsev, dreg, dago, dtxt, "2020", "FORD", "F-150", "ELECTRICAL SYSTEM"))
        for rid, src, sev, reg, ago, txt, e1, e2, e3, cat in rows:
            if rid in have:
                continue
            con.execute(
                """
                INSERT INTO records
                (record_id, occurred_at, received_at, entity_1, entity_2, entity_3,
                 category, subcategory, text, severity_label, region, source,
                 entity_key, provenance)
                VALUES (?, ?, ?, ?, ?, ?, ?, NULL, ?, ?, ?, ?, ?, ?)
                """,
                [rid, now - timedelta(days=ago + 5), now - timedelta(days=ago),
                 e1, e2, e3, cat, txt, sev, reg, src,
                 "|".join([str(e1).upper(), str(e2).upper(), str(e3).upper()]), PROVENANCE],
            )
            inserted_records.append(rid)
        cluster_exists = con.execute(
            "SELECT 1 FROM clusters WHERE cluster_id = ?", [CLUSTER_ID]).fetchone()
        if not cluster_exists:
            con.execute(
                """
                INSERT INTO clusters
                (cluster_id, pack_id, top_terms, category, record_count, first_seen, last_seen)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                [CLUSTER_ID, pack_id, json.dumps(["control", "arm", "crack", "clunk", "suspension"]),
                 SLICE["category"], len(SEED_RECORDS),
                 now - timedelta(days=95), now - timedelta(days=2)],
            )
        have_assign = {(r[0], r[1]) for r in con.execute(
            "SELECT record_id, cluster_id FROM cluster_assignments WHERE cluster_id = ?",
            [CLUSTER_ID]).fetchall()}
        missing = [rid for rid, *_rest in SEED_RECORDS if (rid, CLUSTER_ID) not in have_assign]
        if missing:
            for rid, dist in _assignment_distances([r for r in SEED_RECORDS if r[0] in missing]):
                con.execute(
                    "INSERT INTO cluster_assignments (record_id, cluster_id, distance) VALUES (?, ?, ?)",
                    [rid, CLUSTER_ID, dist],
                )
    return {"inserted_records": inserted_records, "cluster_id": CLUSTER_ID}


def _attach_lot(pack_id: str) -> dict[str, Any]:
    from src.frontline.supplier import attach_supply

    out = attach_supply(record_id="LGD-SEED-001", pack_id=pack_id,
                        supplier=LOT["supplier"], lot_id=LOT["lot_id"],
                        lot_start=LOT["lot_start"], lot_end=LOT["lot_end"])
    return {"seed_record": out["record_id"], **LOT}


def _open_investigation(pack_id: str) -> str:
    from src.frontline.live_intercept import open_or_link_investigation

    return open_or_link_investigation(
        pack_id=pack_id,
        cluster_id=CLUSTER_ID,
        title=f"LotGuard {LOT['lot_id']} {SLICE['category']} {SLICE['entity_2']} {SLICE['entity_3']}".strip(),
        category=SLICE["category"],
        entity_2=SLICE["entity_2"],
        entity_3=SLICE["entity_3"],
    )


def _register_owners(pack_id: str, count: int) -> list[str]:
    from src.frontline.outreach import register_owner

    ids: list[str] = []
    for i in range(max(0, int(count))):
        channel = "phone" if i % 6 == 5 else "whatsapp"
        row = register_owner(pack_id=pack_id, entity_2=SLICE["entity_2"],
                             entity_3=SLICE["entity_3"], cluster_id=CLUSTER_ID,
                             channel=channel,
                             address=f"lotguard-owner-{i:02d}@example.invalid")
        ids.append(row["owner_id"])
    return ids


async def _seed_contact(pack_id: str) -> dict[str, Any]:
    """One synthetic Hinglish contact through the existing orchestrator."""
    from src.agents.orchestrator import OrchestratorHooks, create_interaction

    last_agent: list[str] = [""]
    transcript: list[dict[str, str]] = []

    async def _agent_said(text: str, meta: dict[str, Any]) -> None:
        last_agent[0] = str(text or "")
        transcript.append({"speaker": "agent", "text": last_agent[0]})

    orch, _greeting = await create_interaction(channel="simulated", pack_id=pack_id,
                                               hooks=OrchestratorHooks(emit_customer_turn=_agent_said),
                                               locale="hi-IN")

    async def _say(text: str) -> None:
        transcript.append({"speaker": "customer", "text": text})
        await orch.handle_customer_turn(text)

    for turn in LOTGUARD_TURNS:
        if orch.ctx.state in ("DONE", "ABANDONED", "SUPERVISED"):
            break
        await _say(turn)
    for _ in range(8):
        if orch.ctx.state in ("DONE", "ABANDONED", "SUPERVISED", "CLOSING"):
            break
        said = last_agent[0].lower()
        reply = next((r for keys, r in _FOLLOW_UPS if any(k in said for k in keys)), _DEFAULT_REPLY)
        await _say(reply)
    if orch.ctx.state != "DONE":
        await orch.hangup()
    ctx = orch.ctx
    return {
        "interaction_id": ctx.interaction_id,
        "state": ctx.state,
        "case_id": ctx.case_id,
        "investigation_id": ctx.investigation_id,
        "severity": ctx.severity,
        "safety_flags": sorted(k for k, v in (ctx.safety_flags or {}).items() if v),
        "slots": {k: v for k, v in (ctx.slots or {}).items() if not str(k).startswith("__")},
        "transcript": transcript,
    }


async def seed_lotguard_scenario(*, pack_id: str = PACK_ID, owners: int = 24,
                                 with_contact: bool = True) -> dict[str, Any]:
    """Seed the full LotGuard demo scenario. Re-run safe for records/cluster/investigation."""
    from src.ai_layer import config
    from src.ai_layer.evidence import store_evidence
    from src.ai_layer.store import record_event

    domain = _insert_domain_rows(pack_id)
    lot = _attach_lot(pack_id)
    investigation_id = _open_investigation(pack_id)
    owner_ids = _register_owners(pack_id, owners)
    contact: dict[str, Any] | None = None
    evidence: dict[str, Any] | None = None
    if with_contact:
        contact = await _seed_contact(pack_id)
        owner = {"case_id": contact["case_id"]} if contact.get("case_id") else {
            "interaction_id": contact["interaction_id"]}
        ev = store_evidence(data=synthetic_crack_png(),
                            filename="synthetic_lotguard_control_arm.png",
                            declared_mime="image/png", **owner)
        evidence = {"evidence_id": ev.get("evidence_id"), "source": "synthetic_drawing"}
        record_event(kind="lotguard_seed", interaction_id=contact.get("interaction_id"),
                     case_id=contact.get("case_id"),
                     deterministic={"lot": LOT["lot_id"], "cluster_id": CLUSTER_ID,
                                    "owners": len(owner_ids),
                                    "investigation_id": investigation_id},
                     reason="synthetic demo seed")
    return {
        "label": SCENARIO_LABEL,
        "pack_id": pack_id,
        "lot": lot,
        "cluster_id": CLUSTER_ID,
        "investigation_id": investigation_id,
        "inserted_records": domain["inserted_records"],
        "seed_records": [r[0] for r in SEED_RECORDS],
        "owner_ids": owner_ids,
        "owner_count": len(owner_ids),
        "contact": contact,
        "evidence": evidence,
        "ai_mode": config.ai_mode(),
        "links": {
            "issue": f"#issue/{investigation_id}",
            "early_warning": "#warning",
            "demo": "#demo",
        },
    }


def _lot_rows_for_cluster(pack_id: str, cluster_id: int) -> list[dict[str, Any]]:
    """Distinct lots attached to records assigned to a cluster (observed rows only)."""
    from src.data.warehouse import domain_con, ops_con

    try:
        with domain_con(pack_id, read_only=True) as dcon:
            rids = [r[0] for r in dcon.execute(
                "SELECT record_id FROM cluster_assignments WHERE cluster_id = ?",
                [int(cluster_id)]).fetchall()]
    except Exception:
        return []
    if not rids:
        return []
    try:
        with ops_con(read_only=True) as con:
            try:
                con.execute("SELECT 1 FROM record_supply LIMIT 1")
            except Exception:
                return []
            qmarks = ",".join("?" for _ in rids)
            rows = con.execute(
                f"SELECT supplier, lot_id, lot_start, lot_end, count(*) n FROM record_supply"
                f" WHERE pack_id = ? AND record_id IN ({qmarks})"
                f" GROUP BY 1, 2, 3, 4 ORDER BY n DESC",
                [pack_id, *rids]).fetchall()
    except Exception:
        return []
    return [{"supplier": r[0], "lot_id": r[1], "lot_start": r[2], "lot_end": r[3],
             "linked_records": int(r[4])} for r in rows]


def _lot_rows_for_slice(pack_id: str, category: str | None, entity_2: str | None,
                        entity_3: str | None) -> list[dict[str, Any]]:
    """Slice-level lot match when no cluster resolved (honest fallback)."""
    from src.data.warehouse import domain_con, ops_con

    where = ["(provenance IS NULL OR provenance NOT IN ('inferred', 'fixture'))"]
    args: list[Any] = []
    for col, val in (("category", category), ("entity_2", entity_2), ("entity_3", entity_3)):
        if val:
            where.append(f"upper({col}) = upper(?)")
            args.append(val)
    try:
        with domain_con(pack_id, read_only=True) as dcon:
            rids = [r[0] for r in dcon.execute(
                f"SELECT record_id FROM records WHERE {' AND '.join(where)} LIMIT 5000",
                args).fetchall()]
    except Exception:
        return []
    if not rids:
        return []
    try:
        with ops_con(read_only=True) as con:
            try:
                con.execute("SELECT 1 FROM record_supply LIMIT 1")
            except Exception:
                return []
            qmarks = ",".join("?" for _ in rids)
            rows = con.execute(
                f"SELECT supplier, lot_id, lot_start, lot_end, count(*) n FROM record_supply"
                f" WHERE pack_id = ? AND record_id IN ({qmarks})"
                f" GROUP BY 1, 2, 3, 4 ORDER BY n DESC",
                [pack_id, *rids]).fetchall()
    except Exception:
        return []
    return [{"supplier": r[0], "lot_id": r[1], "lot_start": r[2], "lot_end": r[3],
             "linked_records": int(r[4])} for r in rows]


def lot_for_investigation(pack_id: str, cluster_id: int, category: str | None,
                          entity_2: str | None, entity_3: str | None) -> dict[str, Any]:
    """Best lot for an investigation slice. Never raises; {} when none found."""
    try:
        cid = int(cluster_id or 0)
    except (TypeError, ValueError):
        cid = 0
    rows = _lot_rows_for_cluster(pack_id, cid) if cid > 0 else []
    basis = "cluster" if rows else "slice"
    if not rows:
        rows = _lot_rows_for_slice(pack_id, category, entity_2, entity_3)
    if not rows:
        return {}
    top = rows[0]
    return {**top, "basis": basis, "candidate_lots": len(rows)}


def owners_registered(pack_id: str, cluster_id: int) -> int:
    from src.data.warehouse import ops_con

    try:
        with ops_con(read_only=True) as con:
            return int(con.execute(
                "SELECT count(*) FROM owner_contacts WHERE pack_id = ? AND cluster_id = ?",
                [pack_id, int(cluster_id or 0)]).fetchone()[0])
    except Exception:
        return 0


def lot_context(investigation_id: str) -> dict[str, Any]:
    """Full lot-card payload for one investigation. Raises LookupError when missing."""
    from src.ai_layer.safety import slice_safety
    from src.data.warehouse import domain_con, ops_con

    with ops_con(read_only=True) as con:
        row = con.execute(
            "SELECT investigation_id, pack_id, cluster_id, title, status, case_count,"
            " slice_category, slice_entity_2, slice_entity_3"
            " FROM investigations WHERE investigation_id = ?",
            [investigation_id]).fetchone()
    if not row:
        raise LookupError(f"investigation not found: {investigation_id}")
    iid, pack_id, cid, title, status, cases, cat, e2, e3 = row
    try:
        cid = int(cid or 0)
    except (TypeError, ValueError):
        cid = 0
    lot = lot_for_investigation(pack_id, cid, cat, e2, e3)
    risk = slice_safety(pack_id, cat, e2, e3, limit=500)
    synthetic = False
    seed_record: str | None = None
    if cid > 0:
        try:
            with domain_con(pack_id, read_only=True) as dcon:
                provs = dcon.execute(
                    "SELECT r.record_id, r.provenance, r.source FROM records r"
                    " JOIN cluster_assignments a ON a.record_id = r.record_id"
                    " WHERE a.cluster_id = ?", [cid]).fetchall()
            for rid, prov, src in provs:
                if prov == PROVENANCE:
                    synthetic = True
                if src == "SERVICE" and seed_record is None:
                    seed_record = rid
        except Exception:
            pass
    rationale: list[str] = []
    if lot:
        where = f"cluster #{cid}" if lot.get("basis") == "cluster" else "slice match (no resolved cluster)"
        rationale.append(
            f"{lot['linked_records']} linked record(s) in {where} carry lot {lot['lot_id']}"
            f" from {lot['supplier']}"
            + (f" (build window {lot['lot_start']} to {lot['lot_end']})" if lot.get("lot_start") else "")
            + ".")
        if lot.get("candidate_lots", 1) > 1:
            rationale.append(
                f"{lot['candidate_lots']} candidate lots touch this slice; showing the most-linked one.")
    else:
        rationale.append("No supplier lot is attached to this slice yet; owners are matched by slice only.")
    if seed_record:
        rationale.append(f"Workshop-verified seed record: {seed_record}.")
    return {
        "investigation_id": iid,
        "pack_id": pack_id,
        "cluster_id": cid,
        "title": title,
        "status": status,
        "case_count": int(cases or 0),
        "slice": {"category": cat, "entity_2": e2, "entity_3": e3},
        "lot": lot or None,
        "fallback_slice_only": not bool(lot),
        "owners_registered": owners_registered(pack_id, cid),
        "risk": risk,
        "seed_record": seed_record,
        "synthetic_demo": synthetic,
        "rationale": rationale,
    }


SYMPTOMS = ("clunk", "uneven_wear", "steering_pull", "none")
SYMPTOM_LABELS = {
    "clunk": "Clunk over bumps",
    "uneven_wear": "Uneven tyre wear",
    "steering_pull": "Steering pull",
    "none": "None of these",
}
MOCK_LABEL = ("SIMULATED owner check — notices and replies are recorded locally only; "
              "no WhatsApp/SMS/voice message is sent")

_REPLIES_DDL = """
CREATE TABLE IF NOT EXISTS owner_replies (
    reply_id    VARCHAR PRIMARY KEY,
    notice_id   VARCHAR NOT NULL UNIQUE,
    owner_id    VARCHAR NOT NULL,
    cluster_id  INTEGER NOT NULL,
    pack_id     VARCHAR NOT NULL,
    symptoms    JSON NOT NULL,
    photo_ref   VARCHAR,
    created_at  TIMESTAMP NOT NULL
)
"""


class VerificationError(ValueError):
    """Client-safe verification failure (bad symptom, unknown owner/photo)."""


def _inv_slice(investigation_id: str) -> dict[str, Any]:
    from src.data.warehouse import ops_con

    with ops_con(read_only=True) as con:
        row = con.execute(
            "SELECT pack_id, cluster_id FROM investigations WHERE investigation_id = ?",
            [investigation_id]).fetchone()
    if not row:
        raise LookupError(f"investigation not found: {investigation_id}")
    try:
        cid = int(row[1] or 0)
    except (TypeError, ValueError):
        cid = 0
    return {"pack_id": row[0], "cluster_id": cid}


def notify_lot_owners(investigation_id: str) -> dict[str, Any]:
    """Record simulated owner notices for an investigation's cluster (mock)."""
    from src.frontline.outreach import notify_affected_owners

    inv = _inv_slice(investigation_id)
    out = notify_affected_owners(pack_id=inv["pack_id"], cluster_id=inv["cluster_id"])
    return {"investigation_id": investigation_id, "mock": True, "mock_label": MOCK_LABEL,
            "cluster_id": inv["cluster_id"], "notices": out["selected"], "count": out["count"]}


def _notice_for_owner(pack_id: str, cluster_id: int, owner_id: str) -> str | None:
    from src.data.warehouse import ops_con

    with ops_con(read_only=True) as con:
        try:
            row = con.execute(
                "SELECT notice_id FROM owner_notices WHERE owner_id = ? AND cluster_id = ?"
                " ORDER BY created_at DESC LIMIT 1",
                [owner_id, int(cluster_id)]).fetchone()
        except Exception:
            return None
    return str(row[0]) if row else None


def _photo_exists(photo_ref: str) -> bool:
    from src.data.warehouse import ops_con

    try:
        with ops_con(read_only=True) as con:
            row = con.execute("SELECT 1 FROM case_evidence WHERE evidence_id = ?",
                              [photo_ref]).fetchone()
    except Exception:
        return False
    return row is not None


def record_owner_reply(*, investigation_id: str, owner_id: str,
                       symptoms: list[str], photo_ref: str | None = None) -> dict[str, Any]:
    """Record one owner's structured symptom reply. First reply per notice wins."""
    from src.data.timeutil import utc_now
    from src.data.warehouse import ops_con
    from src.ids import new_ulid

    inv = _inv_slice(investigation_id)
    clean = [str(s or "").strip().lower() for s in (symptoms or [])]
    clean = [s for s in clean if s]
    if not clean:
        raise VerificationError("at least one symptom is required")
    unknown = [s for s in clean if s not in SYMPTOMS]
    if unknown:
        raise VerificationError(f"unknown symptom(s): {', '.join(sorted(set(unknown)))}")
    if "none" in clean and len(set(clean)) > 1:
        raise VerificationError("'none' cannot be combined with symptoms")
    if photo_ref and not _photo_exists(str(photo_ref)):
        raise VerificationError("photo_ref does not match stored evidence")
    notice_id = _notice_for_owner(inv["pack_id"], inv["cluster_id"], owner_id)
    if not notice_id:
        raise VerificationError("owner has no notice for this investigation")
    rid = "rp_" + new_ulid()
    with ops_con() as con:
        con.execute(_REPLIES_DDL)
        dup = con.execute("SELECT reply_id FROM owner_replies WHERE notice_id = ?",
                          [notice_id]).fetchone()
        if dup:
            return {"reply_id": str(dup[0]), "duplicate": True,
                    "status": verification_status(investigation_id)}
        con.execute(
            "INSERT INTO owner_replies (reply_id, notice_id, owner_id, cluster_id, pack_id,"
            " symptoms, photo_ref, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            [rid, notice_id, owner_id, inv["cluster_id"], inv["pack_id"],
             json.dumps(sorted(set(clean))), photo_ref, utc_now()],
        )
    return {"reply_id": rid, "duplicate": False, "status": verification_status(investigation_id)}


def verification_status(investigation_id: str) -> dict[str, Any]:
    """Live counters + recommendation. Pure read; never changes investigation state."""
    import json as _json

    from src.data.warehouse import ops_con

    inv = _inv_slice(investigation_id)
    with ops_con(read_only=True) as con:
        try:
            notified = int(con.execute(
                "SELECT count(*) FROM owner_notices WHERE cluster_id = ?",
                [inv["cluster_id"]]).fetchone()[0])
        except Exception:
            notified = 0
        try:
            con.execute(_REPLIES_DDL)
            rows = con.execute(
                "SELECT symptoms, photo_ref FROM owner_replies WHERE cluster_id = ?",
                [inv["cluster_id"]]).fetchall()
            owner_rows = con.execute(
                "SELECT c.owner_id, c.channel,"
                " (SELECT count(*) FROM owner_notices n WHERE n.owner_id = c.owner_id"
                " AND n.cluster_id = c.cluster_id) AS notices,"
                " (SELECT count(*) FROM owner_replies r WHERE r.owner_id = c.owner_id"
                " AND r.cluster_id = c.cluster_id) AS replies"
                " FROM owner_contacts c WHERE c.cluster_id = ? ORDER BY c.owner_id",
                [inv["cluster_id"]]).fetchall()
        except Exception:
            rows = []
            owner_rows = []
    owners = [{"owner_id": o[0], "channel": o[1], "notified": int(o[2] or 0) > 0,
               "replied": int(o[3] or 0) > 0} for o in owner_rows]
    replied = len(rows)
    matched = 0
    none_count = 0
    photos = 0
    for sym_json, photo in rows:
        try:
            syms = set(_json.loads(sym_json or "[]"))
        except (TypeError, ValueError):
            syms = set()
        if "none" in syms:
            none_count += 1
        else:
            matched += 1
        if photo:
            photos += 1
    card = lot_context(investigation_id)
    critical_seed = card.get("synthetic_demo") and card.get("seed_record") == "LGD-SEED-001"
    if matched >= 1 or critical_seed:
        recommendation, reason = "escalate", (
            f"{matched} owner(s) report symptoms. Review the seed finding and workshop evidence now; "
            "a serious finding must not wait for a majority of replies.")
    else:
        recommendation, reason = "review_required", (
            f"{none_count} replies report no symptoms. No symptoms or no response does not clear a vehicle; "
            "qualified review of the original finding and traceability remains required.")
    return {
        "investigation_id": investigation_id,
        "cluster_id": inv["cluster_id"],
        "mock": True,
        "mock_label": MOCK_LABEL,
        "notified": notified,
        "replied": replied,
        "matched": matched,
        "none_count": none_count,
        "photo_count": photos,
        "owners": owners,
        "recommendation": recommendation,
        "reason": reason,
    }


LANES = ("inspect_7d", "do_not_drive")
LANE_LABELS = {
    "inspect_7d": "Inspect within 7 days",
    "do_not_drive": "Do not drive — arrange pickup",
}

_APPROVALS_DDL = """
CREATE TABLE IF NOT EXISTS lotguard_approvals (
    approval_id      VARCHAR PRIMARY KEY,
    investigation_id VARCHAR NOT NULL,
    decision         VARCHAR NOT NULL,
    lane             VARCHAR,
    verification     JSON,
    note             VARCHAR,
    decided_by       VARCHAR NOT NULL,
    decided_role     VARCHAR NOT NULL,
    created_at       TIMESTAMP NOT NULL
)
"""


class ApprovalError(VerificationError):
    """Client-safe approval failure (bad lane, unknown investigation)."""


def latest_approval(investigation_id: str) -> dict[str, Any] | None:
    """Latest supervisor decision for an investigation, or None. History is kept."""
    from src.data.warehouse import ops_con

    _inv_slice(investigation_id)  # LookupError when unknown
    with ops_con(read_only=True) as con:
        try:
            con.execute(_APPROVALS_DDL)
            row = con.execute(
                "SELECT approval_id, decision, lane, verification, note, decided_by,"
                " decided_role, created_at FROM lotguard_approvals"
                " WHERE investigation_id = ? ORDER BY created_at DESC LIMIT 1",
                [investigation_id]).fetchone()
        except Exception:
            return None
    if not row:
        return None
    try:
        verification = json.loads(row[3] or "{}")
    except (TypeError, ValueError):
        verification = {}
    return {"approval_id": row[0], "investigation_id": investigation_id, "decision": row[1],
            "lane": row[2], "verification": verification, "note": row[4],
            "decided_by": row[5], "decided_role": row[6],
            "created_at": row[7].isoformat() if hasattr(row[7], "isoformat") else str(row[7])}


def decide_approval(*, investigation_id: str, decision: str, lane: str | None = None,
                    note: str | None = None, decided_by: str,
                    decided_role: str) -> dict[str, Any]:
    """Record a supervisor decision. Ledger write propagates: no silent approvals.

    History is append-only; the latest row wins. The verification snapshot is
    stored so auditors see exactly what the supervisor saw.
    """
    from src.data.timeutil import utc_now
    from src.data.warehouse import ops_con
    from src.ids import new_ulid
    from src.ledger import AgentAction, record_action

    inv = _inv_slice(investigation_id)
    clean = str(decision or "").strip().lower()
    if clean not in ("approve", "reject"):
        raise ApprovalError("decision must be approve or reject")
    lane_clean = str(lane or "").strip().lower() or None
    if clean == "approve" and lane_clean not in LANES:
        raise ApprovalError("approving requires a lane: inspect_7d or do_not_drive")
    if clean == "reject" and lane_clean:
        raise ApprovalError("lane is only valid with approve")
    status = verification_status(investigation_id)
    snapshot = {k: status[k] for k in
                ("notified", "replied", "matched", "none_count", "photo_count", "recommendation")}
    aid = "ap_" + new_ulid()
    iid = f"int_lotguard_{inv['cluster_id']}"
    with ops_con() as con:
        con.execute(_APPROVALS_DDL)
        if not con.execute("SELECT 1 FROM interactions WHERE interaction_id = ?",
                           [iid]).fetchone():
            con.execute(
                """
                INSERT INTO interactions
                (interaction_id, pack_id, pack_version, started_at, channel, status, supervised, llm_calls)
                VALUES (?, ?, 'v', ?, 'web_text', 'active', TRUE, 0)
                """,
                [iid, inv["pack_id"], utc_now()],
            )
    # Ledger first: a failed write raises and no approval row is stored.
    record_action(AgentAction(
        interaction_id=iid,
        agent="supervisor",
        action_type="approval_decided",
        input_summary=f"lotguard {investigation_id} {clean} {lane_clean or ''}".strip(),
        output_summary=(f"decision={clean} lane={lane_clean or '-'} by={decided_by}"
                        f" matched={snapshot['matched']} none={snapshot['none_count']}"),
    ))
    with ops_con() as con:
        con.execute(
            "INSERT INTO lotguard_approvals (approval_id, investigation_id, decision, lane,"
            " verification, note, decided_by, decided_role, created_at)"
            " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            [aid, investigation_id, clean, lane_clean, json.dumps(snapshot),
             (note or "")[:2000], decided_by, decided_role, utc_now()],
        )
    return {"approval_id": aid, "investigation_id": investigation_id, "decision": clean,
            "lane": lane_clean, "verification": snapshot, "decided_by": decided_by,
            "decided_role": decided_role}


OUTCOMES = ("crack_found", "wear_only", "no_issue")
OUTCOME_LABELS = {
    "crack_found": "Crack found",
    "wear_only": "Wear only",
    "no_issue": "No issue",
}

_OUTCOMES_DDL = """
CREATE TABLE IF NOT EXISTS lotguard_outcomes (
    outcome_id       VARCHAR PRIMARY KEY,
    investigation_id VARCHAR NOT NULL,
    owner_id         VARCHAR NOT NULL,
    outcome          VARCHAR NOT NULL,
    photo_ref        VARCHAR,
    recorded_by      VARCHAR NOT NULL,
    created_at       TIMESTAMP NOT NULL,
    UNIQUE (investigation_id, owner_id)
)
"""


def _require_approval(investigation_id: str) -> dict[str, Any]:
    approval = latest_approval(investigation_id)
    if not approval or approval["decision"] != "approve":
        raise ApprovalError("workshop queue is locked: no supervisor approval for this investigation")
    return approval


def _owner_registered(pack_id: str, cluster_id: int, owner_id: str) -> bool:
    from src.data.warehouse import ops_con

    try:
        with ops_con(read_only=True) as con:
            row = con.execute(
                "SELECT 1 FROM owner_contacts WHERE pack_id = ? AND cluster_id = ? AND owner_id = ?",
                [pack_id, int(cluster_id), owner_id]).fetchone()
    except Exception:
        return False
    return row is not None


def record_outcome(*, investigation_id: str, owner_id: str, outcome: str,
                   photo_ref: str | None = None, recorded_by: str) -> dict[str, Any]:
    """Record one workshop inspection outcome. Locked until approved. First wins."""
    from src.data.timeutil import utc_now
    from src.data.warehouse import ops_con
    from src.ids import new_ulid

    inv = _inv_slice(investigation_id)
    clean = str(outcome or "").strip().lower()
    if clean not in OUTCOMES:
        raise ApprovalError(f"outcome must be one of: {', '.join(OUTCOMES)}")
    if not _owner_registered(inv["pack_id"], inv["cluster_id"], owner_id):
        raise ApprovalError("owner is not registered to this investigation")
    if photo_ref and not _photo_exists(str(photo_ref)):
        raise ApprovalError("photo_ref does not match stored evidence")
    _require_approval(investigation_id)
    oid = "oc_" + new_ulid()
    with ops_con() as con:
        con.execute(_OUTCOMES_DDL)
        dup = con.execute(
            "SELECT outcome_id FROM lotguard_outcomes WHERE investigation_id = ? AND owner_id = ?",
            [investigation_id, owner_id]).fetchone()
        if dup:
            return {"outcome_id": str(dup[0]), "duplicate": True,
                    "yield": campaign_yield(investigation_id)}
        con.execute(
            "INSERT INTO lotguard_outcomes (outcome_id, investigation_id, owner_id, outcome,"
            " photo_ref, recorded_by, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
            [oid, investigation_id, owner_id, clean, photo_ref, recorded_by, utc_now()],
        )
    return {"outcome_id": oid, "duplicate": False, "yield": campaign_yield(investigation_id)}


def workshop_queue(investigation_id: str) -> dict[str, Any]:
    """Ranked inspection queue. Transparent points like service_centre scoring.

    matched reply + photo 40 / matched reply 25 / notified, no reply 10 /
    registered 0. Reasons explain every point; nothing is AI-generated.
    The queue is visible for review but recording is locked until approved.
    """
    from src.data.warehouse import ops_con

    inv = _inv_slice(investigation_id)
    approval = latest_approval(investigation_id)
    locked = not approval or approval["decision"] != "approve"
    with ops_con(read_only=True) as con:
        try:
            owner_rows = con.execute(
                "SELECT owner_id, channel FROM owner_contacts WHERE cluster_id = ?"
                " ORDER BY owner_id", [inv["cluster_id"]]).fetchall()
        except Exception:
            owner_rows = []
        try:
            con.execute(_REPLIES_DDL)
            replies = {r[0]: (r[1], r[2]) for r in con.execute(
                "SELECT owner_id, symptoms, photo_ref FROM owner_replies WHERE cluster_id = ?",
                [inv["cluster_id"]]).fetchall()}
        except Exception:
            replies = {}
        try:
            con.execute(_OUTCOMES_DDL)
            done = {r[0]: r[1] for r in con.execute(
                "SELECT owner_id, outcome FROM lotguard_outcomes WHERE investigation_id = ?",
                [investigation_id]).fetchall()}
        except Exception:
            done = {}
    queue: list[dict[str, Any]] = []
    for owner_id, channel in owner_rows:
        pts = 0
        reasons: list[str] = []
        rep = replies.get(owner_id)
        if rep:
            try:
                syms = set(json.loads(rep[0] or "[]"))
            except (TypeError, ValueError):
                syms = set()
            if "none" in syms:
                pts += 2
                reasons.append("replied none of the symptoms (+2)")
            else:
                pts += 25
                reasons.append(f"reported {', '.join(sorted(syms)) or 'symptoms'} (+25)")
                if rep[1]:
                    pts += 15
                    reasons.append("attached a photo (+15)")
        else:
            try:
                with ops_con(read_only=True) as con2:
                    notified = con2.execute(
                        "SELECT 1 FROM owner_notices WHERE owner_id = ? AND cluster_id = ?",
                        [owner_id, inv["cluster_id"]]).fetchone()
            except Exception:
                notified = None
            if notified:
                pts += 10
                reasons.append("notified, awaiting reply (+10)")
            else:
                reasons.append("registered, not yet notified (+0)")
        queue.append({"owner_id": owner_id, "channel": channel, "score": pts,
                      "reasons": reasons, "outcome": done.get(owner_id),
                      "inspected": owner_id in done})
    queue.sort(key=lambda r: (-r["score"], r["owner_id"]))
    return {"investigation_id": investigation_id, "locked": locked,
            "lock_reason": ("Supervisor approval required before inspections are recorded."
                            if locked else None),
            "lane": (approval or {}).get("lane"),
            "queue": queue, "count": len(queue)}


def campaign_yield(investigation_id: str) -> dict[str, Any]:
    """Inspection yield from recorded outcomes only. Null yield when none."""
    from src.data.warehouse import ops_con

    _inv_slice(investigation_id)
    with ops_con(read_only=True) as con:
        try:
            con.execute(_OUTCOMES_DDL)
            rows = con.execute(
                "SELECT outcome, count(*) FROM lotguard_outcomes WHERE investigation_id = ?"
                " GROUP BY 1", [investigation_id]).fetchall()
        except Exception:
            rows = []
    counts = {o: 0 for o in OUTCOMES}
    for outcome, n in rows:
        if outcome in counts:
            counts[outcome] = int(n)
    inspected = sum(counts.values())
    return {"investigation_id": investigation_id, "inspected": inspected,
            "crack_found": counts["crack_found"], "wear_only": counts["wear_only"],
            "no_issue": counts["no_issue"],
            "yield": (counts["crack_found"] / inspected) if inspected else None}


def latest_lotguard() -> dict[str, Any] | None:
    """Most recent LotGuard-seeded investigation, or None when unseeded."""
    from src.data.warehouse import ops_con

    with ops_con(read_only=True) as con:
        try:
            row = con.execute(
                "SELECT investigation_id, title, status FROM investigations"
                " WHERE title LIKE 'LotGuard %' ORDER BY opened_at DESC LIMIT 1").fetchone()
        except Exception:
            return None
    if not row:
        return None
    return {"investigation_id": row[0], "title": row[1], "status": row[2]}


def _iso(value: Any) -> str | None:
    if value is None:
        return None
    if hasattr(value, "isoformat"):
        try:
            return value.isoformat()
        except Exception:
            return str(value)
    return str(value)


def campaign_timeline(investigation_id: str) -> dict[str, Any]:
    """Time-to-protect clock from row timestamps. Nulls when a stage is pending."""
    from src.data.warehouse import ops_con

    inv = _inv_slice(investigation_id)
    opened = approved = first_outcome = None
    with ops_con(read_only=True) as con:
        try:
            row = con.execute("SELECT opened_at FROM investigations WHERE investigation_id = ?",
                              [investigation_id]).fetchone()
            opened = _iso(row[0]) if row else None
        except Exception:
            pass
        try:
            con.execute(_APPROVALS_DDL)
            row = con.execute(
                "SELECT created_at FROM lotguard_approvals WHERE investigation_id = ?"
                " AND decision = 'approve' ORDER BY created_at ASC LIMIT 1",
                [investigation_id]).fetchone()
            approved = _iso(row[0]) if row else None
        except Exception:
            pass
        try:
            con.execute(_OUTCOMES_DDL)
            row = con.execute(
                "SELECT min(created_at) FROM lotguard_outcomes WHERE investigation_id = ?",
                [investigation_id]).fetchone()
            first_outcome = _iso(row[0]) if row and row[0] else None
        except Exception:
            pass
    return {"investigation_id": investigation_id, "cluster_id": inv["cluster_id"],
            "opened_at": opened, "approved_at": approved, "first_outcome_at": first_outcome}


def evidence_packet(investigation_id: str) -> dict[str, Any]:
    """One exportable close-out packet: seed, lot, notices, approval, outcomes."""
    from datetime import datetime, timezone

    card = lot_context(investigation_id)
    status = verification_status(investigation_id)
    return {
        "packet": "lotguard-evidence-v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "investigation_id": investigation_id,
        "synthetic_demo": card["synthetic_demo"],
        "seed_record": card["seed_record"],
        "lot": card["lot"],
        "fallback_slice_only": card["fallback_slice_only"],
        "slice": card["slice"],
        "rationale": card["rationale"],
        "risk": card["risk"],
        "verification": {k: status[k] for k in
                         ("notified", "replied", "matched", "none_count", "photo_count",
                          "recommendation")},
        "approval": latest_approval(investigation_id),
        "yield": campaign_yield(investigation_id),
        "owners_registered": card["owners_registered"],
        "timeline": campaign_timeline(investigation_id),
        "method": ("Counts from warehouse rows only. No accident, injury or crash "
                   "prediction is made or implied."),
    }


__all__ = ["CLUSTER_ID", "LANE_LABELS", "LANES", "LOT", "LOTGUARD_TURNS", "MOCK_LABEL",
           "OUTCOME_LABELS", "OUTCOMES", "PACK_ID", "PROVENANCE",
           "SCENARIO_LABEL", "SLICE", "SYMPTOM_LABELS", "SYMPTOMS",
           "ApprovalError", "VerificationError", "campaign_timeline", "campaign_yield",
           "decide_approval",
           "evidence_packet", "latest_approval", "latest_lotguard",
           "lot_context", "lot_for_investigation",
           "notify_lot_owners", "owners_registered", "record_outcome", "record_owner_reply",
           "seed_lotguard_scenario", "synthetic_crack_png", "verification_status",
           "workshop_queue"]
