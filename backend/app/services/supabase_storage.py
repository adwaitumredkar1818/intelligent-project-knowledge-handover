"""Supabase Storage private backend reusing canonical AES-256-GCM envelope encryption."""

from __future__ import annotations

import logging
import re
import time
import uuid
from urllib.parse import urlparse

import httpx

from app.core.exceptions import ServiceUnavailableError
from app.models.enums import StorageProvider
from app.services.storage import (
    ENCRYPTION_ALGORITHM,
    SUPABASE_KEY_ID,
    StoredObjectMetadata,
    decrypt_storage_envelope,
    derive_aes256_storage_key,
    encrypt_storage_envelope,
    expected_envelope_size_bytes,
    generate_storage_object_key,
    validate_storage_object_key,
)

logger = logging.getLogger("app.services.supabase_storage")

_BUCKET_PATTERN = re.compile(r"^[a-z0-9](?:[a-z0-9._-]{0,61}[a-z0-9])?$")
_RETRYABLE_STATUS_CODES = frozenset({429, 500, 502, 503, 504})


def _is_supabase_not_found_response(response: httpx.Response) -> bool:
    if response.status_code == 404:
        return True
    if response.status_code != 400:
        return False
    try:
        payload = response.json()
    except Exception:
        return False
    if not isinstance(payload, dict):
        return False
    status_code = str(payload.get("statusCode") or "").strip()
    error_code = str(payload.get("error") or "").strip().lower()
    message = str(payload.get("message") or "").strip().lower()
    return status_code == "404" or error_code == "not_found" or "object not found" in message


def _parse_strict_content_length(raw_value: str) -> int:
    """Parse HTTP Content-Length strictly as a non-negative ASCII base-10 integer."""
    cleaned = raw_value.strip()
    if not cleaned or not cleaned.isascii() or not cleaned.isdigit():
        raise ServiceUnavailableError(
            "Downloaded ciphertext returned an invalid Content-Length header.",
            code="STORAGE_INTEGRITY_FAILED",
        )
    return int(cleaned)


