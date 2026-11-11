"""Repository operations for project workspaces and project memberships."""

from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import Any, cast

from sqlalchemy import and_, func, or_, select, update
from sqlalchemy.engine import CursorResult
from sqlalchemy.orm import Session, selectinload

from app.models.enums import ProjectMembershipStatus, ProjectStatus, ProjectVisibility
from app.models.project import Project, ProjectMembership
from app.models.rbac import Role, RolePermission


class ProjectRepository:
    """Data-access operations for `projects` and `project_memberships`."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def get_by_id(self, project_id: uuid.UUID) -> Project | None:
        stmt = (
            select(Project)
            .where(Project.id == project_id)
            .options(
                selectinload(Project.organisation),
                selectinload(Project.owner),
                selectinload(Project.created_by),
            )
        )
        return self._session.scalar(stmt)

    def get_by_slug_in_org(
        self,
        *,
        organisation_id: uuid.UUID,
        normalised_slug: str,
    ) -> Project | None:
        stmt = select(Project).where(
            Project.organisation_id == organisation_id,
            Project.slug == normalised_slug,
        )
        return self._session.scalar(stmt)

    def create(
        self,
        *,
        organisation_id: uuid.UUID,
        name: str,
        slug: str,
        description: str | None,
        status: str,
        visibility: str,
        created_by_id: uuid.UUID,
        owner_id: uuid.UUID,
        start_date: date | None,
        target_completion_date: date | None,
    ) -> Project:
        project = Project(
            organisation_id=organisation_id,
            name=name,
            slug=slug,
            description=description,
            status=status,
            visibility=visibility,
            created_by_id=created_by_id,
            owner_id=owner_id,
            start_date=start_date,
            target_completion_date=target_completion_date,
        )
        self._session.add(project)
        self._session.flush()
        return project

    def list_for_user_in_org(
        self,
        *,
        organisation_id: uuid.UUID,
        user_id: uuid.UUID,
        include_all_in_org: bool,
        status: str | None = None,
        search: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[tuple[Project, ProjectMembership | None]], int]:
        active_pm_join = and_(
            ProjectMembership.project_id == Project.id,
            ProjectMembership.user_id == user_id,
            ProjectMembership.status == ProjectMembershipStatus.ACTIVE.value,
        )
        base = (
            select(Project, ProjectMembership)
            .outerjoin(ProjectMembership, active_pm_join)
            .where(Project.organisation_id == organisation_id)
        )
        if not include_all_in_org:
            base = base.where(
                or_(
                    ProjectMembership.id.is_not(None),
                    Project.visibility == ProjectVisibility.ORGANISATION.value,
                )
            )
        if status is not None:
            base = base.where(Project.status == status)
        if search:
            pattern = f"%{search.strip()}%"
            base = base.where(or_(Project.name.ilike(pattern), Project.slug.ilike(pattern)))

        total = int(self._session.scalar(select(func.count()).select_from(base.subquery())) or 0)
        stmt = (
            base.options(
                selectinload(Project.owner),
                selectinload(ProjectMembership.role),
            )
            .order_by(Project.created_at.desc(), Project.id.asc())
            .offset(offset)
            .limit(limit)
        )
        rows: list[tuple[Project, ProjectMembership | None]] = [
            (project, mem) for project, mem in self._session.execute(stmt).all()
        ]
        return rows, total

    def archive(self, project: Project, *, archived_at: datetime) -> None:
        project.status = ProjectStatus.ARCHIVED.value
        project.archived_at = archived_at
        self._session.flush()

    def get_active_membership(
        self,
        *,
        project_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> ProjectMembership | None:
        stmt = (
            select(ProjectMembership)
            .where(
                ProjectMembership.project_id == project_id,
                ProjectMembership.user_id == user_id,
                ProjectMembership.status == ProjectMembershipStatus.ACTIVE.value,
            )
            .options(
                selectinload(ProjectMembership.user),
                selectinload(ProjectMembership.role)
                .selectinload(Role.role_permissions)
                .selectinload(RolePermission.permission),
            )
        )
        return self._session.scalar(stmt)

    def list_memberships(
        self,
        *,
        project_id: uuid.UUID,
        status: str | None = ProjectMembershipStatus.ACTIVE.value,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[ProjectMembership], int]:
        base = select(ProjectMembership).where(ProjectMembership.project_id == project_id)
        if status is not None:
            base = base.where(ProjectMembership.status == status)

        total = int(self._session.scalar(select(func.count()).select_from(base.subquery())) or 0)
        stmt = (
            base.options(
                selectinload(ProjectMembership.user),
                selectinload(ProjectMembership.role),
            )
            .order_by(ProjectMembership.joined_at.asc(), ProjectMembership.id.asc())
            .offset(offset)
            .limit(limit)
        )
        return list(self._session.scalars(stmt).all()), total

    def create_membership(
        self,
        *,
        project_id: uuid.UUID,
        user_id: uuid.UUID,
        role_id: uuid.UUID,
        assigned_by_id: uuid.UUID | None,
        joined_at: datetime | None = None,
    ) -> ProjectMembership:
        membership = ProjectMembership(
            project_id=project_id,
            user_id=user_id,
            role_id=role_id,
            status=ProjectMembershipStatus.ACTIVE.value,
            assigned_by_id=assigned_by_id,
        )
        if joined_at is not None:
            membership.joined_at = joined_at
        self._session.add(membership)
        self._session.flush()
        return membership

    def revoke_all_for_user_in_organisation(
        self,
        *,
        organisation_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> int:
        org_project_ids = select(Project.id).where(Project.organisation_id == organisation_id)
        stmt = (
            update(ProjectMembership)
            .where(
                ProjectMembership.user_id == user_id,
                ProjectMembership.status == ProjectMembershipStatus.ACTIVE.value,
                ProjectMembership.project_id.in_(org_project_ids),
            )
            .values(status=ProjectMembershipStatus.REMOVED.value)
        )
        result = cast(CursorResult[Any], self._session.execute(stmt))
        return int(result.rowcount or 0)
