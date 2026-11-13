"""Pydantic v2 schemas for Phase 2.6 knowledge extraction candidates, provenance & APIs."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Literal

from pydantic import Field, field_validator, model_validator

from app.models.enums import (
    ConfidenceLevel,
    EpistemicStatus,
    ExtractionRunStatus,
    KnowledgeCategory,
    KnowledgeReviewStatus,
    SupportClassification,
)
from app.schemas.common import BaseSchema
from app.schemas.evidence import BackgroundJobResponse

# ==============================================================================
# Candidate Schemas Produced by Structured LLM Output (Before Backend Verification)
# ==============================================================================

DecisionCategoryLiteral = Literal[
    "architectural",
    "product",
    "process",
    "infrastructure",
    "security",
    "operational",
    "unknown",
]
DecisionStatusLiteral = Literal["proposed", "accepted", "rejected", "superseded", "unclear"]

WorkCategoryLiteral = Literal[
    "feature",
    "bug_fix",
    "refactoring",
    "infrastructure",
    "documentation",
    "testing",
    "deployment",
    "research",
    "maintenance",
]
WorkStatusLiteral = Literal[
    "proposed",
    "open",
    "in_progress",
    "completed",
    "blocked",
    "cancelled",
    "unknown",
]

PersonIdentifierTypeLiteral = Literal[
    "display_name",
    "username",
    "email",
    "account_id",
    "role_label",
    "unknown",
]
OwnershipBasisLiteral = Literal[
    "explicitly_assigned",
    "self_reported",
    "inferred_contribution",
    "historical",
    "unconfirmed",
]
OwnershipStatusLiteral = Literal["active", "historical", "transitioning", "unconfirmed"]

TechnicalCategoryLiteral = Literal[
    "architecture",
    "api_behaviour",
    "database_design",
    "component_interaction",
    "technology_choice",
    "configuration",
    "integration",
    "deployment",
    "constraint_or_limitation",
    "convention",
    "operational_procedure",
    "other",
]
TechnicalStatusLiteral = Literal["active", "deprecated", "planned", "uncertain"]

RiskCategoryLiteral = Literal[
    "bug",
    "blocker",
    "technical_risk",
    "operational_risk",
    "security_concern",
    "external_dependency",
    "incomplete_work",
    "known_limitation",
]
RiskSeverityLiteral = Literal["critical", "high", "medium", "low", "unspecified"]
RiskStatusLiteral = Literal["open", "mitigated", "resolved", "blocked", "unclear"]

DependencyTypeLiteral = Literal[
    "technical_service",
    "library_or_api",
    "task_sequence",
    "person_or_team",
    "external_system",
    "configuration_or_infra",
]
DependencyDirectionLiteral = Literal[
    "depends_on",
    "blocks",
    "required_by",
    "integrates_with",
    "unclear",
]
DependencyStatusLiteral = Literal["active", "resolved", "blocked", "proposed", "unclear"]

ProjectOverviewCategoryLiteral = Literal[
    "purpose_mission",
    "core_objectives",
    "problem_statement",
    "scope_boundary",
    "stakeholder_ecosystem",
    "target_audience",
    "success_criteria",
    "constraints",
    "terminology",
    "other",
]
ProjectOverviewStatusLiteral = Literal["current", "legacy", "superseded", "proposed", "unknown"]

OperationalKnowledgeTypeLiteral = Literal[
    "deployment_runbook",
    "incident_response",
    "troubleshooting_guide",
    "backup_restore",
    "migration_procedure",
    "monitoring_alerting",
    "historical_context",
    "key_event_chronology",
    "legacy_decision_history",
    "other",
]
OperationalStatusLiteral = Literal["active", "superseded", "deprecated", "draft", "unknown"]


def _clean_optional_text(value: str | None) -> str | None:
    if value is None:
        return None
    stripped = value.strip()
    if not stripped or stripped.lower() in {"none", "null", "n/a", "na"}:
        return None
    return stripped


def _clean_string_list(values: list[str] | None) -> list[str]:
    if not values:
        return []
    cleaned: list[str] = []
    seen: set[str] = set()
    for item in values:
        val = item.strip()
        if not val or val in seen:
            continue
        seen.add(val)
        cleaned.append(val)
    return cleaned


class CandidateEvidenceRef(BaseSchema):
    """Citation reference asserted by the LLM linking back to a supplied EvidenceChunk."""

    chunk_id: str = Field(min_length=1, max_length=64)
    supporting_excerpt: str = Field(min_length=8, max_length=1200)
    support_type: Literal[
        "direct",
        "direct_support",
        "corroborated",
        "corroboration",
        "interpretation",
        "context",
        "uncertain",
        "contradiction",
    ] = "direct"

    @field_validator("chunk_id", "supporting_excerpt", mode="before")
    @classmethod
    def _strip_strings(cls, value: Any) -> str:
        return str(value or "").strip()


class ConfidenceMetadata(BaseSchema):
    """Explicit non-calibrated confidence & completeness structure."""

    extraction_confidence: ConfidenceLevel = ConfidenceLevel.MEDIUM
    evidence_support_quality: Literal["explicit", "partial", "weak_or_indirect"] = "explicit"
    information_completeness: Literal["complete", "partial", "incomplete"] = "partial"
    attribution_certainty: Literal["explicit", "inferred", "missing"] = "explicit"
    temporal_certainty: Literal["exact_date", "relative_or_partial", "missing"] = "missing"
    missing_fields: list[str] = Field(default_factory=list)
    conflict_or_ambiguity_flag: bool = False


class _BaseCandidateItem(BaseSchema):
    """Common grounded candidate fields shared across all six Phase 2.6 categories."""

    title: str = Field(min_length=3, max_length=500)
    description: str = Field(min_length=5, max_length=4000)
    is_interpretation: bool = False
    is_uncertain: bool = False
    uncertainty_reason: str | None = Field(default=None, max_length=1000)
    confidence_level: ConfidenceLevel = ConfidenceLevel.MEDIUM
    evidence_refs: list[CandidateEvidenceRef] = Field(min_length=1, max_length=8)

    @field_validator("title", "description", mode="before")
    @classmethod
    def _strip_required(cls, value: Any) -> str:
        return str(value or "").strip()

    @field_validator("uncertainty_reason", mode="before")
    @classmethod
    def _clean_uncertainty(cls, value: Any) -> str | None:
        return _clean_optional_text(None if value is None else str(value))


class DecisionCandidate(_BaseCandidateItem):
    """Structured candidate for Category 1: Decisions & Rationale."""

    decision_category: DecisionCategoryLiteral = "unknown"
    decision_maker: str | None = Field(default=None, max_length=255)
    decision_date: str | None = Field(default=None, max_length=100)
    rationale: str | None = Field(default=None, max_length=2000)
    alternatives_considered: list[str] = Field(default_factory=list)
    chosen_approach: str | None = Field(default=None, max_length=2000)
    consequences_or_tradeoffs: list[str] = Field(default_factory=list)
    affected_components: list[str] = Field(default_factory=list)
    decision_status: DecisionStatusLiteral = "unclear"

    @field_validator(
        "decision_maker",
        "decision_date",
        "rationale",
        "chosen_approach",
        mode="before",
    )
    @classmethod
    def _clean_opt(cls, value: Any) -> str | None:
        return _clean_optional_text(None if value is None else str(value))

    @field_validator(
        "alternatives_considered",
        "consequences_or_tradeoffs",
        "affected_components",
        mode="before",
    )
    @classmethod
    def _clean_lists(cls, value: Any) -> list[str]:
        return _clean_string_list(list(value) if isinstance(value, (list, tuple)) else None)


class WorkItemCandidate(_BaseCandidateItem):
    """Structured candidate for Category 2: Completed & Unfinished Work."""

    work_category: WorkCategoryLiteral = "feature"
    work_status: WorkStatusLiteral = "unknown"
    assignee: str | None = Field(default=None, max_length=255)
    creator: str | None = Field(default=None, max_length=255)
    created_date: str | None = Field(default=None, max_length=100)
    updated_date: str | None = Field(default=None, max_length=100)
    completed_date: str | None = Field(default=None, max_length=100)
    related_references: list[str] = Field(default_factory=list)
    blocker_description: str | None = Field(default=None, max_length=1000)

    @field_validator(
        "assignee",
        "creator",
        "created_date",
        "updated_date",
        "completed_date",
        "blocker_description",
        mode="before",
    )
    @classmethod
    def _clean_opt(cls, value: Any) -> str | None:
        return _clean_optional_text(None if value is None else str(value))

    @field_validator("related_references", mode="before")
    @classmethod
    def _clean_refs(cls, value: Any) -> list[str]:
        return _clean_string_list(list(value) if isinstance(value, (list, tuple)) else None)


class ResponsibilityCandidate(_BaseCandidateItem):
    """Structured candidate for Category 3: Responsibilities & Ownership (no identity merging)."""

    person_identity: str = Field(min_length=1, max_length=255)
    person_identifier_type: PersonIdentifierTypeLiteral = "unknown"
    component_or_workstream: str = Field(min_length=1, max_length=255)
    ownership_role: str = Field(default="contributor", min_length=1, max_length=255)
    ownership_basis: OwnershipBasisLiteral = "unconfirmed"
    start_or_observed_date: str | None = Field(default=None, max_length=100)
    end_date: str | None = Field(default=None, max_length=100)
    ownership_status: OwnershipStatusLiteral = "unconfirmed"

    @field_validator(
        "person_identity",
        "component_or_workstream",
        "ownership_role",
        mode="before",
    )
    @classmethod
    def _strip_req(cls, value: Any) -> str:
        return str(value or "").strip()

    @field_validator("start_or_observed_date", "end_date", mode="before")
    @classmethod
    def _clean_opt(cls, value: Any) -> str | None:
        return _clean_optional_text(None if value is None else str(value))


class TechnicalKnowledgeCandidate(_BaseCandidateItem):
    """Structured candidate for Category 4: Technical & Architectural Knowledge."""

    technical_category: TechnicalCategoryLiteral = "other"
    exact_identifiers: list[str] = Field(default_factory=list)
    components: list[str] = Field(default_factory=list)
    constraints_or_limitations: list[str] = Field(default_factory=list)
    operational_notes: str | None = Field(default=None, max_length=2000)
    technical_status: TechnicalStatusLiteral = "active"

    @field_validator("operational_notes", mode="before")
    @classmethod
    def _clean_opt(cls, value: Any) -> str | None:
        return _clean_optional_text(None if value is None else str(value))

    @field_validator("exact_identifiers", "components", "constraints_or_limitations", mode="before")
    @classmethod
    def _clean_lists(cls, value: Any) -> list[str]:
        return _clean_string_list(list(value) if isinstance(value, (list, tuple)) else None)


class RiskBlockerCandidate(_BaseCandidateItem):
    """Structured candidate for Category 5: Bugs, Blockers & Risks."""

    risk_category: RiskCategoryLiteral = "technical_risk"
    severity: RiskSeverityLiteral = "unspecified"
    risk_status: RiskStatusLiteral = "unclear"
    affected_component: str | None = Field(default=None, max_length=255)
    reported_date: str | None = Field(default=None, max_length=100)
    responsible_person: str | None = Field(default=None, max_length=255)
    resolution_or_mitigation_info: str | None = Field(default=None, max_length=2000)

    @field_validator(
        "affected_component",
        "reported_date",
        "responsible_person",
        "resolution_or_mitigation_info",
        mode="before",
    )
    @classmethod
    def _clean_opt(cls, value: Any) -> str | None:
        return _clean_optional_text(None if value is None else str(value))


class DependencyCandidate(_BaseCandidateItem):
    """Structured candidate for Category 6: Dependencies."""

    source_item: str = Field(min_length=1, max_length=255)
    target_item: str = Field(min_length=1, max_length=255)
    dependency_type: DependencyTypeLiteral = "technical_service"
    direction: DependencyDirectionLiteral = "depends_on"
    context: str | None = Field(default=None, max_length=2000)
    dependency_status: DependencyStatusLiteral = "unclear"

    @field_validator("source_item", "target_item", mode="before")
    @classmethod
    def _strip_req(cls, value: Any) -> str:
        return str(value or "").strip()

    @field_validator("context", mode="before")
    @classmethod
    def _clean_opt(cls, value: Any) -> str | None:
        return _clean_optional_text(None if value is None else str(value))


class ProjectOverviewCandidate(_BaseCandidateItem):
    """Structured candidate for Domain 1: Project Overview & Context."""

    overview_category: ProjectOverviewCategoryLiteral = "purpose_mission"
    problem_statement: str | None = Field(default=None, max_length=2000)
    objectives: list[str] = Field(default_factory=list)
    in_scope: list[str] = Field(default_factory=list)
    out_of_scope: list[str] = Field(default_factory=list)
    key_stakeholders: list[str] = Field(default_factory=list)
    target_users: list[str] = Field(default_factory=list)
    success_criteria: list[str] = Field(default_factory=list)
    constraints: list[str] = Field(default_factory=list)
    glossary_terms: list[str] = Field(default_factory=list)
    status: ProjectOverviewStatusLiteral = "current"

    @field_validator("problem_statement", mode="before")
    @classmethod
    def _clean_opt(cls, value: Any) -> str | None:
        return _clean_optional_text(None if value is None else str(value))

    @field_validator(
        "objectives",
        "in_scope",
        "out_of_scope",
        "key_stakeholders",
        "target_users",
        "success_criteria",
        "constraints",
        "glossary_terms",
        mode="before",
    )
    @classmethod
    def _clean_lists(cls, value: Any) -> list[str]:
        return _clean_string_list(list(value) if isinstance(value, (list, tuple)) else None)


class OperationalHistoricalCandidate(_BaseCandidateItem):
    """Structured candidate for Domain 8: Operational & Historical Context."""

    knowledge_type: OperationalKnowledgeTypeLiteral = "historical_context"
    procedure_name: str | None = Field(default=None, max_length=255)
    target_environment: str | None = Field(default=None, max_length=100)
    prerequisites: list[str] = Field(default_factory=list)
    execution_steps: list[str] = Field(default_factory=list)
    verification_steps: list[str] = Field(default_factory=list)
    rollback_steps: list[str] = Field(default_factory=list)
    event_timestamp: str | None = Field(default=None, max_length=100)
    historical_significance: str | None = Field(default=None, max_length=2000)
    lessons_learned: list[str] = Field(default_factory=list)
    superseded_reason: str | None = Field(default=None, max_length=1000)
    status: OperationalStatusLiteral = "active"

    @field_validator(
        "procedure_name",
        "target_environment",
        "event_timestamp",
        "historical_significance",
        "superseded_reason",
        mode="before",
    )
    @classmethod
    def _clean_opt(cls, value: Any) -> str | None:
        return _clean_optional_text(None if value is None else str(value))

    @field_validator(
        "prerequisites",
        "execution_steps",
        "verification_steps",
        "rollback_steps",
        "lessons_learned",
        mode="before",
    )
    @classmethod
    def _clean_lists(cls, value: Any) -> list[str]:
        return _clean_string_list(list(value) if isinstance(value, (list, tuple)) else None)


# ==============================================================================
# API Request & Response Schemas
# ==============================================================================


class EvidenceExtractRequest(BaseSchema):
    """Request payload for triggering knowledge extraction on one evidence item."""

    categories: list[KnowledgeCategory] | None = Field(default=None, min_length=1, max_length=16)
    force_rerun: bool = False


class ProjectKnowledgeExtractRequest(BaseSchema):
    """Request payload for triggering project-wide or multi-evidence extraction."""

    evidence_ids: list[uuid.UUID] | None = Field(default=None, min_length=1, max_length=100)
    categories: list[KnowledgeCategory] | None = Field(default=None, min_length=1, max_length=16)
    force_rerun: bool = False
    include_synthetic: bool = False


class KnowledgeExtractionRunResponse(BaseSchema):
    """Public status and telemetry summary of a Phase 2.6 knowledge extraction run."""

    id: uuid.UUID
    organisation_id: uuid.UUID
    project_id: uuid.UUID
    background_job_id: uuid.UUID | None
    evidence_id: uuid.UUID | None
    triggered_by_user_id: uuid.UUID | None
    scope_type: str
    target_categories: list[str]
    model_name: str
    prompt_version: str
    status: ExtractionRunStatus
    is_synthetic: bool

    total_evidence_items: int
    processed_evidence_items: int
    failed_evidence_items: int
    skipped_evidence_items: int
    total_chunks_evaluated: int
    batches_executed: int
    candidates_generated: int
    claims_persisted: int
    claims_rejected_ungrounded: int
    duplicates_merged: int
    prompt_tokens: int
    completion_tokens: int

    warnings: list[str]
    error_code: str | None
    error_message: str | None
    started_at: datetime | None
    completed_at: datetime | None
    duration_ms: int | None
    created_at: datetime
    updated_at: datetime
    job: BackgroundJobResponse | None = None


class KnowledgeExtractionRunListResponse(BaseSchema):
    """Paginated list of extraction runs scoped to an authorised project."""

    items: list[KnowledgeExtractionRunResponse]
    total: int
    limit: int
    offset: int


class ExtractionTriggerResponse(BaseSchema):
    """Accepted response returned when queueing or reusing an active extraction run."""

    run: KnowledgeExtractionRunResponse
    job: BackgroundJobResponse | None
    already_active: bool = False
    skipped_inaccessible_count: int = 0


class KnowledgeEvidenceLinkResponse(BaseSchema):
    """Verified provenance link tying a knowledge item back to canonical source evidence."""

    id: uuid.UUID
    evidence_id: uuid.UUID
    evidence_chunk_id: uuid.UUID | None
    support_type: SupportClassification
    source_location: dict[str, Any]
    supporting_excerpt: str
    excerpt_verified: bool
    excerpt_match_mode: str
    source_metadata: dict[str, Any]
    created_at: datetime


class KnowledgeItemSummaryResponse(BaseSchema):
    """Structured knowledge record distinguishing epistemic tier and review status."""

    id: uuid.UUID
    organisation_id: uuid.UUID
    project_id: uuid.UUID
    extraction_run_id: uuid.UUID | None
    category: str
    primary_domain: str | None = None
    secondary_domains: list[str] = Field(default_factory=list)
    epistemic_status: EpistemicStatus
    review_status: KnowledgeReviewStatus
    support_classification: SupportClassification
    title: str
    structured_summary: str
    structured_payload: dict[str, Any]
    normalised_status: str | None
    person_or_owner_label: str | None
    source_attribution: dict[str, Any]
    extraction_model: str
    prompt_version: str
    confidence_metadata: dict[str, Any]
    uncertainty_reason: str | None
    is_stale: bool
    stale_reason: str | None
    stale_detected_at: datetime | None
    superseded_by_id: uuid.UUID | None
    is_synthetic: bool
    source_observed_at: datetime | None
    evidence_links_count: int
    created_at: datetime
    updated_at: datetime


class KnowledgeItemDetailResponse(KnowledgeItemSummaryResponse):
    """Detailed knowledge item including verified supporting evidence links."""

    evidence_links: list[KnowledgeEvidenceLinkResponse] = Field(default_factory=list)


class KnowledgeItemListResponse(BaseSchema):
    """Paginated list of accessible extracted knowledge items for a project."""

    items: list[KnowledgeItemSummaryResponse]
    total: int
    limit: int
    offset: int


class ProjectKnowledgeStatusResponse(BaseSchema):
    """Aggregated Phase 2.6 knowledge reconstruction health & breakdown for one project."""

    project_id: uuid.UUID
    total_accessible_items: int
    stale_items_count: int
    counts_by_category: dict[str, int]
    counts_by_epistemic_status: dict[str, int]
    counts_by_support_classification: dict[str, int]
    active_runs_count: int
    latest_run: KnowledgeExtractionRunResponse | None = None


class KnowledgeItemFilterQuery(BaseSchema):
    """Optional validated date/filter constraints for listing extracted knowledge items."""

    date_from: datetime | None = None
    date_to: datetime | None = None

    @model_validator(mode="after")
    def _validate_dates(self) -> KnowledgeItemFilterQuery:
        if (
            self.date_from is not None
            and self.date_to is not None
            and self.date_from > self.date_to
        ):
            raise ValueError("date_from must not be after date_to.")
        return self
