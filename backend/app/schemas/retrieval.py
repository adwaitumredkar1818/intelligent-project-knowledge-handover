"""Pydantic v2 request and response schemas for Phase 2.5 Hybrid Search & Retrieval."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any, Literal

from pydantic import Field, field_validator, model_validator

from app.models.enums import (
    EvidenceCategory,
    EvidenceChunkType,
    EvidenceSourceType,
    SearchMode,
)
from app.schemas.common import BaseSchema
from app.schemas.evidence import BackgroundJobResponse


class SearchFiltersRequest(BaseSchema):
    """Structured metadata filters applied consistently across SQL FTS and Chroma pre-filter."""

    source_types: list[EvidenceSourceType] | None = Field(default=None, max_length=10)
    categories: list[EvidenceCategory] | None = Field(default=None, max_length=15)
    chunk_types: list[EvidenceChunkType] | None = Field(default=None, max_length=20)
    author: str | None = Field(default=None, max_length=255)
    evidence_ids: list[uuid.UUID] | None = Field(default=None, max_length=100)
    date_from: datetime | None = None
    date_to: datetime | None = None
    include_synthetic: bool = False

    @field_validator("author", mode="before")
    @classmethod
    def _clean_author(cls, value: Any) -> str | None:
        if value is None:
            return None
        cleaned = str(value).strip()
        return cleaned or None

    @field_validator("date_from", "date_to", mode="after")
    @classmethod
    def _normalize_dates_to_utc(cls, value: datetime | None) -> datetime | None:
        if value is None:
            return None
        if value.tzinfo is None:
            return value.replace(tzinfo=UTC)
        return value.astimezone(UTC)

    @model_validator(mode="after")
    def _validate_date_range(self) -> SearchFiltersRequest:
        if (
            self.date_from is not None
            and self.date_to is not None
            and self.date_from > self.date_to
        ):
            raise ValueError("filters.date_from must not be later than filters.date_to.")
        return self


class ProjectSearchRequest(BaseSchema):
    """Project-scoped hybrid retrieval request."""

    query: str = Field(min_length=1, max_length=1000)
    mode: SearchMode = SearchMode.HYBRID
    top_k: int | None = Field(default=None, ge=1, le=50)
    filters: SearchFiltersRequest = Field(default_factory=SearchFiltersRequest)

    @field_validator("query", mode="before")
    @classmethod
    def _strip_query(cls, value: Any) -> str:
        if value is None:
            raise ValueError("Search query cannot be empty.")
        cleaned = " ".join(str(value).split())
        if not cleaned:
            raise ValueError("Search query cannot be blank.")
        return cleaned


class SearchCitation(BaseSchema):
    """Full provenance citation linking a retrieved chunk directly back to source evidence."""

    evidence_id: uuid.UUID
    chunk_id: uuid.UUID
    chunk_index: int
    source_type: str
    source_provider: str
    category: str
    source_external_id: str
    source_url: str | None
    title: str
    original_filename: str | None
    section_title: str | None
    page_number: int | None
    char_start: int
    char_end: int
    source_author_identity: str | None
    source_created_at: datetime | None
    extracted_at: datetime | None
    content_hash: str
    chunk_content_hash: str
    acl_scope: str
    is_synthetic: bool = False


class SearchResultScores(BaseSchema):
    """Transparent hybrid fusion, semantic, and keyword score breakdown."""

    hybrid_score: float
    semantic_score: float | None = None
    keyword_score: float | None = None
    semantic_rank: int | None = None
    keyword_rank: int | None = None
    matched_by: list[str] = Field(default_factory=list)


class SearchResultItem(BaseSchema):
    """Ranked project search hit preserving chunk text, bounded snippet, and citation."""

    rank: int
    chunk_id: uuid.UUID
    evidence_id: uuid.UUID
    chunk_index: int
    chunk_type: str
    excerpt: str
    chunk_text: str
    token_estimate: int
    scores: SearchResultScores
    citation: SearchCitation


class ProjectSearchResponse(BaseSchema):
    """Permission-filtered hybrid search response with explicit degraded-mode visibility."""

    project_id: uuid.UUID
    query: str
    mode_requested: SearchMode
    mode_executed: SearchMode
    degraded: bool = False
    degraded_reason: str | None = None
    warnings: list[str] = Field(default_factory=list)
    total_returned: int
    latency_ms: int
    embedding_model: str
    index_version: str
    results: list[SearchResultItem] = Field(default_factory=list)


class ChunkDetailResponse(BaseSchema):
    """Detailed single-chunk view with parent evidence citation metadata."""

    id: uuid.UUID
    organisation_id: uuid.UUID
    project_id: uuid.UUID
    evidence_id: uuid.UUID
    chunk_index: int
    chunk_type: str
    section_title: str | None
    page_number: int | None
    char_start: int
    char_end: int
    char_count: int
    token_estimate: int
    chunk_text: str
    chunk_content_hash: str
    indexing_status: str
    embedding_model: str | None
    embedding_dimensions: int | None
    embedded_at: datetime | None
    metadata_json: dict[str, Any]
    citation: SearchCitation
    created_at: datetime
    updated_at: datetime


class ProjectIndexingStatusResponse(BaseSchema):
    """Canonical project-level chunking, FTS, and vector sync counts."""

    project_id: uuid.UUID
    total_eligible_evidence: int
    status_counts: dict[str, int]
    total_chunks: int
    indexed_chunks: int
    pending_vector_chunks: int
    failed_chunks: int
    active_indexing_jobs: int
    latest_indexed_at: datetime | None
    expected_embedding_model: str
    expected_index_version: str
    observed_embedding_models: list[str]
    observed_index_versions: list[str]
    fts_ready_items: int
    vector_synced_items: int


class ReindexRequest(BaseSchema):
    """Trigger explicit asynchronous project-wide or targeted evidence reindexing."""

    target: Literal["full", "fts_only", "vectors_only"] = "full"
    evidence_ids: list[uuid.UUID] | None = Field(default=None, max_length=200)
    force_rechunk: bool | None = None


class ReindexResponse(BaseSchema):
    """Accepted asynchronous reindex job tracking response."""

    project_id: uuid.UUID
    target: str
    target_evidence_count: int
    already_running: bool
    job: BackgroundJobResponse


class IndexHealthResponse(BaseSchema):
    """Diagnostic health view of PostgreSQL FTS and secondary ChromaDB vector index."""

    project_id: uuid.UUID
    postgresql_fts_ready: bool
    chroma_reachable: bool
    chroma_collection_name: str
    chroma_collection_exists: bool
    chroma_vector_count: int | None
    chroma_space: str | None
    expected_embedding_model: str
    expected_index_version: str
    expected_dimensions: int
    collection_compatible: bool
    compatibility_error: str | None = None
    indexing_summary: ProjectIndexingStatusResponse
