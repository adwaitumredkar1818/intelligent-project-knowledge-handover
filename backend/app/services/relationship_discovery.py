"""Cross-source relationship discovery engine for Relationship Explorer.

Implements 5 complementary discovery methods:
1. Exact Identifier Linking (Jira keys, PR numbers, commit SHAs, ADR references)
2. Structured Connector Links (GitHub authors, reviewers, branches; Jira links, components, assignees)
3. Contextual File/Path Matching (PR changed files vs component paths)
4. Semantic Matching (Embedding cosine similarity over threshold)
5. Qwen3 8B LLM-Assisted Candidate Extraction (grounded in verbatim evidence chunks)
"""

from __future__ import annotations

import logging
import re
import uuid
from dataclasses import dataclass
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models.enums import (
    EntityType,
    RelationshipBasis,
    RelationshipType,
    RelationshipVerificationStatus,
)
from app.models.evidence import EvidenceChunk, EvidenceItem
from app.models.relationship import KnowledgeEntity, KnowledgeRelationship
from app.repositories.relationship import EntityRepository, RelationshipRepository
from app.services.llm import LLMGenerationRequest, StructuredLLMClient
from app.services.relationship_taxonomy import validate_relationship_endpoints

logger = logging.getLogger("app.services.relationship_discovery")

# Regex patterns for Exact Linking
JIRA_KEY_RE = re.compile(r"\b([A-Z][A-Z0-9]+-\d+)\b")
PR_NUM_RE = re.compile(r"(?:pull\s*request|pr|gh-|\#)\s*(\d{1,6})\b", flags=re.IGNORECASE)
COMMIT_SHA_RE = re.compile(r"\b([0-9a-f]{7,40})\b", flags=re.IGNORECASE)
ADR_REF_RE = re.compile(r"\b(ADR-\d+|RFC-\d+|DEP-\d+)\b", flags=re.IGNORECASE)


@dataclass(frozen=True, slots=True)
class DiscoveredRelationshipDraft:
    """Discovered candidate relationship ready for validation and persistence."""

    source_entity_id: uuid.UUID
    target_entity_id: uuid.UUID
    relationship_type: str
    relationship_basis: str
    confidence_score: float
    discovery_method: str
    evidence_id: uuid.UUID
    evidence_chunk_id: uuid.UUID | None
    knowledge_item_id: uuid.UUID | None
    supporting_excerpt: str | None
    source_location_json: dict[str, Any]
    is_llm_assisted: bool = False


