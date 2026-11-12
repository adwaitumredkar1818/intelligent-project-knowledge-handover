"""Delegated per-user OAuth 2.0 flow management, PKCE, and atomic refresh rotation."""

from __future__ import annotations

import base64
import hashlib
import logging
import secrets
import uuid
from datetime import datetime, timedelta
from typing import Any
from urllib.parse import urlencode, urlparse

import httpx
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
from app.core.security import hash_opaque_token, utc_now
from app.models.enums import (
    AuditOutcome,
    IntegrationProvider,
    SourceConnectionStatus,
    UserSourceAuthorisationStatus,
)
from app.models.integration import SourceConnection, UserSourceAuthorisation
from app.repositories.integration import IntegrationRepository
from app.schemas.integrations import (
    OAuthCallbackResponse,
    OAuthStartResponse,
    SourceConnectionResponse,
    UserSourceAuthorisationSummary,
)
from app.services.audit import AuditService
from app.services.integrations.errors import IntegrationAuthError, IntegrationProviderError
from app.services.integrations.http_utils import (
    create_integration_http_client,
    ensure_utc,
    raise_for_provider_error,
)
from app.services.rbac import AuthenticatedPrincipal, OrganisationContext, RbacService
from app.services.token_encryption import TokenEncryptionService, TokenKind

logger = logging.getLogger("app.services.integrations.oauth")


def to_authorisation_summary(
    auth: UserSourceAuthorisation,
) -> UserSourceAuthorisationSummary:
    """Map UserSourceAuthorisation ORM row to strictly non-secret API DTO."""
    return UserSourceAuthorisationSummary(
        id=auth.id,
        user_id=auth.user_id,
        provider=auth.provider,
        external_user_id=auth.external_user_id,
        external_username=auth.external_username,
        external_email=auth.external_email,
        granted_scopes=list(auth.granted_scopes or []),
        status=auth.status,
        token_expires_at=auth.token_expires_at,
        last_refreshed_at=auth.last_refreshed_at,
        last_verified_at=auth.last_verified_at,
        revoked_at=auth.revoked_at,
        last_error_code=auth.last_error_code,
        last_error_summary=auth.last_error_summary,
        created_at=auth.created_at,
        updated_at=auth.updated_at,
    )


def to_source_connection_response(
    connection: SourceConnection,
    *,
    caller_authorisation: UserSourceAuthorisation | None = None,
) -> SourceConnectionResponse:
    """Map SourceConnection ORM row to public metadata DTO."""
    return SourceConnectionResponse(
        id=connection.id,
        organisation_id=connection.organisation_id,
        provider=connection.provider,
        display_name=connection.display_name,
        authorisation_mode=connection.authorisation_mode,
        external_workspace_id=connection.external_workspace_id,
        external_workspace_name=connection.external_workspace_name,
        external_workspace_url=connection.external_workspace_url,
        status=connection.status,
        created_by_user_id=connection.created_by_user_id,
        last_synced_at=connection.last_synced_at,
        last_error_code=connection.last_error_code,
        last_error_summary=connection.last_error_summary,
        metadata_json=dict(connection.metadata_json or {}),
        disconnected_at=connection.disconnected_at,
        created_at=connection.created_at,
        updated_at=connection.updated_at,
        caller_authorisation=(
            to_authorisation_summary(caller_authorisation)
            if caller_authorisation is not None
            else None
        ),
    )


def _pkce_challenge(code_verifier: str) -> str:
    digest = hashlib.sha256(code_verifier.encode("ascii")).digest()
    return base64.urlsafe_b64encode(digest).decode("ascii").rstrip("=")


def _normalize_origin(raw_url: str) -> str:
    parsed = urlparse(raw_url.strip())
    return f"{parsed.scheme.lower()}://{parsed.netloc.lower()}"


