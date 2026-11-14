"""FastAPI HTTP endpoints for Phase 2.4A Evidence Foundation & Document Ingestion."""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, File, Query, Response, UploadFile, status

from app.api.deps import (
    get_app_settings,
    get_current_principal,
    get_evidence_service,
    require_project_permission,
)
from app.core.config import Settings
from app.core.exceptions import PayloadTooLargeError
from app.schemas.evidence import (
    BackgroundJobResponse,
    DocumentUploadResponse,
    EvidenceDetailResponse,
    EvidenceListResponse,
    EvidenceMetricsResponse,
)
from app.services.evidence import EvidenceService
from app.services.rbac import AuthenticatedPrincipal, ProjectContext

router = APIRouter(tags=["Evidence"])

_READ_CHUNK_BYTES = 1024 * 1024


async def _read_bounded_upload(upload: UploadFile, *, max_bytes: int) -> bytes:
    """Stream multipart upload in bounded chunks to reject oversized bodies early."""
    chunks: list[bytes] = []
    total_read = 0
    while True:
        chunk = await upload.read(_READ_CHUNK_BYTES)
        if not chunk:
            break
        total_read += len(chunk)
        if total_read > max_bytes:
            raise PayloadTooLargeError(
                "Uploaded document exceeds the configured maximum upload size.",
                code="FILE_TOO_LARGE",
            )
        chunks.append(chunk)
    return b"".join(chunks)


@router.post(
    "/projects/{project_id}/evidence/documents",
    response_model=DocumentUploadResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload a PDF or DOCX document as project evidence",
)
@router.post(
    "/projects/{project_id}/evidence/upload",
    response_model=DocumentUploadResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload a PDF or DOCX document as project evidence (alias)",
    include_in_schema=False,
)
async def upload_project_document(
    response: Response,
    file: Annotated[UploadFile, File(...)],
    project_ctx: Annotated[
        ProjectContext,
        Depends(
            require_project_permission(
                "project.evidence.contribute",
                require_explicit_membership=True,
            )
        ),
    ],
    settings: Annotated[Settings, Depends(get_app_settings)],
    evidence_service: Annotated[EvidenceService, Depends(get_evidence_service)],
) -> DocumentUploadResponse:
    """Validate, encrypt, deduplicate (within project), persist provenance, and queue extraction."""
    raw_bytes = await _read_bounded_upload(
        file,
        max_bytes=settings.ingestion.max_upload_size_bytes,
    )
    result = evidence_service.upload_document(
        project_ctx=project_ctx,
        filename=file.filename,
        declared_mime_type=file.content_type,
        raw_bytes=raw_bytes,
    )
    response.status_code = status.HTTP_201_CREATED if result.created else status.HTTP_200_OK
    return result.payload


@router.get(
    "/projects/{project_id}/evidence",
    response_model=EvidenceListResponse,
    status_code=status.HTTP_200_OK,
    summary="List evidence items inside an authorised project",
)
def list_project_evidence(
    project_ctx: Annotated[
        ProjectContext,
        Depends(require_project_permission("project.read")),
    ],
    evidence_service: Annotated[EvidenceService, Depends(get_evidence_service)],
    q: str | None = Query(default=None),
    provider: str | None = Query(default=None),
    processing_status: str | None = Query(default=None),
    source_type: str | None = Query(default=None),
    category: str | None = Query(default=None),
    limit: int = Query(default=20, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
) -> EvidenceListResponse:
    """List non-deleted evidence summaries for the authorised project workspace."""
    return evidence_service.list_project_evidence(
        project_ctx=project_ctx,
        processing_status=processing_status,
        source_type=source_type,
        category=category,
        q=q,
        provider=provider,
        limit=limit,
        offset=offset,
    )


@router.get(
    "/projects/{project_id}/evidence/metrics",
    response_model=EvidenceMetricsResponse,
    status_code=status.HTTP_200_OK,
    summary="Get aggregated metrics for Panel B Evidence Library",
)
def get_project_evidence_metrics(
    project_ctx: Annotated[
        ProjectContext,
        Depends(require_project_permission("project.read")),
    ],
    evidence_service: Annotated[EvidenceService, Depends(get_evidence_service)],
) -> EvidenceMetricsResponse:
    """Retrieve evidence library count, document count, bytes, and provider counts."""
    return evidence_service.get_project_evidence_metrics(project_ctx=project_ctx)


@router.get(
    "/evidence/{evidence_id}/download",
    status_code=status.HTTP_200_OK,
    summary="Download decrypted evidence document payload",
)
def download_evidence(
    evidence_id: uuid.UUID,
    principal: Annotated[AuthenticatedPrincipal, Depends(get_current_principal)],
    evidence_service: Annotated[EvidenceService, Depends(get_evidence_service)],
) -> Response:
    """Stream decrypted document bytes with authentic Content-Type and filename."""
    raw_bytes, filename, mime_type = evidence_service.download_evidence_content(
        evidence_id=evidence_id,
        principal=principal,
    )
    safe_filename = filename.replace('"', "").replace("\r", "").replace("\n", "")
    return Response(
        content=raw_bytes,
        media_type=mime_type,
        headers={
            "Content-Disposition": f'attachment; filename="{safe_filename}"',
        },
    )


@router.get(
    "/evidence/{evidence_id}",
    response_model=EvidenceDetailResponse,
    status_code=status.HTTP_200_OK,
    summary="Retrieve evidence provenance, separated extracted content, and jobs",
)
def get_evidence_detail(
    evidence_id: uuid.UUID,
    principal: Annotated[AuthenticatedPrincipal, Depends(get_current_principal)],
    evidence_service: Annotated[EvidenceService, Depends(get_evidence_service)],
) -> EvidenceDetailResponse:
    """Fetch a single evidence item after strict tenant, project, and ACL checks."""
    return evidence_service.get_evidence_detail(
        evidence_id=evidence_id,
        principal=principal,
    )


@router.delete(
    "/evidence/{evidence_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Logically delete an evidence item and remove its private stored payload",
)
def delete_evidence_item(
    evidence_id: uuid.UUID,
    principal: Annotated[AuthenticatedPrincipal, Depends(get_current_principal)],
    evidence_service: Annotated[EvidenceService, Depends(get_evidence_service)],
) -> Response:
    """Logically delete an evidence item after parent-org, project, and role/ownership checks."""
    evidence_service.delete_evidence(
        evidence_id=evidence_id,
        principal=principal,
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(
    "/evidence/{evidence_id}/reprocess",
    response_model=BackgroundJobResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Queue document extraction reprocessing for a failed or partial item",
)
def reprocess_evidence_item(
    evidence_id: uuid.UUID,
    principal: Annotated[AuthenticatedPrincipal, Depends(get_current_principal)],
    evidence_service: Annotated[EvidenceService, Depends(get_evidence_service)],
) -> BackgroundJobResponse:
    """Enqueue a clean retry job using the preserved encrypted upload object."""
    return evidence_service.reprocess_evidence(
        evidence_id=evidence_id,
        principal=principal,
    )
