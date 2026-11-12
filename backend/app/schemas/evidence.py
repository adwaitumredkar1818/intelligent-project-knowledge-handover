"""Pydantic v2 request and response schemas for Phase 2.4A Evidence & Ingestion."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import Field, model_validator

from app.schemas.common import BaseSchema


class BackgroundJobResponse(BaseSchema):
    """Sanitised status view of a PostgreSQL-tracked background job."""

    id: uuid.UUID
    organisation_id: uuid.UUID
    project_id: uuid.UUID
    evidence_id: uuid.UUID | None
    job_type: str
    status: str
    attempt_count: int
    max_attempts: int
    error_code: str | None
    error_message: str | None
    result_json: dict[str, Any] | None
    next_retry_at: datetime | None
    started_at: datetime | None
    completed_at: datetime | None
    duration_ms: int | None
    created_at: datetime
    updated_at: datetime


class EvidencePageContentResponse(BaseSchema):
    """Extracted page or logical section belonging strictly to separated extracted content."""

    page_number: int
    extraction_outcome: str
    ocr_applied: bool
    ocr_truncated: bool
    text_content: str
    char_count: int
    structured_metadata: dict[str, Any]


class EvidenceExtractedContentResponse(BaseSchema):
    """Extracted text layer distinguished from raw original source metadata."""

    char_count: int
    word_count: int
    extraction_warnings: list[str]
    extracted_text: str
    pages: list[EvidencePageContentResponse]


class EvidenceSummaryResponse(BaseSchema):
    """Safe evidence projection preserving provenance and omitting storage keys/paths."""

    id: uuid.UUID
    organisation_id: uuid.UUID
    project_id: uuid.UUID
    uploaded_by_user_id: uuid.UUID | None
    source_type: str
    source_provider: str
    provider: str | None = None
    category: str
    source_external_id: str
    source_url: str | None
    source_author_identity: str | None
    title: str
    original_filename: str | None
    mime_type: str | None
    file_size_bytes: int | None
    content_hash: str
    acl_scope: str
    source_created_at: datetime | None
    source_updated_at: datetime | None
    extracted_at: datetime | None
    last_synced_at: datetime | None
    processing_status: str
    extraction_method: str | None
    page_count: int | None
    ocr_pages_count: int
    truncated_pages_count: int
    error_code: str | None
    error_message: str | None
    indexing_status: str = "not_indexed"
    chunk_count: int = 0
    indexed_at: datetime | None = None
    embedding_model: str | None = None
    index_version: str | None = None
    index_error_code: str | None = None
    index_error_message: str | None = None
    metadata_json: dict[str, Any]
    latest_job: BackgroundJobResponse | None = None
    latest_indexing_job: BackgroundJobResponse | None = None
    created_at: datetime
    updated_at: datetime

    @model_validator(mode="before")
    @classmethod
    def _populate_provider(cls, data: Any) -> Any:
        if isinstance(data, dict):
            if not data.get("provider"):
                cat = str(data.get("category") or "")
                if cat == "pdf_document":
                    data["provider"] = "pdf"
                elif cat == "docx_document":
                    data["provider"] = "docx"
                elif data.get("source_provider") in ("github", "jira", "slack"):
                    data["provider"] = data.get("source_provider")
                else:
                    data["provider"] = data.get("source_provider") or "upload"
        return data


class EvidenceChunkDetailResponse(BaseSchema):
    """Chunk level detail for Panel C Evidence inspection."""

    id: uuid.UUID
    chunk_index: int
    content_text: str
    chunk_type: str = "text_segment"
    section_title: str | None = None
    page_number: int | None = None
    char_length: int = 0
    word_count: int = 0


class EvidenceDetailResponse(EvidenceSummaryResponse):
    """Detailed evidence record including separated extracted content and job history."""

    extracted_content: EvidenceExtractedContentResponse | None = None
    jobs: list[BackgroundJobResponse] = Field(default_factory=list)
    can_download: bool = False
    download_url: str | None = None
    chunks: list[EvidenceChunkDetailResponse] = Field(default_factory=list)


class EvidenceListResponse(BaseSchema):
    """Paginated evidence listing scoped to one accessible project."""

    items: list[EvidenceSummaryResponse]
    total: int
    limit: int
    offset: int


class DocumentUploadResponse(BaseSchema):
    """Response returned when uploading a PDF/DOCX or detecting an active project duplicate."""

    evidence: EvidenceSummaryResponse
    job: BackgroundJobResponse | None
    duplicate_detected: bool
    evidence_item_id: uuid.UUID | None = None

    @model_validator(mode="before")
    @classmethod
    def _populate_item_id(cls, data: Any) -> Any:
        if isinstance(data, dict):
            if not data.get("evidence_item_id"):
                ev = data.get("evidence")
                if isinstance(ev, dict) and "id" in ev:
                    data["evidence_item_id"] = ev["id"]
                elif hasattr(ev, "id"):
                    data["evidence_item_id"] = getattr(ev, "id")
        return data


class EvidenceMetricsResponse(BaseSchema):
    """Aggregated metrics for Panel B Evidence Library header."""

    total_items: int = 0
    total_documents: int = 0
    total_bytes: int = 0
    by_provider: dict[str, int] = Field(default_factory=dict)
    by_status: dict[str, int] = Field(default_factory=dict)

