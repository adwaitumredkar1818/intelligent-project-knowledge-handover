"""ORM model package exporting canonical SQLAlchemy metadata for Alembic discovery."""

from app.db.base import Base
from app.models.audit import AuditLog
from app.models.auth import RefreshSession
from app.models.evidence import (
    EvidenceChunk,
    EvidenceContent,
    EvidenceItem,
    EvidencePageContent,
)
from app.models.integration import (
    OAuthState,
    ProjectSourceMapping,
    SourceAccessPolicy,
    SourceConnection,
    SourceSyncRun,
    UserSourceAuthorisation,
)
from app.models.job import BackgroundJob
from app.models.knowledge import (
    KnowledgeEvidenceLink,
    KnowledgeExtractionRun,
    KnowledgeItem,
)
from app.models.organisation import (
    Organisation,
    OrganisationInvitation,
    OrganisationMembership,
)
from app.models.project import Project, ProjectMembership, ProjectTransition
from app.models.rbac import Permission, Role, RolePermission, UserRole
from app.models.user import User
from app.models.vector_index import ProjectVectorIndex

__all__ = [
    "AuditLog",
    "BackgroundJob",
    "Base",
    "EvidenceChunk",
    "EvidenceContent",
    "EvidenceItem",
    "EvidencePageContent",
    "KnowledgeEvidenceLink",
    "KnowledgeExtractionRun",
    "KnowledgeItem",
    "OAuthState",
    "Organisation",
    "OrganisationInvitation",
    "OrganisationMembership",
    "Permission",
    "Project",
    "ProjectMembership",
    "ProjectSourceMapping",
    "ProjectTransition",
    "ProjectVectorIndex",
    "RefreshSession",
    "Role",
    "RolePermission",
    "SourceAccessPolicy",
    "SourceConnection",
    "SourceSyncRun",
    "User",
    "UserRole",
    "UserSourceAuthorisation",
]