class SupabaseStorageBackend:
    """Private Supabase Storage backend with canonical client-side AES-256-GCM encryption."""

    def __init__(
        self,
        *,
        base_url: str,
        bucket: str = "project-evidence",
        service_role_key: str,
        file_encryption_key: str,
        timeout_seconds: float = 30.0,
        max_retries: int = 2,
        retry_backoff_seconds: float = 0.5,
        verify_ciphertext_size: bool = True,
        http_transport: httpx.BaseTransport | None = None,
    ) -> None:
        cleaned_url = base_url.strip().rstrip("/")
        parsed = urlparse(cleaned_url)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise ValueError("SUPABASE_URL must be a valid http(s) URL.")

        cleaned_bucket = bucket.strip()
        if (
            not cleaned_bucket
            or "/" in cleaned_bucket
            or "\\" in cleaned_bucket
            or ".." in cleaned_bucket
            or not _BUCKET_PATTERN.fullmatch(cleaned_bucket)
        ):
            raise ValueError("Invalid Supabase Storage bucket identifier.")

        cleaned_key = service_role_key.strip()
        if not cleaned_key:
            raise ValueError("SUPABASE_SERVICE_ROLE_KEY is required for Supabase Storage.")
        if cleaned_key.startswith("sb_publishable_"):
            raise ValueError("Publishable keys are not permitted for server-side storage access.")

        if timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be positive.")
        if max_retries < 0:
            raise ValueError("max_retries must be non-negative.")
        if retry_backoff_seconds < 0:
            raise ValueError("retry_backoff_seconds must be non-negative.")

        self._raw_base_url = cleaned_url
        self._storage_endpoint = f"{cleaned_url}/storage/v1"
        self._bucket = cleaned_bucket
        self._service_role_key = cleaned_key
        self._aes_key = derive_aes256_storage_key(file_encryption_key)
        self._timeout_seconds = timeout_seconds
        self._max_retries = max_retries
        self._retry_backoff_seconds = retry_backoff_seconds
        self._verify_ciphertext_size = verify_ciphertext_size
        self._http_transport = http_transport

    def __repr__(self) -> str:
        return (
            f"SupabaseStorageBackend(base_url={self._raw_base_url!r}, "
            f"bucket={self._bucket!r}, verify_ciphertext_size={self._verify_ciphertext_size!r})"
        )

    @property
    def bucket(self) -> str:
        """Configured private Supabase Storage bucket name."""
        return self._bucket

    def _get_client(self) -> httpx.Client:
        headers = {
            "Authorization": f"Bearer {self._service_role_key}",
            "apikey": self._service_role_key,
        }
        return httpx.Client(
            base_url=self._storage_endpoint,
            headers=headers,
            transport=self._http_transport,
            timeout=self._timeout_seconds,
        )

    def _sleep_before_retry(self, attempt: int) -> None:
        if self._retry_backoff_seconds > 0:
            time.sleep(self._retry_backoff_seconds * (2**attempt))

    def _request_with_retries(
        self,
        *,
        method: str,
        path: str,
        content: bytes | None = None,
        headers: dict[str, str] | None = None,
    ) -> httpx.Response:
        total_attempts = self._max_retries + 1
        with self._get_client() as client:
            for attempt in range(total_attempts):
                try:
                    response = client.request(
                        method=method,
                        url=path,
                        content=content,
                        headers=headers,
                    )
                except httpx.TimeoutException as exc:
                    logger.warning(
                        "Supabase Storage %s %s timed out (attempt %s/%s)",
                        method,
                        path,
                        attempt + 1,
                        total_attempts,
                    )
                    if attempt + 1 < total_attempts:
                        self._sleep_before_retry(attempt)
                        continue
                    raise ServiceUnavailableError(
                        "Supabase Storage request timed out.",
                        code="STORAGE_TIMEOUT",
                    ) from exc
                except httpx.HTTPError as exc:
                    logger.warning(
                        "Supabase Storage %s %s transport error (%s, attempt %s/%s)",
                        method,
                        path,
                        type(exc).__name__,
                        attempt + 1,
                        total_attempts,
                    )
                    if attempt + 1 < total_attempts:
                        self._sleep_before_retry(attempt)
                        continue
                    raise ServiceUnavailableError(
                        "Storage service is unreachable.",
                        code="STORAGE_UNAVAILABLE",
                    ) from exc

                if (
                    response.status_code in _RETRYABLE_STATUS_CODES
                    and attempt + 1 < total_attempts
                ):
                    logger.warning(
                        "Supabase Storage %s %s returned transient status %s (attempt %s/%s)",
                        method,
                        path,
                        response.status_code,
                        attempt + 1,
                        total_attempts,
                    )
                    self._sleep_before_retry(attempt)
                    continue

                return response

        raise ServiceUnavailableError(
            "Storage service request failed after retries.",
            code="STORAGE_UNAVAILABLE",
        )

    def store_encrypted_bytes(
        self,
        *,
        organisation_id: uuid.UUID,
        project_id: uuid.UUID,
        data: bytes,
    ) -> StoredObjectMetadata:
        """Encrypt payload with canonical AES-256-GCM envelope and upload to private bucket."""
        object_key = generate_storage_object_key(
            organisation_id=organisation_id,
            project_id=project_id,
        )
        envelope = encrypt_storage_envelope(
            aes_key=self._aes_key,
            organisation_id=organisation_id,
            project_id=project_id,
            object_key=object_key,
            plaintext=data,
        )
        expected_len = expected_envelope_size_bytes(len(data))
        if len(envelope) != expected_len:
            raise ServiceUnavailableError(
                "Encrypted payload envelope size mismatch.",
                code="STORAGE_INTEGRITY_FAILED",
            )

        upload_path = f"/object/{self._bucket}/{object_key}"
        resp = self._request_with_retries(
            method="POST",
            path=upload_path,
            content=envelope,
            headers={
                "Content-Type": "application/octet-stream",
                "x-upsert": "false",
                "Cache-Control": "no-store",
            },
        )
        if resp.status_code not in (200, 201):
            logger.error(
                "Supabase Storage upload failed: status=%s, bucket=%s",
                resp.status_code,
                self._bucket,
            )
            raise ServiceUnavailableError(
                "Failed to persist encrypted document to Supabase Storage.",
                code="STORAGE_UPLOAD_FAILED",
            )

        self._validate_upload_response(response=resp, expected_object_key=object_key)

        return StoredObjectMetadata(
            storage_provider=StorageProvider.SUPABASE_STORAGE.value,
            storage_object_key=object_key,
            encryption_algorithm=ENCRYPTION_ALGORITHM,
            encryption_key_id=SUPABASE_KEY_ID,
            ciphertext_size_bytes=len(envelope),
        )

    def _validate_upload_response(
        self,
        *,
        response: httpx.Response,
        expected_object_key: str,
    ) -> None:
        raw_body = response.content
        if not raw_body or not raw_body.strip():
            logger.error(
                "Supabase Storage upload returned an empty response body: status=%s, bucket=%s",
                response.status_code,
                self._bucket,
            )
            raise ServiceUnavailableError(
                "Supabase Storage upload returned an empty response payload.",
                code="STORAGE_INTEGRITY_FAILED",
            )

        try:
            payload = response.json()
        except (ValueError, UnicodeDecodeError) as exc:
            logger.error(
                "Supabase Storage upload returned invalid JSON: status=%s, bucket=%s",
                response.status_code,
                self._bucket,
            )
            raise ServiceUnavailableError(
                "Supabase Storage upload returned an invalid response payload.",
                code="STORAGE_INTEGRITY_FAILED",
            ) from exc

        if not isinstance(payload, dict):
            logger.error(
                "Supabase Storage upload returned unexpected response type (%s): "
                "status=%s, bucket=%s",
                type(payload).__name__,
                response.status_code,
                self._bucket,
            )
            raise ServiceUnavailableError(
                "Supabase Storage upload returned an unexpected response structure.",
                code="STORAGE_INTEGRITY_FAILED",
            )

        expected_full_key = f"{self._bucket}/{expected_object_key}"
        returned_key = payload.get("Key")
        if returned_key is None:
            logger.error(
                "Supabase Storage upload response omitted Key field: status=%s, bucket=%s",
                response.status_code,
                self._bucket,
            )
            raise ServiceUnavailableError(
                "Supabase Storage upload response omitted the stored object key.",
                code="STORAGE_INTEGRITY_FAILED",
            )

        if not isinstance(returned_key, str) or returned_key != expected_full_key:
            logger.error(
                "Supabase Storage upload returned mismatched object key: status=%s, bucket=%s",
                response.status_code,
                self._bucket,
            )
            raise ServiceUnavailableError(
                "Supabase Storage upload returned an unexpected object key.",
                code="STORAGE_INTEGRITY_FAILED",
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
        """Download ciphertext from private Supabase Storage, verify envelope/size, and decrypt."""
        if key_id is not None and key_id != SUPABASE_KEY_ID:
            raise ServiceUnavailableError(
                "Stored artefact references an unsupported encryption key version.",
                code="STORAGE_KEY_UNSUPPORTED",
            )
        try:
            normalized_key = validate_storage_object_key(storage_object_key)
        except ValueError as exc:
            logger.warning("Rejected unsafe Supabase storage object key lookup.")
            raise ServiceUnavailableError(
                "Stored artefact location is invalid.",
                code="STORAGE_KEY_INVALID",
            ) from exc

        download_path = f"/object/{self._bucket}/{normalized_key}"
        resp = self._request_with_retries(method="GET", path=download_path)
        if _is_supabase_not_found_response(resp):
            raise ServiceUnavailableError(
                "Stored artefact payload is missing from Supabase Storage.",
                code="STORAGE_OBJECT_MISSING",
            )
        if resp.status_code != 200:
            logger.error(
                "Supabase Storage read failed: status=%s, bucket=%s",
                resp.status_code,
                self._bucket,
            )
            raise ServiceUnavailableError(
                "Failed to retrieve document from Supabase Storage.",
                code="STORAGE_READ_FAILED",
            )

        envelope = resp.content
        if "content-length" in resp.headers:
            header_values = resp.headers.get_list("content-length", split_commas=True)
            if len(header_values) != 1:
                raise ServiceUnavailableError(
                    "Downloaded ciphertext returned ambiguous Content-Length headers.",
                    code="STORAGE_INTEGRITY_FAILED",
                )
            declared_length = _parse_strict_content_length(header_values[0])
            if len(envelope) != declared_length:
                raise ServiceUnavailableError(
                    "Downloaded ciphertext length did not match response Content-Length.",
                    code="STORAGE_INTEGRITY_FAILED",
                )

        size_check = expected_plaintext_size if self._verify_ciphertext_size else None
        return decrypt_storage_envelope(
            aes_key=self._aes_key,
            envelope=envelope,
            organisation_id=organisation_id,
            project_id=project_id,
            object_key=normalized_key,
            key_id=key_id,
            expected_key_id=SUPABASE_KEY_ID,
            expected_plaintext_size=size_check,
        )

    def delete_object(self, *, storage_object_key: str) -> bool:
        """Remove a stored encrypted object from private Supabase Storage."""
        try:
            normalized_key = validate_storage_object_key(storage_object_key)
        except ValueError:
            logger.warning("Ignored deletion for invalid storage object key.")
            return False

        delete_path = f"/object/{self._bucket}/{normalized_key}"
        try:
            resp = self._request_with_retries(method="DELETE", path=delete_path)
        except ServiceUnavailableError as exc:
            logger.warning("Supabase Storage delete failed: code=%s", exc.code)
            return False
        if resp.status_code in (200, 204):
            return True
        if _is_supabase_not_found_response(resp):
            return False
        logger.warning(
            "Supabase Storage delete returned unexpected status %s for bucket %s",
            resp.status_code,
            self._bucket,
        )
        return False

    def exists(self, *, storage_object_key: str) -> bool:
        """Check whether an opaque object key currently exists in private Supabase Storage."""
        try:
            normalized_key = validate_storage_object_key(storage_object_key)
        except ValueError:
            return False

        check_path = f"/object/info/{self._bucket}/{normalized_key}"
        resp = self._request_with_retries(method="GET", path=check_path)
        if resp.status_code == 200:
            return True
        if _is_supabase_not_found_response(resp):
            return False
        logger.error(
            "Supabase Storage existence check failed: status=%s, bucket=%s",
            resp.status_code,
            self._bucket,
        )
        raise ServiceUnavailableError(
            "Failed to verify stored artefact existence in Supabase Storage.",
            code="STORAGE_UNAVAILABLE",
        )
