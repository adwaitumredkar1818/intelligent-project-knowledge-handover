"""Project Knowledge Quality and Completeness Scoring Engine.

Implements explainable, transparent 9-dimension project knowledge quality analysis:
1. Evidence Coverage (Ratio of project areas supported by raw evidence)
2. Verification Coverage (Ratio of findings reviewed/verified by humans)
3. Decision Traceability (Ratio of decisions with complete 5-stage causal chains)
4. Ownership Coverage (Ratio of components with active maintainers vs unowned)
5. Dependency Clarity (Ratio of dependencies without cycles or unresolved blockers)
6. Documentation Coverage (Ratio of architecture & operational specs documented)
7. Operational Readiness (Ratio of verified runbooks and deploy procedures)
8. Risk Coverage (Ratio of identified risks with mitigation strategies)
9. Knowledge Freshness (Recency decay and staleness evaluation)
"""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy.orm import Session

from app.models.enums import KnowledgeCategory, KnowledgeReviewStatus
from app.models.knowledge import KnowledgeItem
from app.models.relationship import (
    DecisionTraceabilityChain,
    KnowledgeEntity,
    KnowledgeRelationship,
)
from app.models.verification import VerificationIssue


class KnowledgeQualityEngine:
    """Evaluates project-level knowledge quality across 9 explainable dimensions."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def assess_project_quality(
        self,
        *,
        project_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> dict[str, Any]:
        """Perform comprehensive 9-dimension knowledge quality and gap assessment."""
        items = (
            self.session.query(KnowledgeItem)
            .filter(KnowledgeItem.project_id == project_id)
            .all()
        )
        total_items = len(items)

        entities = (
            self.session.query(KnowledgeEntity)
            .filter(KnowledgeEntity.project_id == project_id)
            .all()
        )
        relationships = (
            self.session.query(KnowledgeRelationship)
            .filter(KnowledgeRelationship.project_id == project_id)
            .all()
        )

        issues = (
            self.session.query(VerificationIssue)
            .filter(VerificationIssue.project_id == project_id)
            .all()
        )

        chains = (
            self.session.query(DecisionTraceabilityChain)
            .filter(DecisionTraceabilityChain.project_id == project_id)
            .all()
        )

        # Dimension 1: Evidence Coverage
        items_with_evidence = sum(
            1 for i in items
            if getattr(i, "evidence_links", None) or getattr(i, "evidence_chunks", None)
        )
        evidence_coverage = (items_with_evidence / total_items) if total_items > 0 else 0.5

        # Dimension 2: Verification Coverage
        verified_items = sum(
            1 for i in items
            if i.review_status == KnowledgeReviewStatus.APPROVED.value
            or i.epistemic_status == "human_verified"
        )
        verification_coverage = (verified_items / total_items) if total_items > 0 else 0.0

        # Dimension 3: Decision Traceability
        complete_chains = sum(
            1 for c in chains
            if c.completeness_status in ("complete", "verified")
            or (c.work_item_count > 0 and c.pull_request_count > 0)
        )
        traceability_coverage = (complete_chains / len(chains)) if len(chains) > 0 else 0.7

        # Dimension 4: Ownership Coverage
        comp_types = ("component", "technical_component", "repository")
        component_entities = [e for e in entities if e.entity_type in comp_types]
        owned_components = 0
        for comp in component_entities:
            has_owner = any(
                r.target_entity_id == comp.id or r.source_entity_id == comp.id
                for r in relationships
                if r.relationship_type in ("owned_by", "maintained_by", "assigned_to")
            )
            if has_owner:
                owned_components += 1
        denom = len(component_entities)
        ownership_coverage = (owned_components / denom) if denom > 0 else 0.8

        # Dimension 5: Dependency Clarity
        conflicting_deps = sum(
            1 for iss in issues
            if "cycle" in iss.issue_type.lower() or "blocker" in iss.issue_type.lower()
        )
        dependency_clarity = max(0.0, 1.0 - (conflicting_deps * 0.1))

        # Dimension 6: Documentation Coverage
        has_architecture = any(
            i.category in (KnowledgeCategory.TECHNICAL_ARCHITECTURE.value, KnowledgeCategory.ARCHITECTURE_TECHNICAL.value)
            or "architecture" in i.title.lower()
            for i in items
        )
        has_decisions = any(
            i.category == KnowledgeCategory.DECISIONS_RATIONALE.value
            for i in items
        )
        doc_score = (0.5 if has_architecture else 0.0) + (0.5 if has_decisions else 0.0)

        # Dimension 7: Operational Readiness
        has_runbook = any(
            "runbook" in i.title.lower()
            or "deployment" in i.title.lower()
            or i.category == KnowledgeCategory.OPERATIONAL_HISTORICAL.value
            for i in items
        )
        operational_readiness = 0.9 if has_runbook else 0.4

        # Dimension 8: Risk Coverage
        risk_items = [
            i for i in items
            if i.category in (KnowledgeCategory.BUGS_BLOCKERS_RISKS.value, KnowledgeCategory.RISKS_BLOCKERS_QUESTIONS.value) or "risk" in i.title.lower()
        ]
        mitigated_risks = sum(
            1 for r in risk_items
            if "mitigation" in (r.content or "").lower() or r.review_status == "approved"
        )
        risk_coverage = (mitigated_risks / len(risk_items)) if risk_items else 0.85

        # Dimension 9: Knowledge Freshness
        stale_count = sum(1 for i in items if i.is_stale)
        freshness_score = max(0.0, 1.0 - (stale_count / total_items)) if total_items > 0 else 1.0

        dimension_scores = {
            "evidence_coverage": round(evidence_coverage * 100, 1),
            "verification_coverage": round(verification_coverage * 100, 1),
            "decision_traceability": round(traceability_coverage * 100, 1),
            "ownership_coverage": round(ownership_coverage * 100, 1),
            "dependency_clarity": round(dependency_clarity * 100, 1),
            "documentation_coverage": round(doc_score * 100, 1),
            "operational_readiness": round(operational_readiness * 100, 1),
            "risk_coverage": round(risk_coverage * 100, 1),
            "knowledge_freshness": round(freshness_score * 100, 1),
        }

        weights = {
            "evidence_coverage": 0.15,
            "verification_coverage": 0.15,
            "decision_traceability": 0.12,
            "ownership_coverage": 0.12,
            "dependency_clarity": 0.10,
            "documentation_coverage": 0.10,
            "operational_readiness": 0.10,
            "risk_coverage": 0.08,
            "knowledge_freshness": 0.08,
        }
        overall_score = sum(dimension_scores[k] * weights[k] for k in weights)

        # Detect Actionable Knowledge Gaps
        gaps: list[dict[str, str]] = []
        if verification_coverage < 0.5:
            pct = dimension_scores['verification_coverage']
            gaps.append({
                "type": "unverified_knowledge",
                "severity": "high",
                "title": "Low Human Verification Coverage",
                "description": f"Only {pct}% of extracted items have been verified by an auditor.",
                "recommendation": "Review pending items in Verification Center.",
            })

        if ownership_coverage < 0.7 and component_entities:
            unowned = len(component_entities) - owned_components
            gaps.append({
                "type": "unowned_components",
                "severity": "high",
                "title": "Unowned Technical Components Detected",
                "description": f"{unowned} component(s) have no assigned maintainer or owner.",
                "recommendation": "Map outgoing developers to incoming successors in Handover.",
            })

        if not has_runbook:
            gaps.append({
                "type": "missing_runbook",
                "severity": "medium",
                "title": "Missing Operational Runbook",
                "description": "No documented deployment or operational procedures were detected.",
                "recommendation": "Upload deployment instructions to Evidence Workspace.",
            })

        if stale_count > 0:
            gaps.append({
                "type": "stale_knowledge",
                "severity": "low",
                "title": "Stale Evidence Present",
                "description": f"{stale_count} item(s) are flagged as potentially outdated.",
                "recommendation": "Sync latest GitHub commits or Jira tickets to refresh.",
            })

        return {
            "project_id": str(project_id),
            "overall_quality_score": round(overall_score, 1),
            "dimension_scores": dimension_scores,
            "total_items": total_items,
            "verified_items": verified_items,
            "stale_items": stale_count,
            "identified_gaps": gaps,
            "recommendation_count": len(gaps),
        }
