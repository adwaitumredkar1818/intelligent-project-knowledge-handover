"""Private encrypted binary storage abstraction for uploaded project documents."""

from __future__ import annotations

import logging
import os
import re
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.hkdf import HKDF

from app.core.exceptions import ServiceUnavailableError
from app.models.enums import StorageProvider

logger = logging.getLogger("app.services.storage")

_STORAGE_KEY_PATTERN = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}/"
    r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}/"
    r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\.enc$"
)
_ENVELOPE_MAGIC = b"IPKRH1\x01"
_NONCE_SIZE = 12
_LOCAL_KEY_ID = "local-v1"
_ENCRYPTION_ALGORITHM = "AES-256-GCM"


@dataclass(frozen=True, slots=True)
class StoredObjectMetadata:
    """Internal descriptor returned after persisting encrypted object bytes."""

    storage_provider: str
    storage_object_key: str
    encryption_algorithm: str
    encryption_key_id: str
    ciphertext_size_bytes: int


class StorageBackend(Protocol):
    """Replaceable private object storage interface keeping host paths off APIs."""

    def store_encrypted_bytes(
        self,
        *,
        organisation_id: uuid.UUID,
        project_id: uuid.UUID,
        data: bytes,
    ) -> StoredObjectMetadata:
        """Encrypt and persist payload under an opaque key bound to tenant/project."""

    def read_decrypted_bytes(
        self,
        *,
        storage_object_key: str,
        organisation_id: uuid.UUID,
        project_id: uuid.UUID,
        key_id: str | None = None,
    ) -> bytes:
        """Read and authenticate encrypted bytes directly in memory."""

    def delete_object(self, *, storage_object_key: str) -> bool:
        """Remove a stored encrypted artefact if it exists."""

    def exists(self, *, storage_object_key: str) -> bool:
        """Return whether an opaque object key currently exists in storage."""


def _derive_aes256_key(raw_secret: str) -> bytes:
    """Derive a domain-separated 256-bit AES-GCM key from `FILE_ENCRYPTION_KEY`."""
    secret_bytes = raw_secret.encode("utf-8")
    if len(secret_bytes) < 16:
        raise ValueError("FILE_ENCRYPTION_KEY must be at least 16 bytes.")
    hkdf = HKDF(
        algorithm=hashes.SHA256(),
        length=32,
        salt=b"ipkrh-private-storage-salt-v1",
        info=b"ipkrh-aes-256-gcm-v1",
    )
    return hkdf.derive(secret_bytes)


def _build_aad(*, organisation_id: uuid.UUID, project_id: uuid.UUID, object_key: str) -> bytes:
    return f"{organisation_id}:{project_id}:{object_key}".encode()


