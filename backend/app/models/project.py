"""Project workspace and project membership SQLAlchemy models."""

from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    String,
    Text,
    UniqueConstraint,
    Uuid,
    func,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.enums import ProjectMembershipStatus, ProjectStatus, ProjectVisibility

if TYPE_CHECKING:
    from app.models.organisation import Organisation
    from app.models.rbac import Role
    from app.models.user import User


class Project(Base):
    """Project workspace scoped strictly inside a parent Organisation."""

    __tablename__ = "projects"
    __table_args__ = (
        UniqueConstraint("organisation_id", "slug", name="uq_projects_organisation_slug"),
        CheckConstraint(
            "status IN ('planning', 'active', 'on_hold', 'completed', 'archived')",
            name="project_status",
        ),
        CheckConstraint(
            "visibility IN ('private', 'organisation')",
            name="project_visibility",
        ),
        CheckConstraint("slug = lower(slug)", name="project_slug_lowercase"),
        CheckConstraint("length(trim(name)) >= 2", name="project_name_len"),
        CheckConstraint(
            "target_completion_date IS NULL OR start_date IS NULL "
            "OR target_completion_date >= start_date",
            name="project_dates_valid",
        ),
        Index("ix_projects_organisation_status", "organisation_id", "status"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    organisation_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("organisations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    slug: Mapped[str] = mapped_column(String(120), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default=ProjectStatus.PLANNING.value,
        server_default=ProjectStatus.PLANNING.value,
        index=True,
    )
    visibility: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default=ProjectVisibility.PRIVATE.value,
        server_default=ProjectVisibility.PRIVATE.value,
    )
    created_by_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    owner_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    start_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    target_completion_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )
    archived_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    organisation: Mapped[Organisation] = relationship(back_populates="projects")
    created_by: Mapped[User] = relationship(foreign_keys=[created_by_id])
    owner: Mapped[User] = relationship(foreign_keys=[owner_id])
    memberships: Mapped[list[ProjectMembership]] = relationship(
        back_populates="project",
        cascade="all, delete-orphan",
    )


class ProjectMembership(Base):
    """Scoped project membership assigning a project-scoped Role within a Project."""

    __tablename__ = "project_memberships"
    __table_args__ = (
        CheckConstraint(
            "status IN ('active', 'removed')",
            name="project_membership_status",
        ),
        Index(
            "uq_project_memberships_active_project_user",
            "project_id",
            "user_id",
            unique=True,
            postgresql_where=text("status = 'active'"),
            sqlite_where=text("status = 'active'"),
        ),
        Index("ix_project_memberships_user_status", "user_id", "status"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    project_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    role_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("roles.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default=ProjectMembershipStatus.ACTIVE.value,
        server_default=ProjectMembershipStatus.ACTIVE.value,
    )
    assigned_by_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    joined_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    project: Mapped[Project] = relationship(back_populates="memberships")
    user: Mapped[User] = relationship(foreign_keys=[user_id])
    assigned_by: Mapped[User | None] = relationship(foreign_keys=[assigned_by_id])
    role: Mapped[Role] = relationship(foreign_keys=[role_id])
