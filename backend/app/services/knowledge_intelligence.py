"""Service coordinating Phase Module 3: Knowledge Intelligence across 8 canonical domains."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Literal

from sqlalchemy.orm import Session

from app.models.enums import (
    KnowledgeCategory,
    KnowledgeReviewStatus,
    SupportClassification,
)
from app.repositories.knowledge import KnowledgeRepository
from app.schemas.knowledge import (
    ExtractionTriggerResponse,
    KnowledgeExtractionRunListResponse,
    KnowledgeExtractionRunResponse,
    KnowledgeItemDetailResponse,
    KnowledgeItemListResponse,
    ProjectKnowledgeExtractRequest,
)
from app.schemas.knowledge_intelligence import (
    DomainCoverageMetric,
    KnowledgeIntelligenceDomainsResponse,
    KnowledgeIntelligenceExtractRequest,
    KnowledgeIntelligenceSummaryResponse,
)
from app.services.knowledge import KnowledgeReconstructionService
from app.services.knowledge_domains import (
    CANONICAL_DOMAINS,
    KnowledgeDomain,
    map_category_to_domain,
    map_domain_to_legacy_categories,
)
from app.services.rbac import ProjectContext
from app.services.timeline import ProjectTimelineResponse, ProjectTimelineService


class KnowledgeIntelligenceService:
    """Coordinates domain intelligence, coverage metrics, findings, timeline, and extraction."""

    def __init__(
        self,
        *,
        session: Session,
        knowledge_repository: KnowledgeRepository | None = None,
        reconstruction_service: KnowledgeReconstructionService | None = None,
        timeline_service: ProjectTimelineService | None = None,
    ) -> None:
        self._session = session
        self._repo = knowledge_repository or KnowledgeRepository(session)
        self._reconstruction_service = reconstruction_service
        self._timeline_service = timeline_service or ProjectTimelineService(session)

    def get_domains_coverage(
        self,
        *,
        project_ctx: ProjectContext,
        include_synthetic: bool = False,
    ) -> KnowledgeIntelligenceDomainsResponse:
        """Calculate live coverage and telemetry across all 8 canonical domains."""
        # Query all accessible items for caller respecting source ACLs
        accessible_items, _ = self._repo.list_accessible_items_for_project(
            project_id=project_ctx.project.id,
            viewer_user_id=project_ctx.user_id,
            has_project_manage=project_ctx.has_permission("project.manage"),
            include_stale=True,
            stale_only=False,
            include_synthetic=include_synthetic,
            limit=5000,
            offset=0,
        )

        domain_metrics: dict[str, DomainCoverageMetric] = {}
        for dom_enum, defn in CANONICAL_DOMAINS.items():
            domain_metrics[dom_enum.value] = DomainCoverageMetric(
                domain_id=dom_enum.value,
                code=defn.code,
                display_name=defn.display_name,
                description=defn.description,
            )

        active_domains_count = 0

        for res in accessible_items:
            item = res.item
            dom_key = item.primary_domain or map_category_to_domain(item.category).value
            metric = domain_metrics.get(dom_key)
            if metric is None:
                continue

            metric.item_count += 1
            if item.is_stale:
                metric.stale_count += 1

            # Verification states
            if (
                item.review_status == KnowledgeReviewStatus.APPROVED.value
                or item.epistemic_status == "human_verified"
            ):
                metric.verified_count += 1
            elif item.review_status == KnowledgeReviewStatus.REJECTED.value:
                metric.rejected_count += 1
            else:
                metric.pending_review_count += 1

            # Confidence breakdown
            conf_meta = dict(item.confidence_metadata_json or {})
            conf_lvl = str(conf_meta.get("extraction_confidence", "medium")).lower()
            if conf_lvl == "high":
                metric.high_confidence_count += 1
            elif conf_lvl == "low":
                metric.low_confidence_count += 1
            else:
                metric.medium_confidence_count += 1

            if (
                item.support_classification == SupportClassification.UNCERTAIN.value
                or conf_meta.get("conflict_or_ambiguity_flag")
            ):
                metric.uncertain_count += 1

            # Sources breakdown
            attr = dict(item.source_attribution_json or {})
            prov = str(attr.get("source_provider") or "unknown").lower()
            metric.sources_breakdown[prov] = metric.sources_breakdown.get(prov, 0) + 1

            # Last extracted timestamp
            if metric.last_extracted_at is None or item.created_at > metric.last_extracted_at:
                metric.last_extracted_at = item.created_at

        # Calculate completeness score and tally active domains
        for metric in domain_metrics.values():
            if metric.item_count > 0:
                active_domains_count += 1
                # Completeness score combines non-stale ratio and verified/high-confidence ratio
                non_stale_ratio = max(0.0, 1.0 - (metric.stale_count / metric.item_count))
                confidence_ratio = (
                    metric.high_confidence_count + 0.5 * metric.medium_confidence_count
                ) / metric.item_count
                verification_ratio = metric.verified_count / metric.item_count
                score = round(
                    (0.4 * non_stale_ratio) + (0.3 * confidence_ratio) + (0.3 * verification_ratio),
                    2,
                )
                metric.completeness_score = min(1.0, max(0.0, score))

        ordered_domains = sorted(domain_metrics.values(), key=lambda d: d.code)

        return KnowledgeIntelligenceDomainsResponse(
            domains=ordered_domains,
            total_domains=len(CANONICAL_DOMAINS),
            active_domains_count=active_domains_count,
        )

    def get_summary(
        self,
        *,
        project_ctx: ProjectContext,
        include_synthetic: bool = False,
    ) -> KnowledgeIntelligenceSummaryResponse:
        """Calculate executive project knowledge intelligence summary."""
        domains_resp = self.get_domains_coverage(
            project_ctx=project_ctx,
            include_synthetic=include_synthetic,
        )

        total_findings = sum(d.item_count for d in domains_resp.domains)
        verified_findings = sum(d.verified_count for d in domains_resp.domains)
        pending_verification = sum(d.pending_review_count for d in domains_resp.domains)
        rejected_findings = sum(d.rejected_count for d in domains_resp.domains)
        stale_findings = sum(d.stale_count for d in domains_resp.domains)

        # Overall confidence score
        total_high = sum(d.high_confidence_count for d in domains_resp.domains)
        total_med = sum(d.medium_confidence_count for d in domains_resp.domains)
        overall_conf = (
            round((total_high * 1.0 + total_med * 0.7) / total_findings, 2)
            if total_findings > 0
            else 0.0
        )

        # Readiness percentage: domain coverage (40%) + verification rate (40%) + confidence (20%)
        domain_breadth_pct = (domains_resp.active_domains_count / 8.0) * 100.0
        verification_pct = (
            (verified_findings / total_findings * 100.0) if total_findings > 0 else 0.0
        )
        readiness_pct = round(
            (0.40 * domain_breadth_pct) + (0.40 * verification_pct) + (0.20 * overall_conf * 100.0),
            1,
        )

        if self._reconstruction_service is not None:
            status_summary = self._reconstruction_service.get_project_knowledge_status(
                project_ctx=project_ctx,
                include_synthetic=include_synthetic,
            )
            active_runs = status_summary.active_runs_count
            latest_run = status_summary.latest_run
        else:
            stats = self._repo.get_project_knowledge_stats(
                project_id=project_ctx.project.id,
                viewer_user_id=project_ctx.user_id,
                has_project_manage=project_ctx.has_permission("project.manage"),
                include_synthetic=include_synthetic,
            )
            active_runs = stats.active_runs_count
            latest_run = None

        return KnowledgeIntelligenceSummaryResponse(
            project_id=project_ctx.project.id,
            total_findings=total_findings,
            verified_findings=verified_findings,
            pending_verification=pending_verification,
            rejected_findings=rejected_findings,
            stale_findings=stale_findings,
            overall_confidence_score=overall_conf,
            overall_readiness_pct=readiness_pct,
            domain_coverage=domains_resp.domains,
            active_runs_count=active_runs,
            latest_run=latest_run,
        )

    def list_findings(
        self,
        *,
        project_ctx: ProjectContext,
        domain: str | None = None,
        category: str | None = None,
        epistemic_status: str | None = None,
        review_status: str | None = None,
        support_classification: str | None = None,
        normalised_status: str | None = None,
        person: str | None = None,
        source_provider: str | None = None,
        evidence_id: uuid.UUID | None = None,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
        include_stale: bool = True,
        stale_only: bool = False,
        include_synthetic: bool = False,
        limit: int = 20,
        offset: int = 0,
    ) -> KnowledgeItemListResponse:
        """List findings filtered by source ACLs and canonical domain or legacy category."""
        return self._reconstruction_service.list_knowledge_items(
            project_ctx=project_ctx,
            category=domain or category,
            epistemic_status=epistemic_status,
            review_status=review_status,
            support_classification=support_classification,
            normalised_status=normalised_status,
            person=person,
            source_provider=source_provider,
            evidence_id=evidence_id,
            date_from=date_from,
            date_to=date_to,
            include_stale=include_stale,
            stale_only=stale_only,
            include_synthetic=include_synthetic,
            limit=limit,
            offset=offset,
        )

    def get_finding_detail(
        self,
        *,
        project_ctx: ProjectContext,
        finding_id: uuid.UUID,
    ) -> KnowledgeItemDetailResponse:
        """Retrieve single finding with verified supporting evidence links."""
        return self._reconstruction_service.get_knowledge_item_detail(
            project_ctx=project_ctx,
            item_id=finding_id,
        )

    def get_timeline(
        self,
        *,
        project_ctx: ProjectContext,
        domain: str | None = None,
        source_provider: str | None = None,
        event_type: str | None = None,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
        sort_order: Literal["asc", "desc"] = "desc",
        limit: int = 50,
        offset: int = 0,
    ) -> ProjectTimelineResponse:
        """Synthesize chronological timeline for the project."""
        return self._timeline_service.get_timeline(
            project_id=project_ctx.project.id,
            viewer_user_id=project_ctx.user_id,
            has_project_manage=project_ctx.has_permission("project.manage"),
            domain=domain,
            source_provider=source_provider,
            event_type=event_type,
            date_from=date_from,
            date_to=date_to,
            sort_order=sort_order,
            limit=limit,
            offset=offset,
        )

    def trigger_extraction(
        self,
        *,
        project_ctx: ProjectContext,
        payload: KnowledgeIntelligenceExtractRequest,
    ) -> ExtractionTriggerResponse:
        """Trigger or queue knowledge extraction across canonical domains."""
        # Convert domains to categories
        categories: list[KnowledgeCategory] = []
        if payload.domains:
            for d in payload.domains:
                try:
                    dom_enum = KnowledgeDomain(d.upper())
                    cats = map_domain_to_legacy_categories(dom_enum)
                    categories.extend(cats)
                except ValueError:
                    try:
                        cat_enum = KnowledgeCategory(d.lower())
                        categories.append(cat_enum)
                    except ValueError:
                        continue

        dedup_cats = list(dict.fromkeys(categories)) if categories else None

        req = ProjectKnowledgeExtractRequest(
            evidence_ids=payload.evidence_ids,
            categories=dedup_cats,
            force_rerun=payload.force_rerun,
            include_synthetic=payload.include_synthetic,
        )
        return self._reconstruction_service.trigger_project_extraction(
            project_ctx=project_ctx,
            payload=req,
        )

    def list_runs(
        self,
        *,
        project_ctx: ProjectContext,
        run_status: str | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> KnowledgeExtractionRunListResponse:
        """List extraction runs for the project."""
        return self._reconstruction_service.list_extraction_runs(
            project_ctx=project_ctx,
            status=run_status,
            limit=limit,
            offset=offset,
        )

    def get_run(
        self,
        *,
        project_ctx: ProjectContext,
        run_id: uuid.UUID,
    ) -> KnowledgeExtractionRunResponse:
        """Retrieve extraction run details."""
        return self._reconstruction_service.get_extraction_run(
            project_ctx=project_ctx,
            run_id=run_id,
        )
