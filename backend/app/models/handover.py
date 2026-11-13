"""SQLAlchemy ORM models for Handover Workspace (Module 4 / Knowledge Transfer Area).

Provides canonical persistence for:
- HandoverCase: Central case managing lifecycle, participants, and metadata
- HandoverPackage: Top-level handover package container
- HandoverPackageVersion: Immutable, versioned assembly snapshot
- HandoverPackageSection: 8-domain structured knowledge compilation
- HandoverContentLink: Lineage links to knowledge items, relationships, and evidence
- HandoverReadinessAssessment: 9-category readiness evaluation results
- HandoverChecklist: Dynamic checklist container
- HandoverChecklistItem: Individual actionable checklist tasks
- HandoverResponsibilityTransfer: Mapped departing -> successor ownership handover
- HandoverSignoff: Three-phase human sign-offs (departing, reviewer, successor)
- HandoverDelivery: Package delivery and encrypted artifact distribution
- HandoverAcknowledgement: Successor receipt and understanding confirmation
- HandoverStatusHistory: Immutable lifecycle status transition audit trail
- HandoverOwnershipTransfer: Explicit internal project/component ownership changes
"""

from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import Any

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import JSON

from app.db.base import Base
from app.models.enums import (
    ChecklistItemStatus,
    HandoverCaseStatus,
    HandoverChecklistType,
    HandoverDeliveryMethod,
    HandoverLinkType,
    HandoverPackageSectionType,
    HandoverReadinessCategory,
    OwnershipTransferType,
    ReadinessLevel,
    SignoffDecision,
    SignoffType,
    TransferStatus,
)

_JSON_VARIANT = JSON().with_variant(JSONB(astext_type=Text()), "postgresql")


class HandoverCase(Base):
    """Central handover case tracking lifecycle, participants, and status transitions."""

    __tablename__ = "handover_cases"
    __table_args__ = (
        Index("ix_hc_project_status", "project_id", "status"),
        Index("ix_hc_project_departing", "project_id", "departing_member_id"),
        Index("ix_hc_project_successor", "project_id", "successor_id"),
        Index("ix_hc_org_project", "organisation_id", "project_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    organisation_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("organisations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    project_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True
    )

    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(
        String(32), default=HandoverCaseStatus.DRAFT.value, nullable=False, index=True
    )

    departing_member_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    successor_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    target_handover_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    created_by_user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )

    metadata_json: Mapped[dict[str, Any]] = mapped_column(
        _JSON_VARIANT, default=dict, nullable=False
    )
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    # Relationships
    package: Mapped[HandoverPackage | None] = relationship(
        "HandoverPackage",
        back_populates="case",
        uselist=False,
        cascade="all, delete-orphan",
    )
    versions: Mapped[list[HandoverPackageVersion]] = relationship(
        "HandoverPackageVersion",
        back_populates="case",
        cascade="all, delete-orphan",
        order_by="HandoverPackageVersion.version_number.desc()",
    )
    checklists: Mapped[list[HandoverChecklist]] = relationship(
        "HandoverChecklist",
        back_populates="case",
        cascade="all, delete-orphan",
        order_by="HandoverChecklist.created_at.asc()",
    )
    responsibility_transfers: Mapped[list[HandoverResponsibilityTransfer]] = relationship(
        "HandoverResponsibilityTransfer",
        back_populates="case",
        cascade="all, delete-orphan",
        order_by="HandoverResponsibilityTransfer.created_at.asc()",
    )
    signoffs: Mapped[list[HandoverSignoff]] = relationship(
        "HandoverSignoff",
        back_populates="case",
        cascade="all, delete-orphan",
        order_by="HandoverSignoff.signed_at.desc()",
    )
    status_history: Mapped[list[HandoverStatusHistory]] = relationship(
        "HandoverStatusHistory",
        back_populates="case",
        cascade="all, delete-orphan",
        order_by="HandoverStatusHistory.changed_at.desc()",
    )
    ownership_transfers: Mapped[list[HandoverOwnershipTransfer]] = relationship(
        "HandoverOwnershipTransfer",
        back_populates="case",
        cascade="all, delete-orphan",
        order_by="HandoverOwnershipTransfer.executed_at.desc()",
    )
    departing_member: Mapped[Any] = relationship("User", foreign_keys=[departing_member_id])
    successor: Mapped[Any] = relationship("User", foreign_keys=[successor_id])
    created_by_user: Mapped[Any] = relationship("User", foreign_keys=[created_by_user_id])
    project: Mapped[Any] = relationship("Project")
    organisation: Mapped[Any] = relationship("Organisation")


