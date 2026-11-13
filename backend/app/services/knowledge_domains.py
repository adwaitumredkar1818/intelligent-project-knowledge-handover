"""Canonical domain registry and compatibility mapping for The Handover Knowledge Intelligence."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Any


class KnowledgeDomain(StrEnum):
    """The eight canonical product-level knowledge domains of The Handover."""

    PROJECT_OVERVIEW_CONTEXT = "PROJECT_OVERVIEW_CONTEXT"
    DECISIONS_RATIONALE = "DECISIONS_RATIONALE"
    ARCHITECTURE_TECHNICAL = "ARCHITECTURE_TECHNICAL"
    WORK_PROGRESS = "WORK_PROGRESS"
    RESPONSIBILITIES_OWNERSHIP = "RESPONSIBILITIES_OWNERSHIP"
    DEPENDENCIES_RELATIONSHIPS = "DEPENDENCIES_RELATIONSHIPS"
    RISKS_BLOCKERS_QUESTIONS = "RISKS_BLOCKERS_QUESTIONS"
    OPERATIONAL_HISTORICAL = "OPERATIONAL_HISTORICAL"


@dataclass(frozen=True, slots=True)
class DomainDefinition:
    """Immutable specification for a canonical knowledge domain."""

    domain: KnowledgeDomain
    identifier: str
    display_name: str
    description: str
    supported_finding_types: tuple[str, ...]
    prompt_template_id: str
    prompt_version: str
    version: str = "1.0"
    is_active: bool = True
    display_order: int = 1

    @property
    def code(self) -> int:
        return self.display_order


# Central canonical domain specifications
_DOMAIN_DEFINITIONS: dict[KnowledgeDomain, DomainDefinition] = {
    KnowledgeDomain.PROJECT_OVERVIEW_CONTEXT: DomainDefinition(
        domain=KnowledgeDomain.PROJECT_OVERVIEW_CONTEXT,
        identifier="PROJECT_OVERVIEW_CONTEXT",
        display_name="Project Overview & Context",
        description=(
            "Project charter, core purpose, objectives, problem statements, in/out of scope "
            "boundaries, business context, stakeholders, key milestones, constraints, and "
            "critical project terminology."
        ),
        supported_finding_types=(
            "project_purpose",
            "project_objective",
            "scope_boundary",
            "stakeholder_context",
            "business_context",
            "project_constraint",
            "project_assumption",
            "terminology_definition",
        ),
        prompt_template_id="overview_context_v1",
        prompt_version="ki-v1.0",
        display_order=1,
    ),
    KnowledgeDomain.DECISIONS_RATIONALE: DomainDefinition(
        domain=KnowledgeDomain.DECISIONS_RATIONALE,
        identifier="DECISIONS_RATIONALE",
        display_name="Decisions & Rationale",
        description=(
            "Architectural, technical, product, process, infrastructure, and security choices "
            "made, proposed, rejected, or superseded, with explicit rationale, alternatives, "
            "and trade-offs."
        ),
        supported_finding_types=(
            "architectural_decision",
            "product_decision",
            "process_decision",
            "infrastructure_choice",
            "security_decision",
            "operational_choice",
        ),
        prompt_template_id="decisions_v1",
        prompt_version="ki-v1.0",
        display_order=2,
    ),
    KnowledgeDomain.ARCHITECTURE_TECHNICAL: DomainDefinition(
        domain=KnowledgeDomain.ARCHITECTURE_TECHNICAL,
        identifier="ARCHITECTURE_TECHNICAL",
        display_name="Architecture & Technical Knowledge",
        description=(
            "System architecture, backend/frontend structures, APIs, database designs, "
            "data models, integration patterns, configurations, conventions, workarounds, "
            "and technical debt."
        ),
        supported_finding_types=(
            "system_architecture",
            "api_endpoint",
            "database_design",
            "data_model",
            "configuration_rule",
            "technical_convention",
            "technical_debt",
            "known_limitation",
        ),
        prompt_template_id="technical_knowledge_v1",
        prompt_version="ki-v1.0",
        display_order=3,
    ),
    KnowledgeDomain.WORK_PROGRESS: DomainDefinition(
        domain=KnowledgeDomain.WORK_PROGRESS,
        identifier="WORK_PROGRESS",
        display_name="Work & Progress",
        description=(
            "Completed work, work in progress, pending tasks, blocked items, PRs, commits, "
            "and Jira issues across the development lifecycle."
        ),
        supported_finding_types=(
            "completed_work",
            "work_in_progress",
            "pending_task",
            "blocked_item",
            "pull_request",
            "commit_milestone",
            "cancelled_work",
        ),
        prompt_template_id="work_items_v1",
        prompt_version="ki-v1.0",
        display_order=4,
    ),
    KnowledgeDomain.RESPONSIBILITIES_OWNERSHIP: DomainDefinition(
        domain=KnowledgeDomain.RESPONSIBILITIES_OWNERSHIP,
        identifier="RESPONSIBILITIES_OWNERSHIP",
        display_name="Responsibilities & Ownership",
        description=(
            "Accountability matrix, component ownership, assigned workstreams, reviewers, "
            "escalation contacts, and historical maintainers."
        ),
        supported_finding_types=(
            "component_ownership",
            "duty_assignment",
            "reviewer_responsibility",
            "escalation_contact",
            "historical_owner",
            "transition_participant",
        ),
        prompt_template_id="responsibilities_v1",
        prompt_version="ki-v1.0",
        display_order=5,
    ),
    KnowledgeDomain.DEPENDENCIES_RELATIONSHIPS: DomainDefinition(
        domain=KnowledgeDomain.DEPENDENCIES_RELATIONSHIPS,
        identifier="DEPENDENCIES_RELATIONSHIPS",
        display_name="Dependencies & Relationships",
        description=(
            "Service-to-service dependencies, API dependencies, module linkages, task sequencing, "
            "blocking conditions, and team approval requirements."
        ),
        supported_finding_types=(
            "service_dependency",
            "api_dependency",
            "task_sequence",
            "approval_dependency",
            "external_system_dependency",
            "blocking_relationship",
        ),
        prompt_template_id="dependencies_v1",
        prompt_version="ki-v1.0",
        display_order=6,
    ),
    KnowledgeDomain.RISKS_BLOCKERS_QUESTIONS: DomainDefinition(
        domain=KnowledgeDomain.RISKS_BLOCKERS_QUESTIONS,
        identifier="RISKS_BLOCKERS_QUESTIONS",
        display_name="Risks, Blockers & Open Questions",
        description=(
            "Technical risks, operational risks, delivery hazards, known bugs, active blockers, "
            "unresolved incidents, and unanswered technical questions."
        ),
        supported_finding_types=(
            "technical_risk",
            "operational_risk",
            "delivery_risk",
            "security_concern",
            "active_blocker",
            "software_bug",
            "unanswered_question",
        ),
        prompt_template_id="risks_blockers_v1",
        prompt_version="ki-v1.0",
        display_order=7,
    ),
    KnowledgeDomain.OPERATIONAL_HISTORICAL: DomainDefinition(
        domain=KnowledgeDomain.OPERATIONAL_HISTORICAL,
        identifier="OPERATIONAL_HISTORICAL",
        display_name="Operational & Historical Knowledge",
        description=(
            "Deployment instructions, setup procedures, environment runbooks, "
            "troubleshooting steps, backup/recovery procedures, historical pivots, "
            "superseded designs, and past incidents."
        ),
        supported_finding_types=(
            "deployment_instruction",
            "setup_procedure",
            "troubleshooting_guide",
            "env_configuration",
            "recovery_procedure",
            "historical_event",
            "superseded_approach",
            "historical_incident",
        ),
        prompt_template_id="operational_historical_v1",
        prompt_version="ki-v1.0",
        display_order=8,
    ),
}

# Compatibility mapping between Phase 2.6 legacy categories and Canonical Domains
_LEGACY_CATEGORY_TO_DOMAIN: dict[str, KnowledgeDomain] = {
    "decisions_rationale": KnowledgeDomain.DECISIONS_RATIONALE,
    "work_items": KnowledgeDomain.WORK_PROGRESS,
    "responsibilities_ownership": KnowledgeDomain.RESPONSIBILITIES_OWNERSHIP,
    "technical_architecture": KnowledgeDomain.ARCHITECTURE_TECHNICAL,
    "bugs_blockers_risks": KnowledgeDomain.RISKS_BLOCKERS_QUESTIONS,
    "dependencies": KnowledgeDomain.DEPENDENCIES_RELATIONSHIPS,
    # Direct lowercase mappings of canonical domain names
    "project_overview_context": KnowledgeDomain.PROJECT_OVERVIEW_CONTEXT,
    "operational_historical": KnowledgeDomain.OPERATIONAL_HISTORICAL,
    "work_progress": KnowledgeDomain.WORK_PROGRESS,
    "architecture_technical": KnowledgeDomain.ARCHITECTURE_TECHNICAL,
    "dependencies_relationships": KnowledgeDomain.DEPENDENCIES_RELATIONSHIPS,
    "risks_blockers_questions": KnowledgeDomain.RISKS_BLOCKERS_QUESTIONS,
}

_DOMAIN_TO_LEGACY_CATEGORY: dict[KnowledgeDomain, str] = {
    KnowledgeDomain.DECISIONS_RATIONALE: "decisions_rationale",
    KnowledgeDomain.WORK_PROGRESS: "work_items",
    KnowledgeDomain.RESPONSIBILITIES_OWNERSHIP: "responsibilities_ownership",
    KnowledgeDomain.ARCHITECTURE_TECHNICAL: "technical_architecture",
    KnowledgeDomain.RISKS_BLOCKERS_QUESTIONS: "bugs_blockers_risks",
    KnowledgeDomain.DEPENDENCIES_RELATIONSHIPS: "dependencies",
    KnowledgeDomain.PROJECT_OVERVIEW_CONTEXT: "project_overview_context",
    KnowledgeDomain.OPERATIONAL_HISTORICAL: "operational_historical",
}


def get_domain_definition(domain: KnowledgeDomain | str) -> DomainDefinition:
    """Retrieve the central specification for a knowledge domain."""
    canonical = resolve_canonical_domain(domain)
    return _DOMAIN_DEFINITIONS[canonical]


def list_all_domain_definitions() -> list[DomainDefinition]:
    """Return all 8 canonical domain definitions ordered by display index."""
    return sorted(_DOMAIN_DEFINITIONS.values(), key=lambda d: d.display_order)


def resolve_canonical_domain(value: KnowledgeDomain | str) -> KnowledgeDomain:
    """Robustly resolve any domain or legacy category string to a canonical KnowledgeDomain."""
    if isinstance(value, KnowledgeDomain):
        return value
    raw = str(value or "").strip()
    # Direct match on uppercase name
    try:
        return KnowledgeDomain(raw.upper())
    except ValueError:
        pass
    # Match on lowercase legacy or canonical key
    lowered = raw.lower()
    if lowered in _LEGACY_CATEGORY_TO_DOMAIN:
        return _LEGACY_CATEGORY_TO_DOMAIN[lowered]
    # Fuzzy fallback on normalized key
    clean = lowered.replace("-", "_")
    if clean in _LEGACY_CATEGORY_TO_DOMAIN:
        return _LEGACY_CATEGORY_TO_DOMAIN[clean]
    raise ValueError(f"Unrecognized knowledge domain or category: {value!r}")


def canonical_domain_to_legacy_category(domain: KnowledgeDomain | str) -> str:
    """Map canonical domain to underlying storage category for DB backward compatibility."""
    canonical = resolve_canonical_domain(domain)
    return _DOMAIN_TO_LEGACY_CATEGORY[canonical]


def is_valid_domain(value: str) -> bool:
    """Check whether a string represents a valid canonical domain or legacy category."""
    try:
        resolve_canonical_domain(value)
        return True
    except (ValueError, KeyError):
        return False


# Aliases for interoperability across services
CANONICAL_DOMAINS = _DOMAIN_DEFINITIONS
map_category_to_domain = resolve_canonical_domain


def map_domain_to_legacy_categories(domain: KnowledgeDomain | str) -> list[Any]:
    """Map canonical domain to legacy KnowledgeCategory enum list."""
    from app.models.enums import KnowledgeCategory

    canonical = resolve_canonical_domain(domain)
    legacy_cat_str = _DOMAIN_TO_LEGACY_CATEGORY[canonical]
    return [KnowledgeCategory(legacy_cat_str)]
