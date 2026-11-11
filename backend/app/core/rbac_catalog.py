"""Canonical RBAC catalog definitions separating platform, organisation, and project scopes."""

from __future__ import annotations

import uuid
from dataclasses import dataclass

from app.models.enums import RoleName, RoleScopeType

_RBAC_UUID_NAMESPACE = uuid.UUID("6b7c84d4-2c1b-4c6f-9c2a-9a3e4f502100")


def deterministic_rbac_id(kind: str, key: str) -> uuid.UUID:
    """Produce deterministic UUIDs for built-in roles and permissions."""
    return uuid.uuid5(_RBAC_UUID_NAMESPACE, f"{kind}:{key}")


@dataclass(frozen=True, slots=True)
class PermissionSpec:
    """Definition of a canonical platform or scoped permission."""

    code: str
    name: str
    description: str
    scope_type: RoleScopeType

    @property
    def id(self) -> uuid.UUID:
        return deterministic_rbac_id("permission", self.code)


@dataclass(frozen=True, slots=True)
class RoleSpec:
    """Definition of a canonical built-in RBAC role."""

    name: str
    display_name: str
    description: str
    scope_type: RoleScopeType
    permission_codes: tuple[str, ...]

    @property
    def id(self) -> uuid.UUID:
        return deterministic_rbac_id("role", self.name)


SYSTEM_PERMISSIONS: tuple[PermissionSpec, ...] = (
    # Platform self-service account permissions
    PermissionSpec(
        code="account.profile.read",
        name="Read Own Profile",
        description="Read authenticated user's own account profile.",
        scope_type=RoleScopeType.PLATFORM,
    ),
    PermissionSpec(
        code="account.sessions.read",
        name="Read Own Sessions",
        description="List authenticated user's own refresh sessions.",
        scope_type=RoleScopeType.PLATFORM,
    ),
    PermissionSpec(
        code="account.sessions.revoke",
        name="Revoke Own Sessions",
        description="Revoke authenticated user's own refresh sessions.",
        scope_type=RoleScopeType.PLATFORM,
    ),
    # Platform administration permissions
    PermissionSpec(
        code="platform.users.read",
        name="Read Platform Users",
        description="List and inspect platform user identities.",
        scope_type=RoleScopeType.PLATFORM,
    ),
    PermissionSpec(
        code="platform.users.manage",
        name="Manage Platform Users",
        description="Activate or disable platform user accounts.",
        scope_type=RoleScopeType.PLATFORM,
    ),
    PermissionSpec(
        code="platform.roles.read",
        name="Read Roles & Permissions",
        description="View defined RBAC roles and permission mappings.",
        scope_type=RoleScopeType.PLATFORM,
    ),
    PermissionSpec(
        code="platform.roles.manage",
        name="Manage Platform Roles",
        description="Assign or revoke platform-scoped roles on user accounts.",
        scope_type=RoleScopeType.PLATFORM,
    ),
    PermissionSpec(
        code="platform.sessions.manage",
        name="Manage Platform Sessions",
        description="Administratively revoke active user refresh sessions.",
        scope_type=RoleScopeType.PLATFORM,
    ),
    PermissionSpec(
        code="platform.organisations.create",
        name="Create Organisations",
        description="Create new multi-tenant organisations owned by the creator.",
        scope_type=RoleScopeType.PLATFORM,
    ),
    # Organisation permissions (Phase 2.3+)
    PermissionSpec(
        code="organisation.read",
        name="Read Organisation",
        description="Read organisation metadata within an assigned organisation.",
        scope_type=RoleScopeType.ORGANISATION,
    ),
    PermissionSpec(
        code="organisation.manage",
        name="Manage Organisation",
        description="Configure and archive an assigned organisation.",
        scope_type=RoleScopeType.ORGANISATION,
    ),
    PermissionSpec(
        code="organisation.members.read",
        name="Read Organisation Members",
        description="View active members and roles within an assigned organisation.",
        scope_type=RoleScopeType.ORGANISATION,
    ),
    PermissionSpec(
        code="organisation.members.manage",
        name="Manage Organisation Members",
        description="Update organisation roles and remove members within an organisation.",
        scope_type=RoleScopeType.ORGANISATION,
    ),
    PermissionSpec(
        code="organisation.invitations.read",
        name="Read Organisation Invitations",
        description="List pending and historical invitations within an organisation.",
        scope_type=RoleScopeType.ORGANISATION,
    ),
    PermissionSpec(
        code="organisation.invitations.manage",
        name="Manage Organisation Invitations",
        description="Issue and revoke invitations for permitted roles within an organisation.",
        scope_type=RoleScopeType.ORGANISATION,
    ),
    PermissionSpec(
        code="organisation.projects.create",
        name="Create Organisation Projects",
        description="Create project workspaces within an assigned organisation.",
        scope_type=RoleScopeType.ORGANISATION,
    ),
    PermissionSpec(
        code="organisation.audit.read",
        name="Read Organisation Audit Events",
        description="Inspect sanitised audit events scoped to an assigned organisation.",
        scope_type=RoleScopeType.ORGANISATION,
    ),
    # Project permissions (Phase 2.3+)
    PermissionSpec(
        code="project.read",
        name="Read Project",
        description="Read permitted project resources within an assigned project.",
        scope_type=RoleScopeType.PROJECT,
    ),
    PermissionSpec(
        code="project.manage",
        name="Manage Project",
        description="Configure, transition lifecycle status, and archive an assigned project.",
        scope_type=RoleScopeType.PROJECT,
    ),
    PermissionSpec(
        code="project.members.read",
        name="Read Project Members",
        description="List active project members and their assigned project roles.",
        scope_type=RoleScopeType.PROJECT,
    ),
    PermissionSpec(
        code="project.members.manage",
        name="Manage Project Members",
        description="Assign and update project-scoped memberships for organisation members.",
        scope_type=RoleScopeType.PROJECT,
    ),
    PermissionSpec(
        code="project.evidence.contribute",
        name="Contribute Project Evidence",
        description="Upload documents and sync authorised sources within an assigned project.",
        scope_type=RoleScopeType.PROJECT,
    ),
    PermissionSpec(
        code="project.knowledge.review",
        name="Review Project Knowledge & Handover",
        description="Perform human verification reviews and designated handover approvals.",
        scope_type=RoleScopeType.PROJECT,
    ),
)

