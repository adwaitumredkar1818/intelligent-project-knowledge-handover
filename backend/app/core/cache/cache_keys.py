"""Deterministic, collision-resistant, namespaced cache key factories.

Security Rules:
1. Never put raw access tokens, passwords, or plaintext secrets into keys.
2. Always isolate keys by project_id and/or user_id where permissions apply.
3. Hash dynamic queries and complex filters using SHA-256 digests.
"""

from __future__ import annotations

import hashlib
import json
import uuid
from typing import Any


def _hash_payload(data: Any) -> str:
    """Return a deterministic 16-character SHA-256 prefix for complex payloads."""
    serialized = json.dumps(data, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()[:16]


class CacheKeys:
    """Centralized key generator ensuring namespace consistency and isolation."""

    @staticmethod
    def dashboard_overview(project_id: uuid.UUID, user_id: uuid.UUID | None = None) -> str:
        if user_id:
            return f"dash:overview:proj:{project_id}:user:{user_id}"
        return f"dash:overview:proj:{project_id}"

    @staticmethod
    def project_metadata(project_id: uuid.UUID) -> str:
        return f"proj_meta:id:{project_id}"

    @staticmethod
    def project_list(organisation_id: uuid.UUID, user_id: uuid.UUID) -> str:
        return f"proj_list:org:{organisation_id}:user:{user_id}"

    @staticmethod
    def rbac_user_project_permissions(project_id: uuid.UUID, user_id: uuid.UUID) -> str:
        return f"rbac:perm:proj:{project_id}:user:{user_id}"

    @staticmethod
    def rbac_user_org_permissions(organisation_id: uuid.UUID, user_id: uuid.UUID) -> str:
        return f"rbac:perm:org:{organisation_id}:user:{user_id}"

    @staticmethod
    def search_query(
        project_id: uuid.UUID,
        user_id: uuid.UUID,
        query: str,
        limit: int,
        offset: int,
        filters: dict[str, Any] | None = None,
    ) -> str:
        query_sig = hashlib.sha256(query.strip().lower().encode("utf-8")).hexdigest()[:12]
        filter_sig = _hash_payload(filters or {})
        return f"search:proj:{project_id}:user:{user_id}:q:{query_sig}:lim:{limit}:off:{offset}:f:{filter_sig}"

    @staticmethod
    def ocr_page(
        content_hash: str,
        page_number: int,
        engine: str = "glm-ocr:latest",
        preprocess_version: str = "v1",
    ) -> str:
        return f"ocr:chash:{content_hash}:p:{page_number}:eng:{engine}:v:{preprocess_version}"

    @staticmethod
    def chunk_embedding(
        chunk_hash: str,
        model_name: str,
        expected_dimensions: int,
    ) -> str:
        return f"emb:chash:{chunk_hash}:m:{model_name}:d:{expected_dimensions}"

    @staticmethod
    def ai_response(
        project_id: uuid.UUID,
        user_id: uuid.UUID,
        query: str,
        context_fingerprint: str,
        model_name: str,
        prompt_version: str = "v1",
    ) -> str:
        q_hash = hashlib.sha256(query.strip().lower().encode("utf-8")).hexdigest()[:16]
        return f"ai_resp:proj:{project_id}:u:{user_id}:q:{q_hash}:ctx:{context_fingerprint}:m:{model_name}:pv:{prompt_version}"
