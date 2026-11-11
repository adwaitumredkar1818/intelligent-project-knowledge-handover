"""Multi-tenant organisation workspace, membership, invitation, and audit routes."""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query, status

from app.api.deps import (
    get_audit_service,
    get_current_principal,
    get_organisation_service,
    require_organisation_permission,
    require_permission,
)
from app.models.enums import (
    InvitationStatus,
    OrganisationMembershipStatus,
    OrganisationStatus,
)
from app.schemas.organisation import (
    AcceptInvitationResponse,
    AuditLogListResponse,
    CreateInvitationRequest,
    CreateInvitationResponse,
    CreateOrganisationRequest,
    InvitationListResponse,
    InvitationSummaryResponse,
    OrganisationListResponse,
    OrganisationMemberListResponse,
    OrganisationMemberResponse,
    OrganisationResponse,
    RemoveMembershipResponse,
    UpdateOrganisationMemberRoleRequest,
    UpdateOrganisationRequest,
)
from app.services.audit import AuditService
from app.services.organisation import OrganisationService
from app.services.rbac import AuthenticatedPrincipal, OrganisationContext

router = APIRouter(tags=["organisations"])


@router.post(
    "/organisations",
    response_model=OrganisationResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create an organisation workspace (requires platform.organisations.create)",
)
def create_organisation(
    payload: CreateOrganisationRequest,
    principal: Annotated[
        AuthenticatedPrincipal,
        Depends(require_permission("platform.organisations.create")),
    ],
    org_service: Annotated[OrganisationService, Depends(get_organisation_service)],
) -> OrganisationResponse:
    """Create a multi-tenant organisation and assign its creator as initial `org_owner`."""
    return org_service.create_organisation(payload=payload, acting_principal=principal)


