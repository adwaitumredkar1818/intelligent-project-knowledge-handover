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
        code="project.evidence.read",
        name="Read Project Evidence",
        description="Search, filter, and inspect evidence in an assigned project.",
        scope_type=RoleScopeType.PROJECT,
    ),
    PermissionSpec(
        code="project.evidence.upload",
        name="Upload Project Evidence",
        description="Upload PDF and DOCX documents to an assigned project.",
        scope_type=RoleScopeType.PROJECT,
    ),
    PermissionSpec(
        code="project.evidence.manage",
        name="Manage Project Evidence",
        description="Delete or trigger reprocessing of evidence items.",
        scope_type=RoleScopeType.PROJECT,
    ),
    PermissionSpec(
        code="project.transition.manage",
        name="Manage Project Transition",
        description="Configure departing member, successor, and capture scope.",
        scope_type=RoleScopeType.PROJECT,
    ),
    PermissionSpec(
        code="project.sources.manage",
        name="Manage Project Sources",
        description="Connect and map external sources (GitHub, Jira) within an assigned project.",
        scope_type=RoleScopeType.PROJECT,
    ),
    PermissionSpec(
        code="project.knowledge.review",
        name="Review Project Knowledge & Handover",
        description="Perform human verification reviews and designated handover approvals.",
        scope_type=RoleScopeType.PROJECT,
    ),
    # Handover Workspace permissions
    PermissionSpec(
        code="handover.read",
        name="Read Handover Packages",
        description="View handover cases, assembled packages, and readiness assessments.",
        scope_type=RoleScopeType.PROJECT,
    ),
    PermissionSpec(
        code="handover.create",
        name="Create Handover Cases",
        description="Create and configure handover cases.",
        scope_type=RoleScopeType.PROJECT,
    ),
    PermissionSpec(
        code="handover.edit",
        name="Edit Handover Cases",
        description="Update handover cases, checklist items, and section narrative notes.",
        scope_type=RoleScopeType.PROJECT,
    ),
    PermissionSpec(
        code="handover.compile",
        name="Compile Handover Packages",
        description="Trigger deterministic 8-domain assembly of package versions.",
        scope_type=RoleScopeType.PROJECT,
    ),
    PermissionSpec(
        code="handover.readiness.assess",
        name="Assess Handover Readiness",
        description="Run 9-category readiness evaluation across verified knowledge.",
        scope_type=RoleScopeType.PROJECT,
    ),
    PermissionSpec(
        code="handover.review",
        name="Review Handover Packages",
        description="Conduct human review and checklist item tracking.",
        scope_type=RoleScopeType.PROJECT,
    ),
    PermissionSpec(
        code="handover.approve",
        name="Approve Handover Packages",
        description="Issue official reviewer approval sign-off on package versions.",
        scope_type=RoleScopeType.PROJECT,
    ),
    PermissionSpec(
        code="handover.deliver",
        name="Deliver Handover Packages",
        description="Release and deliver approved package versions to successors.",
        scope_type=RoleScopeType.PROJECT,
    ),
    PermissionSpec(
        code="handover.acknowledge",
        name="Acknowledge Handover Packages",
        description="Successor receipt and acknowledgement sign-off.",
        scope_type=RoleScopeType.PROJECT,
    ),
    PermissionSpec(
        code="handover.transfer",
        name="Execute Ownership Transfer",
        description="Perform internal project ownership and responsibility transfers.",
        scope_type=RoleScopeType.PROJECT,
    ),
    PermissionSpec(
        code="handover.admin",
        name="Administrate Handover",
        description="Full administrative control over handover lifecycle and rollbacks.",
        scope_type=RoleScopeType.PROJECT,
    ),
    # Project Knowledge Assistant permissions
    PermissionSpec(
        code="assistant.read",
        name="Read Assistant Conversations",
        description="View conversations, message turns, citations, and answers.",
        scope_type=RoleScopeType.PROJECT,
    ),
    PermissionSpec(
        code="assistant.chat",
        name="Ask Assistant Questions",
        description="Create conversations and ask project questions with hybrid RAG.",
        scope_type=RoleScopeType.PROJECT,
    ),
    PermissionSpec(
        code="assistant.manage",
        name="Manage Assistant Conversations",
        description="Rename, archive, or delete user's own project conversations.",
        scope_type=RoleScopeType.PROJECT,
    ),
    PermissionSpec(
        code="assistant.feedback",
        name="Submit Assistant Feedback",
        description="Rate answers and report incorrect citations or information.",
        scope_type=RoleScopeType.PROJECT,
    ),
    PermissionSpec(
        code="assistant.admin",
        name="Administrate Assistant",
        description="View all retrieval diagnostics and manage assistant configuration.",
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
            "project.transition.manage",
            "project.sources.manage",
            "project.evidence.read",
            "project.evidence.upload",
            "project.evidence.manage",
            "project.evidence.contribute",
            "project.knowledge.review",
            "handover.read",
            "handover.create",
            "handover.edit",
            "handover.compile",
            "handover.readiness.assess",
            "handover.review",
            "handover.approve",
            "handover.deliver",
            "handover.acknowledge",
            "handover.transfer",
            "handover.admin",
            "assistant.read",
            "assistant.chat",
            "assistant.manage",
            "assistant.feedback",
            "assistant.admin",
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
            "project.transition.manage",
            "project.sources.manage",
            "project.evidence.read",
            "project.evidence.upload",
            "project.evidence.manage",
            "project.evidence.contribute",
            "project.knowledge.review",
            "handover.read",
            "handover.create",
            "handover.edit",
            "handover.compile",
            "handover.readiness.assess",
            "handover.review",
            "handover.approve",
            "handover.deliver",
            "handover.acknowledge",
            "handover.transfer",
            "handover.admin",
            "assistant.read",
            "assistant.chat",
            "assistant.manage",
            "assistant.feedback",
            "assistant.admin",
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
            "project.transition.manage",
            "project.sources.manage",
            "project.evidence.read",
            "project.evidence.upload",
            "project.evidence.manage",
            "handover.read",
            "handover.create",
            "handover.edit",
            "handover.compile",
            "handover.readiness.assess",
            "handover.review",
            "handover.deliver",
            "handover.transfer",
            "handover.admin",
            "assistant.read",
            "assistant.chat",
            "assistant.manage",
            "assistant.feedback",
            "assistant.admin",
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
            "project.evidence.read",
            "project.evidence.upload",
            "handover.read",
            "handover.edit",
            "handover.acknowledge",
            "assistant.read",
            "assistant.chat",
            "assistant.manage",
            "assistant.feedback",
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
            "project.evidence.read",
            "handover.read",
            "handover.review",
            "handover.approve",
            "handover.readiness.assess",
            "assistant.read",
            "assistant.chat",
            "assistant.manage",
            "assistant.feedback",
        ),
    ),
)
