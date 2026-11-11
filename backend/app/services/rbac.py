"""Centralised Role-Based Access Control (RBAC) & multi-tenant authorisation service."""

from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.core.exceptions import BadRequestError, ForbiddenError, NotFoundError
from app.core.logging import log_security_event
from app.core.rbac_catalog import (
    KNOWN_PERMISSION_CODES,
    ORG_ROLE_RANK,
    ORGANISATION_PERMISSION_CODES,
    PROJECT_PERMISSION_CODES,
)
from app.models.enums import ProjectVisibility, RoleScopeType
from app.models.organisation import Organisation, OrganisationMembership
from app.models.project import Project, ProjectMembership
from app.models.rbac import Role
from app.models.user import User
from app.repositories.organisation import OrganisationRepository
from app.repositories.project import ProjectRepository
from app.repositories.rbac import RbacRepository
from app.repositories.user import UserRepository
from app.schemas.user import AssignRoleResponse, RoleListResponse, RoleResponse


@dataclass(frozen=True, slots=True)
class AuthenticatedPrincipal:
    """Resolved authenticated user identity and active platform-scoped permissions."""

    user: User
    session_family_id: uuid.UUID
    roles: tuple[str, ...]
    permissions: frozenset[str]

    def has_permission(self, permission_code: str) -> bool:
        """Fail closed for unknown or unassigned permissions."""
        if permission_code not in KNOWN_PERMISSION_CODES:
            return False
        return permission_code in self.permissions


@dataclass(frozen=True, slots=True)
class OrganisationContext:
    """Verified multi-tenant organisation context and resolved organisation role/permissions."""

    principal: AuthenticatedPrincipal
    organisation: Organisation
    membership: OrganisationMembership
    role: Role
    permissions: frozenset[str]

    def has_permission(self, permission_code: str) -> bool:
        """Fail closed for unknown or ungranted organisation permissions."""
        if permission_code not in KNOWN_PERMISSION_CODES:
            return False
        return permission_code in self.permissions


@dataclass(frozen=True, slots=True)
class ProjectContext:
    """Verified multi-tenant project context enforcing both parent org and project access."""

    principal: AuthenticatedPrincipal
    organisation: Organisation
    organisation_membership: OrganisationMembership
    organisation_role: Role
    project: Project
    project_membership: ProjectMembership | None
    project_role: Role | None
    permissions: frozenset[str]

    def has_permission(self, permission_code: str) -> bool:
        """Fail closed for unknown or ungranted project permissions."""
        if permission_code not in KNOWN_PERMISSION_CODES:
            return False
        return permission_code in self.permissions


def to_role_response(role: Role) -> RoleResponse:
    """Convert ORM Role into safe RoleResponse DTO."""
    permissions = sorted(rp.permission.code for rp in role.role_permissions if rp.permission)
    return RoleResponse(
        id=role.id,
        name=role.name,
        display_name=role.display_name,
        description=role.description,
        scope_type=role.scope_type,
        is_system=role.is_system,
        permissions=permissions,
    )


def _extract_role_permissions(
    role: Role,
    *,
    allowed_codes: frozenset[str],
) -> frozenset[str]:
    return frozenset(
        rp.permission.code
        for rp in role.role_permissions
        if rp.permission is not None and rp.permission.code in allowed_codes
    )


def _enforce_permissions(
    *,
    has_permission: frozenset[str],
    required_permissions: tuple[str, ...],
    actor_user_id: uuid.UUID,
    event_type: str,
    organisation_id: uuid.UUID | None = None,
    project_id: uuid.UUID | None = None,
) -> None:
    if not required_permissions:
        raise ForbiddenError(
            "Permission check failed closed due to empty requirement.",
            code="FORBIDDEN",
        )

    missing = [
        perm
        for perm in required_permissions
        if perm not in KNOWN_PERMISSION_CODES or perm not in has_permission
    ]
    if missing:
        log_security_event(
            event_type=event_type,
            outcome="denied",
            actor_user_id=str(actor_user_id),
            organisation_id=str(organisation_id) if organisation_id is not None else None,
            project_id=str(project_id) if project_id is not None else None,
            message=f"Denied access lacking required permissions: {', '.join(missing)}.",
            level=logging.WARNING,
        )
        raise ForbiddenError(
            "You do not have permission to perform this action.",
            code="FORBIDDEN",
        )


