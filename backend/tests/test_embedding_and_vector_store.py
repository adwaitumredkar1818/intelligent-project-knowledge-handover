"""Unit tests for OllamaEmbeddingService and ChromaV2HttpVectorStore adapters."""

from __future__ import annotations

import json
import uuid

import httpx
import pytest

from app.services.embedding import EmbeddingExecutionError, OllamaEmbeddingService
from app.services.vector_store import (
    ChromaV2HttpVectorStore,
    VectorStoreError,
    VectorUpsertRecord,
    build_chroma_collection_name,
    build_deterministic_vector_id,
    resolve_permission_scope_key,
    sanitize_vector_metadata,
)


def _unit_vec(dims: int = 8, hot_idx: int = 0) -> list[float]:
    vec = [0.1] * dims
    vec[hot_idx % dims] = 1.0
    return vec


def test_ollama_embedding_service_batching_and_validation() -> None:
    calls: list[list[str]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/api/embed"
        body = json.loads(request.content.decode("utf-8"))
        assert body["model"] == "nomic-embed-text"
        batch = list(body["input"])
        calls.append(batch)
        return httpx.Response(
            200,
            json={"embeddings": [_unit_vec(8, idx) for idx, _ in enumerate(batch)]},
        )

    service = OllamaEmbeddingService(
        base_url="http://127.0.0.1:11434",
        model="nomic-embed-text",
        batch_size=3,
        expected_dimensions=8,
        http_transport=httpx.MockTransport(handler),
    )

    assert service.embed_documents([]) == []
    vectors = service.embed_documents([f"chunk {i}" for i in range(7)])
    assert len(vectors) == 7
    assert [len(b) for b in calls] == [3, 3, 1]
    assert all(len(v) == 8 for v in vectors)

    q_vec = service.embed_query("  PostgreSQL failover architecture ")
    assert len(q_vec) == 8


def test_ollama_embedding_service_rejects_bad_vectors_and_classifies_http_errors() -> None:
    with pytest.raises(EmbeddingExecutionError) as exc_empty:
        OllamaEmbeddingService(
            base_url="http://127.0.0.1:11434",
            expected_dimensions=8,
        ).embed_query("   ")
    assert exc_empty.value.code == "EMPTY_EMBEDDING_INPUT"
    assert exc_empty.value.retryable is False

    # Dimension mismatch -> non-retryable
    dim_svc = OllamaEmbeddingService(
        base_url="http://127.0.0.1:11434",
        expected_dimensions=8,
        http_transport=httpx.MockTransport(
            lambda _r: httpx.Response(200, json={"embeddings": [[0.1, 0.2, 0.3]]})
        ),
    )
    with pytest.raises(EmbeddingExecutionError) as exc_dim:
        dim_svc.embed_documents(["hello"])
    assert exc_dim.value.code == "EMBEDDING_DIMENSION_MISMATCH"
    assert exc_dim.value.retryable is False

    # Zero vector -> non-retryable
    zero_svc = OllamaEmbeddingService(
        base_url="http://127.0.0.1:11434",
        expected_dimensions=8,
        http_transport=httpx.MockTransport(
            lambda _r: httpx.Response(200, json={"embeddings": [[0.0] * 8]})
        ),
    )
    with pytest.raises(EmbeddingExecutionError) as exc_zero:
        zero_svc.embed_documents(["hello"])
    assert exc_zero.value.code == "EMBEDDING_VECTOR_ZERO"
    assert exc_zero.value.retryable is False

    # NaN / non-JSON / HTTP 503 -> retryable
    err_503 = OllamaEmbeddingService(
        base_url="http://127.0.0.1:11434",
        expected_dimensions=8,
        http_transport=httpx.MockTransport(lambda _r: httpx.Response(503, text="busy")),
    )
    with pytest.raises(EmbeddingExecutionError) as exc_503:
        err_503.embed_query("hello")
    assert exc_503.value.code == "EMBEDDING_UPSTREAM_ERROR"
    assert exc_503.value.retryable is True

    # HTTP 400 -> non-retryable
    err_400 = OllamaEmbeddingService(
        base_url="http://127.0.0.1:11434",
        expected_dimensions=8,
        http_transport=httpx.MockTransport(lambda _r: httpx.Response(400, text="bad model")),
    )
    with pytest.raises(EmbeddingExecutionError) as exc_400:
        err_400.embed_query("hello")
    assert exc_400.value.code == "EMBEDDING_REQUEST_REJECTED"
    assert exc_400.value.retryable is False


def test_vector_metadata_sanitisation_and_naming() -> None:
    col = build_chroma_collection_name(
        prefix="___ipkrh---",
        embedding_model="nomic-embed-text:latest",
        index_version="v1",
    )
    assert col[0].isalnum()
    assert col[-1].isalnum()
    assert "nomic-embed-text" in col

    policy_id = uuid.uuid4()
    assert (
        resolve_permission_scope_key(
            acl_scope="project_members",
            source_access_policy_id=None,
        )
        == "project_members"
    )
    assert (
        resolve_permission_scope_key(
            acl_scope="project_members",
            source_access_policy_id=policy_id,
        )
        == f"public:{policy_id}"
    )
    assert (
        resolve_permission_scope_key(
            acl_scope="source_restricted",
            source_access_policy_id=policy_id,
        )
        == f"policy:{policy_id}"
    )
    assert (
        resolve_permission_scope_key(acl_scope="source_restricted", source_access_policy_id=None)
        == "legacy_restricted"
    )

    ev_id = uuid.uuid4()
    assert build_deterministic_vector_id(evidence_id=ev_id, chunk_index=3) == f"{ev_id}:3"

    sanitized = sanitize_vector_metadata(
        {
            "organisation_id": uuid.uuid4(),
            "project_id": uuid.uuid4(),
            "evidence_id": ev_id,
            "chunk_id": uuid.uuid4(),
            "chunk_index": 0,
            "chunk_type": "issue_body",
            "source_type": "github",
            "category": "issue_discussion",
            "acl_scope": "source_restricted",
            "permission_scope_key": f"policy:{policy_id}",
            "is_synthetic": False,
            # Forbidden secret / raw content keys must be dropped cleanly
            "chunk_text": "SECRET PROSE SHOULD NOT BE STORED",
            "storage_object_key": "uploads/secret.bin",
            "access_token": "gho_secret_token",
            "source_author_identity": "secret.email@example.com",
        }
    )
    assert "chunk_text" not in sanitized
    assert "storage_object_key" not in sanitized
    assert "access_token" not in sanitized
    assert "source_author_identity" not in sanitized
    assert sanitized["chunk_type"] == "issue_body"
    assert sanitized["is_synthetic"] is False


def test_chroma_v2_vector_store_lifecycle_model_guard_and_similarity() -> None:
    col_uuid = str(uuid.uuid4())
    captured_upserts: list[dict[str, object]] = []
    state = {"deleted": False}

    def handler(request: httpx.Request) -> httpx.Response:
        path = request.url.path
        col_base = "/api/v2/tenants/default_tenant/databases/default_database/collections"
        if path == col_base and request.method == "POST":
            return httpx.Response(
                200,
                json={
                    "id": col_uuid,
                    "name": "ipkrh_test_evidence_chunks_nomic-embed-text_v1",
                    "dimension": 8,
                    "configuration_json": {"hnsw": {"space": "cosine"}},
                    "metadata": {
                        "embedding_model": "nomic-embed-text",
                        "index_version": "v1",
                        "dimensions": 8,
                    },
                },
            )
        if (
            path == f"{col_base}/ipkrh_test_evidence_chunks_nomic-embed-text_v1"
            and request.method == "GET"
        ):
            if state["deleted"]:
                return httpx.Response(404, json={"message": "not found"})
            return httpx.Response(
                200,
                json={
                    "id": col_uuid,
                    "name": "ipkrh_test_evidence_chunks_nomic-embed-text_v1",
                    "dimension": 8,
                    "configuration_json": {"hnsw": {"space": "cosine"}},
                    "metadata": {
                        "embedding_model": "nomic-embed-text",
                        "index_version": "v1",
                        "dimensions": 8,
                    },
                },
            )
        if path == f"{col_base}/{col_uuid}/upsert":
            body = json.loads(request.content.decode("utf-8"))
            assert "documents" not in body
            captured_upserts.append(body)
            return httpx.Response(201, json={})
        if path == f"{col_base}/{col_uuid}/query":
            return httpx.Response(
                200,
                json={
                    "ids": [["v1", "v2"]],
                    "distances": [[0.18, 0.72]],
                    "metadatas": [[{"chunk_id": "c1"}, {"chunk_id": "c2"}]],
                },
            )
        if path == f"{col_base}/{col_uuid}/count":
            return httpx.Response(200, json=2)
        if path == f"{col_base}/{col_uuid}/delete":
            return httpx.Response(200, json={"deleted": 1})
        if (
            path == f"{col_base}/ipkrh_test_evidence_chunks_nomic-embed-text_v1"
            and request.method == "DELETE"
        ):
            state["deleted"] = True
            return httpx.Response(200, json={})
        raise AssertionError(f"Unexpected request: {request.method} {path}")

    store = ChromaV2HttpVectorStore(
        base_url="http://127.0.0.1:8001",
        collection_prefix="ipkrh_test",
        embedding_model="nomic-embed-text",
        index_version="v1",
        expected_dimensions=8,
        http_transport=httpx.MockTransport(handler),
    )

    info = store.ensure_collection()
    assert info.collection_id == col_uuid
    assert info.space == "cosine"

    ev_id = uuid.uuid4()
    store.upsert_records(
        [
            VectorUpsertRecord(
                vector_id=f"{ev_id}:0",
                embedding=_unit_vec(8, 1),
                metadata={
                    "project_id": str(uuid.uuid4()),
                    "evidence_id": str(ev_id),
                    "chunk_id": "c1",
                    "storage_object_key": "must_be_stripped",
                },
            )
        ]
    )
    assert len(captured_upserts) == 1
    assert "storage_object_key" not in captured_upserts[0]["metadatas"][0]  # type: ignore[index]

    assert store.count_records() == 2
    hits = store.query_vectors(query_embedding=_unit_vec(8, 1), top_k=5)
    assert len(hits) == 2
    assert hits[0].similarity == pytest.approx(0.82)
    assert hits[1].similarity == pytest.approx(0.28)
    assert store.delete_records(ids=[f"{ev_id}:0"]) == 1
    assert store.delete_collection() is True
    assert store.inspect_collection() is None

    # Incompatible embedding model / version raises explicit guard error
    wrong_model_store = ChromaV2HttpVectorStore(
        base_url="http://127.0.0.1:8001",
        collection_prefix="ipkrh_test",
        embedding_model="different-embed-model",
        index_version="v1",
        expected_dimensions=8,
        collection_name_override="ipkrh_test_evidence_chunks_nomic-embed-text_v1",
        http_transport=httpx.MockTransport(
            lambda _r: httpx.Response(
                200,
                json={
                    "id": col_uuid,
                    "name": "ipkrh_test_evidence_chunks_nomic-embed-text_v1",
                    "dimension": 8,
                    "metadata": {
                        "embedding_model": "nomic-embed-text",
                        "index_version": "v1",
                        "dimensions": 8,
                    },
                },
            )
        ),
    )
    with pytest.raises(VectorStoreError) as exc_mod:
        wrong_model_store.inspect_collection()
    assert exc_mod.value.code == "VECTOR_COLLECTION_MODEL_MISMATCH"
