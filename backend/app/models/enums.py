"""Enumerations for identity, sessions, and RBAC models."""

from __future__ import annotations

from enum import StrEnum


class UserStatus(StrEnum):
    """Lifecycle states for FastAPI-managed platform accounts."""

    ACTIVE = "active"
    DISABLED = "disabled"
    LOCKED = "locked"
    PENDING = "pending"


class RoleScopeType(StrEnum):
    """Separates platform permissions from future organisation and project scopes."""

    PLATFORM = "platform"
    ORGANISATION = "organisation"
    PROJECT = "project"


class RoleName(StrEnum):
    """Canonical baseline roles supporting future org/project expansion."""

    STANDARD_USER = "standard_user"
    PLATFORM_ADMIN = "platform_admin"
    ORG_OWNER = "org_owner"
    ORG_ADMIN = "org_admin"
    ORG_MEMBER = "org_member"
    PROJECT_MANAGER = "project_manager"
    PROJECT_MEMBER = "project_member"
    REVIEWER = "reviewer"


class OrganisationStatus(StrEnum):
    """Lifecycle states for multi-tenant organisations."""

    ACTIVE = "active"
    SUSPENDED = "suspended"
    ARCHIVED = "archived"


class OrganisationMembershipStatus(StrEnum):
    """Lifecycle states for a user's membership within an organisation."""

    ACTIVE = "active"
    SUSPENDED = "suspended"
    REMOVED = "removed"


class InvitationStatus(StrEnum):
    """Single-use lifecycle states for hashed organisation invitations."""

    PENDING = "pending"
    ACCEPTED = "accepted"
    REVOKED = "revoked"
    EXPIRED = "expired"


class ProjectStatus(StrEnum):
    """Lifecycle states for project workspaces."""

    PLANNING = "planning"
    ACTIVE = "active"
    ON_HOLD = "on_hold"
    COMPLETED = "completed"
    ARCHIVED = "archived"


class ProjectVisibility(StrEnum):
    """Discovery visibility boundaries within a parent organisation."""

    PRIVATE = "private"
    ORGANISATION = "organisation"


class ProjectMembershipStatus(StrEnum):
    """Lifecycle states for a user's membership within a project."""

    ACTIVE = "active"
    REMOVED = "removed"


class AuditOutcome(StrEnum):
    """Outcome classification persisted in immutable audit logs."""

    SUCCESS = "success"
    DENIED = "denied"
    ERROR = "error"


class RevocationReason(StrEnum):
    """Explicit reasons recorded when a refresh session is invalidated."""

    ROTATED = "rotated"
    LOGOUT = "logout"
    TOKEN_REUSE_DETECTED = "token_reuse_detected"  # noqa: S105
    EXPIRED = "expired"
    USER_DISABLED = "user_disabled"
    REVOKED_BY_USER = "revoked_by_user"
    ADMIN_REVOKED = "admin_revoked"


class SourceProvider(StrEnum):
    """Supported external and local evidence sources."""

    GITHUB = "github"
    JIRA = "jira"
    SLACK = "slack"
    PDF = "pdf"
    DOCX = "docx"


class SourceConnectionStatus(StrEnum):
    """Lifecycle states for external OAuth connections."""

    CONNECTED = "connected"
    NEEDS_REAUTH = "needs_reauth"
    DISCONNECTED = "disconnected"
    ERROR = "error"


class SyncStatus(StrEnum):
    """Synchronization states for mapped external resources."""

    IDLE = "idle"
    SYNCING = "syncing"
    COMPLETED = "completed"
    FAILED = "failed"


class EvidenceProcessingStatus(StrEnum):
    """Processing and extraction lifecycle states for evidence items."""

    PENDING = "pending"
    PROCESSING = "processing"
    EXTRACTED = "extracted"
    INDEXED = "indexed"
    FAILED = "failed"


class EvidenceVerificationStatus(StrEnum):
    """Verification queue states for evidence and knowledge claims."""

    UNVERIFIED = "unverified"
    CANDIDATE = "candidate"
    VERIFIED = "verified"
    CONFLICTED = "conflicted"
    REJECTED = "rejected"


class JobStatus(StrEnum):
    """Background worker job execution states."""

    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"

