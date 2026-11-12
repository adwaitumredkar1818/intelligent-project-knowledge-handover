"""Replaceable vector store abstraction and ChromaDB HTTP v2 REST adapter."""

from __future__ import annotations

import logging
import math
import re
import uuid
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any, Protocol

import httpx

logger = logging.getLogger("app.services.vector_store")

_ALLOWED_CHROMA_METADATA_KEYS: frozenset[str] = frozenset(
    {
        "organisation_id",
        "project_id",
        "evidence_id",
        "chunk_id",
        "chunk_index",
        "chunk_type",
        "source_type",
        "category",
        "acl_scope",
        "permission_scope_key",
        "source_access_policy_id",
        "uploaded_by_user_id",
        "is_synthetic",
        "source_created_ts",
    }
)


class VectorStoreError(RuntimeError):
    """Typed failure raised when ChromaDB vector operations fail or detect drift."""

    def __init__(self, *, code: str, message: str, retryable: bool = True) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.retryable = retryable


@dataclass(frozen=True, slots=True)
class VectorCollectionInfo:
    """Resolved ChromaDB collection identity, metric configuration, and compatibility metadata."""

    collection_id: str
    name: str
    space: str | None
    dimension: int | None
    metadata: dict[str, Any]


@dataclass(frozen=True, slots=True)
class VectorUpsertRecord:
    """Single deterministic vector entry targeting ChromaDB (without secrets or raw blobs)."""

    vector_id: str
    embedding: Sequence[float]
    metadata: dict[str, str | int | float | bool]


@dataclass(frozen=True, slots=True)
class VectorQueryHit:
    """Ranked vector similarity candidate returned from ChromaDB before PG ACL revalidation."""

    vector_id: str
    distance: float
    similarity: float
    metadata: dict[str, Any]


def build_chroma_collection_name(
    *,
    prefix: str,
    embedding_model: str,
    index_version: str,
) -> str:
    """Construct a valid Chroma v2 collection name bound to model & index version."""

    def _clean(raw: str) -> str:
        sub = re.sub(r"[^a-zA-Z0-9._-]+", "_", raw.strip())
        sub = re.sub(r"_+", "_", sub).strip("._-")
        return sub or "default"

    parts = [
        _clean(prefix),
        "evidence_chunks",
        _clean(embedding_model),
        _clean(index_version),
    ]
    joined = "_".join(parts)
    joined = re.sub(r"[^a-zA-Z0-9._-]+", "_", joined).strip("._-")
    if len(joined) < 3:
        joined = f"{joined}_idx"[:16]
    if len(joined) > 160:
        joined = joined[:160].rstrip("._-") or "ipkrh_chunks_v1"
    if not joined[0].isalnum():
        joined = f"c{joined[1:]}"
    if not joined[-1].isalnum():
        joined = f"{joined[:-1]}0"
    return joined


def build_deterministic_vector_id(*, evidence_id: uuid.UUID | str, chunk_index: int) -> str:
    """Return deterministic vector identifier enabling idempotent upsert and overwrite."""
    return f"{evidence_id}:{int(chunk_index)}"


def resolve_permission_scope_key(
    *,
    acl_scope: str,
    source_access_policy_id: uuid.UUID | str | None,
) -> str:
    """Derive non-secret ACL bucket label stored in Chroma metadata for pre-filtering."""
    if acl_scope == "source_restricted":
        if source_access_policy_id is not None:
            return f"policy:{source_access_policy_id}"
        return "legacy_restricted"
    if source_access_policy_id is not None:
        return f"public:{source_access_policy_id}"
    return "project_members"


