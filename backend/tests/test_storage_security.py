"""Unit tests verifying AES-256-GCM at-rest encryption, AAD binding, and path traversal guards."""

from __future__ import annotations

import uuid
from pathlib import Path

import pytest

from app.core.exceptions import ServiceUnavailableError
from app.services.storage import LocalPrivateStorageBackend

_SECRET_A = "local-test-file-encryption-secret-32chars!!"
_SECRET_B = "different-secret-key-for-verification-32ch!"


def test_local_storage_encrypts_at_rest_and_roundtrips_in_memory(tmp_path: Path) -> None:
    storage = LocalPrivateStorageBackend(root_path=tmp_path, file_encryption_key=_SECRET_A)
    org_id = uuid.uuid4()
    proj_id = uuid.uuid4()
    plaintext = b"%PDF-1.7\nConfidential architectural handover blueprint bytes\n"

    stored = storage.store_encrypted_bytes(
        organisation_id=org_id,
        project_id=proj_id,
        data=plaintext,
    )

    assert stored.storage_provider == "local_encrypted"
    assert stored.encryption_algorithm == "AES-256-GCM"
    assert stored.encryption_key_id == "local-v1"
    assert stored.storage_object_key.startswith(f"{org_id}/{proj_id}/")
    assert stored.storage_object_key.endswith(".enc")

    disk_path = tmp_path.resolve() / stored.storage_object_key
    assert disk_path.is_file()
    raw_disk_bytes = disk_path.read_bytes()
    assert b"%PDF-1.7" not in raw_disk_bytes
    assert b"Confidential architectural handover" not in raw_disk_bytes

    decrypted = storage.read_decrypted_bytes(
        storage_object_key=stored.storage_object_key,
        organisation_id=org_id,
        project_id=proj_id,
        key_id=stored.encryption_key_id,
    )
    assert decrypted == plaintext


def test_local_storage_rejects_aad_mismatch_tampering_and_wrong_key(tmp_path: Path) -> None:
    storage = LocalPrivateStorageBackend(root_path=tmp_path, file_encryption_key=_SECRET_A)
    org_id = uuid.uuid4()
    proj_id = uuid.uuid4()
    stored = storage.store_encrypted_bytes(
        organisation_id=org_id,
        project_id=proj_id,
        data=b"Sensitive project runbook",
    )

    # Binding ciphertext to a different project/org fails AEAD tag check
    with pytest.raises(ServiceUnavailableError) as wrong_proj_exc:
        storage.read_decrypted_bytes(
            storage_object_key=stored.storage_object_key,
            organisation_id=org_id,
            project_id=uuid.uuid4(),
        )
    assert wrong_proj_exc.value.code == "STORAGE_INTEGRITY_FAILED"

    # Wrong decryption key fails authentication cleanly
    other_storage = LocalPrivateStorageBackend(root_path=tmp_path, file_encryption_key=_SECRET_B)
    with pytest.raises(ServiceUnavailableError) as wrong_key_exc:
        other_storage.read_decrypted_bytes(
            storage_object_key=stored.storage_object_key,
            organisation_id=org_id,
            project_id=proj_id,
        )
    assert wrong_key_exc.value.code == "STORAGE_INTEGRITY_FAILED"

    # Corrupting a byte on disk fails authentication tag
    disk_path = tmp_path.resolve() / stored.storage_object_key
    corrupted = bytearray(disk_path.read_bytes())
    corrupted[-1] ^= 0xFF
    disk_path.write_bytes(bytes(corrupted))
    with pytest.raises(ServiceUnavailableError) as corrupt_exc:
        storage.read_decrypted_bytes(
            storage_object_key=stored.storage_object_key,
            organisation_id=org_id,
            project_id=proj_id,
        )
    assert corrupt_exc.value.code == "STORAGE_INTEGRITY_FAILED"


def test_local_storage_blocks_path_traversal_and_deletes_safely(tmp_path: Path) -> None:
    storage = LocalPrivateStorageBackend(root_path=tmp_path, file_encryption_key=_SECRET_A)
    org_id = uuid.uuid4()
    proj_id = uuid.uuid4()

    for bad_key in (
        "../outside.enc",
        f"{org_id}/{proj_id}/../../outside.enc",
        "/etc/passwd",
        "..\\windows\\system.ini",
        "not-a-uuid/file.pdf",
    ):
        assert storage.exists(storage_object_key=bad_key) is False
        assert storage.delete_object(storage_object_key=bad_key) is False
        with pytest.raises(ServiceUnavailableError) as exc_info:
            storage.read_decrypted_bytes(
                storage_object_key=bad_key,
                organisation_id=org_id,
                project_id=proj_id,
            )
        assert exc_info.value.code == "STORAGE_KEY_INVALID"

    stored = storage.store_encrypted_bytes(
        organisation_id=org_id,
        project_id=proj_id,
        data=b"to-be-deleted",
    )
    assert storage.exists(storage_object_key=stored.storage_object_key) is True
    assert storage.delete_object(storage_object_key=stored.storage_object_key) is True
    assert storage.exists(storage_object_key=stored.storage_object_key) is False
    assert storage.delete_object(storage_object_key=stored.storage_object_key) is False