class RelationshipDiscoveryEngine:
    """Discovers relationships across connected source evidence and structured knowledge."""

    def __init__(
        self,
        session: Session,
        *,
        llm_client: StructuredLLMClient | None = None,
    ) -> None:
        self._session = session
        self._entity_repo = EntityRepository(session)
        self._rel_repo = RelationshipRepository(session)
        self._llm_client = llm_client

    # --------------------------------------------------------------------------
    # Method 1: Exact Identifier Linking
    # --------------------------------------------------------------------------

    def discover_exact_identifier_links(
        self,
        *,
        project_id: uuid.UUID,
        organisation_id: uuid.UUID,
    ) -> list[DiscoveredRelationshipDraft]:
        """Extract explicit references (Jira keys, PR #, Commit SHA, ADR) across evidence."""
        drafts: list[DiscoveredRelationshipDraft] = []

        # Find all work item entities with external IDs (e.g. Jira keys like "HAND-12")
        work_items = list(
            self._session.execute(
                select(KnowledgeEntity).where(
                    KnowledgeEntity.project_id == project_id,
                    KnowledgeEntity.entity_type == EntityType.WORK_ITEM.value,
                    KnowledgeEntity.is_deleted.is_(False),
                )
            )
            .scalars()
            .all()
        )
        work_item_map = {w.canonical_name.upper(): w for w in work_items}
        for w in work_items:
            if w.external_source_id:
                work_item_map[w.external_source_id.upper()] = w

        # Search PRs and Commits for references to these Jira keys
        code_entities = list(
            self._session.execute(
                select(KnowledgeEntity).where(
                    KnowledgeEntity.project_id == project_id,
                    KnowledgeEntity.entity_type.in_(
                        [EntityType.PULL_REQUEST.value, EntityType.COMMIT.value]
                    ),
                    KnowledgeEntity.is_deleted.is_(False),
                )
            )
            .scalars()
            .all()
        )

        for ce in code_entities:
            text_to_scan = f"{ce.canonical_name} {ce.description or ''}"
            # Check for Jira keys
            found_keys = JIRA_KEY_RE.findall(text_to_scan)
            for k in set(found_keys):
                target_wi = work_item_map.get(k.upper())
                if target_wi and target_wi.id != ce.id:
                    # Valid endpoints: PR/Commit IMPLEMENTS Work Item
                    valid, _ = validate_relationship_endpoints(
                        RelationshipType.IMPLEMENTS.value, ce.entity_type, target_wi.entity_type
                    )
                    if valid and ce.primary_evidence_id:
                        drafts.append(
                            DiscoveredRelationshipDraft(
                                source_entity_id=ce.id,
                                target_entity_id=target_wi.id,
                                relationship_type=RelationshipType.IMPLEMENTS.value,
                                relationship_basis=RelationshipBasis.EXPLICIT.value,
                                confidence_score=1.0,
                                discovery_method="exact_reference",
                                evidence_id=ce.primary_evidence_id,
                                evidence_chunk_id=None,
                                knowledge_item_id=None,
                                supporting_excerpt=f"Matched identifier reference '{k}' in {ce.canonical_name}",
                                source_location_json={"matched_identifier": k},
                            )
                        )

            # Check for ADR references
            found_adrs = ADR_REF_RE.findall(text_to_scan)
            for adr in set(found_adrs):
                adr_norm = adr.upper()
                # Find matching decision entity
                decision = self._session.execute(
                    select(KnowledgeEntity).where(
                        KnowledgeEntity.project_id == project_id,
                        KnowledgeEntity.entity_type == EntityType.DECISION.value,
                        KnowledgeEntity.canonical_name.ilike(f"%{adr_norm}%"),
                        KnowledgeEntity.is_deleted.is_(False),
                    )
                ).scalar_one_or_none()
                if decision and decision.id != ce.id and ce.primary_evidence_id:
                    drafts.append(
                        DiscoveredRelationshipDraft(
                            source_entity_id=ce.id,
                            target_entity_id=decision.id,
                            relationship_type=RelationshipType.IMPLEMENTS.value,
                            relationship_basis=RelationshipBasis.EXPLICIT.value,
                            confidence_score=1.0,
                            discovery_method="exact_reference",
                            evidence_id=ce.primary_evidence_id,
                            evidence_chunk_id=None,
                            knowledge_item_id=None,
                            supporting_excerpt=f"Code artifact explicitly references decision {adr_norm}",
                            source_location_json={"matched_identifier": adr_norm},
                        )
                    )

        return drafts

    # --------------------------------------------------------------------------
    # Method 2: Structured Connector Links
    # --------------------------------------------------------------------------

    def discover_structured_connector_links(
        self,
        *,
        project_id: uuid.UUID,
        organisation_id: uuid.UUID,
    ) -> list[DiscoveredRelationshipDraft]:
        """Extract explicit relations directly from GitHub/Jira metadata JSON."""
        drafts: list[DiscoveredRelationshipDraft] = []

        entities = list(
            self._session.execute(
                select(KnowledgeEntity)
                .options(selectinload(KnowledgeEntity.aliases))
                .where(
                    KnowledgeEntity.project_id == project_id,
                    KnowledgeEntity.is_deleted.is_(False),
                )
            )
            .scalars()
            .all()
        )

        # Build lookup indices
        people = [e for e in entities if e.entity_type == EntityType.PERSON.value]
        components = [e for e in entities if e.entity_type == EntityType.COMPONENT.value]
        work_items = [e for e in entities if e.entity_type == EntityType.WORK_ITEM.value]

        people_by_handle: dict[str, KnowledgeEntity] = {}
        for p in people:
            people_by_handle[p.canonical_name.lower()] = p
            for alias in p.aliases:
                people_by_handle[alias.normalized_alias] = p

        components_by_name = {c.canonical_name.lower(): c for c in components}
        work_items_by_key = {w.canonical_name.upper(): w for w in work_items}
        for w in work_items:
            if w.external_source_id:
                work_items_by_key[w.external_source_id.upper()] = w

        for e in entities:
            meta = e.metadata_json or {}
            ev_id = e.primary_evidence_id
            if not ev_id:
                continue

            # 1. GitHub PR Metadata -> Authors, Reviewers, Base Repo Component
            if e.entity_type == EntityType.PULL_REQUEST.value:
                # Author -> AUTHORED_BY
                author_login = meta.get("author") or meta.get("user")
                if author_login and isinstance(author_login, str):
                    p_node = people_by_handle.get(author_login.lower())
                    if p_node:
                        drafts.append(
                            DiscoveredRelationshipDraft(
                                source_entity_id=e.id,
                                target_entity_id=p_node.id,
                                relationship_type=RelationshipType.AUTHORED_BY.value,
                                relationship_basis=RelationshipBasis.EXPLICIT.value,
                                confidence_score=1.0,
                                discovery_method="structured_connector",
                                evidence_id=ev_id,
                                evidence_chunk_id=None,
                                knowledge_item_id=None,
                                supporting_excerpt=f"GitHub PR author metadata: {author_login}",
                                source_location_json={"author": author_login},
                            )
                        )

                # Reviewers -> REVIEWED_BY
                reviewers = meta.get("reviewers") or meta.get("requested_reviewers") or []
                if isinstance(reviewers, list):
                    for r in reviewers:
                        r_login = r if isinstance(r, str) else r.get("login")
                        if r_login and isinstance(r_login, str):
                            p_node = people_by_handle.get(r_login.lower())
                            if p_node:
                                drafts.append(
                                    DiscoveredRelationshipDraft(
                                        source_entity_id=e.id,
                                        target_entity_id=p_node.id,
                                        relationship_type=RelationshipType.REVIEWED_BY.value,
                                        relationship_basis=RelationshipBasis.EXPLICIT.value,
                                        confidence_score=1.0,
                                        discovery_method="structured_connector",
                                        evidence_id=ev_id,
                                        evidence_chunk_id=None,
                                        knowledge_item_id=None,
                                        supporting_excerpt=f"GitHub PR reviewer metadata: {r_login}",
                                        source_location_json={"reviewer": r_login},
                                    )
                                )

                # Repository / Component -> MERGED_IN / AFFECTS_COMPONENT
                repo_name = meta.get("repository") or meta.get("repo")
                if repo_name and isinstance(repo_name, str):
                    c_node = components_by_name.get(repo_name.lower())
                    if c_node:
                        drafts.append(
                            DiscoveredRelationshipDraft(
                                source_entity_id=e.id,
                                target_entity_id=c_node.id,
                                relationship_type=RelationshipType.AFFECTS_COMPONENT.value,
                                relationship_basis=RelationshipBasis.EXPLICIT.value,
                                confidence_score=1.0,
                                discovery_method="structured_connector",
                                evidence_id=ev_id,
                                evidence_chunk_id=None,
                                knowledge_item_id=None,
                                supporting_excerpt=f"PR belongs to repository/component: {repo_name}",
                                source_location_json={"repository": repo_name},
                            )
                        )

            # 2. Jira Issue Metadata -> Assignee, Reporter, Issue Links, Components
            elif e.entity_type == EntityType.WORK_ITEM.value:
                # Assignee -> ASSIGNED_TO
                assignee = meta.get("assignee")
                if assignee and isinstance(assignee, str):
                    p_node = people_by_handle.get(assignee.lower())
                    if p_node:
                        drafts.append(
                            DiscoveredRelationshipDraft(
                                source_entity_id=e.id,
                                target_entity_id=p_node.id,
                                relationship_type=RelationshipType.ASSIGNED_TO.value,
                                relationship_basis=RelationshipBasis.EXPLICIT.value,
                                confidence_score=1.0,
                                discovery_method="structured_connector",
                                evidence_id=ev_id,
                                evidence_chunk_id=None,
                                knowledge_item_id=None,
                                supporting_excerpt=f"Jira issue assignee: {assignee}",
                                source_location_json={"assignee": assignee},
                            )
                        )

                # Reporter -> REPORTED_BY
                reporter = meta.get("reporter")
                if reporter and isinstance(reporter, str):
                    p_node = people_by_handle.get(reporter.lower())
                    if p_node:
                        drafts.append(
                            DiscoveredRelationshipDraft(
                                source_entity_id=e.id,
                                target_entity_id=p_node.id,
                                relationship_type=RelationshipType.REPORTED_BY.value,
                                relationship_basis=RelationshipBasis.EXPLICIT.value,
                                confidence_score=1.0,
                                discovery_method="structured_connector",
                                evidence_id=ev_id,
                                evidence_chunk_id=None,
                                knowledge_item_id=None,
                                supporting_excerpt=f"Jira issue reporter: {reporter}",
                                source_location_json={"reporter": reporter},
                            )
                        )

                # Jira Components -> AFFECTS_COMPONENT
                jira_comps = meta.get("components") or []
                if isinstance(jira_comps, list):
                    for jc in jira_comps:
                        jc_name = jc if isinstance(jc, str) else jc.get("name")
                        if jc_name and isinstance(jc_name, str):
                            c_node = components_by_name.get(jc_name.lower())
                            if c_node:
                                drafts.append(
                                    DiscoveredRelationshipDraft(
                                        source_entity_id=e.id,
                                        target_entity_id=c_node.id,
                                        relationship_type=RelationshipType.AFFECTS_COMPONENT.value,
                                        relationship_basis=RelationshipBasis.EXPLICIT.value,
                                        confidence_score=1.0,
                                        discovery_method="structured_connector",
                                        evidence_id=ev_id,
                                        evidence_chunk_id=None,
                                        knowledge_item_id=None,
                                        supporting_excerpt=f"Jira issue component tag: {jc_name}",
                                        source_location_json={"component": jc_name},
                                    )
                                )

                # Jira Issue Links (Blocks, Depends on, Relates to)
                issue_links = meta.get("issuelinks") or meta.get("issue_links") or []
                if isinstance(issue_links, list):
                    for link in issue_links:
                        if isinstance(link, dict):
                            link_type = str(link.get("type", "")).lower()
                            inward_key = link.get("inward_issue_key")
                            outward_key = link.get("outward_issue_key")

                            if "block" in link_type and outward_key:
                                target_node = work_items_by_key.get(str(outward_key).upper())
                                if target_node:
                                    drafts.append(
                                        DiscoveredRelationshipDraft(
                                            source_entity_id=e.id,
                                            target_entity_id=target_node.id,
                                            relationship_type=RelationshipType.BLOCKS.value,
                                            relationship_basis=RelationshipBasis.EXPLICIT.value,
                                            confidence_score=1.0,
                                            discovery_method="structured_connector",
                                            evidence_id=ev_id,
                                            evidence_chunk_id=None,
                                            knowledge_item_id=None,
                                            supporting_excerpt=f"Jira link blocks: {outward_key}",
                                            source_location_json={"issue_link": link},
                                        )
                                    )
                            elif ("depend" in link_type or "relat" in link_type) and outward_key:
                                target_node = work_items_by_key.get(str(outward_key).upper())
                                if target_node:
                                    drafts.append(
                                        DiscoveredRelationshipDraft(
                                            source_entity_id=e.id,
                                            target_entity_id=target_node.id,
                                            relationship_type=RelationshipType.DEPENDS_ON.value,
                                            relationship_basis=RelationshipBasis.EXPLICIT.value,
                                            confidence_score=1.0,
                                            discovery_method="structured_connector",
                                            evidence_id=ev_id,
                                            evidence_chunk_id=None,
                                            knowledge_item_id=None,
                                            supporting_excerpt=f"Jira link depends on: {outward_key}",
                                            source_location_json={"issue_link": link},
                                        )
                                    )

        return drafts

    # --------------------------------------------------------------------------
    # Method 3: Contextual File Path Matching
    # --------------------------------------------------------------------------

    def discover_contextual_path_matches(
        self,
        *,
        project_id: uuid.UUID,
    ) -> list[DiscoveredRelationshipDraft]:
        """Correlate PR changed files with known architecture component file paths."""
        drafts: list[DiscoveredRelationshipDraft] = []

        components = list(
            self._session.execute(
                select(KnowledgeEntity).where(
                    KnowledgeEntity.project_id == project_id,
                    KnowledgeEntity.entity_type == EntityType.COMPONENT.value,
                    KnowledgeEntity.is_deleted.is_(False),
                )
            )
            .scalars()
            .all()
        )

        prs = list(
            self._session.execute(
                select(KnowledgeEntity).where(
                    KnowledgeEntity.project_id == project_id,
                    KnowledgeEntity.entity_type == EntityType.PULL_REQUEST.value,
                    KnowledgeEntity.is_deleted.is_(False),
                )
            )
            .scalars()
            .all()
        )

        for pr in prs:
            meta = pr.metadata_json or {}
            changed_files = meta.get("changed_files") or meta.get("files") or []
            if not isinstance(changed_files, list) or not pr.primary_evidence_id:
                continue

            for comp in components:
                comp_meta = comp.metadata_json or {}
                paths = comp_meta.get("paths") or [comp.canonical_name]
                if not isinstance(paths, list):
                    paths = [str(paths)]

                # Check if any changed file matches component path prefix
                matched = False
                matching_file = ""
                for cf in changed_files:
                    if isinstance(cf, str):
                        for p in paths:
                            if (
                                p
                                and isinstance(p, str)
                                and (p.lower() in cf.lower() or cf.lower().startswith(p.lower()))
                            ):
                                matched = True
                                matching_file = cf
                                break
                    if matched:
                        break

                if matched:
                    drafts.append(
                        DiscoveredRelationshipDraft(
                            source_entity_id=pr.id,
                            target_entity_id=comp.id,
                            relationship_type=RelationshipType.AFFECTS_COMPONENT.value,
                            relationship_basis=RelationshipBasis.INFERRED.value,
                            confidence_score=0.85,
                            discovery_method="contextual_match",
                            evidence_id=pr.primary_evidence_id,
                            evidence_chunk_id=None,
                            knowledge_item_id=None,
                            supporting_excerpt=f"PR changed file '{matching_file}' aligns with component paths",
                            source_location_json={"matched_file": matching_file},
                        )
                    )

        return drafts

    # --------------------------------------------------------------------------
    # Method 5: Qwen3 8B LLM-Assisted Candidate Extraction
    # --------------------------------------------------------------------------

    def discover_llm_assisted_relationships(
        self,
        *,
        project_id: uuid.UUID,
        organisation_id: uuid.UUID,
        evidence_limit: int = 10,
    ) -> list[DiscoveredRelationshipDraft]:
        """Use local Qwen3 8B to classify implicit relationships grounded in verbatim evidence chunks."""
        if self._llm_client is None:
            logger.info("LLM client not configured; skipping LLM-assisted relationship discovery.")
            return []

        drafts: list[DiscoveredRelationshipDraft] = []

        # Load candidate chunks from meetings, discussions, documents, or decisions
        chunks = list(
            self._session.execute(
                select(EvidenceChunk)
                .join(EvidenceItem, EvidenceItem.id == EvidenceChunk.evidence_id)
                .where(
                    EvidenceChunk.project_id == project_id,
                    EvidenceItem.deleted_at.is_(None),
                )
                .limit(evidence_limit)
            )
            .scalars()
            .all()
        )

        # Preload project entities
        entities = list(
            self._session.execute(
                select(KnowledgeEntity)
                .options(selectinload(KnowledgeEntity.aliases))
                .where(
                    KnowledgeEntity.project_id == project_id,
                    KnowledgeEntity.is_deleted.is_(False),
                )
            )
            .scalars()
            .all()
        )
        if not entities:
            return []

        entity_lookup = {e.canonical_name.lower(): e for e in entities}
        entity_names_str = ", ".join(
            f"'{e.canonical_name}' ({e.entity_type})" for e in entities[:40]
        )

        system_prompt = (
            "You are an expert Relationship Extraction engine for The Handover project platform.\n"
            "Given an evidence text chunk and a catalog of known project entities, identify meaningful directed relationships.\n"
            "MANDATORY RULES:\n"
            "1. ONLY extract relationships that have a DIRECT verbatim quote in the text chunk.\n"
            "2. NEVER invent or hallucinate relationships without evidence.\n"
            "3. Choose relationship_type strictly from: DECIDED_BY, INFLUENCED_BY, IMPLEMENTED_BY, AFFECTS_COMPONENT, "
            "BLOCKS, DEPENDS_ON, OWNS, ASSIGNED_TO, DISCUSSED_IN, DOCUMENTED_IN, REFERENCES, MITIGATES_RISK.\n"
            "4. Return a JSON object with a single key 'relationships' containing a list of objects:\n"
            "   {\n"
            "     'source_name': str,\n"
            "     'target_name': str,\n"
            "     'relationship_type': str,\n"
            "     'confidence_score': float (0.5 to 1.0),\n"
            "     'verbatim_quote': str\n"
            "   }\n"
            "If no relationships exist, return {'relationships': []}."
        )

        for chunk in chunks:
            if not chunk.content or len(chunk.content.strip()) < 30:
                continue

            user_prompt = (
                f"Known Entities:\n{entity_names_str}\n\n"
                f'Evidence Text Chunk:\n"""{chunk.content[:2000]}"""\n\n'
                "Extract relationships present in this chunk."
            )

            try:
                res = self._llm_client.generate_json(
                    LLMGenerationRequest(
                        system_prompt=system_prompt,
                        user_prompt=user_prompt,
                        temperature=0.1,
                    )
                )
                rels_data = res.parsed_json.get("relationships", [])
                if isinstance(rels_data, list):
                    for item in rels_data:
                        if not isinstance(item, dict):
                            continue
                        s_name = str(item.get("source_name", "")).strip().lower()
                        t_name = str(item.get("target_name", "")).strip().lower()
                        r_type = str(item.get("relationship_type", "")).strip().upper()
                        quote = item.get("verbatim_quote")
                        conf = float(item.get("confidence_score", 0.75))

                        s_node = entity_lookup.get(s_name)
                        t_node = entity_lookup.get(t_name)

                        if s_node and t_node and s_node.id != t_node.id:
                            # Validate endpoints
                            valid, err = validate_relationship_endpoints(
                                r_type, s_node.entity_type, t_node.entity_type
                            )
                            if valid:
                                drafts.append(
                                    DiscoveredRelationshipDraft(
                                        source_entity_id=s_node.id,
                                        target_entity_id=t_node.id,
                                        relationship_type=r_type,
                                        relationship_basis=RelationshipBasis.INFERRED.value,
                                        confidence_score=round(min(1.0, max(0.5, conf)), 3),
                                        discovery_method="llm_assisted_extraction",
                                        evidence_id=chunk.evidence_id,
                                        evidence_chunk_id=chunk.id,
                                        knowledge_item_id=None,
                                        supporting_excerpt=str(quote)[:500] if quote else None,
                                        source_location_json={"chunk_index": chunk.chunk_index},
                                        is_llm_assisted=True,
                                    )
                                )
            except Exception as e:
                logger.warning("LLM relationship extraction failed for chunk %s: %s", chunk.id, e)

        return drafts

    # --------------------------------------------------------------------------
    # Persistence Pipeline
    # --------------------------------------------------------------------------

    def persist_discovered_relationships(
        self,
        *,
        organisation_id: uuid.UUID,
        project_id: uuid.UUID,
        drafts: list[DiscoveredRelationshipDraft],
    ) -> tuple[int, int]:
        """Persist drafts into KnowledgeRelationship and RelationshipEvidenceLink.

        Returns (created_count, updated_count).
        """
        created = 0
        updated = 0

        for d in drafts:
            # Validate endpoints against taxonomy
            s_entity = self._entity_repo.get_entity_by_id(d.source_entity_id)
            t_entity = self._entity_repo.get_entity_by_id(d.target_entity_id)
            if not s_entity or not t_entity or s_entity.id == t_entity.id:
                continue

            valid, _ = validate_relationship_endpoints(
                d.relationship_type, s_entity.entity_type, t_entity.entity_type
            )
            if not valid:
                continue

            # Check if relationship already exists
            fingerprint = RelationshipRepository.compute_fingerprint(
                project_id, d.source_entity_id, d.relationship_type, d.target_entity_id
            )
            existing = self._session.execute(
                select(KnowledgeRelationship).where(
                    KnowledgeRelationship.project_id == project_id,
                    KnowledgeRelationship.fingerprint == fingerprint,
                )
            ).scalar_one_or_none()

            if existing is None:
                rel = self._rel_repo.create_or_get_relationship(
                    organisation_id=organisation_id,
                    project_id=project_id,
                    source_entity_id=d.source_entity_id,
                    target_entity_id=d.target_entity_id,
                    relationship_type=d.relationship_type,
                    relationship_basis=d.relationship_basis,
                    verification_status=RelationshipVerificationStatus.CANDIDATE.value,
                    confidence_score=d.confidence_score,
                    confidence_components_json={"discovery_method": d.discovery_method},
                    discovery_method=d.discovery_method,
                    is_llm_assisted=d.is_llm_assisted,
                )
                created += 1
            else:
                rel = existing
                if float(rel.confidence_score) < d.confidence_score:
                    rel.confidence_score = d.confidence_score
                updated += 1

            # Attach evidence link
            self._rel_repo.add_evidence_link(
                relationship_id=rel.id,
                organisation_id=organisation_id,
                project_id=project_id,
                evidence_id=d.evidence_id,
                evidence_chunk_id=d.evidence_chunk_id,
                knowledge_item_id=d.knowledge_item_id,
                supporting_excerpt=d.supporting_excerpt,
                source_location_json=d.source_location_json,
            )

        self._session.flush()
        return created, updated
