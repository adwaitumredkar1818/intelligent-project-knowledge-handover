"""Private encrypted binary storage abstraction and canonical AES-256-GCM envelope helpers."""

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
ENVELOPE_MAGIC = b"IPKRH1\x01"
_ENVELOPE_MAGIC = ENVELOPE_MAGIC
NONCE_SIZE_BYTES = 12
_NONCE_SIZE = NONCE_SIZE_BYTES
GCM_TAG_SIZE_BYTES = 16
ENVELOPE_OVERHEAD_BYTES = len(ENVELOPE_MAGIC) + NONCE_SIZE_BYTES + GCM_TAG_SIZE_BYTES  # 35 bytes
LOCAL_KEY_ID = "local-v1"
_LOCAL_KEY_ID = LOCAL_KEY_ID
SUPABASE_KEY_ID = "supabase-v1"
ENCRYPTION_ALGORITHM = "AES-256-GCM"
_ENCRYPTION_ALGORITHM = ENCRYPTION_ALGORITHM


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
        expected_plaintext_size: int | None = None,
    ) -> bytes:
        """Read and authenticate encrypted bytes directly in memory."""

    def delete_object(self, *, storage_object_key: str) -> bool:
        """Remove a stored encrypted artefact if it exists."""

    def exists(self, *, storage_object_key: str) -> bool:
        """Return whether an opaque object key currently exists in storage."""


def derive_aes256_storage_key(raw_secret: str) -> bytes:
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


_derive_aes256_key = derive_aes256_storage_key


def build_storage_aad(
    *,
    organisation_id: uuid.UUID,
    project_id: uuid.UUID,
    object_key: str,
) -> bytes:
    """Build AEAD associated data binding ciphertext to tenant, project, and opaque key."""
    return f"{organisation_id}:{project_id}:{object_key}".encode()


def validate_storage_object_key(storage_object_key: str) -> str:
    """Validate strict opaque `<org_uuid>/<project_uuid>/<object_uuid>.enc` key shape."""
    raw = storage_object_key.strip()
    if "\\" in raw:
        raise ValueError("Malformed opaque storage object key.")
    if not _STORAGE_KEY_PATTERN.fullmatch(raw):
        raise ValueError("Malformed opaque storage object key.")
    return raw


def generate_storage_object_key(
    *,
    organisation_id: uuid.UUID,
    project_id: uuid.UUID,
    object_id: uuid.UUID | None = None,
) -> str:
    """Create and validate an opaque storage key bound to org and project UUIDs."""
    candidate = f"{organisation_id}/{project_id}/{object_id or uuid.uuid4()}.enc"
    return validate_storage_object_key(candidate)


def expected_envelope_size_bytes(plaintext_size_bytes: int) -> int:
    """Return exact AEAD envelope byte length for a plaintext payload of known size."""
    if plaintext_size_bytes < 0:
        raise ValueError("plaintext_size_bytes must be non-negative.")
    return plaintext_size_bytes + ENVELOPE_OVERHEAD_BYTES


def encrypt_storage_envelope(
    *,
    aes_key: bytes,
    organisation_id: uuid.UUID,
    project_id: uuid.UUID,
    object_key: str,
    plaintext: bytes,
) -> bytes:
    """Encrypt plaintext bytes using canonical AES-256-GCM envelope with tenant/key AAD."""
    normalized_key = validate_storage_object_key(object_key)
    nonce = os.urandom(NONCE_SIZE_BYTES)
    aad = build_storage_aad(
        organisation_id=organisation_id,
        project_id=project_id,
        object_key=normalized_key,
    )
    ciphertext = AESGCM(aes_key).encrypt(nonce, plaintext, aad)
    return ENVELOPE_MAGIC + nonce + ciphertext


def decrypt_storage_envelope(
    *,
    aes_key: bytes,
    envelope: bytes,
    organisation_id: uuid.UUID,
    project_id: uuid.UUID,
    object_key: str,
    key_id: str | None = None,
    expected_key_id: str | None = None,
    expected_plaintext_size: int | None = None,
) -> bytes:
    """Verify key version, envelope header, ciphertext length, and AEAD tag before decrypting."""
    if expected_key_id is not None and key_id is not None and key_id != expected_key_id:
        raise ServiceUnavailableError(
            "Stored artefact references an unsupported encryption key version.",
            code="STORAGE_KEY_UNSUPPORTED",
        )
    try:
        normalized_key = validate_storage_object_key(object_key)
    except ValueError as exc:
        logger.warning("Rejected unsafe storage object key lookup.")
        raise ServiceUnavailableError(
            "Stored artefact location is invalid.",
            code="STORAGE_KEY_INVALID",
        ) from exc

    if len(envelope) < ENVELOPE_OVERHEAD_BYTES or not envelope.startswith(ENVELOPE_MAGIC):
        raise ServiceUnavailableError(
            "Stored artefact failed envelope integrity verification.",
            code="STORAGE_INTEGRITY_FAILED",
        )

    if expected_plaintext_size is not None:
        expected_len = expected_envelope_size_bytes(expected_plaintext_size)
        if len(envelope) != expected_len:
            raise ServiceUnavailableError(
                "Stored artefact ciphertext size did not match expected integrity envelope.",
                code="STORAGE_INTEGRITY_FAILED",
            )

    offset = len(ENVELOPE_MAGIC)
    nonce = envelope[offset : offset + NONCE_SIZE_BYTES]
    ciphertext = envelope[offset + NONCE_SIZE_BYTES :]
    if len(nonce) != NONCE_SIZE_BYTES or len(ciphertext) < GCM_TAG_SIZE_BYTES:
        raise ServiceUnavailableError(
            "Stored artefact envelope is truncated.",
            code="STORAGE_INTEGRITY_FAILED",
        )

    aad = build_storage_aad(
        organisation_id=organisation_id,
        project_id=project_id,
        object_key=normalized_key,
    )
    try:
        plaintext = AESGCM(aes_key).decrypt(nonce, ciphertext, aad)
    except InvalidTag as exc:
        logger.error("AEAD integrity check failed while reading encrypted object.")
        raise ServiceUnavailableError(
            "Stored artefact failed integrity verification.",
            code="STORAGE_INTEGRITY_FAILED",
        ) from exc

    if expected_plaintext_size is not None and len(plaintext) != expected_plaintext_size:
        raise ServiceUnavailableError(
            "Decrypted artefact size did not match expected evidence size.",
            code="STORAGE_INTEGRITY_FAILED",
        )
    return plaintext


