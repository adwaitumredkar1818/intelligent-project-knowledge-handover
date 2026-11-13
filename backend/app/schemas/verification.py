"""Pydantic v2 schemas for Verification Center APIs.

Platform: The Handover
Module: Verification Center (Module 3 / Validation Area)
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class VerificationIssueResponse(BaseModel):
    """Schema for individual verification issues."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    case_id: uuid.UUID
    issue_type: str
    severity: str
    description: str
    detection_method: str
    details_json: dict[str, Any] = Field(default_factory=dict)
    conflicting_evidence_id: uuid.UUID | None = None
    conflicting_chunk_id: uuid.UUID | None = None
    resolution_state: str
    resolution_reason: str | None = None
    resolved_by_user_id: uuid.UUID | None = None
    resolved_at: datetime | None = None
    created_at: datetime


class VerificationConflictResponse(BaseModel):
    """Schema for cross-source contradiction records."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    case_id: uuid.UUID
    conflict_type: str
    claim_a_text: str
    claim_a_source_evidence_id: uuid.UUID
    claim_a_chunk_id: uuid.UUID | None = None
    claim_a_source_timestamp: datetime | None = None
    claim_b_text: str
    claim_b_source_evidence_id: uuid.UUID
    claim_b_chunk_id: uuid.UUID | None = None
    claim_b_source_timestamp: datetime | None = None
    explanation: str
    temporal_comparison: str
    resolution_state: str
    resolution_notes: str | None = None
    created_at: datetime


class VerificationReviewEventResponse(BaseModel):
    """Schema for audit-tracked review actions."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    case_id: uuid.UUID
    reviewer_user_id: uuid.UUID
    action: str
    previous_status: str
    new_status: str
    review_notes: str | None = None
    finding_patch_json: dict[str, Any] | None = None
    correlation_id: str
    created_at: datetime


class VerificationContextRequestResponse(BaseModel):
    """Schema for in-platform clarification requests."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    case_id: uuid.UUID
    requested_by_user_id: uuid.UUID
    requested_from_user_id: uuid.UUID
    question: str
    requested_information_type: str
    status: str
    response_text: str | None = None
    response_evidence_id: uuid.UUID | None = None
    responded_at: datetime | None = None
    created_at: datetime


class VerificationCaseItemResponse(BaseModel):
    """Compact summary schema for queue browsing."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    organisation_id: uuid.UUID
    project_id: uuid.UUID
    target_type: str
    target_id: uuid.UUID
    case_status: str
    machine_assessment_status: str
    priority: str
    assigned_reviewer_id: uuid.UUID | None = None
    machine_assessment_json: dict[str, Any] = Field(default_factory=dict)
    version: int
    open_issues_count: int = 0
    open_conflicts_count: int = 0
    last_assessed_at: datetime | None = None
    last_reviewed_at: datetime | None = None
    resolved_at: datetime | None = None
    created_at: datetime
    updated_at: datetime


class VerificationCaseDetailResponse(BaseModel):
    """Complete detail schema for inspecting and reviewing a case."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    organisation_id: uuid.UUID
    project_id: uuid.UUID
    target_type: str
    target_id: uuid.UUID
    case_status: str
    machine_assessment_status: str
    priority: str
    assigned_reviewer_id: uuid.UUID | None = None
    machine_assessment_json: dict[str, Any] = Field(default_factory=dict)
    version: int
    last_assessed_at: datetime | None = None
    last_reviewed_at: datetime | None = None
    resolved_at: datetime | None = None
    created_at: datetime
    updated_at: datetime

    target_data: dict[str, Any] = Field(default_factory=dict)
    issues: list[VerificationIssueResponse] = Field(default_factory=list)
    conflicts: list[VerificationConflictResponse] = Field(default_factory=list)
    review_events: list[VerificationReviewEventResponse] = Field(default_factory=list)
    context_requests: list[VerificationContextRequestResponse] = Field(default_factory=list)


class VerificationQueueResponse(BaseModel):
    """Paginated list of verification cases in the human review queue."""

    items: list[VerificationCaseItemResponse]
    total: int
    limit: int
    offset: int


class VerificationSummaryResponse(BaseModel):
    """Aggregated project verification metrics."""

    total_cases: int
    by_status: dict[str, int]
    by_priority: dict[str, int]
    open_issues_count: int
    open_conflicts_count: int
    pending_context_requests_count: int


# ==============================================================================
# Action Requests
# ==============================================================================


class ApproveCaseRequest(BaseModel):
    """Request payload to approve a finding or relationship."""

    expected_version: int = Field(ge=1, description="Current optimistic version of the case.")
    review_notes: str | None = Field(default=None, max_length=2000)


class RejectCaseRequest(BaseModel):
    """Request payload to reject a candidate finding or relationship."""

    expected_version: int = Field(ge=1)
    reason: str = Field(min_length=3, max_length=500)
    review_notes: str | None = Field(default=None, max_length=2000)


class EditFindingRequest(BaseModel):
    """Request payload to correct finding details with diff tracking."""

    expected_version: int = Field(ge=1)
    patch_data: dict[str, Any] = Field(
        description="Fields to patch (title, summary, item_payload)."
    )
    reason: str = Field(min_length=3, max_length=500)


class RequestContextRequest(BaseModel):
    """Request payload to ask a clarification question."""

    requested_from_user_id: uuid.UUID
    question: str = Field(min_length=5, max_length=2000)
    requested_information_type: str = Field(default="general", max_length=64)
    expected_version: int | None = None


class MarkUnresolvedRequest(BaseModel):
    """Request payload to mark a case as unresolved."""

    expected_version: int = Field(ge=1)
    explanation: str = Field(min_length=5, max_length=2000)


class AssignReviewerRequest(BaseModel):
    """Request payload to assign or reassign a verification case."""

    expected_version: int = Field(ge=1)
    assignee_user_id: uuid.UUID | None = None


class RespondContextRequest(BaseModel):
    """Request payload to respond to a clarification question."""

    response_text: str = Field(min_length=2, max_length=4000)
    response_evidence_id: uuid.UUID | None = None


class HandoverEligibilityResponse(BaseModel):
    """Downstream eligibility assessment for handover package generation."""

    is_eligible: bool
    target_type: str
    target_id: uuid.UUID
    case_status: str
    epistemic_status: str
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
