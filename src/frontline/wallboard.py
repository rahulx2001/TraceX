"""Wallboard metrics from real ops tables (feature #54)."""

from __future__ import annotations

import logging
from typing import Any

from src.data.timeutil import utc_now
from src.data.warehouse import domain_con, ops_con


def _add_issue_names(clusters: list[dict[str, Any]]) -> None:
    """Read canonical names per pack; case categories remain the fallback."""
    packs = {c["pack_id"] for c in clusters if c["pack_id"]}
    for pack in packs:
        selected = {c["cluster_id"]: c for c in clusters if c["pack_id"] == pack}
        try:
            with domain_con(pack, read_only=True) as con:
                placeholders = ",".join("?" for _ in selected)
                rows = con.execute(
                    f"SELECT cluster_id, category FROM clusters WHERE pack_id = ? AND cluster_id IN ({placeholders})",
                    [pack, *selected],
                ).fetchall()
            for cid, category in rows:
                if category and category.strip():
                    selected[cid]["category"] = category.strip()
        except Exception:
            # An unavailable domain pack must not hide live operational counts.
            logging.getLogger(__name__).debug("Wallboard issue names unavailable for pack %s", pack, exc_info=True)


def build_wallboard(
    *,
    pack_id: str | None = None,
    limit_clusters: int = 5,
    include_simulated: bool = False,
) -> dict[str, Any]:
    """Live contacts, P1/open counts, top risk clusters."""
    sim_ix = "" if include_simulated else " AND COALESCE(channel, '') <> 'simulated'"
    sim_case = (
        ""
        if include_simulated
        else (
            " AND interaction_id NOT IN "
            "(SELECT interaction_id FROM interactions WHERE channel = 'simulated')"
        )
    )
    with ops_con(read_only=True) as con:
        active = con.execute(
            f"SELECT COUNT(*) FROM interactions WHERE status = 'active'{sim_ix}"
        ).fetchone()[0]
        completed = con.execute(
            f"""
            SELECT COUNT(*) FROM interactions
            WHERE status IN ('completed', 'escalated'){sim_ix}
            """
        ).fetchone()[0]
        open_cases = con.execute(
            f"SELECT COUNT(*) FROM cases WHERE status IN ('open', 'pending_followup'){sim_case}"
        ).fetchone()[0]
        p1 = con.execute(
            f"SELECT COUNT(*) FROM cases WHERE priority = 1 AND status IN ('open', 'pending_followup'){sim_case}"
        ).fetchone()[0]
        critical = con.execute(
            f"SELECT COUNT(*) FROM cases WHERE severity = 'Critical' AND status IN ('open', 'pending_followup'){sim_case}"
        ).fetchone()[0]

        # Top clusters by live case volume.
        # Severity rank via CASE — lexical MAX('Critical','Low') is wrong ('Low').
        sql = (
            """
            SELECT cluster_match_id, pack_id, COUNT(*) AS n,
                   MAX(CASE severity
                         WHEN 'Critical' THEN 4
                         WHEN 'High' THEN 3
                         WHEN 'Medium' THEN 2
                         WHEN 'Low' THEN 1
                         ELSE 0
                       END) AS max_sev_rank,
                   MODE(NULLIF(TRIM(category), '')) AS category
            FROM cases
            WHERE cluster_match_id IS NOT NULL
              AND status IN ('open', 'pending_followup')
            """
            + sim_case
        )
        params: list[Any] = []
        if pack_id:
            sql += " AND pack_id = ?"
            params.append(pack_id)
        sql += """
            GROUP BY cluster_match_id, pack_id
            ORDER BY n DESC, pack_id, cluster_match_id
            LIMIT ?
        """
        params.append(int(limit_clusters))
        cur = con.execute(sql, params)
        _rank_to_sev = {4: "Critical", 3: "High", 2: "Medium", 1: "Low", 0: None}
        top_clusters = [
            {
                "cluster_id": r[0],
                "pack_id": r[1],
                "open_cases": r[2],
                "max_severity": _rank_to_sev.get(int(r[3] or 0)),
                "category": r[4],
            }
            for r in cur.fetchall()
        ]

        live = con.execute(
            f"""
            SELECT interaction_id, pack_id, status, channel, started_at, category
            FROM interactions
            WHERE status = 'active'
            {sim_ix}
            ORDER BY started_at DESC
            LIMIT 20
            """
        ).fetchall()
        live_contacts = [
            {
                "interaction_id": r[0],
                "pack_id": r[1],
                "status": r[2],
                "channel": r[3],
                "started_at": str(r[4]) if r[4] is not None else None,
                "category": r[5],
            }
            for r in live
        ]

    # Release the ops connection before opening domain warehouses.
    _add_issue_names(top_clusters)
    return {
        "ts": utc_now().isoformat() + "Z",
        "active_contacts": int(active),
        "completed_contacts": int(completed),
        "open_cases": int(open_cases),
        "p1_open": int(p1),
        "critical_open": int(critical),
        "top_risk_clusters": top_clusters,
        "live_contacts": live_contacts,
    }


__all__ = ["build_wallboard"]
