"""Supabase Auth token verification, JWKS caching, and user auto-provisioning."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

import jwt
from jwt import PyJWKClient
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.core.exceptions import UnauthorizedError
from app.core.security import utc_now
from app.models.enums import RoleName, UserStatus
from app.models.user import User
from app.repositories.rbac import RbacRepository
from app.repositories.user import UserRepository

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class SupabaseUserClaims:
    """Verified claims extracted from a Supabase Auth JWT."""

    sub: str
    email: str
    full_name: str
    is_email_verified: bool
    role: str | None = None
    raw_claims: dict[str, Any] = field(default_factory=dict)


class SupabaseAuthService:
    """Handles verification of Supabase Auth JWTs via asymmetric JWKS or symmetric secret."""

    def __init__(
        self,
        settings: Settings,
        jwk_client: PyJWKClient | None = None,
    ) -> None:
        self._settings = settings
        self._supabase_config = settings.supabase
        self._jwk_client: PyJWKClient | None = jwk_client

        if self._jwk_client is None and self._supabase_config.auth_jwks_url:
            self._jwk_client = PyJWKClient(
                self._supabase_config.auth_jwks_url,
                cache_keys=True,
                max_cached_keys=16,
                cache_jwk_set=True,
                lifespan=3600,
            )

    @property
    def is_configured(self) -> bool:
        """Return True when Supabase Auth URL/keys are configured."""
        return bool(
            self._supabase_config.enabled
            and (self._supabase_config.url or self._supabase_config.jwks_url)
        )

    def verify_token(self, token: str) -> SupabaseUserClaims:
        """Verify the signature and claims of a Supabase Auth Bearer JWT."""
        if not token or not token.strip():
            raise UnauthorizedError(
                "Authentication credentials were not provided.",
                code="AUTHENTICATION_REQUIRED",
            )

        try:
            unverified_header = jwt.get_unverified_header(token)
        except jwt.PyJWTError as exc:
            raise UnauthorizedError(
                "Invalid token format.",
                code="AUTHENTICATION_INVALID",
            ) from exc

        alg = unverified_header.get("alg", "ES256")
        expected_audience = self._supabase_config.jwt_audience or "authenticated"
        expected_issuer = self._supabase_config.auth_issuer_url

        payload: dict[str, Any]
        try:
            if alg == "HS256" and self._supabase_config.jwt_secret:
                # Symmetric verification with JWT secret
                secret = self._supabase_config.jwt_secret.get_secret_value()
                options = {"verify_aud": bool(expected_audience)}
                decode_kwargs: dict[str, Any] = {
                    "jwt": token,
                    "key": secret,
                    "algorithms": ["HS256"],
                    "options": options,
                }
                if expected_audience:
                    decode_kwargs["audience"] = expected_audience
                if expected_issuer:
                    decode_kwargs["issuer"] = expected_issuer
                payload = jwt.decode(**decode_kwargs)
            elif self._jwk_client is not None:
                # Asymmetric verification via JWKS (ES256 / RS256)
                signing_key = self._jwk_client.get_signing_key_from_jwt(token)
                options = {"verify_aud": bool(expected_audience)}
                decode_kwargs = {
                    "jwt": token,
                    "key": signing_key.key,
                    "algorithms": ["ES256", "RS256", "HS256"],
                    "options": options,
                }
                if expected_audience:
                    decode_kwargs["audience"] = expected_audience
                if expected_issuer:
                    decode_kwargs["issuer"] = expected_issuer
                payload = jwt.decode(**decode_kwargs)
            else:
                raise UnauthorizedError(
                    "Supabase Auth JWKS client is not configured.",
                    code="AUTHENTICATION_MISCONFIGURED",
                )
        except jwt.ExpiredSignatureError as exc:
            raise UnauthorizedError(
                "Token signature has expired.",
                code="SESSION_EXPIRED",
            ) from exc
        except jwt.InvalidTokenError as exc:
            raise UnauthorizedError(
                f"Invalid authentication token: {exc}",
                code="AUTHENTICATION_INVALID",
            ) from exc

        sub = payload.get("sub")
        if not sub:
            raise UnauthorizedError(
                "Token payload missing 'sub' claim.",
                code="AUTHENTICATION_INVALID",
            )

        email = str(payload.get("email") or "").strip().lower()
        user_metadata = payload.get("user_metadata") or {}
        full_name = (
            user_metadata.get("full_name")
            or user_metadata.get("name")
            or (email.split("@")[0] if email else "Supabase User")
        )
        is_email_verified = bool(
            payload.get("email_confirmed_at")
            or user_metadata.get("email_verified")
            or payload.get("app_metadata", {}).get("provider") == "email"
        )
        role = payload.get("role")

        return SupabaseUserClaims(
            sub=str(sub),
            email=email,
            full_name=str(full_name),
            is_email_verified=is_email_verified,
            role=str(role) if role else None,
            raw_claims=payload,
        )

    def provision_or_sync_user(
        self,
        session: Session,
        claims: SupabaseUserClaims,
    ) -> User:
        """Find existing user by supabase_auth_id or email, or provision a new user."""
        user_repo = UserRepository(session)
        user: User | None = None

        # 1. Lookup by supabase_auth_id
        if claims.sub:
            user = user_repo.get_by_supabase_auth_id(claims.sub)

        # 2. Fallback lookup by email
        if user is None and claims.email:
            user = user_repo.get_by_email(claims.email)
            if user is not None:
                # Link existing email account to Supabase Auth ID
                user.supabase_auth_id = claims.sub
                if not user.full_name and claims.full_name:
                    user.full_name = claims.full_name
                if claims.is_email_verified:
                    user.is_email_verified = True
                    user.email_verified_at = utc_now()

        # 3. Provision new user if not found
        if user is None:
            user = user_repo.create(
                full_name=claims.full_name,
                email=claims.email,
                password_hash=None,
                supabase_auth_id=claims.sub,
                status=UserStatus.ACTIVE.value,
                is_email_verified=claims.is_email_verified,
            )
            # Assign baseline platform role so user has profile permissions
            rbac_repo = RbacRepository(session)
            default_role = rbac_repo.get_role_by_name(RoleName.STANDARD_USER.value)
            if default_role is not None:
                rbac_repo.assign_role(user_id=user.id, role_id=default_role.id)
            logger.info(
                "Provisioned new user %s from Supabase Auth ID %s",
                claims.email,
                claims.sub,
            )

        user_repo.update_last_login(user, utc_now())
        session.flush()
        return user
