"""Tests for centralised logging, secret redaction, correlation IDs, and error handling."""

from __future__ import annotations

import logging
from unittest.mock import MagicMock

import pytest
from fastapi import APIRouter
from fastapi.testclient import TestClient
from pydantic import BaseModel

from app import main as app_main
from app.core.exceptions import NotFoundError
from app.core.logging import StructuredJsonFormatter, redact_sensitive_text
from tests.conftest import build_test_settings


def test_redact_sensitive_text_masks_credentials() -> None:
    sample = (
        "connecting to postgresql+psycopg://postgres:MySuperSecretPass@localhost:5432/db "
        "with Authorization: Bearer eyJhbGciOi.payload.sig and password=topsecret token=tok123"
    )
    redacted = redact_sensitive_text(sample)
    assert "MySuperSecretPass" not in redacted
    assert "eyJhbGciOi" not in redacted
    assert "topsecret" not in redacted
    assert "tok123" not in redacted
    assert "[REDACTED]" in redacted


def test_structured_formatter_includes_request_id_and_redacts() -> None:
    formatter = StructuredJsonFormatter()
    record = logging.LogRecord(
        name="app.test",
        level=logging.INFO,
        pathname=__file__,
        lineno=1,
        msg="failed with token=abc999",
        args=(),
        exc_info=None,
    )
    record.correlation_id = "corr-123"
    rendered = formatter.format(record)
    assert '"request_id": "corr-123"' in rendered
    assert "abc999" not in rendered
    assert "[REDACTED]" in rendered


def test_error_handlers_separate_expected_validation_and_unexpected_errors(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(app_main, "create_db_engine", lambda settings: MagicMock())
    monkeypatch.setattr(app_main, "create_session_factory", lambda engine: MagicMock())
    monkeypatch.setattr(app_main, "verify_database_connection", lambda engine: 1.0)

    app = app_main.create_app(build_test_settings())

    class SecretEchoPayload(BaseModel):
        count: int
        secret_note: str

    test_router = APIRouter()

    @test_router.get("/__test/not-found")
    def raise_expected() -> None:
        raise NotFoundError("Sample item missing.", code="SAMPLE_NOT_FOUND")

    @test_router.post("/__test/validate")
    def validate_payload(payload: SecretEchoPayload) -> dict[str, int]:
        return {"count": payload.count}

    @test_router.get("/__test/crash")
    def raise_unexpected() -> None:
        raise RuntimeError("postgresql+psycopg://user:leaked-pw@db:5432/prod internal crash")

    app.include_router(test_router)

    # Disable pytest re-raising server exceptions so Starlette's 500 handler runs.
    with TestClient(app, raise_server_exceptions=False) as client:
        # 1. Expected AppError preserves code, message, and correlation ID
        r_expected = client.get("/__test/not-found", headers={"X-Request-ID": "req-exp-1"})
        assert r_expected.status_code == 404
        assert r_expected.headers["X-Request-ID"] == "req-exp-1"
        assert r_expected.json()["error"] == {
            "code": "SAMPLE_NOT_FOUND",
            "message": "Sample item missing.",
            "request_id": "req-exp-1",
            "details": None,
        }

        # 2. Framework 404 follows exact same envelope and rejects unsafe CRLF request IDs
        r_404 = client.get("/__test/missing", headers={"X-Request-ID": "bad\r\nid"})
        assert r_404.status_code == 404
        req_id = r_404.headers["X-Request-ID"]
        assert req_id != "bad\r\nid"
        assert r_404.json()["error"]["code"] == "HTTP_404"
        assert r_404.json()["error"]["request_id"] == req_id

        # 3. 422 validation error sanitises inputs so invalid payload secrets are not echoed
        r_422 = client.post(
            "/__test/validate",
            json={"count": "not-an-int", "secret_note": "do-not-echo-this-secret"},
        )
        assert r_422.status_code == 422
        assert r_422.json()["error"]["code"] == "VALIDATION_ERROR"
        assert "do-not-echo-this-secret" not in r_422.text
        assert "not-an-int" not in r_422.text

        # 4. Unexpected 500 hides stack trace, DB URL, and internal exception message
        r_500 = client.get("/__test/crash", headers={"X-Request-ID": "req-500-1"})
        assert r_500.status_code == 500
        assert r_500.headers["X-Request-ID"] == "req-500-1"
        assert r_500.json()["error"] == {
            "code": "INTERNAL_SERVER_ERROR",
            "message": "An unexpected internal server error occurred.",
            "request_id": "req-500-1",
            "details": None,
        }
        assert "leaked-pw" not in r_500.text
        assert "RuntimeError" not in r_500.text
