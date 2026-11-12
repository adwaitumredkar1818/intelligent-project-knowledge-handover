"""Data-access repository for Phase 2.6 extraction runs, knowledge items, and evidence links."""

from __future__ import annotations

import uuid
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from sqlalchemy import and_, delete, exists, func, or_, select
from sqlalchemy.orm import Session, joinedload, selectinload

from app.core.security import utc_now
from app.models.enums import (
    EpistemicStatus,
    EvidenceProcessingStatus,
    EvidenceSourceType,
    ExtractionRunStatus,
    KnowledgeCategory,
    SourcePermissionVerificationStatus,
    SupportClassification,
)
from app.models.evidence import EvidenceItem
from app.models.integration import SourceAccessPolicy
from app.models.knowledge import (
    KnowledgeEvidenceLink,
    KnowledgeExtractionRun,
    KnowledgeItem,
)
from app.services.integrations.access_policy import SourceAccessPolicyService
from app.services.knowledge_validator import ValidatedKnowledgeItemDraft

_ACTIVE_RUN_STATUSES: tuple[str, ...] = (
    ExtractionRunStatus.QUEUED.value,
    ExtractionRunStatus.RUNNING.value,
)


@dataclass(frozen=True, slots=True)
class ProjectKnowledgeStats:
    """Permission-filtered knowledge summary metrics for a project workspace."""

    total_accessible_items: int
    stale_items_count: int
    counts_by_category: dict[str, int]
    counts_by_epistemic_status: dict[str, int]
    counts_by_support_classification: dict[str, int]
    active_runs_count: int


@dataclass(frozen=True, slots=True)
class AccessibleKnowledgeItemResult:
    """KnowledgeItem paired with caller-accessible non-deleted KnowledgeEvidenceLinks."""

    item: KnowledgeItem
    accessible_links: tuple[KnowledgeEvidenceLink, ...]


