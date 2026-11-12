"""Data-access repository for canonical EvidenceChunk persistence, PG FTS, and ACL filtering."""

from __future__ import annotations

import math
import re
import uuid
from collections import Counter
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from sqlalchemy import (
    Select,
    and_,
    delete,
    func,
    literal,
    literal_column,
    or_,
    select,
)
from sqlalchemy.orm import Session, joinedload
from sqlalchemy.sql.elements import ColumnElement

from app.models.enums import (
    BackgroundJobStatus,
    BackgroundJobType,
    ChunkIndexingStatus,
    EvidenceIndexingStatus,
    EvidenceProcessingStatus,
    EvidenceSourceType,
    SourcePermissionVerificationStatus,
)
from app.models.evidence import EvidenceChunk, EvidenceItem
from app.models.integration import SourceAccessPolicy
from app.models.job import BackgroundJob
from app.services.chunking import ChunkDraft, extract_fts_identifier_tokens
from app.services.vector_store import build_deterministic_vector_id

_INDEXING_JOB_TYPES: tuple[str, ...] = (
    BackgroundJobType.EVIDENCE_CHUNKING.value,
    BackgroundJobType.EVIDENCE_EMBEDDING.value,
    BackgroundJobType.EVIDENCE_INDEXING.value,
    BackgroundJobType.EVIDENCE_REINDEXING.value,
    BackgroundJobType.EVIDENCE_INDEX_CLEANUP.value,
)

_TOKEN_SPLIT_RE = re.compile(r"[A-Za-z0-9_./:-]+")


@dataclass(frozen=True, slots=True)
class KeywordChunkMatch:
    """Ranked keyword search hit pairing canonical chunk, parent evidence, and rank score."""

    chunk: EvidenceChunk
    evidence: EvidenceItem
    score: float
    rank: int


@dataclass(frozen=True, slots=True)
class ProjectIndexingSummaryCounts:
    """Aggregated canonical indexing state metrics computed from PostgreSQL."""

    total_eligible_evidence: int
    status_counts: dict[str, int]
    total_chunks: int
    indexed_chunks: int
    pending_vector_chunks: int
    failed_chunks: int
    active_indexing_jobs: int
    latest_indexed_at: datetime | None
    distinct_embedding_models: tuple[str, ...]
    distinct_index_versions: tuple[str, ...]


