"""Data-access repository for Relationship Explorer knowledge graph.

Manages:
- Knowledge entities (nodes across 13 types)
- Entity aliases and cross-source identity handles
- Identity resolution candidates (reversible merge pairs)
- Knowledge relationships (typed, directed graph edges with dual classification)
- Relationship evidence links (mandatory provenance citations)
- Decision traceability chains (5-stage Decision -> Work item -> PR -> Commit -> Component)
- Knowledge timeline events (chronological project event log)
- Relationship reconstruction runs (async worker execution lifecycle)

Enforces strict fail-closed source ACL checks at query time.
"""

from __future__ import annotations

import hashlib
import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import and_, exists, func, or_, select
from sqlalchemy.orm import Session, joinedload, selectinload

from app.core.security import utc_now
from app.models.enums import (
    EntityResolutionStatus,
    EvidenceProcessingStatus,
    EvidenceSourceType,
    IdentityCandidateStatus,
    IdentityPolicyBand,
    RelationshipBasis,
    RelationshipEvidenceRole,
    RelationshipRunStatus,
    RelationshipVerificationStatus,
    SourcePermissionVerificationStatus,
    TimelineOrigin,
    TimelinePrecision,
)
from app.models.evidence import EvidenceItem
from app.models.integration import SourceAccessPolicy
from app.models.relationship import (
    DecisionTraceabilityChain,
    EntityAlias,
    IdentityResolutionCandidate,
    KnowledgeEntity,
    KnowledgeRelationship,
    KnowledgeTimelineEvent,
    RelationshipEvidenceLink,
    RelationshipReconstructionRun,
)
from app.services.integrations.access_policy import SourceAccessPolicyService

# ==============================================================================
# Helper ACL Methods
# ==============================================================================


def _get_allowed_and_revoked_policies(
    session: Session,
    *,
    project_id: uuid.UUID,
    viewer_user_id: uuid.UUID,
) -> tuple[list[uuid.UUID], list[uuid.UUID]]:
    policies = list(
        session.execute(
            select(SourceAccessPolicy).where(SourceAccessPolicy.project_id == project_id)
        )
        .scalars()
        .all()
    )
    viewer_str = str(viewer_user_id)
    allowed_ids: list[uuid.UUID] = []
    revoked_ids: list[uuid.UUID] = []
    for policy in policies:
        if policy.sync_permission_status == SourcePermissionVerificationStatus.REVOKED.value:
            revoked_ids.append(policy.id)
            continue
        if viewer_str in (policy.allowed_user_ids or []):
            allowed_ids.append(policy.id)
    return allowed_ids, revoked_ids


def _build_accessible_evidence_clause(
    session: Session,
    *,
    project_id: uuid.UUID,
    viewer_user_id: uuid.UUID,
    has_project_manage: bool,
) -> Any:
    allowed_policy_ids, revoked_policy_ids = _get_allowed_and_revoked_policies(
        session,
        project_id=project_id,
        viewer_user_id=viewer_user_id,
    )
    public_clause = (
        and_(
            EvidenceItem.acl_scope == "project_members",
            or_(
                EvidenceItem.source_access_policy_id.is_(None),
                EvidenceItem.source_access_policy_id.notin_(revoked_policy_ids),
            ),
        )
        if revoked_policy_ids
        else EvidenceItem.acl_scope == "project_members"
    )
    clauses: list[Any] = [public_clause]
    if allowed_policy_ids:
        clauses.append(
            and_(
                EvidenceItem.acl_scope == "source_restricted",
                EvidenceItem.source_access_policy_id.in_(allowed_policy_ids),
            )
        )
    if has_project_manage:
        clauses.append(
            and_(
                EvidenceItem.acl_scope == "source_restricted",
                EvidenceItem.source_type == EvidenceSourceType.DOCUMENT_UPLOAD.value,
                EvidenceItem.source_access_policy_id.is_(None),
                EvidenceItem.source_connection_id.is_(None),
            )
        )
    else:
        clauses.append(
            and_(
                EvidenceItem.acl_scope == "source_restricted",
                EvidenceItem.source_type == EvidenceSourceType.DOCUMENT_UPLOAD.value,
                EvidenceItem.source_access_policy_id.is_(None),
                EvidenceItem.source_connection_id.is_(None),
                EvidenceItem.uploaded_by_user_id == viewer_user_id,
            )
        )
    return or_(*clauses)


# ==============================================================================
# EntityRepository
# ==============================================================================


