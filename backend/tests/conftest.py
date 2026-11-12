"""Shared isolated test configuration and helpers (never modifies dev DB data)."""

from __future__ import annotations

import uuid
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Any

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
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


DEFAULT_TEST_PASSWORD = "Handover!Workspace2026#Secure"


@dataclass(frozen=True, slots=True)
class RegisteredUserSession:
    """Registered and logged-in user credentials for isolated API tests."""

    user_id: uuid.UUID
    email: str
    full_name: str
    access_token: str

    @property
    def headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self.access_token}"}


def register_and_login_user(
    client: TestClient,
    *,
    email: str,
    full_name: str,
    password: str = DEFAULT_TEST_PASSWORD,
) -> RegisteredUserSession:
    """Register a platform account and return its active Bearer session."""
    reg = client.post(
        "/api/v1/auth/register",
        json={"full_name": full_name, "email": email, "password": password},
    )
    if reg.status_code != 201:
        raise AssertionError(f"Failed test user registration ({reg.status_code}): {reg.text}")
    reg_user = reg.json()["user"]

    login = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": password},
    )
    if login.status_code != 200:
        raise AssertionError(f"Failed test user login ({login.status_code}): {login.text}")
    login_data = login.json()

    return RegisteredUserSession(
        user_id=uuid.UUID(reg_user["id"]),
        email=reg_user["email"],
        full_name=reg_user["full_name"],
        access_token=login_data["access_token"],
    )


def invite_and_accept_member(
    client: TestClient,
    *,
    organisation_id: str,
    inviter_headers: dict[str, str],
    invitee: RegisteredUserSession,
    role_name: str = "org_member",
) -> None:
    """Invite an existing user into an organisation and accept via development token."""
    invite_resp = client.post(
        f"/api/v1/organisations/{organisation_id}/invitations",
        headers=inviter_headers,
        json={"email": invitee.email, "role_name": role_name},
    )
    if invite_resp.status_code != 201:
        raise AssertionError(
            f"Failed invitation creation ({invite_resp.status_code}): {invite_resp.text}"
        )
    token = invite_resp.json()["development_invitation_token"]
    if not isinstance(token, str) or not token:
        raise AssertionError("Expected development_invitation_token in test environment.")
    accept_resp = client.post(
        f"/api/v1/invitations/{token}/accept",
        headers=invitee.headers,
    )
    if accept_resp.status_code != 200:
        raise AssertionError(
            f"Failed invitation acceptance ({accept_resp.status_code}): {accept_resp.text}"
        )
