"""Scoped cluster evidence and conservative, raise-only inherited triage."""
from __future__ import annotations

from src.data.warehouse import domain_con

RANK = {"Low": 0, "Medium": 1, "High": 2, "Critical": 3}


def scoped_parents(pack_id: str, cluster_id: int | None, slots: dict, allow_synthetic: bool = False) -> list[dict]:
    if cluster_id is None or not all(slots.get(k) for k in ("category", "entity_1", "entity_2", "entity_3")):
        return []
    with domain_con(pack_id, read_only=True) as con:
        cur = con.execute("""SELECT r.record_id, r.severity_label, r.text, r.source,
            r.provenance, a.distance FROM records r JOIN cluster_assignments a USING(record_id)
            WHERE a.cluster_id = ? AND r.category = ? AND r.entity_1 = ?
            AND r.entity_2 = ? AND r.entity_3 = ?
            AND (? OR COALESCE(r.provenance, '') != 'synthetic_demo')
            ORDER BY r.record_id LIMIT 100""",
            [cluster_id, *[slots[k] for k in ("category", "entity_1", "entity_2", "entity_3")], allow_synthetic])
        return [dict(zip([d[0] for d in cur.description], r)) for r in cur.fetchall()]


def inherit_severity(own: str, parents: list[dict]) -> dict:
    supporting = [p for p in parents if RANK.get(p.get("severity_label"), 0) >= 2]
    # One severe neighbour is insufficient. Cluster evidence can raise Medium
    # to High; Critical remains reserved for this caller's safety evidence.
    raised = own == "Medium" and len(supporting) >= 2
    return {"own_severity": own, "effective_severity": "High" if raised else own,
            "cap": "High", "raised": raised,
            "supporting_record_ids": [p["record_id"] for p in supporting],
            "reason": "Two or more High/Critical reports in the same vehicle/category cluster; inherited triage capped at High." if raised else "No inherited severity increase.",
            "interpretation": "This is review priority, not a diagnosis or a confirmed failure in this vehicle."}