class HandoverPackage(Base):
    """Top-level container grouping immutable versions of a handover package."""

    __tablename__ = "handover_packages"
    __table_args__ = (
        UniqueConstraint("case_id", name="uq_handover_package_case"),
        Index("ix_hp_project_case", "project_id", "case_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    organisation_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("organisations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    project_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True
    )
    case_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("handover_cases.id", ondelete="CASCADE"), nullable=False, unique=True
    )

    title: Mapped[str] = mapped_column(String(255), nullable=False)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_by_user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    # Relationships
    case: Mapped[HandoverCase] = relationship("HandoverCase", back_populates="package")
    versions: Mapped[list[HandoverPackageVersion]] = relationship(
        "HandoverPackageVersion",
        back_populates="package",
        cascade="all, delete-orphan",
        order_by="HandoverPackageVersion.version_number.desc()",
    )
    created_by_user: Mapped[Any] = relationship("User", foreign_keys=[created_by_user_id])


class HandoverPackageVersion(Base):
    """Immutable, versioned snapshot of the assembled handover package."""

    __tablename__ = "handover_package_versions"
    __table_args__ = (
        UniqueConstraint("package_id", "version_number", name="uq_hpv_package_version"),
        Index("ix_hpv_case_version", "case_id", "version_number"),
        Index("ix_hpv_package_current", "package_id", "is_current"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    organisation_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("organisations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    project_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True
    )
    package_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("handover_packages.id", ondelete="CASCADE"), nullable=False, index=True
    )
    case_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("handover_cases.id", ondelete="CASCADE"), nullable=False, index=True
    )

    version_number: Mapped[int] = mapped_column(Integer, nullable=False)
    is_current: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    assembly_status: Mapped[str] = mapped_column(
        String(32), default="assembled", nullable=False
    )

    assembly_snapshot_json: Mapped[dict[str, Any]] = mapped_column(
        _JSON_VARIANT, default=dict, nullable=False
    )
    assembled_by_user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    assembled_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    content_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Relationships
    package: Mapped[HandoverPackage] = relationship("HandoverPackage", back_populates="versions")
    case: Mapped[HandoverCase] = relationship("HandoverCase", back_populates="versions")
    sections: Mapped[list[HandoverPackageSection]] = relationship(
        "HandoverPackageSection",
        back_populates="version",
        cascade="all, delete-orphan",
        order_by="HandoverPackageSection.section_order.asc()",
    )
    readiness_assessments: Mapped[list[HandoverReadinessAssessment]] = relationship(
        "HandoverReadinessAssessment",
        back_populates="version",
        cascade="all, delete-orphan",
        order_by="HandoverReadinessAssessment.category.asc()",
    )
    signoffs: Mapped[list[HandoverSignoff]] = relationship(
        "HandoverSignoff",
        back_populates="version",
        cascade="all, delete-orphan",
        order_by="HandoverSignoff.signed_at.desc()",
    )
    deliveries: Mapped[list[HandoverDelivery]] = relationship(
        "HandoverDelivery",
        back_populates="version",
        cascade="all, delete-orphan",
        order_by="HandoverDelivery.delivered_at.desc()",
    )
    assembled_by_user: Mapped[Any] = relationship("User", foreign_keys=[assembled_by_user_id])