class LocalPrivateStorageBackend:
    """Local filesystem storage encrypting payloads at rest with AES-256-GCM.

    Note: In local development, the master secret comes from `FILE_ENCRYPTION_KEY`
    in environment configuration rather than a hardware KMS / managed envelope service.
    """

    def __init__(self, *, root_path: Path, file_encryption_key: str) -> None:
        self._root_path = root_path.expanduser().resolve()
        self._root_path.mkdir(parents=True, exist_ok=True)
        self._aes_key = _derive_aes256_key(file_encryption_key)

    @property
    def root_path(self) -> Path:
        """Return resolved private storage root (for internal diagnostics/tests only)."""
        return self._root_path

    def _resolve_safe_key(self, storage_object_key: str) -> Path:
        normalized = storage_object_key.strip().replace("\\", "/")
        if not _STORAGE_KEY_PATTERN.fullmatch(normalized):
            raise ValueError("Malformed opaque storage object key.")
        candidate = (self._root_path / normalized).resolve()
        if not candidate.is_relative_to(self._root_path):
            raise ValueError("Storage key escaped configured private storage boundary.")
        return candidate

    def store_encrypted_bytes(
        self,
        *,
        organisation_id: uuid.UUID,
        project_id: uuid.UUID,
        data: bytes,
    ) -> StoredObjectMetadata:
        object_id = uuid.uuid4()
        object_key = f"{organisation_id}/{project_id}/{object_id}.enc"
        try:
            target_path = self._resolve_safe_key(object_key)
            target_path.parent.mkdir(parents=True, exist_ok=True)
            nonce = os.urandom(_NONCE_SIZE)
            aad = _build_aad(
                organisation_id=organisation_id,
                project_id=project_id,
                object_key=object_key,
            )
            ciphertext = AESGCM(self._aes_key).encrypt(nonce, data, aad)
            envelope = _ENVELOPE_MAGIC + nonce + ciphertext

            tmp_path = target_path.with_name(f".tmp-{uuid.uuid4().hex}")
            try:
                with tmp_path.open("wb") as handle:
                    handle.write(envelope)
                    handle.flush()
                    os.fsync(handle.fileno())
                os.replace(tmp_path, target_path)
            finally:
                if tmp_path.exists():
                    tmp_path.unlink(missing_ok=True)
        except Exception as exc:
            logger.exception("Failed to write encrypted object to private storage.")
            raise ServiceUnavailableError(
                "Document could not be persisted to private storage.",
                code="STORAGE_WRITE_FAILED",
            ) from exc

        return StoredObjectMetadata(
            storage_provider=StorageProvider.LOCAL_ENCRYPTED.value,
            storage_object_key=object_key,
            encryption_algorithm=_ENCRYPTION_ALGORITHM,
            encryption_key_id=_LOCAL_KEY_ID,
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
        if key_id is not None and key_id != _LOCAL_KEY_ID:
            raise ServiceUnavailableError(
                "Stored artefact references an unsupported encryption key version.",
                code="STORAGE_KEY_UNSUPPORTED",
            )
        try:
            target_path = self._resolve_safe_key(storage_object_key)
        except ValueError as exc:
            logger.warning("Rejected unsafe storage object key lookup.")
            raise ServiceUnavailableError(
                "Stored artefact location is invalid.",
                code="STORAGE_KEY_INVALID",
            ) from exc

        if not target_path.is_file():
            raise ServiceUnavailableError(
                "Stored artefact payload is missing from private storage.",
                code="STORAGE_OBJECT_MISSING",
            )

        try:
            raw = target_path.read_bytes()
            if not raw.startswith(_ENVELOPE_MAGIC):
                raise ValueError("Invalid encrypted storage envelope header.")
            offset = len(_ENVELOPE_MAGIC)
            nonce = raw[offset : offset + _NONCE_SIZE]
            ciphertext = raw[offset + _NONCE_SIZE :]
            if len(nonce) != _NONCE_SIZE or len(ciphertext) < 16:
                raise ValueError("Truncated encrypted storage envelope.")
            aad = _build_aad(
                organisation_id=organisation_id,
                project_id=project_id,
                object_key=storage_object_key.strip().replace("\\", "/"),
            )
            return AESGCM(self._aes_key).decrypt(nonce, ciphertext, aad)
        except InvalidTag as exc:
            logger.error("AEAD integrity check failed while reading encrypted object.")
            raise ServiceUnavailableError(
                "Stored artefact failed integrity verification.",
                code="STORAGE_INTEGRITY_FAILED",
            ) from exc
        except Exception as exc:
            logger.exception("Failed to read/decrypt stored artefact.")
            raise ServiceUnavailableError(
                "Stored artefact could not be read from private storage.",
                code="STORAGE_READ_FAILED",
            ) from exc

    def delete_object(self, *, storage_object_key: str) -> bool:
        try:
            target_path = self._resolve_safe_key(storage_object_key)
        except ValueError:
            logger.warning("Ignored deletion for invalid storage object key.")
            return False
        if not target_path.exists():
            return False
        target_path.unlink()
        return True

    def exists(self, *, storage_object_key: str) -> bool:
        try:
            target_path = self._resolve_safe_key(storage_object_key)
        except ValueError:
            return False
        return target_path.is_file()
