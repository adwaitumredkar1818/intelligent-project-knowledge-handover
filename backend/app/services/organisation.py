"""Service layer for multi-tenant organisations, memberships, and hashed invitations."""

from __future__ import annotations

import logging
import uuid
from datetime import timedelta

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.core.exceptions import (
    BadRequestError,
    ConflictError,
    ForbiddenError,
    GoneError,
    NotFoundError,
    ServiceUnavailableError,
)
from app.core.rbac_catalog import ORG_ROLE_RANK
from app.core.security import (
    derive_slug_from_name,
    ensure_utc,
    generate_opaque_token,
    hash_opaque_token,
    utc_now,
)
from app.models.enums import (
    AuditOutcome,
    InvitationStatus,
    OrganisationMembershipStatus,
    OrganisationStatus,
    RoleName,
    RoleScopeType,
)
from app.models.organisation import (
    Organisation,
    OrganisationInvitation,
    OrganisationMembership,
)
from app.repositories.organisation import OrganisationRepository
from app.repositories.project import ProjectRepository
from app.repositories.rbac import RbacRepository
from app.repositories.user import UserRepository
from app.schemas.organisation import (
    AcceptInvitationResponse,
    CreateInvitationRequest,
    CreateInvitationResponse,
    CreateOrganisationRequest,
    InvitationListResponse,
    InvitationSummaryResponse,
    OrganisationListResponse,
    OrganisationMemberListResponse,
    OrganisationMemberResponse,
    OrganisationResponse,
    OrganisationSummaryResponse,
    RemoveMembershipResponse,
    UpdateOrganisationMemberRoleRequest,
    UpdateOrganisationRequest,
)
from app.services.audit import AuditService
from app.services.rbac import AuthenticatedPrincipal, OrganisationContext, RbacService


def _build_organisation_summary(
    org: Organisation,
    *,
    my_role: str,
) -> OrganisationSummaryResponse:
    return OrganisationSummaryResponse(
        id=org.id,
        name=org.name,
        slug=org.slug,
        description=org.description,
        status=org.status,
        created_by_id=org.created_by_id,
        my_role=my_role,
        created_at=org.created_at,
        updated_at=org.updated_at,
        archived_at=org.archived_at,
    )


def _build_member_response(membership: OrganisationMembership) -> OrganisationMemberResponse:
    return OrganisationMemberResponse(
        id=membership.id,
        organisation_id=membership.organisation_id,
        user_id=membership.user_id,
        full_name=membership.user.full_name,
        email=membership.user.email,
        role_name=membership.role.name,
        status=membership.status,
        joined_at=membership.joined_at,
        invited_by_id=membership.invited_by_id,
        created_at=membership.created_at,
        updated_at=membership.updated_at,
    )


def _build_invitation_summary(invitation: OrganisationInvitation) -> InvitationSummaryResponse:
    return InvitationSummaryResponse(
        id=invitation.id,
        organisation_id=invitation.organisation_id,
        email=invitation.email,
        role_name=invitation.role.name,
        status=invitation.status,
        invited_by_id=invitation.invited_by_id,
        expires_at=invitation.expires_at,
        accepted_at=invitation.accepted_at,
        revoked_at=invitation.revoked_at,
        created_at=invitation.created_at,
    )


