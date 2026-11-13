"""Pydantic v2 schemas for Handover Workspace APIs.

Platform: The Handover
Module: Handover Workspace (Module 4 / Knowledge Transfer Area)
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


# ---------------------------------------------------------------------------
# Request schemas
# ---------------------------------------------------------------------------


class HandoverCaseCreateRequest(BaseModel):
    """Create a new handover case for a project."""

    title: str = Field(..., min_length=3, max_length=300)
    description: str | None = Field(None, max_length=5000)
    departing_member_id: uuid.UUID
    successor_id: uuid.UUID | None = None
    metadata_json: dict[str, Any] | None = None


class HandoverCaseUpdateRequest(BaseModel):
    """Update mutable fields of a handover case."""

    title: str | None = Field(None, min_length=3, max_length=300)
    description: str | None = Field(None, max_length=5000)
    successor_id: uuid.UUID | None = None
    metadata_json: dict[str, Any] | None = None


class PackageAssemblyRequest(BaseModel):
    """Request assembly of a new package version."""

    assembly_notes: str | None = Field(None, max_length=2000)
    include_domains: list[str] | None = None
    exclude_knowledge_item_ids: list[uuid.UUID] | None = None
    exclude_relationship_ids: list[uuid.UUID] | None = None


class ReadinessAssessmentRequest(BaseModel):
    """Request a readiness assessment for a package version."""

    version_id: uuid.UUID
    notes: str | None = Field(None, max_length=2000)


class ChecklistItemUpdateRequest(BaseModel):
    """Update the status of a checklist item."""

    status: str
    notes: str | None = Field(None, max_length=2000)


class SignoffRequest(BaseModel):
    """Submit a sign-off decision."""

    version_id: uuid.UUID
    signoff_type: str
    decision: str
    comments: str | None = Field(None, max_length=5000)


class DeliveryRequest(BaseModel):
    """Request delivery of a package version."""

    version_id: uuid.UUID
    deliver_to_user_ids: list[uuid.UUID] = Field(..., min_length=1)
    delivery_method: str = "internal_download"
    message: str | None = Field(None, max_length=2000)
    expires_in_days: int | None = Field(None, ge=1, le=365)


class AcknowledgementRequest(BaseModel):
    """Submit successor acknowledgement for a delivery."""

    acknowledgement_notes: str | None = Field(None, max_length=5000)


class ResponsibilityTransferRequest(BaseModel):
    """Define a responsibility transfer mapping."""

    responsibility_description: str = Field(..., min_length=5, max_length=1000)
    knowledge_domain: str | None = None
    proposed_successor_id: uuid.UUID | None = None
    transfer_notes: str | None = Field(None, max_length=2000)


class ResponsibilityTransferBulkRequest(BaseModel):
    """Bulk create responsibility transfer mappings."""

    transfers: list[ResponsibilityTransferRequest] = Field(..., min_length=1)


class OwnershipTransferRequest(BaseModel):
    """Execute an ownership transfer."""

    version_id: uuid.UUID
    transfer_type: str
    to_user_id: uuid.UUID
    entity_type: str | None = None
    entity_id: uuid.UUID | None = None
    transfer_reason: str | None = Field(None, max_length=2000)


class OwnershipTransferRollbackRequest(BaseModel):
    """Rollback a previous ownership transfer."""

    rollback_reason: str = Field(..., min_length=5, max_length=2000)


class NarrativeDraftRequest(BaseModel):
    """Request AI-generated narrative draft for a section."""

    version_id: uuid.UUID
    section_type: str
    additional_context: str | None = Field(None, max_length=2000)


class SectionEditRequest(BaseModel):
    """Edit section content (narrative text only)."""

    section_content: str | None = None
    content_summary: str | None = Field(None, max_length=1000)


# ---------------------------------------------------------------------------
# Response schemas
# ---------------------------------------------------------------------------


class HandoverCaseResponse(BaseModel):
    """Full handover case details."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    organisation_id: uuid.UUID
    project_id: uuid.UUID
    title: str
    description: str | None = None
    status: str
    departing_member_id: uuid.UUID
    successor_id: uuid.UUID | None = None
    created_by_user_id: uuid.UUID
    metadata_json: dict[str, Any] | None = None
    created_at: datetime
    updated_at: datetime


class HandoverCaseListItem(BaseModel):
    """Compact handover case summary for listing."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    title: str
    status: str
    departing_member_id: uuid.UUID
    successor_id: uuid.UUID | None = None
    created_at: datetime
    updated_at: datetime


class HandoverPackageResponse(BaseModel):
    """Package metadata."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    case_id: uuid.UUID
    created_by_user_id: uuid.UUID
    created_at: datetime
    updated_at: datetime


class HandoverPackageVersionResponse(BaseModel):
    """Immutable package version snapshot."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    package_id: uuid.UUID
    version_number: int
    assembly_notes: str | None = None
    assembly_snapshot_json: dict[str, Any] | None = None
    assembled_by_user_id: uuid.UUID | None = None
    assembled_at: datetime | None = None
    is_current: bool = False
    created_at: datetime


class HandoverSectionResponse(BaseModel):
    """Per-domain section content."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    version_id: uuid.UUID
    section_type: str
    section_title: str
    section_content: str | None = None
    content_summary: str | None = None
    section_order: int
    knowledge_item_count: int = 0
    relationship_count: int = 0
    created_at: datetime
    updated_at: datetime


