"""Dedicated OAuth token and verifier encryption service keyed separately from file storage."""

from __future__ import annotations

import base64
import logging
import os
import uuid
from dataclasses import dataclass
from enum import StrEnum
from typing import Protocol

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.hkdf import HKDF

from app.core.exceptions import ServiceUnavailableError

logger = logging.getLogger("app.services.token_encryption")

_TOKEN_ENCRYPTION_ALGORITHM = "AES-256-GCM"  # noqa: S105
_LOCAL_TOKEN_KEY_ID = "token-local-v1"  # noqa: S105
_CIPHER_VERSION_PREFIX = "v1:"
_NONCE_SIZE = 12


class TokenKind(StrEnum):
    """Canonical AAD domain tags separating encrypted secret kinds."""

    ACCESS_TOKEN = "access_token"  # noqa: S105
    REFRESH_TOKEN = "refresh_token"  # noqa: S105
    PKCE_VERIFIER = "pkce_verifier"  # noqa: S105


@dataclass(frozen=True, slots=True)
class EncryptedTokenPayload:
    """Ciphertext and key-version metadata stored in PostgreSQL without plaintext tokens."""

    ciphertext: str
    encryption_algorithm: str
    key_id: str


class TokenEncryptionService(Protocol):
    """Replaceable encryption boundary allowing seamless swap from env keys to KMS/Vault."""

    def encrypt_token(
        self,
        *,
        plaintext: str,
        organisation_id: uuid.UUID,
        user_id: uuid.UUID,
        provider: str,
        token_kind: str,
    ) -> EncryptedTokenPayload:
        """Encrypt a secret token or PKCE verifier bound to tenant/user/provider context."""

    def decrypt_token(
        self,
        *,
        ciphertext: str,
        organisation_id: uuid.UUID,
        user_id: uuid.UUID,
        provider: str,
        token_kind: str,
        key_id: str | None = None,
    ) -> str:
        """Verify AAD and decrypt an encrypted token strictly inside trusted backend/worker."""


def _derive_token_aes_key(raw_secret: str) -> bytes:
    """Derive a dedicated 256-bit key exclusively from `TOKEN_ENCRYPTION_KEY`."""
    secret_bytes = raw_secret.encode("utf-8")
    if len(secret_bytes) < 16:
        raise ValueError("TOKEN_ENCRYPTION_KEY must be at least 16 bytes.")
    hkdf = HKDF(
        algorithm=hashes.SHA256(),
        length=32,
        salt=b"ipkrh-oauth-token-salt-v1",
        info=b"ipkrh-oauth-token-aes-256-gcm-v1",
    )
    return hkdf.derive(secret_bytes)


def _build_token_aad(
    *,
    organisation_id: uuid.UUID,
    user_id: uuid.UUID,
    provider: str,
    token_kind: str,
) -> bytes:
    return f"{organisation_id}:{user_id}:{provider}:{token_kind}".encode()


class LocalTokenEncryptionService:
    """Local AES-256-GCM OAuth token cipher derived strictly from `TOKEN_ENCRYPTION_KEY`."""

    def __init__(self, *, token_encryption_key: str) -> None:
        self._aes_key = _derive_token_aes_key(token_encryption_key)

    def encrypt_token(
        self,
        *,
        plaintext: str,
        organisation_id: uuid.UUID,
        user_id: uuid.UUID,
        provider: str,
        token_kind: str,
    ) -> EncryptedTokenPayload:
        if not plaintext:
            raise ValueError("Token plaintext must not be empty.")
        nonce = os.urandom(_NONCE_SIZE)
        aad = _build_token_aad(
            organisation_id=organisation_id,
            user_id=user_id,
            provider=provider,
            token_kind=token_kind,
        )
        sealed = AESGCM(self._aes_key).encrypt(nonce, plaintext.encode("utf-8"), aad)
        encoded = base64.urlsafe_b64encode(nonce + sealed).decode("ascii")
        return EncryptedTokenPayload(
            ciphertext=f"{_CIPHER_VERSION_PREFIX}{encoded}",
            encryption_algorithm=_TOKEN_ENCRYPTION_ALGORITHM,
            key_id=_LOCAL_TOKEN_KEY_ID,
        )

    def decrypt_token(
        self,
        *,
        ciphertext: str,
        organisation_id: uuid.UUID,
        user_id: uuid.UUID,
        provider: str,
        token_kind: str,
        key_id: str | None = None,
    ) -> str:
        if key_id is not None and key_id != _LOCAL_TOKEN_KEY_ID:
            raise ServiceUnavailableError(
                "Stored source credential references an unsupported encryption key version.",
                code="TOKEN_KEY_UNSUPPORTED",
            )
        if not ciphertext.startswith(_CIPHER_VERSION_PREFIX):
            raise ServiceUnavailableError(
                "Stored source credential has an invalid encryption envelope.",
                code="TOKEN_DECRYPTION_FAILED",
            )
        encoded_payload = ciphertext[len(_CIPHER_VERSION_PREFIX) :]
        try:
            raw = base64.urlsafe_b64decode(encoded_payload.encode("ascii"))
            if len(raw) < _NONCE_SIZE + 16:
                raise ValueError("Truncated encrypted token payload.")
            nonce = raw[:_NONCE_SIZE]
            sealed = raw[_NONCE_SIZE:]
            aad = _build_token_aad(
                organisation_id=organisation_id,
                user_id=user_id,
                provider=provider,
                token_kind=token_kind,
            )
            decrypted_bytes = AESGCM(self._aes_key).decrypt(nonce, sealed, aad)
            return decrypted_bytes.decode("utf-8")
        except InvalidTag as exc:
            logger.error("Token AEAD integrity check failed during credential decryption.")
            raise ServiceUnavailableError(
                "Stored source credential failed integrity verification.",
                code="TOKEN_INTEGRITY_FAILED",
            ) from exc
        except ServiceUnavailableError:
            raise
        except Exception as exc:
            logger.error("Failed to decrypt stored source credential (%s).", type(exc).__name__)
            raise ServiceUnavailableError(
                "Stored source credential could not be decrypted.",
                code="TOKEN_DECRYPTION_FAILED",
            ) from exc
