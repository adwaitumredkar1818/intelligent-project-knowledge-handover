"""Permission-Aware Hybrid Retrieval Service for Project Knowledge Assistant.

Platform: The Handover
Module: Project Knowledge Assistant (Module 5 / AI Assistant Area)
"""

from __future__ import annotations

import logging
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from sqlalchemy import or_, select
from sqlalchemy.orm import Session, selectinload

from app.core.config import Settings
from app.models.enums import (
    KnowledgeCategory,
    KnowledgeReviewStatus,
    SearchMode,
)
from app.models.evidence import EvidenceChunk, EvidenceItem
from app.models.knowledge import KnowledgeEvidenceLink, KnowledgeItem
from app.models.relationship import KnowledgeEntity, KnowledgeRelationship, KnowledgeTimelineEvent
from app.schemas.assistant import AssistantCitationResponse
from app.schemas.retrieval import ProjectSearchRequest, SearchFiltersRequest
from app.services.assistant_query import ClassifiedQuery
from app.services.integrations.access_policy import SourceAccessPolicyService
from app.services.rbac import ProjectContext
from app.services.retrieval import HybridRetrievalService

logger = logging.getLogger("app.services.assistant_retrieval")


@dataclass
class RetrievedEvidenceCandidate:
    """Internal candidate representation before fusion, deduplication, and citation assignment."""

    evidence_id: uuid.UUID
    chunk_id: uuid.UUID | None
    knowledge_item_id: uuid.UUID | None
    source_title: str
    source_provider: str
    source_url: str | None
    source_external_id: str | None
    author: str | None
    source_timestamp: datetime | None
    page_number: int | None
    section_title: str | None
    excerpt: str
    content: str
    score: float
    is_verified: bool
    candidate_type: str  # "chunk", "knowledge_item", "relationship", "timeline"


@dataclass
class AssistantRetrievalResult:
    """Consolidated retrieval result ready for LLM prompt insertion and audit logging."""

    evidence_prompt: str
    citations_manifest: list[AssistantCitationResponse]
    candidates_found: int
    candidates_authorized: int
    duration_ms: int
    diagnostics: dict[str, Any] = field(default_factory=dict)


