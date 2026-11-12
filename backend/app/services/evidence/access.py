"""Source-level ACL service enforcing 'Project Membership != Source Access'."""

from __future__ import annotations

import logging
import uuid

from app.core.exceptions import ForbiddenError
from app.models.enums import SourceProvider
from app.models.evidence import EvidenceItem, SourceConnection

logger = logging.getLogger("app.security.source_acl")


class SourceAclService:
    """Enforces strict source-level authorization independent of project membership.

    Critical Rule:
    A user being a member of a project does NOT grant access to private external sources
    (GitHub repos, Jira boards) connected by another user unless explicitly shared.
    """

    @staticmethod
    def can_access_connection(
        *,
        user_id: uuid.UUID,
        connection: SourceConnection | None,
    ) -> bool:
        """Evaluate whether a user has authorized access to an external source connection."""
        if connection is None:
            return False

        # 1. Connecting owner always retains access
        if connection.connected_by_id == user_id:
            return True

        # 2. Check if shared in connection scopes/metadata
        scopes = connection.scopes or []
        if "shared:organisation" in scopes or "shared:project" in scopes:
            return True

        # 3. Whitelisted delegated user IDs in raw_metadata/scopes
        if f"user:{user_id}" in scopes:
            return True

        return False

    def can_access_evidence_item(
        self,
        *,
        user_id: uuid.UUID,
        item: EvidenceItem,
    ) -> bool:
        """Determine whether a project member is permitted to read this specific evidence item."""
        # Standalone uploaded documents (PDF/DOCX) are accessible
        # to all verified project members with project.evidence.read permission
        if item.provider in (SourceProvider.PDF.value, SourceProvider.DOCX.value):
            return True

        # External sources (github, jira, slack) require strict connection-level ACL verification
        if item.source_mapping is None or item.source_mapping.source_connection is None:
            logger.warning(
                "Denied access to evidence %s because source connection is unlinked (fail closed)",
                item.id,
            )
            return False

        return self.can_access_connection(
            user_id=user_id,
            connection=item.source_mapping.source_connection,
        )

    def enforce_evidence_item_access(
        self,
        *,
        user_id: uuid.UUID,
        item: EvidenceItem,
    ) -> None:
        """Raise ForbiddenError if caller lacks permission to access this evidence item."""
        if not self.can_access_evidence_item(user_id=user_id, item=item):
            logger.warning(
                "Access denied: user %s attempted to access private evidence %s from source %s",
                user_id,
                item.id,
                item.provider,
            )
            raise ForbiddenError(
                f"You do not have permission to access records from this external "
                f"'{item.provider}' source. Source access must be granted separately "
                f"from project membership.",
                code="SOURCE_ACCESS_DENIED",
            )