class OrganisationService:
    """Orchestrates organisation lifecycle, member RBAC, and invitation workflows."""

    def __init__(
        self,
        *,
        settings: Settings,
        db_session: Session,
        org_repository: OrganisationRepository,
        project_repository: ProjectRepository,
        rbac_repository: RbacRepository,
        user_repository: UserRepository,
        rbac_service: RbacService,
        audit_service: AuditService,
    ) -> None:
        self._settings = settings
        self._db = db_session
        self._org_repo = org_repository
        self._project_repo = project_repository
        self._rbac_repo = rbac_repository
        self._user_repo = user_repository
        self._rbac_service = rbac_service
        self._audit = audit_service

    def _require_active_organisation(self, organisation: Organisation) -> None:
        if organisation.status != OrganisationStatus.ACTIVE.value:
            raise ConflictError(
                f"Organisation is currently '{organisation.status}' and cannot be modified.",
                code="ORGANISATION_NOT_ACTIVE",
            )

    def _resolve_slug(self, explicit_slug: str | None, name: str) -> str:
        if explicit_slug is not None:
            return explicit_slug
        try:
            return derive_slug_from_name(name, field_label="Organisation slug")
        except ValueError as exc:
            raise BadRequestError(str(exc), code="INVALID_SLUG") from exc

    def create_organisation(
        self,
        *,
        payload: CreateOrganisationRequest,
        acting_principal: AuthenticatedPrincipal,
    ) -> OrganisationResponse:
        """Create a new organisation and bind the creator as initial `org_owner`."""
        slug = self._resolve_slug(payload.slug, payload.name)
        if self._org_repo.get_by_slug(slug) is not None:
            raise ConflictError(
                "An organisation with this slug already exists.",
                code="ORGANISATION_SLUG_ALREADY_EXISTS",
            )

        owner_role = self._rbac_repo.get_role_by_name(RoleName.ORG_OWNER.value)
        if owner_role is None:
            raise ServiceUnavailableError(
                "Organisation RBAC roles are not initialised.",
                code="RBAC_CATALOG_NOT_READY",
            )

        try:
            org = self._org_repo.create(
                name=payload.name,
                slug=slug,
                description=payload.description,
                created_by_id=acting_principal.user.id,
            )
            self._org_repo.create_membership(
                organisation_id=org.id,
                user_id=acting_principal.user.id,
                role_id=owner_role.id,
                invited_by_id=None,
                joined_at=utc_now(),
            )
            self._audit.record_event(
                event_type="organisation.created",
                resource_type="organisation",
                actor_user_id=acting_principal.user.id,
                organisation_id=org.id,
                resource_id=str(org.id),
                metadata={"slug": org.slug, "initial_role": owner_role.name},
                message=f"Created organisation '{org.slug}'.",
            )
            self._audit.record_event(
                event_type="organisation.member.added",
                resource_type="organisation_membership",
                actor_user_id=acting_principal.user.id,
                organisation_id=org.id,
                resource_id=str(acting_principal.user.id),
                metadata={"role_name": owner_role.name, "via": "organisation_creation"},
                message=f"Assigned creator as '{owner_role.name}' in organisation '{org.slug}'.",
            )
            self._db.commit()
        except IntegrityError as exc:
            self._db.rollback()
            raise ConflictError(
                "An organisation with this slug already exists.",
                code="ORGANISATION_SLUG_ALREADY_EXISTS",
            ) from exc

        ctx = self._rbac_service.resolve_organisation_context(
            organisation_id=org.id,
            principal=acting_principal,
        )
        return self.get_organisation_detail(ctx)

    def list_my_organisations(
        self,
        *,
        principal: AuthenticatedPrincipal,
        status: str | None = None,
        search: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> OrganisationListResponse:
        """List only organisations where the caller holds an active membership."""
        rows, total = self._org_repo.list_for_user(
            user_id=principal.user.id,
            status=status,
            search=search,
            limit=limit,
            offset=offset,
        )
        items = [
            _build_organisation_summary(org, my_role=membership.role.name)
            for org, membership in rows
        ]
        return OrganisationListResponse(items=items, total=total)

    def get_organisation_detail(self, ctx: OrganisationContext) -> OrganisationResponse:
        """Return safe organisation metadata and caller's resolved org permissions."""
        org = ctx.organisation
        return OrganisationResponse(
            id=org.id,
            name=org.name,
            slug=org.slug,
            description=org.description,
            status=org.status,
            created_by_id=org.created_by_id,
            my_role=ctx.role.name,
            my_permissions=sorted(ctx.permissions),
            created_at=org.created_at,
            updated_at=org.updated_at,
            archived_at=org.archived_at,
        )

    def update_organisation(
        self,
        *,
        ctx: OrganisationContext,
        payload: UpdateOrganisationRequest,
    ) -> OrganisationResponse:
        """Update organisation metadata while preserving slug uniqueness and audit log."""
        org = ctx.organisation
        self._require_active_organisation(org)

        changed_fields: list[str] = []
        if "slug" in payload.model_fields_set and payload.slug is not None:
            if payload.slug != org.slug:
                existing = self._org_repo.get_by_slug(payload.slug)
                if existing is not None and existing.id != org.id:
                    raise ConflictError(
                        "An organisation with this slug already exists.",
                        code="ORGANISATION_SLUG_ALREADY_EXISTS",
                    )
                org.slug = payload.slug
                changed_fields.append("slug")
        if "name" in payload.model_fields_set and payload.name is not None:
            if payload.name != org.name:
                org.name = payload.name
                changed_fields.append("name")
        if "description" in payload.model_fields_set and payload.description != org.description:
            org.description = payload.description
            changed_fields.append("description")

        self._audit.record_event(
            event_type="organisation.updated",
            resource_type="organisation",
            actor_user_id=ctx.principal.user.id,
            organisation_id=org.id,
            resource_id=str(org.id),
            metadata={"changed_fields": changed_fields},
            message=f"Updated organisation '{org.id}'.",
        )
        try:
            self._db.commit()
        except IntegrityError as exc:
            self._db.rollback()
            raise ConflictError(
                "An organisation with this slug already exists.",
                code="ORGANISATION_SLUG_ALREADY_EXISTS",
            ) from exc

        refreshed_ctx = self._rbac_service.resolve_organisation_context(
            organisation_id=org.id,
            principal=ctx.principal,
        )
        return self.get_organisation_detail(refreshed_ctx)

    def archive_organisation(self, *, ctx: OrganisationContext) -> OrganisationResponse:
        """Archive an organisation cleanly; rejects duplicate archival."""
        org = ctx.organisation
        if org.status == OrganisationStatus.ARCHIVED.value:
            raise ConflictError(
                "Organisation is already archived.",
                code="ORGANISATION_ALREADY_ARCHIVED",
            )

        now = utc_now()
        org.status = OrganisationStatus.ARCHIVED.value
        org.archived_at = now
        self._audit.record_event(
            event_type="organisation.archived",
            resource_type="organisation",
            actor_user_id=ctx.principal.user.id,
            organisation_id=org.id,
            resource_id=str(org.id),
            metadata={"slug": org.slug},
            message=f"Archived organisation '{org.id}'.",
        )
        self._db.commit()
        refreshed_ctx = self._rbac_service.resolve_organisation_context(
            organisation_id=org.id,
            principal=ctx.principal,
        )
        return self.get_organisation_detail(refreshed_ctx)

    def list_members(
        self,
        *,
        ctx: OrganisationContext,
        status: str | None = OrganisationMembershipStatus.ACTIVE.value,
        limit: int = 50,
        offset: int = 0,
    ) -> OrganisationMemberListResponse:
        """List memberships strictly inside the verified organisation."""
        rows, total = self._org_repo.list_memberships(
            organisation_id=ctx.organisation.id,
            status=status,
            limit=limit,
            offset=offset,
        )
        return OrganisationMemberListResponse(
            items=[_build_member_response(row) for row in rows],
            total=total,
        )

    def update_member_role(
        self,
        *,
        ctx: OrganisationContext,
        target_user_id: uuid.UUID,
        payload: UpdateOrganisationMemberRoleRequest,
    ) -> OrganisationMemberResponse:
        """Update an existing organisation member's role with escalation and owner guards."""
        self._require_active_organisation(ctx.organisation)

        target_role = self._rbac_service.get_scoped_role_or_fail(
            role_name=payload.role_name,
            expected_scope=RoleScopeType.ORGANISATION,
            actor_user_id=ctx.principal.user.id,
            organisation_id=ctx.organisation.id,
        )
        membership = self._org_repo.get_active_membership(
            organisation_id=ctx.organisation.id,
            user_id=target_user_id,
        )
        if membership is None:
            raise NotFoundError(
                "Active organisation membership was not found.",
                code="MEMBERSHIP_NOT_FOUND",
            )

        current_role_name = membership.role.name
        self._rbac_service.require_org_role_authority(
            actor_role_name=ctx.role.name,
            target_role_name=current_role_name,
            actor_user_id=ctx.principal.user.id,
            organisation_id=ctx.organisation.id,
            action_label="modify",
        )
        self._rbac_service.require_org_role_authority(
            actor_role_name=ctx.role.name,
            target_role_name=target_role.name,
            actor_user_id=ctx.principal.user.id,
            organisation_id=ctx.organisation.id,
            action_label="assign",
        )

        if (
            current_role_name == RoleName.ORG_OWNER.value
            and target_role.name != RoleName.ORG_OWNER.value
        ):
            owner_count = self._org_repo.count_active_by_role_name(
                organisation_id=ctx.organisation.id,
                role_name=RoleName.ORG_OWNER.value,
            )
            if owner_count <= 1:
                raise ConflictError(
                    "Cannot demote the last active organisation owner.",
                    code="LAST_ORG_OWNER_FORBIDDEN",
                )

        membership.role_id = target_role.id
        membership.role = target_role
        self._audit.record_event(
            event_type="organisation.member.role_changed",
            resource_type="organisation_membership",
            actor_user_id=ctx.principal.user.id,
            organisation_id=ctx.organisation.id,
            resource_id=str(target_user_id),
            metadata={
                "target_user_id": str(target_user_id),
                "previous_role": current_role_name,
                "new_role": target_role.name,
            },
            message=(
                f"Changed member '{target_user_id}' role in org '{ctx.organisation.id}' "
                f"from '{current_role_name}' to '{target_role.name}'."
            ),
        )
        self._db.commit()
        refreshed = self._org_repo.get_active_membership(
            organisation_id=ctx.organisation.id,
            user_id=target_user_id,
        )
        if refreshed is None:
            raise NotFoundError(
                "Active organisation membership was not found.",
                code="MEMBERSHIP_NOT_FOUND",
            )
        return _build_member_response(refreshed)

    def remove_member(
        self,
        *,
        ctx: OrganisationContext,
        target_user_id: uuid.UUID,
    ) -> RemoveMembershipResponse:
        """Remove an organisation member and immediately revoke all their project memberships."""
        self._require_active_organisation(ctx.organisation)

        membership = self._org_repo.get_active_membership(
            organisation_id=ctx.organisation.id,
            user_id=target_user_id,
        )
        if membership is None:
            raise NotFoundError(
                "Active organisation membership was not found.",
                code="MEMBERSHIP_NOT_FOUND",
            )

        current_role_name = membership.role.name
        self._rbac_service.require_org_role_authority(
            actor_role_name=ctx.role.name,
            target_role_name=current_role_name,
            actor_user_id=ctx.principal.user.id,
            organisation_id=ctx.organisation.id,
            action_label="remove",
        )

        if current_role_name == RoleName.ORG_OWNER.value:
            owner_count = self._org_repo.count_active_by_role_name(
                organisation_id=ctx.organisation.id,
                role_name=RoleName.ORG_OWNER.value,
            )
            if owner_count <= 1:
                raise ConflictError(
                    "Cannot remove the last active organisation owner.",
                    code="LAST_ORG_OWNER_FORBIDDEN",
                )

        membership.status = OrganisationMembershipStatus.REMOVED.value
        revoked_projects = self._project_repo.revoke_all_for_user_in_organisation(
            organisation_id=ctx.organisation.id,
            user_id=target_user_id,
        )
        self._audit.record_event(
            event_type="organisation.member.removed",
            resource_type="organisation_membership",
            actor_user_id=ctx.principal.user.id,
            organisation_id=ctx.organisation.id,
            resource_id=str(target_user_id),
            metadata={
                "target_user_id": str(target_user_id),
                "previous_role": current_role_name,
                "revoked_project_memberships": revoked_projects,
            },
            message=(
                f"Removed member '{target_user_id}' from organisation '{ctx.organisation.id}' "
                f"and revoked {revoked_projects} project membership(s)."
            ),
        )
        self._db.commit()
        return RemoveMembershipResponse(
            message="Organisation member removed and project access revoked immediately.",
            user_id=target_user_id,
            revoked_project_memberships=revoked_projects,
        )

    def create_invitation(
        self,
        *,
        ctx: OrganisationContext,
        payload: CreateInvitationRequest,
    ) -> CreateInvitationResponse:
        """Issue a SHA-256 hashed single-use invitation with honest non-delivery status."""
        self._require_active_organisation(ctx.organisation)

        target_role = self._rbac_service.get_scoped_role_or_fail(
            role_name=payload.role_name,
            expected_scope=RoleScopeType.ORGANISATION,
            actor_user_id=ctx.principal.user.id,
            organisation_id=ctx.organisation.id,
        )
        self._rbac_service.require_org_role_authority(
            actor_role_name=ctx.role.name,
            target_role_name=target_role.name,
            actor_user_id=ctx.principal.user.id,
            organisation_id=ctx.organisation.id,
            action_label="invite",
        )

        existing_user = self._user_repo.get_by_email(payload.email)
        if existing_user is not None:
            active_membership = self._org_repo.get_active_membership(
                organisation_id=ctx.organisation.id,
                user_id=existing_user.id,
            )
            if active_membership is not None:
                raise ConflictError(
                    "User is already an active member of this organisation.",
                    code="MEMBERSHIP_ALREADY_EXISTS",
                )

        now = utc_now()
        pending = self._org_repo.get_pending_invitation(
            organisation_id=ctx.organisation.id,
            normalised_email=payload.email,
        )
        if pending is not None:
            if ensure_utc(pending.expires_at) <= now:
                pending.status = InvitationStatus.EXPIRED.value
                self._db.flush()
            else:
                raise ConflictError(
                    "An active pending invitation already exists for this email address.",
                    code="INVITATION_ALREADY_EXISTS",
                )

        raw_token = generate_opaque_token(48)
        token_hash = hash_opaque_token(raw_token)
        expires_at = now + timedelta(hours=payload.expires_in_hours)

        invitation = self._org_repo.create_invitation(
            organisation_id=ctx.organisation.id,
            email=payload.email,
            role_id=target_role.id,
            token_hash=token_hash,
            invited_by_id=ctx.principal.user.id,
            expires_at=expires_at,
        )
        invitation.role = target_role

        self._audit.record_event(
            event_type="organisation.invitation.created",
            resource_type="organisation_invitation",
            actor_user_id=ctx.principal.user.id,
            organisation_id=ctx.organisation.id,
            resource_id=str(invitation.id),
            metadata={
                "invitee_email": invitation.email,
                "role_name": target_role.name,
                "expires_at": expires_at.isoformat(),
            },
            message=f"Created organisation invitation '{invitation.id}'.",
        )
        self._db.commit()

        dev_token = None if self._settings.is_production else raw_token
        return CreateInvitationResponse(
            invitation=_build_invitation_summary(invitation),
            invitation_delivery="not_configured",
            message=(
                "Invitation created. Outbound email delivery is not configured in this "
                "environment; handle invitation acceptance through the verified token flow."
            ),
            development_invitation_token=dev_token,
        )

    def list_invitations(
        self,
        *,
        ctx: OrganisationContext,
        status: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> InvitationListResponse:
        """List invitation metadata scoped strictly to the org (never leaks hashes/tokens)."""
        changed = self._org_repo.expire_stale_invitations_in_org(
            organisation_id=ctx.organisation.id,
            now=utc_now(),
        )
        if changed:
            self._db.commit()

        rows, total = self._org_repo.list_invitations(
            organisation_id=ctx.organisation.id,
            status=status,
            limit=limit,
            offset=offset,
        )
        return InvitationListResponse(
            items=[_build_invitation_summary(row) for row in rows],
            total=total,
        )

    def accept_invitation(
        self,
        *,
        raw_token: str,
        acting_principal: AuthenticatedPrincipal,
    ) -> AcceptInvitationResponse:
        """Verify and consume a single-use invitation matching the authenticated user's email."""
        cleaned_token = raw_token.strip()
        if not cleaned_token:
            raise NotFoundError("Invitation was not found.", code="INVITATION_NOT_FOUND")

        token_hash = hash_opaque_token(cleaned_token)
        invitation = self._org_repo.get_invitation_by_token_hash_for_update(token_hash)
        if invitation is None:
            raise NotFoundError("Invitation was not found.", code="INVITATION_NOT_FOUND")

        if acting_principal.user.email != invitation.email:
            self._audit.record_event(
                event_type="organisation.invitation.accept_denied",
                resource_type="organisation_invitation",
                actor_user_id=acting_principal.user.id,
                organisation_id=invitation.organisation_id,
                resource_id=str(invitation.id),
                outcome=AuditOutcome.DENIED.value,
                metadata={"reason": "email_mismatch"},
                message="Denied invitation acceptance due to account email mismatch.",
                level=logging.WARNING,
            )
            self._db.commit()
            raise ForbiddenError(
                "This invitation was issued for a different email address.",
                code="INVITATION_EMAIL_MISMATCH",
            )

        if invitation.status == InvitationStatus.ACCEPTED.value:
            raise ConflictError(
                "This invitation has already been accepted.",
                code="INVITATION_ALREADY_ACCEPTED",
            )
        if invitation.status == InvitationStatus.REVOKED.value:
            raise ConflictError(
                "This invitation has been revoked.",
                code="INVITATION_REVOKED",
            )

        now = utc_now()
        if (
            invitation.status == InvitationStatus.EXPIRED.value
            or ensure_utc(invitation.expires_at) <= now
        ):
            if invitation.status == InvitationStatus.PENDING.value:
                invitation.status = InvitationStatus.EXPIRED.value
                self._db.commit()
            raise GoneError(
                "This invitation has expired.",
                code="INVITATION_EXPIRED",
            )

        organisation = invitation.organisation
        self._require_active_organisation(organisation)

        target_role = invitation.role
        if target_role is None or target_role.scope_type != RoleScopeType.ORGANISATION.value:
            raise ForbiddenError("Invalid invitation role scope.", code="INVALID_ROLE_SCOPE")

        inviter_membership = self._org_repo.get_active_membership(
            organisation_id=invitation.organisation_id,
            user_id=invitation.invited_by_id,
        )
        inviter_perms = (
            {
                rp.permission.code
                for rp in inviter_membership.role.role_permissions
                if rp.permission is not None
            }
            if inviter_membership is not None
            else set()
        )
        inviter_rank = (
            ORG_ROLE_RANK.get(inviter_membership.role.name, 0)
            if inviter_membership is not None
            else 0
        )
        if (
            inviter_membership is None
            or "organisation.invitations.manage" not in inviter_perms
            or inviter_rank < ORG_ROLE_RANK.get(target_role.name, 999)
        ):
            raise ForbiddenError(
                "The inviter no longer holds authority to grant this organisation role.",
                code="INVITER_NO_LONGER_AUTHORISED",
            )

        existing_membership = self._org_repo.get_active_membership(
            organisation_id=organisation.id,
            user_id=acting_principal.user.id,
        )
        if existing_membership is not None:
            raise ConflictError(
                "You are already an active member of this organisation.",
                code="MEMBERSHIP_ALREADY_EXISTS",
            )

        try:
            membership = self._org_repo.create_membership(
                organisation_id=organisation.id,
                user_id=acting_principal.user.id,
                role_id=target_role.id,
                invited_by_id=invitation.invited_by_id,
                joined_at=now,
            )
            invitation.status = InvitationStatus.ACCEPTED.value
            invitation.accepted_at = now
            invitation.accepted_by_user_id = acting_principal.user.id

            self._audit.record_event(
                event_type="organisation.invitation.accepted",
                resource_type="organisation_invitation",
                actor_user_id=acting_principal.user.id,
                organisation_id=organisation.id,
                resource_id=str(invitation.id),
                metadata={"role_name": target_role.name},
                message=f"Accepted invitation '{invitation.id}' into org '{organisation.id}'.",
            )
            self._audit.record_event(
                event_type="organisation.member.added",
                resource_type="organisation_membership",
                actor_user_id=acting_principal.user.id,
                organisation_id=organisation.id,
                resource_id=str(acting_principal.user.id),
                metadata={"role_name": target_role.name, "via": "invitation"},
                message=f"User '{acting_principal.user.id}' joined org '{organisation.id}'.",
            )
            self._db.commit()
        except IntegrityError as exc:
            self._db.rollback()
            raise ConflictError(
                "Membership already exists for this organisation.",
                code="MEMBERSHIP_ALREADY_EXISTS",
            ) from exc

        return AcceptInvitationResponse(
            organisation_id=organisation.id,
            organisation_name=organisation.name,
            organisation_slug=organisation.slug,
            role_name=target_role.name,
            membership_status=membership.status,
            joined_at=membership.joined_at,
        )

    def revoke_invitation(
        self,
        *,
        ctx: OrganisationContext,
        invitation_id: uuid.UUID,
    ) -> InvitationSummaryResponse:
        """Revoke an active pending invitation belonging to this organisation."""
        self._require_active_organisation(ctx.organisation)

        invitation = self._org_repo.get_invitation_by_id_in_org(
            organisation_id=ctx.organisation.id,
            invitation_id=invitation_id,
        )
        if invitation is None:
            raise NotFoundError("Invitation was not found.", code="INVITATION_NOT_FOUND")

        self._rbac_service.require_org_role_authority(
            actor_role_name=ctx.role.name,
            target_role_name=invitation.role.name,
            actor_user_id=ctx.principal.user.id,
            organisation_id=ctx.organisation.id,
            action_label="revoke",
        )

        now = utc_now()
        if invitation.status == InvitationStatus.ACCEPTED.value:
            raise ConflictError(
                "Accepted invitations cannot be revoked.",
                code="INVITATION_ALREADY_ACCEPTED",
            )
        if invitation.status == InvitationStatus.REVOKED.value:
            raise ConflictError(
                "Invitation has already been revoked.",
                code="INVITATION_REVOKED",
            )
        if (
            invitation.status == InvitationStatus.EXPIRED.value
            or ensure_utc(invitation.expires_at) <= now
        ):
            if invitation.status == InvitationStatus.PENDING.value:
                invitation.status = InvitationStatus.EXPIRED.value
                self._db.commit()
            raise GoneError("Expired invitations cannot be revoked.", code="INVITATION_EXPIRED")

        invitation.status = InvitationStatus.REVOKED.value
        invitation.revoked_at = now
        invitation.revoked_by_id = ctx.principal.user.id
        self._audit.record_event(
            event_type="organisation.invitation.revoked",
            resource_type="organisation_invitation",
            actor_user_id=ctx.principal.user.id,
            organisation_id=ctx.organisation.id,
            resource_id=str(invitation.id),
            metadata={"invitee_email": invitation.email, "role_name": invitation.role.name},
            message=f"Revoked invitation '{invitation.id}'.",
        )
        self._db.commit()
        return _build_invitation_summary(invitation)
