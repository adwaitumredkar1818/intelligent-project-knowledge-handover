"""Strict upload validation for PDF and DOCX evidence files."""

from __future__ import annotations

import hashlib
import io
import os
import re
import zipfile
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

import docx
import pymupdf

from app.core.exceptions import (
    BadRequestError,
    PayloadTooLargeError,
    UnprocessableEntityError,
    UnsupportedMediaTypeError,
)
from app.models.enums import EvidenceCategory

_PDF_MAGIC = b"%PDF-"
_ZIP_MAGIC = b"PK\x03\x04"

_ALLOWED_PDF_MIMES = frozenset({"application/pdf", "application/x-pdf"})
_ALLOWED_DOCX_MIMES = frozenset(
    {
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    }
)
_CONTROL_CHAR_RE = re.compile(r"[\x00-\x1f\x7f]")
_MAX_FILENAME_LEN = 255
_MAX_ZIP_ENTRIES = 5000
_MAX_ZIP_EXPANSION_RATIO = 100
_ZIP_RATIO_MIN_UNCOMPRESSED_BYTES = 10 * 1024 * 1024


@dataclass(frozen=True, slots=True)
class ValidatedUploadDocument:
    """Verified, memory-checked document payload ready for encrypted storage."""

    original_filename: str
    category: str
    mime_type: str
    file_size_bytes: int
    content_hash: str
    page_count: int | None
    source_author_identity: str | None
    source_created_at: datetime | None
    source_updated_at: datetime | None
    initial_metadata: dict[str, Any]
    raw_bytes: bytes


def sanitise_upload_filename(raw_filename: str | None) -> tuple[str, str]:
    """Validate and sanitise client-supplied filename without relying on OS paths."""
    if raw_filename is None:
        raise BadRequestError("Uploaded file must include a filename.", code="MISSING_FILENAME")

    stripped = raw_filename.replace("\\", "/").split("/")[-1].strip()
    if not stripped or stripped in {".", ".."} or "\x00" in raw_filename:
        raise BadRequestError("Uploaded filename is invalid.", code="INVALID_FILENAME")

    if _CONTROL_CHAR_RE.search(stripped):
        raise BadRequestError(
            "Uploaded filename contains forbidden control characters.",
            code="INVALID_FILENAME",
        )

    if len(stripped) > _MAX_FILENAME_LEN:
        raise BadRequestError(
            f"Uploaded filename must not exceed {_MAX_FILENAME_LEN} characters.",
            code="FILENAME_TOO_LONG",
        )

    ext = os.path.splitext(stripped)[1].lower()
    if ext not in {".pdf", ".docx"}:
        raise UnsupportedMediaTypeError(
            "Only .pdf and .docx document uploads are supported.",
            code="UNSUPPORTED_FILE_EXTENSION",
        )
    return stripped, ext


def parse_pdf_timestamp(raw_value: str | None) -> datetime | None:
    """Parse standard PDF metadata timestamp (`D:YYYYMMDDHHmmSS...`) into UTC datetime."""
    if not raw_value:
        return None
    cleaned = raw_value.strip()
    if cleaned.startswith("D:"):
        cleaned = cleaned[2:]
    digits = "".join(ch for ch in cleaned[:14] if ch.isdigit())
    if len(digits) < 8:
        return None
    try:
        year = int(digits[0:4])
        month = int(digits[4:6])
        day = int(digits[6:8])
        hour = int(digits[8:10]) if len(digits) >= 10 else 0
        minute = int(digits[10:12]) if len(digits) >= 12 else 0
        second = int(digits[12:14]) if len(digits) >= 14 else 0
        return datetime(year, month, day, hour, minute, second, tzinfo=UTC)
    except ValueError:
        return None


def _ensure_utc_datetime(dt: datetime | None) -> datetime | None:
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=UTC)
    return dt.astimezone(UTC)


