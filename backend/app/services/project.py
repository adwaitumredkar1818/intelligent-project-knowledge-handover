"""Service layer for multi-tenant project workspaces and project memberships."""

from __future__ import annotations

import uuid

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.exceptions import (
    BadRequestError,
    ConflictError,
    NotFoundError,
    ServiceUnavailableError,
)
from app.core.security import derive_slug_from_name, utc_now
from app.models.enums import (
    OrganisationStatus,
    ProjectMembershipStatus,
    ProjectStatus,
    RoleName,
    RoleScopeType,
)
from app.models.project import Project, ProjectMembership
from app.repositories.organisation import OrganisationRepository
from app.repositories.project import ProjectRepository
from app.repositories.rbac import RbacRepository
from app.schemas.organisation import RemoveMembershipResponse
from app.schemas.project import (
    AddProjectMemberRequest,
    CreateProjectRequest,
    ProjectListResponse,
    ProjectMemberListResponse,
    ProjectMemberResponse,
    ProjectResponse,
    ProjectSummaryResponse,
    UpdateProjectMemberRoleRequest,
    UpdateProjectRequest,
)
from app.services.audit import AuditService
from app.services.rbac import OrganisationContext, ProjectContext, RbacService

VALID_PROJECT_STATUS_TRANSITIONS: dict[str, frozenset[str]] = {
    ProjectStatus.PLANNING.value: frozenset(
        {
            ProjectStatus.PLANNING.value,
            ProjectStatus.ACTIVE.value,
            ProjectStatus.ON_HOLD.value,
            ProjectStatus.ARCHIVED.value,
        }
    ),
    ProjectStatus.ACTIVE.value: frozenset(
        {
            ProjectStatus.ACTIVE.value,
            ProjectStatus.ON_HOLD.value,
            ProjectStatus.COMPLETED.value,
            ProjectStatus.ARCHIVED.value,
        }
    ),
    ProjectStatus.ON_HOLD.value: frozenset(
        {
            ProjectStatus.ON_HOLD.value,
            ProjectStatus.ACTIVE.value,
            ProjectStatus.ARCHIVED.value,
        }
    ),
    ProjectStatus.COMPLETED.value: frozenset(
        {
            ProjectStatus.COMPLETED.value,
            ProjectStatus.ACTIVE.value,
            ProjectStatus.ARCHIVED.value,
        }
    ),
    ProjectStatus.ARCHIVED.value: frozenset(),
}


def _build_project_summary(
    project: Project,
    *,
    my_project_role: str | None,
) -> ProjectSummaryResponse:
    return ProjectSummaryResponse(
        id=project.id,
        organisation_id=project.organisation_id,
        name=project.name,
        slug=project.slug,
        description=project.description,
        status=project.status,
        visibility=project.visibility,
        created_by_id=project.created_by_id,
        owner_id=project.owner_id,
        my_project_role=my_project_role,
        start_date=project.start_date,
        target_completion_date=project.target_completion_date,
        created_at=project.created_at,
        updated_at=project.updated_at,
        archived_at=project.archived_at,
    )


def _build_project_member_response(membership: ProjectMembership) -> ProjectMemberResponse:
    return ProjectMemberResponse(
        id=membership.id,
        project_id=membership.project_id,
        user_id=membership.user_id,
        full_name=membership.user.full_name,
        email=membership.user.email,
        role_name=membership.role.name,
        status=membership.status,
        assigned_by_id=membership.assigned_by_id,
        joined_at=membership.joined_at,
        created_at=membership.created_at,
        updated_at=membership.updated_at,
    )


