"""Tests for FastAPI startup, lifespan resource disposal, CORS, and production docs hiding."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from app import main as app_main
from tests.conftest import build_test_settings


def test_lifespan_initializes_and_disposes_resources(monkeypatch: pytest.MonkeyPatch) -> None:
    fake_engine = MagicMock()
    fake_factory = MagicMock()
    monkeypatch.setattr(app_main, "create_db_engine", lambda settings: fake_engine)
    monkeypatch.setattr(app_main, "create_session_factory", lambda engine: fake_factory)
    monkeypatch.setattr(app_main, "verify_database_connection", lambda engine: 1.23)

    app = app_main.create_app(build_test_settings())
    with TestClient(app) as client:
        response = client.get("/health")
        assert response.status_code == 200
        assert not app.state.http_client.is_closed
        assert response.headers["X-Content-Type-Options"] == "nosniff"
        assert response.headers["X-Frame-Options"] == "DENY"
        assert "X-Request-ID" in response.headers

    fake_engine.dispose.assert_called_once()
    assert app.state.http_client.is_closed


def test_production_mode_disables_openapi_and_enforces_cors(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake_engine = MagicMock()
    monkeypatch.setattr(app_main, "create_db_engine", lambda settings: fake_engine)
    monkeypatch.setattr(app_main, "create_session_factory", lambda engine: MagicMock())
    monkeypatch.setattr(app_main, "verify_database_connection", lambda engine: 1.0)

    prod_settings = build_test_settings(
        app_env="production",
        cookie_secure=True,
        postgres_ssl_mode="require",
        cors_allowed_origins="https://frontend.example.com",
    )
    app = app_main.create_app(prod_settings)

    with TestClient(app) as client:
        assert client.get("/docs").status_code == 404
        assert client.get("/openapi.json").status_code == 404

        allowed = client.get("/health", headers={"Origin": "https://frontend.example.com"})
        assert allowed.headers.get("access-control-allow-origin") == "https://frontend.example.com"

        disallowed = client.get("/health", headers={"Origin": "https://evil.example.org"})
        assert "access-control-allow-origin" not in disallowed.headers