def _validate_pdf_structure(
    raw_bytes: bytes,
    *,
    max_pages: int,
) -> tuple[int, str | None, datetime | None, datetime | None, dict[str, Any]]:
    if not raw_bytes[:64].lstrip().startswith(_PDF_MAGIC):
        raise UnsupportedMediaTypeError(
            "Uploaded file does not match valid PDF magic bytes.",
            code="INVALID_FILE_SIGNATURE",
        )
    try:
        doc = pymupdf.Document(stream=raw_bytes, filetype="pdf")  # type: ignore[no-untyped-call]
    except Exception as exc:
        raise UnprocessableEntityError(
            "Uploaded PDF file is malformed or unreadable.",
            code="MALFORMED_PDF",
        ) from exc

    try:
        if doc.needs_pass:
            raise UnprocessableEntityError(
                "Password-protected or encrypted PDF documents are not supported.",
                code="ENCRYPTED_DOCUMENT_UNSUPPORTED",
            )
        page_count = int(doc.page_count)
        if page_count <= 0:
            raise UnprocessableEntityError(
                "Uploaded PDF contains zero pages.",
                code="MALFORMED_PDF",
            )
        if page_count > max_pages:
            raise UnprocessableEntityError(
                f"Uploaded PDF exceeds the maximum allowed limit of {max_pages} pages.",
                code="PDF_PAGE_LIMIT_EXCEEDED",
            )
        raw_meta = doc.metadata or {}
        author = (raw_meta.get("author") or "").strip() or None
        doc_title = (raw_meta.get("title") or "").strip() or None
        creator = (raw_meta.get("creator") or "").strip() or None
        producer = (raw_meta.get("producer") or "").strip() or None
        source_created = parse_pdf_timestamp(raw_meta.get("creationDate"))
        source_updated = parse_pdf_timestamp(raw_meta.get("modDate"))
        compact_meta: dict[str, Any] = {
            "document_format": "pdf",
            "page_count": page_count,
        }
        if doc_title:
            compact_meta["embedded_title"] = doc_title[:300]
        if creator:
            compact_meta["creator"] = creator[:200]
        if producer:
            compact_meta["producer"] = producer[:200]
        return (
            page_count,
            author[:255] if author else None,
            source_created,
            source_updated,
            compact_meta,
        )
    finally:
        doc.close()  # type: ignore[no-untyped-call]


def _validate_docx_structure(
    raw_bytes: bytes,
    *,
    max_upload_size_bytes: int,
) -> tuple[str | None, datetime | None, datetime | None, dict[str, Any]]:
    if not raw_bytes.startswith(_ZIP_MAGIC):
        raise UnsupportedMediaTypeError(
            "Uploaded file does not match valid DOCX container signature.",
            code="INVALID_FILE_SIGNATURE",
        )

    try:
        with zipfile.ZipFile(io.BytesIO(raw_bytes), mode="r") as archive:
            infos = archive.infolist()
            if len(infos) == 0 or len(infos) > _MAX_ZIP_ENTRIES:
                raise UnprocessableEntityError(
                    "Uploaded DOCX archive structure exceeds safe entry bounds.",
                    code="MALFORMED_DOCX",
                )
            names = {info.filename for info in infos}
            if "[Content_Types].xml" not in names or "word/document.xml" not in names:
                raise UnsupportedMediaTypeError(
                    "Uploaded ZIP archive is not a valid DOCX document.",
                    code="INVALID_FILE_SIGNATURE",
                )
            total_uncompressed = sum(max(0, int(info.file_size)) for info in infos)
            max_expanded = max(max_upload_size_bytes * 5, 100 * 1024 * 1024)
            if total_uncompressed > max_expanded or (
                total_uncompressed > _ZIP_RATIO_MIN_UNCOMPRESSED_BYTES
                and total_uncompressed > len(raw_bytes) * _MAX_ZIP_EXPANSION_RATIO
            ):
                raise UnprocessableEntityError(
                    "Uploaded DOCX archive exceeds safe decompression limits.",
                    code="ARCHIVE_EXPANSION_LIMIT_EXCEEDED",
                )
    except (UnsupportedMediaTypeError, UnprocessableEntityError):
        raise
    except zipfile.BadZipFile as exc:
        raise UnprocessableEntityError(
            "Uploaded DOCX file is corrupt or unreadable.",
            code="MALFORMED_DOCX",
        ) from exc

    try:
        parsed = docx.Document(io.BytesIO(raw_bytes))
        props = parsed.core_properties
        author = (props.author or "").strip() or None
        doc_title = (props.title or "").strip() or None
        subject = (props.subject or "").strip() or None
        source_created = _ensure_utc_datetime(props.created)
        source_updated = _ensure_utc_datetime(props.modified)
        compact_meta: dict[str, Any] = {
            "document_format": "docx",
            "paragraph_count": len(parsed.paragraphs),
            "table_count": len(parsed.tables),
        }
        if doc_title:
            compact_meta["embedded_title"] = doc_title[:300]
        if subject:
            compact_meta["subject"] = subject[:300]
        return author[:255] if author else None, source_created, source_updated, compact_meta
    except Exception as exc:
        raise UnprocessableEntityError(
            "Uploaded DOCX document XML could not be parsed cleanly.",
            code="MALFORMED_DOCX",
        ) from exc


