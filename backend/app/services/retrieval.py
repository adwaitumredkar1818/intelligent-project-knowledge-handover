"""Permission-aware hybrid retrieval, RRF fusion, PG FTS + Chroma orchestration, and health."""

from __future__ import annotations

import logging
import re
import time
import uuid
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from sqlalchemy.orm import Session

from app.core.config import Settings
from app.core.exceptions import (
    BadRequestError,
    ConflictError,
    ForbiddenError,
    NotFoundError,
    ServiceUnavailableError,
)
from app.models.enums import (
    AuditOutcome,
    BackgroundJobType,
    EvidenceIndexingStatus,
    OrganisationStatus,
    ProjectStatus,
    SearchMode,
)
from app.models.evidence import EvidenceChunk, EvidenceItem
from app.repositories.chunk import EvidenceChunkRepository, KeywordChunkMatch
from app.repositories.job import BackgroundJobRepository
from app.schemas.evidence import BackgroundJobResponse
from app.schemas.retrieval import (
    ChunkDetailResponse,
    IndexHealthResponse,
    ProjectIndexingStatusResponse,
    ProjectSearchRequest,
    ProjectSearchResponse,
    ReindexRequest,
    ReindexResponse,
    SearchCitation,
    SearchResultItem,
    SearchResultScores,
)
from app.services.audit import AuditService
from app.services.embedding import EmbeddingExecutionError, EmbeddingService
from app.services.evidence import to_background_job_response
from app.services.integrations.access_policy import SourceAccessPolicyService
from app.services.rbac import ProjectContext
from app.services.vector_store import VectorQueryHit, VectorStoreClient, VectorStoreError

logger = logging.getLogger("app.services.retrieval")

_EXCERPT_TOKEN_RE = re.compile(r"[A-Za-z0-9_./:-]{2,}")

_PROJECT_INDEXING_ACTIVE_TYPES: tuple[str, ...] = (
    BackgroundJobType.EVIDENCE_REINDEXING.value,
)


@dataclass(frozen=True, slots=True)
class _ValidatedSemanticHit:
    chunk: EvidenceChunk
    evidence: EvidenceItem
    similarity: float
    rank: int


def _build_citation(*, chunk: EvidenceChunk, evidence: EvidenceItem) -> SearchCitation:
    """Build provenance-complete citation omitting all storage keys and internal paths."""
    return SearchCitation(
        evidence_id=evidence.id,
        chunk_id=chunk.id,
        chunk_index=int(chunk.chunk_index),
        source_type=evidence.source_type,
        source_provider=evidence.source_provider,
        category=evidence.category,
        source_external_id=evidence.source_external_id,
        source_url=evidence.source_url,
        title=evidence.title,
        original_filename=evidence.original_filename,
        section_title=chunk.section_title,
        page_number=chunk.page_number,
        char_start=int(chunk.char_start),
        char_end=int(chunk.char_end),
        source_author_identity=chunk.source_author_identity or evidence.source_author_identity,
        source_created_at=chunk.source_created_at or evidence.source_created_at,
        extracted_at=evidence.extracted_at,
        content_hash=evidence.content_hash,
        chunk_content_hash=chunk.chunk_content_hash,
        acl_scope=evidence.acl_scope,
        is_synthetic=EvidenceChunkRepository.is_item_synthetic(evidence),
    )


def _build_bounded_excerpt(text: str, query: str, *, max_chars: int = 320) -> str:
    """Extract a clean readable excerpt centered near the first query token match."""
    cleaned = " ".join(text.split())
    if len(cleaned) <= max_chars:
        return cleaned

    lowered = cleaned.lower()
    best_pos = -1
    for tok in _EXCERPT_TOKEN_RE.findall(query.lower()):
        idx = lowered.find(tok)
        if idx != -1:
            best_pos = idx
            break

    if best_pos <= 40:
        cut = cleaned.rfind(" ", 0, max_chars - 3)
        if cut < int(max_chars * 0.5):
            cut = max_chars - 3
        return f"{cleaned[:cut].rstrip()}..."

    start = max(0, best_pos - 70)
    if start > 0:
        ws = cleaned.find(" ", start, start + 30)
        if ws != -1:
            start = ws + 1
    end = min(len(cleaned), start + max_chars - 6)
    if end < len(cleaned):
        ws_end = cleaned.rfind(" ", start + 80, end)
        if ws_end != -1:
            end = ws_end
    prefix = "..." if start > 0 else ""
    suffix = "..." if end < len(cleaned) else ""
    return f"{prefix}{cleaned[start:end].strip()}{suffix}"


