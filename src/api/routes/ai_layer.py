"""REST routes for the optional Meta AI layer.  [AI-LAYER]

  GET  /api/ai/status                                  -> mode badge (enhanced | deterministic)
  GET  /api/ai/events                                  -> deterministic-vs-AI decision log
  GET  /api/ai/investigations/{investigation_id}/grounded-brief
  GET  /api/ai/lotguard/latest                          -> most recent LotGuard investigation
  GET  /api/ai/lotguard/{investigation_id}                -> supplier lot card + rationale + risk
  POST /api/ai/lotguard/{investigation_id}/notify         -> record simulated owner notices (mock)
  POST /api/ai/lotguard/{investigation_id}/replies        -> record one structured owner reply
  GET  /api/ai/lotguard/{investigation_id}/verification   -> live counters + recommendation
  POST /api/ai/lotguard/{investigation_id}/decision         -> supervisor approve/reject (ledgered)
  GET  /api/ai/lotguard/{investigation_id}/approval         -> latest decision or null
  POST /api/ai/lotguard/{investigation_id}/outcomes         -> record workshop outcome (locked until approved)
  GET  /api/ai/lotguard/{investigation_id}/workshop         -> ranked queue + yield
  GET  /api/ai/lotguard/{investigation_id}/packet           -> exportable evidence packet
  GET  /api/ai/early-warning/safety                    -> investigations ordered by safety risk
  POST /api/ai/demo/seed                               -> seeded India demo contact (synthetic, simulated channel)
  GET  /api/ai/investigations/{investigation_id}/evidence
  GET  /api/ai/clusters/{cluster_id}/evidence?pack_id=
  POST /api/ai/language/normalize                      -> detect + normalise (Hindi/Hinglish)
  POST /api/cases/{case_id}/evidence                   -> upload photo evidence (multipart "file")
  GET  /api/cases/{case_id}/evidence
  POST /api/interactions/{interaction_id}/evidence     -> mid-call upload (attaches to the case later)
  GET  /api/interactions/{interaction_id}/evidence
  GET  /api/evidence/{evidence_id}
  GET  /api/evidence/{evidence_id}/file
  POST /api/evidence/{evidence_id}/analyze

Auth mirrors the existing routers: ``require_api_key`` on the router plus the
existing RBAC permissions (``case:read`` / ``case:write`` / ``contact:write``).
"""

from __future__ import annotations

import asyncio
from typing import Any

from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse

from src.api.auth import require_api_key
from src.api.limiter import limiter
from src.api.rbac import get_actor, get_role, require_perm_dep
from src.data.warehouse import ops_in_thread

router = APIRouter(tags=["ai-layer"], dependencies=[Depends(require_api_key)])


def _evidence_http(exc: Exception) -> HTTPException:
    from src.ai_layer.evidence import EvidenceError
    from src.security.identifiers import InvalidIdentifier

    if isinstance(exc, EvidenceError):
        return HTTPException(status_code=exc.status, detail=exc.detail)
    if isinstance(exc, InvalidIdentifier):
        return HTTPException(status_code=400, detail=str(exc))
    raise exc


@router.get("/api/ai/status")
async def ai_status() -> dict[str, Any]:
    from src.ai_layer.config import ai_status as _status
    from src.ai_layer.meta_client import calls_today

    out = _status()
    out["calls_today"] = await asyncio.to_thread(calls_today)
    return out


@router.get("/api/ai/events")
async def ai_events(
    interaction_id: str | None = None,
    limit: int = 100,
    _role: str = Depends(require_perm_dep("case:read", open_mode_ok=True)),
) -> dict[str, Any]:
    from src.ai_layer.store import list_events
    from src.security.identifiers import safe_token_id

    if interaction_id:
        try:
            safe_token_id(interaction_id, kind="interaction_id")
        except Exception as e:
            raise HTTPException(status_code=400, detail=str(e)) from e
    rows = await ops_in_thread(list_events, interaction_id, limit)
    return {"events": rows, "count": len(rows)}


