"""Pydantic v2 request and response schemas for project workspaces and project memberships."""

from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import Literal

from pydantic import Field, field_validator, model_validator

from app.core.validators import normalize_and_validate_slug, normalize_display_name
from app.schemas.common import BaseSchema
from app.schemas.organisation import _clean_optional_description, _clean_role_name


class CreateProjectRequest(BaseSchema):
    """Request payload to create a project workspace inside an organisation."""

    name: str = Field(min_length=2, max_length=200)
    slug: str | None = Field(default=None, min_length=2, max_length=120)
    description: str | None = Field(default=None, max_length=4000)
    status: Literal["planning", "active"] = "planning"
    visibility: Literal["private", "organisation"] = "private"
    owner_id: uuid.UUID | None = None
    start_date: date | None = None
    target_completion_date: date | None = None

    @field_validator("name")
    @classmethod
    def _validate_name(cls, value: str) -> str:
        return normalize_display_name(value, field_label="Project name", min_len=2, max_len=200)

    @field_validator("slug")
    @classmethod
    def _validate_slug(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return normalize_and_validate_slug(value, field_label="Project slug")

    @field_validator("description")
    @classmethod
    def _validate_description(cls, value: str | None) -> str | None:
        return _clean_optional_description(value)

    @model_validator(mode="after")
    def _validate_dates(self) -> CreateProjectRequest:
        if (
            self.start_date is not None
            and self.target_completion_date is not None
            and self.target_completion_date < self.start_date
        ):
            raise ValueError("Target completion date must not precede start date.")
        return self


class UpdateProjectRequest(BaseSchema):
    """Partial update payload for project workspace settings and lifecycle."""

    name: str | None = Field(default=None, min_length=2, max_length=200)
    slug: str | None = Field(default=None, min_length=2, max_length=120)
    description: str | None = Field(default=None, max_length=4000)
    status: Literal["planning", "active", "on_hold", "completed", "archived"] | None = None
    visibility: Literal["private", "organisation"] | None = None
    owner_id: uuid.UUID | None = None
    start_date: date | None = None
    target_completion_date: date | None = None

    @field_validator("name")
    @classmethod
    def _validate_name(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return normalize_display_name(value, field_label="Project name", min_len=2, max_len=200)

    @field_validator("slug")
    @classmethod
    def _validate_slug(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return normalize_and_validate_slug(value, field_label="Project slug")

    @field_validator("description")
    @classmethod
    def _validate_description(cls, value: str | None) -> str | None:
        return _clean_optional_description(value)

    @model_validator(mode="after")
    def _validate_update(self) -> UpdateProjectRequest:
        if not self.model_fields_set:
            raise ValueError("Provide at least one project field to update.")
        for required_if_present in ("name", "slug", "status", "visibility", "owner_id"):
            if (
                required_if_present in self.model_fields_set
                and getattr(self, required_if_present) is None
            ):
                raise ValueError(f"Field '{required_if_present}' cannot be null.")
        if (
            self.start_date is not None
            and self.target_completion_date is not None
            and self.target_completion_date < self.start_date
        ):
            raise ValueError("Target completion date must not precede start date.")
        return self


class ProjectSummaryResponse(BaseSchema):
    """Safe summary projection of a project accessible within its organisation."""

    id: uuid.UUID
    organisation_id: uuid.UUID
    name: str
    slug: str
    description: str | None
    status: str
    visibility: str
    created_by_id: uuid.UUID
    owner_id: uuid.UUID
    my_project_role: str | None
    start_date: date | None
    target_completion_date: date | None
    created_at: datetime
    updated_at: datetime
    archived_at: datetime | None


class ProjectResponse(ProjectSummaryResponse):
    """Detailed project view including resolved effective permissions in context."""

    effective_permissions: list[str]


class ProjectListResponse(BaseSchema):
    """Paginated list of accessible projects within an organisation."""

    items: list[ProjectSummaryResponse]
    total: int


class ProjectMemberResponse(BaseSchema):
    """Safe projection of an assigned project member."""

    id: uuid.UUID
    project_id: uuid.UUID
    user_id: uuid.UUID
    full_name: str
    email: str
    role_name: str
    status: str
    assigned_by_id: uuid.UUID | None
    joined_at: datetime
    created_at: datetime
    updated_at: datetime


class ProjectMemberListResponse(BaseSchema):
    """Paginated listing of project members."""

    items: list[ProjectMemberResponse]
    total: int


class AddProjectMemberRequest(BaseSchema):
    """Request payload to add an existing organisation member to a project."""

    user_id: uuid.UUID
    role_name: str = Field(min_length=1, max_length=64)

    @field_validator("role_name")
    @classmethod
    def _validate_role_name(cls, value: str) -> str:
        return _clean_role_name(value)


class UpdateProjectMemberRoleRequest(BaseSchema):
    """Request payload to change a project member's project-scoped role."""

    role_name: str = Field(min_length=1, max_length=64)

    @field_validator("role_name")
    @classmethod
    def _validate_role_name(cls, value: str) -> str:
        return _clean_role_name(value)