class KnowledgeRepository:
    """Repository managing extraction runs, structured knowledge items, and provenance links."""

    def __init__(self, session: Session) -> None:
        self._session = session
        self._access_policy = SourceAccessPolicyService()

    # ------------------------------------------------------------------
    # Extraction Run Persistence
    # ------------------------------------------------------------------

    def create_extraction_run(
        self,
        *,
        organisation_id: uuid.UUID,
        project_id: uuid.UUID,
        background_job_id: uuid.UUID | None,
        evidence_id: uuid.UUID | None,
        triggered_by_user_id: uuid.UUID | None,
        scope_type: str,
        target_categories: Sequence[str],
        model_name: str,
        prompt_version: str,
        is_synthetic: bool = False,
        total_evidence_items: int = 0,
    ) -> KnowledgeExtractionRun:
        run = KnowledgeExtractionRun(
            organisation_id=organisation_id,
            project_id=project_id,
            background_job_id=background_job_id,
            evidence_id=evidence_id,
            triggered_by_user_id=triggered_by_user_id,
            scope_type=scope_type,
            target_categories=list(target_categories),
            model_name=model_name,
            prompt_version=prompt_version,
            status=ExtractionRunStatus.QUEUED.value,
            is_synthetic=is_synthetic,
            total_evidence_items=total_evidence_items,
            warnings_json=[],
        )
        self._session.add(run)
        self._session.flush()
        return run

    def get_run_by_id(
        self,
        run_id: uuid.UUID,
        *,
        project_id: uuid.UUID | None = None,
    ) -> KnowledgeExtractionRun | None:
        stmt = (
            select(KnowledgeExtractionRun)
            .options(joinedload(KnowledgeExtractionRun.background_job))
            .where(KnowledgeExtractionRun.id == run_id)
        )
        if project_id is not None:
            stmt = stmt.where(KnowledgeExtractionRun.project_id == project_id)
        return self._session.execute(stmt).unique().scalar_one_or_none()

    def get_active_run_for_evidence(
        self,
        *,
        project_id: uuid.UUID,
        evidence_id: uuid.UUID,
    ) -> KnowledgeExtractionRun | None:
        stmt = (
            select(KnowledgeExtractionRun)
            .options(joinedload(KnowledgeExtractionRun.background_job))
            .where(
                KnowledgeExtractionRun.project_id == project_id,
                KnowledgeExtractionRun.evidence_id == evidence_id,
                KnowledgeExtractionRun.status.in_(_ACTIVE_RUN_STATUSES),
            )
            .order_by(KnowledgeExtractionRun.created_at.desc())
            .limit(1)
        )
        return self._session.execute(stmt).unique().scalar_one_or_none()

    def get_active_project_run(self, *, project_id: uuid.UUID) -> KnowledgeExtractionRun | None:
        stmt = (
            select(KnowledgeExtractionRun)
            .options(joinedload(KnowledgeExtractionRun.background_job))
            .where(
                KnowledgeExtractionRun.project_id == project_id,
                KnowledgeExtractionRun.scope_type == "project",
                KnowledgeExtractionRun.status.in_(_ACTIVE_RUN_STATUSES),
            )
            .order_by(KnowledgeExtractionRun.created_at.desc())
            .limit(1)
        )
        return self._session.execute(stmt).unique().scalar_one_or_none()

    def list_runs_for_project(
        self,
        *,
        project_id: uuid.UUID,
        status: str | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> tuple[list[KnowledgeExtractionRun], int]:
        filters: list[Any] = [KnowledgeExtractionRun.project_id == project_id]
        if status is not None:
            filters.append(KnowledgeExtractionRun.status == status)

        total = int(
            self._session.execute(
                select(func.count()).select_from(KnowledgeExtractionRun).where(*filters)
            ).scalar_one()
        )
        runs = list(
            self._session.execute(
                select(KnowledgeExtractionRun)
                .options(joinedload(KnowledgeExtractionRun.background_job))
                .where(*filters)
                .order_by(
                    KnowledgeExtractionRun.created_at.desc(),
                    KnowledgeExtractionRun.id.desc(),
                )
                .limit(limit)
                .offset(offset)
            )
            .unique()
            .scalars()
            .all()
        )
        return runs, total

    # ------------------------------------------------------------------
    # Knowledge Item Persistence, Conservative Dedup & Stale Marking
    # ------------------------------------------------------------------

    def upsert_validated_draft(
        self,
        *,
        organisation_id: uuid.UUID,
        project_id: uuid.UUID,
        extraction_run_id: uuid.UUID,
        model_name: str,
        prompt_version: str,
        draft: ValidatedKnowledgeItemDraft,
    ) -> tuple[KnowledgeItem, bool]:
        """Persist or conservatively merge a verified knowledge claim.

        Returns `(item, merged)` where `merged=True` indicates an identical compatible
        non-stale record already existed and was augmented with new verified links.
        Never merges conflicting statuses, distinct person identities, or synthetic vs real.
        """
        candidates = list(
            self._session.execute(
                select(KnowledgeItem)
                .options(selectinload(KnowledgeItem.evidence_links))
                .where(
                    KnowledgeItem.project_id == project_id,
                    KnowledgeItem.category == draft.category.value,
                    KnowledgeItem.fingerprint == draft.fingerprint,
                    KnowledgeItem.is_deleted.is_(False),
                    KnowledgeItem.is_stale.is_(False),
                    KnowledgeItem.is_synthetic.is_(draft.is_synthetic),
                )
            )
            .scalars()
            .all()
        )

        matched: KnowledgeItem | None = None
        for existing in candidates:
            if (
                existing.normalised_status == draft.normalised_status
                and existing.person_or_owner_label == draft.person_or_owner_label
                and existing.epistemic_status == draft.epistemic_status
            ):
                matched = existing
                break

        if matched is not None:
            existing_link_sigs: set[tuple[uuid.UUID, uuid.UUID | None, str]] = {
                (lnk.evidence_id, lnk.evidence_chunk_id, lnk.supporting_excerpt)
                for lnk in matched.evidence_links
            }
            added_any = False
            for link_draft in draft.evidence_links:
                sig = (
                    link_draft.evidence_id,
                    link_draft.evidence_chunk_id,
                    link_draft.supporting_excerpt,
                )
                if sig in existing_link_sigs:
                    continue
                new_link = KnowledgeEvidenceLink(
                    organisation_id=organisation_id,
                    project_id=project_id,
                    knowledge_item_id=matched.id,
                    evidence_id=link_draft.evidence_id,
                    evidence_chunk_id=link_draft.evidence_chunk_id,
                    support_type=link_draft.support_type,
                    source_location_json=dict(link_draft.source_location),
                    supporting_excerpt=link_draft.supporting_excerpt,
                    excerpt_verified=True,
                    excerpt_match_mode=link_draft.excerpt_match_mode,
                    source_metadata_json=dict(link_draft.source_metadata),
                )
                self._session.add(new_link)
                matched.evidence_links.append(new_link)
                existing_link_sigs.add(sig)
                added_any = True

            distinct_evidence_ids = {lnk.evidence_id for lnk in matched.evidence_links}
            if (
                len(distinct_evidence_ids) >= 2
                and matched.support_classification == SupportClassification.DIRECT.value
            ):
                matched.support_classification = SupportClassification.CORROBORATED.value

            updated_attr = dict(matched.source_attribution_json or {})
            updated_attr["evidence_count"] = len(distinct_evidence_ids)
            matched.source_attribution_json = updated_attr
            if added_any:
                matched.extraction_run_id = extraction_run_id
                matched.extraction_model = model_name
                matched.prompt_version = prompt_version
            self._session.flush()
            return matched, True

        item = KnowledgeItem(
            organisation_id=organisation_id,
            project_id=project_id,
            extraction_run_id=extraction_run_id,
            category=draft.category.value,
            epistemic_status=draft.epistemic_status,
            review_status=draft.review_status,
            support_classification=draft.support_classification,
            title=draft.title,
            structured_summary=draft.structured_summary,
            structured_payload=dict(draft.structured_payload),
            normalised_status=draft.normalised_status,
            person_or_owner_label=draft.person_or_owner_label,
            source_attribution_json=dict(draft.source_attribution),
            extraction_model=model_name,
            prompt_version=prompt_version,
            fingerprint=draft.fingerprint,
            confidence_metadata_json=dict(draft.confidence_metadata),
            uncertainty_reason=draft.uncertainty_reason,
            source_observed_at=draft.source_observed_at,
            is_synthetic=draft.is_synthetic,
        )
        self._session.add(item)
        self._session.flush()

        for link_draft in draft.evidence_links:
            link = KnowledgeEvidenceLink(
                organisation_id=organisation_id,
                project_id=project_id,
                knowledge_item_id=item.id,
                evidence_id=link_draft.evidence_id,
                evidence_chunk_id=link_draft.evidence_chunk_id,
                support_type=link_draft.support_type,
                source_location_json=dict(link_draft.source_location),
                supporting_excerpt=link_draft.supporting_excerpt,
                excerpt_verified=True,
                excerpt_match_mode=link_draft.excerpt_match_mode,
                source_metadata_json=dict(link_draft.source_metadata),
            )
            self._session.add(link)
            item.evidence_links.append(link)

        self._session.flush()
        return item, False

    def mark_stale_for_evidence(
        self,
        *,
        evidence_id: uuid.UUID,
        reason: str,
        now: datetime | None = None,
        exclude_run_id: uuid.UUID | None = None,
    ) -> int:
        """Mark active non-stale knowledge items backed by `evidence_id` as stale."""
        timestamp = now or utc_now()
        subq = select(KnowledgeEvidenceLink.knowledge_item_id).where(
            KnowledgeEvidenceLink.evidence_id == evidence_id
        )
        stmt = select(KnowledgeItem).where(
            KnowledgeItem.id.in_(subq),
            KnowledgeItem.is_deleted.is_(False),
            KnowledgeItem.is_stale.is_(False),
        )
        if exclude_run_id is not None:
            stmt = stmt.where(
                or_(
                    KnowledgeItem.extraction_run_id.is_(None),
                    KnowledgeItem.extraction_run_id != exclude_run_id,
                )
            )
        items = list(self._session.execute(stmt).scalars().all())
        safe_reason = reason.strip()[:255]
        for item in items:
            item.is_stale = True
            item.stale_reason = safe_reason
            item.stale_detected_at = timestamp
        if items:
            self._session.flush()
        return len(items)

    def purge_links_for_item_chunks(self, evidence_id: uuid.UUID) -> int:
        """Delete nothing when evidence chunks vanish; just mark linked items stale."""
        return self.mark_stale_for_evidence(
            evidence_id=evidence_id,
            reason="evidence_chunks_replaced",
        )

    def has_stale_items_for_evidence(self, evidence_id: uuid.UUID) -> bool:
        """Return True if any non-deleted knowledge item citing `evidence_id` is currently stale."""
        stmt = (
            select(KnowledgeItem.id)
            .join(
                KnowledgeEvidenceLink,
                KnowledgeEvidenceLink.knowledge_item_id == KnowledgeItem.id,
            )
            .where(
                KnowledgeEvidenceLink.evidence_id == evidence_id,
                KnowledgeItem.is_deleted.is_(False),
                KnowledgeItem.is_stale.is_(True),
            )
            .limit(1)
        )
        return self._session.execute(stmt).scalar_one_or_none() is not None

    def delete_synthetic_for_project(self, project_id: uuid.UUID) -> int:
        """Clean helper if synthetic fixture rows need removal in tests."""
        res = self._session.execute(
            delete(KnowledgeItem).where(
                KnowledgeItem.project_id == project_id,
                KnowledgeItem.is_synthetic.is_(True),
            )
        )
        self._session.flush()
        return int(getattr(res, "rowcount", 0) or 0)

    # ------------------------------------------------------------------
    # Live Source-ACL-Enforced Queries
    # ------------------------------------------------------------------

    def _allowed_and_revoked_policies(
        self,
        *,
        project_id: uuid.UUID,
        viewer_user_id: uuid.UUID,
    ) -> tuple[list[uuid.UUID], list[uuid.UUID]]:
        policies = list(
            self._session.execute(
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

    def _accessible_evidence_sql_clause(
        self,
        *,
        project_id: uuid.UUID,
        viewer_user_id: uuid.UUID,
        has_project_manage: bool,
    ) -> Any:
        allowed_policy_ids, revoked_policy_ids = self._allowed_and_revoked_policies(
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

    def _filter_accessible_links(
        self,
        *,
        item: KnowledgeItem,
        viewer_user_id: uuid.UUID,
        has_project_manage: bool,
    ) -> tuple[KnowledgeEvidenceLink, ...]:
        accessible: list[KnowledgeEvidenceLink] = []
        for link in item.evidence_links:
            ev = link.evidence_item
            if ev is None:
                continue
            if ev.deleted_at is not None or (
                ev.processing_status == EvidenceProcessingStatus.DELETED.value
            ):
                continue
            if self._access_policy.can_user_access_evidence(
                evidence=ev,
                user_id=viewer_user_id,
                has_project_manage=has_project_manage,
            ):
                accessible.append(link)
        return tuple(accessible)

    def list_accessible_items_for_project(
        self,
        *,
        project_id: uuid.UUID,
        viewer_user_id: uuid.UUID,
        has_project_manage: bool,
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
    ) -> tuple[list[AccessibleKnowledgeItemResult], int]:
        acl_clause = self._accessible_evidence_sql_clause(
            project_id=project_id,
            viewer_user_id=viewer_user_id,
            has_project_manage=has_project_manage,
        )

        link_subq_conditions: list[Any] = [
            KnowledgeEvidenceLink.knowledge_item_id == KnowledgeItem.id,
            EvidenceItem.deleted_at.is_(None),
            EvidenceItem.processing_status != EvidenceProcessingStatus.DELETED.value,
            acl_clause,
        ]
        if evidence_id is not None:
            link_subq_conditions.append(KnowledgeEvidenceLink.evidence_id == evidence_id)
        if source_provider is not None:
            link_subq_conditions.append(
                func.lower(EvidenceItem.source_provider) == source_provider.strip().lower()
            )

        accessible_link_exists = exists(
            select(KnowledgeEvidenceLink.id)
            .select_from(KnowledgeEvidenceLink)
            .join(EvidenceItem, KnowledgeEvidenceLink.evidence_id == EvidenceItem.id)
            .where(*link_subq_conditions)
        )

        filters: list[Any] = [
            KnowledgeItem.project_id == project_id,
            KnowledgeItem.is_deleted.is_(False),
            accessible_link_exists,
        ]
        if not include_synthetic:
            filters.append(KnowledgeItem.is_synthetic.is_(False))
        if stale_only:
            filters.append(KnowledgeItem.is_stale.is_(True))
        elif not include_stale:
            filters.append(KnowledgeItem.is_stale.is_(False))

        if category is not None:
            filters.append(KnowledgeItem.category == category)
        if epistemic_status is not None:
            filters.append(KnowledgeItem.epistemic_status == epistemic_status)
        if review_status is not None:
            filters.append(KnowledgeItem.review_status == review_status)
        if support_classification is not None:
            filters.append(KnowledgeItem.support_classification == support_classification)
        if normalised_status is not None:
            filters.append(
                func.lower(KnowledgeItem.normalised_status) == normalised_status.strip().lower()
            )
        if person is not None and person.strip():
            needle = person.strip().lower()
            filters.append(
                and_(
                    KnowledgeItem.person_or_owner_label.is_not(None),
                    func.lower(KnowledgeItem.person_or_owner_label).contains(needle),
                )
            )
        if date_from is not None:
            filters.append(
                or_(
                    KnowledgeItem.source_observed_at >= date_from,
                    and_(
                        KnowledgeItem.source_observed_at.is_(None),
                        KnowledgeItem.created_at >= date_from,
                    ),
                )
            )
        if date_to is not None:
            filters.append(
                or_(
                    KnowledgeItem.source_observed_at <= date_to,
                    and_(
                        KnowledgeItem.source_observed_at.is_(None),
                        KnowledgeItem.created_at <= date_to,
                    ),
                )
            )

        total = int(
            self._session.execute(
                select(func.count()).select_from(KnowledgeItem).where(*filters)
            ).scalar_one()
        )

        stmt = (
            select(KnowledgeItem)
            .options(
                selectinload(KnowledgeItem.evidence_links)
                .joinedload(KnowledgeEvidenceLink.evidence_item)
                .joinedload(EvidenceItem.source_access_policy)
            )
            .where(*filters)
            .order_by(KnowledgeItem.created_at.desc(), KnowledgeItem.id.desc())
            .limit(limit)
            .offset(offset)
        )
        rows = list(self._session.execute(stmt).unique().scalars().all())
        results: list[AccessibleKnowledgeItemResult] = []
        for item in rows:
            accessible_links = self._filter_accessible_links(
                item=item,
                viewer_user_id=viewer_user_id,
                has_project_manage=has_project_manage,
            )
            if not accessible_links:
                continue
            results.append(
                AccessibleKnowledgeItemResult(
                    item=item,
                    accessible_links=accessible_links,
                )
            )
        return results, total

    def get_item_with_acl_check(
        self,
        *,
        project_id: uuid.UUID,
        item_id: uuid.UUID,
        viewer_user_id: uuid.UUID,
        has_project_manage: bool,
    ) -> tuple[KnowledgeItem | None, tuple[KnowledgeEvidenceLink, ...], bool]:
        """Return `(item, accessible_links, denied_by_acl)`.

        Returns `(None, (), False)` if item does not exist in `project_id` or is deleted.
        Returns `(item, (), True)` if the item exists in `project_id` but caller lacks live
        source access to every supporting evidence item (fail-closed `403 SOURCE_ACCESS_DENIED`).
        """
        stmt = (
            select(KnowledgeItem)
            .options(
                selectinload(KnowledgeItem.evidence_links)
                .joinedload(KnowledgeEvidenceLink.evidence_item)
                .joinedload(EvidenceItem.source_access_policy)
            )
            .where(
                KnowledgeItem.id == item_id,
                KnowledgeItem.project_id == project_id,
                KnowledgeItem.is_deleted.is_(False),
            )
        )
        item = self._session.execute(stmt).unique().scalar_one_or_none()
        if item is None:
            return None, (), False

        accessible_links = self._filter_accessible_links(
            item=item,
            viewer_user_id=viewer_user_id,
            has_project_manage=has_project_manage,
        )
        if not accessible_links:
            return item, (), True
        return item, accessible_links, False

    def get_project_knowledge_stats(
        self,
        *,
        project_id: uuid.UUID,
        viewer_user_id: uuid.UUID,
        has_project_manage: bool,
        include_synthetic: bool = False,
    ) -> ProjectKnowledgeStats:
        acl_clause = self._accessible_evidence_sql_clause(
            project_id=project_id,
            viewer_user_id=viewer_user_id,
            has_project_manage=has_project_manage,
        )
        accessible_link_exists = exists(
            select(KnowledgeEvidenceLink.id)
            .select_from(KnowledgeEvidenceLink)
            .join(EvidenceItem, KnowledgeEvidenceLink.evidence_id == EvidenceItem.id)
            .where(
                KnowledgeEvidenceLink.knowledge_item_id == KnowledgeItem.id,
                EvidenceItem.deleted_at.is_(None),
                EvidenceItem.processing_status != EvidenceProcessingStatus.DELETED.value,
                acl_clause,
            )
        )
        filters: list[Any] = [
            KnowledgeItem.project_id == project_id,
            KnowledgeItem.is_deleted.is_(False),
            accessible_link_exists,
        ]
        if not include_synthetic:
            filters.append(KnowledgeItem.is_synthetic.is_(False))

        rows = list(
            self._session.execute(
                select(
                    KnowledgeItem.category,
                    KnowledgeItem.epistemic_status,
                    KnowledgeItem.support_classification,
                    KnowledgeItem.is_stale,
                ).where(*filters)
            ).all()
        )

        counts_by_category: dict[str, int] = {cat.value: 0 for cat in KnowledgeCategory}
        counts_by_epistemic: dict[str, int] = {
            EpistemicStatus.EXTRACTED.value: 0,
            EpistemicStatus.AI_INTERPRETED.value: 0,
            EpistemicStatus.HUMAN_VERIFIED.value: 0,
        }
        counts_by_support: dict[str, int] = {sc.value: 0 for sc in SupportClassification}
        stale_count = 0

        for cat, ep, sup, is_stale in rows:
            counts_by_category[str(cat)] = counts_by_category.get(str(cat), 0) + 1
            counts_by_epistemic[str(ep)] = counts_by_epistemic.get(str(ep), 0) + 1
            counts_by_support[str(sup)] = counts_by_support.get(str(sup), 0) + 1
            if is_stale:
                stale_count += 1

        active_runs_count = int(
            self._session.execute(
                select(func.count())
                .select_from(KnowledgeExtractionRun)
                .where(
                    KnowledgeExtractionRun.project_id == project_id,
                    KnowledgeExtractionRun.status.in_(_ACTIVE_RUN_STATUSES),
                )
            ).scalar_one()
        )

        return ProjectKnowledgeStats(
            total_accessible_items=len(rows),
            stale_items_count=stale_count,
            counts_by_category=counts_by_category,
            counts_by_epistemic_status=counts_by_epistemic,
            counts_by_support_classification=counts_by_support,
            active_runs_count=active_runs_count,
        )