@router.get("/api/ai/investigations/{investigation_id}/grounded-brief")
async def grounded_brief(
    investigation_id: str,
    _role: str = Depends(require_perm_dep("case:read", open_mode_ok=True)),
) -> dict[str, Any]:
    from src.ai_layer.grounded_brief import build_grounded_brief

    try:
        return await asyncio.to_thread(build_grounded_brief, investigation_id)
    except LookupError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e


@router.get("/api/ai/lotguard/latest")
async def lotguard_latest(
    _role: str = Depends(require_perm_dep("case:read", open_mode_ok=True)),
) -> dict[str, Any]:
    """Most recent LotGuard-seeded investigation (null when unseeded)."""
    from src.ai_layer.lotguard import latest_lotguard

    return {"lotguard": await asyncio.to_thread(latest_lotguard)}


@router.get("/api/ai/lotguard/{investigation_id}")
async def lotguard_card(
    investigation_id: str,
    _role: str = Depends(require_perm_dep("case:read", open_mode_ok=True)),
) -> dict[str, Any]:
    """LotGuard lot card: supplier lot + rationale + risk for one investigation."""
    from src.ai_layer.lotguard import lot_context

    try:
        return await asyncio.to_thread(lot_context, investigation_id)
    except LookupError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e


@router.post("/api/ai/lotguard/{investigation_id}/notify")
@limiter.limit("12 per minute")
async def lotguard_notify(
    investigation_id: str,
    request: Request,
    _role: str = Depends(require_perm_dep("contact:write", open_mode_ok=True)),
) -> dict[str, Any]:
    """Record simulated owner notices for an investigation's cluster (mock: nothing sent)."""
    from src.ai_layer.lotguard import notify_lot_owners

    try:
        return await asyncio.to_thread(notify_lot_owners, investigation_id)
    except LookupError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e


@router.post("/api/ai/lotguard/{investigation_id}/replies")
@limiter.limit("60 per minute")
async def lotguard_reply(
    investigation_id: str,
    request: Request,
    _role: str = Depends(require_perm_dep("contact:write", open_mode_ok=True)),
) -> dict[str, Any]:
    """Record one owner's structured symptom reply (simulated channel)."""
    from src.ai_layer.lotguard import VerificationError, record_owner_reply

    try:
        body = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="JSON body required") from None
    if not isinstance(body, dict):
        raise HTTPException(status_code=400, detail="JSON object required")
    try:
        return await asyncio.to_thread(
            record_owner_reply,
            investigation_id=investigation_id,
            owner_id=str(body.get("owner_id") or ""),
            symptoms=list(body.get("symptoms") or []),
            photo_ref=body.get("photo_ref"),
        )
    except LookupError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except VerificationError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.get("/api/ai/lotguard/{investigation_id}/verification")
async def lotguard_verification(
    investigation_id: str,
    _role: str = Depends(require_perm_dep("case:read", open_mode_ok=True)),
) -> dict[str, Any]:
    """Live verification counters + recommendation (read-only)."""
    from src.ai_layer.lotguard import verification_status

    try:
        return await asyncio.to_thread(verification_status, investigation_id)
    except LookupError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e


@router.post("/api/ai/lotguard/{investigation_id}/decision")
@limiter.limit("12 per minute")
async def lotguard_decision(
    investigation_id: str,
    request: Request,
    role: str = Depends(get_role),
    actor: str = Depends(get_actor),
) -> dict[str, Any]:
    """Supervisor-only approval gate (approve with lane / reject). Ledgered."""
    from src.ai_layer.lotguard import VerificationError, decide_approval

    # Supervisor only; open mode never bypasses this (unsigned callers are 'agent').
    if role != "supervisor":
        raise HTTPException(status_code=403,
                            detail=f"role {role} cannot decide LotGuard approvals (supervisor only)")
    try:
        body = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="JSON body required") from None
    if not isinstance(body, dict):
        raise HTTPException(status_code=400, detail="JSON object required")
    try:
        return await asyncio.to_thread(
            decide_approval,
            investigation_id=investigation_id,
            decision=str(body.get("decision") or ""),
            lane=body.get("lane"),
            note=body.get("note"),
            decided_by=str(actor or "supervisor"),
            decided_role=role,
        )
    except LookupError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except VerificationError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.get("/api/ai/lotguard/{investigation_id}/approval")