class HandoverPackageSection(Base):
    """Domain-specific structured narrative section within a package version."""

    __tablename__ = "handover_package_sections"
    __table_args__ = (
        UniqueConstraint("version_id", "section_type", name="uq_hps_version_section_type"),
        Index("ix_hps_version_order", "version_id", "section_order"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    organisation_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("organisations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    project_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True
    )
    version_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("handover_package_versions.id", ondelete="CASCADE"), nullable=False, index=True
    )

    section_type: Mapped[str] = mapped_column(String(64), nullable=False)
    section_title: Mapped[str] = mapped_column(String(255), nullable=False)
    section_content: Mapped[str] = mapped_column(Text, nullable=False)
    content_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    section_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    knowledge_item_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    relationship_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    metadata_json: Mapped[dict[str, Any]] = mapped_column(
        _JSON_VARIANT, default=dict, nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Relationships
    version: Mapped[HandoverPackageVersion] = relationship(
        "HandoverPackageVersion", back_populates="sections"
    )
    content_links: Mapped[list[HandoverContentLink]] = relationship(
        "HandoverContentLink",
        back_populates="section",
        cascade="all, delete-orphan",
        order_by="HandoverContentLink.created_at.asc()",
    )


class HandoverContentLink(Base):
    """Direct provenance link between a section and supporting knowledge/relationships/evidence."""

    __tablename__ = "handover_content_links"
    __table_args__ = (
        Index("ix_hcl_section_type", "section_id", "link_type"),
        Index("ix_hcl_version_type", "version_id", "link_type"),
        Index("ix_hcl_knowledge_item", "knowledge_item_id"),
        Index("ix_hcl_relationship", "relationship_id"),
        Index("ix_hcl_evidence", "evidence_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    organisation_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("organisations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    project_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True
    )
    section_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("handover_package_sections.id", ondelete="CASCADE"), nullable=False, index=True
    )
    version_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("handover_package_versions.id", ondelete="CASCADE"), nullable=False, index=True
    )

    link_type: Mapped[str] = mapped_column(String(32), nullable=False)
    knowledge_item_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("knowledge_items.id", ondelete="SET NULL"), nullable=True, index=True
    )
    relationship_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("knowledge_relationships.id", ondelete="SET NULL"), nullable=True, index=True
    )
    evidence_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("evidence_items.id", ondelete="SET NULL"), nullable=True, index=True
    )

    eligibility_status_json: Mapped[dict[str, Any]] = mapped_column(
        _JSON_VARIANT, default=dict, nullable=False
    )
    relevance_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Relationships
    section: Mapped[HandoverPackageSection] = relationship(
        "HandoverPackageSection", back_populates="content_links"
    )
    knowledge_item: Mapped[Any] = relationship("KnowledgeItem", foreign_keys=[knowledge_item_id])
    relationship_entity: Mapped[Any] = relationship(
        "KnowledgeRelationship", foreign_keys=[relationship_id]
    )
    evidence_item: Mapped[Any] = relationship("EvidenceItem", foreign_keys=[evidence_id])


class HandoverReadinessAssessment(Base):
    """Granular readiness evaluation scores across 9 dimensions for a package version."""

    __tablename__ = "handover_readiness_assessments"
    __table_args__ = (
        Index("ix_hra_version_cat", "version_id", "category"),
        Index("ix_hra_case_cat", "case_id", "category"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    organisation_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("organisations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    project_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True
    )
    case_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("handover_cases.id", ondelete="CASCADE"), nullable=False, index=True
    )
    version_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("handover_package_versions.id", ondelete="CASCADE"), nullable=False, index=True
    )

    category: Mapped[str] = mapped_column(String(64), nullable=False)
    score: Mapped[int] = mapped_column(Integer, nullable=False)
    level: Mapped[str] = mapped_column(String(32), nullable=False)

    blockers_json: Mapped[list[Any]] = mapped_column(_JSON_VARIANT, default=list, nullable=False)
    warnings_json: Mapped[list[Any]] = mapped_column(_JSON_VARIANT, default=list, nullable=False)
    details_json: Mapped[dict[str, Any]] = mapped_column(_JSON_VARIANT, default=dict, nullable=False)

    assessed_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    assessed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Relationships
    version: Mapped[HandoverPackageVersion] = relationship(
        "HandoverPackageVersion", back_populates="readiness_assessments"
    )
    assessed_by_user: Mapped[Any] = relationship("User", foreign_keys=[assessed_by_user_id])


