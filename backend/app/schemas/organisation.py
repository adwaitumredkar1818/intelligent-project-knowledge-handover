"""Pydantic v2 schemas for organisations, memberships, invitations, and audit logs."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Literal

from pydantic import Field, field_validator, model_validator

from app.core.validators import normalize_and_validate_slug, normalize_display_name
from app.schemas.common import BaseSchema
from app.schemas.user import NormalisedEmail


def _clean_optional_description(value: str | None) -> str | None:
    if value is None:
        return None
    cleaned = value.strip()
    return cleaned or None


def _clean_role_name(value: str) -> str:
    cleaned = value.strip()
    if not cleaned:
        raise ValueError("Role name must not be empty.")
    return cleaned


class CreateOrganisationRequest(BaseSchema):
    """Request payload to create a new multi-tenant organisation."""

    name: str = Field(min_length=2, max_length=200)
    slug: str | None = Field(default=None, min_length=2, max_length=120)
    description: str | None = Field(default=None, max_length=2000)

    @field_validator("name")
    @classmethod
    def _validate_name(cls, value: str) -> str:
        return normalize_display_name(
            value, field_label="Organisation name", min_len=2, max_len=200
        )

    @field_validator("slug")
    @classmethod
    def _validate_slug(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return normalize_and_validate_slug(value, field_label="Organisation slug")

    @field_validator("description")
    @classmethod
    def _validate_description(cls, value: str | None) -> str | None:
        return _clean_optional_description(value)


class UpdateOrganisationRequest(BaseSchema):
    """Partial update payload for organisation metadata."""

    name: str | None = Field(default=None, min_length=2, max_length=200)
    slug: str | None = Field(default=None, min_length=2, max_length=120)
    description: str | None = Field(default=None, max_length=2000)

    @field_validator("name")
    @classmethod
    def _validate_name(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return normalize_display_name(
            value, field_label="Organisation name", min_len=2, max_len=200
        )

    @field_validator("slug")
    @classmethod
    def _validate_slug(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return normalize_and_validate_slug(value, field_label="Organisation slug")

    @field_validator("description")
    @classmethod
    def _validate_description(cls, value: str | None) -> str | None:
        return _clean_optional_description(value)

    @model_validator(mode="after")
    def _require_non_empty_update(self) -> UpdateOrganisationRequest:
        if not self.model_fields_set:
            raise ValueError("Provide at least one organisation field to update.")
        if "name" in self.model_fields_set and self.name is None:
            raise ValueError("Organisation name cannot be null.")
        if "slug" in self.model_fields_set and self.slug is None:
            raise ValueError("Organisation slug cannot be null.")
        return self


class OrganisationSummaryResponse(BaseSchema):
    """Safe projection of an organisation visible to a member."""

    id: uuid.UUID
    name: str
    slug: str
    description: str | None
    status: str
    created_by_id: uuid.UUID
    my_role: str
    created_at: datetime
    updated_at: datetime
    archived_at: datetime | None


class OrganisationResponse(OrganisationSummaryResponse):
    """Detailed organisation view including resolved effective organisation permissions."""

    my_permissions: list[str]


class OrganisationListResponse(BaseSchema):
    """Paginated list of organisations accessible to the authenticated user."""

    items: list[OrganisationSummaryResponse]
    total: int


class OrganisationMemberResponse(BaseSchema):
    """Safe projection of a user's membership and role within an organisation."""

    id: uuid.UUID
    organisation_id: uuid.UUID
    user_id: uuid.UUID
    full_name: str
    email: str
    role_name: str
    status: str
    joined_at: datetime
    invited_by_id: uuid.UUID | None
    created_at: datetime
    updated_at: datetime


class OrganisationMemberListResponse(BaseSchema):
    """Paginated member listing scoped strictly to one organisation."""

    items: list[OrganisationMemberResponse]
    total: int


class UpdateOrganisationMemberRoleRequest(BaseSchema):
    """Request to update a member's organisation-scoped role."""

    role_name: str = Field(min_length=1, max_length=64)

    @field_validator("role_name")
    @classmethod
    def _validate_role_name(cls, value: str) -> str:
        return _clean_role_name(value)


class RemoveMembershipResponse(BaseSchema):
    """Confirmation returned after removing an organisation or project membership."""

    message: str
    user_id: uuid.UUID
    revoked_project_memberships: int = 0


class CreateInvitationRequest(BaseSchema):
    """Request payload to issue a hashed single-use organisation invitation."""

    email: NormalisedEmail
    role_name: str = Field(min_length=1, max_length=64)
    expires_in_hours: int = Field(default=72, ge=1, le=720)

    @field_validator("role_name")
    @classmethod
    def _validate_role_name(cls, value: str) -> str:
        return _clean_role_name(value)


class InvitationSummaryResponse(BaseSchema):
    """Safe invitation record without raw tokens or cryptographic hashes."""

    id: uuid.UUID
    organisation_id: uuid.UUID
    email: str
    role_name: str
    status: str
    invited_by_id: uuid.UUID
    expires_at: datetime
    accepted_at: datetime | None
    revoked_at: datetime | None
    created_at: datetime


class CreateInvitationResponse(BaseSchema):
    """Invitation creation response reporting honest email-delivery configuration."""

    invitation: InvitationSummaryResponse
    invitation_delivery: Literal["not_configured"]
    message: str
    development_invitation_token: str | None = None


class InvitationListResponse(BaseSchema):
    """Paginated list of invitations scoped strictly to one organisation."""

    items: list[InvitationSummaryResponse]
    total: int


class AcceptInvitationResponse(BaseSchema):
    """Confirmation of invitation acceptance and active organisation membership."""

    organisation_id: uuid.UUID
    organisation_name: str
    organisation_slug: str
    role_name: str
    membership_status: str
    joined_at: datetime


class AuditLogEntryResponse(BaseSchema):
    """Non-sensitive organisational audit log projection."""

    id: uuid.UUID
    actor_user_id: uuid.UUID | None
    organisation_id: uuid.UUID | None
    project_id: uuid.UUID | None
    event_type: str
    resource_type: str
    resource_id: str | None
    outcome: str
    request_id: str | None
    event_metadata: dict[str, Any] | None
    created_at: datetime


class AuditLogListResponse(BaseSchema):
    """Paginated audit log listing scoped to an organisation."""

    items: list[AuditLogEntryResponse]
    total: int
