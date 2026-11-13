"""Full relationship reconstruction coordinator service.

Coordinates the complete cross-source relationship pipeline:
1. Entity seeding from KnowledgeItems and Evidence metadata
2. Exact identifier discovery (Method 1)
3. Structured connector discovery (Method 2)
4. Contextual path discovery (Method 3)
5. Optional Qwen3 8B LLM discovery (Method 5)
6. Identity resolution and deduplication
7. Decision-to-implementation traceability indexing
8. Timeline event generation
9. Reconstruction run progress and telemetry tracking
"""

from __future__ import annotations

import logging
import time
import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.enums import (
    EntityType,
    KnowledgeCategory,
    RelationshipBasis,
    RelationshipRunStatus,
    TimelineOrigin,
    TimelinePrecision,
)
from app.models.evidence import EvidenceItem
from app.models.knowledge import KnowledgeItem
from app.models.relationship import KnowledgeEntity, RelationshipReconstructionRun
from app.repositories.relationship import (
    EntityRepository,
    RelationshipRepository,
    RelationshipRunRepository,
    TimelineRepository,
)
from app.services.identity_resolution import IdentityResolutionService
from app.services.llm import StructuredLLMClient
from app.services.relationship_discovery import RelationshipDiscoveryEngine
from app.services.traceability import DecisionTraceabilityService

logger = logging.getLogger("app.services.relationship_coordinator")

# Mapping from KnowledgeCategory to EntityType
_CATEGORY_TO_ENTITY_TYPE: dict[str, str] = {
    KnowledgeCategory.DECISIONS_RATIONALE.value: EntityType.DECISION.value,
    KnowledgeCategory.TECHNICAL_ARCHITECTURE.value: EntityType.COMPONENT.value,
    KnowledgeCategory.WORK_ITEMS.value: EntityType.WORK_ITEM.value,
    KnowledgeCategory.BUGS_BLOCKERS_RISKS.value: EntityType.RISK.value,
    KnowledgeCategory.DEPENDENCIES.value: EntityType.DEPENDENCY.value,
    KnowledgeCategory.OPERATIONAL_HISTORICAL.value: EntityType.PROCEDURE.value,
    KnowledgeCategory.RESPONSIBILITIES_OWNERSHIP.value: EntityType.PERSON.value,
    KnowledgeCategory.PROJECT_OVERVIEW_CONTEXT.value: EntityType.DOCUMENT.value,
}