class ProjectService:
    """Orchestrates project creation, lifecycle governance, and tenant-isolated membership."""

    def __init__(
        self,
        *,
        db_session: Session,
        org_repository: OrganisationRepository,
        project_repository: ProjectRepository,
        rbac_repository: RbacRepository,
        rbac_service: RbacService,
        audit_service: AuditService,
    ) -> None:
        self._db = db_session
        self._org_repo = org_repository
        self._project_repo = project_repository
        self._rbac_repo = rbac_repository
        self._rbac_service = rbac_service
        self._audit = audit_service

    def _require_active_organisation_and_project(
        self,
        *,
        ctx: ProjectContext,
        allow_archived_project: bool = False,
    ) -> None:
        if ctx.organisation.status != OrganisationStatus.ACTIVE.value:
            raise ConflictError(
                f"Parent organisation is '{ctx.organisation.status}' and blocks modifications.",
                code="ORGANISATION_NOT_ACTIVE",
            )
        if not allow_archived_project and ctx.project.status == ProjectStatus.ARCHIVED.value:
            raise ConflictError(
                "Archived projects cannot be modified.",
                code="PROJECT_ARCHIVED",
            )

    def _require_active_org_member(
        self,
        *,
        organisation_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> None:
        if (
            self._org_repo.get_active_membership(
                organisation_id=organisation_id,
                user_id=user_id,
            )
            is None
        ):
            # Identical error for non-existent and out-of-tenant users prevents user enumeration.
            raise BadRequestError(
                "Target user must be an active member of the parent organisation.",
                code="USER_NOT_ORG_MEMBER",
            )

    def _resolve_slug(self, explicit_slug: str | None, name: str) -> str:
        if explicit_slug is not None:
            return explicit_slug
        try:
            return derive_slug_from_name(name, field_label="Project slug")
        except ValueError as exc:
            raise BadRequestError(str(exc), code="INVALID_SLUG") from exc

    def create_project(
        self,
        *,
        org_ctx: OrganisationContext,
        payload: CreateProjectRequest,
    ) -> ProjectResponse:
        """Create a project inside a verified organisation and assign initial project managers."""
        if org_ctx.organisation.status != OrganisationStatus.ACTIVE.value:
            raise ConflictError(
                f"Organisation is '{org_ctx.organisation.status}' and cannot host new projects.",
                code="ORGANISATION_NOT_ACTIVE",
            )

        slug = self._resolve_slug(payload.slug, payload.name)
        if (
            self._project_repo.get_by_slug_in_org(
                organisation_id=org_ctx.organisation.id,
                normalised_slug=slug,
            )
            is not None
        ):
            raise ConflictError(
                "A project with this slug already exists in the organisation.",
                code="PROJECT_SLUG_ALREADY_EXISTS",
            )

        owner_id = payload.owner_id or org_ctx.principal.user.id
        self._require_active_org_member(
            organisation_id=org_ctx.organisation.id,
            user_id=owner_id,
        )

        manager_role = self._rbac_repo.get_role_by_name(RoleName.PROJECT_MANAGER.value)
        if manager_role is None:
            raise ServiceUnavailableError(
                "Project RBAC roles are not initialised.",
                code="RBAC_CATALOG_NOT_READY",
            )

        now = utc_now()
        try:
            project = self._project_repo.create(
                organisation_id=org_ctx.organisation.id,
                name=payload.name,
                slug=slug,
                description=payload.description,
                status=payload.status,
                visibility=payload.visibility,
                created_by_id=org_ctx.principal.user.id,
                owner_id=owner_id,
                start_date=payload.start_date,
                target_completion_date=payload.target_completion_date,
            )
            self._project_repo.create_membership(
                project_id=project.id,
                user_id=owner_id,
                role_id=manager_role.id,
                assigned_by_id=org_ctx.principal.user.id,
                joined_at=now,
            )
            if org_ctx.principal.user.id != owner_id:
                self._project_repo.create_membership(
                    project_id=project.id,
                    user_id=org_ctx.principal.user.id,
                    role_id=manager_role.id,
                    assigned_by_id=org_ctx.principal.user.id,
                    joined_at=now,
                )

            self._audit.record_event(
                event_type="project.created",
                resource_type="project",
                actor_user_id=org_ctx.principal.user.id,
                organisation_id=org_ctx.organisation.id,
                project_id=project.id,
                resource_id=str(project.id),
                metadata={
                    "slug": project.slug,
                    "status": project.status,
                    "visibility": project.visibility,
                    "owner_id": str(owner_id),
                },
                message=(
                    f"Created project '{project.slug}' "
                    f"in organisation '{org_ctx.organisation.id}'."
                ),
            )
            self._audit.record_event(
                event_type="project.member.added",
                resource_type="project_membership",
                actor_user_id=org_ctx.principal.user.id,
                organisation_id=org_ctx.organisation.id,
                project_id=project.id,
                resource_id=str(owner_id),
                metadata={"role_name": manager_role.name, "via": "project_creation"},
                message=(
                    f"Assigned '{owner_id}' as '{manager_role.name}' "
                    f"in project '{project.id}'."
                ),
            )
            self._db.commit()
        except IntegrityError as exc:
            self._db.rollback()
            raise ConflictError(
                "A project with this slug already exists in the organisation.",
                code="PROJECT_SLUG_ALREADY_EXISTS",
            ) from exc

        project_ctx = self._rbac_service.resolve_project_context(
            project_id=project.id,
            principal=org_ctx.principal,
        )
        return self.get_project_detail(project_ctx)

    def list_projects_in_organisation(
        self,
        *,
        org_ctx: OrganisationContext,
        status: str | None = None,
        search: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> ProjectListResponse:
        """List permitted projects strictly scoped to the caller's verified organisation."""
        rows, total = self._project_repo.list_for_user_in_org(
            organisation_id=org_ctx.organisation.id,
            user_id=org_ctx.principal.user.id,
            include_all_in_org=org_ctx.has_permission("project.read"),
            status=status,
            search=search,
            limit=limit,
            offset=offset,
        )
        items = [
            _build_project_summary(
                project,
                my_project_role=mem.role.name if mem is not None else None,
            )
            for project, mem in rows
        ]
        return ProjectListResponse(items=items, total=total)

    def get_project_detail(self, ctx: ProjectContext) -> ProjectResponse:
        """Return project metadata plus effective permissions in the verified project context."""
        project = ctx.project
        return ProjectResponse(
            id=project.id,
            organisation_id=project.organisation_id,
            name=project.name,
            slug=project.slug,
            description=project.description,
            status=project.status,
            visibility=project.visibility,
            created_by_id=project.created_by_id,
            owner_id=project.owner_id,
            my_project_role=ctx.project_role.name if ctx.project_role is not None else None,
            effective_permissions=sorted(ctx.permissions),
            start_date=project.start_date,
            target_completion_date=project.target_completion_date,
            created_at=project.created_at,
            updated_at=project.updated_at,
            archived_at=project.archived_at,
        )

    def update_project(
        self,
        *,
        ctx: ProjectContext,
        payload: UpdateProjectRequest,
    ) -> ProjectResponse:
        """Update project workspace attributes, validated lifecycle transitions, and ownership."""
        self._require_active_organisation_and_project(ctx=ctx)
        project = ctx.project
        changed_fields: list[str] = []

        merged_start = (
            payload.start_date
            if "start_date" in payload.model_fields_set
            else project.start_date
        )
        merged_target = (
            payload.target_completion_date
            if "target_completion_date" in payload.model_fields_set
            else project.target_completion_date
        )
        if merged_start is not None and merged_target is not None and merged_target < merged_start:
            raise BadRequestError(
                "Target completion date must not precede start date.",
                code="INVALID_PROJECT_DATES",
            )

        if "slug" in payload.model_fields_set and payload.slug is not None:
            if payload.slug != project.slug:
                existing = self._project_repo.get_by_slug_in_org(
                    organisation_id=project.organisation_id,
                    normalised_slug=payload.slug,
                )
                if existing is not None and existing.id != project.id:
                    raise ConflictError(
                        "A project with this slug already exists in the organisation.",
                        code="PROJECT_SLUG_ALREADY_EXISTS",
                    )
                project.slug = payload.slug
                changed_fields.append("slug")

        if "name" in payload.model_fields_set and payload.name is not None:
            if payload.name != project.name:
                project.name = payload.name
                changed_fields.append("name")

        if "description" in payload.model_fields_set and payload.description != project.description:
            project.description = payload.description
            changed_fields.append("description")

        if "visibility" in payload.model_fields_set and payload.visibility is not None:
            if payload.visibility != project.visibility:
                project.visibility = payload.visibility
                changed_fields.append("visibility")

        if "start_date" in payload.model_fields_set and payload.start_date != project.start_date:
            project.start_date = payload.start_date
            changed_fields.append("start_date")

        if (
            "target_completion_date" in payload.model_fields_set
            and payload.target_completion_date != project.target_completion_date
        ):
            project.target_completion_date = payload.target_completion_date
            changed_fields.append("target_completion_date")

        if "status" in payload.model_fields_set and payload.status is not None:
            allowed_next = VALID_PROJECT_STATUS_TRANSITIONS.get(project.status, frozenset())
            if payload.status not in allowed_next:
                raise ConflictError(
                    f"Cannot transition project status from '{project.status}' "
                    f"to '{payload.status}'.",
                    code="INVALID_PROJECT_STATUS_TRANSITION",
                )
            if payload.status != project.status:
                project.status = payload.status
                changed_fields.append("status")
                if payload.status == ProjectStatus.ARCHIVED.value:
                    project.archived_at = utc_now()

        if "owner_id" in payload.model_fields_set and payload.owner_id is not None:
            if payload.owner_id != project.owner_id:
                self._require_active_org_member(
                    organisation_id=project.organisation_id,
                    user_id=payload.owner_id,
                )
                manager_role = self._rbac_repo.get_role_by_name(RoleName.PROJECT_MANAGER.value)
                if manager_role is None:
                    raise ServiceUnavailableError(
                        "Project RBAC roles are not initialised.",
                        code="RBAC_CATALOG_NOT_READY",
                    )
                owner_mem = self._project_repo.get_active_membership(
                    project_id=project.id,
                    user_id=payload.owner_id,
                )
                if owner_mem is None:
                    self._project_repo.create_membership(
                        project_id=project.id,
                        user_id=payload.owner_id,
                        role_id=manager_role.id,
                        assigned_by_id=ctx.principal.user.id,
                        joined_at=utc_now(),
                    )
                else:
                    owner_mem.role_id = manager_role.id
                project.owner_id = payload.owner_id
                changed_fields.append("owner_id")

        self._audit.record_event(
            event_type="project.updated",
            resource_type="project",
            actor_user_id=ctx.principal.user.id,
            organisation_id=project.organisation_id,
            project_id=project.id,
            resource_id=str(project.id),
            metadata={"changed_fields": changed_fields, "status": project.status},
            message=f"Updated project '{project.id}'.",
        )
        try:
            self._db.commit()
        except IntegrityError as exc:
            self._db.rollback()
            raise ConflictError(
                "A project with this slug already exists in the organisation.",
                code="PROJECT_SLUG_ALREADY_EXISTS",
            ) from exc

        refreshed = self._rbac_service.resolve_project_context(
            project_id=project.id,
            principal=ctx.principal,
        )
        return self.get_project_detail(refreshed)

    def archive_project(self, *, ctx: ProjectContext) -> ProjectResponse:
        """Archive a non-archived project within an active organisation."""
        self._require_active_organisation_and_project(ctx=ctx, allow_archived_project=True)
        if ctx.project.status == ProjectStatus.ARCHIVED.value:
            raise ConflictError(
                "Project is already archived.",
                code="PROJECT_ALREADY_ARCHIVED",
            )

        self._project_repo.archive(ctx.project, archived_at=utc_now())
        self._audit.record_event(
            event_type="project.archived",
            resource_type="project",
            actor_user_id=ctx.principal.user.id,
            organisation_id=ctx.organisation.id,
            project_id=ctx.project.id,
            resource_id=str(ctx.project.id),
            metadata={"slug": ctx.project.slug},
            message=f"Archived project '{ctx.project.id}'.",
        )
        self._db.commit()
        refreshed = self._rbac_service.resolve_project_context(
            project_id=ctx.project.id,
            principal=ctx.principal,
        )
        return self.get_project_detail(refreshed)

    def list_project_members(
        self,
        *,
        ctx: ProjectContext,
        status: str | None = ProjectMembershipStatus.ACTIVE.value,
        limit: int = 50,
        offset: int = 0,
    ) -> ProjectMemberListResponse:
        """List members strictly scoped to one verified project."""
        rows, total = self._project_repo.list_memberships(
            project_id=ctx.project.id,
            status=status,
            limit=limit,
            offset=offset,
        )
        return ProjectMemberListResponse(
            items=[_build_project_member_response(row) for row in rows],
            total=total,
        )

    def add_project_member(
        self,
        *,
        ctx: ProjectContext,
        payload: AddProjectMemberRequest,
    ) -> ProjectMemberResponse:
        """Assign a parent-organisation member into a project using a project-scoped role."""
        self._require_active_organisation_and_project(ctx=ctx)

        target_role = self._rbac_service.get_scoped_role_or_fail(
            role_name=payload.role_name,
            expected_scope=RoleScopeType.PROJECT,
            actor_user_id=ctx.principal.user.id,
            organisation_id=ctx.organisation.id,
            project_id=ctx.project.id,
        )
        self._require_active_org_member(
            organisation_id=ctx.organisation.id,
            user_id=payload.user_id,
        )

        if (
            self._project_repo.get_active_membership(
                project_id=ctx.project.id,
                user_id=payload.user_id,
            )
            is not None
        ):
            raise ConflictError(
                "User is already an active member of this project.",
                code="MEMBERSHIP_ALREADY_EXISTS",
            )

        try:
            self._project_repo.create_membership(
                project_id=ctx.project.id,
                user_id=payload.user_id,
                role_id=target_role.id,
                assigned_by_id=ctx.principal.user.id,
                joined_at=utc_now(),
            )
            self._audit.record_event(
                event_type="project.member.added",
                resource_type="project_membership",
                actor_user_id=ctx.principal.user.id,
                organisation_id=ctx.organisation.id,
                project_id=ctx.project.id,
                resource_id=str(payload.user_id),
                metadata={"target_user_id": str(payload.user_id), "role_name": target_role.name},
                message=(
                    f"Added user '{payload.user_id}' as '{target_role.name}' "
                    f"to project '{ctx.project.id}'."
                ),
            )
            self._db.commit()
        except IntegrityError as exc:
            self._db.rollback()
            raise ConflictError(
                "User is already an active member of this project.",
                code="MEMBERSHIP_ALREADY_EXISTS",
            ) from exc

        loaded = self._project_repo.get_active_membership(
            project_id=ctx.project.id,
            user_id=payload.user_id,
        )
        if loaded is None:
            raise NotFoundError(
                "Active project membership was not found.",
                code="MEMBERSHIP_NOT_FOUND",
            )
        return _build_project_member_response(loaded)

    def update_project_member_role(
        self,
        *,
        ctx: ProjectContext,
        target_user_id: uuid.UUID,
        payload: UpdateProjectMemberRoleRequest,
    ) -> ProjectMemberResponse:
        """Change an active project member's project-scoped role."""
        self._require_active_organisation_and_project(ctx=ctx)

        target_role = self._rbac_service.get_scoped_role_or_fail(
            role_name=payload.role_name,
            expected_scope=RoleScopeType.PROJECT,
            actor_user_id=ctx.principal.user.id,
            organisation_id=ctx.organisation.id,
            project_id=ctx.project.id,
        )
        membership = self._project_repo.get_active_membership(
            project_id=ctx.project.id,
            user_id=target_user_id,
        )
        if membership is None:
            raise NotFoundError(
                "Active project membership was not found.",
                code="MEMBERSHIP_NOT_FOUND",
            )

        if (
            target_user_id == ctx.project.owner_id
            and target_role.name != RoleName.PROJECT_MANAGER.value
        ):
            raise ConflictError(
                "Transfer project ownership before demoting the project owner.",
                code="PROJECT_OWNER_ROLE_LOCKED",
            )

        previous_role = membership.role.name
        membership.role_id = target_role.id
        membership.role = target_role
        self._audit.record_event(
            event_type="project.member.role_changed",
            resource_type="project_membership",
            actor_user_id=ctx.principal.user.id,
            organisation_id=ctx.organisation.id,
            project_id=ctx.project.id,
            resource_id=str(target_user_id),
            metadata={
                "target_user_id": str(target_user_id),
                "previous_role": previous_role,
                "new_role": target_role.name,
            },
            message=(
                f"Changed project member '{target_user_id}' role in '{ctx.project.id}' "
                f"from '{previous_role}' to '{target_role.name}'."
            ),
        )
        self._db.commit()
        refreshed = self._project_repo.get_active_membership(
            project_id=ctx.project.id,
            user_id=target_user_id,
        )
        if refreshed is None:
            raise NotFoundError(
                "Active project membership was not found.",
                code="MEMBERSHIP_NOT_FOUND",
            )
        return _build_project_member_response(refreshed)

    def remove_project_member(
        self,
        *,
        ctx: ProjectContext,
        target_user_id: uuid.UUID,
    ) -> RemoveMembershipResponse:
        """Remove a user's active membership from the project immediately."""
        self._require_active_organisation_and_project(ctx=ctx)

        membership = self._project_repo.get_active_membership(
            project_id=ctx.project.id,
            user_id=target_user_id,
        )
        if membership is None:
            raise NotFoundError(
                "Active project membership was not found.",
                code="MEMBERSHIP_NOT_FOUND",
            )

        if target_user_id == ctx.project.owner_id:
            raise ConflictError(
                "Transfer project ownership before removing the current project owner.",
                code="PROJECT_OWNER_REMOVAL_FORBIDDEN",
            )

        previous_role = membership.role.name
        membership.status = ProjectMembershipStatus.REMOVED.value
        self._audit.record_event(
            event_type="project.member.removed",
            resource_type="project_membership",
            actor_user_id=ctx.principal.user.id,
            organisation_id=ctx.organisation.id,
            project_id=ctx.project.id,
            resource_id=str(target_user_id),
            metadata={"target_user_id": str(target_user_id), "previous_role": previous_role},
            message=f"Removed user '{target_user_id}' from project '{ctx.project.id}'.",
        )
        self._db.commit()
        return RemoveMembershipResponse(
            message="Project member removed and project access revoked immediately.",
            user_id=target_user_id,
            revoked_project_memberships=1,
        )
