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
    SUPABASE_STORAGE = "supabase_storage"


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
    RELATIONSHIP_RECONSTRUCTION = "relationship_reconstruction"
    HANDOVER_ASSEMBLY = "handover_assembly"
    HANDOVER_READINESS = "handover_readiness"
    HANDOVER_PDF_GENERATION = "handover_pdf_generation"
    HANDOVER_NARRATIVE_DRAFT = "handover_narrative_draft"


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
    """Eight canonical knowledge domains and Phase 2.6 extraction categories."""

    PROJECT_OVERVIEW_CONTEXT = "project_overview_context"
    DECISIONS_RATIONALE = "decisions_rationale"
    WORK_ITEMS = "work_items"
    RESPONSIBILITIES_OWNERSHIP = "responsibilities_ownership"
    TECHNICAL_ARCHITECTURE = "technical_architecture"
    BUGS_BLOCKERS_RISKS = "bugs_blockers_risks"
    DEPENDENCIES = "dependencies"
    OPERATIONAL_HISTORICAL = "operational_historical"
    # Canonical domain aliases
    WORK_PROGRESS = "work_progress"
    ARCHITECTURE_TECHNICAL = "architecture_technical"
    DEPENDENCIES_RELATIONSHIPS = "dependencies_relationships"
    RISKS_BLOCKERS_QUESTIONS = "risks_blockers_questions"


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
    DIRECT_SUPPORT = "direct_support"
    CORROBORATED = "corroborated"
    CORROBORATION = "corroboration"
    INTERPRETATION = "interpretation"
    CONTEXT = "context"
    UNCERTAIN = "uncertain"
    CONTRADICTION = "contradiction"


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


class EntityType(StrEnum):
    """Canonical project-scoped entity types for the knowledge graph."""

    # 19 Canonical Entities
    PROJECT = "project"
    PERSON = "person"
    ORGANISATION = "organisation"
    DECISION = "decision"
    REQUIREMENT = "requirement"
    TASK = "task"
    FEATURE = "feature"
    TECHNICAL_COMPONENT = "technical_component"
    ARCHITECTURE_COMPONENT = "architecture_component"
    REPOSITORY = "repository"
    PULL_REQUEST = "pull_request"
    COMMIT = "commit"
    ISSUE = "issue"
    DOCUMENT = "document"
    RISK = "risk"
    BLOCKER = "blocker"
    DEPENDENCY = "dependency"
    MILESTONE = "milestone"
    OPERATIONAL_PROCEDURE = "operational_procedure"

    # Backward-compatible aliases
    TEAM = "team"
    DISCUSSION = "discussion"
    DISCUSSION_THREAD = "discussion_thread"
    WORK_ITEM = "work_item"
    MEETING_NOTE = "meeting_note"
    COMPONENT = "component"
    BUG = "bug"
    PROCEDURE = "procedure"


