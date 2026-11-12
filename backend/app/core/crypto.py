"""Cryptographic utilities for symmetric encryption of sensitive source tokens and files at rest."""

from __future__ import annotations

import base64
import hashlib

from cryptography.fernet import Fernet
from pydantic import SecretStr


def _derive_fernet_key(raw_key: str | SecretStr) -> bytes:
    """Derive a canonical 32-byte Fernet key from any configured secret string."""
    key_str = raw_key.get_secret_value() if isinstance(raw_key, SecretStr) else raw_key
    key_bytes = key_str.encode("utf-8")

    # If already a valid 32-byte url-safe base64 key, verify Fernet compatibility directly
    if len(key_bytes) == 44:
        try:
            decoded = base64.urlsafe_b64decode(key_bytes)
            if len(decoded) == 32:
                return key_bytes
        except ValueError:
            pass

    # Otherwise, derive a predictable 32-byte key via SHA-256 and urlsafe base64 encode it
    digest = hashlib.sha256(key_bytes).digest()
    return base64.urlsafe_b64encode(digest)


def encrypt_token(plain_token: str, key: str | SecretStr) -> str:
    """Encrypt a sensitive OAuth or Personal Access Token for secure storage in PostgreSQL."""
    fernet_key = _derive_fernet_key(key)
    f = Fernet(fernet_key)
    encrypted_bytes = f.encrypt(plain_token.encode("utf-8"))
    return encrypted_bytes.decode("utf-8")


def decrypt_token(cipher_text: str, key: str | SecretStr) -> str:
    """Decrypt a previously encrypted OAuth or Personal Access Token from PostgreSQL."""
    fernet_key = _derive_fernet_key(key)
    f = Fernet(fernet_key)
    decrypted_bytes = f.decrypt(cipher_text.encode("utf-8"))
    return decrypted_bytes.decode("utf-8")


def encrypt_bytes(raw_bytes: bytes, key: str | SecretStr) -> bytes:
    """Encrypt raw file bytes for encrypted-at-rest document storage on disk."""
    fernet_key = _derive_fernet_key(key)
    f = Fernet(fernet_key)
    return f.encrypt(raw_bytes)


def decrypt_bytes(cipher_bytes: bytes, key: str | SecretStr) -> bytes:
    """Decrypt raw file bytes previously encrypted at rest on disk."""
    fernet_key = _derive_fernet_key(key)
    f = Fernet(fernet_key)
    return f.decrypt(cipher_bytes)
