"""PostgreSQL-backed background job queue tracking SQLAlchemy model."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import (
    JSON,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    Uuid,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.enums import BackgroundJobStatus, BackgroundJobType

if TYPE_CHECKING:
    from app.models.evidence import EvidenceItem
    from app.models.organisation import Organisation
    from app.models.project import Project
    from app.models.user import User

_JSON_VARIANT = JSON().with_variant(JSONB(astext_type=Text()), "postgresql")


class BackgroundJob(Base):
    """Durable PostgreSQL-tracked background work item without external brokers."""

    __tablename__ = "background_jobs"
    __table_args__ = (
        CheckConstraint(
            "job_type IN ("
            "'document_ingestion', 'source_sync', "
            "'evidence_chunking', 'evidence_embedding', 'evidence_indexing', "
            "'evidence_reindexing', 'evidence_index_cleanup', "
            "'knowledge_reconstruction', 'relationship_reconstruction'"
            ")",
            name="background_job_type",
        ),
        CheckConstraint(
            "status IN ('queued', 'running', 'succeeded', 'failed', 'cancelled')",
            name="background_job_status",
        ),
        CheckConstraint(
            "attempt_count >= 0 AND max_attempts >= 1 AND attempt_count <= max_attempts",
            name="background_job_attempts_valid",
        ),
        CheckConstraint(
            "duration_ms IS NULL OR duration_ms >= 0",
            name="background_job_duration_non_negative",
        ),
        Index(
            "ix_background_jobs_claimable",
            "priority",
            "next_retry_at",
            "created_at",
            sqlite_where=text("status = 'queued'"),
            postgresql_where=text("status = 'queued'"),
        ),
        Index("ix_background_jobs_evidence_created", "evidence_id", "created_at"),
        Index(
            "ix_background_jobs_org_project_status",
            "organisation_id",
            "project_id",
            "status",
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
    evidence_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("evidence_items.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    triggered_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    job_type: Mapped[str] = mapped_column(
        String(48),
        nullable=False,
        default=BackgroundJobType.DOCUMENT_INGESTION.value,
    )
    status: Mapped[str] = mapped_column(
        String(24),
        nullable=False,
        default=BackgroundJobStatus.QUEUED.value,
        server_default=BackgroundJobStatus.QUEUED.value,
        index=True,
    )
    priority: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=100,
        server_default="100",
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
    payload_json: Mapped[dict[str, Any]] = mapped_column(
        _JSON_VARIANT,
        nullable=False,
        default=dict,
    )
    result_json: Mapped[dict[str, Any] | None] = mapped_column(
        _JSON_VARIANT,
        nullable=True,
        default=None,
    )
    error_code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    error_message: Mapped[str | None] = mapped_column(String(500), nullable=True)
    locked_by: Mapped[str | None] = mapped_column(String(128), nullable=True)
    locked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    lease_expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    next_retry_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    duration_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
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
    evidence_item: Mapped[EvidenceItem | None] = relationship(
        back_populates="jobs",
        foreign_keys=[evidence_id],
    )
    triggered_by_user: Mapped[User | None] = relationship(foreign_keys=[triggered_by_user_id])