class LocalPrivateStorageBackend:
    """Local filesystem storage encrypting payloads at rest with AES-256-GCM.

    Note: In local development, the master secret comes from `FILE_ENCRYPTION_KEY`
    in environment configuration rather than a hardware KMS / managed envelope service.
    """

    def __init__(self, *, root_path: Path, file_encryption_key: str) -> None:
        self._root_path = root_path.expanduser().resolve()
        self._root_path.mkdir(parents=True, exist_ok=True)
        self._aes_key = derive_aes256_storage_key(file_encryption_key)

    @property
    def root_path(self) -> Path:
        """Return resolved private storage root (for internal diagnostics/tests only)."""
        return self._root_path

    def _resolve_safe_key(self, storage_object_key: str) -> Path:
        normalized = validate_storage_object_key(storage_object_key)
        candidate = (self._root_path / normalized).resolve()
        if not candidate.is_relative_to(self._root_path):
            raise ValueError("Storage key escaped configured private storage boundary.")
        return candidate

    def _locate_existing_file(self, storage_object_key: str) -> Path | None:
        """Locate stored artefact, checking configured root and fallback repo upload locations."""
        try:
            target_path = self._resolve_safe_key(storage_object_key)
            if target_path.is_file():
                return target_path
        except ValueError:
            return None

        normalized = validate_storage_object_key(storage_object_key)
        candidates: list[Path] = []
        parts = self._root_path.parts
        if "backend" in parts:
            idx = parts.index("backend")
            repo_root = Path(*parts[:idx])
            candidates.append(repo_root / "data" / "uploads" / normalized)
        else:
            candidates.append(self._root_path.parent / "backend" / "data" / "uploads" / normalized)
            candidates.append(self._root_path / "backend" / "data" / "uploads" / normalized)

        for candidate in candidates:
            try:
                resolved = candidate.resolve()
                if resolved.is_file():
                    return resolved
            except (OSError, ValueError):
                continue
        return None

    def store_encrypted_bytes(
        self,
        *,
        organisation_id: uuid.UUID,
        project_id: uuid.UUID,
        data: bytes,
    ) -> StoredObjectMetadata:
        object_key = generate_storage_object_key(
            organisation_id=organisation_id,
            project_id=project_id,
        )
        try:
            target_path = self._resolve_safe_key(object_key)
            target_path.parent.mkdir(parents=True, exist_ok=True)
            envelope = encrypt_storage_envelope(
                aes_key=self._aes_key,
                organisation_id=organisation_id,
                project_id=project_id,
                object_key=object_key,
                plaintext=data,
            )

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
            encryption_algorithm=ENCRYPTION_ALGORITHM,
            encryption_key_id=LOCAL_KEY_ID,
            ciphertext_size_bytes=len(envelope),
        )

    def read_decrypted_bytes(
        self,
        *,
        storage_object_key: str,
        organisation_id: uuid.UUID,
        project_id: uuid.UUID,
        key_id: str | None = None,
        expected_plaintext_size: int | None = None,
    ) -> bytes:
        if key_id is not None and key_id != LOCAL_KEY_ID:
            raise ServiceUnavailableError(
                "Stored artefact references an unsupported encryption key version.",
                code="STORAGE_KEY_UNSUPPORTED",
            )
        try:
            validate_storage_object_key(storage_object_key)
        except ValueError as exc:
            logger.warning("Rejected unsafe storage object key lookup.")
            raise ServiceUnavailableError(
                "Stored artefact location is invalid.",
                code="STORAGE_KEY_INVALID",
            ) from exc

        located = self._locate_existing_file(storage_object_key)
        if not located:
            raise ServiceUnavailableError(
                "Stored artefact payload is missing from private storage.",
                code="STORAGE_OBJECT_MISSING",
            )

        try:
            raw = located.read_bytes()
        except OSError as exc:
            logger.exception("Failed to read stored artefact from local disk.")
            raise ServiceUnavailableError(
                "Stored artefact could not be read from private storage.",
                code="STORAGE_READ_FAILED",
            ) from exc

        return decrypt_storage_envelope(
            aes_key=self._aes_key,
            envelope=raw,
            organisation_id=organisation_id,
            project_id=project_id,
            object_key=storage_object_key,
            key_id=key_id,
            expected_key_id=LOCAL_KEY_ID,
            expected_plaintext_size=expected_plaintext_size,
        )

    def delete_object(self, *, storage_object_key: str) -> bool:
        located = self._locate_existing_file(storage_object_key)
        if not located or not located.exists():
            return False
        located.unlink()
        return True

    def exists(self, *, storage_object_key: str) -> bool:
        return self._locate_existing_file(storage_object_key) is not None
