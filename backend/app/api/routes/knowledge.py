"""FastAPI HTTP endpoints for Phase 2.6 Knowledge Reconstruction & Extracted Intelligence."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Body, Depends, Query, status

from app.api.deps import (
    get_knowledge_reconstruction_service,
    require_project_permission,
    resolve_project_context,
)
from app.schemas.knowledge import (
    EvidenceExtractRequest,
    ExtractionTriggerResponse,
    KnowledgeExtractionRunListResponse,
    KnowledgeExtractionRunResponse,
    KnowledgeItemDetailResponse,
    KnowledgeItemListResponse,
    ProjectKnowledgeExtractRequest,
    ProjectKnowledgeStatusResponse,
)
from app.services.knowledge import KnowledgeReconstructionService
from app.services.rbac import ProjectContext

router = APIRouter(tags=["Knowledge Reconstruction"])


@router.post(
    "/projects/{project_id}/evidence/{evidence_id}/extract",
    response_model=ExtractionTriggerResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Queue evidence-grounded knowledge extraction for one evidence item",
)
def trigger_evidence_knowledge_extraction(
    evidence_id: uuid.UUID,
    project_ctx: Annotated[ProjectContext, Depends(resolve_project_context)],
    service: Annotated[
        KnowledgeReconstructionService,
        Depends(get_knowledge_reconstruction_service),
    ],
    payload: Annotated[EvidenceExtractRequest | None, Body()] = None,
) -> ExtractionTriggerResponse:
    """Queue asynchronous AI knowledge extraction for a single accessible, chunked item."""
    return service.trigger_evidence_extraction(
        project_ctx=project_ctx,
        evidence_id=evidence_id,
        payload=payload or EvidenceExtractRequest(),
    )


@router.post(
    "/projects/{project_id}/knowledge/extract",
    response_model=ExtractionTriggerResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Queue knowledge extraction across accessible evidence items in a project",
)
def trigger_project_knowledge_extraction(
    project_ctx: Annotated[ProjectContext, Depends(resolve_project_context)],
    service: Annotated[
        KnowledgeReconstructionService,
        Depends(get_knowledge_reconstruction_service),
    ],
    payload: Annotated[ProjectKnowledgeExtractRequest | None, Body()] = None,
) -> ExtractionTriggerResponse:
    """Queue project-wide or targeted knowledge extraction respecting caller source ACLs."""
    return service.trigger_project_extraction(
        project_ctx=project_ctx,
        payload=payload or ProjectKnowledgeExtractRequest(),
    )


@router.get(
    "/projects/{project_id}/knowledge/status",
    response_model=ProjectKnowledgeStatusResponse,
    status_code=status.HTTP_200_OK,
    summary="Inspect accessible knowledge item counts and latest extraction run for a project",
)
def get_project_knowledge_status(
    project_ctx: Annotated[
        ProjectContext,
        Depends(require_project_permission("project.read")),
    ],
    service: Annotated[
        KnowledgeReconstructionService,
        Depends(get_knowledge_reconstruction_service),
    ],
    include_synthetic: Annotated[bool, Query()] = False,
) -> ProjectKnowledgeStatusResponse:
    """Return ACL-filtered category, epistemic, and staleness summary for a project."""
    return service.get_project_knowledge_status(
        project_ctx=project_ctx,
        include_synthetic=include_synthetic,
    )


@router.get(
    "/projects/{project_id}/knowledge/runs",
    response_model=KnowledgeExtractionRunListResponse,
    status_code=status.HTTP_200_OK,
    summary="List knowledge extraction runs for a project",
)
def list_project_extraction_runs(
    project_ctx: Annotated[
        ProjectContext,
        Depends(require_project_permission("project.read")),
    ],
    service: Annotated[
        KnowledgeReconstructionService,
        Depends(get_knowledge_reconstruction_service),
    ],
    run_status: Annotated[str | None, Query(alias="status")] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> KnowledgeExtractionRunListResponse:
    """List extraction run history and metrics within one authorised project."""
    return service.list_extraction_runs(
        project_ctx=project_ctx,
        status=run_status,
        limit=limit,
        offset=offset,
    )


@router.get(
    "/projects/{project_id}/knowledge/runs/{run_id}",
    response_model=KnowledgeExtractionRunResponse,
    status_code=status.HTTP_200_OK,
    summary="Inspect status, token telemetry, and grounding counts for one extraction run",
)
def get_project_extraction_run(
    run_id: uuid.UUID,
    project_ctx: Annotated[
        ProjectContext,
        Depends(require_project_permission("project.read")),
    ],
    service: Annotated[
        KnowledgeReconstructionService,
        Depends(get_knowledge_reconstruction_service),
    ],
) -> KnowledgeExtractionRunResponse:
    """Retrieve one project extraction run and associated background job status."""
    return service.get_extraction_run(project_ctx=project_ctx, run_id=run_id)


@router.post(
    "/projects/{project_id}/knowledge/runs/{run_id}/retry",
    response_model=ExtractionTriggerResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Retry a failed, partial, or cancelled knowledge extraction run",
)
def retry_project_extraction_run(
    run_id: uuid.UUID,
    project_ctx: Annotated[ProjectContext, Depends(resolve_project_context)],
    service: Annotated[
        KnowledgeReconstructionService,
        Depends(get_knowledge_reconstruction_service),
    ],
) -> ExtractionTriggerResponse:
    """Enqueue a clean new run retrying a failed, partial, or cancelled extraction run."""
    return service.retry_extraction_run(project_ctx=project_ctx, run_id=run_id)


@router.post(
    "/projects/{project_id}/knowledge/runs/{run_id}/cancel",
    response_model=KnowledgeExtractionRunResponse,
    status_code=status.HTTP_200_OK,
    summary="Cancel a queued knowledge extraction run",
)
def cancel_project_extraction_run(
    run_id: uuid.UUID,
    project_ctx: Annotated[ProjectContext, Depends(resolve_project_context)],
    service: Annotated[
        KnowledgeReconstructionService,
        Depends(get_knowledge_reconstruction_service),
    ],
) -> KnowledgeExtractionRunResponse:
    """Cancel a queued extraction run and its linked PostgreSQL background job."""
    return service.cancel_extraction_run(project_ctx=project_ctx, run_id=run_id)


@router.get(
    "/projects/{project_id}/knowledge/items",
    response_model=KnowledgeItemListResponse,
    status_code=status.HTTP_200_OK,
    summary="List accessible extracted knowledge items with category & provenance filters",
)
def list_project_knowledge_items(
    project_ctx: Annotated[
        ProjectContext,
        Depends(require_project_permission("project.read")),
    ],
    service: Annotated[
        KnowledgeReconstructionService,
        Depends(get_knowledge_reconstruction_service),
    ],
    category: Annotated[str | None, Query()] = None,
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
    """Return structured knowledge items strictly filtered by caller's live source ACLs."""
    return service.list_knowledge_items(
        project_ctx=project_ctx,
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
    "/projects/{project_id}/knowledge/items/{item_id}",
    response_model=KnowledgeItemDetailResponse,
    status_code=status.HTTP_200_OK,
    summary="Retrieve one knowledge item with verified supporting excerpts & source metadata",
)
def get_project_knowledge_item_detail(
    item_id: uuid.UUID,
    project_ctx: Annotated[
        ProjectContext,
        Depends(require_project_permission("project.read")),
    ],
    service: Annotated[
        KnowledgeReconstructionService,
        Depends(get_knowledge_reconstruction_service),
    ],
) -> KnowledgeItemDetailResponse:
    """Return detailed item and accessible evidence links (fail-closed if ACL revoked)."""
    return service.get_knowledge_item_detail(project_ctx=project_ctx, item_id=item_id)