class RelationshipType(StrEnum):
    """Canonical controlled relationship types across project entities."""

    # Part 6 Canonical Directed Types
    DECIDED_BY = "DECIDED_BY"
    INFLUENCED_BY = "INFLUENCED_BY"
    IMPLEMENTED_BY = "IMPLEMENTED_BY"
    SUPERSEDES = "SUPERSEDES"
    ARCHITECTURAL_DEPENDENCY = "ARCHITECTURAL_DEPENDENCY"
    AFFECTS_COMPONENT = "AFFECTS_COMPONENT"

    IMPLEMENTS = "IMPLEMENTS"
    FIXES = "FIXES"
    PART_OF = "PART_OF"
    BLOCKS = "BLOCKS"
    BLOCKED_BY = "BLOCKED_BY"
    DEPENDS_ON = "DEPENDS_ON"
    MERGED_IN = "MERGED_IN"
    BRANCHED_FROM = "BRANCHED_FROM"

    OWNS = "OWNS"
    MAINTAINS = "MAINTAINS"
    ASSIGNED_TO = "ASSIGNED_TO"
    AUTHORED_BY = "AUTHORED_BY"
    REVIEWED_BY = "REVIEWED_BY"
    REPORTED_BY = "REPORTED_BY"

    DISCUSSED_IN = "DISCUSSED_IN"
    DOCUMENTED_IN = "DOCUMENTED_IN"
    REFERENCES = "REFERENCES"
    DERIVED_FROM = "DERIVED_FROM"
    RESOLVED_BY = "RESOLVED_BY"

    INTRODUCES_RISK = "INTRODUCES_RISK"
    MITIGATES_RISK = "MITIGATES_RISK"
    CAUSED_BY = "CAUSED_BY"

    # Decision relationships
    DECISION_REFERENCED_IN_DISCUSSION = "DECISION_REFERENCED_IN_DISCUSSION"
    DECISION_RECORDED_IN_DOCUMENT = "DECISION_RECORDED_IN_DOCUMENT"
    DECISION_IMPLEMENTED_BY = "DECISION_IMPLEMENTED_BY"
    DECISION_AFFECTS_COMPONENT = "DECISION_AFFECTS_COMPONENT"
    DECISION_SUPERSEDES = "DECISION_SUPERSEDES"
    DECISION_CONFLICTS_WITH = "DECISION_CONFLICTS_WITH"

    # Work relationships
    WORK_ITEM_TRACKED_BY = "WORK_ITEM_TRACKED_BY"
    WORK_ITEM_IMPLEMENTED_BY = "WORK_ITEM_IMPLEMENTED_BY"
    WORK_ITEM_BLOCKED_BY = "WORK_ITEM_BLOCKED_BY"
    WORK_ITEM_DEPENDS_ON = "WORK_ITEM_DEPENDS_ON"
    WORK_ITEM_RELATED_TO = "WORK_ITEM_RELATED_TO"
    WORK_ITEM_ADDRESSED_BY_COMMIT = "WORK_ITEM_ADDRESSED_BY_COMMIT"

    # GitHub relationships
    COMMIT_BELONGS_TO_PULL_REQUEST = "COMMIT_BELONGS_TO_PULL_REQUEST"
    PULL_REQUEST_REFERENCES_ISSUE = "PULL_REQUEST_REFERENCES_ISSUE"
    PULL_REQUEST_MODIFIES_COMPONENT = "PULL_REQUEST_MODIFIES_COMPONENT"
    COMMIT_MODIFIES_COMPONENT = "COMMIT_MODIFIES_COMPONENT"
    PULL_REQUEST_REVIEWED_BY = "PULL_REQUEST_REVIEWED_BY"
    PULL_REQUEST_AUTHORED_BY = "PULL_REQUEST_AUTHORED_BY"

    # Person relationships
    PERSON_AUTHORED = "PERSON_AUTHORED"
    PERSON_REVIEWED = "PERSON_REVIEWED"
    PERSON_ASSIGNED_TO = "PERSON_ASSIGNED_TO"
    PERSON_RESPONSIBLE_FOR = "PERSON_RESPONSIBLE_FOR"
    PERSON_DISCUSSIONS_PARTICIPANT = "PERSON_DISCUSSIONS_PARTICIPANT"
    PERSON_CONTRIBUTED_TO = "PERSON_CONTRIBUTED_TO"

    # Technical relationships
    COMPONENT_DEPENDS_ON = "COMPONENT_DEPENDS_ON"
    COMPONENT_CALLS_COMPONENT = "COMPONENT_CALLS_COMPONENT"
    COMPONENT_USES_SERVICE = "COMPONENT_USES_SERVICE"
    COMPONENT_STORES_DATA_IN = "COMPONENT_STORES_DATA_IN"
    COMPONENT_EXPOSES_API = "COMPONENT_EXPOSES_API"
    DOCUMENT_DESCRIBES_COMPONENT = "DOCUMENT_DESCRIBES_COMPONENT"
    DOCUMENT_DESCRIBES_DECISION = "DOCUMENT_DESCRIBES_DECISION"

    # Risk and bug relationships
    RISK_AFFECTS_COMPONENT = "RISK_AFFECTS_COMPONENT"
    BUG_FOUND_IN_COMPONENT = "BUG_FOUND_IN_COMPONENT"
    RISK_BLOCKS_WORK_ITEM = "RISK_BLOCKS_WORK_ITEM"
    BUG_RELATED_TO_WORK_ITEM = "BUG_RELATED_TO_WORK_ITEM"
    RISK_DEPENDS_ON_EXTERNAL_FACTOR = "RISK_DEPENDS_ON_EXTERNAL_FACTOR"

    # Evidence relationships
    KNOWLEDGE_SUPPORTED_BY_EVIDENCE = "KNOWLEDGE_SUPPORTED_BY_EVIDENCE"
    KNOWLEDGE_CORROBORATED_BY = "KNOWLEDGE_CORROBORATED_BY"
    DOCUMENT_REFERENCES_EVIDENCE = "DOCUMENT_REFERENCES_EVIDENCE"
    DISCUSSION_REFERENCES_WORK_ITEM = "DISCUSSION_REFERENCES_WORK_ITEM"

    # Module C Canonical Lowercase Verbs & Aliases
    PROPOSED_BY = "proposed_by"
    APPROVED_BY = "approved_by"
    MOTIVATED_BY = "motivated_by"
    CONTRADICTS = "contradicts"
    REVISES = "revises"
    REQUIRES = "requires"
    USES = "uses"
    INTEGRATES_WITH = "integrates_with"
    EXTENDS = "extends"
    REPLACES = "replaces"
    DEPLOYED_AS = "deployed_as"
    CONFIGURED_BY = "configured_by"
    SUPPORTED_BY = "supported_by"
    MENTIONED_IN = "mentioned_in"
    CORROBORATED_BY = "corroborated_by"
    CONFLICTS_WITH = "conflicts_with"
    BELONGS_TO = "belongs_to"
    COMPLETED_IN = "completed_in"