async def lotguard_approval(
    investigation_id: str,
    _role: str = Depends(require_perm_dep("case:read", open_mode_ok=True)),
) -> dict[str, Any]:
    """Latest supervisor decision for an investigation (null when undecided)."""
    from src.ai_layer.lotguard import latest_approval

    try:
        return {"approval": await asyncio.to_thread(latest_approval, investigation_id)}
    except LookupError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e


@router.post("/api/ai/lotguard/{investigation_id}/outcomes")
@limiter.limit("60 per minute")
async def lotguard_outcome(
    investigation_id: str,
    request: Request,
    _role: str = Depends(require_perm_dep("case:write", open_mode_ok=True)),
    actor: str = Depends(get_actor),
) -> dict[str, Any]:
    """Record one workshop inspection outcome (locked until approved)."""
    from src.ai_layer.lotguard import VerificationError, record_outcome

    try:
        body = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="JSON body required") from None
    if not isinstance(body, dict):
        raise HTTPException(status_code=400, detail="JSON object required")
    try:
        return await asyncio.to_thread(
            record_outcome,
            investigation_id=investigation_id,
            owner_id=str(body.get("owner_id") or ""),
            outcome=str(body.get("outcome") or ""),
            photo_ref=body.get("photo_ref"),
            recorded_by=str(actor or "unknown"),
        )
    except LookupError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except VerificationError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.get("/api/ai/lotguard/{investigation_id}/workshop")
async def lotguard_workshop(
    investigation_id: str,
    _role: str = Depends(require_perm_dep("case:read", open_mode_ok=True)),
) -> dict[str, Any]:
    """Ranked workshop queue + yield (read-only)."""
    from src.ai_layer.lotguard import campaign_yield, workshop_queue

    try:
        queue = await asyncio.to_thread(workshop_queue, investigation_id)
        queue["yield"] = await asyncio.to_thread(campaign_yield, investigation_id)
        return queue
    except LookupError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e


@router.get("/api/ai/lotguard/{investigation_id}/packet")
async def lotguard_packet(
    investigation_id: str,
    _role: str = Depends(require_perm_dep("case:read", open_mode_ok=True)),
) -> dict[str, Any]:
    """Exportable evidence packet (seed, lot, notices, approval, outcomes)."""
    from src.ai_layer.lotguard import evidence_packet

    try:
        return await asyncio.to_thread(evidence_packet, investigation_id)
    except LookupError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e


@router.get("/api/ai/early-warning/safety")
async def early_warning_safety(
    limit: int = 50,
    _role: str = Depends(require_perm_dep("case:read", open_mode_ok=True)),
) -> dict[str, Any]:
    from src.ai_layer.safety_board import safety_board

    return await ops_in_thread(safety_board, max(1, min(int(limit), 200)))


@router.post("/api/ai/demo/seed")
@limiter.limit("6 per minute")
async def demo_seed(
    request: Request,
    _role: str = Depends(require_perm_dep("contact:write", open_mode_ok=True)),
) -> dict[str, Any]:
    """One synthetic Hinglish/Hindi contact through the real orchestrator,
    plus a synthetic photo on its case. Disabled unless AI_DEMO_ENABLED=1."""
    import os

    from src.ai_layer.demo import seed_india_scenario

    if os.environ.get("AI_DEMO_ENABLED", "").strip() not in ("1", "true", "yes"):
        raise HTTPException(status_code=403, detail="demo seeding disabled (set AI_DEMO_ENABLED=1)")
    return await seed_india_scenario()


@router.post("/api/ai/demo/meta-workflow")
@limiter.limit("5 per minute")
async def demo_meta_workflow(request: Request,
    _role: str = Depends(require_perm_dep("contact:write", open_mode_ok=True)),
) -> dict[str, Any]:
    import os
    from src.ai_layer.demo import run_meta_workflow
    if os.getenv("AI_DEMO_ENABLED") != "1":
        raise HTTPException(status_code=403, detail="demo seeding disabled")
    return await run_meta_workflow()


