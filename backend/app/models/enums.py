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


class EvidenceSourceType(StrEnum):
    """Canonical origin platforms/channels supported by the unified evidence ledger."""

    DOCUMENT_UPLOAD = "document_upload"
    GITHUB = "github"
    JIRA = "jira"
    SLACK = "slack"
    MANUAL_NOTE = "manual_note"


class EvidenceCategory(StrEnum):
    """Granular artefact categories across uploaded files and future connectors."""

    PDF_DOCUMENT = "pdf_document"
    DOCX_DOCUMENT = "docx_document"
    ISSUE = "issue"
    PULL_REQUEST = "pull_request"
    COMMIT = "commit"
    DISCUSSION_THREAD = "discussion_thread"
    DESIGN_DOCUMENT = "design_document"
    OTHER = "other"


class EvidenceProcessingStatus(StrEnum):
    """Processing lifecycle states tracking raw ingestion through extraction."""

    PENDING = "pending"
    QUEUED = "queued"
    PROCESSING = "processing"
    EXTRACTED = "extracted"
    PARTIALLY_EXTRACTED = "partially_extracted"
    FAILED = "failed"
    DELETED = "deleted"


class DocumentExtractionMethod(StrEnum):
    """Extraction pipeline strategy used to extract content from a document."""

    PYMUPDF_TEXT = "pymupdf_text"
    GLM_OCR = "glm_ocr"
    PYMUPDF_AND_OCR = "pymupdf_and_ocr"
    PYTHON_DOCX = "python_docx"


class PageExtractionOutcome(StrEnum):
    """Per-page extraction outcomes recording digital text vs OCR completeness."""

    DIGITAL_TEXT = "digital_text"
    OCR_SUCCEEDED = "ocr_succeeded"
    OCR_TRUNCATED = "ocr_truncated"
    OCR_FAILED = "ocr_failed"
    EMPTY = "empty"
    SKIPPED_LIMIT = "skipped_limit"


class StorageProvider(StrEnum):
    """Storage backend providers for persisted encrypted artefacts."""

    LOCAL_ENCRYPTED = "local_encrypted"


class BackgroundJobType(StrEnum):
    """PostgreSQL-backed asynchronous job categories."""

    DOCUMENT_INGESTION = "document_ingestion"
    SOURCE_SYNC = "source_sync"
    EVIDENCE_CHUNKING = "evidence_chunking"
    EVIDENCE_EMBEDDING = "evidence_embedding"
    EVIDENCE_INDEXING = "evidence_indexing"
    EVIDENCE_REINDEXING = "evidence_reindexing"
    EVIDENCE_INDEX_CLEANUP = "evidence_index_cleanup"
    KNOWLEDGE_RECONSTRUCTION = "knowledge_reconstruction"


class EvidenceIndexingStatus(StrEnum):
    """Chunking, FTS indexing, and ChromaDB vector lifecycle state on EvidenceItem."""

    NOT_INDEXED = "not_indexed"
    QUEUED = "queued"
    PROCESSING = "processing"
    INDEXED = "indexed"
    PARTIALLY_INDEXED = "partially_indexed"
    FAILED = "failed"
    DELETED = "deleted"


class ChunkIndexingStatus(StrEnum):
    """Lifecycle states tracked per canonical PostgreSQL EvidenceChunk row."""

    CHUNKED = "chunked"
    EMBEDDED = "embedded"
    INDEXED = "indexed"
    PARTIALLY_INDEXED = "partially_indexed"
    FAILED = "failed"


class EvidenceChunkType(StrEnum):
    """Structural classification preserving document, issue, PR, and comment boundaries."""

    DOCUMENT_SECTION = "document_section"
    OCR_PAGE = "ocr_page"
    TABLE_SEGMENT = "table_segment"
    REPOSITORY_OVERVIEW = "repository_overview"
    ISSUE_BODY = "issue_body"
    ISSUE_COMMENT = "issue_comment"
    ISSUE_HIERARCHY = "issue_hierarchy"
    ISSUE_ACTIVITY = "issue_activity"
    PR_BODY = "pr_body"
    PR_REVIEW = "pr_review"
    PR_COMMENT = "pr_comment"
    PR_CHANGED_FILES = "pr_changed_files"
    COMMIT_MESSAGE = "commit_message"
    DOCUMENTATION = "documentation"
    DISCUSSION_THREAD = "discussion_thread"
    JIRA_PROJECT = "jira_project"
    TEXT_SEGMENT = "text_segment"


