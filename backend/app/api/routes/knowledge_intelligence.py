"""FastAPI HTTP endpoints for Module 3: Knowledge Intelligence across 8 canonical domains."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Annotated, Any, Literal

from fastapi import APIRouter, Body, Depends, Query, status
from sqlalchemy.orm import Session

from app.api.deps import (
    get_db_session,
    get_knowledge_intelligence_service,
    require_project_permission,
    resolve_project_context,
)
from app.schemas.knowledge import (
    ExtractionTriggerResponse,
    KnowledgeExtractionRunListResponse,
    KnowledgeExtractionRunResponse,
    KnowledgeItemDetailResponse,
    KnowledgeItemListResponse,
)
from app.schemas.knowledge_intelligence import (
    KnowledgeIntelligenceDomainsResponse,
    KnowledgeIntelligenceExtractRequest,
    KnowledgeIntelligenceSummaryResponse,
)
from app.services.knowledge_intelligence import KnowledgeIntelligenceService
from app.services.knowledge_quality import KnowledgeQualityEngine
from app.services.rbac import ProjectContext
from app.services.timeline import ProjectTimelineResponse

router = APIRouter(tags=["Knowledge Intelligence"])


@router.get(
    "/projects/{project_id}/knowledge-intelligence/domains",
    response_model=KnowledgeIntelligenceDomainsResponse,
    status_code=status.HTTP_200_OK,
    summary="Inspect live coverage and verification metrics across all 8 canonical domains",
)
def get_knowledge_domains_coverage(
    project_ctx: Annotated[
        ProjectContext,
        Depends(require_project_permission("project.read")),
    ],
    service: Annotated[
        KnowledgeIntelligenceService,
        Depends(get_knowledge_intelligence_service),
    ],
    include_synthetic: Annotated[bool, Query()] = False,
) -> KnowledgeIntelligenceDomainsResponse:
    """Return aggregated metrics, confidence distribution, and completeness for the 8 domains."""
    return service.get_domains_coverage(
        project_ctx=project_ctx,
        include_synthetic=include_synthetic,
    )


@router.get(
    "/projects/{project_id}/knowledge-intelligence/summary",
    response_model=KnowledgeIntelligenceSummaryResponse,
    status_code=status.HTTP_200_OK,
    summary="Executive project knowledge intelligence summary and handover readiness telemetry",
)
def get_knowledge_intelligence_summary(
    project_ctx: Annotated[
        ProjectContext,
        Depends(require_project_permission("project.read")),
    ],
    service: Annotated[
        KnowledgeIntelligenceService,
        Depends(get_knowledge_intelligence_service),
    ],
    include_synthetic: Annotated[bool, Query()] = False,
) -> KnowledgeIntelligenceSummaryResponse:
    """Return executive summary with readiness score, domain coverage, and run telemetry."""
    return service.get_summary(
        project_ctx=project_ctx,
        include_synthetic=include_synthetic,
    )


@router.get(
    "/projects/{project_id}/knowledge-intelligence/findings",
    response_model=KnowledgeItemListResponse,
    status_code=status.HTTP_200_OK,
    summary="List extracted findings filtered by canonical domain, verification, and ACLs",
)
def list_knowledge_findings(
    project_ctx: Annotated[
        ProjectContext,
        Depends(require_project_permission("project.read")),
    ],
    service: Annotated[
        KnowledgeIntelligenceService,
        Depends(get_knowledge_intelligence_service),
    ],
    domain: Annotated[
        str | None, Query(description="Canonical domain name or legacy category")
    ] = None,
    category: Annotated[str | None, Query(description="Legacy category alias")] = None,
    epistemic_status: Annotated[str | None, Query()] = None,
    review_status: Annotated[str | None, Query()] = None,
    support_classification: Annotated[str | None, Query()] = None,
    normalised_status: Annotated[str | None, Query()] = None,
    person: Annotated[str | None, Query()] = None,
    source_provider: Annotated[str | None, Query()] = None,
    evidence_id: Annotated[uuid.UUID | None, Query()] = None,
    date_from: Annotated[datetime | None, Query()] = None,
    date_to: Annotated[datetime | None, Query()] = None,
    include_stale: Annotated[bool, Query()] = True,
    stale_only: Annotated[bool, Query()] = False,
    include_synthetic: Annotated[bool, Query()] = False,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> KnowledgeItemListResponse:
    """Return paginated findings strictly filtered by caller's live source ACLs."""
    return service.list_findings(
        project_ctx=project_ctx,
        domain=domain,
        category=category,
        epistemic_status=epistemic_status,
        review_status=review_status,
        support_classification=support_classification,
        normalised_status=normalised_status,
        person=person,
        source_provider=source_provider,
        evidence_id=evidence_id,
        date_from=date_from,
        date_to=date_to,
        include_stale=include_stale,
        stale_only=stale_only,
        include_synthetic=include_synthetic,
        limit=limit,
        offset=offset,
    )


