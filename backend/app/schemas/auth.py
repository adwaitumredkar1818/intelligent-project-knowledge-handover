"""Pydantic request and response schemas for platform authentication and sessions."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Literal

from pydantic import Field, field_validator, model_validator

from app.core.validators import validate_password_strength
from app.schemas.common import BaseSchema
from app.schemas.user import AuthenticatedUserResponse, NormalisedEmail, UserSummaryResponse


class RegisterRequest(BaseSchema):
    """Platform registration payload (email normalised; password strength enforced)."""

    full_name: str = Field(min_length=2, max_length=255)
    email: NormalisedEmail
    password: str

    @field_validator("full_name")
    @classmethod
    def _normalize_full_name(cls, value: str) -> str:
        cleaned = " ".join(value.split())
        if len(cleaned) < 2:
            raise ValueError("Full name must contain at least 2 non-whitespace characters.")
        return cleaned

    @model_validator(mode="after")
    def _validate_password(self) -> RegisterRequest:
        validate_password_strength(self.password, email=self.email)
        return self


class RegisterResponse(BaseSchema):
    """Registration result clearly stating email verification delivery status."""

    user: UserSummaryResponse
    email_verification_required: bool = True
    email_verification_delivery: Literal["not_configured"] = "not_configured"
    message: str


class LoginRequest(BaseSchema):
    """Platform email/password login credentials."""

    email: NormalisedEmail
    password: str = Field(min_length=1, max_length=128)


class AccessTokenResponse(BaseSchema):
    """Short-lived access token response; refresh token travels solely via HttpOnly cookie."""

    access_token: str
    token_type: Literal["bearer"] = "bearer"  # noqa: S105
    expires_in: int
    user: AuthenticatedUserResponse


class LogoutResponse(BaseSchema):
    """Logout result after revoking the active refresh session and clearing cookie."""

    message: str
    revoked: bool


class RefreshSessionSummary(BaseSchema):
    """Safe metadata projection of a user's refresh session (never exposes hashes/tokens)."""

    id: uuid.UUID
    token_family_id: uuid.UUID
    created_at: datetime
    expires_at: datetime
    last_used_at: datetime | None
    revoked_at: datetime | None
    revoked_reason: str | None
    is_current_family: bool
    session_metadata: dict[str, str] | None


class SessionListResponse(BaseSchema):
    """List of refresh sessions belonging strictly to the authenticated user."""

    items: list[RefreshSessionSummary]


class RevokeSessionResponse(BaseSchema):
    """Confirmation of revoking a specific session."""

    session_id: uuid.UUID
    revoked: bool
    message: str
