"""Centralised Pydantic Settings configuration loaded from root `.env`."""

from __future__ import annotations

import json
import re
from functools import cached_property, lru_cache
from pathlib import Path
from typing import Annotated, Any, Literal
from urllib.parse import parse_qs, urlparse

from pydantic import BaseModel, ConfigDict, Field, SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict
from sqlalchemy.engine import make_url

AppEnv = Literal["development", "test", "production"]
LogLevel = Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
PostgresSslMode = Literal["disable", "allow", "prefer", "require", "verify-ca", "verify-full"]
CookieSameSite = Literal["lax", "strict", "none"]
AllowedJwtAlgorithm = Literal["HS256", "HS384", "HS512"]
StorageBackendProvider = Literal["local_encrypted", "supabase_storage"]

_STORAGE_BUCKET_PATTERN = re.compile(r"^[a-z0-9](?:[a-z0-9._-]{0,61}[a-z0-9])?$")

_REPO_ROOT = Path(__file__).resolve().parents[3]
_DEFAULT_ENV_FILE = _REPO_ROOT / ".env"


def _normalize_optional_str(value: str | None) -> str | None:
    if value is None:
        return None
    stripped = value.strip()
    return stripped or None


def _require_http_url(value: str, field_name: str) -> str:
    cleaned = value.strip().rstrip("/")
    parsed = urlparse(cleaned)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ValueError(f"{field_name} must be a valid http(s) URL.")
    return cleaned


class StorageSettings(BaseModel):
    """Explicit private encrypted object storage configuration (local or Supabase Storage)."""

    model_config = ConfigDict(frozen=True)

    provider: StorageBackendProvider = "local_encrypted"
    upload_storage_path: Path = Path("./data/uploads")
    supabase_url: str | None = None
    supabase_service_role_key: SecretStr | None = None
    supabase_storage_bucket: str = "project-evidence"
    supabase_storage_timeout_seconds: float = Field(default=30.0, gt=0.5, le=300.0)
    supabase_storage_max_retries: int = Field(default=2, ge=0, le=5)
    supabase_storage_retry_backoff_seconds: float = Field(default=0.5, ge=0.0, le=10.0)
    supabase_storage_verify_ciphertext_size: bool = True

    @field_validator("supabase_storage_bucket", mode="before")
    @classmethod
    def _validate_bucket_name(cls, value: Any) -> str:
        cleaned = str(value or "").strip()
        if (
            not cleaned
            or "/" in cleaned
            or "\\" in cleaned
            or ".." in cleaned
            or not _STORAGE_BUCKET_PATTERN.fullmatch(cleaned)
        ):
            raise ValueError(
                "SUPABASE_STORAGE_BUCKET must be a valid lowercase bucket identifier "
                "(letters, digits, '.', '_', '-'; no slashes or traversal)."
            )
        return cleaned

    @model_validator(mode="after")
    def _validate_storage_provider(self) -> StorageSettings:
        normalized_url = _normalize_optional_str(self.supabase_url)
        if normalized_url is not None:
            normalized_url = _require_http_url(normalized_url, "SUPABASE_URL")
            object.__setattr__(self, "supabase_url", normalized_url)

        service_key = (
            self.supabase_service_role_key.get_secret_value().strip()
            if self.supabase_service_role_key is not None
            else ""
        )
        if service_key.startswith("sb_publishable_"):
            raise ValueError(
                "SUPABASE_SERVICE_ROLE_KEY must not be a publishable key; "
                "configure a server-side service-role or secret key."
            )

        if self.provider == "supabase_storage":
            if not normalized_url:
                raise ValueError(
                    "SUPABASE_URL is required when STORAGE_PROVIDER='supabase_storage'."
                )
            if not service_key:
                raise ValueError(
                    "SUPABASE_SERVICE_ROLE_KEY is required when "
                    "STORAGE_PROVIDER='supabase_storage'."
                )
        return self


class DatabaseSettings(BaseModel):
    """PostgreSQL connectivity settings (canonical application database)."""

    model_config = ConfigDict(frozen=True)

    host: str = Field(min_length=1)
    port: int = Field(ge=1, le=65535)
    name: str = Field(min_length=1)
    user: str = Field(min_length=1)
    password: SecretStr
    url: SecretStr
    ssl_mode: PostgresSslMode = "prefer"
    connect_timeout_seconds: int = Field(default=30, ge=1, le=60)

    @model_validator(mode="after")
    def _validate_database(self) -> DatabaseSettings:
        if not self.password.get_secret_value().strip():
            raise ValueError("POSTGRES_PASSWORD must not be empty.")
        raw_url = self.url.get_secret_value().strip()
        parsed = urlparse(raw_url)
        if parsed.scheme != "postgresql+psycopg":
            raise ValueError("DATABASE_URL must use the 'postgresql+psycopg' SQLAlchemy driver.")
        if parsed.fragment:
            raise ValueError(
                "DATABASE_URL must not contain a URL fragment ('#'); "
                "percent-encode special characters in the password."
            )
        try:
            port = parsed.port
        except ValueError as exc:
            raise ValueError(
                "DATABASE_URL contains an invalid port or unencoded special characters; "
                "percent-encode special characters in the password."
            ) from exc
        if port is not None and not (1 <= port <= 65535):
            raise ValueError("DATABASE_URL port must be between 1 and 65535.")
        try:
            sa_url = make_url(raw_url)
        except Exception as exc:
            raise ValueError("DATABASE_URL is not a valid SQLAlchemy database URL.") from exc
        if (
            not parsed.hostname
            or not parsed.path.lstrip("/")
            or not sa_url.host
            or not sa_url.database
        ):
            raise ValueError("DATABASE_URL must include a valid host and database name.")
        if "@" in sa_url.host:
            raise ValueError(
                "DATABASE_URL host contains '@'; percent-encode special characters in the password."
            )
        return self

    def sqlalchemy_url(self) -> str:
        """Return raw SQLAlchemy connection URL strictly for internal engine creation."""
        return self.url.get_secret_value()


