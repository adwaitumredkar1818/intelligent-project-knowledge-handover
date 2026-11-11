"""Shared isolated test configuration and helpers (never modifies dev DB data)."""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Any

import pytest
from fastapi import FastAPI
from sqlalchemy import Engine, create_engine, event
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app import main as app_main
from app.core.config import Settings
from app.models import Base
from app.repositories.rbac import RbacRepository


def build_test_settings(**overrides: Any) -> Settings:
    """Create isolated Settings without reading host root `.env`."""
    defaults: dict[str, Any] = {
        "app_name": "IPKRH Test Backend",
        "app_env": "test",
        "log_level": "WARNING",
        "backend_host": "127.0.0.1",
        "backend_port": 8000,
        "cors_allowed_origins": ["http://localhost:3000"],
        "postgres_host": "127.0.0.1",
        "postgres_port": 5432,
        "postgres_db": "test_db",
        "postgres_user": "test_user",
        "postgres_password": "test-only-password-placeholder",
        "database_url": "postgresql+psycopg://test_user:test-only-password-placeholder@127.0.0.1:5432/test_db",
        "postgres_ssl_mode": "prefer",
        "chroma_host": "127.0.0.1",
        "chroma_port": 8001,
        "chroma_collection_prefix": "ipkrh_test",
        "chroma_auth_token": None,
        "ollama_base_url": "http://127.0.0.1:11434",
        "ollama_llm_model": "qwen3:8b",
        "ollama_embedding_model": "nomic-embed-text",
        "ollama_ocr_model": "glm-ocr:latest",
        "jwt_secret_key": "test-only-jwt-secret-key-at-least-32-chars",
        "jwt_algorithm": "HS256",
        "jwt_access_token_expire_minutes": 15,
        "jwt_refresh_token_expire_days": 7,
        "token_encryption_key": "test-only-token-key-at-least-32-chars",
        "file_encryption_key": "test-only-file-key-at-least-32-chars!",
        "cookie_secure": False,
        "cookie_samesite": "lax",
        "cookie_domain": None,
    }
    defaults.update(overrides)
    return Settings(_env_file=None, **defaults)


@dataclass(slots=True)
class IsolatedAppContext:
    """Self-contained FastAPI app + isolated SQLite DB context (never touches dev DB)."""

    app: FastAPI
    engine: Engine
    session_factory: sessionmaker[Session]
    settings: Settings


def create_isolated_auth_context(
    monkeypatch: pytest.MonkeyPatch,
    **settings_overrides: Any,
) -> IsolatedAppContext:
    """Build a FastAPI app wired to a fresh in-memory DB with seeded RBAC catalog."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    @event.listens_for(engine, "connect")
    def _enable_sqlite_fks(dbapi_conn: Any, _: Any) -> None:
        cursor = dbapi_conn.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    Base.metadata.create_all(engine)
    session_factory: sessionmaker[Session] = sessionmaker(
        bind=engine,
        autocommit=False,
        autoflush=False,
        expire_on_commit=False,
        class_=Session,
    )
    with session_factory() as session:
        RbacRepository(session).ensure_catalog_seeded()
        session.commit()

    settings = build_test_settings(**settings_overrides)
    monkeypatch.setattr(app_main, "create_db_engine", lambda _settings: engine)
    monkeypatch.setattr(app_main, "create_session_factory", lambda _engine: session_factory)
    monkeypatch.setattr(app_main, "verify_database_connection", lambda _engine: 1.0)

    app = app_main.create_app(settings)
    return IsolatedAppContext(
        app=app,
        engine=engine,
        session_factory=session_factory,
        settings=settings,
    )


@contextmanager
def isolated_auth_app(
    monkeypatch: pytest.MonkeyPatch,
    **settings_overrides: Any,
) -> Iterator[IsolatedAppContext]:
    """Context manager guaranteeing clean disposal of isolated test engine."""
    ctx = create_isolated_auth_context(monkeypatch, **settings_overrides)
    try:
        yield ctx
    finally:
        ctx.engine.dispose()