class HandoverChecklist(Base):
    """Dynamic transition checklist generated for a handover case and version."""

    __tablename__ = "handover_checklists"
    __table_args__ = (
        Index("ix_hcl_case_type", "case_id", "checklist_type"),
        Index("ix_hcl_project_case", "project_id", "case_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    organisation_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("organisations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    project_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True
    )
    case_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("handover_cases.id", ondelete="CASCADE"), nullable=False, index=True
    )
    version_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("handover_package_versions.id", ondelete="SET NULL"), nullable=True, index=True
    )

    checklist_type: Mapped[str] = mapped_column(
        String(32), default=HandoverChecklistType.PRE_HANDOVER.value, nullable=False
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    total_items: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    completed_items: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    is_completed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    # Relationships
    case: Mapped[HandoverCase] = relationship("HandoverCase", back_populates="checklists")
    items: Mapped[list[HandoverChecklistItem]] = relationship(
        "HandoverChecklistItem",
        back_populates="checklist",
        cascade="all, delete-orphan",
        order_by="HandoverChecklistItem.sort_order.asc()",
    )


class HandoverChecklistItem(Base):
    """Specific actionable item in a handover checklist."""

    __tablename__ = "handover_checklist_items"
    __table_args__ = (
        Index("ix_hcli_checklist_status", "checklist_id", "status"),
        Index("ix_hcli_checklist_order", "checklist_id", "sort_order"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    organisation_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("organisations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    project_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True
    )
    checklist_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("handover_checklists.id", ondelete="CASCADE"), nullable=False, index=True
    )

    item_text: Mapped[str] = mapped_column(Text, nullable=False)
    category: Mapped[str] = mapped_column(String(64), default="general", nullable=False)
    status: Mapped[str] = mapped_column(
        String(32), default=ChecklistItemStatus.PENDING.value, nullable=False
    )
    assigned_to_user_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    completed_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    blocking: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    # Relationships
    checklist: Mapped[HandoverChecklist] = relationship(
        "HandoverChecklist", back_populates="items"
    )
    assigned_to_user: Mapped[Any] = relationship("User", foreign_keys=[assigned_to_user_id])
    completed_by_user: Mapped[Any] = relationship("User", foreign_keys=[completed_by_user_id])


class HandoverResponsibilityTransfer(Base):
    """Explicit mapping transferring task/system ownership from departing to successor."""

    __tablename__ = "handover_responsibility_transfers"
    __table_args__ = (
        Index("ix_hrt_case_status", "case_id", "transfer_status"),
        Index("ix_hrt_owner", "current_owner_id"),
        Index("ix_hrt_successor", "proposed_successor_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    organisation_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("organisations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    project_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True
    )
    case_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("handover_cases.id", ondelete="CASCADE"), nullable=False, index=True
    )
    version_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("handover_package_versions.id", ondelete="SET NULL"), nullable=True, index=True
    )

    responsibility_description: Mapped[str] = mapped_column(Text, nullable=False)
    knowledge_domain: Mapped[str] = mapped_column(
        String(64), default="responsibilities_ownership", nullable=False
    )
    current_owner_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    proposed_successor_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    transfer_status: Mapped[str] = mapped_column(
        String(32), default=TransferStatus.PENDING.value, nullable=False
    )
    transfer_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    related_entity_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("knowledge_entities.id", ondelete="SET NULL"), nullable=True, index=True
    )
    transferred_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    # Relationships
    case: Mapped[HandoverCase] = relationship(
        "HandoverCase", back_populates="responsibility_transfers"
    )
    current_owner: Mapped[Any] = relationship("User", foreign_keys=[current_owner_id])
    proposed_successor: Mapped[Any] = relationship("User", foreign_keys=[proposed_successor_id])
    related_entity: Mapped[Any] = relationship("KnowledgeEntity", foreign_keys=[related_entity_id])


class HandoverSignoff(Base):
    """Immutable audit record of a human sign-off on a specific package version."""

    __tablename__ = "handover_signoffs"
    __table_args__ = (
        Index("ix_hs_case_version_type", "case_id", "version_id", "signoff_type"),
        Index("ix_hs_signer", "signer_user_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    organisation_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("organisations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    project_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True
    )
    case_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("handover_cases.id", ondelete="CASCADE"), nullable=False, index=True
    )
    version_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("handover_package_versions.id", ondelete="CASCADE"), nullable=False, index=True
    )

    signoff_type: Mapped[str] = mapped_column(String(32), nullable=False)
    signer_user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    decision: Mapped[str] = mapped_column(String(32), nullable=False)
    comments: Mapped[str | None] = mapped_column(Text, nullable=True)
    conditions: Mapped[str | None] = mapped_column(Text, nullable=True)
    signed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    signature_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Relationships
    case: Mapped[HandoverCase] = relationship("HandoverCase", back_populates="signoffs")
    version: Mapped[HandoverPackageVersion] = relationship(
        "HandoverPackageVersion", back_populates="signoffs"
    )
    signer_user: Mapped[Any] = relationship("User", foreign_keys=[signer_user_id])