class RelationshipBasis(StrEnum):
    """How the relationship was established."""

    EXPLICIT = "explicit"
    INFERRED = "inferred"
    HUMAN_CONFIRMED = "human_confirmed"


class RelationshipVerificationStatus(StrEnum):
    """Review lifecycle state for graph relationships."""

    CANDIDATE = "candidate"
    VERIFIED = "verified"
    REJECTED = "rejected"
    CONFLICTED = "conflicted"
    UNRESOLVED = "unresolved"
    STALE = "stale"


class EntityResolutionStatus(StrEnum):
    """Lifecycle and merge status of knowledge entities."""

    UNRESOLVED = "unresolved"
    CANONICAL = "canonical"
    MERGED = "merged"
    DISPUTED = "disputed"


class AliasResolutionStatus(StrEnum):
    """Review and resolution state for entity aliases."""

    UNRESOLVED = "unresolved"
    CANDIDATE = "candidate"
    ACCEPTED = "accepted"
    REJECTED = "rejected"


class IdentityPolicyBand(StrEnum):
    """Classification band determined by IdentityResolutionService."""

    AUTO_MERGE = "auto_merge"
    STRONG_CANDIDATE = "strong_candidate"
    MANUAL_REVIEW = "manual_review"
    SEPARATE = "separate"
    UNRESOLVED = "unresolved"


class IdentityCandidateStatus(StrEnum):
    """Review decision status on identity merge candidates."""

    PENDING = "pending"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    REVERTED = "reverted"


class TraceabilityCompletenessStatus(StrEnum):
    """Completeness state for Decision-to-Implementation chains."""

    COMPLETE = "complete"
    PARTIALLY_TRACED = "partially_traced"
    UNTRACED = "untraced"
    CONFLICTING = "conflicting"