class RelationshipCoordinatorService:
    """Coordinates full asynchronous or on-demand relationship graph reconstruction."""

    def __init__(
        self,
        session: Session,
        *,
        llm_client: StructuredLLMClient | None = None,
    ) -> None:
        self._session = session
        self._entity_repo = EntityRepository(session)
        self._rel_repo = RelationshipRepository(session)
        self._run_repo = RelationshipRunRepository(session)
        self._timeline_repo = TimelineRepository(session)
        self._discovery_engine = RelationshipDiscoveryEngine(session, llm_client=llm_client)
        self._identity_service = IdentityResolutionService(session)
        self._traceability_service = DecisionTraceabilityService(session)

    def seed_entities_from_project_evidence(
        self,
        *,
        organisation_id: uuid.UUID,
        project_id: uuid.UUID,
    ) -> int:
        """Seed KnowledgeEntity records from existing KnowledgeItems and EvidenceItems."""
        seeded = 0

        # 1. From KnowledgeItems
        k_items = list(
            self._session.execute(
                select(KnowledgeItem).where(
                    KnowledgeItem.project_id == project_id,
                    KnowledgeItem.is_deleted.is_(False),
                )
            )
            .scalars()
            .all()
        )

        for k in k_items:
            e_type = _CATEGORY_TO_ENTITY_TYPE.get(k.category, EntityType.DOCUMENT.value)
            # Find primary evidence link if available
            ev_id = k.evidence_links[0].evidence_id if k.evidence_links else None

            self._entity_repo.create_or_get_entity(
                organisation_id=organisation_id,
                project_id=project_id,
                entity_type=e_type,
                canonical_name=k.title[:255],
                description=k.content,
                primary_knowledge_item_id=k.id,
                primary_evidence_id=ev_id,
                confidence_score=float(k.confidence_score or 1.0),
                metadata_json=k.metadata_json or {},
                first_observed_at=k.created_at,
                last_observed_at=k.updated_at,
                is_synthetic=k.is_synthetic,
            )
            seeded += 1

            # If there's an author/owner person mentioned in metadata, seed person entity
            owner_name = (k.metadata_json or {}).get("owner") or (k.metadata_json or {}).get(
                "author"
            )
            if owner_name and isinstance(owner_name, str) and len(owner_name.strip()) > 1:
                p_ent = self._entity_repo.create_or_get_entity(
                    organisation_id=organisation_id,
                    project_id=project_id,
                    entity_type=EntityType.PERSON.value,
                    canonical_name=owner_name.strip(),
                    source_provider="metadata",
                    is_synthetic=k.is_synthetic,
                )
                self._entity_repo.add_alias(
                    entity_id=p_ent.id,
                    organisation_id=organisation_id,
                    project_id=project_id,
                    alias_value=owner_name.strip(),
                    source_provider="metadata",
                    is_synthetic=k.is_synthetic,
                )

        # 2. From EvidenceItems (GitHub PRs, Commits, Jira Issues)
        evidence_items = list(
            self._session.execute(
                select(EvidenceItem).where(
                    EvidenceItem.project_id == project_id,
                    EvidenceItem.deleted_at.is_(None),
                )
            )
            .scalars()
            .all()
        )

        for ev in evidence_items:
            meta = ev.metadata_json or {}
            source_type = ev.source_type

            if "pull_request" in source_type or "pr" in source_type:
                ent_type = EntityType.PULL_REQUEST.value
            elif "commit" in source_type:
                ent_type = EntityType.COMMIT.value
            elif "jira" in source_type or "issue" in source_type:
                ent_type = EntityType.WORK_ITEM.value
            elif "meeting" in source_type:
                ent_type = EntityType.MEETING_NOTE.value
            else:
                ent_type = EntityType.DOCUMENT.value

            self._entity_repo.create_or_get_entity(
                organisation_id=organisation_id,
                project_id=project_id,
                entity_type=ent_type,
                canonical_name=ev.title[:255],
                description=getattr(ev, "description", None),
                primary_evidence_id=ev.id,
                external_source_id=ev.source_external_id,
                source_provider=ev.source_type,
                metadata_json=meta,
                first_observed_at=ev.source_created_at or ev.created_at,
                last_observed_at=ev.source_updated_at or ev.created_at,
                is_synthetic=getattr(ev, "is_synthetic", False),
            )
            seeded += 1

            # Seed author/creator aliases
            author = meta.get("author") or meta.get("user") or meta.get("reporter")
            if author and isinstance(author, str) and len(author.strip()) > 1:
                p_ent = self._entity_repo.create_or_get_entity(
                    organisation_id=organisation_id,
                    project_id=project_id,
                    entity_type=EntityType.PERSON.value,
                    canonical_name=author.strip(),
                    source_provider=ev.source_type,
                    is_synthetic=getattr(ev, "is_synthetic", False),
                )
                self._entity_repo.add_alias(
                    entity_id=p_ent.id,
                    organisation_id=organisation_id,
                    project_id=project_id,
                    alias_value=author.strip(),
                    source_provider=ev.source_type,
                    is_synthetic=getattr(ev, "is_synthetic", False),
                )

        self._session.flush()
        return seeded

    def run_reconstruction(
        self,
        *,
        organisation_id: uuid.UUID,
        project_id: uuid.UUID,
        run_id: uuid.UUID | None = None,
        include_llm_suggestions: bool = False,
    ) -> RelationshipReconstructionRun:
        """Execute full relationship discovery and graph reconstruction run."""
        start_time = time.monotonic()

        if run_id is not None:
            run = self._run_repo.get_run(run_id)
            if not run:
                raise ValueError(f"Run {run_id} not found")
        else:
            run = self._run_repo.create_run(organisation_id=organisation_id, project_id=project_id)

        self._run_repo.update_run_progress(run.id, status=RelationshipRunStatus.RUNNING.value)

        try:
            # 1. Seed Entities
            self.seed_entities_from_project_evidence(
                organisation_id=organisation_id,
                project_id=project_id,
            )

            # 2. Discover Exact Identifier Links
            exact_drafts = self._discovery_engine.discover_exact_identifier_links(
                project_id=project_id,
                organisation_id=organisation_id,
            )

            # 3. Discover Structured Connector Links
            connector_drafts = self._discovery_engine.discover_structured_connector_links(
                project_id=project_id,
                organisation_id=organisation_id,
            )

            # 4. Discover Contextual File Path Matches
            contextual_drafts = self._discovery_engine.discover_contextual_path_matches(
                project_id=project_id,
            )

            # 5. Optional LLM Extraction
            llm_drafts = []
            if include_llm_suggestions:
                llm_drafts = self._discovery_engine.discover_llm_assisted_relationships(
                    project_id=project_id,
                    organisation_id=organisation_id,
                )

            all_drafts = exact_drafts + connector_drafts + contextual_drafts + llm_drafts

            # Persist Relationships
            created_count, updated_count = self._discovery_engine.persist_discovered_relationships(
                organisation_id=organisation_id,
                project_id=project_id,
                drafts=all_drafts,
            )

            explicit_count = sum(
                1 for d in all_drafts if d.relationship_basis == RelationshipBasis.EXPLICIT.value
            )
            inferred_count = sum(
                1 for d in all_drafts if d.relationship_basis == RelationshipBasis.INFERRED.value
            )

            # 6. Run Identity Resolution across entities of the same type
            all_entities = list(
                self._session.execute(
                    select(KnowledgeEntity).where(
                        KnowledgeEntity.project_id == project_id,
                        KnowledgeEntity.is_deleted.is_(False),
                    )
                )
                .scalars()
                .all()
            )
            # Compare entities of same type
            by_type: dict[str, list[KnowledgeEntity]] = {}
            for e in all_entities:
                by_type.setdefault(e.entity_type, []).append(e)

            for _e_type, group in by_type.items():
                if len(group) > 1:
                    for i in range(len(group)):
                        for j in range(i + 1, min(i + 20, len(group))):
                            self._identity_service.evaluate_and_record_candidate(group[i], group[j])

            # 7. Index Decision Traceability Chains
            self._traceability_service.index_project_traceability(
                organisation_id=organisation_id,
                project_id=project_id,
            )

            # 8. Index Timeline Events from Evidence Items
            evidence_items = list(
                self._session.execute(
                    select(EvidenceItem).where(
                        EvidenceItem.project_id == project_id,
                        EvidenceItem.deleted_at.is_(None),
                    )
                )
                .scalars()
                .all()
            )
            for ev in evidence_items:
                # Find matching entities
                matched_ents = (
                    self._session.execute(
                        select(KnowledgeEntity).where(
                            KnowledgeEntity.project_id == project_id,
                            KnowledgeEntity.primary_evidence_id == ev.id,
                            KnowledgeEntity.is_deleted.is_(False),
                        )
                    )
                    .scalars()
                    .all()
                )
                for matched_ent in matched_ents:
                    evt_title = (
                        f"{matched_ent.entity_type.replace('_', ' ').title()}: "
                        f"{matched_ent.canonical_name}"
                    )
                    self._timeline_repo.create_event(
                        organisation_id=organisation_id,
                        project_id=project_id,
                        entity_id=matched_ent.id,
                        evidence_id=ev.id,
                        event_type=matched_ent.entity_type,
                        title=evt_title,
                        summary=matched_ent.description,
                        occurred_at=ev.source_created_at or ev.created_at,
                        timestamp_precision=TimelinePrecision.EXACT_DATETIME.value,
                        timestamp_origin=TimelineOrigin.SOURCE_API.value,
                        is_synthetic=getattr(ev, "is_synthetic", False),
                    )

            duration_ms = int((time.monotonic() - start_time) * 1000)

            run = self._run_repo.update_run_progress(
                run.id,
                status=RelationshipRunStatus.COMPLETED.value,
                entities_count=len(all_entities),
                relationships_count=created_count + updated_count,
                explicit_count=explicit_count,
                inferred_count=inferred_count,
                duration_ms=duration_ms,
            )
            return run

        except Exception as exc:
            logger.exception("Relationship reconstruction run %s failed: %s", run.id, exc)
            duration_ms = int((time.monotonic() - start_time) * 1000)
            run = self._run_repo.update_run_progress(
                run.id,
                status=RelationshipRunStatus.FAILED.value,
                duration_ms=duration_ms,
                error_message=str(exc)[:500],
            )
            raise
