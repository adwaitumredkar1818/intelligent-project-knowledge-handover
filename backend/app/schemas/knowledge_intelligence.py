"""Pydantic schemas for Module 3: Knowledge Intelligence APIs."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import Field

from app.schemas.common import BaseSchema
from app.schemas.knowledge import (
    KnowledgeExtractionRunResponse,
)


class DomainCoverageMetric(BaseSchema):
    """Granular coverage, confidence, and verification breakdown for one canonical domain."""

    domain_id: str
    code: int
    display_name: str
    description: str
    item_count: int = 0
    verified_count: int = 0
    pending_review_count: int = 0
    rejected_count: int = 0
    stale_count: int = 0
    high_confidence_count: int = 0
    medium_confidence_count: int = 0
    low_confidence_count: int = 0
    uncertain_count: int = 0
    completeness_score: float = 0.0
    sources_breakdown: dict[str, int] = Field(default_factory=dict)
    last_extracted_at: datetime | None = None


class KnowledgeIntelligenceDomainsResponse(BaseSchema):
    """All eight canonical project knowledge domains with live coverage telemetry."""

    domains: list[DomainCoverageMetric]
    total_domains: int = 8
    active_domains_count: int = 0


class KnowledgeIntelligenceSummaryResponse(BaseSchema):
    """Executive project knowledge intelligence summary for dashboard and audits."""

    project_id: uuid.UUID
    total_findings: int
    verified_findings: int
    pending_verification: int
    rejected_findings: int
    stale_findings: int
    overall_confidence_score: float
    overall_readiness_pct: float
    domain_coverage: list[DomainCoverageMetric]
    active_runs_count: int
    latest_run: KnowledgeExtractionRunResponse | None = None


class KnowledgeIntelligenceExtractRequest(BaseSchema):
    """Trigger or schedule knowledge extraction across specified domains."""

    evidence_ids: list[uuid.UUID] | None = Field(default=None, max_length=100)
    domains: list[str] | None = Field(default=None, max_length=16)
    force_rerun: bool = False
    include_synthetic: bool = False
