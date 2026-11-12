"""Unified evidence ledger and separated extracted document content SQLAlchemy models."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import (
    JSON,
    BigInteger,
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    Uuid,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB, TSVECTOR
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.enums import (
    ChunkIndexingStatus,
    EvidenceChunkType,
    EvidenceIndexingStatus,
    EvidenceProcessingStatus,
    EvidenceSourceType,
    PageExtractionOutcome,
)

if TYPE_CHECKING:
    from app.models.integration import SourceAccessPolicy, SourceConnection
    from app.models.job import BackgroundJob
    from app.models.organisation import Organisation
    from app.models.project import Project
    from app.models.user import User

_JSON_VARIANT = JSON().with_variant(JSONB(astext_type=Text()), "postgresql")
_TSVECTOR_VARIANT = Text().with_variant(TSVECTOR(), "postgresql")


class EvidenceItem(Base):
    """Canonical multi-source evidence record with strict provenance and private storage refs."""

    __tablename__ = "evidence_items"
    __table_args__ = (
        CheckConstraint(
            "source_type IN ('document_upload', 'github', 'jira', 'slack', 'manual_note')",
            name="evidence_source_type",
        ),
        CheckConstraint(
            "category IN ("
            "'pdf_document', 'docx_document', 'issue', 'pull_request', "
            "'commit', 'discussion_thread', 'design_document', 'other'"
            ")",
            name="evidence_category",
        ),
        CheckConstraint(
            "processing_status IN ("
            "'pending', 'queued', 'processing', 'extracted', "
            "'partially_extracted', 'failed', 'deleted'"
            ")",
            name="evidence_processing_status",
        ),
        CheckConstraint(
            "acl_scope IN ('project_members', 'source_restricted')",
            name="evidence_acl_scope",
        ),
        CheckConstraint(
            "length(content_hash) = 64",
            name="evidence_content_hash_sha256_len",
        ),
        CheckConstraint(
            "file_size_bytes IS NULL OR file_size_bytes >= 0",
            name="evidence_file_size_non_negative",
        ),
        CheckConstraint(
            "page_count IS NULL OR page_count >= 0",
            name="evidence_page_count_non_negative",
        ),
        CheckConstraint(
            "ocr_pages_count >= 0 AND truncated_pages_count >= 0",
            name="evidence_ocr_counts_non_negative",
        ),
        CheckConstraint(
            "indexing_status IN ("
            "'not_indexed', 'queued', 'processing', 'indexed', "
            "'partially_indexed', 'failed', 'deleted'"
            ")",
            name="evidence_indexing_status",
        ),
        CheckConstraint(
            "chunk_count >= 0",
            name="evidence_chunk_count_non_negative",
        ),
        Index(
            "uq_evidence_active_project_hash",
            "project_id",
            "content_hash",
            unique=True,
            sqlite_where=text("deleted_at IS NULL AND processing_status != 'deleted'"),
            postgresql_where=text("deleted_at IS NULL AND processing_status != 'deleted'"),
        ),
        Index(
            "uq_evidence_active_project_source_external_id",
            "project_id",
            "source_type",
            "source_external_id",
            unique=True,
            sqlite_where=text("deleted_at IS NULL AND processing_status != 'deleted'"),
            postgresql_where=text("deleted_at IS NULL AND processing_status != 'deleted'"),
        ),
        Index(
            "ix_evidence_org_project_status",
            "organisation_id",
            "project_id",
            "processing_status",
        ),
        Index("ix_evidence_project_source_type", "project_id", "source_type"),
        Index("ix_evidence_project_created_at", "project_id", "created_at"),
        Index("ix_evidence_project_indexing_status", "project_id", "indexing_status"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    organisation_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("organisations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    project_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    uploaded_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # Provenance & connector readiness fields (AGENTS.md mandatory retention rules)
    source_type: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default=EvidenceSourceType.DOCUMENT_UPLOAD.value,
    )
    source_provider: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        default="local_upload",
    )
    category: Mapped[str] = mapped_column(String(32), nullable=False)
    source_external_id: Mapped[str] = mapped_column(String(255), nullable=False)
    source_url: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    source_author_identity: Mapped[str | None] = mapped_column(String(255), nullable=True)

    title: Mapped[str] = mapped_column(String(500), nullable=False)
    original_filename: Mapped[str | None] = mapped_column(String(255), nullable=True)
    mime_type: Mapped[str | None] = mapped_column(String(128), nullable=True)
    file_size_bytes: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False)

    # Private encrypted storage metadata (never serialised in public API responses)
    storage_provider: Mapped[str | None] = mapped_column(String(32), nullable=True)
    storage_object_key: Mapped[str | None] = mapped_column(String(255), nullable=True)
    encryption_algorithm: Mapped[str | None] = mapped_column(String(32), nullable=True)
    encryption_key_id: Mapped[str | None] = mapped_column(String(64), nullable=True)

    # Delegated source connection & ACL linkage
    source_connection_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("source_connections.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    source_access_policy_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("source_access_policies.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    acl_scope: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="project_members",
        server_default="project_members",
    )

    # Source and extraction timestamps
    source_created_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    source_updated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    extracted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    last_synced_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # Processing lifecycle and structured document metrics
    processing_status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default=EvidenceProcessingStatus.QUEUED.value,
        server_default=EvidenceProcessingStatus.QUEUED.value,
        index=True,
    )
    extraction_method: Mapped[str | None] = mapped_column(String(32), nullable=True)
    page_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    ocr_pages_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default="0",
    )
    truncated_pages_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default="0",
    )
    error_code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    error_message: Mapped[str | None] = mapped_column(String(500), nullable=True)

    # Chunking, FTS indexing, and rebuildable ChromaDB vector status
    indexing_status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default=EvidenceIndexingStatus.NOT_INDEXED.value,
        server_default=EvidenceIndexingStatus.NOT_INDEXED.value,
    )
    chunk_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default="0",
    )
    indexed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    embedding_model: Mapped[str | None] = mapped_column(String(128), nullable=True)
    index_version: Mapped[str | None] = mapped_column(String(32), nullable=True)
    index_error_code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    index_error_message: Mapped[str | None] = mapped_column(String(500), nullable=True)

    # Small structured non-sensitive metadata ONLY (large extracted text lives in dedicated tables)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(
        _JSON_VARIANT,
        nullable=False,
        default=dict,
    )

    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    deleted_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    organisation: Mapped[Organisation] = relationship(foreign_keys=[organisation_id])
    project: Mapped[Project] = relationship(foreign_keys=[project_id])
    uploaded_by_user: Mapped[User | None] = relationship(foreign_keys=[uploaded_by_user_id])
    deleted_by_user: Mapped[User | None] = relationship(foreign_keys=[deleted_by_user_id])
    source_connection: Mapped[SourceConnection | None] = relationship(
        foreign_keys=[source_connection_id]
    )
    source_access_policy: Mapped[SourceAccessPolicy | None] = relationship(
        foreign_keys=[source_access_policy_id]
    )
    content: Mapped[EvidenceContent | None] = relationship(
        back_populates="evidence_item",
        cascade="all, delete-orphan",
        uselist=False,
    )
    pages: Mapped[list[EvidencePageContent]] = relationship(
        back_populates="evidence_item",
        cascade="all, delete-orphan",
        order_by="EvidencePageContent.page_number",
    )
    chunks: Mapped[list[EvidenceChunk]] = relationship(
        back_populates="evidence_item",
        cascade="all, delete-orphan",
        order_by="EvidenceChunk.chunk_index",
    )
    jobs: Mapped[list[BackgroundJob]] = relationship(
        back_populates="evidence_item",
        cascade="all, delete-orphan",
        order_by="BackgroundJob.created_at.desc()",
    )


class EvidenceContent(Base):
    """Canonical separated extracted text for an evidence item (kept out of metadata_json)."""

    __tablename__ = "evidence_contents"
    __table_args__ = (
        CheckConstraint(
            "char_count >= 0 AND word_count >= 0",
            name="evidence_content_counts_non_negative",
        ),
    )

    evidence_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("evidence_items.id", ondelete="CASCADE"),
        primary_key=True,
    )
    extracted_text: Mapped[str] = mapped_column(Text, nullable=False, default="")
    char_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    word_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    extraction_warnings: Mapped[list[str]] = mapped_column(
        _JSON_VARIANT,
        nullable=False,
        default=list,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    evidence_item: Mapped[EvidenceItem] = relationship(back_populates="content")


class EvidencePageContent(Base):
    """Ordered per-page or per-section extracted content preserving structure & OCR status."""

    __tablename__ = "evidence_page_contents"
    __table_args__ = (
        UniqueConstraint("evidence_id", "page_number", name="uq_evidence_page_number"),
        CheckConstraint("page_number >= 1", name="evidence_page_number_positive"),
        CheckConstraint("char_count >= 0", name="evidence_page_char_count_non_negative"),
        CheckConstraint(
            "extraction_outcome IN ("
            "'digital_text', 'ocr_succeeded', 'ocr_truncated', "
            "'ocr_failed', 'empty', 'skipped_limit'"
            ")",
            name="evidence_page_extraction_outcome",
        ),
        Index("ix_evidence_pages_evidence_page", "evidence_id", "page_number"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    evidence_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("evidence_items.id", ondelete="CASCADE"),
        nullable=False,
    )
    page_number: Mapped[int] = mapped_column(Integer, nullable=False)
    extraction_outcome: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default=PageExtractionOutcome.DIGITAL_TEXT.value,
    )
    ocr_applied: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default="false",
    )
    ocr_truncated: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default="false",
    )
    text_content: Mapped[str] = mapped_column(Text, nullable=False, default="")
    char_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    structured_metadata: Mapped[dict[str, Any]] = mapped_column(
        _JSON_VARIANT,
        nullable=False,
        default=dict,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    evidence_item: Mapped[EvidenceItem] = relationship(back_populates="pages")


class EvidenceChunk(Base):
    """Canonical PostgreSQL evidence chunk with FTS tsvector and rebuildable Chroma tracking."""

    __tablename__ = "evidence_chunks"
    __table_args__ = (
        UniqueConstraint("evidence_id", "chunk_index", name="uq_evidence_chunk_order"),
        CheckConstraint("chunk_index >= 0", name="evidence_chunk_index_non_negative"),
        CheckConstraint(
            "char_count >= 0 AND token_estimate >= 0",
            name="evidence_chunk_counts_non_negative",
        ),
        CheckConstraint(
            "char_start >= 0 AND char_end >= char_start",
            name="evidence_chunk_offsets_valid",
        ),
        CheckConstraint(
            "page_number IS NULL OR page_number >= 1",
            name="evidence_chunk_page_positive",
        ),
        CheckConstraint(
            "length(chunk_content_hash) = 64",
            name="evidence_chunk_hash_sha256_len",
        ),
        CheckConstraint(
            "indexing_status IN ("
            "'chunked', 'embedded', 'indexed', 'partially_indexed', 'failed'"
            ")",
            name="evidence_chunk_indexing_status",
        ),
        CheckConstraint(
            "embedding_dimensions IS NULL OR embedding_dimensions > 0",
            name="evidence_chunk_embedding_dims_positive",
        ),
        CheckConstraint(
            "acl_scope IN ('project_members', 'source_restricted')",
            name="evidence_chunk_acl_scope",
        ),
        Index(
            "ix_evidence_chunks_org_project_evidence",
            "organisation_id",
            "project_id",
            "evidence_id",
        ),
        Index("ix_evidence_chunks_project_status", "project_id", "indexing_status"),
        Index("ix_evidence_chunks_project_source_type", "project_id", "source_type"),
        Index(
            "ix_evidence_chunks_search_vector",
            "search_vector",
            postgresql_using="gin",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    organisation_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("organisations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    project_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    evidence_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("evidence_items.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)
    chunk_type: Mapped[str] = mapped_column(
        String(48),
        nullable=False,
        default=EvidenceChunkType.TEXT_SEGMENT.value,
    )
    section_title: Mapped[str | None] = mapped_column(String(500), nullable=True)
    page_number: Mapped[int | None] = mapped_column(Integer, nullable=True)
    char_start: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    char_end: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    char_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    token_estimate: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    chunk_text: Mapped[str] = mapped_column(Text, nullable=False)
    chunk_content_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    search_identifier_text: Mapped[str] = mapped_column(Text, nullable=False, default="")
    search_vector: Mapped[str | None] = mapped_column(_TSVECTOR_VARIANT, nullable=True)
    source_type: Mapped[str] = mapped_column(String(32), nullable=False)
    source_author_identity: Mapped[str | None] = mapped_column(String(255), nullable=True)
    source_created_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    acl_scope: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="project_members",
        server_default="project_members",
    )
    metadata_json: Mapped[dict[str, Any]] = mapped_column(
        _JSON_VARIANT,
        nullable=False,
        default=dict,
    )
    indexing_status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default=ChunkIndexingStatus.CHUNKED.value,
        server_default=ChunkIndexingStatus.CHUNKED.value,
    )
    chroma_collection_name: Mapped[str | None] = mapped_column(String(160), nullable=True)
    chroma_vector_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    embedding_model: Mapped[str | None] = mapped_column(String(128), nullable=True)
    embedding_dimensions: Mapped[int | None] = mapped_column(Integer, nullable=True)
    embedded_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    error_code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    error_message: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    evidence_item: Mapped[EvidenceItem] = relationship(back_populates="chunks")
    organisation: Mapped[Organisation] = relationship(foreign_keys=[organisation_id])
    project: Mapped[Project] = relationship(foreign_keys=[project_id])
