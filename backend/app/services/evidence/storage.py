"""Secure file storage service enforcing opaque filenames, hashing, and encryption at rest."""

from __future__ import annotations

import hashlib
import mimetypes
import os
import uuid
from pathlib import Path

from app.core.config import Settings
from app.core.crypto import decrypt_bytes, encrypt_bytes
from app.core.exceptions import BadRequestError, NotFoundError

# Allowed MIME types and corresponding extensions
ALLOWED_EXTENSIONS: set[str] = {".pdf", ".docx"}
MAX_FILE_SIZE_BYTES: int = 50 * 1024 * 1024  # 50 MB


class SecureStorageService:
    """Manages encrypted-at-rest document file storage with integrity validation."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._storage_dir: Path = settings.security.upload_storage_path
        self._file_key = settings.security.file_encryption_key
        # Ensure base upload storage directory exists
        self._storage_dir.mkdir(parents=True, exist_ok=True)

    def validate_file(self, filename: str, content: bytes) -> tuple[str, str]:
        """Validate filename extension, file size, and magic byte headers."""
        if len(content) == 0:
            raise BadRequestError("Uploaded file cannot be empty.", code="EMPTY_FILE")

        if len(content) > MAX_FILE_SIZE_BYTES:
            max_mb = MAX_FILE_SIZE_BYTES // (1024 * 1024)
            raise BadRequestError(
                f"File size exceeds maximum allowed threshold of {max_mb} MB.",
                code="FILE_TOO_LARGE",
            )

        ext = Path(filename).suffix.lower()
        if ext not in ALLOWED_EXTENSIONS:
            allowed = ", ".join(sorted(ALLOWED_EXTENSIONS))
            raise BadRequestError(
                f"Unsupported file format '{ext}'. Allowed formats: {allowed}.",
                code="UNSUPPORTED_FILE_TYPE",
            )

        # Magic byte verification
        if ext == ".pdf":
            if not content.startswith(b"%PDF"):
                raise BadRequestError(
                    "Invalid PDF header signature.",
                    code="INVALID_FILE_SIGNATURE",
                )
            mime_type = "application/pdf"
        elif ext == ".docx":
            if not content.startswith(b"PK\x03\x04"):
                raise BadRequestError(
                    "Invalid DOCX archive header signature.", code="INVALID_FILE_SIGNATURE"
                )
            mime_type = (
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
            )
        else:
            mime_type = mimetypes.guess_type(filename)[0] or "application/octet-stream"

        return ext, mime_type

    def save_file(
        self,
        *,
        filename: str,
        content: bytes,
    ) -> tuple[str, str, int, str]:
        """Encrypt and persist file content to an opaque disk path.

        Returns: (relative_storage_path, sha256_hash, byte_size, mime_type)
        """
        ext, mime_type = self.validate_file(filename, content)
        sha256_hash = hashlib.sha256(content).hexdigest()
        byte_size = len(content)

        # Generate an opaque unguessable server filename
        opaque_name = f"{uuid.uuid4().hex}{ext}.enc"
        target_path = self._storage_dir / opaque_name

        # Encrypt at rest
        encrypted_data = encrypt_bytes(content, self._file_key)
        target_path.write_bytes(encrypted_data)

        # Return storage path relative to project root or storage directory
        return str(target_path.resolve()), sha256_hash, byte_size, mime_type

    def read_file(self, storage_path: str) -> bytes:
        """Read and decrypt stored file content from disk."""
        path = Path(storage_path)
        if not path.is_file():
            raise NotFoundError(
                "Stored document file could not be found on disk.",
                code="FILE_NOT_FOUND",
            )

        encrypted_data = path.read_bytes()
        return decrypt_bytes(encrypted_data, self._file_key)

    def delete_file(self, storage_path: str) -> bool:
        """Safely remove a stored document file from disk."""
        path = Path(storage_path)
        if path.is_file():
            try:
                os.remove(path)
                return True
            except OSError:
                return False
        return False