@router.get(
    "/organisations",
    response_model=OrganisationListResponse,
    status_code=status.HTTP_200_OK,
    summary="List organisations where the caller holds active membership",
)
def list_my_organisations(
    principal: Annotated[AuthenticatedPrincipal, Depends(get_current_principal)],
    org_service: Annotated[OrganisationService, Depends(get_organisation_service)],
    org_status: Annotated[OrganisationStatus | None, Query(alias="status")] = None,
    search: Annotated[str | None, Query(max_length=120)] = None,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> OrganisationListResponse:
    """Return organisations strictly scoped to the authenticated user's active memberships."""
    return org_service.list_my_organisations(
        principal=principal,
        status=org_status.value if org_status is not None else None,
        search=search,
        limit=limit,
        offset=offset,
    )


@router.get(
    "/organisations/{organisation_id}",
    response_model=OrganisationResponse,
    status_code=status.HTTP_200_OK,
    summary="Get organisation workspace details (requires active membership and organisation.read)",
)
def get_organisation_detail(
    org_ctx: Annotated[
        OrganisationContext,
        Depends(require_organisation_permission("organisation.read")),
    ],
    org_service: Annotated[OrganisationService, Depends(get_organisation_service)],
) -> OrganisationResponse:
    """Return safe organisation metadata and the caller's resolved organisation permissions."""
    return org_service.get_organisation_detail(org_ctx)


@router.patch(
    "/organisations/{organisation_id}",
    response_model=OrganisationResponse,
    status_code=status.HTTP_200_OK,
    summary="Update organisation metadata (requires organisation.manage)",
)
def update_organisation(
    payload: UpdateOrganisationRequest,
    org_ctx: Annotated[
        OrganisationContext,
        Depends(require_organisation_permission("organisation.manage")),
    ],
    org_service: Annotated[OrganisationService, Depends(get_organisation_service)],
) -> OrganisationResponse:
    """Update an active organisation's name, slug, or description."""
    return org_service.update_organisation(ctx=org_ctx, payload=payload)


@router.post(
    "/organisations/{organisation_id}/archive",
    response_model=OrganisationResponse,
    status_code=status.HTTP_200_OK,
    summary="Archive an organisation workspace (requires organisation.manage)",
)
def archive_organisation(
    org_ctx: Annotated[
        OrganisationContext,
        Depends(require_organisation_permission("organisation.manage")),
    ],
    org_service: Annotated[OrganisationService, Depends(get_organisation_service)],
) -> OrganisationResponse:
    """Archive an active organisation workspace cleanly and record an audit event."""
    return org_service.archive_organisation(ctx=org_ctx)


@router.get(
    "/organisations/{organisation_id}/members",
    response_model=OrganisationMemberListResponse,
    status_code=status.HTTP_200_OK,
    summary="List organisation members (requires organisation.members.read)",
)
def list_organisation_members(
    org_ctx: Annotated[
        OrganisationContext,
        Depends(require_organisation_permission("organisation.members.read")),
    ],
    org_service: Annotated[OrganisationService, Depends(get_organisation_service)],
    member_status: Annotated[
        OrganisationMembershipStatus | None,
        Query(alias="status"),
    ] = OrganisationMembershipStatus.ACTIVE,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> OrganisationMemberListResponse:
    """List member profiles and roles strictly within the verified organisation."""
    return org_service.list_members(
        ctx=org_ctx,
        status=member_status.value if member_status is not None else None,
        limit=limit,
        offset=offset,
    )


@router.patch(
    "/organisations/{organisation_id}/members/{user_id}/role",
    response_model=OrganisationMemberResponse,
    status_code=status.HTTP_200_OK,
    summary="Update an organisation member's role (requires organisation.members.manage)",
)
def update_organisation_member_role(
    user_id: uuid.UUID,
    payload: UpdateOrganisationMemberRoleRequest,
    org_ctx: Annotated[
        OrganisationContext,
        Depends(require_organisation_permission("organisation.members.manage")),
    ],
    org_service: Annotated[OrganisationService, Depends(get_organisation_service)],
) -> OrganisationMemberResponse:
    """Update an active member's organisation-scoped role with escalation and owner guards."""
    return org_service.update_member_role(
        ctx=org_ctx,
        target_user_id=user_id,
        payload=payload,
    )


@router.delete(
    "/organisations/{organisation_id}/members/{user_id}",
    response_model=RemoveMembershipResponse,
    status_code=status.HTTP_200_OK,
    summary="Remove an organisation member (requires organisation.members.manage)",
)
def remove_organisation_member(
    user_id: uuid.UUID,
    org_ctx: Annotated[
        OrganisationContext,
        Depends(require_organisation_permission("organisation.members.manage")),
    ],
    org_service: Annotated[OrganisationService, Depends(get_organisation_service)],
) -> RemoveMembershipResponse:
    """Remove an organisation member and revoke all their project memberships in that tenant."""
    return org_service.remove_member(ctx=org_ctx, target_user_id=user_id)


@router.post(
    "/organisations/{organisation_id}/invitations",
    response_model=CreateInvitationResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create an organisation invitation (requires organisation.invitations.manage)",
)
def create_organisation_invitation(
    payload: CreateInvitationRequest,
    org_ctx: Annotated[
        OrganisationContext,
        Depends(require_organisation_permission("organisation.invitations.manage")),
    ],
    org_service: Annotated[OrganisationService, Depends(get_organisation_service)],
) -> CreateInvitationResponse:
    """Issue a SHA-256 hashed single-use invitation without claiming email delivery."""
    return org_service.create_invitation(ctx=org_ctx, payload=payload)


@router.get(
    "/organisations/{organisation_id}/invitations",
    response_model=InvitationListResponse,
    status_code=status.HTTP_200_OK,
    summary="List organisation invitations (requires organisation.invitations.read)",
)
def list_organisation_invitations(
    org_ctx: Annotated[
        OrganisationContext,
        Depends(require_organisation_permission("organisation.invitations.read")),
    ],
    org_service: Annotated[OrganisationService, Depends(get_organisation_service)],
    invitation_status: Annotated[InvitationStatus | None, Query(alias="status")] = None,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> InvitationListResponse:
    """List hashed invitation metadata scoped to this organisation."""
    return org_service.list_invitations(
        ctx=org_ctx,
        status=invitation_status.value if invitation_status is not None else None,
        limit=limit,
        offset=offset,
    )


@router.delete(
    "/organisations/{organisation_id}/invitations/{invitation_id}",
    response_model=InvitationSummaryResponse,
    status_code=status.HTTP_200_OK,
    summary="Revoke a pending organisation invitation (requires organisation.invitations.manage)",
)
def revoke_organisation_invitation(
    invitation_id: uuid.UUID,
    org_ctx: Annotated[
        OrganisationContext,
        Depends(require_organisation_permission("organisation.invitations.manage")),
    ],
    org_service: Annotated[OrganisationService, Depends(get_organisation_service)],
) -> InvitationSummaryResponse:
    """Revoke a pending invitation so its token can no longer be accepted."""
    return org_service.revoke_invitation(ctx=org_ctx, invitation_id=invitation_id)


@router.post(
    "/invitations/{token}/accept",
    response_model=AcceptInvitationResponse,
    status_code=status.HTTP_200_OK,
    summary="Accept a single-use organisation invitation as the authenticated user",
)
def accept_organisation_invitation(
    token: str,
    principal: Annotated[AuthenticatedPrincipal, Depends(get_current_principal)],
    org_service: Annotated[OrganisationService, Depends(get_organisation_service)],
) -> AcceptInvitationResponse:
    """Validate token hash, expiry, email match, and single-use state to activate membership."""
    return org_service.accept_invitation(raw_token=token, acting_principal=principal)


@router.get(
    "/organisations/{organisation_id}/audit-events",
    response_model=AuditLogListResponse,
    status_code=status.HTTP_200_OK,
    summary="Query organisational audit events (requires organisation.audit.read)",
)
def list_organisation_audit_events(
    org_ctx: Annotated[
        OrganisationContext,
        Depends(require_organisation_permission("organisation.audit.read")),
    ],
    audit_service: Annotated[AuditService, Depends(get_audit_service)],
    project_id: Annotated[uuid.UUID | None, Query()] = None,
    event_type: Annotated[str | None, Query(max_length=120)] = None,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> AuditLogListResponse:
    """Return sanitised, tenant-scoped audit log records for governance review."""
    return audit_service.list_organisation_events(
        organisation_id=org_ctx.organisation.id,
        project_id=project_id,
        event_type=event_type,
        limit=limit,
        offset=offset,
    )
