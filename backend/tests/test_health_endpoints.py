"""Tests for liveness and dependency-aware readiness endpoints."""

from __future__ import annotations

from collections.abc import Iterator
from unittest.mock import MagicMock

import httpx
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.exc import OperationalError

from app import main as app_main
from app.api.deps import get_db_session
from tests.conftest import build_test_settings


def _build_client_with_mocked_infra(
    monkeypatch: pytest.MonkeyPatch,
    *,
    db_healthy: bool,
    ollama_status: int | Exception,
    chroma_status: int | Exception,
    chroma_auth_token: str | None = None,
) -> tuple[TestClient, list[str], MagicMock]:
    fake_engine = MagicMock()
    seen_headers: list[str] = []

    class FakeSession:
        def __init__(self) -> None:
            self.closed = False

        def execute(self, stmt: object) -> object:
            if not db_healthy:
                raise OperationalError("SELECT 1", {}, Exception("db down postgresql://u:pw@host/db"))
            return MagicMock()

        def rollback(self) -> None:
            pass

        def close(self) -> None:
            self.closed = True

    def fake_handler(request: httpx.Request) -> httpx.Response:
        if "Authorization" in request.headers:
            seen_headers.append(request.headers["Authorization"])
        if str(request.url).endswith("/api/version"):
            if isinstance(ollama_status, Exception):
                raise ollama_status
            return httpx.Response(status_code=ollama_status, json={"version": "0.40.16"})
        if str(request.url).endswith("/api/v2/heartbeat"):
            if isinstance(chroma_status, Exception):
                raise chroma_status
            return httpx.Response(status_code=chroma_status, json={"nanosecond heartbeat": 1})
        return httpx.Response(status_code=404)

    monkeypatch.setattr(app_main, "create_db_engine", lambda settings: fake_engine)
    monkeypatch.setattr(app_main, "create_session_factory", lambda engine: MagicMock())
    monkeypatch.setattr(app_main, "verify_database_connection", lambda engine: 1.0)

    settings = build_test_settings(chroma_auth_token=chroma_auth_token)
    app = app_main.create_app(settings)

    def override_db() -> Iterator[FakeSession]:
        session = FakeSession()
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_db_session] = override_db
    client = TestClient(app)
    client.__enter__()
    # Replace lifespan http_client cleanly with deterministic MockTransport
    app.state.http_client = httpx.AsyncClient(transport=httpx.MockTransport(fake_handler))
    return client, seen_headers, fake_engine


def test_liveness_endpoints_do_not_require_db_or_external_services(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake_engine = MagicMock()
    monkeypatch.setattr(app_main, "create_db_engine", lambda settings: fake_engine)
    monkeypatch.setattr(app_main, "create_session_factory", lambda engine: MagicMock())
    monkeypatch.setattr(app_main, "verify_database_connection", lambda engine: 1.0)

    app = app_main.create_app(build_test_settings())

    def failing_db_override() -> Iterator[object]:
        raise AssertionError("Liveness endpoints must not acquire DB sessions")

    app.dependency_overrides[get_db_session] = failing_db_override

    with TestClient(app) as client:
        root_resp = client.get("/health", headers={"X-Request-ID": "trace-root-123"})
        assert root_resp.status_code == 200
        assert root_resp.headers["X-Request-ID"] == "trace-root-123"
        assert root_resp.json() == {
            "status": "ok",
            "service": "IPKRH Test Backend",
            "environment": "test",
            "api_version": "v1",
            "request_id": "trace-root-123",
        }

        v1_resp = client.get("/api/v1/health")
        assert v1_resp.status_code == 200
        body = v1_resp.json()
        assert body["status"] == "ok"
        assert body["api_version"] == "v1"
        assert body["request_id"] == v1_resp.headers["X-Request-ID"]


def test_readiness_all_healthy(monkeypatch: pytest.MonkeyPatch) -> None:
    client, seen_headers, _ = _build_client_with_mocked_infra(
        monkeypatch,
        db_healthy=True,
        ollama_status=200,
        chroma_status=200,
        chroma_auth_token="secret-chroma-token",
    )
    try:
        resp = client.get("/health/ready")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ready"
        assert data["application"] == {"status": "ok"}
        assert data["database"]["status"] == "ok"
        assert data["database"]["required"] is True
        assert data["external_services"]["ollama"]["status"] == "ok"
        assert data["external_services"]["ollama"]["required"] is False
        assert data["external_services"]["chromadb"]["status"] == "ok"
        assert seen_headers == ["Bearer secret-chroma-token"]
        assert "secret-chroma-token" not in resp.text
    finally:
        client.__exit__(None, None, None)


def test_readiness_optional_ai_unavailable_stays_degraded_200(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client, _, _ = _build_client_with_mocked_infra(
        monkeypatch,
        db_healthy=True,
        ollama_status=httpx.ConnectError("connection refused"),
        chroma_status=503,
    )
    try:
        resp = client.get("/health/ready")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "degraded"
        assert data["application"] == {"status": "ok"}
        assert data["database"]["status"] == "ok"
        assert data["external_services"]["ollama"]["status"] == "unavailable"
        assert data["external_services"]["chromadb"]["status"] == "unavailable"
        assert "11434" not in resp.text
        assert "8001" not in resp.text
    finally:
        client.__exit__(None, None, None)


def test_readiness_database_unavailable_returns_503_without_leaking_url(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client, _, _ = _build_client_with_mocked_infra(
        monkeypatch,
        db_healthy=False,
        ollama_status=200,
        chroma_status=200,
    )
    try:
        resp = client.get("/health/ready")
        assert resp.status_code == 503
        data = resp.json()
        assert data["status"] == "unavailable"
        assert data["application"] == {"status": "ok"}
        assert data["database"]["status"] == "unavailable"
        assert data["external_services"]["ollama"]["status"] == "ok"
        assert "postgresql" not in resp.text.lower()
        assert "test_user" not in resp.text
    finally:
        client.__exit__(None, None, None)
