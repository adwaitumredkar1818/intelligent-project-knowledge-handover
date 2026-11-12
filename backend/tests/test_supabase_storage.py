"""Unit tests for Supabase Storage backend with AES-256-GCM envelope encryption."""

from __future__ import annotations

import json
import uuid

import httpx
import pytest

from app.models.enums import StorageProvider
from app.services.storage import _ENVELOPE_MAGIC
from app.services.supabase_storage import SupabaseStorageBackend

_FILE_KEY = "test-storage-file-key-at-least-32-chars-long!"
_API_KEY = "test-supabase-api-key"
_BASE_URL = "https://mock.supabase.co"


def test_supabase_storage_store_and_read_decrypted() -> None:
    uploaded_objects: dict[str, bytes] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        path = request.url.path
        if request.method == "POST" and path.startswith("/storage/v1/object/project-evidence/"):
            key = path[len("/storage/v1/object/project-evidence/") :]
            uploaded_objects[key] = request.content
            return httpx.Response(200, json={"Key": key})
        if request.method == "GET" and path.startswith("/storage/v1/object/project-evidence/"):
            key = path[len("/storage/v1/object/project-evidence/") :]
            if key in uploaded_objects:
                return httpx.Response(200, content=uploaded_objects[key])
            return httpx.Response(404, json={"error": "Not found"})
        if request.method == "DELETE" and path.startswith("/storage/v1/object/project-evidence/"):
            key = path[len("/storage/v1/object/project-evidence/") :]
            uploaded_objects.pop(key, None)
            return httpx.Response(200, json={"message": "Deleted"})
        return httpx.Response(404)

    transport = httpx.MockTransport(handler)
    backend = SupabaseStorageBackend(
        base_url=_BASE_URL,
        bucket="project-evidence",
        api_key=_API_KEY,
        file_encryption_key=_FILE_KEY,
        http_transport=transport,
    )

    org_id = uuid.uuid4()
    proj_id = uuid.uuid4()
    original_data = b"Handover architecture decision record content with secrets: DB_PASS=xyz"

    # Store
    meta = backend.store_encrypted_bytes(
        organisation_id=org_id,
        project_id=proj_id,
        data=original_data,
    )
    assert meta.storage_provider == StorageProvider.SUPABASE_STORAGE.value
    assert meta.storage_object_key.startswith(f"{org_id}/{proj_id}/")
    assert meta.ciphertext_size_bytes > len(original_data)

    # Verify uploaded bytes on server are encrypted with envelope magic
    stored_bytes = uploaded_objects[meta.storage_object_key]
    assert stored_bytes.startswith(_ENVELOPE_MAGIC)
    assert b"secrets" not in stored_bytes
    assert b"DB_PASS" not in stored_bytes

    # Read and decrypt
    decrypted = backend.read_decrypted_bytes(
        storage_object_key=meta.storage_object_key,
        organisation_id=org_id,
        project_id=proj_id,
    )
    assert decrypted == original_data


def test_supabase_storage_integrity_tampering_fails() -> None:
    uploaded_objects: dict[str, bytes] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        path = request.url.path
        if request.method == "POST":
            key = path[len("/storage/v1/object/project-evidence/") :]
            uploaded_objects[key] = request.content
            return httpx.Response(200, json={"Key": key})
        if request.method == "GET":
            key = path[len("/storage/v1/object/project-evidence/") :]
            return httpx.Response(200, content=uploaded_objects[key])
        return httpx.Response(404)

    transport = httpx.MockTransport(handler)
    backend = SupabaseStorageBackend(
        base_url=_BASE_URL,
        bucket="project-evidence",
        api_key=_API_KEY,
        file_encryption_key=_FILE_KEY,
        http_transport=transport,
    )

    org_id = uuid.uuid4()
    proj_id = uuid.uuid4()
    meta = backend.store_encrypted_bytes(
        organisation_id=org_id,
        project_id=proj_id,
        data=b"Confidential handover specification",
    )

    # Tamper with stored bytes
    raw = uploaded_objects[meta.storage_object_key]
    tampered = raw[:-2] + b"\x00\x00"
    uploaded_objects[meta.storage_object_key] = tampered

    # Decryption should fail integrity check
    with pytest.raises(ValueError, match="Integrity verification failed"):
        backend.read_decrypted_bytes(
            storage_object_key=meta.storage_object_key,
            organisation_id=org_id,
            project_id=proj_id,
        )


def test_supabase_storage_signed_url_generation() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.method == "POST" and "/sign/" in request.url.path:
            body = json.loads(request.content.decode("utf-8"))
            assert body["expiresIn"] <= 60
            return httpx.Response(
                200,
                json={"signedURL": "/storage/v1/object/sign/project-evidence/file.enc?token=abc123token"},
            )
        return httpx.Response(404)

    transport = httpx.MockTransport(handler)
    backend = SupabaseStorageBackend(
        base_url=_BASE_URL,
        bucket="project-evidence",
        api_key=_API_KEY,
        file_encryption_key=_FILE_KEY,
        http_transport=transport,
    )

    org_id = uuid.uuid4()
    proj_id = uuid.uuid4()
    doc_id = uuid.uuid4()
    valid_key = f"{org_id}/{proj_id}/{doc_id}.enc"

    signed_url = backend.create_signed_download_url(
        storage_object_key=valid_key,
        expires_in_seconds=60,
    )
    assert "signedURL" in signed_url or "token=" in signed_url
    assert signed_url.startswith("https://mock.supabase.co")