class ChromaSettings(BaseModel):
    """ChromaDB HTTP server settings (secondary rebuildable vector index)."""

    model_config = ConfigDict(frozen=True)

    host: str = Field(min_length=1)
    port: int = Field(ge=1, le=65535)
    collection_prefix: str = Field(min_length=1)
    auth_token: SecretStr | None = None
    tenant: str = Field(default="default_tenant", min_length=1)
    database: str = Field(default="default_database", min_length=1)
    index_version: str = Field(default="v1", min_length=1)
    health_timeout_seconds: float = Field(default=2.0, gt=0.1, le=30.0)
    request_timeout_seconds: float = Field(default=15.0, gt=0.5, le=120.0)

    @property
    def base_url(self) -> str:
        """Return HTTP base URL for the dedicated ChromaDB server."""
        return f"http://{self.host}:{self.port}"


class ChunkingSettings(BaseModel):
    """Empirical structure-aware evidence chunking boundaries calibrated for nomic-embed-text."""

    model_config = ConfigDict(frozen=True)

    target_chars: int = Field(default=1100, ge=200, le=3000)
    max_chars: int = Field(default=1400, ge=300, le=4000)
    overlap_chars: int = Field(default=150, ge=0, le=600)
    min_chars: int = Field(default=120, ge=20, le=600)

    @model_validator(mode="after")
    def _validate_bounds(self) -> ChunkingSettings:
        if not (self.min_chars <= self.target_chars <= self.max_chars):
            raise ValueError(
                "CHUNK_MIN_CHARS <= CHUNK_TARGET_CHARS <= CHUNK_MAX_CHARS must hold."
            )
        if self.overlap_chars >= self.target_chars:
            raise ValueError("CHUNK_OVERLAP_CHARS must be strictly less than CHUNK_TARGET_CHARS.")
        return self


class EmbeddingSettings(BaseModel):
    """Embedding batching and consistency validation settings."""

    model_config = ConfigDict(frozen=True)

    batch_size: int = Field(default=8, ge=1, le=64)
    expected_dimensions: int = Field(default=768, ge=64, le=4096)
    timeout_seconds: float = Field(default=60.0, gt=1.0, le=300.0)


class RetrievalSettings(BaseModel):
    """Hybrid keyword + semantic retrieval candidate fetch and Reciprocal Rank Fusion tuning."""

    model_config = ConfigDict(frozen=True)

    default_top_k: int = Field(default=10, ge=1, le=100)
    max_top_k: int = Field(default=50, ge=1, le=200)
    candidate_multiplier: int = Field(default=4, ge=1, le=20)
    min_candidate_limit: int = Field(default=40, ge=5, le=500)
    rrf_k: int = Field(default=60, ge=1, le=500)
    semantic_weight: float = Field(default=1.0, ge=0.0, le=10.0)
    keyword_weight: float = Field(default=1.0, ge=0.0, le=10.0)
    min_semantic_similarity: float = Field(default=0.15, ge=0.0, le=1.0)
    min_keyword_score: float = Field(default=0.0, ge=0.0, le=1.0)
    min_hybrid_score: float = Field(default=0.0, ge=0.0, le=1.0)

    @model_validator(mode="after")
    def _validate_retrieval(self) -> RetrievalSettings:
        if self.default_top_k > self.max_top_k:
            raise ValueError("RETRIEVAL_DEFAULT_TOP_K must not exceed RETRIEVAL_MAX_TOP_K.")
        if self.semantic_weight + self.keyword_weight <= 0.0:
            raise ValueError(
                "RETRIEVAL_SEMANTIC_WEIGHT + RETRIEVAL_KEYWORD_WEIGHT must be positive."
            )
        return self


class OllamaSettings(BaseModel):
    """Local Ollama runtime configuration (LLM, embeddings, and OCR)."""

    model_config = ConfigDict(frozen=True)

    base_url: str
    llm_model: str = Field(min_length=1)
    embedding_model: str = Field(min_length=1)
    ocr_model: str = Field(min_length=1)
    health_timeout_seconds: float = Field(default=2.0, gt=0.1, le=30.0)
    llm_num_ctx: int = Field(default=8192, ge=2048, le=40960)
    llm_num_predict: int = Field(default=2048, ge=256, le=8192)
    llm_temperature: float = Field(default=0.1, ge=0.0, le=1.0)
    llm_timeout_seconds: float = Field(default=120.0, gt=1.0, le=600.0)
    llm_think: bool = False
    ocr_num_ctx: int = Field(default=8192, ge=2048, le=65536)
    ocr_num_predict: int = Field(default=4096, ge=256, le=16384)
    ocr_timeout_seconds: float = Field(default=120.0, gt=1.0, le=600.0)

    @field_validator("base_url")
    @classmethod
    def _validate_base_url(cls, value: str) -> str:
        return _require_http_url(value, "OLLAMA_BASE_URL")