class EvidenceChunkRepository:
    """Repository managing canonical chunks, PostgreSQL GIN FTS, and ACL-enforced retrieval."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def _dialect_name(self) -> str:
        bind = self._session.get_bind()
        return str(bind.dialect.name) if bind is not None else "sqlite"

    def _build_pg_tsvector_expr(
        self,
        *,
        title: str,
        section_title: str | None,
        identifier_text: str,
        chunk_text: str,
    ) -> Any:
        simple_cfg: ColumnElement[Any] = literal_column("'simple'")
        english_cfg: ColumnElement[Any] = literal_column("'english'")
        weight_a = " ".join(part for part in (identifier_text, title) if part).strip()
        weight_b = " ".join(
            part for part in (title, section_title or "", chunk_text) if part
        ).strip()
        weight_c = " ".join(part for part in (section_title or "", chunk_text) if part).strip()

        vec_a = func.setweight(
            func.to_tsvector(simple_cfg, literal(weight_a)),
            literal_column("'A'"),
        )
        vec_b = func.setweight(
            func.to_tsvector(english_cfg, literal(weight_b)),
            literal_column("'B'"),
        )
        vec_c = func.setweight(
            func.to_tsvector(simple_cfg, literal(weight_c)),
            literal_column("'C'"),
        )
        return vec_a.op("||")(vec_b).op("||")(vec_c)

    def replace_chunks_for_evidence(
        self,
        *,
        evidence: EvidenceItem,
        drafts: Sequence[ChunkDraft],
        collection_name: str,
    ) -> tuple[list[EvidenceChunk], list[str]]:
        """Atomically replace canonical chunks and return `(new_chunks, obsolete_vector_ids)`."""
        existing_rows = list(
            self._session.execute(
                select(
                    EvidenceChunk.chroma_vector_id,
                    EvidenceChunk.chunk_index,
                ).where(EvidenceChunk.evidence_id == evidence.id)
            ).all()
        )
        previous_vector_ids = [
            str(vec_id)
            if vec_id
            else build_deterministic_vector_id(evidence_id=evidence.id, chunk_index=int(c_idx))
            for vec_id, c_idx in existing_rows
        ]

        self._session.execute(
            delete(EvidenceChunk).where(EvidenceChunk.evidence_id == evidence.id)
        )
        self._session.flush()

        is_pg = self._dialect_name() == "postgresql"
        new_vector_id_set: set[str] = set()
        inserted: list[EvidenceChunk] = []

        for draft in drafts:
            vector_id = build_deterministic_vector_id(
                evidence_id=evidence.id,
                chunk_index=draft.chunk_index,
            )
            new_vector_id_set.add(vector_id)
            ts_expr = (
                self._build_pg_tsvector_expr(
                    title=evidence.title,
                    section_title=draft.section_title,
                    identifier_text=draft.search_identifier_text,
                    chunk_text=draft.chunk_text,
                )
                if is_pg
                else None
            )
            chunk = EvidenceChunk(
                organisation_id=evidence.organisation_id,
                project_id=evidence.project_id,
                evidence_id=evidence.id,
                chunk_index=draft.chunk_index,
                chunk_type=draft.chunk_type,
                section_title=draft.section_title,
                page_number=draft.page_number,
                char_start=draft.char_start,
                char_end=draft.char_end,
                char_count=draft.char_count,
                token_estimate=draft.token_estimate,
                chunk_text=draft.chunk_text,
                chunk_content_hash=draft.chunk_content_hash,
                search_identifier_text=draft.search_identifier_text,
                search_vector=ts_expr,
                source_type=evidence.source_type,
                source_author_identity=draft.source_author_identity,
                source_created_at=draft.source_created_at,
                acl_scope=evidence.acl_scope,
                metadata_json=dict(draft.metadata_json),
                indexing_status=ChunkIndexingStatus.CHUNKED.value,
                chroma_collection_name=collection_name,
                chroma_vector_id=vector_id,
            )
            self._session.add(chunk)
            inserted.append(chunk)

        self._session.flush()
        obsolete_vector_ids = [vid for vid in previous_vector_ids if vid not in new_vector_id_set]
        return inserted, obsolete_vector_ids

    def list_chunks_for_evidence(self, evidence_id: uuid.UUID) -> list[EvidenceChunk]:
        stmt = (
            select(EvidenceChunk)
            .where(EvidenceChunk.evidence_id == evidence_id)
            .order_by(EvidenceChunk.chunk_index.asc())
        )
        return list(self._session.execute(stmt).scalars().all())

    def delete_chunks_for_evidence(self, evidence_id: uuid.UUID) -> list[str]:
        """Delete canonical chunks for an evidence item and return known Chroma vector IDs."""
        rows = list(
            self._session.execute(
                select(
                    EvidenceChunk.chroma_vector_id,
                    EvidenceChunk.chunk_index,
                ).where(EvidenceChunk.evidence_id == evidence_id)
            ).all()
        )
        vector_ids = [
            str(vec_id)
            if vec_id
            else build_deterministic_vector_id(evidence_id=evidence_id, chunk_index=int(c_idx))
            for vec_id, c_idx in rows
        ]
        self._session.execute(delete(EvidenceChunk).where(EvidenceChunk.evidence_id == evidence_id))
        self._session.flush()
        return vector_ids

    def mark_chunks_vector_results(
        self,
        *,
        chunks: Sequence[EvidenceChunk],
        indexing_status: str,
        collection_name: str,
        embedding_model: str | None = None,
        embedding_dimensions: int | None = None,
        embedded_at: datetime | None = None,
        error_code: str | None = None,
        error_message: str | None = None,
    ) -> None:
        safe_msg = error_message[:500] if error_message else None
        safe_code = error_code[:64] if error_code else None
        for chunk in chunks:
            chunk.indexing_status = indexing_status
            chunk.chroma_collection_name = collection_name
            if embedding_model is not None:
                chunk.embedding_model = embedding_model
            if embedding_dimensions is not None:
                chunk.embedding_dimensions = embedding_dimensions
            if embedded_at is not None:
                chunk.embedded_at = embedded_at
            chunk.error_code = safe_code
            chunk.error_message = safe_msg
        self._session.flush()

    def get_chunk_with_evidence(
        self,
        *,
        project_id: uuid.UUID,
        chunk_id: uuid.UUID,
    ) -> EvidenceChunk | None:
        stmt = (
            select(EvidenceChunk)
            .join(EvidenceItem, EvidenceChunk.evidence_id == EvidenceItem.id)
            .options(
                joinedload(EvidenceChunk.evidence_item).joinedload(
                    EvidenceItem.source_access_policy
                )
            )
            .where(
                EvidenceChunk.id == chunk_id,
                EvidenceChunk.project_id == project_id,
                EvidenceItem.project_id == project_id,
                EvidenceItem.deleted_at.is_(None),
                EvidenceItem.processing_status != EvidenceProcessingStatus.DELETED.value,
            )
        )
        return self._session.execute(stmt).unique().scalar_one_or_none()

    def get_many_with_evidence(
        self,
        *,
        project_id: uuid.UUID,
        chunk_ids: Sequence[uuid.UUID],
    ) -> dict[uuid.UUID, EvidenceChunk]:
        if not chunk_ids:
            return {}
        stmt = (
            select(EvidenceChunk)
            .join(EvidenceItem, EvidenceChunk.evidence_id == EvidenceItem.id)
            .options(
                joinedload(EvidenceChunk.evidence_item).joinedload(
                    EvidenceItem.source_access_policy
                )
            )
            .where(
                EvidenceChunk.id.in_(list(chunk_ids)),
                EvidenceChunk.project_id == project_id,
                EvidenceItem.project_id == project_id,
                EvidenceItem.deleted_at.is_(None),
                EvidenceItem.processing_status != EvidenceProcessingStatus.DELETED.value,
            )
        )
        rows = self._session.execute(stmt).unique().scalars().all()
        return {row.id: row for row in rows}

    def get_allowed_and_revoked_policies(
        self,
        *,
        project_id: uuid.UUID,
        viewer_user_id: uuid.UUID | None,
    ) -> tuple[list[uuid.UUID], list[uuid.UUID], list[uuid.UUID]]:
        """Return `(allowed_restricted_ids, project_member_ids, revoked_ids)` for retrieval."""
        if viewer_user_id is None:
            return [], [], []
        policies = list(
            self._session.execute(
                select(SourceAccessPolicy).where(SourceAccessPolicy.project_id == project_id)
            )
            .scalars()
            .all()
        )
        viewer_str = str(viewer_user_id)
        allowed_restricted: list[uuid.UUID] = []
        project_member_policies: list[uuid.UUID] = []
        revoked: list[uuid.UUID] = []
        for policy in policies:
            if policy.sync_permission_status == SourcePermissionVerificationStatus.REVOKED.value:
                revoked.append(policy.id)
                continue
            if viewer_str in (policy.allowed_user_ids or []):
                allowed_restricted.append(policy.id)
            if policy.visibility_policy == "project_members_verified":
                project_member_policies.append(policy.id)
        return allowed_restricted, project_member_policies, revoked

    def _build_acl_predicate(
        self,
        *,
        viewer_user_id: uuid.UUID | None,
        has_project_manage: bool,
        allowed_policy_ids: Sequence[uuid.UUID],
        revoked_policy_ids: Sequence[uuid.UUID],
    ) -> Any:
        public_clause = (
            and_(
                EvidenceItem.acl_scope == "project_members",
                or_(
                    EvidenceItem.source_access_policy_id.is_(None),
                    EvidenceItem.source_access_policy_id.notin_(list(revoked_policy_ids)),
                ),
            )
            if revoked_policy_ids
            else EvidenceItem.acl_scope == "project_members"
        )
        acl_clauses: list[Any] = [public_clause]
        if allowed_policy_ids:
            acl_clauses.append(
                and_(
                    EvidenceItem.acl_scope == "source_restricted",
                    EvidenceItem.source_access_policy_id.in_(list(allowed_policy_ids)),
                )
            )
        if has_project_manage:
            acl_clauses.append(
                and_(
                    EvidenceItem.acl_scope == "source_restricted",
                    EvidenceItem.source_type == EvidenceSourceType.DOCUMENT_UPLOAD.value,
                    EvidenceItem.source_access_policy_id.is_(None),
                    EvidenceItem.source_connection_id.is_(None),
                )
            )
        elif viewer_user_id is not None:
            acl_clauses.append(
                and_(
                    EvidenceItem.acl_scope == "source_restricted",
                    EvidenceItem.source_type == EvidenceSourceType.DOCUMENT_UPLOAD.value,
                    EvidenceItem.source_access_policy_id.is_(None),
                    EvidenceItem.source_connection_id.is_(None),
                    EvidenceItem.uploaded_by_user_id == viewer_user_id,
                )
            )
        return or_(*acl_clauses)

    def _apply_common_search_filters(
        self,
        stmt: Select[Any],
        *,
        project_id: uuid.UUID,
        viewer_user_id: uuid.UUID | None,
        has_project_manage: bool,
        allowed_policy_ids: Sequence[uuid.UUID],
        revoked_policy_ids: Sequence[uuid.UUID],
        source_types: Sequence[str] | None,
        categories: Sequence[str] | None,
        chunk_types: Sequence[str] | None,
        author: str | None,
        evidence_ids: Sequence[uuid.UUID] | None,
        date_from: datetime | None,
        date_to: datetime | None,
    ) -> Select[Any]:
        stmt = stmt.where(
            EvidenceChunk.project_id == project_id,
            EvidenceItem.project_id == project_id,
            EvidenceItem.deleted_at.is_(None),
            EvidenceItem.processing_status != EvidenceProcessingStatus.DELETED.value,
            self._build_acl_predicate(
                viewer_user_id=viewer_user_id,
                has_project_manage=has_project_manage,
                allowed_policy_ids=allowed_policy_ids,
                revoked_policy_ids=revoked_policy_ids,
            ),
        )
        if source_types:
            stmt = stmt.where(EvidenceItem.source_type.in_(list(source_types)))
        if categories:
            stmt = stmt.where(EvidenceItem.category.in_(list(categories)))
        if chunk_types:
            stmt = stmt.where(EvidenceChunk.chunk_type.in_(list(chunk_types)))
        if evidence_ids:
            stmt = stmt.where(EvidenceItem.id.in_(list(evidence_ids)))
        if author and author.strip():
            pattern = f"%{author.strip()}%"
            stmt = stmt.where(
                or_(
                    EvidenceChunk.source_author_identity.ilike(pattern),
                    EvidenceItem.source_author_identity.ilike(pattern),
                )
            )
        if date_from is not None:
            effective_dt = func.coalesce(
                EvidenceChunk.source_created_at,
                EvidenceItem.source_created_at,
                EvidenceItem.created_at,
            )
            stmt = stmt.where(effective_dt >= date_from)
        if date_to is not None:
            effective_dt = func.coalesce(
                EvidenceChunk.source_created_at,
                EvidenceItem.source_created_at,
                EvidenceItem.created_at,
            )
            stmt = stmt.where(effective_dt <= date_to)
        return stmt

    @staticmethod
    def is_item_synthetic(evidence: EvidenceItem) -> bool:
        meta = evidence.metadata_json or {}
        return bool(meta.get("is_synthetic") is True or meta.get("synthetic_fixture") is True)

    def keyword_search(
        self,
        *,
        project_id: uuid.UUID,
        query: str,
        limit: int,
        viewer_user_id: uuid.UUID | None,
        has_project_manage: bool,
        allowed_policy_ids: Sequence[uuid.UUID],
        revoked_policy_ids: Sequence[uuid.UUID],
        source_types: Sequence[str] | None = None,
        categories: Sequence[str] | None = None,
        chunk_types: Sequence[str] | None = None,
        author: str | None = None,
        evidence_ids: Sequence[uuid.UUID] | None = None,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
        include_synthetic: bool = False,
    ) -> list[KeywordChunkMatch]:
        cleaned_query = query.strip()
        if not cleaned_query or limit <= 0:
            return []

        if self._dialect_name() == "postgresql":
            return self._keyword_search_postgresql(
                project_id=project_id,
                query=cleaned_query,
                limit=limit,
                viewer_user_id=viewer_user_id,
                has_project_manage=has_project_manage,
                allowed_policy_ids=allowed_policy_ids,
                revoked_policy_ids=revoked_policy_ids,
                source_types=source_types,
                categories=categories,
                chunk_types=chunk_types,
                author=author,
                evidence_ids=evidence_ids,
                date_from=date_from,
                date_to=date_to,
                include_synthetic=include_synthetic,
            )
        return self._keyword_search_python_fallback(
            project_id=project_id,
            query=cleaned_query,
            limit=limit,
            viewer_user_id=viewer_user_id,
            has_project_manage=has_project_manage,
            allowed_policy_ids=allowed_policy_ids,
            revoked_policy_ids=revoked_policy_ids,
            source_types=source_types,
            categories=categories,
            chunk_types=chunk_types,
            author=author,
            evidence_ids=evidence_ids,
            date_from=date_from,
            date_to=date_to,
            include_synthetic=include_synthetic,
        )

    def _keyword_search_postgresql(
        self,
        *,
        project_id: uuid.UUID,
        query: str,
        limit: int,
        viewer_user_id: uuid.UUID | None,
        has_project_manage: bool,
        allowed_policy_ids: Sequence[uuid.UUID],
        revoked_policy_ids: Sequence[uuid.UUID],
        source_types: Sequence[str] | None,
        categories: Sequence[str] | None,
        chunk_types: Sequence[str] | None,
        author: str | None,
        evidence_ids: Sequence[uuid.UUID] | None,
        date_from: datetime | None,
        date_to: datetime | None,
        include_synthetic: bool,
    ) -> list[KeywordChunkMatch]:
        english_cfg: ColumnElement[Any] = literal_column("'english'")
        simple_cfg: ColumnElement[Any] = literal_column("'simple'")
        eng_tsq = func.websearch_to_tsquery(english_cfg, literal(query))
        simple_tsq = func.websearch_to_tsquery(simple_cfg, literal(query))
        combined_tsq = eng_tsq.op("||")(simple_tsq)

        # Normalize score smoothly into (0, 1) with length damping (flag 33 = 32 | 1)
        rank_expr = func.ts_rank_cd(EvidenceChunk.search_vector, combined_tsq, 33).label(
            "fts_rank"
        )

        stmt = (
            select(EvidenceChunk, rank_expr)
            .join(EvidenceItem, EvidenceChunk.evidence_id == EvidenceItem.id)
            .options(
                joinedload(EvidenceChunk.evidence_item).joinedload(
                    EvidenceItem.source_access_policy
                )
            )
            .where(
                EvidenceChunk.search_vector.is_not(None),
                EvidenceChunk.search_vector.op("@@")(combined_tsq),
            )
        )
        stmt = self._apply_common_search_filters(
            stmt,
            project_id=project_id,
            viewer_user_id=viewer_user_id,
            has_project_manage=has_project_manage,
            allowed_policy_ids=allowed_policy_ids,
            revoked_policy_ids=revoked_policy_ids,
            source_types=source_types,
            categories=categories,
            chunk_types=chunk_types,
            author=author,
            evidence_ids=evidence_ids,
            date_from=date_from,
            date_to=date_to,
        )
        if not include_synthetic:
            is_syn_flag = EvidenceItem.metadata_json["is_synthetic"].as_string()
            syn_fixture_flag = EvidenceItem.metadata_json["synthetic_fixture"].as_string()
            stmt = stmt.where(
                and_(
                    or_(is_syn_flag.is_(None), func.lower(is_syn_flag) != "true"),
                    or_(syn_fixture_flag.is_(None), func.lower(syn_fixture_flag) != "true"),
                )
            )

        stmt = stmt.order_by(
            rank_expr.desc(),
            EvidenceChunk.created_at.desc(),
            EvidenceChunk.id.asc(),
        ).limit(limit)

        rows = self._session.execute(stmt).unique().all()
        matches: list[KeywordChunkMatch] = []
        for rank_idx, (chunk, score_val) in enumerate(rows, start=1):
            ev = chunk.evidence_item
            if not include_synthetic and self.is_item_synthetic(ev):
                continue
            matches.append(
                KeywordChunkMatch(
                    chunk=chunk,
                    evidence=ev,
                    score=max(0.0, float(score_val or 0.0)),
                    rank=rank_idx,
                )
            )
        return matches

    def _keyword_search_python_fallback(
        self,
        *,
        project_id: uuid.UUID,
        query: str,
        limit: int,
        viewer_user_id: uuid.UUID | None,
        has_project_manage: bool,
        allowed_policy_ids: Sequence[uuid.UUID],
        revoked_policy_ids: Sequence[uuid.UUID],
        source_types: Sequence[str] | None,
        categories: Sequence[str] | None,
        chunk_types: Sequence[str] | None,
        author: str | None,
        evidence_ids: Sequence[uuid.UUID] | None,
        date_from: datetime | None,
        date_to: datetime | None,
        include_synthetic: bool,
    ) -> list[KeywordChunkMatch]:
        """SQLite-compatible lexical matcher enforcing identical SQL ACL & metadata filters."""
        stmt = (
            select(EvidenceChunk)
            .join(EvidenceItem, EvidenceChunk.evidence_id == EvidenceItem.id)
            .options(
                joinedload(EvidenceChunk.evidence_item).joinedload(
                    EvidenceItem.source_access_policy
                )
            )
        )
        stmt = self._apply_common_search_filters(
            stmt,
            project_id=project_id,
            viewer_user_id=viewer_user_id,
            has_project_manage=has_project_manage,
            allowed_policy_ids=allowed_policy_ids,
            revoked_policy_ids=revoked_policy_ids,
            source_types=source_types,
            categories=categories,
            chunk_types=chunk_types,
            author=author,
            evidence_ids=evidence_ids,
            date_from=date_from,
            date_to=date_to,
        )
        chunks = list(self._session.execute(stmt).unique().scalars().all())
        if not chunks:
            return []

        query_lower = query.lower()
        raw_terms = [t.lower() for t in _TOKEN_SPLIT_RE.findall(query) if len(t) >= 2]
        ident_terms = [
            t.lower()
            for t in extract_fts_identifier_tokens(query, max_tokens=20).split()
            if len(t) >= 2
        ]
        terms = list(dict.fromkeys([*raw_terms, *ident_terms]))
        if not terms:
            terms = [query_lower]

        scored: list[tuple[float, EvidenceChunk]] = []
        for chunk in chunks:
            ev = chunk.evidence_item
            if not include_synthetic and self.is_item_synthetic(ev):
                continue

            ident_field = (chunk.search_identifier_text or "").lower()
            title_field = (ev.title or "").lower()
            section_field = (chunk.section_title or "").lower()
            body_field = (chunk.chunk_text or "").lower()
            combined_tokens = Counter(
                _TOKEN_SPLIT_RE.findall(f"{ident_field} {title_field} {section_field} {body_field}")
            )

            score = 0.0
            matched_terms = 0
            for term in terms:
                tf = 0.0
                if term in ident_field:
                    tf += 3.0
                if term in title_field:
                    tf += 2.2
                if term in section_field:
                    tf += 1.5
                if term in body_field:
                    tf += 1.0 + math.log1p(combined_tokens.get(term, 1))
                if tf > 0.0:
                    matched_terms += 1
                    score += tf

            if matched_terms == 0:
                continue

            # Reward matching a higher fraction of query terms + exact phrase matches
            coverage = matched_terms / max(1, len(raw_terms or terms))
            phrase_bonus = 2.0 if len(query_lower) >= 4 and query_lower in body_field else 0.0
            raw_rank = (score * (0.5 + 0.5 * coverage)) + phrase_bonus
            normalized = raw_rank / (raw_rank + 4.0)
            scored.append((normalized, chunk))

        scored.sort(key=lambda item: (-item[0], str(item[1].id)))
        return [
            KeywordChunkMatch(
                chunk=chunk,
                evidence=chunk.evidence_item,
                score=score_val,
                rank=idx,
            )
            for idx, (score_val, chunk) in enumerate(scored[:limit], start=1)
        ]

    def get_project_indexing_summary(
        self,
        *,
        project_id: uuid.UUID,
        include_synthetic: bool = False,
    ) -> ProjectIndexingSummaryCounts:
        items = list(
            self._session.execute(
                select(EvidenceItem).where(
                    EvidenceItem.project_id == project_id,
                    EvidenceItem.deleted_at.is_(None),
                    EvidenceItem.processing_status != EvidenceProcessingStatus.DELETED.value,
                )
            )
            .scalars()
            .all()
        )

        status_counts: dict[str, int] = {
            status.value: 0
            for status in EvidenceIndexingStatus
            if status != EvidenceIndexingStatus.DELETED
        }
        eligible_ids: list[uuid.UUID] = []
        latest_indexed_at: datetime | None = None
        models_seen: set[str] = set()
        versions_seen: set[str] = set()

        for item in items:
            if not include_synthetic and self.is_item_synthetic(item):
                continue
            if item.processing_status not in {
                EvidenceProcessingStatus.EXTRACTED.value,
                EvidenceProcessingStatus.PARTIALLY_EXTRACTED.value,
            }:
                continue
            eligible_ids.append(item.id)
            st = item.indexing_status or EvidenceIndexingStatus.NOT_INDEXED.value
            status_counts[st] = status_counts.get(st, 0) + 1
            if item.indexed_at is not None and (
                latest_indexed_at is None or item.indexed_at > latest_indexed_at
            ):
                latest_indexed_at = item.indexed_at
            if item.embedding_model:
                models_seen.add(item.embedding_model)
            if item.index_version:
                versions_seen.add(item.index_version)

        total_chunks = 0
        indexed_chunks = 0
        pending_vector_chunks = 0
        failed_chunks = 0

        if eligible_ids:
            chunk_rows = list(
                self._session.execute(
                    select(
                        EvidenceChunk.indexing_status,
                        func.count(EvidenceChunk.id),
                    )
                    .where(
                        EvidenceChunk.project_id == project_id,
                        EvidenceChunk.evidence_id.in_(eligible_ids),
                    )
                    .group_by(EvidenceChunk.indexing_status)
                ).all()
            )
            for c_status, cnt in chunk_rows:
                c_int = int(cnt or 0)
                total_chunks += c_int
                if c_status == ChunkIndexingStatus.INDEXED.value:
                    indexed_chunks += c_int
                elif c_status in {
                    ChunkIndexingStatus.CHUNKED.value,
                    ChunkIndexingStatus.EMBEDDED.value,
                    ChunkIndexingStatus.PARTIALLY_INDEXED.value,
                }:
                    pending_vector_chunks += c_int
                elif c_status == ChunkIndexingStatus.FAILED.value:
                    failed_chunks += c_int

        active_jobs = int(
            self._session.execute(
                select(func.count())
                .select_from(BackgroundJob)
                .where(
                    BackgroundJob.project_id == project_id,
                    BackgroundJob.job_type.in_(_INDEXING_JOB_TYPES),
                    BackgroundJob.status.in_(
                        (
                            BackgroundJobStatus.QUEUED.value,
                            BackgroundJobStatus.RUNNING.value,
                        )
                    ),
                )
            ).scalar_one()
        )

        return ProjectIndexingSummaryCounts(
            total_eligible_evidence=len(eligible_ids),
            status_counts=status_counts,
            total_chunks=total_chunks,
            indexed_chunks=indexed_chunks,
            pending_vector_chunks=pending_vector_chunks,
            failed_chunks=failed_chunks,
            active_indexing_jobs=active_jobs,
            latest_indexed_at=latest_indexed_at,
            distinct_embedding_models=tuple(sorted(models_seen)),
            distinct_index_versions=tuple(sorted(versions_seen)),
        )

    def list_project_evidence_ids_for_reindex(
        self,
        *,
        project_id: uuid.UUID,
        evidence_ids: Sequence[uuid.UUID] | None = None,
        include_synthetic: bool = False,
    ) -> list[uuid.UUID]:
        stmt = select(EvidenceItem).where(
            EvidenceItem.project_id == project_id,
            EvidenceItem.deleted_at.is_(None),
            EvidenceItem.processing_status.in_(
                (
                    EvidenceProcessingStatus.EXTRACTED.value,
                    EvidenceProcessingStatus.PARTIALLY_EXTRACTED.value,
                )
            ),
        )
        if evidence_ids:
            stmt = stmt.where(EvidenceItem.id.in_(list(evidence_ids)))
        stmt = stmt.order_by(EvidenceItem.created_at.asc(), EvidenceItem.id.asc())
        items = list(self._session.execute(stmt).scalars().all())
        return [
            item.id
            for item in items
            if include_synthetic or not self.is_item_synthetic(item)
        ]

    def rebuild_pg_fts_for_evidence(
        self,
        *,
        evidence: EvidenceItem,
    ) -> int:
        """Rebuild PG TSVECTOR weights for existing canonical chunks without re-embedding."""
        chunks = self.list_chunks_for_evidence(evidence.id)
        if self._dialect_name() != "postgresql":
            return len(chunks)
        for chunk in chunks:
            chunk.search_vector = self._build_pg_tsvector_expr(
                title=evidence.title,
                section_title=chunk.section_title,
                identifier_text=chunk.search_identifier_text,
                chunk_text=chunk.chunk_text,
            )
        self._session.flush()
        return len(chunks)
