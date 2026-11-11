"""Repository operations for organisations, memberships, and hashed invitations."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, cast

from sqlalchemy import func, or_, select, update
from sqlalchemy.engine import CursorResult
from sqlalchemy.orm import Session, selectinload

from app.models.enums import (
    InvitationStatus,
    OrganisationMembershipStatus,
    OrganisationStatus,
)
from app.models.organisation import (
    Organisation,
    OrganisationInvitation,
    OrganisationMembership,
)
from app.models.rbac import Role, RolePermission


class OrganisationRepository:
    """Data-access operations for `organisations`, `organisation_memberships`,
    and `organisation_invitations`.
    """

    def __init__(self, session: Session) -> None:
        self._session = session

    def get_by_id(self, organisation_id: uuid.UUID) -> Organisation | None:
        stmt = select(Organisation).where(Organisation.id == organisation_id)
        return self._session.scalar(stmt)

    def get_by_slug(self, normalised_slug: str) -> Organisation | None:
        stmt = select(Organisation).where(Organisation.slug == normalised_slug)
        return self._session.scalar(stmt)

    def create(
        self,
        *,
        name: str,
        slug: str,
        description: str | None,
        created_by_id: uuid.UUID,
    ) -> Organisation:
        org = Organisation(
            name=name,
            slug=slug,
            description=description,
            status=OrganisationStatus.ACTIVE.value,
            created_by_id=created_by_id,
        )
        self._session.add(org)
        self._session.flush()
        return org

    def list_for_user(
        self,
        *,
        user_id: uuid.UUID,
        status: str | None = None,
        search: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[tuple[Organisation, OrganisationMembership]], int]:
        base = (
            select(Organisation, OrganisationMembership)
            .join(
                OrganisationMembership,
                OrganisationMembership.organisation_id == Organisation.id,
            )
            .where(
                OrganisationMembership.user_id == user_id,
                OrganisationMembership.status == OrganisationMembershipStatus.ACTIVE.value,
            )
        )
        if status is not None:
            base = base.where(Organisation.status == status)
        if search:
            pattern = f"%{search.strip()}%"
            base = base.where(
                or_(Organisation.name.ilike(pattern), Organisation.slug.ilike(pattern))
            )

        count_stmt = select(func.count()).select_from(base.subquery())
        total = int(self._session.scalar(count_stmt) or 0)

        rows_stmt = (
            base.options(selectinload(OrganisationMembership.role))
            .order_by(Organisation.created_at.desc(), Organisation.id.asc())
            .offset(offset)
            .limit(limit)
        )
        rows = [(org, mem) for org, mem in self._session.execute(rows_stmt).all()]
        return rows, total

    def get_active_membership(
        self,
        *,
        organisation_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> OrganisationMembership | None:
        stmt = (
            select(OrganisationMembership)
            .where(
                OrganisationMembership.organisation_id == organisation_id,
                OrganisationMembership.user_id == user_id,
                OrganisationMembership.status == OrganisationMembershipStatus.ACTIVE.value,
            )
            .options(
                selectinload(OrganisationMembership.user),
                selectinload(OrganisationMembership.role)
                .selectinload(Role.role_permissions)
                .selectinload(RolePermission.permission),
            )
        )
        return self._session.scalar(stmt)

    def list_memberships(
        self,
        *,
        organisation_id: uuid.UUID,
        status: str | None = OrganisationMembershipStatus.ACTIVE.value,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[OrganisationMembership], int]:
        base = select(OrganisationMembership).where(
            OrganisationMembership.organisation_id == organisation_id
        )
        if status is not None:
            base = base.where(OrganisationMembership.status == status)

        total = int(self._session.scalar(select(func.count()).select_from(base.subquery())) or 0)
        stmt = (
            base.options(
                selectinload(OrganisationMembership.user),
                selectinload(OrganisationMembership.role),
            )
            .order_by(OrganisationMembership.joined_at.asc(), OrganisationMembership.id.asc())
            .offset(offset)
            .limit(limit)
        )
        return list(self._session.scalars(stmt).all()), total

    def count_active_by_role_name(
        self,
        *,
        organisation_id: uuid.UUID,
        role_name: str,
    ) -> int:
        stmt = (
            select(func.count(OrganisationMembership.id))
            .join(Role, Role.id == OrganisationMembership.role_id)
            .where(
                OrganisationMembership.organisation_id == organisation_id,
                OrganisationMembership.status == OrganisationMembershipStatus.ACTIVE.value,
                Role.name == role_name,
            )
        )
        return int(self._session.scalar(stmt) or 0)

    def create_membership(
        self,
        *,
        organisation_id: uuid.UUID,
        user_id: uuid.UUID,
        role_id: uuid.UUID,
        invited_by_id: uuid.UUID | None = None,
        joined_at: datetime | None = None,
    ) -> OrganisationMembership:
        membership = OrganisationMembership(
            organisation_id=organisation_id,
            user_id=user_id,
            role_id=role_id,
            status=OrganisationMembershipStatus.ACTIVE.value,
            invited_by_id=invited_by_id,
        )
        if joined_at is not None:
            membership.joined_at = joined_at
        self._session.add(membership)
        self._session.flush()
        return membership

    def get_invitation_by_token_hash_for_update(
        self,
        token_hash: str,
    ) -> OrganisationInvitation | None:
        stmt = (
            select(OrganisationInvitation)
            .where(OrganisationInvitation.token_hash == token_hash)
            .options(
                selectinload(OrganisationInvitation.organisation),
                selectinload(OrganisationInvitation.role),
            )
            .with_for_update()
        )
        return self._session.scalar(stmt)

    def get_invitation_by_id_in_org(
        self,
        *,
        organisation_id: uuid.UUID,
        invitation_id: uuid.UUID,
    ) -> OrganisationInvitation | None:
        stmt = (
            select(OrganisationInvitation)
            .where(
                OrganisationInvitation.id == invitation_id,
                OrganisationInvitation.organisation_id == organisation_id,
            )
            .options(selectinload(OrganisationInvitation.role))
            .with_for_update()
        )
        return self._session.scalar(stmt)

    def get_pending_invitation(
        self,
        *,
        organisation_id: uuid.UUID,
        normalised_email: str,
    ) -> OrganisationInvitation | None:
        stmt = select(OrganisationInvitation).where(
            OrganisationInvitation.organisation_id == organisation_id,
            OrganisationInvitation.email == normalised_email,
            OrganisationInvitation.status == InvitationStatus.PENDING.value,
        )
        return self._session.scalar(stmt)

    def list_invitations(
        self,
        *,
        organisation_id: uuid.UUID,
        status: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[OrganisationInvitation], int]:
        base = select(OrganisationInvitation).where(
            OrganisationInvitation.organisation_id == organisation_id
        )
        if status is not None:
            base = base.where(OrganisationInvitation.status == status)

        total = int(self._session.scalar(select(func.count()).select_from(base.subquery())) or 0)
        stmt = (
            base.options(selectinload(OrganisationInvitation.role))
            .order_by(OrganisationInvitation.created_at.desc(), OrganisationInvitation.id.asc())
            .offset(offset)
            .limit(limit)
        )
        return list(self._session.scalars(stmt).all()), total

    def expire_stale_invitations_in_org(
        self,
        *,
        organisation_id: uuid.UUID,
        now: datetime,
    ) -> int:
        stmt = (
            update(OrganisationInvitation)
            .where(
                OrganisationInvitation.organisation_id == organisation_id,
                OrganisationInvitation.status == InvitationStatus.PENDING.value,
                OrganisationInvitation.expires_at <= now,
            )
            .values(status=InvitationStatus.EXPIRED.value)
        )
        result = cast(CursorResult[Any], self._session.execute(stmt))
        return int(result.rowcount or 0)

    def create_invitation(
        self,
        *,
        organisation_id: uuid.UUID,
        email: str,
        role_id: uuid.UUID,
        token_hash: str,
        invited_by_id: uuid.UUID,
        expires_at: datetime,
    ) -> OrganisationInvitation:
        invitation = OrganisationInvitation(
            organisation_id=organisation_id,
            email=email,
            role_id=role_id,
            token_hash=token_hash,
            invited_by_id=invited_by_id,
            status=InvitationStatus.PENDING.value,
            expires_at=expires_at,
        )
        self._session.add(invitation)
        self._session.flush()
        return invitation
