"""ORM models for Verification Center (Module 3 / Validation Area).

Provides canonical persistence for:
- Verification cases (polymorphic tracking of knowledge items and relationships)
- Verification issues (provenance, grounding, freshness, and consistency flaws)
- Verification conflicts (side-by-side cross-source contradiction records)
- Verification review events (immutable, append-only human review action history)
- Verification context requests (in-platform clarification requests to team members)
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import JSON

from app.db.base import Base
from app.models.enums import (
    ConflictResolutionState,
    ConflictType,
    ContextRequestStatus,
    IssueResolutionState,
    MachineAssessmentStatus,
    ReviewActionType,
    TemporalComparison,
    VerificationCaseStatus,
    VerificationIssueType,
    VerificationPriority,
    VerificationSeverity,
    VerificationTargetType,
)

_JSON_VARIANT = JSON().with_variant(JSONB(astext_type=Text()), "postgresql")


class VerificationCase(Base):
    """Canonical verification case tracking validation status and human review."""

    __tablename__ = "verification_cases"
    __table_args__ = (
        Index("ix_vc_project_status", "project_id", "case_status"),
        Index("ix_vc_project_target", "project_id", "target_type", "target_id"),
        Index("ix_vc_project_priority", "project_id", "priority"),
        Index("ix_vc_assigned_reviewer", "project_id", "assigned_reviewer_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    organisation_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("organisations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    project_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True
    )

    target_type: Mapped[VerificationTargetType] = mapped_column(String(32), nullable=False)
    target_id: Mapped[uuid.UUID] = mapped_column(nullable=False, index=True)

    case_status: Mapped[VerificationCaseStatus] = mapped_column(
        String(32), default=VerificationCaseStatus.CANDIDATE, nullable=False
    )
    machine_assessment_status: Mapped[MachineAssessmentStatus] = mapped_column(
        String(32), default=MachineAssessmentStatus.PASSED, nullable=False
    )
    priority: Mapped[VerificationPriority] = mapped_column(
        String(16), default=VerificationPriority.MEDIUM, nullable=False
    )
    assigned_reviewer_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    machine_assessment_json: Mapped[dict[str, Any]] = mapped_column(
        _JSON_VARIANT, default=dict, nullable=False
    )
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)

    last_assessed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    last_reviewed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    # Relationships
    issues: Mapped[list[VerificationIssue]] = relationship(
        "VerificationIssue",
        back_populates="case",
        cascade="all, delete-orphan",
        order_by="VerificationIssue.created_at.asc()",
    )
    conflicts: Mapped[list[VerificationConflict]] = relationship(
        "VerificationConflict",
        back_populates="case",
        cascade="all, delete-orphan",
        order_by="VerificationConflict.created_at.asc()",
    )
    review_events: Mapped[list[VerificationReviewEvent]] = relationship(
        "VerificationReviewEvent",
        back_populates="case",
        cascade="all, delete-orphan",
        order_by="VerificationReviewEvent.created_at.desc()",
    )
    context_requests: Mapped[list[VerificationContextRequest]] = relationship(
        "VerificationContextRequest",
        back_populates="case",
        cascade="all, delete-orphan",
        order_by="VerificationContextRequest.created_at.desc()",
    )
    assigned_reviewer: Mapped[Any] = relationship("User", foreign_keys=[assigned_reviewer_id])
    project: Mapped[Any] = relationship("Project")
    organisation: Mapped[Any] = relationship("Organisation")


class VerificationIssue(Base):
    """Specific flaw, missing evidence item, or detected inconsistency."""

    __tablename__ = "verification_issues"
    __table_args__ = (
        Index("ix_vi_case_type", "case_id", "issue_type"),
        Index("ix_vi_project_state", "project_id", "resolution_state"),
        Index("ix_vi_project_severity", "project_id", "severity"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    organisation_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("organisations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    project_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True
    )
    case_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("verification_cases.id", ondelete="CASCADE"), nullable=False, index=True
    )

    issue_type: Mapped[VerificationIssueType] = mapped_column(String(64), nullable=False)
    severity: Mapped[VerificationSeverity] = mapped_column(
        String(16), default=VerificationSeverity.MEDIUM, nullable=False
    )
    description: Mapped[str] = mapped_column(Text, nullable=False)
    detection_method: Mapped[str] = mapped_column(
        String(32), default="deterministic_rule", nullable=False
    )
    details_json: Mapped[dict[str, Any]] = mapped_column(
        _JSON_VARIANT, default=dict, nullable=False
    )

    conflicting_evidence_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("evidence_items.id", ondelete="SET NULL"), nullable=True, index=True
    )
    conflicting_chunk_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("evidence_chunks.id", ondelete="SET NULL"), nullable=True, index=True
    )

    resolution_state: Mapped[IssueResolutionState] = mapped_column(
        String(32), default=IssueResolutionState.OPEN, nullable=False
    )
    resolution_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    resolved_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    # Relationships
    case: Mapped[VerificationCase] = relationship("VerificationCase", back_populates="issues")
    conflicting_evidence: Mapped[Any] = relationship(
        "EvidenceItem", foreign_keys=[conflicting_evidence_id]
    )
    conflicting_chunk: Mapped[Any] = relationship(
        "EvidenceChunk", foreign_keys=[conflicting_chunk_id]
    )
    resolved_by_user: Mapped[Any] = relationship("User", foreign_keys=[resolved_by_user_id])


class VerificationConflict(Base):
    """Side-by-side contradiction record between conflicting evidence claims."""

    __tablename__ = "verification_conflicts"
    __table_args__ = (
        Index("ix_vc_conflicts_case", "case_id", "resolution_state"),
        Index("ix_vc_conflicts_project_type", "project_id", "conflict_type"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    organisation_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("organisations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    project_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True
    )
    case_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("verification_cases.id", ondelete="CASCADE"), nullable=False, index=True
    )

    conflict_type: Mapped[ConflictType] = mapped_column(String(32), nullable=False)
    claim_a_text: Mapped[str] = mapped_column(Text, nullable=False)
    claim_a_source_evidence_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("evidence_items.id", ondelete="CASCADE"), nullable=False, index=True
    )
    claim_a_chunk_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("evidence_chunks.id", ondelete="SET NULL"), nullable=True, index=True
    )
    claim_a_source_timestamp: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    claim_b_text: Mapped[str] = mapped_column(Text, nullable=False)
    claim_b_source_evidence_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("evidence_items.id", ondelete="CASCADE"), nullable=False, index=True
    )
    claim_b_chunk_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("evidence_chunks.id", ondelete="SET NULL"), nullable=True, index=True
    )
    claim_b_source_timestamp: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    explanation: Mapped[str] = mapped_column(Text, nullable=False)
    temporal_comparison: Mapped[TemporalComparison] = mapped_column(
        String(32), default=TemporalComparison.AMBIGUOUS, nullable=False
    )
    resolution_state: Mapped[ConflictResolutionState] = mapped_column(
        String(32), default=ConflictResolutionState.UNRESOLVED, nullable=False
    )
    resolution_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    resolved_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Relationships
    case: Mapped[VerificationCase] = relationship("VerificationCase", back_populates="conflicts")
    claim_a_evidence: Mapped[Any] = relationship(
        "EvidenceItem", foreign_keys=[claim_a_source_evidence_id]
    )
    claim_b_evidence: Mapped[Any] = relationship(
        "EvidenceItem", foreign_keys=[claim_b_source_evidence_id]
    )
    resolved_by_user: Mapped[Any] = relationship("User", foreign_keys=[resolved_by_user_id])


class VerificationReviewEvent(Base):
    """Immutable, append-only history of human verification decisions and field corrections."""

    __tablename__ = "verification_review_events"
    __table_args__ = (
        Index("ix_vre_case_time", "case_id", "created_at"),
        Index("ix_vre_project_reviewer", "project_id", "reviewer_user_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    organisation_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("organisations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    project_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True
    )
    case_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("verification_cases.id", ondelete="CASCADE"), nullable=False, index=True
    )
    reviewer_user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )

    action: Mapped[ReviewActionType] = mapped_column(String(32), nullable=False)
    previous_status: Mapped[str] = mapped_column(String(32), nullable=False)
    new_status: Mapped[str] = mapped_column(String(32), nullable=False)
    review_notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    finding_patch_json: Mapped[dict[str, Any] | None] = mapped_column(
        _JSON_VARIANT, default=None, nullable=True
    )
    previous_snapshot_json: Mapped[dict[str, Any] | None] = mapped_column(
        _JSON_VARIANT, default=None, nullable=True
    )
    new_snapshot_json: Mapped[dict[str, Any] | None] = mapped_column(
        _JSON_VARIANT, default=None, nullable=True
    )

    correlation_id: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Relationships
    case: Mapped[VerificationCase] = relationship(
        "VerificationCase", back_populates="review_events"
    )
    reviewer: Mapped[Any] = relationship("User", foreign_keys=[reviewer_user_id])


class VerificationContextRequest(Base):
    """Clarification request dispatched to a departing project member or team lead."""

    __tablename__ = "verification_context_requests"
    __table_args__ = (
        Index("ix_vcr_case_status", "case_id", "status"),
        Index("ix_vcr_target_user", "requested_from_user_id", "status"),
        Index("ix_vcr_project_status", "project_id", "status"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    organisation_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("organisations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    project_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True
    )
    case_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("verification_cases.id", ondelete="CASCADE"), nullable=False, index=True
    )

    requested_by_user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    requested_from_user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )

    question: Mapped[str] = mapped_column(Text, nullable=False)
    requested_information_type: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[ContextRequestStatus] = mapped_column(
        String(32), default=ContextRequestStatus.PENDING, nullable=False
    )

    response_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    response_evidence_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("evidence_items.id", ondelete="SET NULL"), nullable=True, index=True
    )
    responded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    # Relationships
    case: Mapped[VerificationCase] = relationship(
        "VerificationCase", back_populates="context_requests"
    )
    requested_by: Mapped[Any] = relationship("User", foreign_keys=[requested_by_user_id])
    requested_from: Mapped[Any] = relationship("User", foreign_keys=[requested_from_user_id])
    response_evidence: Mapped[Any] = relationship(
        "EvidenceItem", foreign_keys=[response_evidence_id]
    )