@router.get("/api/ai/demo/proof")
async def demo_proof() -> dict[str, Any]:
    """Recorded synthetic evidence lets judges review without their own key."""
    import json
    import os
    from src.ai_layer.live_proof import proof_path
    if os.getenv("AI_DEMO_ENABLED") != "1":
        raise HTTPException(status_code=403, detail="demo proof disabled")
    try:
        return json.loads(await asyncio.to_thread(proof_path().read_text))
    except (OSError, ValueError):
        raise HTTPException(status_code=404, detail="No recorded Meta proof available") from None


@router.post("/api/ai/demo/safety-contrast")
@limiter.limit("60 per minute")
async def demo_safety_contrast(
    request: Request,
    body: dict[str, Any],
    _role: str = Depends(require_perm_dep("contact:write", open_mode_ok=True)),
) -> dict[str, Any]:
    """Read-only hero check: the existing kill-switch lexicon on the original
    words vs on their English normalisation. Touches no interaction."""
    from src.ai_layer.demo import safety_contrast

    text = str((body or {}).get("text") or "")[:2000]
    return await asyncio.to_thread(safety_contrast, text)


@router.get("/api/ai/investigations/{investigation_id}/evidence")
async def investigation_evidence(
    investigation_id: str,
    _role: str = Depends(require_perm_dep("case:read", open_mode_ok=True)),
) -> dict[str, Any]:
    from src.ai_layer.evidence import list_for_investigation

    rows = await ops_in_thread(list_for_investigation, investigation_id)
    return {"investigation_id": investigation_id, "evidence": rows}


@router.get("/api/ai/clusters/{cluster_id}/evidence")
async def cluster_evidence(
    cluster_id: int,
    pack_id: str = "automotive_nhtsa",
    _role: str = Depends(require_perm_dep("case:read", open_mode_ok=True)),
) -> dict[str, Any]:
    from src.ai_layer.evidence import list_for_cluster

    rows = await ops_in_thread(list_for_cluster, pack_id, cluster_id)
    return {"pack_id": pack_id, "cluster_id": cluster_id, "evidence": rows}


@router.post("/api/ai/language/normalize")
@limiter.limit("60 per minute")
async def normalize_language(
    request: Request,
    body: dict[str, Any],
    _role: str = Depends(require_perm_dep("contact:write", open_mode_ok=True)),
) -> dict[str, Any]:
    from src.ai_layer.normalize import normalize_text

    text = str((body or {}).get("text") or "")[:2000]
    return await asyncio.to_thread(normalize_text, text)


async def _read_upload(file: UploadFile) -> bytes:
    from src.ai_layer.config import evidence_max_bytes

    limit = evidence_max_bytes()
    data = await file.read(limit + 1)
    if len(data) > limit:
        raise HTTPException(status_code=413, detail=f"file too large (max {limit} bytes)")
    return data


def _schedule_analysis(evidence: dict[str, Any]) -> None:
    from src.ai_layer.config import meta_enabled
    from src.ai_layer.evidence import analyze_evidence

    if not meta_enabled() or evidence.get("analysis_status") != "pending":
        return

    async def _run() -> None:
        try:
            await asyncio.to_thread(analyze_evidence, evidence["evidence_id"])
        except Exception:
            pass

    try:
        asyncio.get_running_loop().create_task(_run())
    except RuntimeError:
        pass


@router.post("/api/cases/{case_id}/evidence", status_code=201)
@limiter.limit("30 per minute")
async def upload_case_evidence(
    request: Request,
    case_id: str,
    file: UploadFile = File(...),
    _role: str = Depends(require_perm_dep("case:write", open_mode_ok=True)),
) -> dict[str, Any]:
    from src.ai_layer.evidence import store_evidence

    data = await _read_upload(file)
    try:
        ev = await ops_in_thread(
            lambda: store_evidence(data=data, filename=file.filename, declared_mime=file.content_type, case_id=case_id)
        )
    except Exception as e:
        raise _evidence_http(e) from e
    _schedule_analysis(ev)
    return ev


