"""Evidence Workspace SQLAlchemy models supporting external sources, uploads, and extraction."""

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
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.enums import (
    EvidenceProcessingStatus,
    EvidenceVerificationStatus,
    JobStatus,
    SourceConnectionStatus,
    SourceProvider,
    SyncStatus,
)

if TYPE_CHECKING:
    from app.models.organisation import Organisation
    from app.models.project import Project
    from app.models.user import User


class SourceConnection(Base):
    """Delegated external source authorization (GitHub, Jira, Slack) scoped to an Organisation."""

    __tablename__ = "source_connections"
    __table_args__ = (
        CheckConstraint(
            "provider IN ('github', 'jira', 'slack')",
            name="source_connection_provider",
        ),
        CheckConstraint(
            "connection_status IN ('connected', 'needs_reauth', 'disconnected', 'error')",
            name="source_connection_status_valid",
        ),
        Index("ix_source_connections_org_provider", "organisation_id", "provider"),
        Index("ix_source_connections_connected_by", "connected_by_id"),
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
    connected_by_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    provider: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default=SourceProvider.GITHUB.value,
    )
    account_identifier: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    encrypted_access_token: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
    encrypted_refresh_token: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    token_expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    scopes: Mapped[list[str] | None] = mapped_column(
        JSON,
        nullable=True,
        default=list,
    )
    connection_status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default=SourceConnectionStatus.CONNECTED.value,
        server_default=SourceConnectionStatus.CONNECTED.value,
    )
    last_health_check_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    error_message: Mapped[str | None] = mapped_column(
        Text,
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
    connected_by: Mapped[User] = relationship(foreign_keys=[connected_by_id])
    project_mappings: Mapped[list[ProjectSourceMapping]] = relationship(
        back_populates="source_connection",
        cascade="all, delete-orphan",
    )


class ProjectSourceMapping(Base):
    """Explicit mapping between external source (repo, Jira project) and platform Project."""

    __tablename__ = "project_source_mappings"
    __table_args__ = (
        UniqueConstraint(
            "project_id",
            "external_resource_id",
            name="uq_project_source_mappings_project_resource",
        ),
        CheckConstraint(
            "sync_status IN ('idle', 'syncing', 'completed', 'failed')",
            name="project_source_mapping_sync_status",
        ),
        Index("ix_project_source_mappings_project_status", "project_id", "sync_status"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    project_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    source_connection_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("source_connections.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    external_resource_id: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    external_resource_name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    external_metadata: Mapped[dict[str, Any] | None] = mapped_column(
        JSON,
        nullable=True,
        default=dict,
    )
    sync_status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default=SyncStatus.IDLE.value,
        server_default=SyncStatus.IDLE.value,
    )
    last_synced_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    sync_error: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default="true",
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

    project: Mapped[Project] = relationship(foreign_keys=[project_id])
    source_connection: Mapped[SourceConnection] = relationship(back_populates="project_mappings")
    evidence_items: Mapped[list[EvidenceItem]] = relationship(
        back_populates="source_mapping",
    )
    sync_jobs: Mapped[list[SourceSyncJob]] = relationship(
        back_populates="source_mapping",
        cascade="all, delete-orphan",
    )


class EvidenceItem(Base):
    """Canonical evidence record representing an ingested source item or uploaded document."""

    __tablename__ = "evidence_items"
    __table_args__ = (
        CheckConstraint(
            "provider IN ('github', 'jira', 'pdf', 'docx', 'slack')",
            name="evidence_item_provider",
        ),
        CheckConstraint(
            "processing_status IN ('pending', 'processing', 'extracted', 'indexed', 'failed')",
            name="evidence_item_processing_status",
        ),
        CheckConstraint(
            "verification_status IN ("
            "'unverified', 'candidate', 'verified', 'conflicted', 'rejected')",
            name="evidence_item_verification_status",
        ),
        Index("ix_evidence_items_proj_provider", "project_id", "provider"),
        Index("ix_evidence_items_proj_status", "project_id", "processing_status"),
        Index("ix_evidence_items_proj_created", "project_id", "created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    project_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    source_mapping_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("project_source_mappings.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    provider: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
    )
    record_type: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
    )
    external_source_id: Mapped[str] = mapped_column(
        String(500),
        nullable=False,
        index=True,
    )
    source_url: Mapped[str | None] = mapped_column(
        String(2048),
        nullable=True,
    )
    title: Mapped[str] = mapped_column(
        String(500),
        nullable=False,
    )
    author: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )
    source_created_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    source_updated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    ingested_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    processing_status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default=EvidenceProcessingStatus.PENDING.value,
        server_default=EvidenceProcessingStatus.PENDING.value,
    )
    verification_status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default=EvidenceVerificationStatus.UNVERIFIED.value,
        server_default=EvidenceVerificationStatus.UNVERIFIED.value,
    )
    content_hash: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
    )
    raw_metadata: Mapped[dict[str, Any] | None] = mapped_column(
        JSON,
        nullable=True,
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

    project: Mapped[Project] = relationship(foreign_keys=[project_id])
    source_mapping: Mapped[ProjectSourceMapping | None] = relationship(
        back_populates="evidence_items"
    )
    document_file: Mapped[DocumentFile | None] = relationship(
        back_populates="evidence_item",
        uselist=False,
        cascade="all, delete-orphan",
    )
    contents: Mapped[list[EvidenceContent]] = relationship(
        back_populates="evidence_item",
        cascade="all, delete-orphan",
    )


class DocumentFile(Base):
    """Uploaded physical document metadata and encrypted storage pointer."""

    __tablename__ = "document_files"
    __table_args__ = (
        UniqueConstraint("evidence_item_id", name="uq_document_files_evidence_item"),
        CheckConstraint(
            "file_format IN ('pdf', 'docx')",
            name="document_file_format_valid",
        ),
        Index("ix_document_files_sha256", "sha256_hash"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    evidence_item_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("evidence_items.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )
    uploaded_by_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    original_filename: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    file_format: Mapped[str] = mapped_column(
        String(16),
        nullable=False,
    )
    mime_type: Mapped[str] = mapped_column(
        String(128),
        nullable=False,
    )
    file_size_bytes: Mapped[int] = mapped_column(
        BigInteger,
        nullable=False,
    )
    storage_path: Mapped[str] = mapped_column(
        String(1024),
        nullable=False,
    )
    sha256_hash: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
    )
    is_encrypted: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default="true",
    )
    page_count: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )
    ocr_applied: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default="false",
    )
    extraction_error: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    evidence_item: Mapped[EvidenceItem] = relationship(back_populates="document_file")
    uploaded_by: Mapped[User] = relationship(foreign_keys=[uploaded_by_id])


