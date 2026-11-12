"""Shared private storage backend builder used identically by FastAPI API and workers."""

from __future__ import annotations

import httpx

from app.core.config import Settings
from app.models.enums import StorageProvider
from app.services.storage import LocalPrivateStorageBackend, StorageBackend
from app.services.supabase_storage import SupabaseStorageBackend


def build_storage_backend(
    settings: Settings,
    *,
    http_transport: httpx.BaseTransport | None = None,
) -> StorageBackend:
    """Construct the configured private encrypted storage backend consistently."""
    storage_cfg = settings.storage
    file_encryption_key = settings.security.file_encryption_key.get_secret_value()

    if storage_cfg.provider == StorageProvider.SUPABASE_STORAGE.value:
        if not storage_cfg.supabase_url:
            raise ValueError("SUPABASE_URL is required when STORAGE_PROVIDER='supabase_storage'.")
        service_role_key = (
            storage_cfg.supabase_service_role_key.get_secret_value().strip()
            if storage_cfg.supabase_service_role_key is not None
            else ""
        )
        if not service_role_key:
            raise ValueError(
                "SUPABASE_SERVICE_ROLE_KEY is required when STORAGE_PROVIDER='supabase_storage'."
            )
        return SupabaseStorageBackend(
            base_url=storage_cfg.supabase_url,
            bucket=storage_cfg.supabase_storage_bucket,
            service_role_key=service_role_key,
            file_encryption_key=file_encryption_key,
            timeout_seconds=storage_cfg.supabase_storage_timeout_seconds,
            max_retries=storage_cfg.supabase_storage_max_retries,
            retry_backoff_seconds=storage_cfg.supabase_storage_retry_backoff_seconds,
            verify_ciphertext_size=storage_cfg.supabase_storage_verify_ciphertext_size,
            http_transport=http_transport,
        )

    return LocalPrivateStorageBackend(
        root_path=storage_cfg.upload_storage_path,
        file_encryption_key=file_encryption_key,
    )