class HandoverDelivery(Base):
    """Secure package release and delivery tracking record."""

    __tablename__ = "handover_deliveries"
    __table_args__ = (
        Index("ix_hd_version_user", "version_id", "delivered_to_user_id"),
        Index("ix_hd_case_user", "case_id", "delivered_to_user_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    organisation_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("organisations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    project_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True
    )
    case_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("handover_cases.id", ondelete="CASCADE"), nullable=False, index=True
    )
    version_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("handover_package_versions.id", ondelete="CASCADE"), nullable=False, index=True
    )

    delivered_to_user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    delivered_by_user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    delivery_method: Mapped[str] = mapped_column(
        String(32), default=HandoverDeliveryMethod.INTERNAL_DOWNLOAD.value, nullable=False
    )
    artifact_storage_path: Mapped[str | None] = mapped_column(String(512), nullable=True)
    artifact_checksum: Mapped[str | None] = mapped_column(String(64), nullable=True)
    delivered_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Relationships
    version: Mapped[HandoverPackageVersion] = relationship(
        "HandoverPackageVersion", back_populates="deliveries"
    )
    acknowledgements: Mapped[list[HandoverAcknowledgement]] = relationship(
        "HandoverAcknowledgement",
        back_populates="delivery",
        cascade="all, delete-orphan",
    )
    delivered_to_user: Mapped[Any] = relationship("User", foreign_keys=[delivered_to_user_id])
    delivered_by_user: Mapped[Any] = relationship("User", foreign_keys=[delivered_by_user_id])


class HandoverAcknowledgement(Base):
    """Successor acknowledgement confirming receipt, review, and understanding."""

    __tablename__ = "handover_acknowledgements"
    __table_args__ = (
        Index("ix_ha_delivery", "delivery_id"),
        Index("ix_ha_case_user", "case_id", "acknowledged_by_user_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    organisation_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("organisations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    project_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True
    )
    delivery_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("handover_deliveries.id", ondelete="CASCADE"), nullable=False, index=True
    )
    case_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("handover_cases.id", ondelete="CASCADE"), nullable=False, index=True
    )
    version_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("handover_package_versions.id", ondelete="CASCADE"), nullable=False, index=True
    )

    acknowledged_by_user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    acknowledged_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    acknowledgement_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    confirmations_json: Mapped[dict[str, Any]] = mapped_column(
        _JSON_VARIANT, default=dict, nullable=False
    )
    acknowledgement_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Relationships
    delivery: Mapped[HandoverDelivery] = relationship(
        "HandoverDelivery", back_populates="acknowledgements"
    )
    acknowledged_by_user: Mapped[Any] = relationship(
        "User", foreign_keys=[acknowledged_by_user_id]
    )


class HandoverStatusHistory(Base):
    """Immutable transition audit log tracking handover case lifecycle progression."""

    __tablename__ = "handover_status_histories"
    __table_args__ = (
        Index("ix_hsh_case_time", "case_id", "changed_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    organisation_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("organisations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    project_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True
    )
    case_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("handover_cases.id", ondelete="CASCADE"), nullable=False, index=True
    )

    previous_status: Mapped[str] = mapped_column(String(32), nullable=False)
    new_status: Mapped[str] = mapped_column(String(32), nullable=False)
    changed_by_user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    change_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    changed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    metadata_json: Mapped[dict[str, Any]] = mapped_column(
        _JSON_VARIANT, default=dict, nullable=False
    )

    # Relationships
    case: Mapped[HandoverCase] = relationship("HandoverCase", back_populates="status_history")
    changed_by_user: Mapped[Any] = relationship("User", foreign_keys=[changed_by_user_id])


class HandoverOwnershipTransfer(Base):
    """Explicit, auditable project or component ownership transfer event."""

    __tablename__ = "handover_ownership_transfers"
    __table_args__ = (
        Index("ix_hot_case_type", "case_id", "transfer_type"),
        Index("ix_hot_from_user", "from_user_id"),
        Index("ix_hot_to_user", "to_user_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    organisation_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("organisations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    project_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True
    )
    case_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("handover_cases.id", ondelete="CASCADE"), nullable=False, index=True
    )
    version_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("handover_package_versions.id", ondelete="CASCADE"), nullable=False, index=True
    )

    transfer_type: Mapped[str] = mapped_column(
        String(32), default=OwnershipTransferType.PROJECT_OWNERSHIP.value, nullable=False
    )
    from_user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    to_user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    entity_type: Mapped[str | None] = mapped_column(String(32), nullable=True)
    entity_id: Mapped[uuid.UUID | None] = mapped_column(nullable=True)

    transfer_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    executed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    executed_by_user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )

    rolled_back: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    rollback_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    rolled_back_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    rolled_back_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Relationships
    case: Mapped[HandoverCase] = relationship(
        "HandoverCase", back_populates="ownership_transfers"
    )
    from_user: Mapped[Any] = relationship("User", foreign_keys=[from_user_id])
    to_user: Mapped[Any] = relationship("User", foreign_keys=[to_user_id])
    executed_by_user: Mapped[Any] = relationship("User", foreign_keys=[executed_by_user_id])
    rolled_back_by_user: Mapped[Any] = relationship("User", foreign_keys=[rolled_back_by_user_id])
