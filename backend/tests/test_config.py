"""Tests for Pydantic Settings loading, domain separation, and security validation."""

from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import ValidationError

from app.core.config import Settings
from tests.conftest import build_test_settings


def test_separated_domain_configurations() -> None:
    settings = build_test_settings(
        chroma_host="chromadb",
        chroma_port=8000,
        ollama_base_url="http://host.docker.internal:11434/",
    )

    assert settings.database.host == "127.0.0.1"
    assert settings.database.port == 5432
    assert settings.database.name == "test_db"
    assert settings.database.sqlalchemy_url().startswith("postgresql+psycopg://")

    assert settings.chroma.base_url == "http://chromadb:8000"
    assert settings.chroma.collection_prefix == "ipkrh_test"

    assert settings.ollama.base_url == "http://host.docker.internal:11434"
    assert settings.ollama.llm_model == "qwen3:8b"
    assert settings.ollama.llm_num_ctx == 8192
    assert settings.ollama.llm_num_predict == 2048
    assert settings.ollama.llm_think is False
    assert settings.ollama.embedding_model == "nomic-embed-text"
    assert settings.ollama.ocr_model == "glm-ocr:latest"
    assert settings.extraction.prompt_version == "p2.6-v1"
    assert settings.extraction.max_retries >= 1
    assert settings.extraction.auto_reextract_on_update is False


def test_cors_parsing_and_wildcard_rejection() -> None:
    parsed = build_test_settings(
        cors_allowed_origins="http://localhost:3000/, https://app.example.com"
    )
    assert parsed.cors_allowed_origins == [
        "http://localhost:3000",
        "https://app.example.com",
    ]

    json_parsed = build_test_settings(cors_allowed_origins='["http://localhost:3000"]')
    assert json_parsed.cors_allowed_origins == ["http://localhost:3000"]

    with pytest.raises(ValidationError, match="Wildcard"):
        build_test_settings(cors_allowed_origins="*")

    with pytest.raises(ValidationError, match="Wildcard"):
        build_test_settings(cors_allowed_origins="http://localhost:3000,*")


def test_production_mode_enforces_security_invariants() -> None:
    # Missing cookie_secure in production must fail fast.
    with pytest.raises(ValidationError, match="COOKIE_SECURE"):
        build_test_settings(
            app_env="production",
            cookie_secure=False,
            postgres_ssl_mode="require",
        )

    # Placeholder secrets must fail fast in production.
    with pytest.raises(ValidationError, match="JWT_SECRET_KEY"):
        build_test_settings(
            app_env="production",
            cookie_secure=True,
            postgres_ssl_mode="require",
            jwt_secret_key="change-me-generate-minimum-32-byte-random-secret",
        )

    # Disabled TLS for PostgreSQL must fail in production.
    with pytest.raises(ValidationError, match="POSTGRES_SSL_MODE"):
        build_test_settings(
            app_env="production",
            cookie_secure=True,
            postgres_ssl_mode="disable",
        )

    # Valid hardened production config succeeds cleanly.
    prod = build_test_settings(
        app_env="production",
        cookie_secure=True,
        postgres_ssl_mode="require",
        cors_allowed_origins="https://handover.internal.example",
    )
    assert prod.is_production is True


def test_rejects_unsupported_database_driver_and_bad_urls() -> None:
    with pytest.raises(ValidationError, match="postgresql\\+psycopg"):
        build_test_settings(database_url="sqlite:///./should_fail.db")

    with pytest.raises(ValidationError, match="percent-encode"):
        build_test_settings(
            database_url="postgresql+psycopg://postgres.proj:sec#ret@pooler.example.com:5432/postgres"
        )

    with pytest.raises(ValidationError, match="percent-encode"):
        build_test_settings(
            database_url="postgresql+psycopg://postgres.proj:sec@ret@pooler.example.com:5432/postgres"
        )

    with pytest.raises(ValidationError, match="sslmode"):
        build_test_settings(
            app_env="production",
            cookie_secure=True,
            postgres_ssl_mode="require",
            database_url="postgresql+psycopg://postgres.proj:secret@pooler.example.com:5432/postgres?sslmode=disable",
        )

    with pytest.raises(ValidationError, match="OLLAMA_BASE_URL"):
        build_test_settings(ollama_base_url="ftp://invalid-ollama")

    with pytest.raises(ValidationError, match="COOKIE_SECURE"):
        build_test_settings(cookie_samesite="none", cookie_secure=False)


def test_supabase_style_pooler_url_and_ssl_require() -> None:
    settings = build_test_settings(
        postgres_ssl_mode="require",
        postgres_connect_timeout_seconds=20,
        database_url=(
            "postgresql+psycopg://postgres.example_ref:p%40ss%23word%3A1"
            "@region-1.pooler.supabase.com:5432/postgres"
        ),
    )
    assert settings.database.ssl_mode == "require"
    assert settings.database.connect_timeout_seconds == 20
    assert settings.database.sqlalchemy_url().startswith("postgresql+psycopg://")
    rendered = f"{repr(settings)} {str(settings)} {repr(settings.database)}"
    assert "p%40ss%23word%3A1" not in rendered


def test_secret_fields_masked_in_representations() -> None:
    settings = build_test_settings(
        postgres_password="super-secret-pg-password",
        jwt_secret_key="super-secret-jwt-value-for-signing-tokens",
        token_encryption_key="super-secret-token-encryption-key-value",
        file_encryption_key="super-secret-file-encryption-key-value!",
        chroma_auth_token="super-secret-chroma-token",
    )
    rendered = f"{repr(settings)} {str(settings)} {repr(settings.database)}"
    for secret in (
        "super-secret-pg-password",
        "super-secret-jwt-value-for-signing-tokens",
        "super-secret-token-encryption-key-value",
        "super-secret-file-encryption-key-value!",
        "super-secret-chroma-token",
    ):
        assert secret not in rendered


def test_loads_from_explicit_env_file(tmp_path: Path) -> None:
    env_file = tmp_path / "test.env"
    env_file.write_text(
        "\n".join(
            [
                "APP_ENV=test",
                "CORS_ALLOWED_ORIGINS=http://localhost:3000",
                "POSTGRES_PASSWORD=env-file-pg-pass",
                "DATABASE_URL=postgresql+psycopg://postgres:env-file-pg-pass@localhost:5432/knowledge_handover",
                "JWT_SECRET_KEY=env-file-jwt-secret-key-with-32-plus-chars",
                "TOKEN_ENCRYPTION_KEY=env-file-token-key-with-32-plus-characters",
                "FILE_ENCRYPTION_KEY=env-file-file-key-with-32-plus-characters!",
            ]
        ),
        encoding="utf-8",
    )
    settings = Settings(_env_file=env_file)
    assert settings.app_env == "test"
    assert settings.database.name == "knowledge_handover"
    assert settings.chroma.base_url == "http://localhost:8001"
