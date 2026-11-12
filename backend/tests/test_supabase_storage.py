"""Unit tests for hardened Supabase Storage backend and canonical AES-256-GCM envelope."""

from __future__ import annotations

import uuid
from collections.abc import Callable

import httpx
import pytest

from app.core.exceptions import ServiceUnavailableError
from app.models.enums import StorageProvider
from app.services.storage import (
    ENVELOPE_MAGIC,
    ENVELOPE_OVERHEAD_BYTES,
    SUPABASE_KEY_ID,
    StoredObjectMetadata,
    expected_envelope_size_bytes,
)
from app.services.supabase_storage import SupabaseStorageBackend

_FILE_KEY = "test-storage-file-key-at-least-32-chars-long!"
_SERVICE_ROLE_KEY = "test-supabase-service-role-key-secret"
_BASE_URL = "https://mock.supabase.co"


def test_supabase_storage_store_read_exists_delete_roundtrip() -> None:
    uploaded_objects: dict[str, bytes] = {}
    captured_headers: list[dict[str, str]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        path = request.url.path
        captured_headers.append(dict(request.headers))
        if request.method == "POST" and path.startswith("/storage/v1/object/project-evidence/"):
            assert request.headers.get("x-upsert") == "false"
            assert request.headers.get("authorization") == f"Bearer {_SERVICE_ROLE_KEY}"
            assert request.headers.get("apikey") == _SERVICE_ROLE_KEY
            key = path[len("/storage/v1/object/project-evidence/") :]
            uploaded_objects[key] = request.content
            return httpx.Response(200, json={"Key": f"project-evidence/{key}"})
        if request.method == "GET" and path.startswith("/storage/v1/object/info/project-evidence/"):
            key = path[len("/storage/v1/object/info/project-evidence/") :]
            if key in uploaded_objects:
                return httpx.Response(200, json={"name": key, "size": len(uploaded_objects[key])})
            return httpx.Response(404, json={"statusCode": "404", "error": "not_found"})
        if request.method == "GET" and path.startswith("/storage/v1/object/project-evidence/"):
            key = path[len("/storage/v1/object/project-evidence/") :]
            if key in uploaded_objects:
                body = uploaded_objects[key]
                return httpx.Response(
                    200,
                    content=body,
                    headers={"Content-Length": str(len(body))},
                )
            return httpx.Response(404, json={"error": "Not found"})
        if request.method == "DELETE" and path.startswith("/storage/v1/object/project-evidence/"):
            key = path[len("/storage/v1/object/project-evidence/") :]
            existed = uploaded_objects.pop(key, None) is not None
            if existed:
                return httpx.Response(200, json={"message": "Deleted"})
            return httpx.Response(404, json={"statusCode": "404", "error": "not_found"})
        return httpx.Response(404)

    backend = SupabaseStorageBackend(
        base_url=_BASE_URL,
        bucket="project-evidence",
        service_role_key=_SERVICE_ROLE_KEY,
        file_encryption_key=_FILE_KEY,
        retry_backoff_seconds=0.0,
        http_transport=httpx.MockTransport(handler),
    )
    assert not hasattr(backend, "create_signed_download_url")
    assert _SERVICE_ROLE_KEY not in repr(backend)

    org_id = uuid.uuid4()
    proj_id = uuid.uuid4()
    original_data = b"Handover architecture decision record content with secrets: DB_PASS=xyz"

    meta = backend.store_encrypted_bytes(
        organisation_id=org_id,
        project_id=proj_id,
        data=original_data,
    )
    assert meta.storage_provider == StorageProvider.SUPABASE_STORAGE.value
    assert meta.storage_object_key.startswith(f"{org_id}/{proj_id}/")
    assert meta.storage_object_key.endswith(".enc")
    assert meta.encryption_key_id == SUPABASE_KEY_ID
    assert meta.ciphertext_size_bytes == expected_envelope_size_bytes(len(original_data))
    assert meta.ciphertext_size_bytes == len(original_data) + ENVELOPE_OVERHEAD_BYTES

    stored_bytes = uploaded_objects[meta.storage_object_key]
    assert stored_bytes.startswith(ENVELOPE_MAGIC)
    assert b"secrets" not in stored_bytes
    assert b"DB_PASS" not in stored_bytes

    assert backend.exists(storage_object_key=meta.storage_object_key) is True

    decrypted = backend.read_decrypted_bytes(
        storage_object_key=meta.storage_object_key,
        organisation_id=org_id,
        project_id=proj_id,
        key_id=SUPABASE_KEY_ID,
        expected_plaintext_size=len(original_data),
    )
    assert decrypted == original_data

    assert backend.delete_object(storage_object_key=meta.storage_object_key) is True
    assert backend.exists(storage_object_key=meta.storage_object_key) is False
    assert backend.delete_object(storage_object_key=meta.storage_object_key) is False


def test_supabase_storage_integrity_size_key_id_and_traversal_guards() -> None:
    uploaded_objects: dict[str, bytes] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        path = request.url.path
        if request.method == "POST":
            key = path[len("/storage/v1/object/project-evidence/") :]
            uploaded_objects[key] = request.content
            return httpx.Response(200, json={"Key": f"project-evidence/{key}"})
        if request.method == "GET" and "/object/info/" in path:
            return httpx.Response(404, json={"error": "not_found"})
        if request.method == "GET":
            key = path[len("/storage/v1/object/project-evidence/") :]
            if key not in uploaded_objects:
                return httpx.Response(400, json={"statusCode": "404", "error": "not_found"})
            return httpx.Response(200, content=uploaded_objects[key])
        return httpx.Response(404)

    backend = SupabaseStorageBackend(
        base_url=_BASE_URL,
        bucket="project-evidence",
        service_role_key=_SERVICE_ROLE_KEY,
        file_encryption_key=_FILE_KEY,
        retry_backoff_seconds=0.0,
        http_transport=httpx.MockTransport(handler),
    )

    org_id = uuid.uuid4()
    proj_id = uuid.uuid4()
    plaintext = b"Confidential handover specification"
    meta = backend.store_encrypted_bytes(
        organisation_id=org_id,
        project_id=proj_id,
        data=plaintext,
    )

    # Unsupported key_id rejected cleanly
    with pytest.raises(ServiceUnavailableError) as key_id_exc:
        backend.read_decrypted_bytes(
            storage_object_key=meta.storage_object_key,
            organisation_id=org_id,
            project_id=proj_id,
            key_id="local-v1",
        )
    assert key_id_exc.value.code == "STORAGE_KEY_UNSUPPORTED"

    # Wrong tenant AAD rejected
    with pytest.raises(ServiceUnavailableError) as aad_exc:
        backend.read_decrypted_bytes(
            storage_object_key=meta.storage_object_key,
            organisation_id=org_id,
            project_id=uuid.uuid4(),
            key_id=SUPABASE_KEY_ID,
        )
    assert aad_exc.value.code == "STORAGE_INTEGRITY_FAILED"

    # Expected size mismatch rejected before/after decryption
    with pytest.raises(ServiceUnavailableError) as size_exc:
        backend.read_decrypted_bytes(
            storage_object_key=meta.storage_object_key,
            organisation_id=org_id,
            project_id=proj_id,
            key_id=SUPABASE_KEY_ID,
            expected_plaintext_size=len(plaintext) + 5,
        )
    assert size_exc.value.code == "STORAGE_INTEGRITY_FAILED"

    # Path traversal keys rejected safely without issuing HTTP requests
    for bad_key in ("../escape.enc", f"{org_id}\\{proj_id}\\bad.enc", "bad/key"):
        assert backend.exists(storage_object_key=bad_key) is False
        assert backend.delete_object(storage_object_key=bad_key) is False
        with pytest.raises(ServiceUnavailableError) as key_exc:
            backend.read_decrypted_bytes(
                storage_object_key=bad_key,
                organisation_id=org_id,
                project_id=proj_id,
            )
        assert key_exc.value.code == "STORAGE_KEY_INVALID"

    # Ciphertext tampering fails AEAD verification
    raw = uploaded_objects[meta.storage_object_key]
    uploaded_objects[meta.storage_object_key] = raw[:-2] + b"\x00\x00"
    with pytest.raises(ServiceUnavailableError) as tamper_exc:
        backend.read_decrypted_bytes(
            storage_object_key=meta.storage_object_key,
            organisation_id=org_id,
            project_id=proj_id,
            key_id=SUPABASE_KEY_ID,
            expected_plaintext_size=len(plaintext),
        )
    assert tamper_exc.value.code == "STORAGE_INTEGRITY_FAILED"

    # Missing object (even via Supabase 400 statusCode="404" JSON) maps to STORAGE_OBJECT_MISSING
    missing_key = f"{org_id}/{proj_id}/{uuid.uuid4()}.enc"
    with pytest.raises(ServiceUnavailableError) as missing_exc:
        backend.read_decrypted_bytes(
            storage_object_key=missing_key,
            organisation_id=org_id,
            project_id=proj_id,
        )
    assert missing_exc.value.code == "STORAGE_OBJECT_MISSING"


def test_supabase_storage_retries_timeouts_and_fails_closed_on_auth_errors() -> None:
    attempts = 0
    uploaded_objects: dict[str, bytes] = {}

    def flaky_handler(request: httpx.Request) -> httpx.Response:
        nonlocal attempts
        attempts += 1
        path = request.url.path
        if request.method == "POST":
            if attempts == 1:
                raise httpx.ReadTimeout("Transient write timeout", request=request)
            if attempts == 2:
                return httpx.Response(503, json={"error": "Service overloaded"})
            key = path[len("/storage/v1/object/project-evidence/") :]
            uploaded_objects[key] = request.content
            return httpx.Response(201, json={"Key": f"project-evidence/{key}"})
        if request.method == "GET":
            key = path[len("/storage/v1/object/project-evidence/") :]
            if key in uploaded_objects:
                return httpx.Response(200, content=uploaded_objects[key])
            return httpx.Response(404)
        return httpx.Response(404)

    backend = SupabaseStorageBackend(
        base_url=_BASE_URL,
        bucket="project-evidence",
        service_role_key=_SERVICE_ROLE_KEY,
        file_encryption_key=_FILE_KEY,
        max_retries=2,
        retry_backoff_seconds=0.0,
        http_transport=httpx.MockTransport(flaky_handler),
    )

    org_id = uuid.uuid4()
    proj_id = uuid.uuid4()
    meta = backend.store_encrypted_bytes(
        organisation_id=org_id,
        project_id=proj_id,
        data=b"Retry recovery payload",
    )
    assert attempts == 3
    assert (
        backend.read_decrypted_bytes(
            storage_object_key=meta.storage_object_key,
            organisation_id=org_id,
            project_id=proj_id,
        )
        == b"Retry recovery payload"
    )

    # Persistent timeout raises STORAGE_TIMEOUT after bounded retries
    timeout_calls = 0

    def always_timeout(request: httpx.Request) -> httpx.Response:
        nonlocal timeout_calls
        timeout_calls += 1
        raise httpx.ConnectTimeout("Timed out", request=request)

    timeout_backend = SupabaseStorageBackend(
        base_url=_BASE_URL,
        bucket="project-evidence",
        service_role_key=_SERVICE_ROLE_KEY,
        file_encryption_key=_FILE_KEY,
        max_retries=1,
        retry_backoff_seconds=0.0,
        http_transport=httpx.MockTransport(always_timeout),
    )
    with pytest.raises(ServiceUnavailableError) as timeout_exc:
        timeout_backend.store_encrypted_bytes(
            organisation_id=org_id,
            project_id=proj_id,
            data=b"Payload",
        )
    assert timeout_exc.value.code == "STORAGE_TIMEOUT"
    assert timeout_calls == 2

    # 403 Forbidden fails immediately without retrying and fails closed on exists()
    auth_calls = 0

    def forbidden_handler(_request: httpx.Request) -> httpx.Response:
        nonlocal auth_calls
        auth_calls += 1
        return httpx.Response(403, json={"error": "Forbidden"})

    forbidden_backend = SupabaseStorageBackend(
        base_url=_BASE_URL,
        bucket="project-evidence",
        service_role_key=_SERVICE_ROLE_KEY,
        file_encryption_key=_FILE_KEY,
        max_retries=3,
        retry_backoff_seconds=0.0,
        http_transport=httpx.MockTransport(forbidden_handler),
    )
    with pytest.raises(ServiceUnavailableError) as auth_exc:
        forbidden_backend.exists(storage_object_key=meta.storage_object_key)
    assert auth_exc.value.code == "STORAGE_UNAVAILABLE"
    assert auth_calls == 1


@pytest.mark.parametrize(
    "bad_header",
    [
        "abc",
        "",
        "   ",
        "-1",
        "-42",
        "42.0",
        "12.5",
        "+42",
        "4_2",
        "50, 50",
    ],
)
def test_supabase_storage_rejects_malformed_content_length_headers(bad_header: str) -> None:
    uploaded_objects: dict[str, bytes] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        path = request.url.path
        key = path.split("/project-evidence/", 1)[1]
        if request.method == "POST":
            uploaded_objects[key] = request.content
            return httpx.Response(200, json={"Key": f"project-evidence/{key}"})
        if request.method == "GET":
            return httpx.Response(
                200,
                content=uploaded_objects[key],
                headers={"Content-Length": bad_header},
            )
        return httpx.Response(404)

    backend = SupabaseStorageBackend(
        base_url=_BASE_URL,
        bucket="project-evidence",
        service_role_key=_SERVICE_ROLE_KEY,
        file_encryption_key=_FILE_KEY,
        retry_backoff_seconds=0.0,
        http_transport=httpx.MockTransport(handler),
    )
    org_id = uuid.uuid4()
    proj_id = uuid.uuid4()
    plaintext = b"Strict header verification payload."
    meta = backend.store_encrypted_bytes(organisation_id=org_id, project_id=proj_id, data=plaintext)

    with pytest.raises(ServiceUnavailableError) as exc_info:
        backend.read_decrypted_bytes(
            storage_object_key=meta.storage_object_key,
            organisation_id=org_id,
            project_id=proj_id,
            key_id=SUPABASE_KEY_ID,
            expected_plaintext_size=len(plaintext),
        )
    assert exc_info.value.code == "STORAGE_INTEGRITY_FAILED"


def test_supabase_storage_content_length_zero_missing_and_mismatched_sizes() -> None:
    uploaded_objects: dict[str, bytes] = {}
    download_mode = "valid_positive"

    def handler(request: httpx.Request) -> httpx.Response:
        path = request.url.path
        key = path.split("/project-evidence/", 1)[1]
        if request.method == "POST":
            uploaded_objects[key] = request.content
            return httpx.Response(200, json={"Key": f"project-evidence/{key}"})
        if request.method == "GET":
            envelope = uploaded_objects[key]
            if download_mode == "valid_positive":
                return httpx.Response(
                    200,
                    content=envelope,
                    headers={"Content-Length": str(len(envelope))},
                )
            if download_mode == "missing_header":
                resp = httpx.Response(200, stream=httpx.ByteStream(envelope))
                assert "content-length" not in resp.headers
                return resp
            if download_mode == "zero_header_empty_body":
                return httpx.Response(
                    200,
                    content=b"",
                    headers={"Content-Length": "0"},
                )
            if download_mode == "zero_header_non_empty_body":
                return httpx.Response(
                    200,
                    content=envelope,
                    headers={"Content-Length": "0"},
                )
            if download_mode == "smaller_than_actual":
                return httpx.Response(
                    200,
                    content=envelope,
                    headers={"Content-Length": str(len(envelope) - 1)},
                )
            if download_mode == "larger_than_actual":
                return httpx.Response(
                    200,
                    content=envelope,
                    headers={"Content-Length": str(len(envelope) + 1)},
                )
            if download_mode == "truncated_ciphertext_matching_header":
                truncated = envelope[:-4]
                return httpx.Response(
                    200,
                    content=truncated,
                    headers={"Content-Length": str(len(truncated))},
                )
        return httpx.Response(404)

    backend = SupabaseStorageBackend(
        base_url=_BASE_URL,
        bucket="project-evidence",
        service_role_key=_SERVICE_ROLE_KEY,
        file_encryption_key=_FILE_KEY,
        retry_backoff_seconds=0.0,
        http_transport=httpx.MockTransport(handler),
    )
    org_id = uuid.uuid4()
    proj_id = uuid.uuid4()
    plaintext = b"Envelope integrity check payload body."
    meta = backend.store_encrypted_bytes(organisation_id=org_id, project_id=proj_id, data=plaintext)

    # Valid positive Content-Length succeeds
    download_mode = "valid_positive"
    assert (
        backend.read_decrypted_bytes(
            storage_object_key=meta.storage_object_key,
            organisation_id=org_id,
            project_id=proj_id,
            key_id=SUPABASE_KEY_ID,
            expected_plaintext_size=len(plaintext),
        )
        == plaintext
    )

    # Missing Content-Length falls back cleanly to ciphertext envelope + GCM + size checks
    download_mode = "missing_header"
    assert (
        backend.read_decrypted_bytes(
            storage_object_key=meta.storage_object_key,
            organisation_id=org_id,
            project_id=proj_id,
            key_id=SUPABASE_KEY_ID,
            expected_plaintext_size=len(plaintext),
        )
        == plaintext
    )

    # Zero, under-declared, over-declared, and inconsistent ciphertext sizes all fail closed
    for mode in (
        "zero_header_empty_body",
        "zero_header_non_empty_body",
        "smaller_than_actual",
        "larger_than_actual",
        "truncated_ciphertext_matching_header",
    ):
        download_mode = mode
        with pytest.raises(ServiceUnavailableError) as exc_info:
            backend.read_decrypted_bytes(
                storage_object_key=meta.storage_object_key,
                organisation_id=org_id,
                project_id=proj_id,
                key_id=SUPABASE_KEY_ID,
                expected_plaintext_size=len(plaintext),
            )
        assert exc_info.value.code == "STORAGE_INTEGRITY_FAILED", mode


def test_supabase_storage_upload_response_validation_contract() -> None:
    org_id = uuid.uuid4()
    proj_id = uuid.uuid4()
    payload = b"Upload validation test document content"

    def _run_upload_with(response_factory: Callable[[str], httpx.Response]) -> StoredObjectMetadata:
        def handler(request: httpx.Request) -> httpx.Response:
            key = request.url.path.split("/project-evidence/", 1)[1]
            return response_factory(key)

        backend = SupabaseStorageBackend(
            base_url=_BASE_URL,
            bucket="project-evidence",
            service_role_key=_SERVICE_ROLE_KEY,
            file_encryption_key=_FILE_KEY,
            max_retries=1,
            retry_backoff_seconds=0.0,
            http_transport=httpx.MockTransport(handler),
        )
        return backend.store_encrypted_bytes(
            organisation_id=org_id,
            project_id=proj_id,
            data=payload,
        )

    # HTTP 200 and HTTP 201 with valid "{bucket}/{key}" contract succeed
    meta_200 = _run_upload_with(
        lambda key: httpx.Response(200, json={"Key": f"project-evidence/{key}", "Id": "obj-1"})
    )
    assert meta_200.storage_provider == StorageProvider.SUPABASE_STORAGE.value
    meta_201 = _run_upload_with(
        lambda key: httpx.Response(201, json={"Key": f"project-evidence/{key}"})
    )
    assert meta_201.storage_provider == StorageProvider.SUPABASE_STORAGE.value

    # Invalid / mismatched / missing / malformed upload responses fail with STORAGE_INTEGRITY_FAILED
    bad_responses: list[Callable[[str], httpx.Response]] = [
        lambda key: httpx.Response(200, json={"Key": f"project-evidence/{org_id}/wrong.enc"}),
        lambda key: httpx.Response(200, json={"Key": f"other-bucket/{key}"}),
        lambda key: httpx.Response(200, json={"Key": key}),
        lambda _key: httpx.Response(200, json={"Key": 123}),
        lambda _key: httpx.Response(200, json={}),
        lambda _key: httpx.Response(200, json={"Id": "uuid-without-key"}),
        lambda _key: httpx.Response(200, json={"Key": None}),
        lambda _key: httpx.Response(200, content=b"not-valid-json"),
        lambda _key: httpx.Response(200, content=b""),
        lambda _key: httpx.Response(201, content=b"   "),
        lambda _key: httpx.Response(200, json=["unexpected", "list"]),
        lambda _key: httpx.Response(200, json="unexpected-string"),
    ]
    for factory in bad_responses:
        with pytest.raises(ServiceUnavailableError) as exc_info:
            _run_upload_with(factory)
        assert exc_info.value.code == "STORAGE_INTEGRITY_FAILED"

    # Non-retryable HTTP error returns STORAGE_UPLOAD_FAILED without retrying
    http_error_calls = 0

    def error_handler(_request: httpx.Request) -> httpx.Response:
        nonlocal http_error_calls
        http_error_calls += 1
        return httpx.Response(400, json={"error": "InvalidRequest"})

    err_backend = SupabaseStorageBackend(
        base_url=_BASE_URL,
        bucket="project-evidence",
        service_role_key=_SERVICE_ROLE_KEY,
        file_encryption_key=_FILE_KEY,
        max_retries=2,
        retry_backoff_seconds=0.0,
        http_transport=httpx.MockTransport(error_handler),
    )
    with pytest.raises(ServiceUnavailableError) as upload_err:
        err_backend.store_encrypted_bytes(organisation_id=org_id, project_id=proj_id, data=payload)
    assert upload_err.value.code == "STORAGE_UPLOAD_FAILED"
    assert http_error_calls == 1

    # Retryable 503 followed by valid 201 + contract Key succeeds
    retry_calls = 0

    def retry_then_ok(request: httpx.Request) -> httpx.Response:
        nonlocal retry_calls
        retry_calls += 1
        if retry_calls == 1:
            return httpx.Response(503, json={"error": "temporary"})
        key = request.url.path.split("/project-evidence/", 1)[1]
        return httpx.Response(201, json={"Key": f"project-evidence/{key}", "Id": "retry-ok"})

    retry_backend = SupabaseStorageBackend(
        base_url=_BASE_URL,
        bucket="project-evidence",
        service_role_key=_SERVICE_ROLE_KEY,
        file_encryption_key=_FILE_KEY,
        max_retries=2,
        retry_backoff_seconds=0.0,
        http_transport=httpx.MockTransport(retry_then_ok),
    )
    retried_meta = retry_backend.store_encrypted_bytes(
        organisation_id=org_id,
        project_id=proj_id,
        data=payload,
    )
    assert retry_calls == 2
    assert retried_meta.storage_object_key.startswith(f"{org_id}/{proj_id}/")
