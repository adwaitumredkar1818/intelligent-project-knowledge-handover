"""Evidence Library (Panel B) and Evidence Details (Panel C) routes with ACL enforcement."""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import (
    APIRouter,
    Depends,
    File,
    Query,
    Response,
    UploadFile,
    status,
)

from app.api.deps import (
    get_current_principal,
    get_evidence_service,
    require_project_permission,
)
from app.models.enums import EvidenceProcessingStatus, SourceProvider
from app.schemas.evidence import (
    DocumentUploadResponse,
    EvidenceItemDetail,
    EvidenceLibraryMetricsResponse,
    EvidenceListResponse,
)
from app.services.evidence import EvidenceService
from app.services.rbac import AuthenticatedPrincipal, ProjectContext

router = APIRouter(tags=["evidence"])


# -----------------------------------------------------------------------------
# Document Upload (PDF & DOCX Extraction)
# -----------------------------------------------------------------------------
@router.post(
    "/projects/{project_id}/evidence/upload",
    response_model=DocumentUploadResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload and extract a PDF or DOCX document (requires project.evidence.upload)",
)
async def upload_document_evidence(
    project_id: uuid.UUID,
    file: Annotated[UploadFile, File(...)],
    project_ctx: Annotated[
        ProjectContext,
        Depends(require_project_permission("project.evidence.upload")),
    ],
    principal: Annotated[AuthenticatedPrincipal, Depends(get_current_principal)],
    evidence_service: Annotated[EvidenceService, Depends(get_evidence_service)],
) -> DocumentUploadResponse:
    """Upload a PDF or DOCX file, encrypt at rest, extract structure, and record evidence."""
    content = await file.read()
    filename = file.filename or "uploaded_document.dat"

    return evidence_service.upload_document(
        project_id=project_id,
        user_id=principal.user_id,
        filename=filename,
        content=content,
    )


# -----------------------------------------------------------------------------
# Panel B: Evidence Library
# -----------------------------------------------------------------------------
@router.get(
    "/projects/{project_id}/evidence",
    response_model=EvidenceListResponse,
    status_code=status.HTTP_200_OK,
    summary="Search, filter, and list project evidence items (requires project.evidence.read)",
)
def list_evidence_library(
    project_id: uuid.UUID,
    project_ctx: Annotated[
        ProjectContext,
        Depends(require_project_permission("project.evidence.read")),
    ],
    principal: Annotated[AuthenticatedPrincipal, Depends(get_current_principal)],
    evidence_service: Annotated[EvidenceService, Depends(get_evidence_service)],
    q: Annotated[str | None, Query(description="Search by keyword, author, or original ID")] = None,
    provider: Annotated[SourceProvider | None, Query(description="Filter by provider")] = None,
    processing_status: Annotated[
        EvidenceProcessingStatus | None,
        Query(alias="status", description="Filter by status"),
    ] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> EvidenceListResponse:
    """Retrieve filtered evidence items with strict source ACL pre-filtering."""
    return evidence_service.list_evidence(
        project_id=project_id,
        user_id=principal.user_id,
        search_query=q,
        provider=provider,
        status=processing_status,
        limit=limit,
        offset=offset,
    )


@router.get(
    "/projects/{project_id}/evidence/metrics",
    response_model=EvidenceLibraryMetricsResponse,
    status_code=status.HTTP_200_OK,
    summary="Get aggregated evidence summary metrics for a project (project.evidence.read)",
)
def get_evidence_metrics(
    project_id: uuid.UUID,
    project_ctx: Annotated[
        ProjectContext,
        Depends(require_project_permission("project.evidence.read")),
    ],
    evidence_service: Annotated[EvidenceService, Depends(get_evidence_service)],
) -> EvidenceLibraryMetricsResponse:
    """Return total records, breakdown by source, bytes stored, and sync status."""
    return evidence_service.get_evidence_metrics(project_id=project_id)


# -----------------------------------------------------------------------------
# Panel C: Evidence Details & Secure Document Download
# -----------------------------------------------------------------------------
@router.get(
    "/evidence/{evidence_id}",
    response_model=EvidenceItemDetail,
    status_code=status.HTTP_200_OK,
    summary="Fetch full evidence details and extracted chunks (enforces strict Source ACL)",
)
def get_evidence_detail(
    evidence_id: uuid.UUID,
    principal: Annotated[AuthenticatedPrincipal, Depends(get_current_principal)],
    evidence_service: Annotated[EvidenceService, Depends(get_evidence_service)],
) -> EvidenceItemDetail:
    """Retrieve full evidence item with content and chunks; fails closed if unauthorized."""
    return evidence_service.get_evidence_detail(
        evidence_id=evidence_id,
        user_id=principal.user_id,
    )


@router.get(
    "/evidence/{evidence_id}/download",
    status_code=status.HTTP_200_OK,
    summary="Download decrypted document file content (enforces strict Source ACL)",
)
def download_document(
    evidence_id: uuid.UUID,
    principal: Annotated[AuthenticatedPrincipal, Depends(get_current_principal)],
    evidence_service: Annotated[EvidenceService, Depends(get_evidence_service)],
) -> Response:
    """Decrypt and stream stored document file with correct Content-Disposition."""
    raw_bytes, filename, mime_type = evidence_service.download_document_file(
        evidence_id=evidence_id,
        user_id=principal.user_id,
    )
    headers = {
        "Content-Disposition": f'attachment; filename="{filename}"',
        "Content-Length": str(len(raw_bytes)),
    }
    return Response(content=raw_bytes, media_type=mime_type, headers=headers)
