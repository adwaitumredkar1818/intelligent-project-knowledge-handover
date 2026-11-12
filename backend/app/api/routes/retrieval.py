"""FastAPI HTTP endpoints for Phase 2.5 Hybrid Search, Provenance & Index Management."""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Body, Depends, status

from app.api.deps import (
    get_hybrid_retrieval_service,
    require_project_permission,
    resolve_project_context,
)
from app.schemas.evidence import BackgroundJobResponse
from app.schemas.retrieval import (
    ChunkDetailResponse,
    IndexHealthResponse,
    ProjectIndexingStatusResponse,
    ProjectSearchRequest,
    ProjectSearchResponse,
    ReindexRequest,
    ReindexResponse,
)
from app.services.rbac import ProjectContext
from app.services.retrieval import HybridRetrievalService

router = APIRouter(tags=["Retrieval & Indexing"])


@router.post(
    "/projects/{project_id}/search",
    response_model=ProjectSearchResponse,
    status_code=status.HTTP_200_OK,
    summary="Execute permission-aware hybrid, keyword, or semantic search within a project",
)
def search_project_evidence(
    payload: ProjectSearchRequest,
    project_ctx: Annotated[
        ProjectContext,
        Depends(require_project_permission("project.read")),
    ],
    service: Annotated[HybridRetrievalService, Depends(get_hybrid_retrieval_service)],
) -> ProjectSearchResponse:
    """Search authorised evidence chunks using PostgreSQL FTS and ChromaDB semantic search."""
    return service.search_project(project_ctx=project_ctx, payload=payload)


@router.get(
    "/projects/{project_id}/chunks/{chunk_id}",
    response_model=ChunkDetailResponse,
    status_code=status.HTTP_200_OK,
    summary="Fetch one evidence chunk with parent provenance and ACL verification",
)
def get_project_chunk_detail(
    chunk_id: uuid.UUID,
    project_ctx: Annotated[
        ProjectContext,
        Depends(require_project_permission("project.read")),
    ],
    service: Annotated[HybridRetrievalService, Depends(get_hybrid_retrieval_service)],
) -> ChunkDetailResponse:
    """Return canonical chunk text and parent citation after verifying source access."""
    return service.get_chunk_detail(project_ctx=project_ctx, chunk_id=chunk_id)


@router.get(
    "/projects/{project_id}/indexing/status",
    response_model=ProjectIndexingStatusResponse,
    status_code=status.HTTP_200_OK,
    summary="Inspect PostgreSQL FTS and vector indexing status for a project",
)
def get_project_indexing_status(
    project_ctx: Annotated[
        ProjectContext,
        Depends(require_project_permission("project.read")),
    ],
    service: Annotated[HybridRetrievalService, Depends(get_hybrid_retrieval_service)],
) -> ProjectIndexingStatusResponse:
    """Return project chunking, keyword readiness, and vector synchronisation counts."""
    return service.get_project_indexing_status(project_ctx=project_ctx)


@router.post(
    "/projects/{project_id}/indexing/reindex",
    response_model=ReindexResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Enqueue asynchronous project-wide or targeted evidence reindexing",
)
def trigger_project_reindex(
    project_ctx: Annotated[ProjectContext, Depends(resolve_project_context)],
    service: Annotated[HybridRetrievalService, Depends(get_hybrid_retrieval_service)],
    payload: Annotated[ReindexRequest | None, Body()] = None,
) -> ReindexResponse:
    """Queue an asynchronous PostgreSQL reindexing job for contributors or managers."""
    req = payload or ReindexRequest()
    return service.trigger_reindex(project_ctx=project_ctx, payload=req)


@router.get(
    "/projects/{project_id}/indexing/health",
    response_model=IndexHealthResponse,
    status_code=status.HTTP_200_OK,
    summary="Check PostgreSQL FTS and secondary ChromaDB collection health for a project",
)
def get_project_index_health(
    project_ctx: Annotated[
        ProjectContext,
        Depends(require_project_permission("project.read")),
    ],
    service: Annotated[HybridRetrievalService, Depends(get_hybrid_retrieval_service)],
) -> IndexHealthResponse:
    """Inspect ChromaDB reachability, collection schema compatibility, and index counts."""
    return service.get_index_health(project_ctx=project_ctx)


@router.get(
    "/projects/{project_id}/indexing/jobs/{job_id}",
    response_model=BackgroundJobResponse,
    status_code=status.HTTP_200_OK,
    summary="Inspect status of a project-scoped indexing or reindex job",
)
def get_project_indexing_job(
    job_id: uuid.UUID,
    project_ctx: Annotated[
        ProjectContext,
        Depends(require_project_permission("project.read")),
    ],
    service: Annotated[HybridRetrievalService, Depends(get_hybrid_retrieval_service)],
) -> BackgroundJobResponse:
    """Return background job status for indexing, embedding, cleanup, or reindexing."""
    return service.get_indexing_job_status(project_ctx=project_ctx, job_id=job_id)