class HandoverContentLinkResponse(BaseModel):
    """Link between section content and knowledge/evidence."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    section_id: uuid.UUID
    knowledge_item_id: uuid.UUID | None = None
    relationship_id: uuid.UUID | None = None
    evidence_id: uuid.UUID | None = None
    link_type: str
    eligibility_status_json: dict[str, Any] | None = None
    created_at: datetime


class HandoverReadinessAssessmentResponse(BaseModel):
    """Readiness assessment for a category."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    version_id: uuid.UUID
    category: str
    score: int
    level: str
    blockers_json: list[str] = Field(default_factory=list)
    warnings_json: list[str] = Field(default_factory=list)
    assessed_by_user_id: uuid.UUID | None = None
    assessed_at: datetime
    created_at: datetime


class HandoverReadinessSummaryResponse(BaseModel):
    """Aggregated readiness summary across all categories."""

    version_id: uuid.UUID
    overall_score: int
    overall_level: str
    categories: list[HandoverReadinessAssessmentResponse]
    is_ready_for_signoff: bool
    blocker_count: int
    warning_count: int


class HandoverChecklistItemResponse(BaseModel):
    """Individual checklist item."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    checklist_id: uuid.UUID
    item_text: str
    status: str
    category: str | None = None
    assigned_to_user_id: uuid.UUID | None = None
    completed_by_user_id: uuid.UUID | None = None
    completed_at: datetime | None = None
    created_at: datetime
    updated_at: datetime


class HandoverChecklistResponse(BaseModel):
    """Checklist container."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    case_id: uuid.UUID
    generated_for_version_id: uuid.UUID | None = None
    checklist_type: str
    created_at: datetime
    items: list[HandoverChecklistItemResponse] = Field(default_factory=list)


class HandoverSignoffResponse(BaseModel):
    """Sign-off record."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    case_id: uuid.UUID
    version_id: uuid.UUID
    signoff_type: str
    signer_user_id: uuid.UUID
    decision: str
    comments: str | None = None
    signed_at: datetime
    created_at: datetime


class HandoverDeliveryResponse(BaseModel):
    """Delivery record."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    version_id: uuid.UUID
    delivered_to_user_id: uuid.UUID
    delivery_method: str
    artifact_storage_path: str | None = None
    message: str | None = None
    delivered_at: datetime
    expires_at: datetime | None = None
    created_at: datetime


class HandoverAcknowledgementResponse(BaseModel):
    """Successor acknowledgement."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    delivery_id: uuid.UUID
    acknowledged_by_user_id: uuid.UUID
    acknowledgement_notes: str | None = None
    acknowledged_at: datetime
    created_at: datetime


class HandoverResponsibilityTransferResponse(BaseModel):
    """Responsibility transfer mapping."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    case_id: uuid.UUID
    version_id: uuid.UUID | None = None
    responsibility_description: str
    current_owner_id: uuid.UUID
    proposed_successor_id: uuid.UUID | None = None
    knowledge_domain: str | None = None
    transfer_status: str
    transfer_notes: str | None = None
    created_at: datetime
    updated_at: datetime


class HandoverStatusHistoryResponse(BaseModel):
    """Immutable status transition record."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    case_id: uuid.UUID
    previous_status: str
    new_status: str
    changed_by_user_id: uuid.UUID
    change_reason: str | None = None
    changed_at: datetime


class HandoverOwnershipTransferResponse(BaseModel):
    """Ownership transfer record."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    case_id: uuid.UUID
    version_id: uuid.UUID
    transfer_type: str
    from_user_id: uuid.UUID
    to_user_id: uuid.UUID
    entity_type: str | None = None
    entity_id: uuid.UUID | None = None
    executed_at: datetime
    executed_by_user_id: uuid.UUID
    rolled_back: bool = False
    rollback_reason: str | None = None
    created_at: datetime


class HandoverEligibilityCheckResponse(BaseModel):
    """Eligibility check result for a knowledge item or relationship."""

    target_type: str
    target_id: uuid.UUID
    is_eligible: bool
    case_status: str
    epistemic_status: str
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Paginated response wrapper
# ---------------------------------------------------------------------------


class PaginatedHandoverCaseResponse(BaseModel):
    """Paginated list of handover cases."""

    items: list[HandoverCaseListItem]
    total: int
    page: int
    page_size: int
    total_pages: int


class HandoverCaseDetailResponse(BaseModel):
    """Full handover case with nested package/version/signoff details."""

    case: HandoverCaseResponse
    packages: list[HandoverPackageResponse] = Field(default_factory=list)
    current_version: HandoverPackageVersionResponse | None = None
    signoffs: list[HandoverSignoffResponse] = Field(default_factory=list)
    status_history: list[HandoverStatusHistoryResponse] = Field(default_factory=list)
    responsibility_transfers: list[HandoverResponsibilityTransferResponse] = Field(
        default_factory=list
    )


class HandoverPackageDetailResponse(BaseModel):
    """Full package version with sections and content links."""

    version: HandoverPackageVersionResponse
    sections: list[HandoverSectionResponse] = Field(default_factory=list)
    readiness: HandoverReadinessSummaryResponse | None = None
    checklists: list[HandoverChecklistResponse] = Field(default_factory=list)