def sanitize_vector_metadata(
    raw_metadata: Mapping[str, Any],
) -> dict[str, str | int | float | bool]:
    """Allowlist strict scalar operational metadata and drop None/unknown/secret fields."""
    sanitized: dict[str, str | int | float | bool] = {}
    for key in _ALLOWED_CHROMA_METADATA_KEYS:
        if key not in raw_metadata:
            continue
        value = raw_metadata[key]
        if value is None:
            continue
        if isinstance(value, bool):
            sanitized[key] = value
        elif isinstance(value, int):
            sanitized[key] = value
        elif isinstance(value, float):
            if math.isfinite(value):
                sanitized[key] = value
        elif isinstance(value, uuid.UUID):
            sanitized[key] = str(value)
        elif isinstance(value, str):
            trimmed = value.strip()
            if trimmed:
                sanitized[key] = trimmed[:255]
    return sanitized


class VectorStoreClient(Protocol):
    """Replaceable boundary between indexing/retrieval and the Chroma vector backend."""

    @property
    def collection_name(self) -> str:
        """Canonical collection name bound to active embedding model & version."""

    @property
    def embedding_model(self) -> str:
        """Active embedding model associated with vectors in this collection."""

    @property
    def index_version(self) -> str:
        """Index schema/pipeline version identifier."""

    @property
    def expected_dimensions(self) -> int:
        """Expected vector dimensionality."""

    def ensure_collection(self) -> VectorCollectionInfo:
        """Create or retrieve the configured collection and verify model/version match."""

    def inspect_collection(self) -> VectorCollectionInfo | None:
        """Inspect collection status without implicitly creating it if absent."""

    def upsert_records(self, records: Sequence[VectorUpsertRecord]) -> None:
        """Idempotently upsert deterministic vector records and allowed metadata."""

    def query_vectors(
        self,
        *,
        query_embedding: Sequence[float],
        top_k: int,
        where: dict[str, Any] | None = None,
    ) -> list[VectorQueryHit]:
        """Query nearest semantic matches ordered from highest similarity to lowest."""

    def delete_records(
        self,
        *,
        ids: Sequence[str] | None = None,
        where: dict[str, Any] | None = None,
    ) -> int:
        """Delete vector records by IDs and/or metadata filter idempotently."""

    def count_records(self) -> int:
        """Return total stored vector count in the active collection (0 when missing)."""

    def delete_collection(self) -> bool:
        """Delete the active collection when present (mainly for tests/rebuild)."""


