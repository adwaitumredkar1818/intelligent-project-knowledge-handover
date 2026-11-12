"""Deterministic in-memory EmbeddingService and Chroma VectorStoreClient fakes for tests."""

from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import Any

from app.services.embedding import EmbeddingExecutionError
from app.services.vector_store import (
    VectorCollectionInfo,
    VectorQueryHit,
    VectorStoreError,
    VectorUpsertRecord,
    build_chroma_collection_name,
    sanitize_vector_metadata,
)


def _text_to_unit_vector(text: str, dims: int = 64) -> list[float]:
    """Produce a deterministic, semantically meaningful bag-of-topics toy vector."""
    lower = text.lower()
    buckets = [
        ("postgres", "postgresql", "database", "tsvector", "gin", "canonical", "schema"),
        ("chroma", "vector", "nomic", "embedding", "semantic", "cosine", "hnsw"),
        ("auth", "jwt", "refresh", "cookie", "session", "oauth", "rbac", "password"),
        ("github", "pull", "commit", "repository", "branch", "merge"),
        ("jira", "issue", "ticket", "sprint", "backlog", "worklog", "nex"),
        ("ocr", "pdf", "scan", "glm", "scanned", "image"),
        ("failover", "backup", "replica", "outage", "retry", "recovery", "latency"),
        ("handover", "ownership", "onboarding", "responsibility", "runbook", "risk"),
    ]
    vec = [0.05] * dims
    for idx, keywords in enumerate(buckets[:dims]):
        for kw in keywords:
            if kw in lower:
                vec[idx] += 1.0
    # Add light character bigram signal so arbitrary unique phrases still align cleanly
    for ch_idx, ch in enumerate(lower[:64]):
        vec[(ord(ch) + ch_idx) % dims] += 0.02
    norm = math.sqrt(sum(v * v for v in vec)) or 1.0
    return [v / norm for v in vec]


def _cosine_distance(a: Sequence[float], b: Sequence[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b, strict=True))
    na = math.sqrt(sum(x * x for x in a)) or 1.0
    nb = math.sqrt(sum(y * y for y in b)) or 1.0
    sim = max(-1.0, min(1.0, dot / (na * nb)))
    return max(0.0, 1.0 - sim)


def matches_chroma_where(meta: dict[str, Any], where: dict[str, Any] | None) -> bool:
    """Evaluate Chroma v2 metadata `where` filter expressions accurately in memory."""
    if not where:
        return True
    for key, cond in where.items():
        if key == "$and":
            if not all(matches_chroma_where(meta, sub) for sub in cond):
                return False
            continue
        if key == "$or":
            if not any(matches_chroma_where(meta, sub) for sub in cond):
                return False
            continue
        val = meta.get(key)
        if isinstance(cond, dict):
            for op, target in cond.items():
                if op == "$eq":
                    if val != target:
                        return False
                elif op == "$ne":
                    if val == target:
                        return False
                elif op == "$in":
                    if val not in target:
                        return False
                elif op == "$nin":
                    if val in target:
                        return False
                elif op == "$gte":
                    if val is None or val < target:
                        return False
                elif op == "$lte":
                    if val is None or val > target:
                        return False
                elif op == "$gt":
                    if val is None or val <= target:
                        return False
                elif op == "$lt":
                    if val is None or val >= target:
                        return False
        else:
            if val != cond:
                return False
    return True


@dataclass
class InMemoryEmbeddingService:
    """Test double implementing EmbeddingService with configurable failure injection."""

    model: str = "nomic-embed-text"
    dims: int = 64
    fail_documents: bool = False
    fail_query: bool = False
    retryable_failure: bool = True
    embed_calls: list[list[str]] = field(default_factory=list)

    @property
    def model_name(self) -> str:
        return self.model

    @property
    def expected_dimensions(self) -> int:
        return self.dims

    def embed_documents(self, texts: Sequence[str]) -> list[list[float]]:
        self.embed_calls.append(list(texts))
        if self.fail_documents:
            raise EmbeddingExecutionError(
                code="EMBEDDING_UNAVAILABLE",
                message="Simulated Ollama embedding outage.",
                retryable=self.retryable_failure,
            )
        return [_text_to_unit_vector(t, dims=self.dims) for t in texts]

    def embed_query(self, text: str) -> list[float]:
        if self.fail_query:
            raise EmbeddingExecutionError(
                code="EMBEDDING_UNAVAILABLE",
                message="Simulated Ollama query embedding outage.",
                retryable=self.retryable_failure,
            )
        return _text_to_unit_vector(text, dims=self.dims)