class TimelinePrecision(StrEnum):
    """Precision tier for extracted project timeline events."""

    EXACT_DATETIME = "exact_datetime"
    DATE_ONLY = "date_only"
    MONTH_ONLY = "month_only"
    UNKNOWN = "unknown"


class TimelineOrigin(StrEnum):
    """Source origin of timestamp."""

    SOURCE_API = "source_api"
    SOURCE_CHANGELOG = "source_changelog"
    SOURCE_COMMIT = "source_commit"
    DOCUMENT_HEADER = "document_header"
    TEXT_DATE_MENTION = "text_date_mention"
    UNKNOWN = "unknown"


class RelationshipEvidenceRole(StrEnum):
    """Role that supporting evidence plays in establishing a relationship."""

    DIRECT_SUPPORT = "direct_support"
    CORROBORATION = "corroboration"
    CONTEXT = "context"
    CONTRADICTION = "contradiction"


class RelationshipRunStatus(StrEnum):
    """Lifecycle states for relationship reconstruction runs."""

    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


# =============================================================================
# Verification Center Enums (Module 3 / Validation Area)
# =============================================================================


class VerificationTargetType(StrEnum):
    """Polymorphic entity type undergoing verification."""

    KNOWLEDGE_ITEM = "knowledge_item"
    RELATIONSHIP = "relationship"


class VerificationCaseStatus(StrEnum):
    """Workflow state of a verification review case."""

    CANDIDATE = "candidate"
    PENDING_REVIEW = "pending_review"
    VERIFIED = "verified"
    CONFLICTED = "conflicted"
    REJECTED = "rejected"
    UNRESOLVED = "unresolved"
    ARCHIVED = "archived"


class MachineAssessmentStatus(StrEnum):
    """Deterministic & AI automated evaluation outcome."""

    PASSED = "passed"
    ISSUES_DETECTED = "issues_detected"
    CONFLICT_DETECTED = "conflict_detected"
    UNCERTAIN = "uncertain"
    INSUFFICIENT_EVIDENCE = "insufficient_evidence"


class VerificationPriority(StrEnum):
    """Urgency level for human review routing."""

    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class VerificationIssueType(StrEnum):
    """Taxonomy of detected flaws, missing evidence, or conflicts."""

    MISSING_EVIDENCE = "missing_evidence"
    INVALID_SOURCE_REFERENCE = "invalid_source_reference"
    UNSUPPORTED_CLAIM = "unsupported_claim"
    CONFLICTING_SOURCES = "conflicting_sources"
    INCONSISTENT_STATUS = "inconsistent_status"
    OUTDATED_INFORMATION = "outdated_information"
    STALE_KNOWLEDGE = "stale_knowledge"
    DUPLICATE_RECORD = "duplicate_record"
    UNCERTAIN_RELATIONSHIP = "uncertain_relationship"
    INVALID_ENTITY_MAPPING = "invalid_entity_mapping"
    INCORRECT_ATTRIBUTION = "incorrect_attribution"
    MISSING_SOURCE_CONTEXT = "missing_source_context"
    INSUFFICIENT_INFORMATION = "insufficient_information"
    INCOMPLETE_TRACEABILITY = "incomplete_traceability"


class VerificationSeverity(StrEnum):
    """Impact tier of a verification issue."""

    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


class IssueResolutionState(StrEnum):
    """Lifecycle state of an individual verification issue."""

    OPEN = "open"
    RESOLVED = "resolved"
    DISMISSED = "dismissed"
    ACKNOWLEDGED = "acknowledged"


class ConflictType(StrEnum):
    """Category of contradiction detected across sources."""

    STATUS_CONFLICT = "status_conflict"
    OWNERSHIP_CONFLICT = "ownership_conflict"
    DECISION_CONFLICT = "decision_conflict"
    TECHNICAL_CONFLICT = "technical_conflict"
    TEMPORAL_CONFLICT = "temporal_conflict"
    RELATIONSHIP_CONFLICT = "relationship_conflict"


