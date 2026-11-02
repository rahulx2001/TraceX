"""Safety campaign API. Pilot-tenant scope comes from the authenticated warehouse."""
from typing import Any, Literal
from pathlib import Path
import re

from fastapi import APIRouter, Depends, HTTPException, Request, Query
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, ConfigDict, Field

from src.ai_layer import safety_campaigns as service
from src.ai_layer import campaign_investigator, report_sources
from src.api.auth import require_api_key
from src.api.limiter import limiter
from src.api.rbac import get_actor, get_role, require_perm, require_perm_dep
from src.data.warehouse import ops_in_thread

router = APIRouter(prefix="/api/safety-campaigns", tags=["safety-campaigns"], dependencies=[Depends(require_api_key)])
read = require_perm_dep("case:read", open_mode_ok=True)
write = require_perm_dep("case:write", open_mode_ok=True)
contact = require_perm_dep("contact:write", open_mode_ok=True)


class CreateCampaign(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    title: str = Field(min_length=1, max_length=160)
    supplier: str = Field(min_length=1, max_length=120)
    part_number: str = Field(min_length=1, max_length=120)
    lot_id: str = Field(min_length=1, max_length=120)
    component_name: str = Field(min_length=1, max_length=120)
    seed_evidence: str = Field(min_length=1, max_length=2000)
    requires_recovery: bool = False
    investigation_id: str | None = Field(default=None, max_length=160)


class CampaignAction(BaseModel):
    model_config = ConfigDict(extra="forbid")
    revision: int = Field(ge=1)
    request_id: str = Field(min_length=1, max_length=100)
    data: dict[str, Any] = Field(default_factory=dict)


class ReplyAnalysis(BaseModel):
    text: str = Field(min_length=1, max_length=4000)


class InvestigationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    vehicle_id: str = Field(min_length=1, max_length=160)
    text: str | None = Field(default=None, min_length=1, max_length=4000)
    source_ref: dict[str, Any] | None = None
    source_reviewed: bool = False
    vehicle_association_confirmed: bool = False
    revision: int = Field(ge=1)
    request_id: str = Field(min_length=1, max_length=100)
    parent_run_id: str | None = Field(default=None, max_length=100)
    assistance_mode: Literal["full_investigation", "extraction_only"] = "full_investigation"


class InvestigationReview(BaseModel):
    model_config = ConfigDict(extra="forbid")
    decision: str = Field(max_length=50)
    note: str = Field(min_length=1, max_length=2000)
    attestation: bool
    corrections: list[dict[str, Any]] = Field(default_factory=list, max_length=8)
    observation_corrections: list[dict[str, Any]] = Field(default_factory=list, max_length=16)


async def run(fn, *args, **kwargs):
    try:
        return await ops_in_thread(fn, *args, **kwargs)
    except service.CampaignError as exc:
        raise HTTPException(status_code=exc.status, detail=str(exc)) from exc


@router.get("")
async def campaigns(_role: str = Depends(read)):
    return {"campaigns": await run(service.list_campaigns)}


@router.post("")
@limiter.limit("12 per minute")
async def create(body: CreateCampaign, request: Request, _role: str = Depends(write),
                 role: str = Depends(get_role), actor: str = Depends(get_actor)):
    return await run(service.create_campaign, body.model_dump(), actor, role)


@router.post("/demo")
@limiter.limit("6 per minute")
async def demo(request: Request, _role: str = Depends(contact), role: str = Depends(get_role), actor: str = Depends(get_actor)):
    return await run(service.prepared_demo_campaign, actor, role)


@router.post("/analyze-reply")
@limiter.limit("12 per minute")
async def analyze(body: ReplyAnalysis, request: Request, _role: str = Depends(contact)):
    return await run(service.analyze_reply, body.text)


@router.get("/review-kit/{document}")
async def review_kit(document: str, _role: str = Depends(read)):
    files = {"original-300": "reports/defect/repair/human_review.html",
             "development": "reports/defect/evidence_v1/development_review.html",
             "fuel-complaints": "reports/defect/evidence_v1/fuel_complaint_review.html",
             "recalls": "reports/defect/evidence_v1/recall_review.html",
             "study": "reports/hackathon/reviewer_study/study.html"}
    relative = files.get(document)
    path = Path(__file__).resolve().parents[3]/relative if relative else None
    if path is None or not path.is_file():
        raise HTTPException(status_code=404, detail="Review document has not been prepared")
    script = "original-review.js" if document == "original-300" else "reviewer-study.js" if document == "study" else "evidence-review.js"
    # The app CSP forbids inline execution. Serve constant JS from static assets;
    # the redacted review rows remain an inert application/json block.
    html = re.sub(r"<script>[\s\S]*?</script>", f'<script src="/ui/review-scripts/{script}"></script>', path.read_text())
    return HTMLResponse(html, headers={"Cache-Control": "no-store"})


@router.get("/report-sources/interactions/{interaction_id}")
async def interaction_source(interaction_id: str, _role: str = Depends(read)):
    return await run(report_sources.interaction_report, interaction_id)


@router.get("/{campaign_id}/report-sources/replies/{vehicle_id}/{reply_id}")
async def reply_source(campaign_id: str, vehicle_id: str, reply_id: str, _role: str = Depends(read)):
    return await run(report_sources.reply_report, campaign_id, vehicle_id, reply_id)


@router.get("/{campaign_id}/vehicles/{vehicle_id}/records/{kind}")
async def records(campaign_id: str, vehicle_id: str, kind: str, offset: int = Query(0, ge=0),
                  limit: int = Query(5, ge=1, le=20), _role: str = Depends(read)):
    return await run(report_sources.vehicle_records, campaign_id, vehicle_id, kind, offset, limit)


@router.get("/{campaign_id}")
async def detail(campaign_id: str, _role: str = Depends(read)):
    c = await run(service.get_campaign, campaign_id)
    c["notice_preview"] = service.notice_preview(c)
    return c


@router.get("/{campaign_id}/packet")
async def packet(campaign_id: str, _role: str = Depends(read)):
    result = await run(service.get_campaign, campaign_id, packet=True)
    result["investigation_drafts"] = await run(campaign_investigator.list_runs, campaign_id)
    return result


@router.get("/{campaign_id}/investigations")
async def investigations(campaign_id: str, _role: str = Depends(read)):
    await run(service.get_campaign, campaign_id)
    return {"runs": await run(campaign_investigator.list_runs, campaign_id)}


@router.post("/{campaign_id}/investigations")
@limiter.limit("6 per minute")
async def investigate(campaign_id: str, body: InvestigationRequest, request: Request,
                      _role: str = Depends(read), role: str = Depends(get_role), actor: str = Depends(get_actor)):
    current = await run(service.get_campaign, campaign_id)
    require_perm(role, "contact:write" if current["synthetic_demo"] else "case:write", open_mode_ok=True)
    return await run(campaign_investigator.investigate, campaign_id, body.model_dump(), actor, role)


@router.post("/{campaign_id}/investigations/{run_id}/review")
@limiter.limit("12 per minute")
async def review_investigation(campaign_id: str, run_id: str, body: InvestigationReview, request: Request,
                               _role: str = Depends(read), role: str = Depends(get_role), actor: str = Depends(get_actor)):
    current = await run(service.get_campaign, campaign_id)
    require_perm(role, "contact:write" if current["synthetic_demo"] else "case:write", open_mode_ok=True)
    return await run(campaign_investigator.review, campaign_id, run_id, body.model_dump(), actor, role)


@router.post("/{campaign_id}/actions/{kind}")
@limiter.limit("60 per minute")
async def action(campaign_id: str, kind: str, body: CampaignAction, request: Request,
                 _role: str = Depends(read), role: str = Depends(get_role), actor: str = Depends(get_actor)):
    current = await run(service.get_campaign, campaign_id)
    # Rehearsal data is editable by operators; real campaign authority is unchanged.
    require_perm(role, "contact:write" if current["synthetic_demo"] else "case:write", open_mode_ok=True)
    c = await run(service.apply_action, campaign_id, kind, body.data, actor, role, body.revision, body.request_id)
    c["notice_preview"] = service.notice_preview(c)
    return c