class RbacService:
    """Authorisation service resolving and enforcing platform, organisation, and project RBAC."""

    def __init__(
        self,
        *,
        db_session: Session,
        rbac_repository: RbacRepository,
        user_repository: UserRepository,
        organisation_repository: OrganisationRepository | None = None,
        project_repository: ProjectRepository | None = None,
    ) -> None:
        self._db = db_session
        self._rbac_repo = rbac_repository
        self._user_repo = user_repository
        self._org_repo = organisation_repository or OrganisationRepository(db_session)
        self._project_repo = project_repository or ProjectRepository(db_session)

    def resolve_principal(
        self,
        *,
        user: User,
        session_family_id: uuid.UUID,
    ) -> AuthenticatedPrincipal:
        """Resolve strictly platform-scoped roles and permissions for an authenticated user."""
        role_names, permissions = self._rbac_repo.get_user_platform_roles_and_permissions(user.id)
        return AuthenticatedPrincipal(
            user=user,
            session_family_id=session_family_id,
            roles=tuple(role_names),
            permissions=permissions,
        )

    def require_permissions(
        self,
        principal: AuthenticatedPrincipal,
        required_permissions: tuple[str, ...],
    ) -> None:
        """Enforce all required platform permissions, failing closed on missing or unknown codes."""
        _enforce_permissions(
            has_permission=principal.permissions,
            required_permissions=required_permissions,
            actor_user_id=principal.user.id,
            event_type="rbac.permission_denied",
        )

    def resolve_organisation_context(
        self,
        *,
        organisation_id: uuid.UUID,
        principal: AuthenticatedPrincipal,
    ) -> OrganisationContext:
        """Resolve verified active membership & role for one organisation (404 on non-member)."""
        organisation = self._org_repo.get_by_id(organisation_id)
        if organisation is None:
            raise NotFoundError("Organisation was not found.", code="ORGANISATION_NOT_FOUND")

        membership = self._org_repo.get_active_membership(
            organisation_id=organisation.id,
            user_id=principal.user.id,
        )
        if membership is None:
            log_security_event(
                event_type="tenant.organisation_access_denied",
                outcome="denied",
                actor_user_id=str(principal.user.id),
                organisation_id=str(organisation.id),
                message="Denied non-member access to organisation resource.",
                level=logging.WARNING,
            )
            raise NotFoundError("Organisation was not found.", code="ORGANISATION_NOT_FOUND")

        role = membership.role
        if role is None or role.scope_type != RoleScopeType.ORGANISATION.value:
            raise ForbiddenError(
                "Invalid organisation role configuration.",
                code="FORBIDDEN",
            )

        permissions = _extract_role_permissions(
            role,
            allowed_codes=ORGANISATION_PERMISSION_CODES | PROJECT_PERMISSION_CODES,
        )
        return OrganisationContext(
            principal=principal,
            organisation=organisation,
            membership=membership,
            role=role,
            permissions=permissions,
        )

    def require_organisation_permissions(
        self,
        context: OrganisationContext,
        required_permissions: tuple[str, ...],
    ) -> None:
        """Enforce required organisation-scoped permissions inside an already-verified org."""
        _enforce_permissions(
            has_permission=context.permissions,
            required_permissions=required_permissions,
            actor_user_id=context.principal.user.id,
            organisation_id=context.organisation.id,
            event_type="rbac.organisation_permission_denied",
        )

    def resolve_project_context(
        self,
        *,
        project_id: uuid.UUID,
        principal: AuthenticatedPrincipal,
        require_explicit_membership: bool = False,
    ) -> ProjectContext:
        """Resolve verified multi-tenant project context; parent org membership is mandatory."""
        project = self._project_repo.get_by_id(project_id)
        if project is None or project.organisation is None:
            raise NotFoundError("Project was not found.", code="PROJECT_NOT_FOUND")

        org_membership = self._org_repo.get_active_membership(
            organisation_id=project.organisation_id,
            user_id=principal.user.id,
        )
        if (
            org_membership is None
            or org_membership.role is None
            or org_membership.role.scope_type != RoleScopeType.ORGANISATION.value
        ):
            log_security_event(
                event_type="tenant.project_access_denied",
                outcome="denied",
                actor_user_id=str(principal.user.id),
                organisation_id=str(project.organisation_id),
                project_id=str(project.id),
                message="Denied project access because caller is not an active parent org member.",
                level=logging.WARNING,
            )
            raise NotFoundError("Project was not found.", code="PROJECT_NOT_FOUND")

        org_permissions = _extract_role_permissions(
            org_membership.role,
            allowed_codes=ORGANISATION_PERMISSION_CODES | PROJECT_PERMISSION_CODES,
        )
        project_membership = self._project_repo.get_active_membership(
            project_id=project.id,
            user_id=principal.user.id,
        )
        project_role: Role | None = None
        project_permissions: frozenset[str] = frozenset()
        if project_membership is not None:
            candidate_role = project_membership.role
            if (
                candidate_role is None
                or candidate_role.scope_type != RoleScopeType.PROJECT.value
            ):
                raise ForbiddenError(
                    "Invalid project role configuration.",
                    code="FORBIDDEN",
                )
            project_role = candidate_role
            project_permissions = _extract_role_permissions(
                candidate_role,
                allowed_codes=PROJECT_PERMISSION_CODES,
            )

        can_discover = (
            project_membership is not None
            or "project.read" in org_permissions
            or (
                project.visibility == ProjectVisibility.ORGANISATION.value
                and "organisation.read" in org_permissions
            )
        )
        if not can_discover:
            log_security_event(
                event_type="tenant.project_access_denied",
                outcome="denied",
                actor_user_id=str(principal.user.id),
                organisation_id=str(project.organisation_id),
                project_id=str(project.id),
                message="Denied access to private project without project membership.",
                level=logging.WARNING,
            )
            raise NotFoundError("Project was not found.", code="PROJECT_NOT_FOUND")

        if require_explicit_membership and project_membership is None:
            log_security_event(
                event_type="rbac.project_membership_required",
                outcome="denied",
                actor_user_id=str(principal.user.id),
                organisation_id=str(project.organisation_id),
                project_id=str(project.id),
                message="Denied action requiring explicit project membership.",
                level=logging.WARNING,
            )
            raise ForbiddenError(
                "Active project membership is required to access this resource.",
                code="FORBIDDEN",
            )

        return ProjectContext(
            principal=principal,
            organisation=project.organisation,
            organisation_membership=org_membership,
            organisation_role=org_membership.role,
            project=project,
            project_membership=project_membership,
            project_role=project_role,
            permissions=org_permissions | project_permissions,
        )

    def require_project_permissions(
        self,
        context: ProjectContext,
        required_permissions: tuple[str, ...],
        *,
        require_explicit_membership: bool = False,
    ) -> None:
        """Enforce project-scoped permissions inside an already-verified project context."""
        if require_explicit_membership and context.project_membership is None:
            log_security_event(
                event_type="rbac.project_membership_required",
                outcome="denied",
                actor_user_id=str(context.principal.user.id),
                organisation_id=str(context.organisation.id),
                project_id=str(context.project.id),
                message="Denied project operation without active project membership.",
                level=logging.WARNING,
            )
            raise ForbiddenError(
                "Active project membership is required to perform this action.",
                code="FORBIDDEN",
            )
        _enforce_permissions(
            has_permission=context.permissions,
            required_permissions=required_permissions,
            actor_user_id=context.principal.user.id,
            organisation_id=context.organisation.id,
            project_id=context.project.id,
            event_type="rbac.project_permission_denied",
        )

    def resolve_project_read_context(
        self,
        *,
        project_id: uuid.UUID,
        principal: AuthenticatedPrincipal,
    ) -> ProjectContext:
        """Enforce read permission consistent with project membership or organisation visibility."""
        context = self.resolve_project_context(project_id=project_id, principal=principal)
        if context.has_permission("project.read"):
            return context
        if (
            context.project.visibility == ProjectVisibility.ORGANISATION.value
            and context.has_permission("organisation.read")
        ):
            return context
        _enforce_permissions(
            has_permission=context.permissions,
            required_permissions=("project.read",),
            actor_user_id=principal.user.id,
            organisation_id=context.organisation.id,
            project_id=context.project.id,
            event_type="rbac.project_permission_denied",
        )
        return context  # pragma: no cover

    def require_org_role_authority(
        self,
        *,
        actor_role_name: str,
        target_role_name: str,
        actor_user_id: uuid.UUID,
        organisation_id: uuid.UUID,
        action_label: str,
    ) -> None:
        """Prevent privilege escalation beyond an actor's own organisation role rank."""
        actor_rank = ORG_ROLE_RANK.get(actor_role_name, 0)
        target_rank = ORG_ROLE_RANK.get(target_role_name, 999)
        if actor_rank < target_rank:
            log_security_event(
                event_type="rbac.privilege_escalation_blocked",
                outcome="denied",
                actor_user_id=str(actor_user_id),
                organisation_id=str(organisation_id),
                message=(
                    f"Blocked '{actor_role_name}' from {action_label} role '{target_role_name}'."
                ),
                level=logging.WARNING,
            )
            raise ForbiddenError(
                "You cannot assign or manage an organisation role above your own authority.",
                code="INSUFFICIENT_ROLE_AUTHORITY",
            )

    def get_scoped_role_or_fail(
        self,
        *,
        role_name: str,
        expected_scope: RoleScopeType,
        actor_user_id: uuid.UUID,
        organisation_id: uuid.UUID | None = None,
        project_id: uuid.UUID | None = None,
    ) -> Role:
        """Resolve a catalog role by name and enforce its strict RBAC scope boundary."""
        role = self._rbac_repo.get_role_by_name(role_name)
        if role is None:
            raise NotFoundError("Requested role does not exist.", code="ROLE_NOT_FOUND")
        if role.scope_type != expected_scope.value:
            log_security_event(
                event_type="rbac.invalid_role_scope",
                outcome="denied",
                actor_user_id=str(actor_user_id),
                organisation_id=str(organisation_id) if organisation_id is not None else None,
                project_id=str(project_id) if project_id is not None else None,
                message=(
                    f"Rejected assignment of '{role.name}' (scope '{role.scope_type}') "
                    f"as '{expected_scope.value}' role."
                ),
                level=logging.WARNING,
            )
            raise BadRequestError(
                f"Role '{role.name}' cannot be assigned at {expected_scope.value} scope.",
                code="INVALID_ROLE_SCOPE",
            )
        return role

    def list_roles(self) -> RoleListResponse:
        """Return all defined platform, organisation, and project catalog roles."""
        roles = self._rbac_repo.list_roles()
        return RoleListResponse(items=[to_role_response(role) for role in roles])

    def assign_platform_role(
        self,
        *,
        target_user_id: uuid.UUID,
        role_name: str,
        acting_principal: AuthenticatedPrincipal,
    ) -> AssignRoleResponse:
        """Assign a strictly platform-scoped role to a target user account."""
        target_user = self._user_repo.get_by_id(target_user_id)
        if target_user is None:
            raise NotFoundError("Target user was not found.", code="USER_NOT_FOUND")

        role = self.get_scoped_role_or_fail(
            role_name=role_name,
            expected_scope=RoleScopeType.PLATFORM,
            actor_user_id=acting_principal.user.id,
        )

        assignment = self._rbac_repo.assign_role(
            user_id=target_user.id,
            role_id=role.id,
            assigned_by_id=acting_principal.user.id,
        )
        self._db.commit()

        log_security_event(
            event_type="rbac.role_assigned",
            outcome="success",
            actor_user_id=str(acting_principal.user.id),
            message=f"Assigned platform role '{role.name}' to user '{target_user.id}'.",
        )
        return AssignRoleResponse(
            user_id=target_user.id,
            role_name=role.name,
            scope_type=role.scope_type,
            assigned_at=assignment.assigned_at,
        )
