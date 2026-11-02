"""Case completeness: why each drawer panel is filled or empty.

The case drawer mixes four kinds of field, and an empty one means a
different thing for each:

* advisory      - deterministic Sentinel SQL match against the advisories
                  (recalls) table. No LLM, Baseten included, may invent an
                  advisory id; empty means no recall row matched scope.
* fault codes   - customer-supplied OBD-II DTCs only (transcript scan or
                  operator entry). Empty means the customer never gave one.
* photos        - customer uploads only. Empty means no upload yet; the
                  follow-up draft now asks for one.
* operator notes - human pilot-team notes. An AI draft is suggested here
                  but is only stored when an operator posts it as a note.

Optional evidence lookup failures are reported as unavailable. No writes occur.
"""

from __future__ import annotations

import json
from typing import Any

from src.data.warehouse import ops_con


def _case_row(case_id: str) -> dict[str, Any] | None:
    with ops_con(read_only=True) as con:
        cur = con.execute("SELECT * FROM cases WHERE case_id = ?", [case_id])
        row = cur.fetchone()
        if not row:
            return None
        return dict(zip([d[0] for d in cur.description], row))


def _interaction_scope(interaction_id: str | None) -> dict[str, Any]:
    if not interaction_id:
        return {}
    try:
        with ops_con(read_only=True) as con:
            cur = con.execute(
                "SELECT entity_1, entity_2, entity_3 FROM interactions WHERE interaction_id = ?",
                [interaction_id],
            )
            row = cur.fetchone()
            if not row:
                return {}
            return {"year": row[0], "make": row[1], "model": row[2]}
    except Exception:
        return {}


def draft_operator_note(case: dict[str, Any], *, fault_codes: list[str] | None = None,
                        photo_count: int = 0, fault_codes_available: bool = True,
                        photos_available: bool = True) -> str:
    """Grounded one-paragraph draft for the pilot team. Not a stored note."""
    flags = case.get("safety_flags")
    if isinstance(flags, str):
        try:
            flags = json.loads(flags)
        except Exception:
            flags = {}
    active = [k for k, v in (flags or {}).items() if v] if isinstance(flags, dict) else []
    parts = [
        f"{case.get('category') or 'Uncategorised'} case, severity "
        f"{case.get('severity') or 'unknown'} (P{case.get('priority')}), "
        f"status {case.get('status') or 'open'}.",
    ]
    if active:
        parts.append(f"Safety flags: {', '.join(active)}.")
    if case.get("advisory_match_id"):
        parts.append(f"Advisory match {case['advisory_match_id']}.")
    else:
        parts.append("No recall is linked to this case.")
    if case.get("cluster_match_id") is not None:
        parts.append(f"Cluster {case['cluster_match_id']}.")
    if not fault_codes_available:
        parts.append("Fault-code records could not be loaded.")
    elif fault_codes:
        parts.append(f"Fault codes: {', '.join(fault_codes)}.")
    else:
        parts.append("No fault codes supplied yet.")
    parts.append(f"Photos attached: {photo_count}." if photos_available else
                 "Photo records could not be loaded.")
    parts.append("Review evidence and confirm next action before contacting the customer.")
    return " ".join(parts)


def completeness_for_case(case_id: str) -> dict[str, Any]:
    case = _case_row(case_id)
    if case is None:
        return {"case_id": case_id, "case_found": False}

    scope = _interaction_scope(case.get("interaction_id"))
    scope_label = " ".join(str(v) for v in (scope.get("year"), scope.get("make"), scope.get("model")) if v).strip()
    advisory_id = case.get("advisory_match_id")
    advisory = {
        "status": "matched" if advisory_id else "no_match",
        "advisory_id": advisory_id,
        "checked_scope": scope_label or (case.get("category") or ""),
        "reason": (
            f"Matched advisory {advisory_id} by Sentinel scope check."
            if advisory_id else
            "No recall is linked to "
            f"{scope_label or 'this vehicle'} / {case.get('category') or 'category'}. "
            "You can review the report without a recall match."
        ),
    }

    codes: list[str] = []
    codes_available = True
    try:
        from src.ai_layer.fault_codes import for_case
        codes = [c["code"] for c in for_case(case_id).get("codes", [])]
    except Exception:
        codes_available = False
    fault_codes = {
        "status": "unavailable" if not codes_available else "attached" if codes else "not_supplied",
        "codes": codes,
        "count": len(codes) if codes_available else None,
        "reason": "Could not load fault codes. Retry before deciding whether any were supplied." if not codes_available else None if codes else
        "Customer has not supplied a fault code yet. Codes mentioned in the "
        "conversation are captured automatically; otherwise add them here or "
        "via the follow-up reply.",
    }

    photo_count = 0
    photos_available = True
    try:
        from src.ai_layer.evidence import list_for_case
        photo_count = len(list_for_case(case_id))
    except Exception:
        photos_available = False
    photos = {
        "status": "unavailable" if not photos_available else "attached" if photo_count else "not_supplied",
        "count": photo_count if photos_available else None,
        "reason": "Could not load photos. Retry before deciding whether any were attached." if not photos_available else None if photo_count else
        "No photo attached. Add one if it is available and safe to take; you can review the report without one.",
    }

    notes_count = 0
    notes_available = True
    try:
        from src.frontline.ops import list_case_notes
        notes_count = len(list_case_notes(case_id))
    except Exception:
        notes_available = False

    missing = []
    if codes_available and not codes:
        missing.append("fault_codes")
    if photos_available and not photo_count:
        missing.append("photos")
    if notes_available and not notes_count:
        missing.append("operator_notes")
    if not (case.get("followup_draft") or "").strip():
        missing.append("followup_draft")
    unavailable = [name for name, available in (
        ("fault_codes", codes_available), ("photos", photos_available),
        ("operator_notes", notes_available)) if not available]

    return {
        "case_id": case_id,
        "case_found": True,
        "reported_vehicle": scope,
        "vehicle_details_missing": [name for name in ("year", "make", "model") if not scope.get(name)],
        "advisory": advisory,
        "fault_codes": fault_codes,
        "photos": photos,
        "followup_draft": {"status": "drafted" if (case.get("followup_draft") or "").strip() else "missing"},
        "operator_notes": {"count": notes_count if notes_available else None,
                           "status": "unavailable" if not notes_available else "recorded" if notes_count else "not_recorded"},
        "missing": missing,
        "unavailable": unavailable,
        "complete": not missing and not unavailable,
        "draft_operator_note": draft_operator_note(case, fault_codes=codes, photo_count=photo_count,
                                                   fault_codes_available=codes_available,
                                                   photos_available=photos_available),
    }


__all__ = ["completeness_for_case", "draft_operator_note"]