class TemporalComparison(StrEnum):
    """Time-based precedence analysis between conflicting claims."""

    SIMULTANEOUS = "simultaneous"
    B_SUPERSEDES_A = "b_supersedes_a"
    A_SUPERSEDES_B = "a_supersedes_b"
    AMBIGUOUS = "ambiguous"


class ConflictResolutionState(StrEnum):
    """Resolution status for side-by-side contradiction records."""

    UNRESOLVED = "unresolved"
    RECONCILED = "reconciled"
    SUPERSEDED = "superseded"
    DISMISSED = "dismissed"


class ReviewActionType(StrEnum):
    """Atomic human review action performed on a verification case."""

    APPROVE = "approve"
    REJECT = "reject"
    EDIT = "edit"
    REQUEST_CONTEXT = "request_context"
    MARK_UNRESOLVED = "mark_unresolved"
    RETURN_FOR_CORRECTION = "return_for_correction"
    ASSIGN = "assign"


class ContextRequestStatus(StrEnum):
    """Lifecycle state of an outbound clarification query."""

    PENDING = "pending"
    RESPONDED = "responded"
    CANCELLED = "cancelled"
    EXPIRED = "expired"


# =============================================================================
# Handover Workspace Enums (Module 4 / Knowledge Transfer Area)
# =============================================================================


class HandoverCaseStatus(StrEnum):
    """Lifecycle state machine for a handover case (14 states)."""

    DRAFT = "draft"
    ASSEMBLING = "assembling"
    ASSEMBLED = "assembled"
    READINESS_PENDING = "readiness_pending"
    READINESS_ASSESSED = "readiness_assessed"
    REVIEW_PENDING = "review_pending"
    UNDER_REVIEW = "under_review"
    APPROVED = "approved"
    REJECTED = "rejected"
    DELIVERED = "delivered"
    ACKNOWLEDGED = "acknowledged"
    TRANSFERRED = "transferred"
    ARCHIVED = "archived"
    SUPERSEDED = "superseded"


class HandoverPackageSectionType(StrEnum):
    """Canonical 8-domain sections compiling verified handover knowledge."""

    DECISIONS_RATIONALE = "decisions_rationale"
    TECHNICAL_ARCHITECTURE = "technical_architecture"
    WORK_PROGRESS = "work_progress"
    RESPONSIBILITIES_OWNERSHIP = "responsibilities_ownership"
    DEPENDENCIES_RELATIONSHIPS = "dependencies_relationships"
    BUGS_BLOCKERS_RISKS = "bugs_blockers_risks"
    OPERATIONAL_HISTORICAL = "operational_historical"
    PROJECT_OVERVIEW_CONTEXT = "project_overview_context"


class HandoverReadinessCategory(StrEnum):
    """Nine evaluation categories determining handover package readiness."""

    EVIDENCE_COVERAGE = "evidence_coverage"
    VERIFICATION_COMPLETENESS = "verification_completeness"
    CONFLICT_RESOLUTION = "conflict_resolution"
    KNOWLEDGE_FRESHNESS = "knowledge_freshness"
    RELATIONSHIP_VALIDATION = "relationship_validation"
    RESPONSIBILITY_COVERAGE = "responsibility_coverage"
    RISK_ASSESSMENT = "risk_assessment"
    DEPENDENCY_MAPPING = "dependency_mapping"
    OVERALL_QUALITY = "overall_quality"


class ReadinessLevel(StrEnum):
    """Readiness scoring levels for handover package assessment."""

    NOT_READY = "not_ready"
    PARTIALLY_READY = "partially_ready"
    READY = "ready"
    READY_WITH_WARNINGS = "ready_with_warnings"


class ChecklistItemStatus(StrEnum):
    """Completion state of an individual handover checklist item."""

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    SKIPPED = "skipped"
    BLOCKED = "blocked"


