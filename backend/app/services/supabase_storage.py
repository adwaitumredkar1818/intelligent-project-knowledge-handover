"""Supabase Storage private backend with client-side AES-256-GCM envelope encryption."""

from __future__ import annotations

import logging
import os
import re
import uuid
from pathlib import Path
from typing import Any

import httpx
from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.hkdf import HKDF

from app.core.exceptions import ServiceUnavailableError
from app.models.enums import StorageProvider
from app.services.storage import (
    _ENCRYPTION_ALGORITHM,
    _ENVELOPE_MAGIC,
    _NONCE_SIZE,
    _STORAGE_KEY_PATTERN,
    StoredObjectMetadata,
    _build_aad,
    _derive_aes256_key,
)

logger = logging.getLogger("app.services.supabase_storage")

_SUPABASE_KEY_ID = "supabase-v1"


class SupabaseStorageBackend:
    """Private object storage backend using Supabase Storage with AES-256-GCM envelope encryption."""

    def __init__(
        self,
        *,
        base_url: str,
        bucket: str = "project-evidence",
        api_key: str,
        file_encryption_key: str,
        http_transport: httpx.BaseTransport | None = None,
        timeout_seconds: float = 30.0,
    ) -> None:
        self._bucket = bucket.strip()
        self._api_key = api_key.strip()
        self._raw_base_url = base_url.rstrip("/")
        self._storage_endpoint = f"{self._raw_base_url}/storage/v1"
        self._key = _derive_aes256_key(file_encryption_key)
        self._http_transport = http_transport
        self._timeout_seconds = timeout_seconds

    def _get_client(self) -> httpx.Client:
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "apikey": self._api_key,
        }
        return httpx.Client(
            base_url=self._storage_endpoint,
            headers=headers,
            transport=self._http_transport,
            timeout=self._timeout_seconds,
        )

    def store_encrypted_bytes(
        self,
        *,
        organisation_id: uuid.UUID,
        project_id: uuid.UUID,
        data: bytes,
    ) -> StoredObjectMetadata:
        """Encrypt payload with AES-256-GCM and upload directly to private Supabase Storage bucket."""
        object_id = uuid.uuid4()
        object_key = f"{organisation_id}/{project_id}/{object_id}.enc"
        if not _STORAGE_KEY_PATTERN.match(object_key):
            raise ValueError(f"Invalid generated storage key: {object_key}")

        nonce = os.urandom(_NONCE_SIZE)
        aad = _build_aad(
            organisation_id=organisation_id,
            project_id=project_id,
            object_key=object_key,
        )
        aesgcm = AESGCM(self._key)
        ciphertext = aesgcm.encrypt(nonce, data, aad)
        envelope = _ENVELOPE_MAGIC + nonce + ciphertext

        upload_path = f"/object/{self._bucket}/{object_key}"
        try:
            with self._get_client() as client:
                resp = client.post(
                    upload_path,
                    content=envelope,
                    headers={"Content-Type": "application/octet-stream"},
                )
                if resp.status_code not in (200, 201):
                    logger.error(
                        "Supabase storage upload failed: status %s, body: %s",
                        resp.status_code,
                        resp.text[:200],
                    )
                    raise ServiceUnavailableError(
                        "Failed to persist encrypted document to Supabase Storage.",
                        code="STORAGE_UPLOAD_FAILED",
                    )
        except httpx.HTTPError as exc:
            logger.error("Supabase storage connection error: %s", exc)
            raise ServiceUnavailableError(
                "Storage service is unreachable.",
                code="STORAGE_UNAVAILABLE",
            ) from exc

        return StoredObjectMetadata(
            storage_provider=StorageProvider.SUPABASE_STORAGE.value,
            storage_object_key=object_key,
            encryption_algorithm=_ENCRYPTION_ALGORITHM,
            encryption_key_id=_SUPABASE_KEY_ID,
            ciphertext_size_bytes=len(envelope),
        )

    def read_decrypted_bytes(
        self,
        *,
        storage_object_key: str,
        organisation_id: uuid.UUID,
        project_id: uuid.UUID,
        key_id: str | None = None,
    ) -> bytes:
        """Download ciphertext from Supabase Storage, authenticate tag, and decrypt."""
        if not _STORAGE_KEY_PATTERN.match(storage_object_key):
            raise ValueError(f"Invalid storage key: {storage_object_key}")

        download_path = f"/object/{self._bucket}/{storage_object_key}"
        try:
            with self._get_client() as client:
                resp = client.get(download_path)
                if resp.status_code == 404:
                    raise FileNotFoundError(f"Storage object not found: {storage_object_key}")
                if resp.status_code != 200:
                    logger.error(
                        "Supabase storage read failed: status %s, body: %s",
                        resp.status_code,
                        resp.text[:200],
                    )
                    raise ServiceUnavailableError(
                        "Failed to retrieve document from Supabase Storage.",
                        code="STORAGE_READ_FAILED",
                    )
                envelope = resp.content
        except httpx.HTTPError as exc:
            logger.error("Supabase storage read connection error: %s", exc)
            raise ServiceUnavailableError(
                "Storage service is unreachable.",
                code="STORAGE_UNAVAILABLE",
            ) from exc

        magic_len = len(_ENVELOPE_MAGIC)
        if len(envelope) < magic_len + _NONCE_SIZE + 16:
            raise ValueError("Corrupt or incomplete storage payload.")
        if envelope[:magic_len] != _ENVELOPE_MAGIC:
            raise ValueError("Unrecognised storage envelope magic header.")

        nonce = envelope[magic_len : magic_len + _NONCE_SIZE]
        ciphertext = envelope[magic_len + _NONCE_SIZE :]
        aad = _build_aad(
            organisation_id=organisation_id,
            project_id=project_id,
            object_key=storage_object_key,
        )
        aesgcm = AESGCM(self._key)
        try:
            return aesgcm.decrypt(nonce, ciphertext, aad)
        except InvalidTag as exc:
            raise ValueError(
                "Integrity verification failed; ciphertext or tenant context was altered."
            ) from exc

    def delete_object(self, *, storage_object_key: str) -> bool:
        """Remove a stored encrypted object from Supabase Storage."""
        if not _STORAGE_KEY_PATTERN.match(storage_object_key):
            return False

        delete_path = f"/object/{self._bucket}/{storage_object_key}"
        try:
            with self._get_client() as client:
                resp = client.delete(delete_path)
                return resp.status_code in (200, 204)
        except httpx.HTTPError as exc:
            logger.warning("Supabase storage delete error: %s", exc)
            return False

    def exists(self, *, storage_object_key: str) -> bool:
        """Check whether object exists in Supabase Storage."""
        if not _STORAGE_KEY_PATTERN.match(storage_object_key):
            return False

        check_path = f"/object/info/{self._bucket}/{storage_object_key}"
        try:
            with self._get_client() as client:
                resp = client.get(check_path)
                return resp.status_code == 200
        except httpx.HTTPError:
            return False

    def create_signed_download_url(
        self,
        *,
        storage_object_key: str,
        expires_in_seconds: int = 60,
    ) -> str:
        """Create a strictly short-lived (max 60s) signed download URL."""
        if not _STORAGE_KEY_PATTERN.match(storage_object_key):
            raise ValueError(f"Invalid storage key: {storage_object_key}")

        sign_path = f"/object/sign/{self._bucket}/{storage_object_key}"
        try:
            with self._get_client() as client:
                resp = client.post(
                    sign_path,
                    json={"expiresIn": min(max(expires_in_seconds, 10), 60)},
                )
                if resp.status_code == 200:
                    data = resp.json()
                    signed_url_path = data.get("signedURL") or data.get("signedUrl")
                    if signed_url_path:
                        if signed_url_path.startswith("http"):
                            return signed_url_path
                        return f"{self._raw_base_url}/storage/v1{signed_url_path}"
                raise ServiceUnavailableError(
                    "Failed to create signed URL from Supabase Storage.",
                    code="STORAGE_SIGN_FAILED",
                )
        except httpx.HTTPError as exc:
            raise ServiceUnavailableError(
                "Storage service is unreachable.",
                code="STORAGE_UNAVAILABLE",
            ) from exc