class EntityRepository:
    """Data-access repository for knowledge entities, aliases, and identity candidates."""

    def __init__(self, session: Session) -> None:
        self._session = session
        self._access_policy = SourceAccessPolicyService()

    def create_or_get_entity(
        self,
        *,
        organisation_id: uuid.UUID,
        project_id: uuid.UUID,
        entity_type: str,
        canonical_name: str,
        description: str | None = None,
        primary_knowledge_item_id: uuid.UUID | None = None,
        primary_evidence_id: uuid.UUID | None = None,
        external_source_id: str | None = None,
        source_provider: str | None = None,
        confidence_score: float = 1.0,
        metadata_json: dict[str, Any] | None = None,
        first_observed_at: datetime | None = None,
        last_observed_at: datetime | None = None,
        is_synthetic: bool = False,
    ) -> KnowledgeEntity:
        norm_name = canonical_name.strip().lower()
        stmt = select(KnowledgeEntity).where(
            KnowledgeEntity.project_id == project_id,
            KnowledgeEntity.entity_type == entity_type,
            KnowledgeEntity.normalized_name == norm_name,
            KnowledgeEntity.is_deleted.is_(False),
        )
        existing = self._session.execute(stmt).scalar_one_or_none()
        if existing is not None:
            if last_observed_at and (
                not existing.last_observed_at or last_observed_at > existing.last_observed_at
            ):
                existing.last_observed_at = last_observed_at
            if metadata_json:
                merged_meta = dict(existing.metadata_json or {})
                merged_meta.update(metadata_json)
                existing.metadata_json = merged_meta
            return existing

        entity = KnowledgeEntity(
            organisation_id=organisation_id,
            project_id=project_id,
            entity_type=entity_type,
            canonical_name=canonical_name.strip(),
            normalized_name=norm_name,
            description=description,
            primary_knowledge_item_id=primary_knowledge_item_id,
            primary_evidence_id=primary_evidence_id,
            external_source_id=external_source_id,
            source_provider=source_provider,
            confidence_score=confidence_score,
            metadata_json=metadata_json or {},
            first_observed_at=first_observed_at or utc_now(),
            last_observed_at=last_observed_at or utc_now(),
            is_synthetic=is_synthetic,
        )
        self._session.add(entity)
        self._session.flush()
        return entity

    def get_entity_by_id(
        self,
        entity_id: uuid.UUID,
        *,
        project_id: uuid.UUID | None = None,
    ) -> KnowledgeEntity | None:
        stmt = (
            select(KnowledgeEntity)
            .options(selectinload(KnowledgeEntity.aliases))
            .where(
                KnowledgeEntity.id == entity_id,
                KnowledgeEntity.is_deleted.is_(False),
            )
        )
        if project_id is not None:
            stmt = stmt.where(KnowledgeEntity.project_id == project_id)
        return self._session.execute(stmt).scalar_one_or_none()

    def get_accessible_entity(
        self,
        entity_id: uuid.UUID,
        *,
        project_id: uuid.UUID,
        viewer_user_id: uuid.UUID,
        has_project_manage: bool,
    ) -> tuple[KnowledgeEntity | None, bool]:
        """Return (entity, denied_by_acl).

        If entity does not exist: returns (None, False).
        If entity's primary evidence is restricted and inaccessible: returns (entity, True).
        """
        entity = self.get_entity_by_id(entity_id, project_id=project_id)
        if entity is None:
            return None, False

        if entity.primary_evidence_id is not None:
            ev = self._session.get(EvidenceItem, entity.primary_evidence_id)
            if ev and not self._access_policy.can_user_access_evidence(
                evidence=ev,
                user_id=viewer_user_id,
                has_project_manage=has_project_manage,
            ):
                return entity, True

        return entity, False

    def list_accessible_entities(
        self,
        *,
        project_id: uuid.UUID,
        viewer_user_id: uuid.UUID,
        has_project_manage: bool,
        entity_type: str | None = None,
        resolution_status: str | None = None,
        query: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[KnowledgeEntity], int]:
        filters: list[Any] = [
            KnowledgeEntity.project_id == project_id,
            KnowledgeEntity.is_deleted.is_(False),
        ]
        if entity_type:
            filters.append(KnowledgeEntity.entity_type == entity_type)
        if resolution_status:
            filters.append(KnowledgeEntity.resolution_status == resolution_status)
        if query:
            q_like = f"%{query.strip().lower()}%"
            filters.append(KnowledgeEntity.normalized_name.ilike(q_like))

        # Check evidence access: if primary_evidence_id is set, it must satisfy ACL
        acl_clause = _build_accessible_evidence_clause(
            self._session,
            project_id=project_id,
            viewer_user_id=viewer_user_id,
            has_project_manage=has_project_manage,
        )
        accessible_ev_exists = exists(
            select(EvidenceItem.id).where(
                EvidenceItem.id == KnowledgeEntity.primary_evidence_id,
                acl_clause,
                EvidenceItem.deleted_at.is_(None),
                EvidenceItem.processing_status != EvidenceProcessingStatus.DELETED.value,
            )
        )
        filters.append(
            or_(
                KnowledgeEntity.primary_evidence_id.is_(None),
                accessible_ev_exists,
            )
        )

        total_stmt = select(func.count(KnowledgeEntity.id)).where(and_(*filters))
        total = int(self._session.execute(total_stmt).scalar() or 0)

        data_stmt = (
            select(KnowledgeEntity)
            .options(selectinload(KnowledgeEntity.aliases))
            .where(and_(*filters))
            .order_by(KnowledgeEntity.canonical_name.asc())
            .limit(limit)
            .offset(offset)
        )
        rows = list(self._session.execute(data_stmt).scalars().all())
        return rows, total

    # Aliases
    def add_alias(
        self,
        *,
        entity_id: uuid.UUID,
        organisation_id: uuid.UUID,
        project_id: uuid.UUID,
        alias_value: str,
        source_provider: str,
        alias_kind: str = "display_name",
        source_external_id: str | None = None,
        confidence_score: float = 1.0,
        is_synthetic: bool = False,
    ) -> EntityAlias:
        norm_alias = alias_value.strip().lower()
        stmt = select(EntityAlias).where(
            EntityAlias.entity_id == entity_id,
            EntityAlias.normalized_alias == norm_alias,
            EntityAlias.source_provider == source_provider,
        )
        existing = self._session.execute(stmt).scalar_one_or_none()
        if existing is not None:
            return existing

        alias = EntityAlias(
            entity_id=entity_id,
            organisation_id=organisation_id,
            project_id=project_id,
            alias_value=alias_value.strip(),
            normalized_alias=norm_alias,
            alias_kind=alias_kind,
            source_provider=source_provider,
            source_external_id=source_external_id,
            confidence_score=confidence_score,
            is_synthetic=is_synthetic,
        )
        self._session.add(alias)
        self._session.flush()
        return alias

    def find_entity_by_alias(
        self,
        *,
        project_id: uuid.UUID,
        alias_value: str,
        source_provider: str | None = None,
    ) -> KnowledgeEntity | None:
        norm = alias_value.strip().lower()
        stmt = (
            select(KnowledgeEntity)
            .join(EntityAlias, EntityAlias.entity_id == KnowledgeEntity.id)
            .where(
                EntityAlias.project_id == project_id,
                EntityAlias.normalized_alias == norm,
                KnowledgeEntity.is_deleted.is_(False),
            )
        )
        if source_provider:
            stmt = stmt.where(EntityAlias.source_provider == source_provider)
        return self._session.execute(stmt).scalar_one_or_none()

    # Identity Candidates
    def create_identity_candidate(
        self,
        *,
        organisation_id: uuid.UUID,
        project_id: uuid.UUID,
        left_entity_id: uuid.UUID,
        right_entity_id: uuid.UUID,
        match_score: float,
        signal_breakdown_json: dict[str, Any],
        policy_band: str = IdentityPolicyBand.MANUAL_REVIEW.value,
        is_synthetic: bool = False,
    ) -> IdentityResolutionCandidate:
        # Canonical order to prevent duplicate mirrored pairs
        if str(left_entity_id) > str(right_entity_id):
            left_entity_id, right_entity_id = right_entity_id, left_entity_id

        stmt = select(IdentityResolutionCandidate).where(
            IdentityResolutionCandidate.project_id == project_id,
            IdentityResolutionCandidate.left_entity_id == left_entity_id,
            IdentityResolutionCandidate.right_entity_id == right_entity_id,
        )
        existing = self._session.execute(stmt).scalar_one_or_none()
        if existing is not None:
            existing.match_score = match_score
            existing.signal_breakdown_json = signal_breakdown_json
            existing.policy_band = policy_band
            return existing

        cand = IdentityResolutionCandidate(
            organisation_id=organisation_id,
            project_id=project_id,
            left_entity_id=left_entity_id,
            right_entity_id=right_entity_id,
            match_score=match_score,
            signal_breakdown_json=signal_breakdown_json,
            policy_band=policy_band,
            is_synthetic=is_synthetic,
        )
        self._session.add(cand)
        self._session.flush()
        return cand

    def list_identity_candidates(
        self,
        *,
        project_id: uuid.UUID,
        decision_status: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[IdentityResolutionCandidate], int]:
        filters: list[Any] = [IdentityResolutionCandidate.project_id == project_id]
        if decision_status:
            filters.append(IdentityResolutionCandidate.decision_status == decision_status)

        total_stmt = select(func.count(IdentityResolutionCandidate.id)).where(and_(*filters))
        total = int(self._session.execute(total_stmt).scalar() or 0)

        data_stmt = (
            select(IdentityResolutionCandidate)
            .where(and_(*filters))
            .order_by(IdentityResolutionCandidate.match_score.desc())
            .limit(limit)
            .offset(offset)
        )
        rows = list(self._session.execute(data_stmt).scalars().all())
        return rows, total

    def get_identity_candidate(
        self,
        candidate_id: uuid.UUID,
        *,
        project_id: uuid.UUID | None = None,
    ) -> IdentityResolutionCandidate | None:
        stmt = select(IdentityResolutionCandidate).where(
            IdentityResolutionCandidate.id == candidate_id
        )
        if project_id is not None:
            stmt = stmt.where(IdentityResolutionCandidate.project_id == project_id)
        return self._session.execute(stmt).scalar_one_or_none()

    def review_identity_candidate(
        self,
        candidate_id: uuid.UUID,
        *,
        user_id: uuid.UUID,
        action: str,  # 'accept' or 'reject'
        rationale: str | None = None,
    ) -> IdentityResolutionCandidate:
        candidate = self.get_identity_candidate(candidate_id)
        if candidate is None:
            raise ValueError(f"Candidate {candidate_id} not found")

        candidate.decided_by_user_id = user_id
        candidate.decided_at = utc_now()
        candidate.decision_rationale = rationale

        if action == "accept":
            candidate.decision_status = IdentityCandidateStatus.ACCEPTED.value
            left_entity = self.get_entity_by_id(candidate.left_entity_id)
            right_entity = self.get_entity_by_id(candidate.right_entity_id)
            if left_entity and right_entity:
                # Capture previous state for reversibility
                candidate.previous_state_json = {
                    "right_entity_id": str(right_entity.id),
                    "resolution_status": right_entity.resolution_status,
                    "merged_into_entity_id": str(right_entity.merged_into_entity_id)
                    if right_entity.merged_into_entity_id
                    else None,
                }
                right_entity.resolution_status = EntityResolutionStatus.MERGED.value
                right_entity.merged_into_entity_id = left_entity.id
        elif action == "reject":
            candidate.decision_status = IdentityCandidateStatus.REJECTED.value
        else:
            raise ValueError(f"Unknown review action: {action}")

        self._session.flush()
        return candidate

    def revert_identity_candidate(
        self,
        candidate_id: uuid.UUID,
        *,
        user_id: uuid.UUID,
        rationale: str | None = None,
    ) -> IdentityResolutionCandidate:
        candidate = self.get_identity_candidate(candidate_id)
        if candidate is None:
            raise ValueError(f"Candidate {candidate_id} not found")

        if candidate.decision_status != IdentityCandidateStatus.ACCEPTED.value:
            raise ValueError("Only accepted merges can be reverted")

        right_entity = self.get_entity_by_id(candidate.right_entity_id)
        if right_entity and candidate.previous_state_json:
            right_entity.resolution_status = candidate.previous_state_json.get(
                "resolution_status", EntityResolutionStatus.CANONICAL.value
            )
            prev_merged = candidate.previous_state_json.get("merged_into_entity_id")
            right_entity.merged_into_entity_id = uuid.UUID(prev_merged) if prev_merged else None

        candidate.decision_status = IdentityCandidateStatus.REVERTED.value
        candidate.decided_by_user_id = user_id
        candidate.decided_at = utc_now()
        if rationale:
            candidate.decision_rationale = (
                f"{candidate.decision_rationale or ''}\n[REVERTED]: {rationale}".strip()
            )

        self._session.flush()
        return candidate