class SourceOAuthService:
    """Orchestrates delegated OAuth 2.0 initiation, single-use callback, and token refresh."""

    def __init__(
        self,
        *,
        session: Session,
        settings: Settings,
        integration_repo: IntegrationRepository,
        token_encryption: TokenEncryptionService,
        rbac_service: RbacService,
        audit_service: AuditService,
        http_transport: httpx.BaseTransport | None = None,
    ) -> None:
        self._session = session
        self._settings = settings
        self._repo = integration_repo
        self._encryption = token_encryption
        self._rbac = rbac_service
        self._audit = audit_service
        self._transport = http_transport

    def ensure_provider_enabled(self, provider: str) -> str:
        normalized = provider.strip().lower()
        if normalized == "slack":
            raise ConflictError(
                "Slack integration is disabled pending governance approval.",
                code="SLACK_INTEGRATION_DISABLED",
            )
        if normalized not in {
            IntegrationProvider.GITHUB.value,
            IntegrationProvider.JIRA.value,
        }:
            raise BadRequestError(
                f"Unsupported integration provider '{provider}'.",
                code="UNSUPPORTED_PROVIDER",
            )
        if (
            normalized == IntegrationProvider.GITHUB.value
            and not self._settings.integrations.github.enabled
        ):
            raise ServiceUnavailableError(
                "GitHub integration is not enabled on this server.",
                code="INTEGRATION_DISABLED",
            )
        if (
            normalized == IntegrationProvider.JIRA.value
            and not self._settings.integrations.jira.enabled
        ):
            raise ServiceUnavailableError(
                "Jira integration is not enabled on this server.",
                code="INTEGRATION_DISABLED",
            )
        return normalized

    def _validate_post_auth_redirect(self, redirect_after: str | None) -> str | None:
        if redirect_after is None:
            return None
        cleaned = redirect_after.strip()
        if not cleaned:
            return None
        parsed = urlparse(cleaned)
        if parsed.scheme.lower() not in {"http", "https"} or not parsed.netloc:
            raise BadRequestError(
                "Post-authorisation redirect URL must be a valid http(s) URL.",
                code="INVALID_REDIRECT_URL",
            )
        if parsed.username is not None or parsed.password is not None:
            raise BadRequestError(
                "Post-authorisation redirect URL must not contain userinfo.",
                code="INVALID_REDIRECT_URL",
            )

        origin = _normalize_origin(cleaned)
        allowed_origins = {
            _normalize_origin(item) for item in self._settings.cors_allowed_origins
        }
        explicit_urls = self._settings.integrations.allowed_post_auth_redirects
        allowed_explicit_prefixes = tuple(item.rstrip("/") for item in explicit_urls)
        allowed_explicit_origins = {_normalize_origin(item) for item in explicit_urls}

        if origin in allowed_origins or origin in allowed_explicit_origins:
            return cleaned
        if any(cleaned.rstrip("/").startswith(prefix) for prefix in allowed_explicit_prefixes):
            return cleaned

        raise BadRequestError(
            "Post-authorisation redirect target is not in the configured allowlist.",
            code="REDIRECT_URL_NOT_ALLOWLISTED",
        )

    def _effective_github_scopes(self) -> list[str]:
        gh = self._settings.integrations.github
        raw_scopes = [part.strip() for part in gh.oauth_scopes.split() if part.strip()]
        if gh.oauth_mode == "github_app":
            return [scope for scope in raw_scopes if scope != "repo"]
        if not gh.allow_classic_private_repo_scope:
            return [scope for scope in raw_scopes if scope != "repo"]
        return raw_scopes

    def start_oauth(
        self,
        *,
        org_ctx: OrganisationContext,
        provider: str,
        display_name: str | None = None,
        redirect_after: str | None = None,
        source_connection_id: uuid.UUID | None = None,
    ) -> OAuthStartResponse:
        """Create a cryptographic single-use state + pending/target connection and OAuth URL."""
        normalized_provider = self.ensure_provider_enabled(provider)
        validated_redirect = self._validate_post_auth_redirect(redirect_after)
        actor_user_id = org_ctx.principal.user.id
        org_id = org_ctx.organisation.id

        connection: SourceConnection | None = None
        if source_connection_id is not None:
            connection = self._repo.get_connection_by_id(source_connection_id)
            if connection is None or connection.organisation_id != org_id:
                raise NotFoundError(
                    "Source connection was not found in this organisation.",
                    code="SOURCE_CONNECTION_NOT_FOUND",
                )
            if connection.provider != normalized_provider:
                raise BadRequestError(
                    "Source connection provider does not match requested OAuth provider.",
                    code="PROVIDER_MISMATCH",
                )
            if connection.status == SourceConnectionStatus.DISCONNECTED.value:
                raise ConflictError(
                    "Source connection has been disconnected and cannot accept new authorisations.",
                    code="CONNECTION_DISCONNECTED",
                )
        else:
            cleaned_name = (display_name or "").strip() or (
                f"{normalized_provider.title()} Workspace Connection"
            )
            connection = self._repo.create_connection(
                organisation_id=org_id,
                provider=normalized_provider,
                display_name=cleaned_name[:200],
                created_by_user_id=actor_user_id,
                status=SourceConnectionStatus.PENDING_AUTH.value,
                metadata_json={"created_via": "oauth_start"},
            )

        raw_state = secrets.token_urlsafe(32)
        state_hash = hash_opaque_token(raw_state)
        code_verifier = secrets.token_urlsafe(64)
        code_challenge = _pkce_challenge(code_verifier)
        encrypted_verifier = self._encryption.encrypt_token(
            plaintext=code_verifier,
            organisation_id=org_id,
            user_id=actor_user_id,
            provider=normalized_provider,
            token_kind=TokenKind.PKCE_VERIFIER,
        )
        now = utc_now()
        expires_at = now + timedelta(
            minutes=self._settings.integrations.oauth_state_expire_minutes
        )

        state_row = self._repo.create_oauth_state(
            state_hash=state_hash,
            organisation_id=org_id,
            user_id=actor_user_id,
            source_connection_id=connection.id,
            provider=normalized_provider,
            encrypted_code_verifier=encrypted_verifier.ciphertext,
            code_verifier_key_id=encrypted_verifier.key_id,
            redirect_after=validated_redirect,
            expires_at=expires_at,
        )

        if normalized_provider == IntegrationProvider.GITHUB.value:
            gh = self._settings.integrations.github
            params: dict[str, str] = {
                "client_id": gh.client_id or "",
                "redirect_uri": gh.redirect_uri,
                "state": raw_state,
                "code_challenge": code_challenge,
                "code_challenge_method": "S256",
            }
            scopes = self._effective_github_scopes()
            if scopes and gh.oauth_mode == "oauth_app":
                params["scope"] = " ".join(scopes)
            authorisation_url = f"{gh.auth_base_url}/login/oauth/authorize?{urlencode(params)}"
        else:
            jira = self._settings.integrations.jira
            params = {
                "audience": "api.atlassian.com",
                "client_id": jira.client_id or "",
                "scope": jira.oauth_scopes,
                "redirect_uri": jira.redirect_uri,
                "state": raw_state,
                "response_type": "code",
                "prompt": "consent",
                "code_challenge": code_challenge,
                "code_challenge_method": "S256",
            }
            authorisation_url = f"{jira.auth_base_url}/authorize?{urlencode(params)}"

        self._audit.record_event(
            event_type="integration.oauth_started",
            resource_type="source_connection",
            actor_user_id=actor_user_id,
            organisation_id=org_id,
            resource_id=str(connection.id),
            metadata={
                "provider": normalized_provider,
                "state_id": str(state_row.id),
                "reused_connection": source_connection_id is not None,
            },
            message=f"Initiated delegated {normalized_provider} OAuth 2.0 authorisation flow.",
        )
        self._session.commit()

        return OAuthStartResponse(
            provider=normalized_provider,
            organisation_id=org_id,
            source_connection_id=connection.id,
            authorisation_url=authorisation_url,
            expires_at=expires_at,
            state_id=state_row.id,
        )

    def complete_oauth_callback(
        self,
        *,
        provider: str,
        principal: AuthenticatedPrincipal,
        code: str | None = None,
        state: str | None = None,
        oauth_error: str | None = None,
        oauth_error_description: str | None = None,
    ) -> OAuthCallbackResponse:
        """Validate single-use OAuth state, exchange PKCE code, and store encrypted tokens."""
        normalized_provider = self.ensure_provider_enabled(provider)
        if not state or not state.strip():
            raise BadRequestError("OAuth state parameter is missing.", code="OAUTH_STATE_MISSING")

        state_hash = hash_opaque_token(state.strip())
        oauth_state = self._repo.get_oauth_state_by_hash(state_hash, for_update=True)
        if oauth_state is None:
            raise BadRequestError("OAuth state parameter is invalid.", code="OAUTH_STATE_INVALID")

        if oauth_state.provider != normalized_provider:
            self._audit.record_event(
                event_type="integration.oauth_callback_failed",
                resource_type="oauth_state",
                actor_user_id=principal.user.id,
                organisation_id=oauth_state.organisation_id,
                resource_id=str(oauth_state.id),
                outcome=AuditOutcome.DENIED.value,
                metadata={"expected": oauth_state.provider, "actual": normalized_provider},
                message="Rejected OAuth callback with mismatched provider.",
                level=logging.WARNING,
            )
            self._session.commit()
            raise BadRequestError(
                "OAuth callback provider does not match issued state.",
                code="OAUTH_STATE_MISMATCH",
            )

        if oauth_state.user_id != principal.user.id:
            self._audit.record_event(
                event_type="integration.oauth_callback_failed",
                resource_type="oauth_state",
                actor_user_id=principal.user.id,
                organisation_id=oauth_state.organisation_id,
                resource_id=str(oauth_state.id),
                outcome=AuditOutcome.DENIED.value,
                metadata={"reason": "user_mismatch"},
                message="Blocked OAuth state belonging to a different authenticated user.",
                level=logging.WARNING,
            )
            self._session.commit()
            raise ForbiddenError(
                "OAuth state belongs to a different user session.",
                code="OAUTH_STATE_USER_MISMATCH",
            )

        # Ensure caller still holds active membership in target organisation.
        self._rbac.resolve_organisation_context(
            organisation_id=oauth_state.organisation_id,
            principal=principal,
        )

        if oauth_state.consumed_at is not None:
            self._audit.record_event(
                event_type="integration.oauth_callback_failed",
                resource_type="oauth_state",
                actor_user_id=principal.user.id,
                organisation_id=oauth_state.organisation_id,
                resource_id=str(oauth_state.id),
                outcome=AuditOutcome.DENIED.value,
                metadata={"reason": "state_replayed"},
                message="Rejected single-use OAuth state replay attempt.",
                level=logging.WARNING,
            )
            self._session.commit()
            raise ConflictError(
                "OAuth state has already been consumed.",
                code="OAUTH_STATE_REPLAYED",
            )

        now = utc_now()
        expires_at = ensure_utc(oauth_state.expires_at)
        if expires_at is None or expires_at <= now:
            oauth_state.consumed_at = now
            self._audit.record_event(
                event_type="integration.oauth_callback_failed",
                resource_type="oauth_state",
                actor_user_id=principal.user.id,
                organisation_id=oauth_state.organisation_id,
                resource_id=str(oauth_state.id),
                outcome=AuditOutcome.ERROR.value,
                metadata={"reason": "state_expired"},
                message="Rejected expired OAuth state.",
                level=logging.WARNING,
            )
            self._session.commit()
            raise GoneError(
                "OAuth authorisation state has expired. Please restart connection setup.",
                code="OAUTH_STATE_EXPIRED",
            )

        # Consume state before external exchange so callbacks are strictly single-use.
        oauth_state.consumed_at = now
        self._session.flush()

        if oauth_error:
            self._audit.record_event(
                event_type="integration.oauth_denied",
                resource_type="source_connection",
                actor_user_id=principal.user.id,
                organisation_id=oauth_state.organisation_id,
                resource_id=(
                    str(oauth_state.source_connection_id)
                    if oauth_state.source_connection_id
                    else str(oauth_state.id)
                ),
                outcome=AuditOutcome.DENIED.value,
                metadata={
                    "provider": normalized_provider,
                    "oauth_error": oauth_error[:64],
                },
                message=(
                    f"External OAuth consent denied or aborted ({oauth_error[:64]}): "
                    f"{(oauth_error_description or '')[:200]}"
                ),
                level=logging.WARNING,
            )
            self._session.commit()
            raise ForbiddenError(
                "External source authorisation was denied or cancelled.",
                code="OAUTH_ACCESS_DENIED",
            )

        if not code or not code.strip():
            self._session.commit()
            raise BadRequestError("OAuth authorisation code is missing.", code="OAUTH_CODE_MISSING")

        code_verifier = ""
        if oauth_state.encrypted_code_verifier:
            code_verifier = self._encryption.decrypt_token(
                ciphertext=oauth_state.encrypted_code_verifier,
                organisation_id=oauth_state.organisation_id,
                user_id=oauth_state.user_id,
                provider=normalized_provider,
                token_kind=TokenKind.PKCE_VERIFIER,
                key_id=oauth_state.code_verifier_key_id,
            )

        if oauth_state.source_connection_id is None:
            raise BadRequestError(
                "OAuth state lacks connection target.",
                code="OAUTH_STATE_INVALID",
            )
        connection = self._repo.get_connection_by_id(oauth_state.source_connection_id)
        if connection is None or connection.organisation_id != oauth_state.organisation_id:
            raise NotFoundError(
                "Source connection was not found.",
                code="SOURCE_CONNECTION_NOT_FOUND",
            )
        if connection.status == SourceConnectionStatus.DISCONNECTED.value:
            raise ConflictError(
                "Source connection was disconnected before OAuth completed.",
                code="CONNECTION_DISCONNECTED",
            )

        try:
            if normalized_provider == IntegrationProvider.GITHUB.value:
                auth_row, sites_count = self._exchange_github_and_store(
                    connection=connection,
                    user_id=principal.user.id,
                    code=code.strip(),
                    code_verifier=code_verifier,
                    now=now,
                )
            else:
                auth_row, sites_count = self._exchange_jira_and_store(
                    connection=connection,
                    user_id=principal.user.id,
                    code=code.strip(),
                    code_verifier=code_verifier,
                    now=now,
                )
        except IntegrationProviderError as exc:
            self._audit.record_event(
                event_type="integration.oauth_callback_failed",
                resource_type="source_connection",
                actor_user_id=principal.user.id,
                organisation_id=connection.organisation_id,
                resource_id=str(connection.id),
                outcome=AuditOutcome.ERROR.value,
                metadata={"provider": normalized_provider, "error_code": exc.code},
                message=f"OAuth token exchange failed: {exc.message}",
                level=logging.ERROR,
            )
            self._session.commit()
            raise ServiceUnavailableError(
                exc.message,
                code=exc.code,
            ) from exc

        self._audit.record_event(
            event_type="integration.oauth_connected",
            resource_type="source_connection",
            actor_user_id=principal.user.id,
            organisation_id=connection.organisation_id,
            resource_id=str(connection.id),
            metadata={
                "provider": normalized_provider,
                "authorisation_id": str(auth_row.id),
                "external_user_id": auth_row.external_user_id,
                "granted_scopes": auth_row.granted_scopes,
                "discovered_sites_count": sites_count,
            },
            message=f"Connected delegated {normalized_provider} credentials for user.",
        )
        self._session.commit()
        self._session.refresh(connection)
        self._session.refresh(auth_row)

        return OAuthCallbackResponse(
            connection=to_source_connection_response(connection, caller_authorisation=auth_row),
            authorisation=to_authorisation_summary(auth_row),
            redirect_after=oauth_state.redirect_after,
            discovered_sites_count=sites_count,
        )

    def _exchange_github_and_store(
        self,
        *,
        connection: SourceConnection,
        user_id: uuid.UUID,
        code: str,
        code_verifier: str,
        now: datetime,
    ) -> tuple[UserSourceAuthorisation, int | None]:
        gh = self._settings.integrations.github
        client_secret = gh.client_secret.get_secret_value() if gh.client_secret else ""
        with create_integration_http_client(
            timeout_seconds=self._settings.integrations.http_timeout_seconds,
            transport=self._transport,
        ) as client:
            token_resp = client.post(
                f"{gh.auth_base_url}/login/oauth/access_token",
                headers={"Accept": "application/json"},
                data={
                    "client_id": gh.client_id or "",
                    "client_secret": client_secret,
                    "code": code,
                    "redirect_uri": gh.redirect_uri,
                    "code_verifier": code_verifier,
                },
            )
            raise_for_provider_error(token_resp, provider="github", endpoint_label="oauth_token")
            token_json = token_resp.json()
            if token_json.get("error"):
                raise IntegrationProviderError(
                    provider="github",
                    code="GITHUB_OAUTH_EXCHANGE_FAILED",
                    message=(
                        f"GitHub rejected OAuth code exchange ({token_json.get('error')})."
                    ),
                    status_code=400,
                )
            access_token = str(token_json.get("access_token") or "")
            if not access_token:
                raise IntegrationProviderError(
                    provider="github",
                    code="GITHUB_OAUTH_MISSING_TOKEN",
                    message="GitHub OAuth response did not contain an access token.",
                    status_code=502,
                )
            refresh_token = (
                str(token_json["refresh_token"])
                if token_json.get("refresh_token")
                else None
            )
            expires_in = token_json.get("expires_in")
            token_expires_at = (
                now + timedelta(seconds=int(expires_in))
                if isinstance(expires_in, (int, float)) and int(expires_in) > 0
                else None
            )
            raw_scope = str(token_json.get("scope") or "")
            granted_scopes = [
                part.strip() for part in raw_scope.replace(",", " ").split() if part.strip()
            ]
            token_type = str(token_json.get("token_type") or "bearer")

            headers = {
                "Authorization": f"Bearer {access_token}",
                "Accept": "application/vnd.github+json",
                "User-Agent": "IPKRH-Platform/0.1",
            }
            user_resp = client.get(f"{gh.api_base_url}/user", headers=headers)
            raise_for_provider_error(user_resp, provider="github", endpoint_label="user_profile")
            user_json = user_resp.json()
            external_user_id = str(user_json.get("id") or "")
            external_username = (
                str(user_json.get("login")) if user_json.get("login") else None
            )
            external_email = (
                str(user_json.get("email")) if user_json.get("email") else None
            )
            if not external_user_id:
                raise IntegrationProviderError(
                    provider="github",
                    code="GITHUB_IDENTITY_MISSING",
                    message="GitHub user profile did not include numeric account identifier.",
                    status_code=502,
                )
            if not external_email:
                emails_resp = client.get(f"{gh.api_base_url}/user/emails", headers=headers)
                if emails_resp.status_code == 200:
                    emails_data = emails_resp.json()
                    if isinstance(emails_data, list):
                        primary = next(
                            (
                                item.get("email")
                                for item in emails_data
                                if isinstance(item, dict)
                                and item.get("primary")
                                and item.get("verified")
                            ),
                            None,
                        )
                        if primary:
                            external_email = str(primary)

        enc_access = self._encryption.encrypt_token(
            plaintext=access_token,
            organisation_id=connection.organisation_id,
            user_id=user_id,
            provider="github",
            token_kind=TokenKind.ACCESS_TOKEN,
        )
        enc_refresh_value: str | None = None
        if refresh_token:
            enc_refresh = self._encryption.encrypt_token(
                plaintext=refresh_token,
                organisation_id=connection.organisation_id,
                user_id=user_id,
                provider="github",
                token_kind=TokenKind.REFRESH_TOKEN,
            )
            enc_refresh_value = enc_refresh.ciphertext

        auth_row = self._repo.replace_active_authorisation(
            source_connection_id=connection.id,
            organisation_id=connection.organisation_id,
            user_id=user_id,
            provider="github",
            external_user_id=external_user_id,
            external_username=external_username,
            external_email=external_email,
            encrypted_access_token=enc_access.ciphertext,
            encrypted_refresh_token=enc_refresh_value,
            token_encryption_algorithm=enc_access.encryption_algorithm,
            token_key_id=enc_access.key_id,
            token_type=token_type,
            granted_scopes=granted_scopes,
            token_expires_at=token_expires_at,
            metadata_json={"oauth_mode": gh.oauth_mode},
            now=now,
        )
        connection.status = SourceConnectionStatus.ACTIVE.value
        connection.last_error_code = None
        connection.last_error_summary = None
        if not connection.external_workspace_name and external_username:
            connection.external_workspace_name = f"github.com/{external_username}"
            connection.external_workspace_url = "https://github.com"
        return auth_row, None

    def _exchange_jira_and_store(
        self,
        *,
        connection: SourceConnection,
        user_id: uuid.UUID,
        code: str,
        code_verifier: str,
        now: datetime,
    ) -> tuple[UserSourceAuthorisation, int]:
        jira = self._settings.integrations.jira
        client_secret = jira.client_secret.get_secret_value() if jira.client_secret else ""
        with create_integration_http_client(
            timeout_seconds=self._settings.integrations.http_timeout_seconds,
            transport=self._transport,
        ) as client:
            token_resp = client.post(
                f"{jira.auth_base_url}/oauth/token",
                headers={"Accept": "application/json"},
                json={
                    "grant_type": "authorization_code",
                    "client_id": jira.client_id or "",
                    "client_secret": client_secret,
                    "code": code,
                    "redirect_uri": jira.redirect_uri,
                    "code_verifier": code_verifier,
                },
            )
            raise_for_provider_error(token_resp, provider="jira", endpoint_label="oauth_token")
            token_json = token_resp.json()
            access_token = str(token_json.get("access_token") or "")
            if not access_token:
                raise IntegrationProviderError(
                    provider="jira",
                    code="JIRA_OAUTH_MISSING_TOKEN",
                    message="Atlassian OAuth response did not include an access token.",
                    status_code=502,
                )
            refresh_token = (
                str(token_json["refresh_token"])
                if token_json.get("refresh_token")
                else None
            )
            expires_in = token_json.get("expires_in")
            token_expires_at = (
                now + timedelta(seconds=int(expires_in))
                if isinstance(expires_in, (int, float)) and int(expires_in) > 0
                else None
            )
            granted_scopes = [
                part.strip()
                for part in str(token_json.get("scope") or "").split()
                if part.strip()
            ]
            token_type = str(token_json.get("token_type") or "Bearer")

            headers = {
                "Authorization": f"Bearer {access_token}",
                "Accept": "application/json",
            }
            sites_resp = client.get(
                f"{jira.api_base_url}/oauth/token/accessible-resources",
                headers=headers,
            )
            raise_for_provider_error(
                sites_resp,
                provider="jira",
                endpoint_label="accessible_resources",
            )
            raw_sites = sites_resp.json()
            accessible_sites: list[dict[str, Any]] = []
            if isinstance(raw_sites, list):
                for site in raw_sites:
                    if isinstance(site, dict) and site.get("id"):
                        accessible_sites.append(
                            {
                                "cloud_id": str(site["id"]),
                                "name": str(site.get("name") or site["id"]),
                                "url": str(site["url"]) if site.get("url") else None,
                                "scopes": [str(s) for s in (site.get("scopes") or [])],
                                "avatar_url": (
                                    str(site["avatarUrl"]) if site.get("avatarUrl") else None
                                ),
                            }
                        )

            external_user_id = ""
            external_username: str | None = None
            external_email: str | None = None
            if accessible_sites:
                first_cloud_id = accessible_sites[0]["cloud_id"]
                myself_resp = client.get(
                    f"{jira.api_base_url}/ex/jira/{first_cloud_id}/rest/api/3/myself",
                    headers=headers,
                )
                if myself_resp.status_code == 200:
                    me = myself_resp.json()
                    external_user_id = str(me.get("accountId") or "")
                    external_username = (
                        str(me.get("displayName")) if me.get("displayName") else None
                    )
                    external_email = (
                        str(me.get("emailAddress")) if me.get("emailAddress") else None
                    )
            if not external_user_id:
                me_resp = client.get(f"{jira.api_base_url}/me", headers=headers)
                if me_resp.status_code == 200:
                    me = me_resp.json()
                    external_user_id = str(me.get("account_id") or "")
                    external_username = str(me.get("name")) if me.get("name") else None
                    external_email = str(me.get("email")) if me.get("email") else None
            if not external_user_id:
                raise IntegrationProviderError(
                    provider="jira",
                    code="JIRA_IDENTITY_MISSING",
                    message="Could not resolve Jira Cloud account identity for OAuth user.",
                    status_code=502,
                )

        enc_access = self._encryption.encrypt_token(
            plaintext=access_token,
            organisation_id=connection.organisation_id,
            user_id=user_id,
            provider="jira",
            token_kind=TokenKind.ACCESS_TOKEN,
        )
        enc_refresh_value: str | None = None
        if refresh_token:
            enc_refresh = self._encryption.encrypt_token(
                plaintext=refresh_token,
                organisation_id=connection.organisation_id,
                user_id=user_id,
                provider="jira",
                token_kind=TokenKind.REFRESH_TOKEN,
            )
            enc_refresh_value = enc_refresh.ciphertext

        auth_row = self._repo.replace_active_authorisation(
            source_connection_id=connection.id,
            organisation_id=connection.organisation_id,
            user_id=user_id,
            provider="jira",
            external_user_id=external_user_id,
            external_username=external_username,
            external_email=external_email,
            encrypted_access_token=enc_access.ciphertext,
            encrypted_refresh_token=enc_refresh_value,
            token_encryption_algorithm=enc_access.encryption_algorithm,
            token_key_id=enc_access.key_id,
            token_type=token_type,
            granted_scopes=granted_scopes,
            token_expires_at=token_expires_at,
            metadata_json={"accessible_sites": accessible_sites},
            now=now,
        )
        connection.status = SourceConnectionStatus.ACTIVE.value
        connection.last_error_code = None
        connection.last_error_summary = None
        if accessible_sites and not connection.external_workspace_id:
            connection.external_workspace_id = accessible_sites[0]["cloud_id"]
            connection.external_workspace_name = accessible_sites[0]["name"]
            connection.external_workspace_url = accessible_sites[0]["url"]
        return auth_row, len(accessible_sites)

    def get_valid_access_token(
        self,
        *,
        authorisation_id: uuid.UUID,
        leeway_seconds: int = 60,
    ) -> tuple[str, UserSourceAuthorisation]:
        """Decrypt the user's active access token or atomically refresh if expiring."""
        auth = self._repo.get_authorisation_by_id(authorisation_id)
        if auth is None or auth.status != UserSourceAuthorisationStatus.ACTIVE.value:
            raise IntegrationAuthError(
                provider=auth.provider if auth else "unknown",
                code="AUTHORISATION_INACTIVE",
                message="Delegated source authorisation is inactive or revoked.",
            )
        connection = self._repo.get_connection_by_id(auth.source_connection_id)
        if connection is None or connection.status == SourceConnectionStatus.DISCONNECTED.value:
            raise IntegrationAuthError(
                provider=auth.provider,
                code="CONNECTION_DISCONNECTED",
                message="Parent source connection has been disconnected.",
            )

        now = utc_now()
        exp = ensure_utc(auth.token_expires_at)
        if exp is not None and exp <= now + timedelta(seconds=leeway_seconds):
            return self.refresh_access_token(authorisation_id=auth.id, force=False)

        access_token = self._encryption.decrypt_token(
            ciphertext=auth.encrypted_access_token,
            organisation_id=auth.organisation_id,
            user_id=auth.user_id,
            provider=auth.provider,
            token_kind=TokenKind.ACCESS_TOKEN,
            key_id=auth.token_key_id,
        )
        return access_token, auth

    def refresh_access_token(
        self,
        *,
        authorisation_id: uuid.UUID,
        force: bool = True,
    ) -> tuple[str, UserSourceAuthorisation]:
        """Atomically rotate a single-use OAuth refresh token using DB row locking."""
        auth = self._repo.get_authorisation_for_update(authorisation_id)
        if auth is None or auth.status not in {
            UserSourceAuthorisationStatus.ACTIVE.value,
            UserSourceAuthorisationStatus.EXPIRED.value,
        }:
            raise IntegrationAuthError(
                provider=auth.provider if auth else "unknown",
                code="AUTHORISATION_INACTIVE",
                message="Delegated source authorisation is revoked or missing.",
            )

        now = utc_now()
        exp = ensure_utc(auth.token_expires_at)
        if not force and exp is not None and exp > now + timedelta(seconds=60):
            # Another concurrent worker already rotated this token cleanly.
            token = self._encryption.decrypt_token(
                ciphertext=auth.encrypted_access_token,
                organisation_id=auth.organisation_id,
                user_id=auth.user_id,
                provider=auth.provider,
                token_kind=TokenKind.ACCESS_TOKEN,
                key_id=auth.token_key_id,
            )
            return token, auth

        if not auth.encrypted_refresh_token:
            auth.status = UserSourceAuthorisationStatus.EXPIRED.value
            auth.last_error_code = "REAUTH_REQUIRED"
            auth.last_error_summary = "Access token expired and no refresh token is available."
            self._audit.record_event(
                event_type="integration.token_refresh_failed",
                resource_type="user_source_authorisation",
                actor_user_id=auth.user_id,
                organisation_id=auth.organisation_id,
                resource_id=str(auth.id),
                outcome=AuditOutcome.ERROR.value,
                metadata={"provider": auth.provider, "reason": "missing_refresh_token"},
                message="Source authorisation expired without refresh token.",
                level=logging.WARNING,
            )
            self._session.commit()
            raise IntegrationAuthError(
                provider=auth.provider,
                code="REAUTH_REQUIRED",
                message="Delegated source token expired and requires re-authorisation.",
            )

        refresh_plaintext = self._encryption.decrypt_token(
            ciphertext=auth.encrypted_refresh_token,
            organisation_id=auth.organisation_id,
            user_id=auth.user_id,
            provider=auth.provider,
            token_kind=TokenKind.REFRESH_TOKEN,
            key_id=auth.token_key_id,
        )

        new_access: str = ""
        new_refresh: str | None = None
        new_expires_at: datetime | None = auth.token_expires_at

        try:
            with create_integration_http_client(
                timeout_seconds=self._settings.integrations.http_timeout_seconds,
                transport=self._transport,
            ) as client:
                if auth.provider == IntegrationProvider.JIRA.value:
                    jira = self._settings.integrations.jira
                    secret = jira.client_secret.get_secret_value() if jira.client_secret else ""
                    resp = client.post(
                        f"{jira.auth_base_url}/oauth/token",
                        headers={"Accept": "application/json"},
                        json={
                            "grant_type": "refresh_token",
                            "client_id": jira.client_id or "",
                            "client_secret": secret,
                            "refresh_token": refresh_plaintext,
                        },
                    )
                else:
                    gh = self._settings.integrations.github
                    secret = gh.client_secret.get_secret_value() if gh.client_secret else ""
                    resp = client.post(
                        f"{gh.auth_base_url}/login/oauth/access_token",
                        headers={"Accept": "application/json"},
                        data={
                            "grant_type": "refresh_token",
                            "client_id": gh.client_id or "",
                            "client_secret": secret,
                            "refresh_token": refresh_plaintext,
                        },
                    )

                if resp.status_code in {400, 401, 403}:
                    raise IntegrationAuthError(
                        provider=auth.provider,
                        code="TOKEN_REFRESH_REJECTED",
                        message=f"{auth.provider.title()} rejected refresh token rotation.",
                        status_code=resp.status_code,
                    )
                raise_for_provider_error(
                    resp,
                    provider=auth.provider,
                    endpoint_label="oauth_refresh",
                )
                payload = resp.json()
                if payload.get("error"):
                    raise IntegrationAuthError(
                        provider=auth.provider,
                        code="TOKEN_REFRESH_REJECTED",
                        message=(
                            f"{auth.provider.title()} refresh failed ({payload.get('error')})."
                        ),
                        status_code=400,
                    )
                new_access = str(payload.get("access_token") or "")
                if not new_access:
                    raise IntegrationAuthError(
                        provider=auth.provider,
                        code="TOKEN_REFRESH_MISSING_ACCESS",
                        message="Refresh response did not include an access token.",
                    )
                if payload.get("refresh_token"):
                    new_refresh = str(payload["refresh_token"])
                if isinstance(payload.get("expires_in"), (int, float)):
                    new_expires_at = now + timedelta(seconds=int(payload["expires_in"]))
        except IntegrationAuthError as exc:
            auth.status = UserSourceAuthorisationStatus.EXPIRED.value
            auth.last_error_code = exc.code
            auth.last_error_summary = exc.message
            conn = self._repo.get_connection_by_id(auth.source_connection_id)
            if conn is not None and conn.status == SourceConnectionStatus.ACTIVE.value:
                conn.status = SourceConnectionStatus.REAUTH_REQUIRED.value
                conn.last_error_code = exc.code
                conn.last_error_summary = exc.message
            self._audit.record_event(
                event_type="integration.token_refresh_failed",
                resource_type="user_source_authorisation",
                actor_user_id=auth.user_id,
                organisation_id=auth.organisation_id,
                resource_id=str(auth.id),
                outcome=AuditOutcome.ERROR.value,
                metadata={"provider": auth.provider, "error_code": exc.code},
                message=exc.message,
                level=logging.WARNING,
            )
            self._session.commit()
            raise

        enc_access = self._encryption.encrypt_token(
            plaintext=new_access,
            organisation_id=auth.organisation_id,
            user_id=auth.user_id,
            provider=auth.provider,
            token_kind=TokenKind.ACCESS_TOKEN,
        )
        auth.encrypted_access_token = enc_access.ciphertext
        auth.token_encryption_algorithm = enc_access.encryption_algorithm
        auth.token_key_id = enc_access.key_id
        if new_refresh:
            enc_refresh = self._encryption.encrypt_token(
                plaintext=new_refresh,
                organisation_id=auth.organisation_id,
                user_id=auth.user_id,
                provider=auth.provider,
                token_kind=TokenKind.REFRESH_TOKEN,
            )
            auth.encrypted_refresh_token = enc_refresh.ciphertext
        auth.token_expires_at = new_expires_at
        auth.last_refreshed_at = now
        auth.last_verified_at = now
        auth.status = UserSourceAuthorisationStatus.ACTIVE.value
        auth.last_error_code = None
        auth.last_error_summary = None

        self._audit.record_event(
            event_type="integration.token_refreshed",
            resource_type="user_source_authorisation",
            actor_user_id=auth.user_id,
            organisation_id=auth.organisation_id,
            resource_id=str(auth.id),
            metadata={"provider": auth.provider, "rotated_refresh_token": new_refresh is not None},
            message=f"Refreshed delegated {auth.provider} OAuth credentials atomically.",
        )
        self._session.commit()
        return new_access, auth
