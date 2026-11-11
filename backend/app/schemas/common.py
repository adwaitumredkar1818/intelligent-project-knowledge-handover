"""Shared Pydantic response and structured error schemas."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict


class BaseSchema(BaseModel):
    """Shared Pydantic base schema with strict attribute defaults."""

    model_config = ConfigDict(from_attributes=True)


class ErrorDetail(BaseSchema):
    """Canonical sanitised error payload returned by all API error handlers."""

    code: str
    message: str
    request_id: str
    details: list[dict[str, Any]] | dict[str, Any] | None = None


class ErrorResponse(BaseSchema):
    """Top-level error response envelope."""

    error: ErrorDetail