KNOWN_PERMISSION_CODES: frozenset[str] = frozenset(spec.code for spec in SYSTEM_PERMISSIONS)
PLATFORM_PERMISSION_CODES: frozenset[str] = frozenset(
    spec.code for spec in SYSTEM_PERMISSIONS if spec.scope_type == RoleScopeType.PLATFORM
)
ORGANISATION_PERMISSION_CODES: frozenset[str] = frozenset(
    spec.code for spec in SYSTEM_PERMISSIONS if spec.scope_type == RoleScopeType.ORGANISATION
)
PROJECT_PERMISSION_CODES: frozenset[str] = frozenset(
    spec.code for spec in SYSTEM_PERMISSIONS if spec.scope_type == RoleScopeType.PROJECT
)

ORG_ROLE_RANK: dict[str, int] = {
    RoleName.ORG_MEMBER.value: 1,
    RoleName.ORG_ADMIN.value: 2,
    RoleName.ORG_OWNER.value: 3,
}

SYSTEM_ROLES: tuple[RoleSpec, ...] = (
    RoleSpec(
        name=RoleName.STANDARD_USER.value,
        display_name="Standard Platform User",
        description="Default authenticated user with self-account access and org creation.",
        scope_type=RoleScopeType.PLATFORM,
        permission_codes=(
            "account.profile.read",
            "account.sessions.read",
            "account.sessions.revoke",
            "platform.organisations.create",
        ),
    ),
    RoleSpec(
        name=RoleName.PLATFORM_ADMIN.value,
        display_name="Platform Administrator",
        description="Manages platform accounts, platform roles, and active platform sessions.",
        scope_type=RoleScopeType.PLATFORM,
        permission_codes=(
            "account.profile.read",
            "account.sessions.read",
            "account.sessions.revoke",
            "platform.organisations.create",
            "platform.users.read",
            "platform.users.manage",
            "platform.roles.read",
            "platform.roles.manage",
            "platform.sessions.manage",
        ),
    ),
    RoleSpec(
        name=RoleName.ORG_OWNER.value,
        display_name="Organisation Owner",
        description="Full governance within an organisation and its projects.",
        scope_type=RoleScopeType.ORGANISATION,
        permission_codes=(
            "organisation.read",
            "organisation.manage",
            "organisation.members.read",
            "organisation.members.manage",
            "organisation.invitations.read",
            "organisation.invitations.manage",
            "organisation.projects.create",
            "organisation.audit.read",
            "project.read",
            "project.manage",
            "project.members.read",
            "project.members.manage",
        ),
    ),
    RoleSpec(
        name=RoleName.ORG_ADMIN.value,
        display_name="Organisation Administrator",
        description="Administers members, invitations, and projects within one organisation.",
        scope_type=RoleScopeType.ORGANISATION,
        permission_codes=(
            "organisation.read",
            "organisation.members.read",
            "organisation.members.manage",
            "organisation.invitations.read",
            "organisation.invitations.manage",
            "organisation.projects.create",
            "organisation.audit.read",
            "project.read",
            "project.manage",
            "project.members.read",
            "project.members.manage",
        ),
    ),
    RoleSpec(
        name=RoleName.ORG_MEMBER.value,
        display_name="Organisation Member",
        description="Standard organisation member accessing permitted organisation resources.",
        scope_type=RoleScopeType.ORGANISATION,
        permission_codes=(
            "organisation.read",
            "organisation.members.read",
        ),
    ),
    RoleSpec(
        name=RoleName.PROJECT_MANAGER.value,
        display_name="Project Manager",
        description="Manages an assigned project workspace and its project memberships.",
        scope_type=RoleScopeType.PROJECT,
        permission_codes=(
            "project.read",
            "project.manage",
            "project.members.read",
            "project.members.manage",
            "project.evidence.contribute",
        ),
    ),
    RoleSpec(
        name=RoleName.PROJECT_MEMBER.value,
        display_name="Project Member",
        description="Contributes evidence and curated knowledge inside assigned projects.",
        scope_type=RoleScopeType.PROJECT,
        permission_codes=(
            "project.read",
            "project.members.read",
            "project.evidence.contribute",
        ),
    ),
    RoleSpec(
        name=RoleName.REVIEWER.value,
        display_name="Reviewer",
        description="Verifies reconstructed knowledge and issues designated handover approvals.",
        scope_type=RoleScopeType.PROJECT,
        permission_codes=(
            "project.read",
            "project.members.read",
            "project.knowledge.review",
        ),
    ),
)