class ChromaV2HttpVectorStore:
    """HTTPX adapter for ChromaDB Server v2 (`/api/v2`) running as a dedicated service."""

    def __init__(
        self,
        *,
        base_url: str,
        tenant: str = "default_tenant",
        database: str = "default_database",
        collection_prefix: str = "ipkrh",
        embedding_model: str = "nomic-embed-text",
        index_version: str = "v1",
        expected_dimensions: int = 768,
        auth_token: str | None = None,
        request_timeout_seconds: float = 15.0,
        collection_name_override: str | None = None,
        http_client: httpx.Client | None = None,
        http_transport: httpx.BaseTransport | None = None,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._tenant = tenant.strip() or "default_tenant"
        self._database = database.strip() or "default_database"
        self._embedding_model = embedding_model.strip()
        self._index_version = index_version.strip()
        self._expected_dimensions = max(1, int(expected_dimensions))
        self._auth_token = auth_token.strip() if auth_token and auth_token.strip() else None
        self._timeout = max(0.5, float(request_timeout_seconds))
        self._collection_name = (
            collection_name_override.strip()
            if collection_name_override and collection_name_override.strip()
            else build_chroma_collection_name(
                prefix=collection_prefix,
                embedding_model=self._embedding_model,
                index_version=self._index_version,
            )
        )
        self._http_client = http_client
        self._http_transport = http_transport
        self._cached_collection_id: str | None = None

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

    @property
    def _collections_base_path(self) -> str:
        return (
            f"{self._base_url}/api/v2/tenants/{self._tenant}"
            f"/databases/{self._database}/collections"
        )

    def _headers(self) -> dict[str, str]:
        if not self._auth_token:
            return {}
        return {
            "Authorization": f"Bearer {self._auth_token}",
            "X-Chroma-Token": self._auth_token,
        }

    def _request(
        self,
        method: str,
        url: str,
        *,
        json_body: dict[str, Any] | None = None,
    ) -> httpx.Response:
        try:
            if self._http_client is not None:
                return self._http_client.request(
                    method,
                    url,
                    json=json_body,
                    headers=self._headers(),
                    timeout=self._timeout,
                )
            with httpx.Client(
                timeout=self._timeout,
                transport=self._http_transport,
            ) as client:
                return client.request(
                    method,
                    url,
                    json=json_body,
                    headers=self._headers(),
                )
        except httpx.TimeoutException as exc:
            raise VectorStoreError(
                code="CHROMA_TIMEOUT",
                message="ChromaDB vector service request timed out.",
                retryable=True,
            ) from exc
        except httpx.HTTPError as exc:
            raise VectorStoreError(
                code="CHROMA_UNAVAILABLE",
                message="ChromaDB vector service is unreachable.",
                retryable=True,
            ) from exc

    def _parse_collection_info(self, payload: dict[str, Any]) -> VectorCollectionInfo:
        col_id = str(payload.get("id") or "").strip()
        col_name = str(payload.get("name") or self._collection_name)
        meta = dict(payload.get("metadata") or {})
        cfg = payload.get("configuration_json") or {}
        hnsw = cfg.get("hnsw") if isinstance(cfg, dict) else None
        space = str(hnsw.get("space")) if isinstance(hnsw, dict) and hnsw.get("space") else None
        raw_dim = payload.get("dimension")
        dimension = int(raw_dim) if isinstance(raw_dim, int) else None
        return VectorCollectionInfo(
            collection_id=col_id,
            name=col_name,
            space=space,
            dimension=dimension,
            metadata=meta,
        )

    def _validate_collection_compatibility(self, info: VectorCollectionInfo) -> None:
        meta = info.metadata
        recorded_model = str(meta.get("embedding_model") or "").strip()
        if recorded_model and recorded_model != self._embedding_model:
            raise VectorStoreError(
                code="VECTOR_COLLECTION_MODEL_MISMATCH",
                message=(
                    f"Chroma collection '{info.name}' is pinned to embedding model "
                    f"'{recorded_model}', incompatible with '{self._embedding_model}'."
                ),
                retryable=False,
            )
        recorded_version = str(meta.get("index_version") or "").strip()
        if recorded_version and recorded_version != self._index_version:
            raise VectorStoreError(
                code="VECTOR_COLLECTION_VERSION_MISMATCH",
                message=(
                    f"Chroma collection '{info.name}' has index_version '{recorded_version}', "
                    f"expected '{self._index_version}'."
                ),
                retryable=False,
            )
        meta_dims = meta.get("dimensions")
        effective_dim = info.dimension if info.dimension is not None else meta_dims
        if isinstance(effective_dim, int) and effective_dim != self._expected_dimensions:
            raise VectorStoreError(
                code="VECTOR_COLLECTION_DIMENSION_MISMATCH",
                message=(
                    f"Chroma collection '{info.name}' expects {effective_dim} dimensions, "
                    f"but active embedding model outputs {self._expected_dimensions}."
                ),
                retryable=False,
            )

    def _raise_for_unexpected_status(self, resp: httpx.Response, *, operation: str) -> None:
        if resp.status_code < 400:
            return
        retryable = resp.status_code >= 500 or resp.status_code == 429
        detail = ""
        try:
            err_json = resp.json()
            if isinstance(err_json, dict) and err_json.get("message"):
                detail = f": {str(err_json['message'])[:200]}"
        except ValueError:
            pass
        raise VectorStoreError(
            code="CHROMA_HTTP_ERROR",
            message=f"ChromaDB {operation} failed with HTTP {resp.status_code}{detail}",
            retryable=retryable,
        )

    def inspect_collection(self) -> VectorCollectionInfo | None:
        resp = self._request("GET", f"{self._collections_base_path}/{self._collection_name}")
        if resp.status_code == 404:
            self._cached_collection_id = None
            return None
        self._raise_for_unexpected_status(resp, operation="inspect_collection")
        try:
            payload = resp.json()
        except ValueError as exc:
            raise VectorStoreError(
                code="CHROMA_INVALID_RESPONSE",
                message="ChromaDB inspect_collection returned invalid JSON.",
                retryable=True,
            ) from exc
        if not isinstance(payload, dict) or not payload.get("id"):
            raise VectorStoreError(
                code="CHROMA_INVALID_RESPONSE",
                message="ChromaDB inspect_collection response omitted collection id.",
                retryable=True,
            )
        info = self._parse_collection_info(payload)
        self._validate_collection_compatibility(info)
        self._cached_collection_id = info.collection_id
        return info

    def ensure_collection(self) -> VectorCollectionInfo:
        if self._cached_collection_id:
            existing = self.inspect_collection()
            if existing is not None:
                return existing

        payload = {
            "name": self._collection_name,
            "get_or_create": True,
            "configuration": {"hnsw": {"space": "cosine"}},
            "metadata": {
                "embedding_model": self._embedding_model,
                "index_version": self._index_version,
                "dimensions": self._expected_dimensions,
                "purpose": "evidence_chunks",
            },
        }
        resp = self._request("POST", self._collections_base_path, json_body=payload)
        self._raise_for_unexpected_status(resp, operation="ensure_collection")
        try:
            data = resp.json()
        except ValueError as exc:
            raise VectorStoreError(
                code="CHROMA_INVALID_RESPONSE",
                message="ChromaDB ensure_collection returned invalid JSON.",
                retryable=True,
            ) from exc
        if not isinstance(data, dict) or not data.get("id"):
            raise VectorStoreError(
                code="CHROMA_INVALID_RESPONSE",
                message="ChromaDB ensure_collection response omitted collection id.",
                retryable=True,
            )
        info = self._parse_collection_info(data)
        self._validate_collection_compatibility(info)
        self._cached_collection_id = info.collection_id
        return info

    def _resolve_collection_id(self) -> str:
        if self._cached_collection_id:
            return self._cached_collection_id
        return self.ensure_collection().collection_id

    def upsert_records(self, records: Sequence[VectorUpsertRecord]) -> None:
        if not records:
            return
        ids: list[str] = []
        embeddings: list[list[float]] = []
        metadatas: list[dict[str, str | int | float | bool]] = []
        for rec in records:
            if len(rec.embedding) != self._expected_dimensions:
                raise VectorStoreError(
                    code="VECTOR_DIMENSION_MISMATCH",
                    message=(
                        f"Refusing to upsert vector '{rec.vector_id}' with {len(rec.embedding)} "
                        f"dimensions; expected {self._expected_dimensions}."
                    ),
                    retryable=False,
                )
            ids.append(rec.vector_id)
            embeddings.append([float(v) for v in rec.embedding])
            metadatas.append(sanitize_vector_metadata(rec.metadata))

        col_id = self._resolve_collection_id()
        url = f"{self._collections_base_path}/{col_id}/upsert"
        resp = self._request(
            "POST",
            url,
            json_body={
                "ids": ids,
                "embeddings": embeddings,
                "metadatas": metadatas,
            },
        )
        if resp.status_code == 404:
            self._cached_collection_id = None
            col_id = self.ensure_collection().collection_id
            url = f"{self._collections_base_path}/{col_id}/upsert"
            resp = self._request(
                "POST",
                url,
                json_body={
                    "ids": ids,
                    "embeddings": embeddings,
                    "metadatas": metadatas,
                },
            )
        self._raise_for_unexpected_status(resp, operation="upsert_records")

    def query_vectors(
        self,
        *,
        query_embedding: Sequence[float],
        top_k: int,
        where: dict[str, Any] | None = None,
    ) -> list[VectorQueryHit]:
        if top_k <= 0:
            return []
        if len(query_embedding) != self._expected_dimensions:
            raise VectorStoreError(
                code="QUERY_DIMENSION_MISMATCH",
                message=(
                    f"Query embedding dimensionality {len(query_embedding)} does not match "
                    f"collection expected dimensions {self._expected_dimensions}."
                ),
                retryable=False,
            )

        info = self.inspect_collection()
        if info is None:
            return []

        payload: dict[str, Any] = {
            "query_embeddings": [[float(v) for v in query_embedding]],
            "n_results": int(top_k),
            "include": ["metadatas", "distances"],
        }
        if where:
            payload["where"] = where

        url = f"{self._collections_base_path}/{info.collection_id}/query"
        resp = self._request("POST", url, json_body=payload)
        if resp.status_code == 404:
            self._cached_collection_id = None
            return []
        self._raise_for_unexpected_status(resp, operation="query_vectors")

        try:
            data = resp.json()
        except ValueError as exc:
            raise VectorStoreError(
                code="CHROMA_INVALID_RESPONSE",
                message="ChromaDB query_vectors returned invalid JSON.",
                retryable=True,
            ) from exc

        raw_ids = (data.get("ids") or [[]])[0] or []
        raw_distances = (data.get("distances") or [[]])[0] or []
        raw_metas = (data.get("metadatas") or [[]])[0] or []

        hits: list[VectorQueryHit] = []
        for idx, vec_id in enumerate(raw_ids):
            dist_val = (
                float(raw_distances[idx])
                if idx < len(raw_distances) and raw_distances[idx] is not None
                else 1.0
            )
            # Cosine distance returned by Chroma hnsw(space="cosine") is (1 - cosine_similarity)
            similarity = max(0.0, min(1.0, 1.0 - dist_val))
            meta = (
                dict(raw_metas[idx] or {})
                if idx < len(raw_metas) and isinstance(raw_metas[idx], dict)
                else {}
            )
            hits.append(
                VectorQueryHit(
                    vector_id=str(vec_id),
                    distance=dist_val,
                    similarity=similarity,
                    metadata=meta,
                )
            )
        return hits

    def delete_records(
        self,
        *,
        ids: Sequence[str] | None = None,
        where: dict[str, Any] | None = None,
    ) -> int:
        if not ids and not where:
            return 0
        info = self.inspect_collection()
        if info is None:
            return 0
        payload: dict[str, Any] = {}
        if ids:
            payload["ids"] = list(ids)
        if where:
            payload["where"] = where
        url = f"{self._collections_base_path}/{info.collection_id}/delete"
        resp = self._request("POST", url, json_body=payload)
        if resp.status_code == 404:
            self._cached_collection_id = None
            return 0
        self._raise_for_unexpected_status(resp, operation="delete_records")
        try:
            data = resp.json()
            if isinstance(data, dict) and isinstance(data.get("deleted"), int):
                return int(data["deleted"])
        except ValueError:
            pass
        return 0

    def count_records(self) -> int:
        info = self.inspect_collection()
        if info is None:
            return 0
        url = f"{self._collections_base_path}/{info.collection_id}/count"
        resp = self._request("GET", url)
        if resp.status_code == 404:
            self._cached_collection_id = None
            return 0
        self._raise_for_unexpected_status(resp, operation="count_records")
        try:
            raw = resp.json()
            if isinstance(raw, int):
                return raw
            if isinstance(raw, dict) and isinstance(raw.get("count"), int):
                return int(raw["count"])
        except ValueError as exc:
            raise VectorStoreError(
                code="CHROMA_INVALID_RESPONSE",
                message="ChromaDB count_records returned non-integer JSON.",
                retryable=True,
            ) from exc
        raise VectorStoreError(
            code="CHROMA_INVALID_RESPONSE",
            message="ChromaDB count_records returned unexpected payload.",
            retryable=True,
        )

    def delete_collection(self) -> bool:
        resp = self._request("DELETE", f"{self._collections_base_path}/{self._collection_name}")
        self._cached_collection_id = None
        if resp.status_code == 404:
            return False
        self._raise_for_unexpected_status(resp, operation="delete_collection")
        return True