class HandoverChecklistType(StrEnum):
    """Category classification of handover checklists."""

    PRE_HANDOVER = "pre_handover"
    POST_HANDOVER = "post_handover"
    KNOWLEDGE_TRANSFER = "knowledge_transfer"
    ACCESS_REVOCATION = "access_revocation"


class SignoffType(StrEnum):
    """Three mandatory human sign-off phases."""

    DEPARTING_SIGNOFF = "departing_signoff"
    REVIEWER_APPROVAL = "reviewer_approval"
    SUCCESSOR_ACKNOWLEDGEMENT = "successor_acknowledgement"


class SignoffDecision(StrEnum):
    """Decision outcomes for a sign-off or approval action."""

    APPROVED = "approved"
    REJECTED = "rejected"
    RETURNED_FOR_REVISION = "returned_for_revision"


class TransferStatus(StrEnum):
    """State tracking for a responsibility or ownership transfer."""

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    ROLLED_BACK = "rolled_back"
    FAILED = "failed"


class HandoverDeliveryMethod(StrEnum):
    """Delivery mechanism for the compiled handover package."""

    INTERNAL_DOWNLOAD = "internal_download"
    SECURE_LINK = "secure_link"


class OwnershipTransferType(StrEnum):
    """Category of ownership being transferred."""

    PROJECT_OWNERSHIP = "project_ownership"
    COMPONENT_OWNERSHIP = "component_ownership"
    RESPONSIBILITY_TRANSFER = "responsibility_transfer"


class HandoverLinkType(StrEnum):
    """Entity type linked to a handover package section."""

    KNOWLEDGE_ITEM = "knowledge_item"
    RELATIONSHIP = "relationship"
    EVIDENCE_ITEM = "evidence_item"


# ---------------------------------------------------------------------------
# Project Knowledge Assistant Enums
# ---------------------------------------------------------------------------


class AssistantSenderType(StrEnum):
    """Originator of a message turn in an assistant conversation."""

    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


class AssistantAnswerStatus(StrEnum):
    """Epistemic quality and completion state of an assistant answer."""

    ANSWERED = "answered"
    PARTIALLY_ANSWERED = "partially_answered"
    INSUFFICIENT_EVIDENCE = "insufficient_evidence"
    CONFLICTED_EVIDENCE = "conflicted_evidence"
    OUTDATED_EVIDENCE = "outdated_evidence"
    ACCESS_RESTRICTED = "access_restricted"
    UNSUPPORTED_QUERY = "unsupported_query"
    PROCESSING_ERROR = "processing_error"


class AssistantConversationStatus(StrEnum):
    """Lifecycle state of an assistant conversation."""

    ACTIVE = "active"
    ARCHIVED = "archived"


class AssistantQueryType(StrEnum):
    """Classification of user questions determining retrieval routing."""

    PROJECT_OVERVIEW = "project_overview"
    DECISION_RATIONALE = "decision_rationale"
    TECHNICAL_ARCHITECTURE = "technical_architecture"
    WORK_PROGRESS = "work_progress"
    RESPONSIBILITY_OWNERSHIP = "responsibility_ownership"
    DEPENDENCY_RELATIONSHIP = "dependency_relationship"
    RISK_PROBLEM = "risk_problem"
    OPERATIONAL_HISTORICAL = "operational_historical"
    TIMELINE_EVOLUTION = "timeline_evolution"
    COMPARATIVE = "comparative"
    MULTI_HOP = "multi_hop"
    KNOWLEDGE_GAP = "knowledge_gap"
    GENERAL = "general"


class AssistantFeedbackType(StrEnum):
    """User feedback classification on an assistant message."""

    HELPFUL = "helpful"
    UNHELPFUL = "unhelpful"
    INCORRECT_CITATION = "incorrect_citation"
    INACCURATE = "inaccurate"
    INCOMPLETE = "incomplete"