@router.get("/api/cases/{case_id}/evidence")
async def list_case_evidence(
    case_id: str,
    _role: str = Depends(require_perm_dep("case:read", open_mode_ok=True)),
) -> dict[str, Any]:
    from src.ai_layer.evidence import list_for_case

    try:
        rows = await ops_in_thread(list_for_case, case_id)
    except Exception as e:
        raise _evidence_http(e) from e
    return {"case_id": case_id, "evidence": rows}


@router.post("/api/interactions/{interaction_id}/evidence", status_code=201)
@limiter.limit("30 per minute")
async def upload_interaction_evidence(
    request: Request,
    interaction_id: str,
    file: UploadFile = File(...),
    _role: str = Depends(require_perm_dep("contact:write", open_mode_ok=True)),
) -> dict[str, Any]:
    from src.ai_layer.evidence import store_evidence

    data = await _read_upload(file)
    try:
        ev = await ops_in_thread(
            lambda: store_evidence(data=data, filename=file.filename, declared_mime=file.content_type,
                                   interaction_id=interaction_id)
        )
    except Exception as e:
        raise _evidence_http(e) from e
    _schedule_analysis(ev)
    return ev


@router.get("/api/interactions/{interaction_id}/evidence")
async def list_interaction_evidence(
    interaction_id: str,
    _role: str = Depends(require_perm_dep("case:read", open_mode_ok=True)),
) -> dict[str, Any]:
    from src.ai_layer.evidence import list_for_interaction

    rows = await ops_in_thread(list_for_interaction, interaction_id)
    return {"interaction_id": interaction_id, "evidence": rows}


def _check_evidence_id(evidence_id: str) -> None:
    from src.security.identifiers import safe_token_id

    try:
        safe_token_id(evidence_id, kind="evidence_id")
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.get("/api/evidence/{evidence_id}")
async def get_evidence(
    evidence_id: str,
    _role: str = Depends(require_perm_dep("case:read", open_mode_ok=True)),
) -> dict[str, Any]:
    from src.ai_layer.evidence import get_evidence as _get

    _check_evidence_id(evidence_id)
    try:
        return await ops_in_thread(_get, evidence_id)
    except Exception as e:
        raise _evidence_http(e) from e


@router.get("/api/evidence/{evidence_id}/file")
async def get_evidence_file(
    evidence_id: str,
    _role: str = Depends(require_perm_dep("case:read", open_mode_ok=True)),
):
    from pathlib import Path

    from src.ai_layer.evidence import evidence_dir, get_evidence as _get

    _check_evidence_id(evidence_id)
    try:
        ev = await ops_in_thread(lambda: _get(evidence_id, include_path=True))
    except Exception as e:
        raise _evidence_http(e) from e
    path = Path(ev["storage_path"]).resolve()
    root = evidence_dir()
    if root not in path.parents or not path.is_file():
        raise HTTPException(status_code=404, detail="evidence file missing")
    return FileResponse(str(path), media_type=ev["mime"], headers={"Cache-Control": "private, no-store"})


@router.post("/api/evidence/{evidence_id}/analyze")
@limiter.limit("20 per minute")
async def analyze(
    request: Request,
    evidence_id: str,
    _role: str = Depends(require_perm_dep("case:write", open_mode_ok=True)),
) -> dict[str, Any]:
    from src.ai_layer.evidence import analyze_evidence

    _check_evidence_id(evidence_id)
    try:
        return await asyncio.to_thread(analyze_evidence, evidence_id)
    except Exception as e:
        raise _evidence_http(e) from e


# Hackathon extensions live in their own module and are mounted here so the
# existing app wiring (src/api/main.py) stays a single include.
from src.api.routes.ai_layer_plus import router as _plus_router  # noqa: E402

router.include_router(_plus_router)

# [AI-LAYER] v2: Meta call health, supervisor review of AI raises, status overview.
from src.api.routes.ai_layer_v2 import router as _v2_router  # noqa: E402

router.include_router(_v2_router)
