"""Repository operations for RBAC roles, permissions, and user role assignments."""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.core.rbac_catalog import SYSTEM_PERMISSIONS, SYSTEM_ROLES
from app.models.enums import RoleScopeType
from app.models.rbac import Permission, Role, RolePermission, UserRole


class RbacRepository:
    """Data-access operations for `roles`, `permissions`, `role_permissions`, and `user_roles`."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def get_role_by_name(self, name: str) -> Role | None:
        stmt = (
            select(Role)
            .where(Role.name == name)
            .options(selectinload(Role.role_permissions).selectinload(RolePermission.permission))
        )
        return self._session.scalar(stmt)

    def list_roles(self) -> list[Role]:
        stmt = (
            select(Role)
            .options(selectinload(Role.role_permissions).selectinload(RolePermission.permission))
            .order_by(Role.scope_type.asc(), Role.name.asc())
        )
        return list(self._session.scalars(stmt).all())

    def get_user_platform_roles_and_permissions(
        self,
        user_id: uuid.UUID,
    ) -> tuple[list[str], frozenset[str]]:
        """Return strictly platform-scoped role names and permission codes for a user."""
        role_stmt = (
            select(Role.name)
            .join(UserRole, UserRole.role_id == Role.id)
            .where(
                UserRole.user_id == user_id,
                Role.scope_type == RoleScopeType.PLATFORM.value,
            )
            .order_by(Role.name.asc())
        )
        role_names = list(self._session.scalars(role_stmt).all())

        perm_stmt = (
            select(Permission.code)
            .join(RolePermission, RolePermission.permission_id == Permission.id)
            .join(Role, Role.id == RolePermission.role_id)
            .join(UserRole, UserRole.role_id == Role.id)
            .where(
                UserRole.user_id == user_id,
                Role.scope_type == RoleScopeType.PLATFORM.value,
                Permission.scope_type == RoleScopeType.PLATFORM.value,
            )
            .distinct()
        )
        permissions = frozenset(self._session.scalars(perm_stmt).all())
        return role_names, permissions

    def assign_role(
        self,
        *,
        user_id: uuid.UUID,
        role_id: uuid.UUID,
        assigned_by_id: uuid.UUID | None = None,
    ) -> UserRole:
        existing = self._session.scalar(
            select(UserRole).where(
                UserRole.user_id == user_id,
                UserRole.role_id == role_id,
            )
        )
        if existing is not None:
            return existing

        assignment = UserRole(
            user_id=user_id,
            role_id=role_id,
            assigned_by_id=assigned_by_id,
        )
        self._session.add(assignment)
        self._session.flush()
        return assignment

    def ensure_catalog_seeded(self) -> None:
        """Idempotently populate built-in roles and permissions (used by isolated tests)."""
        existing_perms = {
            p.code: p for p in self._session.scalars(select(Permission)).all()
        }
        for spec in SYSTEM_PERMISSIONS:
            if spec.code not in existing_perms:
                perm = Permission(
                    id=spec.id,
                    code=spec.code,
                    name=spec.name,
                    description=spec.description,
                    scope_type=spec.scope_type.value,
                )
                self._session.add(perm)
                existing_perms[spec.code] = perm
        self._session.flush()

        existing_roles = {r.name: r for r in self._session.scalars(select(Role)).all()}
        existing_links = {
            (rp.role_id, rp.permission_id)
            for rp in self._session.scalars(select(RolePermission)).all()
        }

        for role_spec in SYSTEM_ROLES:
            role = existing_roles.get(role_spec.name)
            if role is None:
                role = Role(
                    id=role_spec.id,
                    name=role_spec.name,
                    display_name=role_spec.display_name,
                    description=role_spec.description,
                    scope_type=role_spec.scope_type.value,
                    is_system=True,
                )
                self._session.add(role)
                existing_roles[role_spec.name] = role
                self._session.flush()

            for perm_code in role_spec.permission_codes:
                perm_obj = existing_perms[perm_code]
                key = (role.id, perm_obj.id)
                if key not in existing_links:
                    self._session.add(
                        RolePermission(role_id=role.id, permission_id=perm_obj.id)
                    )
                    existing_links.add(key)

        self._session.flush()