class SearchMode(StrEnum):
    """Supported hybrid retrieval execution modes."""

    KEYWORD = "keyword"
    SEMANTIC = "semantic"
    HYBRID = "hybrid"


class BackgroundJobStatus(StrEnum):
    """PostgreSQL-backed background worker lifecycle states."""

    QUEUED = "queued"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ConnectorExtractionMethod(StrEnum):
    """Source API extraction strategies stored cleanly alongside document methods."""

    GITHUB_API = "github_api"
    JIRA_API = "jira_api"


class IntegrationProvider(StrEnum):
    """Authorised external source providers supported in Phase 2.4B."""

    GITHUB = "github"
    JIRA = "jira"


class SourceConnectionStatus(StrEnum):
    """Lifecycle states for an organisation-scoped delegated source connection."""

    PENDING_AUTH = "pending_auth"
    ACTIVE = "active"
    REAUTH_REQUIRED = "reauth_required"
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


class UserSourceAuthorisationStatus(StrEnum):
    """Lifecycle states for per-user delegated OAuth credentials."""

    ACTIVE = "active"
    EXPIRED = "expired"
    REVOKED = "revoked"
    ERROR = "error"


class SourceVisibilityPolicy(StrEnum):
    """Access visibility boundaries enforced before evidence inspection or retrieval."""

    RESTRICTED_FAIL_CLOSED = "restricted_fail_closed"
    EXPLICIT_USER_GRANTS = "explicit_user_grants"
    VERIFIED_SOURCE_ACL = "verified_source_acl"
    PROJECT_MEMBERS_VERIFIED = "project_members_verified"


class SourcePermissionVerificationStatus(StrEnum):
    """Verification states tracking whether external ACL visibility was confirmed."""

    VERIFIED = "verified"
    UNVERIFIED = "unverified"
    REVOKED = "revoked"
    FAILED = "failed"


class ProjectSourceMappingStatus(StrEnum):
    """Lifecycle states binding one external repository or Jira project to a project workspace."""

    ACTIVE = "active"
    DISABLED = "disabled"
    DISCONNECTED = "disconnected"
    ERROR = "error"


class SourceSyncMode(StrEnum):
    """Execution mode for connector ingestion jobs."""

    INITIAL = "initial"
    INCREMENTAL = "incremental"
    MANUAL = "manual"


class SourceSyncRunStatus(StrEnum):
    """Outcome states persisted per external connector sync attempt."""

    QUEUED = "queued"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    PARTIAL = "partial"
    FAILED = "failed"
    CANCELLED = "cancelled"


class KnowledgeCategory(StrEnum):
    """Six canonical knowledge extraction categories implemented in Phase 2.6."""

    DECISIONS_RATIONALE = "decisions_rationale"
    WORK_ITEMS = "work_items"
    RESPONSIBILITIES_OWNERSHIP = "responsibilities_ownership"
    TECHNICAL_ARCHITECTURE = "technical_architecture"
    BUGS_BLOCKERS_RISKS = "bugs_blockers_risks"
    DEPENDENCIES = "dependencies"


class EpistemicStatus(StrEnum):
    """Four-tier epistemic provenance boundaries (LLM never emits human_verified)."""

    EXTRACTED = "extracted"
    AI_INTERPRETED = "ai_interpreted"
    HUMAN_VERIFIED = "human_verified"


class KnowledgeReviewStatus(StrEnum):
    """Review lifecycle states (always initialized as `pending_review` in Phase 2.6)."""

    PENDING_REVIEW = "pending_review"
    APPROVED = "approved"
    REJECTED = "rejected"
    NEEDS_CLARIFICATION = "needs_clarification"


class SupportClassification(StrEnum):
    """How strongly supporting evidence backs an extracted knowledge item."""

    DIRECT = "direct"
    CORROBORATED = "corroborated"
    INTERPRETATION = "interpretation"
    UNCERTAIN = "uncertain"


class ExtractionRunScope(StrEnum):
    """Execution scope of a Phase 2.6 knowledge extraction run."""

    EVIDENCE = "evidence"
    PROJECT = "project"


class ExtractionRunStatus(StrEnum):
    """Lifecycle states for PostgreSQL-tracked knowledge extraction runs."""

    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    PARTIALLY_COMPLETED = "partially_completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ConfidenceLevel(StrEnum):
    """Non-calibrated explicit confidence indicators separated from numerical scores."""

    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