class EvidenceContent(Base):
    """Extracted text chunks, page coordinates, and vector indexing metadata for an EvidenceItem."""

    __tablename__ = "evidence_contents"
    __table_args__ = (
        Index("ix_evidence_contents_item_chunk", "evidence_item_id", "chunk_index"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    evidence_item_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("evidence_items.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    chunk_index: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )
    page_number: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )
    section_heading: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )
    content_text: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
    token_count: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )
    chroma_point_id: Mapped[str | None] = mapped_column(
        String(128),
        nullable=True,
    )
    indexing_status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default=EvidenceProcessingStatus.PENDING.value,
        server_default=EvidenceProcessingStatus.PENDING.value,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    evidence_item: Mapped[EvidenceItem] = relationship(back_populates="contents")


class SourceSyncJob(Base):
    """PostgreSQL-backed job queue for background ingestion, sync, and OCR processing."""

    __tablename__ = "source_sync_jobs"
    __table_args__ = (
        CheckConstraint(
            "status IN ('queued', 'running', 'completed', 'failed')",
            name="source_sync_job_status_valid",
        ),
        Index("ix_source_sync_jobs_status_created", "status", "created_at"),
        Index("ix_source_sync_jobs_project", "project_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    project_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    source_mapping_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("project_source_mappings.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    job_type: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
    )
    status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default=JobStatus.QUEUED.value,
        server_default=JobStatus.QUEUED.value,
    )
    attempt_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default="0",
    )
    max_attempts: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=3,
        server_default="3",
    )
    locked_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    locked_by: Mapped[str | None] = mapped_column(
        String(128),
        nullable=True,
    )
    error_message: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    progress_percent: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default="0",
    )
    started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    project: Mapped[Project] = relationship(foreign_keys=[project_id])
    source_mapping: Mapped[ProjectSourceMapping | None] = relationship(back_populates="sync_jobs")