class InMemoryVectorStoreClient:
    """Test double implementing Chroma VectorStoreClient with optional fault & leak simulation."""

    def __init__(
        self,
        *,
        collection_prefix: str = "ipkrh_test",
        embedding_model: str = "nomic-embed-text",
        index_version: str = "v1",
        expected_dimensions: int = 64,
    ) -> None:
        self._collection_name = build_chroma_collection_name(
            prefix=collection_prefix,
            embedding_model=embedding_model,
            index_version=index_version,
        )
        self._embedding_model = embedding_model
        self._index_version = index_version
        self._expected_dimensions = expected_dimensions
        self.collection_created = False
        self.records: dict[str, tuple[list[float], dict[str, Any]]] = {}
        self.fail_upsert = False
        self.fail_query = False
        self.fail_delete = False
        self.fail_inspect = False
        # When True, `query_vectors` ignores `where` to test mandatory PG post-revalidation
        self.bypass_where_to_simulate_stale_chroma = False

    @property
    def collection_name(self) -> str:
        return self._collection_name

    @property
    def embedding_model(self) -> str:
        return self._embedding_model

    @property
    def index_version(self) -> str:
        return self._index_version

    @property
    def expected_dimensions(self) -> int:
        return self._expected_dimensions

    def ensure_collection(self) -> VectorCollectionInfo:
        if self.fail_inspect:
            raise VectorStoreError(
                code="CHROMA_UNAVAILABLE",
                message="Simulated ChromaDB unavailability.",
                retryable=True,
            )
        self.collection_created = True
        return VectorCollectionInfo(
            collection_id="inmem-col-001",
            name=self._collection_name,
            space="cosine",
            dimension=self._expected_dimensions,
            metadata={
                "embedding_model": self._embedding_model,
                "index_version": self._index_version,
                "dimensions": self._expected_dimensions,
            },
        )

    def inspect_collection(self) -> VectorCollectionInfo | None:
        if self.fail_inspect:
            raise VectorStoreError(
                code="CHROMA_UNAVAILABLE",
                message="Simulated ChromaDB unavailability.",
                retryable=True,
            )
        if not self.collection_created:
            return None
        return VectorCollectionInfo(
            collection_id="inmem-col-001",
            name=self._collection_name,
            space="cosine",
            dimension=self._expected_dimensions,
            metadata={
                "embedding_model": self._embedding_model,
                "index_version": self._index_version,
                "dimensions": self._expected_dimensions,
            },
        )

    def upsert_records(self, records: Sequence[VectorUpsertRecord]) -> None:
        if self.fail_upsert:
            raise VectorStoreError(
                code="CHROMA_UNAVAILABLE",
                message="Simulated ChromaDB upsert outage.",
                retryable=True,
            )
        self.ensure_collection()
        for rec in records:
            self.records[rec.vector_id] = (
                [float(v) for v in rec.embedding],
                sanitize_vector_metadata(rec.metadata),
            )

    def query_vectors(
        self,
        *,
        query_embedding: Sequence[float],
        top_k: int,
        where: dict[str, Any] | None = None,
    ) -> list[VectorQueryHit]:
        if self.fail_query:
            raise VectorStoreError(
                code="CHROMA_UNAVAILABLE",
                message="Simulated ChromaDB query outage.",
                retryable=True,
            )
        if not self.collection_created:
            return []
        hits: list[VectorQueryHit] = []
        for vec_id, (vec, meta) in self.records.items():
            if not self.bypass_where_to_simulate_stale_chroma and not matches_chroma_where(
                meta, where
            ):
                continue
            dist = _cosine_distance(query_embedding, vec)
            sim = max(0.0, min(1.0, 1.0 - dist))
            hits.append(
                VectorQueryHit(
                    vector_id=vec_id,
                    distance=dist,
                    similarity=sim,
                    metadata=dict(meta),
                )
            )
        hits.sort(key=lambda h: (h.distance, h.vector_id))
        return hits[:top_k]

    def delete_records(
        self,
        *,
        ids: Sequence[str] | None = None,
        where: dict[str, Any] | None = None,
    ) -> int:
        if self.fail_delete:
            raise VectorStoreError(
                code="CHROMA_UNAVAILABLE",
                message="Simulated ChromaDB delete outage.",
                retryable=True,
            )
        if not self.collection_created:
            return 0
        to_remove: list[str] = []
        id_set = set(ids or [])
        for vec_id, (_vec, meta) in self.records.items():
            if ids and vec_id in id_set:
                to_remove.append(vec_id)
            elif where and matches_chroma_where(meta, where):
                to_remove.append(vec_id)
        for vec_id in set(to_remove):
            self.records.pop(vec_id, None)
        return len(set(to_remove))

    def count_records(self) -> int:
        if self.fail_inspect:
            raise VectorStoreError(
                code="CHROMA_UNAVAILABLE",
                message="Simulated ChromaDB inspect outage.",
                retryable=True,
            )
        if not self.collection_created:
            return 0
        return len(self.records)

    def delete_collection(self) -> bool:
        existed = self.collection_created
        self.collection_created = False
        self.records.clear()
        return existed