def _as_utc(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def _collapse_or(clauses: list[dict[str, Any]]) -> dict[str, Any]:
    if len(clauses) == 1:
        return clauses[0]
    return {"$or": clauses}


def _collapse_and(clauses: list[dict[str, Any]]) -> dict[str, Any]:
    if len(clauses) == 1:
        return clauses[0]
    return {"$and": clauses}


class HybridRetrievalService:
    """Permission-aware PG FTS + ChromaDB semantic retrieval, RRF fusion, and reindex manager."""

    def __init__(
        self,
        *,
        session: Session,
        settings: Settings,
        chunk_repository: EvidenceChunkRepository,
        job_repository: BackgroundJobRepository,
        embedding_service: EmbeddingService,
        vector_store: VectorStoreClient,
        audit_service: AuditService,
        access_policy_service: SourceAccessPolicyService | None = None,
    ) -> None:
        self._session = session
        self._settings = settings
        self._chunk_repo = chunk_repository
        self._job_repo = job_repository
        self._embedding = embedding_service
        self._vector_store = vector_store
        self._audit = audit_service
        self._access_policy = access_policy_service or SourceAccessPolicyService()

    def search_project(
        self,
        *,
        project_ctx: ProjectContext,
        payload: ProjectSearchRequest,
    ) -> ProjectSearchResponse:
        """Execute hybrid, keyword, or semantic search with strict PG ACL enforcement."""
        started = time.perf_counter()
        top_k = payload.top_k or self._settings.retrieval.default_top_k
        if top_k > self._settings.retrieval.max_top_k:
            raise BadRequestError(
                f"Requested top_k ({top_k}) exceeds configured maximum "
                f"({self._settings.retrieval.max_top_k}).",
                code="TOP_K_EXCEEDED",
            )

        filters = payload.filters
        source_types = (
            [item.value for item in filters.source_types] if filters.source_types else None
        )
        categories = [item.value for item in filters.categories] if filters.categories else None
        chunk_types = [item.value for item in filters.chunk_types] if filters.chunk_types else None
        evidence_ids = list(filters.evidence_ids) if filters.evidence_ids else None

        user_id = project_ctx.principal.user.id
        has_project_manage = project_ctx.has_permission("project.manage")
        allowed_restricted_ids, project_member_ids, revoked_ids = (
            self._chunk_repo.get_allowed_and_revoked_policies(
                project_id=project_ctx.project.id,
                viewer_user_id=user_id,
            )
        )
        # Every policy where this viewer is explicitly allowed (restricted or public)
        combined_pg_allowed_ids = list(dict.fromkeys([*allowed_restricted_ids]))

        # Extra candidate overfetch when author/post-filter constraints or ACL pruning apply
        multiplier = self._settings.retrieval.candidate_multiplier
        if filters.author:
            multiplier = max(multiplier, 6)
        candidate_limit = max(
            self._settings.retrieval.min_candidate_limit,
            top_k * multiplier,
        )

        keyword_matches: list[KeywordChunkMatch] = []
        semantic_matches: list[_ValidatedSemanticHit] = []
        mode_requested = payload.mode
        mode_executed = payload.mode
        degraded = False
        degraded_reason: str | None = None
        warnings: list[str] = []

        if mode_requested in {SearchMode.KEYWORD, SearchMode.HYBRID}:
            raw_kw = self._chunk_repo.keyword_search(
                project_id=project_ctx.project.id,
                query=payload.query,
                limit=candidate_limit,
                viewer_user_id=user_id,
                has_project_manage=has_project_manage,
                allowed_policy_ids=combined_pg_allowed_ids,
                revoked_policy_ids=revoked_ids,
                source_types=source_types,
                categories=categories,
                chunk_types=chunk_types,
                author=filters.author,
                evidence_ids=evidence_ids,
                date_from=filters.date_from,
                date_to=filters.date_to,
                include_synthetic=filters.include_synthetic,
            )
            # Re-verify every keyword row through canonical SourceAccessPolicyService
            rank_counter = 0
            for kw_hit in raw_kw:
                if not self._passes_post_validation(
                    chunk=kw_hit.chunk,
                    evidence=kw_hit.evidence,
                    project_id=project_ctx.project.id,
                    user_id=user_id,
                    has_project_manage=has_project_manage,
                    include_synthetic=filters.include_synthetic,
                    source_types=source_types,
                    categories=categories,
                    chunk_types=chunk_types,
                    author=filters.author,
                    evidence_ids=evidence_ids,
                    date_from=filters.date_from,
                    date_to=filters.date_to,
                ):
                    continue
                if kw_hit.score < self._settings.retrieval.min_keyword_score:
                    continue
                rank_counter += 1
                keyword_matches.append(
                    KeywordChunkMatch(
                        chunk=kw_hit.chunk,
                        evidence=kw_hit.evidence,
                        score=kw_hit.score,
                        rank=rank_counter,
                    )
                )

        if mode_requested in {SearchMode.SEMANTIC, SearchMode.HYBRID}:
            chroma_where = self._build_chroma_where_filter(
                organisation_id=project_ctx.organisation.id,
                project_id=project_ctx.project.id,
                user_id=user_id,
                has_project_manage=has_project_manage,
                allowed_restricted_ids=allowed_restricted_ids,
                project_member_policy_ids=project_member_ids,
                source_types=source_types,
                categories=categories,
                chunk_types=chunk_types,
                evidence_ids=evidence_ids,
                date_from=filters.date_from,
                date_to=filters.date_to,
                include_synthetic=filters.include_synthetic,
            )
            try:
                query_vec = self._embedding.embed_query(payload.query)
                raw_vec_hits = self._vector_store.query_vectors(
                    query_embedding=query_vec,
                    top_k=candidate_limit,
                    where=chroma_where,
                )
                semantic_matches = self._revalidate_semantic_hits(
                    hits=raw_vec_hits,
                    project_id=project_ctx.project.id,
                    user_id=user_id,
                    has_project_manage=has_project_manage,
                    include_synthetic=filters.include_synthetic,
                    source_types=source_types,
                    categories=categories,
                    chunk_types=chunk_types,
                    author=filters.author,
                    evidence_ids=evidence_ids,
                    date_from=filters.date_from,
                    date_to=filters.date_to,
                )
            except (EmbeddingExecutionError, VectorStoreError) as exc:
                if mode_requested == SearchMode.SEMANTIC:
                    raise ServiceUnavailableError(
                        exc.message,
                        code=exc.code,
                    ) from exc
                degraded = True
                degraded_reason = exc.code
                mode_executed = SearchMode.KEYWORD
                warnings.append(
                    f"Semantic vector search is currently unavailable ({exc.code}); "
                    "served results using PostgreSQL full-text keyword search only."
                )
                logger.warning(
                    "Hybrid search degraded cleanly to PostgreSQL keyword search.",
                    extra={
                        "project_id": str(project_ctx.project.id),
                        "error_code": exc.code,
                    },
                )

        fused_items = self._fuse_and_rank(
            query=payload.query,
            mode=mode_executed,
            top_k=top_k,
            keyword_matches=keyword_matches,
            semantic_matches=semantic_matches,
        )

        latency_ms = max(0, int((time.perf_counter() - started) * 1000))

        self._audit.record_event(
            event_type="evidence.search_executed",
            resource_type="project",
            actor_user_id=user_id,
            organisation_id=project_ctx.organisation.id,
            project_id=project_ctx.project.id,
            resource_id=str(project_ctx.project.id),
            metadata={
                "mode_requested": mode_requested.value,
                "mode_executed": mode_executed.value,
                "degraded": degraded,
                "degraded_reason": degraded_reason,
                "top_k": top_k,
                "total_returned": len(fused_items),
                "latency_ms": latency_ms,
                "include_synthetic": filters.include_synthetic,
            },
            message=(
                f"Executed {mode_executed.value} evidence search returning "
                f"{len(fused_items)} result(s)."
            ),
        )
        self._session.commit()

        return ProjectSearchResponse(
            project_id=project_ctx.project.id,
            query=payload.query,
            mode_requested=mode_requested,
            mode_executed=mode_executed,
            degraded=degraded,
            degraded_reason=degraded_reason,
            warnings=warnings,
            total_returned=len(fused_items),
            latency_ms=latency_ms,
            embedding_model=self._embedding.model_name,
            index_version=self._vector_store.index_version,
            results=fused_items,
        )

    def _build_chroma_where_filter(
        self,
        *,
        organisation_id: uuid.UUID,
        project_id: uuid.UUID,
        user_id: uuid.UUID,
        has_project_manage: bool,
        allowed_restricted_ids: Sequence[uuid.UUID],
        project_member_policy_ids: Sequence[uuid.UUID],
        source_types: Sequence[str] | None,
        categories: Sequence[str] | None,
        chunk_types: Sequence[str] | None,
        evidence_ids: Sequence[uuid.UUID] | None,
        date_from: Any,
        date_to: Any,
        include_synthetic: bool,
    ) -> dict[str, Any]:
        """Construct Chroma metadata filter limiting candidate vectors to authorised scopes."""
        and_clauses: list[dict[str, Any]] = [
            {"organisation_id": {"$eq": str(organisation_id)}},
            {"project_id": {"$eq": str(project_id)}},
        ]
        if not include_synthetic:
            and_clauses.append({"is_synthetic": {"$eq": False}})

        # Pre-retrieval ACL bucket clause (post-query PG revalidation STILL always runs)
        acl_or_clauses: list[dict[str, Any]] = [
            {"permission_scope_key": {"$eq": "project_members"}},
        ]
        seen_scope_keys: set[str] = {"project_members"}

        for pub_pid in project_member_policy_ids:
            key = f"public:{pub_pid}"
            if key not in seen_scope_keys:
                seen_scope_keys.add(key)
                acl_or_clauses.append({"permission_scope_key": {"$eq": key}})

        for pid in allowed_restricted_ids:
            for key in (f"policy:{pid}", f"public:{pid}"):
                if key not in seen_scope_keys:
                    seen_scope_keys.add(key)
                    acl_or_clauses.append({"permission_scope_key": {"$eq": key}})

        if has_project_manage:
            acl_or_clauses.append({"permission_scope_key": {"$eq": "legacy_restricted"}})
        else:
            acl_or_clauses.append(
                {
                    "$and": [
                        {"permission_scope_key": {"$eq": "legacy_restricted"}},
                        {"uploaded_by_user_id": {"$eq": str(user_id)}},
                    ]
                }
            )
        and_clauses.append(_collapse_or(acl_or_clauses))

        if source_types:
            if len(source_types) == 1:
                and_clauses.append({"source_type": {"$eq": source_types[0]}})
            else:
                and_clauses.append({"source_type": {"$in": list(source_types)}})
        if categories:
            if len(categories) == 1:
                and_clauses.append({"category": {"$eq": categories[0]}})
            else:
                and_clauses.append({"category": {"$in": list(categories)}})
        if chunk_types:
            if len(chunk_types) == 1:
                and_clauses.append({"chunk_type": {"$eq": chunk_types[0]}})
            else:
                and_clauses.append({"chunk_type": {"$in": list(chunk_types)}})
        if evidence_ids:
            str_ids = [str(eid) for eid in evidence_ids]
            if len(str_ids) == 1:
                and_clauses.append({"evidence_id": {"$eq": str_ids[0]}})
            else:
                and_clauses.append({"evidence_id": {"$in": str_ids}})
        if date_from is not None:
            norm_from = _as_utc(date_from)
            if norm_from is not None:
                and_clauses.append({"source_created_ts": {"$gte": int(norm_from.timestamp())}})
        if date_to is not None:
            norm_to = _as_utc(date_to)
            if norm_to is not None:
                and_clauses.append({"source_created_ts": {"$lte": int(norm_to.timestamp())}})

        return _collapse_and(and_clauses)

    def _passes_post_validation(
        self,
        *,
        chunk: EvidenceChunk,
        evidence: EvidenceItem,
        project_id: uuid.UUID,
        user_id: uuid.UUID,
        has_project_manage: bool,
        include_synthetic: bool,
        source_types: Sequence[str] | None,
        categories: Sequence[str] | None,
        chunk_types: Sequence[str] | None,
        author: str | None,
        evidence_ids: Sequence[uuid.UUID] | None,
        date_from: Any,
        date_to: Any,
    ) -> bool:
        """Fail-closed PG & ACL check preventing stale/cross-tenant/revoked vector leakage."""
        if chunk.project_id != project_id or evidence.project_id != project_id:
            return False
        if evidence.deleted_at is not None or evidence.processing_status == "deleted":
            return False
        if not include_synthetic and EvidenceChunkRepository.is_item_synthetic(evidence):
            return False
        if not self._access_policy.can_user_access_evidence(
            evidence=evidence,
            user_id=user_id,
            has_project_manage=has_project_manage,
        ):
            return False
        if source_types and evidence.source_type not in source_types:
            return False
        if categories and evidence.category not in categories:
            return False
        if chunk_types and chunk.chunk_type not in chunk_types:
            return False
        if evidence_ids and evidence.id not in evidence_ids:
            return False
        if author:
            needle = author.strip().lower()
            candidates = (
                (chunk.source_author_identity or "").lower(),
                (evidence.source_author_identity or "").lower(),
            )
            if not any(needle in cand for cand in candidates if cand):
                return False
        eff_dt = _as_utc(
            chunk.source_created_at or evidence.source_created_at or evidence.created_at
        )
        norm_from = _as_utc(date_from)
        norm_to = _as_utc(date_to)
        if norm_from is not None and eff_dt is not None and eff_dt < norm_from:
            return False
        if norm_to is not None and eff_dt is not None and eff_dt > norm_to:
            return False
        return True

    def _revalidate_semantic_hits(
        self,
        *,
        hits: Sequence[VectorQueryHit],
        project_id: uuid.UUID,
        user_id: uuid.UUID,
        has_project_manage: bool,
        include_synthetic: bool,
        source_types: Sequence[str] | None,
        categories: Sequence[str] | None,
        chunk_types: Sequence[str] | None,
        author: str | None,
        evidence_ids: Sequence[uuid.UUID] | None,
        date_from: Any,
        date_to: Any,
    ) -> list[_ValidatedSemanticHit]:
        """Re-hydrate candidate chunks from canonical PostgreSQL & strip unauthorized hits."""
        parsed_ids: list[tuple[VectorQueryHit, uuid.UUID]] = []
        min_sim = self._settings.retrieval.min_semantic_similarity

        for hit in hits:
            if hit.similarity < min_sim:
                continue
            raw_chunk_id = hit.metadata.get("chunk_id")
            if not raw_chunk_id:
                continue
            try:
                parsed_cid = uuid.UUID(str(raw_chunk_id))
            except ValueError:
                continue
            parsed_ids.append((hit, parsed_cid))

        if not parsed_ids:
            return []

        chunk_map = self._chunk_repo.get_many_with_evidence(
            project_id=project_id,
            chunk_ids=list(dict.fromkeys(cid for _, cid in parsed_ids)),
        )

        validated: list[_ValidatedSemanticHit] = []
        seen_chunk_ids: set[uuid.UUID] = set()
        for hit, cid in parsed_ids:
            if cid in seen_chunk_ids:
                continue
            chunk = chunk_map.get(cid)
            if chunk is None:
                continue
            evidence = chunk.evidence_item
            if not self._passes_post_validation(
                chunk=chunk,
                evidence=evidence,
                project_id=project_id,
                user_id=user_id,
                has_project_manage=has_project_manage,
                include_synthetic=include_synthetic,
                source_types=source_types,
                categories=categories,
                chunk_types=chunk_types,
                author=author,
                evidence_ids=evidence_ids,
                date_from=date_from,
                date_to=date_to,
            ):
                continue
            seen_chunk_ids.add(cid)
            validated.append(
                _ValidatedSemanticHit(
                    chunk=chunk,
                    evidence=evidence,
                    similarity=hit.similarity,
                    rank=len(validated) + 1,
                )
            )
        return validated

    def _fuse_and_rank(
        self,
        *,
        query: str,
        mode: SearchMode,
        top_k: int,
        keyword_matches: Sequence[KeywordChunkMatch],
        semantic_matches: Sequence[_ValidatedSemanticHit],
    ) -> list[SearchResultItem]:
        """Combine keyword & semantic candidates via weighted RRF into SearchResultItem list."""
        kw_by_id = {m.chunk.id: m for m in keyword_matches}
        sem_by_id = {m.chunk.id: m for m in semantic_matches}
        all_chunk_ids = list(dict.fromkeys([*kw_by_id.keys(), *sem_by_id.keys()]))

        rrf_k = self._settings.retrieval.rrf_k
        w_kw = self._settings.retrieval.keyword_weight
        w_sem = self._settings.retrieval.semantic_weight
        max_possible_rrf = (w_kw + w_sem) / (rrf_k + 1)
        min_hybrid = self._settings.retrieval.min_hybrid_score

        scored_entries: list[
            tuple[float, int, EvidenceChunk, EvidenceItem, SearchResultScores]
        ] = []

        for cid in all_chunk_ids:
            kw_m = kw_by_id.get(cid)
            sem_m = sem_by_id.get(cid)
            matched_by: list[str] = []
            if kw_m is not None:
                matched_by.append("keyword")
            if sem_m is not None:
                matched_by.append("semantic")

            if kw_m is not None:
                chunk = kw_m.chunk
                evidence = kw_m.evidence
            elif sem_m is not None:
                chunk = sem_m.chunk
                evidence = sem_m.evidence
            else:
                continue

            if mode == SearchMode.KEYWORD:
                if kw_m is None:
                    continue
                final_score = round(kw_m.score, 6)
            elif mode == SearchMode.SEMANTIC:
                if sem_m is None:
                    continue
                final_score = round(sem_m.similarity, 6)
            else:
                kw_rrf = (w_kw / (rrf_k + kw_m.rank)) if kw_m is not None else 0.0
                sem_rrf = (w_sem / (rrf_k + sem_m.rank)) if sem_m is not None else 0.0
                final_score = round(min(1.0, (kw_rrf + sem_rrf) / max_possible_rrf), 6)
                if final_score < min_hybrid:
                    continue

            best_rank_tiebreak = min(
                kw_m.rank if kw_m is not None else 10_000,
                sem_m.rank if sem_m is not None else 10_000,
            )
            scores = SearchResultScores(
                hybrid_score=final_score,
                semantic_score=round(sem_m.similarity, 6) if sem_m is not None else None,
                keyword_score=round(kw_m.score, 6) if kw_m is not None else None,
                semantic_rank=sem_m.rank if sem_m is not None else None,
                keyword_rank=kw_m.rank if kw_m is not None else None,
                matched_by=matched_by,
            )
            scored_entries.append((final_score, best_rank_tiebreak, chunk, evidence, scores))

        scored_entries.sort(key=lambda item: (-item[0], item[1], str(item[2].id)))

        results: list[SearchResultItem] = []
        for idx, (_score, _tie, chunk, evidence, scores) in enumerate(
            scored_entries[:top_k],
            start=1,
        ):
            results.append(
                SearchResultItem(
                    rank=idx,
                    chunk_id=chunk.id,
                    evidence_id=evidence.id,
                    chunk_index=int(chunk.chunk_index),
                    chunk_type=chunk.chunk_type,
                    excerpt=_build_bounded_excerpt(chunk.chunk_text, query),
                    chunk_text=chunk.chunk_text,
                    token_estimate=int(chunk.token_estimate),
                    scores=scores,
                    citation=_build_citation(chunk=chunk, evidence=evidence),
                )
            )
        return results

    def get_chunk_detail(
        self,
        *,
        project_ctx: ProjectContext,
        chunk_id: uuid.UUID,
    ) -> ChunkDetailResponse:
        """Fetch one chunk with parent provenance after enforcing project & source ACL."""
        chunk = self._chunk_repo.get_chunk_with_evidence(
            project_id=project_ctx.project.id,
            chunk_id=chunk_id,
        )
        if chunk is None:
            raise NotFoundError("Evidence chunk was not found.", code="CHUNK_NOT_FOUND")

        evidence = chunk.evidence_item
        self._access_policy.enforce_evidence_access(
            evidence=evidence,
            project_ctx=project_ctx,
            session=self._session,
            audit_service=self._audit,
        )

        return ChunkDetailResponse(
            id=chunk.id,
            organisation_id=chunk.organisation_id,
            project_id=chunk.project_id,
            evidence_id=chunk.evidence_id,
            chunk_index=int(chunk.chunk_index),
            chunk_type=chunk.chunk_type,
            section_title=chunk.section_title,
            page_number=chunk.page_number,
            char_start=int(chunk.char_start),
            char_end=int(chunk.char_end),
            char_count=int(chunk.char_count),
            token_estimate=int(chunk.token_estimate),
            chunk_text=chunk.chunk_text,
            chunk_content_hash=chunk.chunk_content_hash,
            indexing_status=chunk.indexing_status,
            embedding_model=chunk.embedding_model,
            embedding_dimensions=chunk.embedding_dimensions,
            embedded_at=chunk.embedded_at,
            metadata_json=dict(chunk.metadata_json or {}),
            citation=_build_citation(chunk=chunk, evidence=evidence),
            created_at=chunk.created_at,
            updated_at=chunk.updated_at,
        )

    def get_project_indexing_status(
        self,
        *,
        project_ctx: ProjectContext,
    ) -> ProjectIndexingStatusResponse:
        """Return canonical PostgreSQL indexing status counts for a project."""
        summary = self._chunk_repo.get_project_indexing_summary(
            project_id=project_ctx.project.id,
            include_synthetic=False,
        )
        fts_ready = (
            summary.status_counts.get(EvidenceIndexingStatus.INDEXED.value, 0)
            + summary.status_counts.get(EvidenceIndexingStatus.PARTIALLY_INDEXED.value, 0)
        )
        vector_synced = summary.status_counts.get(EvidenceIndexingStatus.INDEXED.value, 0)
        return ProjectIndexingStatusResponse(
            project_id=project_ctx.project.id,
            total_eligible_evidence=summary.total_eligible_evidence,
            status_counts=summary.status_counts,
            total_chunks=summary.total_chunks,
            indexed_chunks=summary.indexed_chunks,
            pending_vector_chunks=summary.pending_vector_chunks,
            failed_chunks=summary.failed_chunks,
            active_indexing_jobs=summary.active_indexing_jobs,
            latest_indexed_at=summary.latest_indexed_at,
            expected_embedding_model=self._embedding.model_name,
            expected_index_version=self._vector_store.index_version,
            observed_embedding_models=list(summary.distinct_embedding_models),
            observed_index_versions=list(summary.distinct_index_versions),
            fts_ready_items=fts_ready,
            vector_synced_items=vector_synced,
        )

    def trigger_reindex(
        self,
        *,
        project_ctx: ProjectContext,
        payload: ReindexRequest,
    ) -> ReindexResponse:
        """Enqueue asynchronous project-wide or targeted reindexing in PostgreSQL."""
        if project_ctx.organisation.status != OrganisationStatus.ACTIVE.value:
            raise ConflictError(
                f"Organisation is '{project_ctx.organisation.status}' and cannot reindex.",
                code="ORGANISATION_NOT_ACTIVE",
            )
        if project_ctx.project.status == ProjectStatus.ARCHIVED.value:
            raise ConflictError(
                "Project workspace is archived and cannot reindex evidence.",
                code="PROJECT_ARCHIVED",
            )

        can_reindex = project_ctx.has_permission("project.manage") or (
            project_ctx.project_membership is not None
            and project_ctx.has_permission("project.evidence.contribute")
        )
        if not can_reindex:
            self._audit.record_event(
                event_type="evidence.reindex_denied",
                resource_type="project",
                actor_user_id=project_ctx.principal.user.id,
                organisation_id=project_ctx.organisation.id,
                project_id=project_ctx.project.id,
                resource_id=str(project_ctx.project.id),
                outcome=AuditOutcome.DENIED.value,
                message="Denied project reindex without manage or contribute permission.",
                level=logging.WARNING,
            )
            self._session.commit()
            raise ForbiddenError(
                "You do not have permission to reindex evidence in this project.",
                code="FORBIDDEN",
            )

        target_ids = self._chunk_repo.list_project_evidence_ids_for_reindex(
            project_id=project_ctx.project.id,
            evidence_ids=payload.evidence_ids,
            include_synthetic=False,
        )
        if payload.evidence_ids and len(target_ids) != len(set(payload.evidence_ids)):
            raise NotFoundError(
                "One or more target evidence items were not found or cannot be reindexed.",
                code="EVIDENCE_NOT_FOUND",
            )

        existing_job = self._job_repo.has_active_job_for_project(
            project_id=project_ctx.project.id,
            job_types=_PROJECT_INDEXING_ACTIVE_TYPES,
        )
        if existing_job is not None:
            return ReindexResponse(
                project_id=project_ctx.project.id,
                target=payload.target,
                target_evidence_count=len(target_ids),
                already_running=True,
                job=to_background_job_response(existing_job),
            )

        force_rechunk = (
            bool(payload.force_rechunk)
            if payload.force_rechunk is not None
            else (payload.target == "full")
        )
        job = self._job_repo.create_job(
            organisation_id=project_ctx.organisation.id,
            project_id=project_ctx.project.id,
            evidence_id=target_ids[0] if len(target_ids) == 1 else None,
            triggered_by_user_id=project_ctx.principal.user.id,
            job_type=BackgroundJobType.EVIDENCE_REINDEXING.value,
            max_attempts=self._settings.ingestion.worker_max_attempts,
            priority=90,
            payload_json={
                "target": payload.target,
                "force_rechunk": force_rechunk,
                "evidence_ids": [str(eid) for eid in (payload.evidence_ids or [])],
            },
        )
        self._audit.record_event(
            event_type="evidence.reindex_queued",
            resource_type="project",
            actor_user_id=project_ctx.principal.user.id,
            organisation_id=project_ctx.organisation.id,
            project_id=project_ctx.project.id,
            resource_id=str(project_ctx.project.id),
            metadata={
                "job_id": str(job.id),
                "target": payload.target,
                "force_rechunk": force_rechunk,
                "target_evidence_count": len(target_ids),
            },
            message=(
                f"Queued asynchronous '{payload.target}' reindex job for "
                f"{len(target_ids)} item(s)."
            ),
        )
        self._session.commit()
        self._session.refresh(job)
        return ReindexResponse(
            project_id=project_ctx.project.id,
            target=payload.target,
            target_evidence_count=len(target_ids),
            already_running=False,
            job=to_background_job_response(job),
        )

    def get_index_health(
        self,
        *,
        project_ctx: ProjectContext,
    ) -> IndexHealthResponse:
        """Report PostgreSQL FTS readiness and ChromaDB vector collection health cleanly."""
        summary = self.get_project_indexing_status(project_ctx=project_ctx)

        chroma_reachable = False
        collection_exists = False
        vector_count: int | None = None
        chroma_space: str | None = None
        collection_compatible = True
        compatibility_error: str | None = None

        try:
            info = self._vector_store.inspect_collection()
            chroma_reachable = True
            if info is not None:
                collection_exists = True
                chroma_space = info.space
                vector_count = self._vector_store.count_records()
            else:
                vector_count = 0
        except VectorStoreError as exc:
            if exc.code.startswith("VECTOR_COLLECTION_"):
                chroma_reachable = True
                collection_exists = True
                collection_compatible = False
                compatibility_error = exc.message
            else:
                chroma_reachable = False
                collection_compatible = False
                compatibility_error = exc.message

        return IndexHealthResponse(
            project_id=project_ctx.project.id,
            postgresql_fts_ready=True,
            chroma_reachable=chroma_reachable,
            chroma_collection_name=self._vector_store.collection_name,
            chroma_collection_exists=collection_exists,
            chroma_vector_count=vector_count,
            chroma_space=chroma_space,
            expected_embedding_model=self._embedding.model_name,
            expected_index_version=self._vector_store.index_version,
            expected_dimensions=self._embedding.expected_dimensions,
            collection_compatible=collection_compatible,
            compatibility_error=compatibility_error,
            indexing_summary=summary,
        )

    def get_indexing_job_status(
        self,
        *,
        project_ctx: ProjectContext,
        job_id: uuid.UUID,
    ) -> BackgroundJobResponse:
        """Inspect one project-scoped indexing or reindex job cleanly."""
        job = self._job_repo.get_by_id(job_id)
        if job is None or job.project_id != project_ctx.project.id:
            raise NotFoundError("Indexing job was not found.", code="JOB_NOT_FOUND")
        if job.job_type not in {
            BackgroundJobType.EVIDENCE_CHUNKING.value,
            BackgroundJobType.EVIDENCE_EMBEDDING.value,
            BackgroundJobType.EVIDENCE_INDEXING.value,
            BackgroundJobType.EVIDENCE_REINDEXING.value,
            BackgroundJobType.EVIDENCE_INDEX_CLEANUP.value,
        }:
            raise NotFoundError("Indexing job was not found.", code="JOB_NOT_FOUND")
        return to_background_job_response(job)