def validate_uploaded_document(
    *,
    filename: str | None,
    declared_mime_type: str | None,
    raw_bytes: bytes,
    max_upload_size_bytes: int,
    max_document_pages: int,
) -> ValidatedUploadDocument:
    """Validate uploaded PDF or DOCX bytes, headers, size limits, and SHA-256 checksum."""
    clean_name, ext = sanitise_upload_filename(filename)

    if len(raw_bytes) == 0:
        raise BadRequestError("Uploaded document must not be empty.", code="EMPTY_FILE")

    if len(raw_bytes) > max_upload_size_bytes:
        raise PayloadTooLargeError(
            "Uploaded document exceeds the configured maximum upload size.",
            code="FILE_TOO_LARGE",
        )

    normalized_mime = (declared_mime_type or "").split(";")[0].strip().lower()
    content_hash = hashlib.sha256(raw_bytes).hexdigest()

    if ext == ".pdf":
        if normalized_mime not in _ALLOWED_PDF_MIMES:
            raise UnsupportedMediaTypeError(
                "Invalid Content-Type header for a PDF upload.",
                code="UNSUPPORTED_MEDIA_TYPE",
            )
        page_count, author, src_created, src_updated, compact_meta = _validate_pdf_structure(
            raw_bytes,
            max_pages=max_document_pages,
        )
        return ValidatedUploadDocument(
            original_filename=clean_name,
            category=EvidenceCategory.PDF_DOCUMENT.value,
            mime_type="application/pdf",
            file_size_bytes=len(raw_bytes),
            content_hash=content_hash,
            page_count=page_count,
            source_author_identity=author,
            source_created_at=src_created,
            source_updated_at=src_updated,
            initial_metadata=compact_meta,
            raw_bytes=raw_bytes,
        )

    if normalized_mime not in _ALLOWED_DOCX_MIMES:
        raise UnsupportedMediaTypeError(
            "Invalid Content-Type header for a DOCX upload.",
            code="UNSUPPORTED_MEDIA_TYPE",
        )
    author, src_created, src_updated, compact_meta = _validate_docx_structure(
        raw_bytes,
        max_upload_size_bytes=max_upload_size_bytes,
    )
    return ValidatedUploadDocument(
        original_filename=clean_name,
        category=EvidenceCategory.DOCX_DOCUMENT.value,
        mime_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        file_size_bytes=len(raw_bytes),
        content_hash=content_hash,
        page_count=None,
        source_author_identity=author,
        source_created_at=src_created,
        source_updated_at=src_updated,
        initial_metadata=compact_meta,
        raw_bytes=raw_bytes,
    )
