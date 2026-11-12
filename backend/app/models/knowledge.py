"""Canonical SQLAlchemy models for Phase 2.6 knowledge reconstruction and provenance."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import (
    JSON,
    Boolean,
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
from app.models.enums import (
    EpistemicStatus,
    ExtractionRunStatus,
    KnowledgeReviewStatus,
)

if TYPE_CHECKING:
    from app.models.evidence import EvidenceChunk, EvidenceItem
    from app.models.job import BackgroundJob
    from app.models.organisation import Organisation
    from app.models.project import Project
    from app.models.user import User

_JSON_VARIANT = JSON().with_variant(JSONB(astext_type=Text()), "postgresql")


class KnowledgeExtractionRun(Base):
    """Tracks execution lifecycle, model/prompt versioning, and metrics per extraction run."""

    __tablename__ = "knowledge_extraction_runs"
    __table_args__ = (
        CheckConstraint(
            "scope_type IN ('evidence', 'project')",
            name="knowledge_extraction_scope_type",
        ),
        CheckConstraint(
            "status IN ("
            "'queued', 'running', 'completed', 'partially_completed', 'failed', 'cancelled'"
            ")",
            name="knowledge_extraction_run_status",
        ),
        CheckConstraint(
            "total_evidence_items >= 0 AND processed_evidence_items >= 0 "
            "AND failed_evidence_items >= 0 AND skipped_evidence_items >= 0 "
            "AND total_chunks_evaluated >= 0 AND batches_executed >= 0 "
            "AND candidates_generated >= 0 AND claims_persisted >= 0 "
            "AND claims_rejected_ungrounded >= 0 AND duplicates_merged >= 0 "
            "AND prompt_tokens >= 0 AND completion_tokens >= 0",
            name="knowledge_extraction_counters_non_negative",
        ),
        Index(
            "ix_knowledge_extraction_runs_project_created",
            "project_id",
            "created_at",
        ),
        Index(
            "ix_knowledge_extraction_runs_project_status",
            "project_id",
            "status",
        ),
        Index(
            "ix_knowledge_extraction_runs_evidence_id",
            "evidence_id",
        ),
        Index(
            "ix_knowledge_extraction_runs_job_id",
            "background_job_id",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organisation_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("organisations.id", ondelete="CASCADE"),
        nullable=False,
    )
    project_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
    )
    background_job_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("background_jobs.id", ondelete="SET NULL"),
        nullable=True,
    )
    evidence_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("evidence_items.id", ondelete="CASCADE"),
        nullable=True,
    )
    triggered_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    scope_type: Mapped[str] = mapped_column(String(32), nullable=False)
    target_categories: Mapped[list[str]] = mapped_column(
        _JSON_VARIANT, nullable=False, default=list
    )
    model_name: Mapped[str] = mapped_column(String(128), nullable=False)
    prompt_version: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default=ExtractionRunStatus.QUEUED.value,
    )
    is_synthetic: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default=text("false"),
    )

    total_evidence_items: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default=text("0")
    )
    processed_evidence_items: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default=text("0")
    )
    failed_evidence_items: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default=text("0")
    )
    skipped_evidence_items: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default=text("0")
    )
    total_chunks_evaluated: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default=text("0")
    )
    batches_executed: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default=text("0")
    )
    candidates_generated: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default=text("0")
    )
    claims_persisted: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default=text("0")
    )
    claims_rejected_ungrounded: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default=text("0")
    )
    duplicates_merged: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default=text("0")
    )
    prompt_tokens: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default=text("0")
    )
    completion_tokens: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default=text("0")
    )

    warnings_json: Mapped[list[str]] = mapped_column(_JSON_VARIANT, nullable=False, default=list)
    error_code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    error_message: Mapped[str | None] = mapped_column(String(500), nullable=True)

    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    duration_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    organisation: Mapped[Organisation] = relationship("Organisation")
    project: Mapped[Project] = relationship("Project")
    background_job: Mapped[BackgroundJob | None] = relationship("BackgroundJob")
    evidence_item: Mapped[EvidenceItem | None] = relationship("EvidenceItem")
    triggered_by_user: Mapped[User | None] = relationship("User")
    knowledge_items: Mapped[list[KnowledgeItem]] = relationship(
        "KnowledgeItem",
        back_populates="extraction_run",
        passive_deletes=True,
    )


class KnowledgeItem(Base):
    """Canonical structured project knowledge item backed strictly by cited evidence."""

    __tablename__ = "knowledge_items"
    __table_args__ = (
        CheckConstraint(
            "category IN ("
            "'decisions_rationale', 'work_items', 'responsibilities_ownership', "
            "'technical_architecture', 'bugs_blockers_risks', 'dependencies'"
            ")",
            name="knowledge_item_category",
        ),
        CheckConstraint(
            "epistemic_status IN ('extracted', 'ai_interpreted', 'human_verified')",
            name="knowledge_item_epistemic_status",
        ),
        CheckConstraint(
            "review_status IN ('pending_review', 'approved', 'rejected', 'needs_clarification')",
            name="knowledge_item_review_status",
        ),
        CheckConstraint(
            "support_classification IN ('direct', 'corroborated', 'interpretation', 'uncertain')",
            name="knowledge_item_support_classification",
        ),
        Index(
            "ix_knowledge_items_project_cat_fp",
            "project_id",
            "category",
            "fingerprint",
        ),
        Index(
            "ix_knowledge_items_project_filters",
            "project_id",
            "is_deleted",
            "is_stale",
            "category",
            "review_status",
        ),
        Index("ix_knowledge_items_run_id", "extraction_run_id"),
        Index("ix_knowledge_items_org_project", "organisation_id", "project_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organisation_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("organisations.id", ondelete="CASCADE"),
        nullable=False,
    )
    project_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
    )
    extraction_run_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("knowledge_extraction_runs.id", ondelete="SET NULL"),
        nullable=True,
    )

    category: Mapped[str] = mapped_column(String(64), nullable=False)
    epistemic_status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default=EpistemicStatus.EXTRACTED.value,
    )
    review_status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default=KnowledgeReviewStatus.PENDING_REVIEW.value,
    )
    support_classification: Mapped[str] = mapped_column(String(32), nullable=False)

    title: Mapped[str] = mapped_column(String(500), nullable=False)
    structured_summary: Mapped[str] = mapped_column(Text, nullable=False)
    structured_payload: Mapped[dict[str, Any]] = mapped_column(_JSON_VARIANT, nullable=False)
    normalised_status: Mapped[str | None] = mapped_column(String(64), nullable=True)
    person_or_owner_label: Mapped[str | None] = mapped_column(String(255), nullable=True)
    source_attribution_json: Mapped[dict[str, Any]] = mapped_column(
        _JSON_VARIANT, nullable=False, default=dict
    )

    extraction_model: Mapped[str] = mapped_column(String(128), nullable=False)
    prompt_version: Mapped[str] = mapped_column(String(64), nullable=False)
    fingerprint: Mapped[str] = mapped_column(String(64), nullable=False)

    confidence_metadata_json: Mapped[dict[str, Any]] = mapped_column(
        _JSON_VARIANT, nullable=False, default=dict
    )
    uncertainty_reason: Mapped[str | None] = mapped_column(Text, nullable=True)

    is_stale: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default=text("false"),
    )
    stale_reason: Mapped[str | None] = mapped_column(String(255), nullable=True)
    stale_detected_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    superseded_by_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("knowledge_items.id", ondelete="SET NULL"),
        nullable=True,
    )

    is_synthetic: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default=text("false"),
    )
    source_observed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    is_deleted: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default=text("false"),
    )
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    extraction_run: Mapped[KnowledgeExtractionRun | None] = relationship(
        "KnowledgeExtractionRun",
        back_populates="knowledge_items",
    )
    evidence_links: Mapped[list[KnowledgeEvidenceLink]] = relationship(
        "KnowledgeEvidenceLink",
        back_populates="knowledge_item",
        cascade="all, delete-orphan",
        order_by="KnowledgeEvidenceLink.created_at.asc()",
    )


class KnowledgeEvidenceLink(Base):
    """Verifiable provenance link joining a KnowledgeItem to canonical evidence and chunks."""

    __tablename__ = "knowledge_evidence_links"
    __table_args__ = (
        CheckConstraint(
            "support_type IN ('direct', 'corroborated', 'interpretation', 'uncertain')",
            name="knowledge_evidence_link_support_type",
        ),
        CheckConstraint(
            "excerpt_match_mode IN ('exact', 'normalized_whitespace')",
            name="knowledge_evidence_link_match_mode",
        ),
        Index(
            "ix_knowledge_evidence_links_item_evidence",
            "knowledge_item_id",
            "evidence_id",
        ),
        Index(
            "ix_knowledge_evidence_links_evidence_id",
            "evidence_id",
            "knowledge_item_id",
        ),
        Index("ix_knowledge_evidence_links_chunk_id", "evidence_chunk_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organisation_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("organisations.id", ondelete="CASCADE"),
        nullable=False,
    )
    project_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
    )
    knowledge_item_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("knowledge_items.id", ondelete="CASCADE"),
        nullable=False,
    )
    evidence_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("evidence_items.id", ondelete="CASCADE"),
        nullable=False,
    )
    evidence_chunk_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("evidence_chunks.id", ondelete="SET NULL"),
        nullable=True,
    )

    support_type: Mapped[str] = mapped_column(String(32), nullable=False)
    source_location_json: Mapped[dict[str, Any]] = mapped_column(
        _JSON_VARIANT, nullable=False, default=dict
    )
    supporting_excerpt: Mapped[str] = mapped_column(Text, nullable=False)
    excerpt_verified: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default=text("true"),
    )
    excerpt_match_mode: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="exact",
    )
    source_metadata_json: Mapped[dict[str, Any]] = mapped_column(
        _JSON_VARIANT, nullable=False, default=dict
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    knowledge_item: Mapped[KnowledgeItem] = relationship(
        "KnowledgeItem",
        back_populates="evidence_links",
    )
    evidence_item: Mapped[EvidenceItem] = relationship("EvidenceItem")
    evidence_chunk: Mapped[EvidenceChunk | None] = relationship("EvidenceChunk")