# ==============================================================================
# RelationshipRepository
# ==============================================================================


class RelationshipRepository:
    """Data-access repository for knowledge relationships and verifiable evidence links."""

    def __init__(self, session: Session) -> None:
        self._session = session
        self._access_policy = SourceAccessPolicyService()

    @staticmethod
    def compute_fingerprint(
        project_id: uuid.UUID,
        source_entity_id: uuid.UUID,
        relationship_type: str,
        target_entity_id: uuid.UUID,
    ) -> str:
        raw = f"{project_id}:{source_entity_id}:{relationship_type.strip().lower()}:{target_entity_id}"
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()

    def create_or_get_relationship(
        self,
        *,
        organisation_id: uuid.UUID,
        project_id: uuid.UUID,
        source_entity_id: uuid.UUID,
        target_entity_id: uuid.UUID,
        relationship_type: str,
        relationship_basis: str = RelationshipBasis.EXPLICIT.value,
        verification_status: str = RelationshipVerificationStatus.CANDIDATE.value,
        confidence_score: float = 1.0,
        confidence_components_json: dict[str, Any] | None = None,
        discovery_method: str = "exact_reference",
        is_bidirectional_display: bool = False,
        is_llm_assisted: bool = False,
        first_observed_at: datetime | None = None,
        last_observed_at: datetime | None = None,
        is_synthetic: bool = False,
    ) -> KnowledgeRelationship:
        fingerprint = self.compute_fingerprint(
            project_id, source_entity_id, relationship_type, target_entity_id
        )
        stmt = select(KnowledgeRelationship).where(
            KnowledgeRelationship.project_id == project_id,
            KnowledgeRelationship.fingerprint == fingerprint,
        )
        existing = self._session.execute(stmt).scalar_one_or_none()
        if existing is not None:
            if float(existing.confidence_score) < confidence_score:
                existing.confidence_score = confidence_score
            if last_observed_at and (
                not existing.last_observed_at or last_observed_at > existing.last_observed_at
            ):
                existing.last_observed_at = last_observed_at
            return existing

        rel = KnowledgeRelationship(
            organisation_id=organisation_id,
            project_id=project_id,
            source_entity_id=source_entity_id,
            target_entity_id=target_entity_id,
            relationship_type=relationship_type,
            relationship_basis=relationship_basis,
            verification_status=verification_status,
            confidence_score=confidence_score,
            confidence_components_json=confidence_components_json or {},
            discovery_method=discovery_method,
            is_bidirectional_display=is_bidirectional_display,
            is_llm_assisted=is_llm_assisted,
            fingerprint=fingerprint,
            first_observed_at=first_observed_at or utc_now(),
            last_observed_at=last_observed_at or utc_now(),
            is_synthetic=is_synthetic,
        )
        self._session.add(rel)
        self._session.flush()
        return rel

    def add_evidence_link(
        self,
        *,
        relationship_id: uuid.UUID,
        organisation_id: uuid.UUID,
        project_id: uuid.UUID,
        evidence_id: uuid.UUID,
        evidence_chunk_id: uuid.UUID | None = None,
        knowledge_item_id: uuid.UUID | None = None,
        evidence_role: str = RelationshipEvidenceRole.DIRECT_SUPPORT.value,
        supporting_excerpt: str | None = None,
        source_location_json: dict[str, Any] | None = None,
        is_synthetic: bool = False,
    ) -> RelationshipEvidenceLink:
        stmt = select(RelationshipEvidenceLink).where(
            RelationshipEvidenceLink.relationship_id == relationship_id,
            RelationshipEvidenceLink.evidence_id == evidence_id,
        )
        if evidence_chunk_id is not None:
            stmt = stmt.where(RelationshipEvidenceLink.evidence_chunk_id == evidence_chunk_id)
        existing = self._session.execute(stmt).scalar_one_or_none()
        if existing is not None:
            return existing

        link = RelationshipEvidenceLink(
            relationship_id=relationship_id,
            organisation_id=organisation_id,
            project_id=project_id,
            evidence_id=evidence_id,
            evidence_chunk_id=evidence_chunk_id,
            knowledge_item_id=knowledge_item_id,
            evidence_role=evidence_role,
            supporting_excerpt=supporting_excerpt,
            source_location_json=source_location_json or {},
            is_synthetic=is_synthetic,
        )
        self._session.add(link)
        self._session.flush()
        return link

    def get_relationship_by_id(
        self,
        relationship_id: uuid.UUID,
        *,
        project_id: uuid.UUID | None = None,
    ) -> KnowledgeRelationship | None:
        stmt = (
            select(KnowledgeRelationship)
            .options(
                joinedload(KnowledgeRelationship.source_entity),
                joinedload(KnowledgeRelationship.target_entity),
                selectinload(KnowledgeRelationship.evidence_links),
            )
            .where(KnowledgeRelationship.id == relationship_id)
        )
        if project_id is not None:
            stmt = stmt.where(KnowledgeRelationship.project_id == project_id)
        return self._session.execute(stmt).unique().scalar_one_or_none()

    def get_accessible_relationship(
        self,
        relationship_id: uuid.UUID,
        *,
        project_id: uuid.UUID,
        viewer_user_id: uuid.UUID,
        has_project_manage: bool,
    ) -> tuple[KnowledgeRelationship | None, tuple[RelationshipEvidenceLink, ...], bool]:
        """Return (relationship, accessible_links, denied_by_acl).

        If rel not found: returns (None, (), False).
        If rel exists but all supporting evidence links are inaccessible: returns (rel, (), True).
        """
        rel = self.get_relationship_by_id(relationship_id, project_id=project_id)
        if rel is None:
            return None, (), False

        # Filter accessible links
        accessible_links: list[RelationshipEvidenceLink] = []
        for link in rel.evidence_links:
            ev = self._session.get(EvidenceItem, link.evidence_id)
            if (
                ev
                and not ev.deleted_at
                and ev.processing_status != EvidenceProcessingStatus.DELETED.value
            ):
                if self._access_policy.can_user_access_evidence(
                    evidence=ev,
                    user_id=viewer_user_id,
                    has_project_manage=has_project_manage,
                ):
                    accessible_links.append(link)

        if not accessible_links:
            return rel, (), True

        return rel, tuple(accessible_links), False

    def list_accessible_relationships(
        self,
        *,
        project_id: uuid.UUID,
        viewer_user_id: uuid.UUID,
        has_project_manage: bool,
        relationship_type: str | None = None,
        relationship_basis: str | None = None,
        verification_status: str | None = None,
        entity_id: uuid.UUID | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> tuple[list[KnowledgeRelationship], int]:
        filters: list[Any] = [KnowledgeRelationship.project_id == project_id]
        if relationship_type:
            filters.append(KnowledgeRelationship.relationship_type == relationship_type)
        if relationship_basis:
            filters.append(KnowledgeRelationship.relationship_basis == relationship_basis)
        if verification_status:
            filters.append(KnowledgeRelationship.verification_status == verification_status)
        if entity_id:
            filters.append(
                or_(
                    KnowledgeRelationship.source_entity_id == entity_id,
                    KnowledgeRelationship.target_entity_id == entity_id,
                )
            )

        # Enforce that at least one evidence link is accessible to viewer
        acl_clause = _build_accessible_evidence_clause(
            self._session,
            project_id=project_id,
            viewer_user_id=viewer_user_id,
            has_project_manage=has_project_manage,
        )
        accessible_link_exists = exists(
            select(RelationshipEvidenceLink.id)
            .join(EvidenceItem, EvidenceItem.id == RelationshipEvidenceLink.evidence_id)
            .where(
                RelationshipEvidenceLink.relationship_id == KnowledgeRelationship.id,
                acl_clause,
                EvidenceItem.deleted_at.is_(None),
                EvidenceItem.processing_status != EvidenceProcessingStatus.DELETED.value,
            )
        )
        filters.append(accessible_link_exists)

        total_stmt = select(func.count(KnowledgeRelationship.id)).where(and_(*filters))
        total = int(self._session.execute(total_stmt).scalar() or 0)

        data_stmt = (
            select(KnowledgeRelationship)
            .options(
                joinedload(KnowledgeRelationship.source_entity),
                joinedload(KnowledgeRelationship.target_entity),
                selectinload(KnowledgeRelationship.evidence_links),
            )
            .where(and_(*filters))
            .order_by(KnowledgeRelationship.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        rows = list(self._session.execute(data_stmt).unique().scalars().all())
        return rows, total

    def review_relationship(
        self,
        relationship_id: uuid.UUID,
        *,
        user_id: uuid.UUID,
        action: str,  # 'verify', 'reject', 'dispute', 'request_evidence'
        note: str | None = None,
    ) -> KnowledgeRelationship:
        rel = self.get_relationship_by_id(relationship_id)
        if rel is None:
            raise ValueError(f"Relationship {relationship_id} not found")

        rel.reviewed_by_user_id = user_id
        rel.reviewed_at = utc_now()
        rel.review_note = note

        if action == "verify":
            rel.verification_status = RelationshipVerificationStatus.VERIFIED.value
            rel.relationship_basis = RelationshipBasis.HUMAN_CONFIRMED.value
        elif action == "reject":
            rel.verification_status = RelationshipVerificationStatus.REJECTED.value
        elif action == "dispute":
            rel.verification_status = RelationshipVerificationStatus.CONFLICTED.value
        elif action == "request_evidence":
            rel.verification_status = RelationshipVerificationStatus.UNRESOLVED.value
        else:
            raise ValueError(f"Unknown relationship review action: {action}")

        self._session.flush()
        return rel

    def mark_stale_for_evidence(self, *, evidence_id: uuid.UUID, reason: str) -> int:
        stmt = (
            select(KnowledgeRelationship)
            .join(
                RelationshipEvidenceLink,
                RelationshipEvidenceLink.relationship_id == KnowledgeRelationship.id,
            )
            .where(RelationshipEvidenceLink.evidence_id == evidence_id)
        )
        rels = list(self._session.execute(stmt).scalars().all())
        for rel in rels:
            rel.is_stale = True
            rel.stale_reason = reason[:255]
        if rels:
            self._session.flush()
        return len(rels)


# ==============================================================================
# TraceabilityRepository
# ==============================================================================


class TraceabilityRepository:
    """Data-access repository for Decision Traceability Chains."""

    def __init__(self, session: Session) -> None:
        self._session = session
        self._access_policy = SourceAccessPolicyService()

    def create_or_update_chain(
        self,
        *,
        organisation_id: uuid.UUID,
        project_id: uuid.UUID,
        decision_entity_id: uuid.UUID,
        completeness_status: str,
        work_item_ids_json: list[str],
        pull_request_ids_json: list[str],
        commit_ids_json: list[str],
        component_ids_json: list[str],
        relationship_ids_json: list[str],
        missing_links_json: list[str],
        uncertainty_reasons_json: list[str],
        aggregate_confidence: float = 1.0,
        earliest_event_at: datetime | None = None,
        latest_event_at: datetime | None = None,
        is_synthetic: bool = False,
    ) -> DecisionTraceabilityChain:
        stmt = select(DecisionTraceabilityChain).where(
            DecisionTraceabilityChain.project_id == project_id,
            DecisionTraceabilityChain.decision_entity_id == decision_entity_id,
        )
        existing = self._session.execute(stmt).scalar_one_or_none()
        if existing is not None:
            existing.completeness_status = completeness_status
            existing.work_item_ids_json = work_item_ids_json
            existing.pull_request_ids_json = pull_request_ids_json
            existing.commit_ids_json = commit_ids_json
            existing.component_ids_json = component_ids_json
            existing.relationship_ids_json = relationship_ids_json
            existing.missing_links_json = missing_links_json
            existing.uncertainty_reasons_json = uncertainty_reasons_json
            existing.aggregate_confidence = aggregate_confidence
            existing.earliest_event_at = earliest_event_at
            existing.latest_event_at = latest_event_at
            return existing

        chain = DecisionTraceabilityChain(
            organisation_id=organisation_id,
            project_id=project_id,
            decision_entity_id=decision_entity_id,
            completeness_status=completeness_status,
            work_item_ids_json=work_item_ids_json,
            pull_request_ids_json=pull_request_ids_json,
            commit_ids_json=commit_ids_json,
            component_ids_json=component_ids_json,
            relationship_ids_json=relationship_ids_json,
            missing_links_json=missing_links_json,
            uncertainty_reasons_json=uncertainty_reasons_json,
            aggregate_confidence=aggregate_confidence,
            earliest_event_at=earliest_event_at,
            latest_event_at=latest_event_at,
            is_synthetic=is_synthetic,
        )
        self._session.add(chain)
        self._session.flush()
        return chain

    def get_chain_by_decision(
        self,
        *,
        project_id: uuid.UUID,
        decision_entity_id: uuid.UUID,
    ) -> DecisionTraceabilityChain | None:
        stmt = select(DecisionTraceabilityChain).where(
            DecisionTraceabilityChain.project_id == project_id,
            DecisionTraceabilityChain.decision_entity_id == decision_entity_id,
        )
        return self._session.execute(stmt).scalar_one_or_none()

    def list_accessible_chains(
        self,
        *,
        project_id: uuid.UUID,
        viewer_user_id: uuid.UUID,
        has_project_manage: bool,
        completeness_status: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[DecisionTraceabilityChain], int]:
        filters: list[Any] = [DecisionTraceabilityChain.project_id == project_id]
        if completeness_status:
            filters.append(DecisionTraceabilityChain.completeness_status == completeness_status)

        # Ensure decision entity is accessible
        acl_clause = _build_accessible_evidence_clause(
            self._session,
            project_id=project_id,
            viewer_user_id=viewer_user_id,
            has_project_manage=has_project_manage,
        )
        accessible_decision_exists = exists(
            select(KnowledgeEntity.id).where(
                KnowledgeEntity.id == DecisionTraceabilityChain.decision_entity_id,
                KnowledgeEntity.is_deleted.is_(False),
                or_(
                    KnowledgeEntity.primary_evidence_id.is_(None),
                    exists(
                        select(EvidenceItem.id).where(
                            EvidenceItem.id == KnowledgeEntity.primary_evidence_id,
                            acl_clause,
                            EvidenceItem.deleted_at.is_(None),
                            EvidenceItem.processing_status
                            != EvidenceProcessingStatus.DELETED.value,
                        )
                    ),
                ),
            )
        )
        filters.append(accessible_decision_exists)

        total_stmt = select(func.count(DecisionTraceabilityChain.id)).where(and_(*filters))
        total = int(self._session.execute(total_stmt).scalar() or 0)

        data_stmt = (
            select(DecisionTraceabilityChain)
            .where(and_(*filters))
            .order_by(DecisionTraceabilityChain.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        rows = list(self._session.execute(data_stmt).scalars().all())
        return rows, total


# ==============================================================================
# TimelineRepository
# ==============================================================================


class TimelineRepository:
    """Data-access repository for Knowledge Timeline Events."""

    def __init__(self, session: Session) -> None:
        self._session = session
        self._access_policy = SourceAccessPolicyService()

    @staticmethod
    def compute_event_fingerprint(
        project_id: uuid.UUID,
        entity_id: uuid.UUID,
        event_type: str,
        occurred_at: datetime | None,
    ) -> str:
        ts = occurred_at.isoformat() if occurred_at else "none"
        raw = f"{project_id}:{entity_id}:{event_type}:{ts}"
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()

    def create_event(
        self,
        *,
        organisation_id: uuid.UUID,
        project_id: uuid.UUID,
        entity_id: uuid.UUID,
        evidence_id: uuid.UUID,
        event_type: str,
        title: str,
        summary: str | None = None,
        occurred_at: datetime | None = None,
        timestamp_precision: str = TimelinePrecision.EXACT_DATETIME.value,
        timestamp_origin: str = TimelineOrigin.SOURCE_API.value,
        secondary_entity_id: uuid.UUID | None = None,
        relationship_id: uuid.UUID | None = None,
        is_synthetic: bool = False,
    ) -> KnowledgeTimelineEvent:
        fingerprint = self.compute_event_fingerprint(project_id, entity_id, event_type, occurred_at)
        stmt = select(KnowledgeTimelineEvent).where(
            KnowledgeTimelineEvent.project_id == project_id,
            KnowledgeTimelineEvent.event_fingerprint == fingerprint,
        )
        existing = self._session.execute(stmt).scalar_one_or_none()
        if existing is not None:
            return existing

        evt = KnowledgeTimelineEvent(
            organisation_id=organisation_id,
            project_id=project_id,
            entity_id=entity_id,
            secondary_entity_id=secondary_entity_id,
            relationship_id=relationship_id,
            evidence_id=evidence_id,
            event_type=event_type,
            title=title.strip(),
            summary=summary,
            occurred_at=occurred_at,
            timestamp_precision=timestamp_precision,
            timestamp_origin=timestamp_origin,
            event_fingerprint=fingerprint,
            is_synthetic=is_synthetic,
        )
        self._session.add(evt)
        self._session.flush()
        return evt

    def list_accessible_events(
        self,
        *,
        project_id: uuid.UUID,
        viewer_user_id: uuid.UUID,
        has_project_manage: bool,
        entity_id: uuid.UUID | None = None,
        event_type: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> tuple[list[KnowledgeTimelineEvent], int]:
        filters: list[Any] = [KnowledgeTimelineEvent.project_id == project_id]
        if entity_id:
            filters.append(
                or_(
                    KnowledgeTimelineEvent.entity_id == entity_id,
                    KnowledgeTimelineEvent.secondary_entity_id == entity_id,
                )
            )
        if event_type:
            filters.append(KnowledgeTimelineEvent.event_type == event_type)

        # Enforce that evidence_id satisfies caller's ACL
        acl_clause = _build_accessible_evidence_clause(
            self._session,
            project_id=project_id,
            viewer_user_id=viewer_user_id,
            has_project_manage=has_project_manage,
        )
        accessible_ev_exists = exists(
            select(EvidenceItem.id).where(
                EvidenceItem.id == KnowledgeTimelineEvent.evidence_id,
                acl_clause,
                EvidenceItem.deleted_at.is_(None),
                EvidenceItem.processing_status != EvidenceProcessingStatus.DELETED.value,
            )
        )
        filters.append(accessible_ev_exists)

        total_stmt = select(func.count(KnowledgeTimelineEvent.id)).where(and_(*filters))
        total = int(self._session.execute(total_stmt).scalar() or 0)

        data_stmt = (
            select(KnowledgeTimelineEvent)
            .where(and_(*filters))
            .order_by(
                KnowledgeTimelineEvent.occurred_at.desc().nullslast(),
                KnowledgeTimelineEvent.created_at.desc(),
            )
            .limit(limit)
            .offset(offset)
        )
        rows = list(self._session.execute(data_stmt).scalars().all())
        return rows, total


# ==============================================================================
# RelationshipRunRepository
# ==============================================================================


class RelationshipRunRepository:
    """Data-access repository for RelationshipReconstructionRun tracking."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def create_run(
        self,
        *,
        organisation_id: uuid.UUID,
        project_id: uuid.UUID,
        is_synthetic: bool = False,
    ) -> RelationshipReconstructionRun:
        run = RelationshipReconstructionRun(
            organisation_id=organisation_id,
            project_id=project_id,
            status=RelationshipRunStatus.QUEUED.value,
            is_synthetic=is_synthetic,
        )
        self._session.add(run)
        self._session.flush()
        return run

    def get_run(
        self,
        run_id: uuid.UUID,
        *,
        project_id: uuid.UUID | None = None,
    ) -> RelationshipReconstructionRun | None:
        stmt = select(RelationshipReconstructionRun).where(
            RelationshipReconstructionRun.id == run_id
        )
        if project_id is not None:
            stmt = stmt.where(RelationshipReconstructionRun.project_id == project_id)
        return self._session.execute(stmt).scalar_one_or_none()

    def get_active_run(self, *, project_id: uuid.UUID) -> RelationshipReconstructionRun | None:
        stmt = (
            select(RelationshipReconstructionRun)
            .where(
                RelationshipReconstructionRun.project_id == project_id,
                RelationshipReconstructionRun.status.in_(
                    [
                        RelationshipRunStatus.QUEUED.value,
                        RelationshipRunStatus.RUNNING.value,
                    ]
                ),
            )
            .order_by(RelationshipReconstructionRun.created_at.desc())
            .limit(1)
        )
        return self._session.execute(stmt).scalar_one_or_none()

    def list_runs(
        self,
        *,
        project_id: uuid.UUID,
        limit: int = 20,
        offset: int = 0,
    ) -> tuple[list[RelationshipReconstructionRun], int]:
        total_stmt = select(func.count(RelationshipReconstructionRun.id)).where(
            RelationshipReconstructionRun.project_id == project_id
        )
        total = int(self._session.execute(total_stmt).scalar() or 0)

        stmt = (
            select(RelationshipReconstructionRun)
            .where(RelationshipReconstructionRun.project_id == project_id)
            .order_by(RelationshipReconstructionRun.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        rows = list(self._session.execute(stmt).scalars().all())
        return rows, total

    def update_run_progress(
        self,
        run_id: uuid.UUID,
        *,
        status: str | None = None,
        entities_count: int | None = None,
        relationships_count: int | None = None,
        explicit_count: int | None = None,
        inferred_count: int | None = None,
        duration_ms: int | None = None,
        error_message: str | None = None,
    ) -> RelationshipReconstructionRun:
        run = self.get_run(run_id)
        if run is None:
            raise ValueError(f"Run {run_id} not found")

        if status:
            run.status = status
            if status in (
                RelationshipRunStatus.COMPLETED.value,
                RelationshipRunStatus.FAILED.value,
            ):
                run.completed_at = utc_now()
        if entities_count is not None:
            run.entities_discovered_count = entities_count
        if relationships_count is not None:
            run.relationships_discovered_count = relationships_count
        if explicit_count is not None:
            run.explicit_links_count = explicit_count
        if inferred_count is not None:
            run.inferred_links_count = inferred_count
        if duration_ms is not None:
            run.duration_ms = duration_ms
        if error_message is not None:
            run.error_message = error_message

        self._session.flush()
        return run