@router.get(
    "/projects/{project_id}/knowledge-intelligence/findings/{finding_id}",
    response_model=KnowledgeItemDetailResponse,
    status_code=status.HTTP_200_OK,
    summary="Retrieve finding detail with verified supporting excerpts and source provenance",
)
def get_knowledge_finding_detail(
    finding_id: uuid.UUID,
    project_ctx: Annotated[
        ProjectContext,
        Depends(require_project_permission("project.read")),
    ],
    service: Annotated[
        KnowledgeIntelligenceService,
        Depends(get_knowledge_intelligence_service),
    ],
) -> KnowledgeItemDetailResponse:
    """Return detailed finding and accessible evidence links (fail-closed if ACL revoked)."""
    return service.get_finding_detail(
        project_ctx=project_ctx,
        finding_id=finding_id,
    )


@router.get(
    "/projects/{project_id}/knowledge-intelligence/timeline",
    response_model=ProjectTimelineResponse,
    status_code=status.HTTP_200_OK,
    summary="Synthesize timeline of decisions, milestones, work, and incidents",
)
def get_project_timeline(
    project_ctx: Annotated[
        ProjectContext,
        Depends(require_project_permission("project.read")),
    ],
    service: Annotated[
        KnowledgeIntelligenceService,
        Depends(get_knowledge_intelligence_service),
    ],
    domain: Annotated[str | None, Query()] = None,
    source_provider: Annotated[str | None, Query()] = None,
    event_type: Annotated[str | None, Query()] = None,
    date_from: Annotated[datetime | None, Query()] = None,
    date_to: Annotated[datetime | None, Query()] = None,
    sort_order: Annotated[Literal["asc", "desc"], Query()] = "desc",
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> ProjectTimelineResponse:
    """Return permission-filtered event stream with second- and day-precision events."""
    return service.get_timeline(
        project_ctx=project_ctx,
        domain=domain,
        source_provider=source_provider,
        event_type=event_type,
        date_from=date_from,
        date_to=date_to,
        sort_order=sort_order,
        limit=limit,
        offset=offset,
    )


@router.post(
    "/projects/{project_id}/knowledge-intelligence/extract",
    response_model=ExtractionTriggerResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Queue knowledge intelligence extraction across all or targeted canonical domains",
)
def trigger_knowledge_intelligence_extraction(
    project_ctx: Annotated[ProjectContext, Depends(resolve_project_context)],
    service: Annotated[
        KnowledgeIntelligenceService,
        Depends(get_knowledge_intelligence_service),
    ],
    payload: Annotated[KnowledgeIntelligenceExtractRequest | None, Body()] = None,
) -> ExtractionTriggerResponse:
    """Queue asynchronous extraction job across canonical domains respecting caller source ACLs."""
    return service.trigger_extraction(
        project_ctx=project_ctx,
        payload=payload or KnowledgeIntelligenceExtractRequest(),
    )


@router.get(
    "/projects/{project_id}/knowledge-intelligence/runs",
    response_model=KnowledgeExtractionRunListResponse,
    status_code=status.HTTP_200_OK,
    summary="List knowledge extraction runs and progress telemetry for a project",
)
def list_knowledge_intelligence_runs(
    project_ctx: Annotated[
        ProjectContext,
        Depends(require_project_permission("project.read")),
    ],
    service: Annotated[
        KnowledgeIntelligenceService,
        Depends(get_knowledge_intelligence_service),
    ],
    run_status: Annotated[str | None, Query(alias="status")] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> KnowledgeExtractionRunListResponse:
    """List extraction run history, token telemetry, and completion states."""
    return service.list_runs(
        project_ctx=project_ctx,
        run_status=run_status,
        limit=limit,
        offset=offset,
    )


@router.get(
    "/projects/{project_id}/knowledge-intelligence/runs/{run_id}",
    response_model=KnowledgeExtractionRunResponse,
    status_code=status.HTTP_200_OK,
    summary="Inspect status, grounding rate, and token usage for one extraction run",
)
def get_knowledge_intelligence_run(
    run_id: uuid.UUID,
    project_ctx: Annotated[
        ProjectContext,
        Depends(require_project_permission("project.read")),
    ],
    service: Annotated[
        KnowledgeIntelligenceService,
        Depends(get_knowledge_intelligence_service),
    ],
) -> KnowledgeExtractionRunResponse:
    """Retrieve detailed execution telemetry and linked background job state for one run."""
    return service.get_run(
        project_ctx=project_ctx,
        run_id=run_id,
    )


@router.get(
    "/projects/{project_id}/knowledge-intelligence/quality",
    status_code=status.HTTP_200_OK,
    summary="Comprehensive 9-dimension project knowledge quality, gap, and completeness analysis",
)
def get_knowledge_quality_assessment(
    project_ctx: Annotated[
        ProjectContext,
        Depends(require_project_permission("project.read")),
    ],
    session: Annotated[Session, Depends(get_db_session)],
) -> dict[str, Any]:
    """Calculate transparent 9-dimension knowledge completeness and surface actionable gaps."""
    engine = KnowledgeQualityEngine(session)
    return engine.assess_project_quality(
        project_id=project_ctx.project.id,
        user_id=project_ctx.user_id,
    )
