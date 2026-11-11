"""Centralised Pydantic Settings configuration loaded from root `.env`."""

from __future__ import annotations

import json
from functools import cached_property, lru_cache
from pathlib import Path
from typing import Annotated, Any, Literal
from urllib.parse import urlparse

from pydantic import BaseModel, ConfigDict, Field, SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict

AppEnv = Literal["development", "test", "production"]
LogLevel = Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
PostgresSslMode = Literal["disable", "allow", "prefer", "require", "verify-ca", "verify-full"]
CookieSameSite = Literal["lax", "strict", "none"]
AllowedJwtAlgorithm = Literal["HS256", "HS384", "HS512"]

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
    connect_timeout_seconds: int = Field(default=5, ge=1, le=60)

    @model_validator(mode="after")
    def _validate_database(self) -> DatabaseSettings:
        if not self.password.get_secret_value().strip():
            raise ValueError("POSTGRES_PASSWORD must not be empty.")
        raw_url = self.url.get_secret_value().strip()
        parsed = urlparse(raw_url)
        if parsed.scheme != "postgresql+psycopg":
            raise ValueError("DATABASE_URL must use the 'postgresql+psycopg' SQLAlchemy driver.")
        if not parsed.hostname or not parsed.path.lstrip("/"):
            raise ValueError("DATABASE_URL must include a valid host and database name.")
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
    health_timeout_seconds: float = Field(default=2.0, gt=0.1, le=30.0)

    @property
    def base_url(self) -> str:
        """Return HTTP base URL for the dedicated ChromaDB server."""
        return f"http://{self.host}:{self.port}"


class OllamaSettings(BaseModel):
    """Local Ollama runtime configuration (LLM, embeddings, and OCR)."""

    model_config = ConfigDict(frozen=True)

    base_url: str
    llm_model: str = Field(min_length=1)
    embedding_model: str = Field(min_length=1)
    ocr_model: str = Field(min_length=1)
    health_timeout_seconds: float = Field(default=2.0, gt=0.1, le=30.0)

    @field_validator("base_url")
    @classmethod
    def _validate_base_url(cls, value: str) -> str:
        return _require_http_url(value, "OLLAMA_BASE_URL")


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

    # ChromaDB configuration fields (grouped into `settings.chroma`)
    chroma_host: str = Field(default="localhost", min_length=1)
    chroma_port: int = Field(default=8001, ge=1, le=65535)
    chroma_collection_prefix: str = Field(default="ipkrh", min_length=1)
    chroma_auth_token: SecretStr | None = None

    # Ollama configuration fields (grouped into `settings.ollama`)
    ollama_base_url: str = "http://localhost:11434"
    ollama_llm_model: str = Field(default="qwen3:8b", min_length=1)
    ollama_embedding_model: str = Field(default="nomic-embed-text", min_length=1)
    ollama_ocr_model: str = Field(default="glm-ocr:latest", min_length=1)

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

    @field_validator("cookie_domain", "jwt_issuer", "jwt_audience", mode="before")
    @classmethod
    def _normalize_optional_setting(cls, value: Any) -> str | None:
        if value is None:
            return None
        return _normalize_optional_str(str(value))

    @field_validator("chroma_auth_token", mode="before")
    @classmethod
    def _normalize_chroma_token(cls, value: Any) -> SecretStr | None:
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
        _ = self.security

        if self.app_env == "production":
            if not self.cors_allowed_origins:
                raise ValueError("CORS_ALLOWED_ORIGINS must define explicit origins in production.")
            if not self.cookie_secure:
                raise ValueError("COOKIE_SECURE must be true in production.")
            if self.postgres_ssl_mode == "disable":
                raise ValueError("POSTGRES_SSL_MODE must not be 'disable' in production.")

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
        )

    @cached_property
    def chroma(self) -> ChromaSettings:
        """Separated ChromaDB HTTP service configuration."""
        return ChromaSettings(
            host=self.chroma_host.strip(),
            port=self.chroma_port,
            collection_prefix=self.chroma_collection_prefix.strip(),
            auth_token=self.chroma_auth_token,
        )

    @cached_property
    def ollama(self) -> OllamaSettings:
        """Separated local Ollama AI and OCR configuration."""
        return OllamaSettings(
            base_url=self.ollama_base_url,
            llm_model=self.ollama_llm_model.strip(),
            embedding_model=self.ollama_embedding_model.strip(),
            ocr_model=self.ollama_ocr_model.strip(),
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
