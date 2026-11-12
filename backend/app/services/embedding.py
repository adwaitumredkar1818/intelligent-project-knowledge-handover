"""Replaceable embedding service abstraction and Ollama `nomic-embed-text` adapter."""

from __future__ import annotations

import logging
import math
import time
from collections.abc import Sequence
from typing import Any, Protocol

import httpx

from app.services.ocr import _OLLAMA_INFERENCE_LOCK

logger = logging.getLogger("app.services.embedding")


class EmbeddingExecutionError(RuntimeError):
    """Typed, sanitised failure raised when embedding generation fails."""

    def __init__(self, *, code: str, message: str, retryable: bool = True) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.retryable = retryable


class EmbeddingService(Protocol):
    """Replaceable boundary separating indexing/retrieval from the active embedding backend."""

    @property
    def model_name(self) -> str:
        """Identifier of the active embedding model used for indexing and querying."""

    @property
    def expected_dimensions(self) -> int:
        """Expected fixed dimensionality produced by the active embedding model."""

    def embed_documents(self, texts: Sequence[str]) -> list[list[float]]:
        """Generate validated dense embedding vectors for one or more document chunks."""

    def embed_query(self, text: str) -> list[float]:
        """Generate a validated dense embedding vector for a search query."""


class OllamaEmbeddingService:
    """Native Ollama `/api/embed` adapter pinned to consistent dimensionality & batch bounds."""

    def __init__(
        self,
        *,
        base_url: str,
        model: str = "nomic-embed-text",
        batch_size: int = 8,
        expected_dimensions: int = 768,
        timeout_seconds: float = 60.0,
        http_client: httpx.Client | None = None,
        http_transport: httpx.BaseTransport | None = None,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._model = model.strip()
        self._batch_size = max(1, int(batch_size))
        self._expected_dimensions = max(1, int(expected_dimensions))
        self._timeout_seconds = max(1.0, float(timeout_seconds))
        self._http_client = http_client
        self._http_transport = http_transport

    @property
    def model_name(self) -> str:
        return self._model

    @property
    def expected_dimensions(self) -> int:
        return self._expected_dimensions

    def embed_query(self, text: str) -> list[float]:
        cleaned = text.strip()
        if not cleaned:
            raise EmbeddingExecutionError(
                code="EMPTY_EMBEDDING_INPUT",
                message="Search query text cannot be empty for semantic embedding.",
                retryable=False,
            )
        vectors = self.embed_documents([cleaned])
        return vectors[0]

    def embed_documents(self, texts: Sequence[str]) -> list[list[float]]:
        if not texts:
            return []

        cleaned_inputs: list[str] = []
        for idx, raw in enumerate(texts):
            item = raw.strip()
            if not item:
                raise EmbeddingExecutionError(
                    code="EMPTY_EMBEDDING_INPUT",
                    message=f"Embedding input at position {idx} is blank.",
                    retryable=False,
                )
            cleaned_inputs.append(item)

        all_vectors: list[list[float]] = []
        for start in range(0, len(cleaned_inputs), self._batch_size):
            batch = cleaned_inputs[start : start + self._batch_size]
            batch_vectors = self._embed_batch(batch)
            all_vectors.extend(batch_vectors)
        return all_vectors

    def _post_embed(self, payload: dict[str, Any]) -> httpx.Response:
        if self._http_client is not None:
            return self._http_client.post(
                f"{self._base_url}/api/embed",
                json=payload,
                timeout=self._timeout_seconds,
            )
        with httpx.Client(
            timeout=self._timeout_seconds,
            transport=self._http_transport,
        ) as client:
            return client.post(
                f"{self._base_url}/api/embed",
                json=payload,
            )

    def _embed_batch(self, batch: list[str]) -> list[list[float]]:
        payload = {
            "model": self._model,
            "input": batch,
            "truncate": True,
        }
        started = time.perf_counter()
        with _OLLAMA_INFERENCE_LOCK:
            try:
                resp = self._post_embed(payload)
            except httpx.TimeoutException as exc:
                raise EmbeddingExecutionError(
                    code="EMBEDDING_TIMEOUT",
                    message="Embedding service timed out while generating vectors.",
                    retryable=True,
                ) from exc
            except httpx.HTTPError as exc:
                raise EmbeddingExecutionError(
                    code="EMBEDDING_UNAVAILABLE",
                    message="Local Ollama embedding service is unavailable.",
                    retryable=True,
                ) from exc

        elapsed_ms = int((time.perf_counter() - started) * 1000)

        if resp.status_code >= 500:
            raise EmbeddingExecutionError(
                code="EMBEDDING_UPSTREAM_ERROR",
                message=f"Embedding service returned HTTP {resp.status_code}.",
                retryable=True,
            )
        if resp.status_code >= 400:
            raise EmbeddingExecutionError(
                code="EMBEDDING_REQUEST_REJECTED",
                message=f"Embedding service rejected batch request ({resp.status_code}).",
                retryable=False,
            )

        try:
            raw_json = resp.json()
        except ValueError as exc:
            raise EmbeddingExecutionError(
                code="EMBEDDING_INVALID_RESPONSE",
                message="Embedding service returned non-JSON output.",
                retryable=True,
            ) from exc

        if not isinstance(raw_json, dict):
            raise EmbeddingExecutionError(
                code="EMBEDDING_INVALID_RESPONSE",
                message="Embedding service returned an unexpected JSON payload shape.",
                retryable=True,
            )

        if raw_json.get("error"):
            raise EmbeddingExecutionError(
                code="EMBEDDING_MODEL_ERROR",
                message=f"Embedding model reported an error: {str(raw_json['error'])[:200]}",
                retryable=False,
            )

        raw_embeddings = raw_json.get("embeddings")
        if not isinstance(raw_embeddings, list) or len(raw_embeddings) != len(batch):
            raise EmbeddingExecutionError(
                code="EMBEDDING_COUNT_MISMATCH",
                message="Embedding response count did not match input batch size.",
                retryable=True,
            )

        validated: list[list[float]] = []
        for idx, raw_vec in enumerate(raw_embeddings):
            if not isinstance(raw_vec, list):
                raise EmbeddingExecutionError(
                    code="EMBEDDING_VECTOR_INVALID",
                    message=f"Embedding vector at index {idx} is not a numeric list.",
                    retryable=False,
                )
            if len(raw_vec) != self._expected_dimensions:
                raise EmbeddingExecutionError(
                    code="EMBEDDING_DIMENSION_MISMATCH",
                    message=(
                        f"Expected {self._expected_dimensions} embedding dimensions for "
                        f"'{self._model}', received {len(raw_vec)}."
                    ),
                    retryable=False,
                )
            floats: list[float] = []
            sq_sum = 0.0
            for val in raw_vec:
                if isinstance(val, bool) or not isinstance(val, (int, float)):
                    raise EmbeddingExecutionError(
                        code="EMBEDDING_VECTOR_INVALID",
                        message="Embedding vector contained a non-numeric value.",
                        retryable=False,
                    )
                fval = float(val)
                if not math.isfinite(fval):
                    raise EmbeddingExecutionError(
                        code="EMBEDDING_VECTOR_INVALID",
                        message="Embedding vector contained NaN or Inf value.",
                        retryable=False,
                    )
                floats.append(fval)
                sq_sum += fval * fval
            if sq_sum <= 0.0:
                raise EmbeddingExecutionError(
                    code="EMBEDDING_VECTOR_ZERO",
                    message="Embedding service returned an all-zero vector.",
                    retryable=False,
                )
            validated.append(floats)

        logger.debug(
            "Generated embeddings batch via Ollama.",
            extra={
                "embedding_model": self._model,
                "batch_size": len(batch),
                "dimensions": self._expected_dimensions,
                "duration_ms": elapsed_ms,
            },
        )
        return validated
