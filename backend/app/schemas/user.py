"""Pydantic request and response schemas for platform users and RBAC."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Annotated, Literal

from pydantic import AfterValidator, Field, field_validator

from app.core.validators import normalize_and_validate_email
from app.schemas.common import BaseSchema

NormalisedEmail = Annotated[str, AfterValidator(normalize_and_validate_email)]


class UserSummaryResponse(BaseSchema):
    """Public/authenticated safe projection of a platform user (never exposes secrets)."""

    id: uuid.UUID
    full_name: str
    email: str
    status: str
    is_email_verified: bool
    email_verified_at: datetime | None
    roles: list[str]
    created_at: datetime
    updated_at: datetime
    last_login_at: datetime | None


class AuthenticatedUserResponse(UserSummaryResponse):
    """Authenticated user projection including resolved platform permissions."""

    permissions: list[str]


class UserListResponse(BaseSchema):
    """Paginated list of platform user accounts."""

    items: list[UserSummaryResponse]
    total: int


class UpdateUserStatusRequest(BaseSchema):
    """Request payload for administrative user account lifecycle updates."""

    status: Literal["active", "disabled", "locked"]


class RoleResponse(BaseSchema):
    """RBAC role metadata including its explicit scope boundary and permission codes."""

    id: uuid.UUID
    name: str
    display_name: str
    description: str | None
    scope_type: str
    is_system: bool
    permissions: list[str]


class RoleListResponse(BaseSchema):
    """Catalog of defined RBAC roles."""

    items: list[RoleResponse]


class AssignRoleRequest(BaseSchema):
    """Request to assign a platform-scoped role to a user account."""

    role_name: str = Field(min_length=1, max_length=64)

    @field_validator("role_name")
    @classmethod
    def _clean_role_name(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("Role name must not be empty.")
        return cleaned


class AssignRoleResponse(BaseSchema):
    """Confirmation of a platform-level role assignment."""

    user_id: uuid.UUID
    role_name: str
    scope_type: str
    assigned_at: datetime