class ExtractionSettings(BaseModel):
    """Phase 2.6 bounded knowledge reconstruction & validation configuration."""

    model_config = ConfigDict(frozen=True)

    prompt_version: str = Field(default="p2.6-v1", min_length=1, max_length=64)
    max_retries: int = Field(default=2, ge=0, le=5)
    max_chunks_per_batch: int = Field(default=6, ge=1, le=20)
    max_chars_per_batch: int = Field(default=5500, ge=1000, le=24000)
    auto_reextract_on_update: bool = False


class IngestionSettings(BaseModel):
    """Document validation, OCR triage bounds, and background worker settings."""

    model_config = ConfigDict(frozen=True)

    max_upload_size_mb: int = Field(default=50, ge=1, le=500)
    max_document_pages: int = Field(default=200, ge=1, le=2000)
    ocr_render_dpi: int = Field(default=150, ge=72, le=300)
    ocr_max_image_dimension: int = Field(default=2048, ge=512, le=4096)
    ocr_min_text_chars_per_page: int = Field(default=40, ge=0, le=1000)
    ocr_max_pages_per_document: int = Field(default=40, ge=1, le=500)
    worker_poll_interval_seconds: float = Field(default=5.0, ge=0.2, le=300.0)
    worker_max_attempts: int = Field(default=3, ge=1, le=10)
    worker_retry_base_seconds: int = Field(default=15, ge=1, le=3600)
    worker_lease_seconds: int = Field(default=300, ge=30, le=3600)

    @property
    def max_upload_size_bytes(self) -> int:
        """Return the strict maximum upload size in bytes."""
        return self.max_upload_size_mb * 1024 * 1024