class AssistantRetrievalService:
    """Permission-aware retrieval orchestrator combining Chunks, Knowledge, and Graph."""

    def __init__(
        self,
        *,
        session: Session,
        settings: Settings,
        hybrid_retrieval_service: HybridRetrievalService | None = None,
        access_policy_service: SourceAccessPolicyService | None = None,
    ) -> None:
        self.session = session
        self.settings = settings
        self.hybrid_service = hybrid_retrieval_service
        self.access_policy = access_policy_service or SourceAccessPolicyService()

    def retrieve(
        self,
        *,
        project_ctx: ProjectContext,
        classified_query: ClassifiedQuery,
        search_mode: str = "hybrid",
        include_domains: list[KnowledgeCategory] | None = None,
        max_citations: int = 8,
    ) -> AssistantRetrievalResult:
        """Execute multi-source permission-aware retrieval and return formatted evidence context."""
        started_at = time.perf_counter()
        user_id = project_ctx.principal.user.id
        has_manage = project_ctx.has_permission("project.manage")
        project_id = project_ctx.project.id

        candidates: list[RetrievedEvidenceCandidate] = []
        candidates_found = 0
        candidates_authorized = 0

        # -------------------------------------------------------------------
        # 1. Hybrid Search across Document & Integration Chunks
        # -------------------------------------------------------------------
        chunk_hits: list[RetrievedEvidenceCandidate] = []
        if self.hybrid_service is not None:
            try:
                mode_enum = SearchMode.HYBRID
                if search_mode == "keyword":
                    mode_enum = SearchMode.KEYWORD
                elif search_mode == "semantic":
                    mode_enum = SearchMode.SEMANTIC

                search_req = ProjectSearchRequest(
                    query=classified_query.raw_query,
                    mode=mode_enum,
                    top_k=min(20, max_citations * 2),
                    filters=SearchFiltersRequest(),
                )
                search_resp = self.hybrid_service.search_project(
                    project_ctx=project_ctx,
                    payload=search_req,
                )
                candidates_found += search_resp.total_returned
                candidates_authorized += len(search_resp.results)

                for item in search_resp.results:
                    cit = item.citation
                    chunk_hits.append(
                        RetrievedEvidenceCandidate(
                            evidence_id=cit.evidence_id,
                            chunk_id=cit.chunk_id,
                            knowledge_item_id=None,
                            source_title=cit.title or "Document Evidence",
                            source_provider=cit.source_provider or "system",
                            source_url=cit.source_url,
                            source_external_id=cit.source_external_id,
                            author=cit.source_author_identity,
                            source_timestamp=cit.source_created_at,
                            page_number=cit.page_number,
                            section_title=cit.section_title,
                            excerpt=item.excerpt or item.chunk_text[:300],
                            content=item.chunk_text,
                            score=item.scores.hybrid_score if item.scores else 1.0,
                            is_verified=True,
                            candidate_type="chunk",
                        )
                    )
            except Exception as ex:
                logger.warning("Hybrid search step in assistant retrieval failed: %s", ex, exc_info=True)

        candidates.extend(chunk_hits)

        # -------------------------------------------------------------------
        # 2. Knowledge Intelligence Domain Search (PostgreSQL)
        # -------------------------------------------------------------------
        target_cats = include_domains or classified_query.target_categories
        cat_values = [c.value for c in target_cats] if target_cats else []

        stmt = (
            select(KnowledgeItem)
            .where(
                KnowledgeItem.project_id == project_id,
                KnowledgeItem.is_deleted.is_(False),
            )
            .options(
                selectinload(KnowledgeItem.evidence_links).selectinload(KnowledgeEvidenceLink.evidence_item),
                selectinload(KnowledgeItem.evidence_links).selectinload(KnowledgeEvidenceLink.evidence_chunk),
            )
        )
        if cat_values:
            stmt = stmt.where(
                or_(
                    KnowledgeItem.category.in_(cat_values),
                    KnowledgeItem.primary_domain.in_(cat_values),
                )
            )

        # If search keywords are available, add ILIKE filtering on title/structured_summary
        if classified_query.search_keywords:
            keyword_clauses = [
                or_(
                    KnowledgeItem.title.ilike(f"%{kw}%"),
                    KnowledgeItem.structured_summary.ilike(f"%{kw}%"),
                )
                for kw in classified_query.search_keywords[:5]
            ]
            stmt = stmt.where(or_(*keyword_clauses))

        stmt = stmt.order_by(
            # Prefer approved / human_verified findings
            KnowledgeItem.review_status == KnowledgeReviewStatus.APPROVED.value,
            KnowledgeItem.created_at.desc(),
        ).limit(15)

        knowledge_items = list(self.session.scalars(stmt).all())
        candidates_found += len(knowledge_items)

        for ki in knowledge_items:
            # Check source ACL permissions on supporting evidence
            accessible_links: list[KnowledgeEvidenceLink] = []
            for link in ki.evidence_links:
                if link.evidence_item:
                    can_access = self.access_policy.can_user_access_evidence(
                        evidence=link.evidence_item,
                        user_id=user_id,
                        has_project_manage=has_manage,
                    )
                    if can_access:
                        accessible_links.append(link)

            # Fail closed: if the item has evidence links but NONE are accessible, discard item
            if ki.evidence_links and not accessible_links:
                continue

            candidates_authorized += 1
            primary_link = accessible_links[0] if accessible_links else None
            ev = primary_link.evidence_item if primary_link else None
            chk = primary_link.evidence_chunk if primary_link else None

            excerpt_text = primary_link.supporting_excerpt if primary_link else ki.structured_summary[:300]
            content_text = f"**{ki.title}** ({ki.category})\n{ki.structured_summary}"

            # If there's an active uncertainty or conflict note, surface it
            if ki.uncertainty_reason:
                content_text += f"\n[Uncertainty]: {ki.uncertainty_reason}"

            candidates.append(
                RetrievedEvidenceCandidate(
                    evidence_id=ev.id if ev else ki.id,
                    chunk_id=chk.id if chk else None,
                    knowledge_item_id=ki.id,
                    source_title=ev.title if ev else ki.title,
                    source_provider=ev.source_provider if ev else "reconstructed_knowledge",
                    source_url=ev.source_url if ev else None,
                    source_external_id=ev.source_external_id if ev else None,
                    author=ev.source_author_identity if ev else ki.person_or_owner_label,
                    source_timestamp=ev.source_created_at if ev else ki.created_at,
                    page_number=chk.page_number if chk else None,
                    section_title=chk.section_title if chk else ki.primary_domain,
                    excerpt=excerpt_text,
                    content=content_text,
                    score=0.9 if ki.review_status == KnowledgeReviewStatus.APPROVED.value else 0.7,
                    is_verified=(ki.review_status == KnowledgeReviewStatus.APPROVED.value),
                    candidate_type="knowledge_item",
                )
            )

        # -------------------------------------------------------------------
        # 3. Graph, Timeline, and Traceability Expansion
        # -------------------------------------------------------------------
        # For timeline or work progress queries, retrieve chronological timeline events
        if classified_query.query_type.value in {"timeline_evolution", "work_progress", "operational_historical"}:
            t_stmt = (
                select(KnowledgeTimelineEvent)
                .where(KnowledgeTimelineEvent.project_id == project_id)
                .order_by(KnowledgeTimelineEvent.event_timestamp.desc())
                .limit(8)
            )
            timeline_events = list(self.session.scalars(t_stmt).all())
            candidates_found += len(timeline_events)

            for evt in timeline_events:
                ev = None
                if evt.evidence_id:
                    ev = self.session.get(EvidenceItem, evt.evidence_id)
                    if ev:
                        can_access = self.access_policy.can_user_access_evidence(
                            evidence=ev,
                            user_id=user_id,
                            has_project_manage=has_manage,
                        )
                        if not can_access:
                            continue

                candidates_authorized += 1
                candidates.append(
                    RetrievedEvidenceCandidate(
                        evidence_id=evt.evidence_id if evt.evidence_id else evt.id,
                        chunk_id=None,
                        knowledge_item_id=None,
                        source_title=evt.event_title,
                        source_provider="timeline",
                        source_url=ev.source_url if ev else None,
                        source_external_id=None,
                        author=evt.actor_label,
                        source_timestamp=evt.event_timestamp,
                        page_number=None,
                        section_title="Project Timeline",
                        excerpt=evt.event_summary[:300],
                        content=f"**Timeline Event**: {evt.event_title} ({evt.event_timestamp.isoformat() if evt.event_timestamp else 'N/A'})\n{evt.event_summary}",
                        score=0.85,
                        is_verified=True,
                        candidate_type="timeline",
                    )
                )

        # For dependency or multi-hop queries, retrieve relationships
        if classified_query.query_type.value in {"dependency_relationship", "multi_hop"}:
            r_stmt = (
                select(KnowledgeRelationship)
                .where(
                    KnowledgeRelationship.project_id == project_id,
                    KnowledgeRelationship.is_deleted.is_(False),
                )
                .options(
                    selectinload(KnowledgeRelationship.source_entity),
                    selectinload(KnowledgeRelationship.target_entity),
                    selectinload(KnowledgeRelationship.evidence_links),
                )
                .limit(10)
            )
            relationships = list(self.session.scalars(r_stmt).all())
            candidates_found += len(relationships)

            for rel in relationships:
                # Format relation summary
                src_name = rel.source_entity.canonical_name if rel.source_entity else "Entity"
                tgt_name = rel.target_entity.canonical_name if rel.target_entity else "Entity"
                rel_content = (
                    f"**Relationship**: {src_name} --[{rel.relationship_type}]--> {tgt_name}\n"
                    f"Basis: {rel.relationship_basis} | Description: {rel.relationship_description or 'N/A'}"
                )
                candidates_authorized += 1
                candidates.append(
                    RetrievedEvidenceCandidate(
                        evidence_id=rel.id,
                        chunk_id=None,
                        knowledge_item_id=None,
                        source_title=f"{src_name} -> {tgt_name}",
                        source_provider="relationship_graph",
                        source_url=None,
                        source_external_id=None,
                        author=None,
                        source_timestamp=rel.created_at,
                        page_number=None,
                        section_title="Relationship Graph",
                        excerpt=rel_content[:300],
                        content=rel_content,
                        score=0.8,
                        is_verified=True,
                        candidate_type="relationship",
                    )
                )

        # -------------------------------------------------------------------
        # 4. Fusion, Deduplication, and Bounding
        # -------------------------------------------------------------------
        # Sort candidates by score descending
        candidates.sort(key=lambda c: c.score, reverse=True)

        # Deduplicate candidates by (evidence_id, chunk_id, knowledge_item_id)
        seen_keys: set[str] = set()
        deduped: list[RetrievedEvidenceCandidate] = []
        for c in candidates:
            key = f"{c.evidence_id}:{c.chunk_id}:{c.knowledge_item_id}"
            if key in seen_keys:
                continue
            seen_keys.add(key)
            deduped.append(c)
            if len(deduped) >= max_citations:
                break

        # -------------------------------------------------------------------
        # 5. Citation Manifest & Context Block Generation
        # -------------------------------------------------------------------
        citations_manifest: list[AssistantCitationResponse] = []
        context_blocks: list[str] = []

        for idx, item in enumerate(deduped, start=1):
            label = f"S{idx}"
            cit = AssistantCitationResponse(
                citation_label=label,
                evidence_id=item.evidence_id,
                chunk_id=item.chunk_id,
                knowledge_item_id=item.knowledge_item_id,
                source_title=item.source_title,
                source_provider=item.source_provider,
                source_url=item.source_url,
                source_external_id=item.source_external_id,
                author=item.author,
                source_timestamp=item.source_timestamp,
                page_number=item.page_number,
                section_title=item.section_title,
                excerpt=item.excerpt,
                is_verified=item.is_verified,
            )
            citations_manifest.append(cit)

            # Build XML-delimited prompt block
            date_str = item.source_timestamp.strftime("%Y-%m-%d") if item.source_timestamp else "Undated"
            author_str = item.author or "Unknown Author"
            sec_str = f" | Section: {item.section_title}" if item.section_title else ""
            pg_str = f" | Page: {item.page_number}" if item.page_number else ""

            block = (
                f'<project_evidence id="{label}" provider="{item.source_provider}" title="{item.source_title}">\n'
                f"**Metadata**: Author: {author_str} | Date: {date_str}{sec_str}{pg_str}\n"
                f"**Content**:\n{item.content.strip()}\n"
                f"</project_evidence>"
            )
            context_blocks.append(block)

        evidence_prompt = "\n\n".join(context_blocks)
        duration_ms = int((time.perf_counter() - started_at) * 1000)

        diagnostics = {
            "query_type": classified_query.query_type.value,
            "search_mode": search_mode,
            "target_categories": [c.value for c in target_cats],
            "extracted_jira_keys": classified_query.extracted_jira_keys,
            "extracted_pr_numbers": classified_query.extracted_pr_numbers,
            "extracted_commit_hashes": classified_query.extracted_commit_hashes,
            "chunk_hits_count": len(chunk_hits),
            "total_candidates_found": candidates_found,
            "total_candidates_authorized": candidates_authorized,
            "total_selected": len(deduped),
            "duration_ms": duration_ms,
        }

        return AssistantRetrievalResult(
            evidence_prompt=evidence_prompt,
            citations_manifest=citations_manifest,
            candidates_found=candidates_found,
            candidates_authorized=candidates_authorized,
            duration_ms=duration_ms,
            diagnostics=diagnostics,
        )
