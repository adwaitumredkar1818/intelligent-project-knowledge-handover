"""Pure validation and UTC timestamp helpers with zero internal app imports."""

from __future__ import annotations

import re
from datetime import UTC, datetime

_EMAIL_LOCAL_RE = re.compile(r"^[A-Za-z0-9.!#$%&'*+/=?^_`{|}~-]+$")
_EMAIL_DOMAIN_LABEL_RE = re.compile(r"^[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?$")
_SLUG_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
_SLUG_SEPARATOR_RE = re.compile(r"[^a-z0-9]+")

_PASSWORD_MIN_LENGTH = 12
_PASSWORD_MAX_LENGTH = 128


def normalize_display_name(
    value: str,
    *,
    field_label: str = "Name",
    min_len: int = 2,
    max_len: int = 200,
) -> str:
    """Collapse internal whitespace and validate non-empty display names."""
    cleaned = " ".join(value.strip().split())
    if len(cleaned) < min_len:
        raise ValueError(f"{field_label} must be at least {min_len} characters long.")
    if len(cleaned) > max_len:
        raise ValueError(f"{field_label} must not exceed {max_len} characters.")
    return cleaned


def normalize_and_validate_slug(
    value: str,
    *,
    field_label: str = "Slug",
    min_len: int = 2,
    max_len: int = 120,
) -> str:
    """Normalise to trimmed lowercase and enforce strict URL-safe slug syntax."""
    cleaned = value.strip().lower()
    if len(cleaned) < min_len:
        raise ValueError(f"{field_label} must be at least {min_len} characters long.")
    if len(cleaned) > max_len:
        raise ValueError(f"{field_label} must not exceed {max_len} characters.")
    if not _SLUG_RE.fullmatch(cleaned):
        raise ValueError(
            f"{field_label} must contain only lowercase alphanumeric segments "
            "separated by single hyphens."
        )
    return cleaned


def derive_slug_from_name(
    name: str,
    *,
    field_label: str = "Slug",
    min_len: int = 2,
    max_len: int = 120,
) -> str:
    """Derive a normalised URL-safe slug from a human-readable name."""
    raw = _SLUG_SEPARATOR_RE.sub("-", name.strip().lower()).strip("-")
    if len(raw) > max_len:
        raw = raw[:max_len].rstrip("-")
    return normalize_and_validate_slug(
        raw,
        field_label=field_label,
        min_len=min_len,
        max_len=max_len,
    )


def utc_now() -> datetime:
    """Return the current UTC timezone-aware timestamp."""
    return datetime.now(UTC)


def ensure_utc(value: datetime) -> datetime:
    """Normalise naive (e.g. SQLite) or offset timestamps cleanly to UTC."""
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def normalize_and_validate_email(value: str) -> str:
    """Normalise email to trimmed lowercase and verify structural validity."""
    cleaned = value.strip().lower()
    if not cleaned or len(cleaned) > 254 or any(ch.isspace() for ch in cleaned):
        raise ValueError("Enter a valid email address.")
    if cleaned.count("@") != 1:
        raise ValueError("Enter a valid email address.")

    local_part, domain_part = cleaned.split("@", 1)
    if (
        not local_part
        or len(local_part) > 64
        or local_part.startswith(".")
        or local_part.endswith(".")
        or ".." in local_part
        or not _EMAIL_LOCAL_RE.fullmatch(local_part)
    ):
        raise ValueError("Enter a valid email address.")

    labels = domain_part.split(".")
    if (
        len(labels) < 2
        or len(domain_part) > 253
        or any(not label or not _EMAIL_DOMAIN_LABEL_RE.fullmatch(label) for label in labels)
        or len(labels[-1]) < 2
        or labels[-1].isdigit()
    ):
        raise ValueError("Enter a valid email address.")

    return cleaned


def validate_password_strength(password: str, *, email: str | None = None) -> str:
    """Validate strong password requirements without altering the submitted secret."""
    if len(password) < _PASSWORD_MIN_LENGTH:
        raise ValueError(
            f"Password must be at least {_PASSWORD_MIN_LENGTH} characters long."
        )
    if len(password) > _PASSWORD_MAX_LENGTH:
        raise ValueError(
            f"Password must not exceed {_PASSWORD_MAX_LENGTH} characters."
        )
    if not password.strip():
        raise ValueError("Password must not consist solely of whitespace.")

    has_lower = any(ch.islower() for ch in password)
    has_upper = any(ch.isupper() for ch in password)
    has_digit = any(ch.isdigit() for ch in password)
    has_special = any(not ch.isalnum() and not ch.isspace() for ch in password)
    if not (has_lower and has_upper and has_digit and has_special):
        raise ValueError(
            "Password must include uppercase, lowercase, numeric, and special characters."
        )

    if email:
        lowered_pw = password.lower()
        normalized_email = email.strip().lower()
        local_part = normalized_email.split("@", 1)[0] if "@" in normalized_email else ""
        if normalized_email in lowered_pw or (len(local_part) >= 4 and local_part in lowered_pw):
            raise ValueError("Password must not contain your email address.")

    return password