class SecuritySettings(BaseModel):
    """Security-conscious platform token, cookie, and private storage settings."""

    model_config = ConfigDict(frozen=True)

    jwt_secret_key: SecretStr
    jwt_algorithm: AllowedJwtAlgorithm = "HS256"
    jwt_issuer: str | None = "ipkrh-platform"
    jwt_audience: str | None = "ipkrh-api"
    jwt_access_token_expire_minutes: int = Field(ge=1, le=1440)
    jwt_refresh_token_expire_days: int = Field(ge=1, le=90)
    token_encryption_key: SecretStr
    file_encryption_key: SecretStr
    upload_storage_path: Path
    cookie_secure: bool
    cookie_samesite: CookieSameSite
    cookie_domain: str | None = None
    refresh_cookie_name: str = "ipkrh_refresh_token"
    refresh_cookie_path: str = "/api/v1/auth"
    auth_rate_limit_enabled: bool = True
    auth_rate_limit_max_attempts: int = Field(default=20, ge=1, le=10000)
    auth_rate_limit_window_seconds: int = Field(default=60, ge=1, le=3600)

    @field_validator("refresh_cookie_path")
    @classmethod
    def _validate_cookie_path(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned.startswith("/"):
            raise ValueError("refresh_cookie_path must start with '/'.")
        return cleaned


class GitHubIntegrationSettings(BaseModel):
    """GitHub delegated OAuth & REST API configuration."""

    model_config = ConfigDict(frozen=True)

    enabled: bool = False
    auth_base_url: str = "https://github.com"
    api_base_url: str = "https://api.github.com"
    client_id: str | None = None
    client_secret: SecretStr | None = None
    redirect_uri: str = "http://localhost:8000/api/v1/integrations/github/callback"
    oauth_mode: Literal["github_app", "oauth_app"] = "github_app"
    oauth_scopes: str = "read:user user:email"
    allow_classic_private_repo_scope: bool = False

    @field_validator("auth_base_url", "api_base_url", "redirect_uri")
    @classmethod
    def _validate_github_urls(cls, value: str) -> str:
        return _require_http_url(value, "GitHub integration URL")

    @model_validator(mode="after")
    def _validate_when_enabled(self) -> GitHubIntegrationSettings:
        if self.enabled:
            if not self.client_id:
                raise ValueError("GITHUB_CLIENT_ID is required when GITHUB_ENABLED=true.")
            secret = self.client_secret.get_secret_value().strip() if self.client_secret else ""
            if not secret:
                raise ValueError("GITHUB_CLIENT_SECRET is required when GITHUB_ENABLED=true.")
        return self


class JiraIntegrationSettings(BaseModel):
    """Atlassian Jira Cloud OAuth 2.0 (3LO) & REST v3 configuration."""

    model_config = ConfigDict(frozen=True)

    enabled: bool = False
    auth_base_url: str = "https://auth.atlassian.com"
    api_base_url: str = "https://api.atlassian.com"
    client_id: str | None = None
    client_secret: SecretStr | None = None
    redirect_uri: str = "http://localhost:8000/api/v1/integrations/jira/callback"
    oauth_scopes: str = "read:jira-work read:jira-user offline_access"

    @field_validator("auth_base_url", "api_base_url", "redirect_uri")
    @classmethod
    def _validate_jira_urls(cls, value: str) -> str:
        return _require_http_url(value, "Jira integration URL")

    @model_validator(mode="after")
    def _validate_when_enabled(self) -> JiraIntegrationSettings:
        if self.enabled:
            if not self.client_id:
                raise ValueError("JIRA_CLIENT_ID is required when JIRA_ENABLED=true.")
            secret = self.client_secret.get_secret_value().strip() if self.client_secret else ""
            if not secret:
                raise ValueError("JIRA_CLIENT_SECRET is required when JIRA_ENABLED=true.")
        return self


class RedisSettings(BaseModel):
    """Centralized Redis connection and caching configuration."""

    model_config = ConfigDict(frozen=True)

    enabled: bool = True
    url: SecretStr | None = None
    host: str = "127.0.0.1"
    port: int = Field(default=6379, ge=1, le=65535)
    password: SecretStr | None = None
    db: int = Field(default=0, ge=0, le=15)
    max_connections: int = Field(default=20, ge=1, le=200)
    socket_timeout: float = Field(default=2.0, ge=0.1, le=30.0)
    connect_timeout: float = Field(default=2.0, ge=0.1, le=30.0)
    cache_prefix: str = "ipkrh:cache:"
    default_ttl: int = Field(default=300, ge=1, le=86400)
    max_memory: str = "256mb"


class IntegrationsSettings(BaseModel):
    """Grouped configuration for Phase 2.4B GitHub & Jira connectors and sync bounds."""

    model_config = ConfigDict(frozen=True)

    github: GitHubIntegrationSettings
    jira: JiraIntegrationSettings
    slack_enabled: bool = False
    oauth_state_expire_minutes: int = Field(default=10, ge=1, le=60)
    http_timeout_seconds: float = Field(default=20.0, gt=0.5, le=120.0)
    sync_max_items_per_run: int = Field(default=250, ge=1, le=5000)
    allowed_post_auth_redirects: tuple[str, ...] = ()
    default_github_commits_limit: int = Field(default=50, ge=1, le=500)
    default_github_docs_limit: int = Field(default=20, ge=1, le=100)


class Settings(BaseSettings):
    """Centralised application settings loaded from environment and root `.env`."""

    model_config = SettingsConfigDict(
        env_file=_DEFAULT_ENV_FILE if _DEFAULT_ENV_FILE.exists() else None,
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Application & API runtime
    app_name: str = Field(
        default="Intelligent Project Knowledge Reconstruction & Handover Platform",
        min_length=1,
    )
    app_env: AppEnv = "development"
    log_level: LogLevel = "INFO"
    backend_host: str = Field(default="0.0.0.0", min_length=1)  # noqa: S104
    backend_port: int = Field(default=8000, ge=1, le=65535)
    cors_allowed_origins: Annotated[list[str], NoDecode] = Field(
        default_factory=lambda: ["http://localhost:3000"]
    )

    # PostgreSQL configuration fields (grouped into `settings.database`)
    postgres_host: str = Field(default="localhost", min_length=1)
    postgres_port: int = Field(default=5432, ge=1, le=65535)
    postgres_db: str = Field(default="knowledge_handover", min_length=1)
    postgres_user: str = Field(default="postgres", min_length=1)
    postgres_password: SecretStr
    database_url: SecretStr
    postgres_ssl_mode: PostgresSslMode = "prefer"
    postgres_connect_timeout_seconds: int = Field(default=5, ge=1, le=60)

    # ChromaDB configuration fields (grouped into `settings.chroma`)
    chroma_host: str = Field(default="localhost", min_length=1)
    chroma_port: int = Field(default=8001, ge=1, le=65535)
    chroma_collection_prefix: str = Field(default="ipkrh", min_length=1)
    chroma_auth_token: SecretStr | None = None
    chroma_tenant: str = Field(default="default_tenant", min_length=1)
    chroma_database: str = Field(default="default_database", min_length=1)
    chroma_index_version: str = Field(default="v1", min_length=1)
    chroma_request_timeout_seconds: float = Field(default=15.0, gt=0.5, le=120.0)

    # Chunking, embedding & hybrid retrieval settings (`settings.chunking/embedding/retrieval`)
    chunk_target_chars: int = Field(default=1100, ge=200, le=3000)
    chunk_max_chars: int = Field(default=1400, ge=300, le=4000)
    chunk_overlap_chars: int = Field(default=150, ge=0, le=600)
    chunk_min_chars: int = Field(default=120, ge=20, le=600)
    embedding_batch_size: int = Field(default=8, ge=1, le=64)
    embedding_expected_dimensions: int = Field(default=768, ge=64, le=4096)
    embedding_timeout_seconds: float = Field(default=60.0, gt=1.0, le=300.0)
    retrieval_default_top_k: int = Field(default=10, ge=1, le=100)
    retrieval_max_top_k: int = Field(default=50, ge=1, le=200)
    retrieval_candidate_multiplier: int = Field(default=4, ge=1, le=20)
    retrieval_min_candidate_limit: int = Field(default=40, ge=5, le=500)
    retrieval_rrf_k: int = Field(default=60, ge=1, le=500)
    retrieval_semantic_weight: float = Field(default=1.0, ge=0.0, le=10.0)
    retrieval_keyword_weight: float = Field(default=1.0, ge=0.0, le=10.0)
    retrieval_min_semantic_similarity: float = Field(default=0.15, ge=0.0, le=1.0)
    retrieval_min_keyword_score: float = Field(default=0.0, ge=0.0, le=1.0)
    retrieval_min_hybrid_score: float = Field(default=0.0, ge=0.0, le=1.0)

    # Ollama configuration fields (grouped into `settings.ollama`)
    ollama_base_url: str = "http://localhost:11434"
    ollama_llm_model: str = Field(default="qwen3:8b", min_length=1)
    ollama_embedding_model: str = Field(default="nomic-embed-text", min_length=1)
    ollama_ocr_model: str = Field(default="glm-ocr:latest", min_length=1)
    ollama_llm_num_ctx: int = Field(default=8192, ge=2048, le=40960)
    ollama_llm_num_predict: int = Field(default=2048, ge=256, le=8192)
    ollama_llm_temperature: float = Field(default=0.1, ge=0.0, le=1.0)
    ollama_llm_timeout_seconds: float = Field(default=120.0, gt=1.0, le=600.0)
    ollama_llm_think: bool = False
    ollama_ocr_num_ctx: int = Field(default=8192, ge=2048, le=65536)
    ollama_ocr_num_predict: int = Field(default=4096, ge=256, le=16384)
    ollama_ocr_timeout_seconds: float = Field(default=120.0, gt=1.0, le=600.0)

    # Knowledge reconstruction fields (`settings.extraction`)
    extraction_prompt_version: str = Field(default="p2.6-v1", min_length=1, max_length=64)
    extraction_max_retries: int = Field(default=2, ge=0, le=5)
    extraction_max_chunks_per_batch: int = Field(default=6, ge=1, le=20)
    extraction_max_chars_per_batch: int = Field(default=5500, ge=1000, le=24000)
    extraction_auto_reextract_on_update: bool = False

    # Document ingestion, OCR triage & lightweight worker fields (`settings.ingestion`)
    max_upload_size_mb: int = Field(default=50, ge=1, le=500)
    max_document_pages: int = Field(default=200, ge=1, le=2000)
    ocr_render_dpi: int = Field(default=150, ge=72, le=300)
    ocr_max_image_dimension: int = Field(default=2048, ge=512, le=4096)
    ocr_min_text_chars_per_page: int = Field(default=40, ge=0, le=1000)
    ocr_max_pages_per_document: int = Field(default=40, ge=1, le=500)
    worker_poll_interval_seconds: float = Field(default=5.0, ge=0.2, le=300.0)
    worker_max_attempts: int = Field(default=3, ge=1, le=10)
    worker_retry_base_seconds: int = Field(default=15, ge=1, le=3600)
    worker_lease_seconds: int = Field(default=300, ge=30, le=3600)

    # Security & storage configuration fields (grouped into `settings.security`)
    jwt_secret_key: SecretStr
    jwt_algorithm: AllowedJwtAlgorithm = "HS256"
    jwt_issuer: str | None = "ipkrh-platform"
    jwt_audience: str | None = "ipkrh-api"
    jwt_access_token_expire_minutes: int = Field(default=15, ge=1, le=1440)
    jwt_refresh_token_expire_days: int = Field(default=7, ge=1, le=90)
    token_encryption_key: SecretStr
    file_encryption_key: SecretStr
    upload_storage_path: Path = Path("./data/uploads")
    cookie_secure: bool = False
    cookie_samesite: CookieSameSite = "lax"
    cookie_domain: str | None = None
    refresh_cookie_name: str = Field(default="ipkrh_refresh_token", min_length=1)
    refresh_cookie_path: str = Field(default="/api/v1/auth", min_length=1)
    auth_rate_limit_enabled: bool = True
    auth_rate_limit_max_attempts: int = Field(default=20, ge=1, le=10000)
    auth_rate_limit_window_seconds: int = Field(default=60, ge=1, le=3600)

    # Delegated source integration fields (`settings.integrations`)
    github_enabled: bool = False
    github_auth_base_url: str = "https://github.com"
    github_api_base_url: str = "https://api.github.com"
    github_client_id: str | None = None
    github_client_secret: SecretStr | None = None
    github_redirect_uri: str = "http://localhost:8000/api/v1/integrations/github/callback"
    github_oauth_mode: Literal["github_app", "oauth_app"] = "github_app"
    github_oauth_scopes: str = "read:user user:email"
    github_allow_classic_private_repo_scope: bool = False

    jira_enabled: bool = False
    jira_auth_base_url: str = "https://auth.atlassian.com"
    jira_api_base_url: str = "https://api.atlassian.com"
    jira_client_id: str | None = None
    jira_client_secret: SecretStr | None = None
    jira_redirect_uri: str = "http://localhost:8000/api/v1/integrations/jira/callback"
    jira_oauth_scopes: str = "read:jira-work read:jira-user offline_access"

    # Optional Slack MVP remains gated & disabled until formal approval
    slack_enabled: bool = False

    oauth_state_expire_minutes: int = Field(default=10, ge=1, le=60)
    integration_http_timeout_seconds: float = Field(default=20.0, gt=0.5, le=120.0)
    integration_sync_max_items_per_run: int = Field(default=250, ge=1, le=5000)
    integration_allowed_post_auth_redirects: Annotated[list[str], NoDecode] = Field(
        default_factory=list
    )
    github_default_commits_limit: int = Field(default=50, ge=1, le=500)
    github_default_docs_limit: int = Field(default=20, ge=1, le=100)

    # Private encrypted document storage (`settings.storage`)
    storage_provider: StorageBackendProvider = "local_encrypted"
    supabase_url: str | None = None
    supabase_service_role_key: SecretStr | None = None
    supabase_secret_key: SecretStr | None = None
    supabase_storage_bucket: str = "project-evidence"
    supabase_storage_timeout_seconds: float = Field(default=30.0, gt=0.5, le=300.0)
    supabase_storage_max_retries: int = Field(default=2, ge=0, le=5)
    supabase_storage_retry_backoff_seconds: float = Field(default=0.5, ge=0.0, le=10.0)
    supabase_storage_verify_ciphertext_size: bool = True

    # Redis Caching Layer (`settings.redis`)
    redis_enabled: bool = True
    redis_url: SecretStr | None = None
    redis_host: str = "127.0.0.1"
    redis_port: int = Field(default=6379, ge=1, le=65535)
    redis_password: SecretStr | None = None
    redis_db: int = Field(default=0, ge=0, le=15)
    redis_max_connections: int = Field(default=20, ge=1, le=200)
    redis_socket_timeout: float = Field(default=2.0, ge=0.1, le=30.0)
    redis_connect_timeout: float = Field(default=2.0, ge=0.1, le=30.0)
    redis_cache_prefix: str = "ipkrh:cache:"
    redis_default_ttl: int = Field(default=300, ge=1, le=86400)
    redis_max_memory: str = "256mb"

    @field_validator("storage_provider", mode="before")
    @classmethod
    def _normalize_storage_provider(cls, value: Any) -> str:
        return str(value or "local_encrypted").strip().lower()

    @field_validator("cors_allowed_origins", mode="before")
    @classmethod
    def _parse_cors_origins(cls, value: Any) -> list[str]:
        raw_items: list[str]
        if isinstance(value, str):
            stripped = value.strip()
            if not stripped:
                return []
            if stripped.startswith("["):
                loaded = json.loads(stripped)
                if not isinstance(loaded, list):
                    raise ValueError("CORS_ALLOWED_ORIGINS JSON value must be an array.")
                raw_items = [str(item) for item in loaded]
            else:
                raw_items = stripped.split(",")
        elif isinstance(value, (list, tuple, set)):
            raw_items = [str(item) for item in value]
        else:
            raise ValueError("CORS_ALLOWED_ORIGINS must be a comma-separated string or list.")

        origins: list[str] = []
        for item in raw_items:
            origin = item.strip().rstrip("/")
            if not origin:
                continue
            if origin == "*":
                raise ValueError("Wildcard '*' is not allowed in CORS_ALLOWED_ORIGINS.")
            _require_http_url(origin, "CORS_ALLOWED_ORIGINS entry")
            origins.append(origin)
        return origins

    @field_validator("integration_allowed_post_auth_redirects", mode="before")
    @classmethod
    def _parse_post_auth_redirects(cls, value: Any) -> list[str]:
        if value is None:
            return []
        raw_items: list[str]
        if isinstance(value, str):
            stripped = value.strip()
            if not stripped:
                return []
            if stripped.startswith("["):
                loaded = json.loads(stripped)
                if not isinstance(loaded, list):
                    raise ValueError(
                        "INTEGRATION_ALLOWED_POST_AUTH_REDIRECTS JSON value must be an array."
                    )
                raw_items = [str(item) for item in loaded]
            else:
                raw_items = stripped.split(",")
        elif isinstance(value, (list, tuple, set)):
            raw_items = [str(item) for item in value]
        else:
            raise ValueError(
                "INTEGRATION_ALLOWED_POST_AUTH_REDIRECTS must be comma-separated or list."
            )

        cleaned: list[str] = []
        for item in raw_items:
            candidate = item.strip()
            if not candidate:
                continue
            cleaned.append(_require_http_url(candidate, "INTEGRATION_ALLOWED_POST_AUTH_REDIRECTS"))
        return cleaned

    @field_validator(
        "cookie_domain",
        "jwt_issuer",
        "jwt_audience",
        "github_client_id",
        "jira_client_id",
        "supabase_url",
        mode="before",
    )
    @classmethod
    def _normalize_optional_setting(cls, value: Any) -> str | None:
        if value is None:
            return None
        return _normalize_optional_str(str(value))

    @field_validator(
        "chroma_auth_token",
        "github_client_secret",
        "jira_client_secret",
        "supabase_service_role_key",
        "supabase_secret_key",
        mode="before",
    )
    @classmethod
    def _normalize_optional_secret(cls, value: Any) -> SecretStr | None:
        if value is None:
            return None
        if isinstance(value, SecretStr):
            cleaned = _normalize_optional_str(value.get_secret_value())
            return SecretStr(cleaned) if cleaned is not None else None
        cleaned = _normalize_optional_str(str(value))
        return SecretStr(cleaned) if cleaned is not None else None

    @model_validator(mode="after")
    def _validate_startup_invariants(self) -> Settings:
        # Force construction and validation of separated domain sub-settings at startup.
        _ = self.database
        _ = self.chroma
        _ = self.ollama
        _ = self.extraction
        _ = self.ingestion
        _ = self.chunking
        _ = self.embedding
        _ = self.retrieval
        _ = self.security
        _ = self.storage
        _ = self.integrations

        if self.app_env == "production":
            if not self.cors_allowed_origins:
                raise ValueError("CORS_ALLOWED_ORIGINS must define explicit origins in production.")
            if not self.cookie_secure:
                raise ValueError("COOKIE_SECURE must be true in production.")
            if self.postgres_ssl_mode == "disable":
                raise ValueError("POSTGRES_SSL_MODE must not be 'disable' in production.")
            parsed_db_query = parse_qs(urlparse(self.database.sqlalchemy_url()).query)
            if any(mode.lower() == "disable" for mode in parsed_db_query.get("sslmode", [])):
                raise ValueError("DATABASE_URL sslmode must not be 'disable' in production.")

            for env_name, secret in (
                ("POSTGRES_PASSWORD", self.postgres_password),
                ("JWT_SECRET_KEY", self.jwt_secret_key),
                ("TOKEN_ENCRYPTION_KEY", self.token_encryption_key),
                ("FILE_ENCRYPTION_KEY", self.file_encryption_key),
            ):
                raw = secret.get_secret_value().strip()
                if not raw or raw.startswith("change-me"):
                    raise ValueError(f"{env_name} must be replaced before running in production.")
                if env_name != "POSTGRES_PASSWORD" and len(raw) < 32:
                    raise ValueError(f"{env_name} must be at least 32 characters in production.")

        if self.cookie_samesite == "none" and not self.cookie_secure:
            raise ValueError("COOKIE_SAMESITE='none' requires COOKIE_SECURE=true.")

        return self

    @cached_property
    def database(self) -> DatabaseSettings:
        """Separated PostgreSQL configuration."""
        return DatabaseSettings(
            host=self.postgres_host.strip(),
            port=self.postgres_port,
            name=self.postgres_db.strip(),
            user=self.postgres_user.strip(),
            password=self.postgres_password,
            url=self.database_url,
            ssl_mode=self.postgres_ssl_mode,
            connect_timeout_seconds=self.postgres_connect_timeout_seconds,
        )

    @cached_property
    def chroma(self) -> ChromaSettings:
        """Separated ChromaDB HTTP service configuration."""
        return ChromaSettings(
            host=self.chroma_host.strip(),
            port=self.chroma_port,
            collection_prefix=self.chroma_collection_prefix.strip(),
            auth_token=self.chroma_auth_token,
            tenant=self.chroma_tenant.strip(),
            database=self.chroma_database.strip(),
            index_version=self.chroma_index_version.strip(),
            request_timeout_seconds=self.chroma_request_timeout_seconds,
        )

    @cached_property
    def chunking(self) -> ChunkingSettings:
        """Separated structure-aware evidence chunking configuration."""
        return ChunkingSettings(
            target_chars=self.chunk_target_chars,
            max_chars=self.chunk_max_chars,
            overlap_chars=self.chunk_overlap_chars,
            min_chars=self.chunk_min_chars,
        )

    @cached_property
    def embedding(self) -> EmbeddingSettings:
        """Separated Ollama embedding batch and dimensionality settings."""
        return EmbeddingSettings(
            batch_size=self.embedding_batch_size,
            expected_dimensions=self.embedding_expected_dimensions,
            timeout_seconds=self.embedding_timeout_seconds,
        )

    @cached_property
    def retrieval(self) -> RetrievalSettings:
        """Separated hybrid keyword + semantic retrieval and fusion tuning."""
        return RetrievalSettings(
            default_top_k=self.retrieval_default_top_k,
            max_top_k=self.retrieval_max_top_k,
            candidate_multiplier=self.retrieval_candidate_multiplier,
            min_candidate_limit=self.retrieval_min_candidate_limit,
            rrf_k=self.retrieval_rrf_k,
            semantic_weight=self.retrieval_semantic_weight,
            keyword_weight=self.retrieval_keyword_weight,
            min_semantic_similarity=self.retrieval_min_semantic_similarity,
            min_keyword_score=self.retrieval_min_keyword_score,
            min_hybrid_score=self.retrieval_min_hybrid_score,
        )

    @cached_property
    def ollama(self) -> OllamaSettings:
        """Separated local Ollama AI and OCR configuration."""
        return OllamaSettings(
            base_url=self.ollama_base_url,
            llm_model=self.ollama_llm_model.strip(),
            embedding_model=self.ollama_embedding_model.strip(),
            ocr_model=self.ollama_ocr_model.strip(),
            llm_num_ctx=self.ollama_llm_num_ctx,
            llm_num_predict=self.ollama_llm_num_predict,
            llm_temperature=self.ollama_llm_temperature,
            llm_timeout_seconds=self.ollama_llm_timeout_seconds,
            llm_think=self.ollama_llm_think,
            ocr_num_ctx=self.ollama_ocr_num_ctx,
            ocr_num_predict=self.ollama_ocr_num_predict,
            ocr_timeout_seconds=self.ollama_ocr_timeout_seconds,
        )

    @cached_property
    def extraction(self) -> ExtractionSettings:
        """Separated Phase 2.6 knowledge reconstruction & validation settings."""
        return ExtractionSettings(
            prompt_version=self.extraction_prompt_version.strip(),
            max_retries=self.extraction_max_retries,
            max_chunks_per_batch=self.extraction_max_chunks_per_batch,
            max_chars_per_batch=self.extraction_max_chars_per_batch,
            auto_reextract_on_update=self.extraction_auto_reextract_on_update,
        )

    @cached_property
    def ingestion(self) -> IngestionSettings:
        """Separated document validation, OCR triage bounds, and worker configuration."""
        return IngestionSettings(
            max_upload_size_mb=self.max_upload_size_mb,
            max_document_pages=self.max_document_pages,
            ocr_render_dpi=self.ocr_render_dpi,
            ocr_max_image_dimension=self.ocr_max_image_dimension,
            ocr_min_text_chars_per_page=self.ocr_min_text_chars_per_page,
            ocr_max_pages_per_document=self.ocr_max_pages_per_document,
            worker_poll_interval_seconds=self.worker_poll_interval_seconds,
            worker_max_attempts=self.worker_max_attempts,
            worker_retry_base_seconds=self.worker_retry_base_seconds,
            worker_lease_seconds=self.worker_lease_seconds,
        )

    @cached_property
    def security(self) -> SecuritySettings:
        """Separated authentication, encryption, cookie, and private storage settings."""
        return SecuritySettings(
            jwt_secret_key=self.jwt_secret_key,
            jwt_algorithm=self.jwt_algorithm,
            jwt_issuer=self.jwt_issuer,
            jwt_audience=self.jwt_audience,
            jwt_access_token_expire_minutes=self.jwt_access_token_expire_minutes,
            jwt_refresh_token_expire_days=self.jwt_refresh_token_expire_days,
            token_encryption_key=self.token_encryption_key,
            file_encryption_key=self.file_encryption_key,
            upload_storage_path=self.upload_storage_path,
            cookie_secure=self.cookie_secure,
            cookie_samesite=self.cookie_samesite,
            cookie_domain=self.cookie_domain,
            refresh_cookie_name=self.refresh_cookie_name.strip(),
            refresh_cookie_path=self.refresh_cookie_path.strip(),
            auth_rate_limit_enabled=self.auth_rate_limit_enabled,
            auth_rate_limit_max_attempts=self.auth_rate_limit_max_attempts,
            auth_rate_limit_window_seconds=self.auth_rate_limit_window_seconds,
        )

    @cached_property
    def integrations(self) -> IntegrationsSettings:
        """Separated source integration settings for GitHub and Jira."""
        return IntegrationsSettings(
            github=GitHubIntegrationSettings(
                enabled=self.github_enabled,
                auth_base_url=self.github_auth_base_url,
                api_base_url=self.github_api_base_url,
                client_id=self.github_client_id,
                client_secret=self.github_client_secret,
                redirect_uri=self.github_redirect_uri,
                oauth_mode=self.github_oauth_mode,
                oauth_scopes=self.github_oauth_scopes.strip(),
                allow_classic_private_repo_scope=self.github_allow_classic_private_repo_scope,
            ),
            jira=JiraIntegrationSettings(
                enabled=self.jira_enabled,
                auth_base_url=self.jira_auth_base_url,
                api_base_url=self.jira_api_base_url,
                client_id=self.jira_client_id,
                client_secret=self.jira_client_secret,
                redirect_uri=self.jira_redirect_uri,
                oauth_scopes=self.jira_oauth_scopes.strip(),
            ),
            slack_enabled=self.slack_enabled,
            oauth_state_expire_minutes=self.oauth_state_expire_minutes,
            http_timeout_seconds=self.integration_http_timeout_seconds,
            sync_max_items_per_run=self.integration_sync_max_items_per_run,
            allowed_post_auth_redirects=tuple(self.integration_allowed_post_auth_redirects),
            default_github_commits_limit=self.github_default_commits_limit,
            default_github_docs_limit=self.github_default_docs_limit,
        )

    @cached_property
    def storage(self) -> StorageSettings:
        """Separated private encrypted storage provider configuration."""
        resolved_service_key = self.supabase_service_role_key or self.supabase_secret_key
        return StorageSettings(
            provider=self.storage_provider,
            upload_storage_path=self.upload_storage_path,
            supabase_url=self.supabase_url,
            supabase_service_role_key=resolved_service_key,
            supabase_storage_bucket=self.supabase_storage_bucket,
            supabase_storage_timeout_seconds=self.supabase_storage_timeout_seconds,
            supabase_storage_max_retries=self.supabase_storage_max_retries,
            supabase_storage_retry_backoff_seconds=self.supabase_storage_retry_backoff_seconds,
            supabase_storage_verify_ciphertext_size=self.supabase_storage_verify_ciphertext_size,
        )

    @cached_property
    def redis(self) -> RedisSettings:
        """Centralized Redis connection and caching configuration."""
        return RedisSettings(
            enabled=self.redis_enabled,
            url=self.redis_url,
            host=self.redis_host.strip(),
            port=self.redis_port,
            password=self.redis_password,
            db=self.redis_db,
            max_connections=self.redis_max_connections,
            socket_timeout=self.redis_socket_timeout,
            connect_timeout=self.redis_connect_timeout,
            cache_prefix=self.redis_cache_prefix.strip(),
            default_ttl=self.redis_default_ttl,
            max_memory=self.redis_max_memory.strip(),
        )

    @property
    def is_production(self) -> bool:
        """Return True when running in production environment mode."""
        return self.app_env == "production"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return cached validated Settings instance."""
    return Settings()


def clear_settings_cache() -> None:
    """Reset cached settings (primarily for isolated test configuration)."""
    get_settings.cache_clear()
