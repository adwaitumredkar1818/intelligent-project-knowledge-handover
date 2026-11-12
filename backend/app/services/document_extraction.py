"""Document content extraction pipeline for PDF (PyMuPDF + OCR) and DOCX files."""

from __future__ import annotations

import io
import logging
import re
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

import docx
import pymupdf
from docx.oxml.table import CT_Tbl
from docx.oxml.text.paragraph import CT_P
from docx.table import Table
from docx.text.paragraph import Paragraph

from app.core.config import IngestionSettings
from app.models.enums import (
    DocumentExtractionMethod,
    EvidenceCategory,
    EvidenceProcessingStatus,
    PageExtractionOutcome,
)
from app.services.document_validation import parse_pdf_timestamp
from app.services.ocr import OCRExecutionError, OCRPageRequest, OCRService

logger = logging.getLogger("app.services.document_extraction")

_DOCX_HEADING_STYLE_RE = re.compile(r"^Heading\s+(\d+)$", re.IGNORECASE)
_DOCX_SECTION_TARGET_CHARS = 4000


class DocumentExtractionError(RuntimeError):
    """Sanitised domain failure surfaced to worker retry / status tracking."""

    def __init__(self, *, code: str, message: str, retryable: bool = False) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.retryable = retryable


@dataclass(frozen=True, slots=True)
class ExtractedPageData:
    """Extracted text and provenance/telemetry for one page or logical section."""

    page_number: int
    extraction_outcome: str
    ocr_applied: bool
    ocr_truncated: bool
    text_content: str
    structured_metadata: dict[str, Any]


@dataclass(frozen=True, slots=True)
class ExtractedDocumentResult:
    """Complete extraction result kept separate from raw metadata JSON."""

    processing_status: str
    extraction_method: str
    page_count: int
    ocr_pages_count: int
    truncated_pages_count: int
    extracted_text: str
    source_created_at: datetime | None
    source_updated_at: datetime | None
    source_author_identity: str | None
    metadata_json: dict[str, Any]
    warnings: tuple[str, ...]
    pages: tuple[ExtractedPageData, ...]


def _ensure_utc(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def _count_words(text: str) -> int:
    return len(text.split()) if text.strip() else 0


class DocumentExtractionService:
    """Extracts text and structure from PDF and DOCX bytes with replaceable OCR."""

    def __init__(
        self,
        *,
        ocr_service: OCRService,
        ingestion_settings: IngestionSettings,
    ) -> None:
        self._ocr_service = ocr_service
        self._settings = ingestion_settings

    def extract_document(
        self,
        *,
        category: str,
        raw_bytes: bytes,
        document_title: str | None = None,
    ) -> ExtractedDocumentResult:
        """Dispatch validated bytes to PDF or DOCX extractor cleanly."""
        if category == EvidenceCategory.PDF_DOCUMENT.value:
            return self._extract_pdf(raw_bytes=raw_bytes, document_title=document_title)
        if category == EvidenceCategory.DOCX_DOCUMENT.value:
            return self._extract_docx(raw_bytes=raw_bytes)
        raise DocumentExtractionError(
            code="UNSUPPORTED_EXTRACTION_CATEGORY",
            message="Evidence category is not supported by document extractors.",
            retryable=False,
        )

    def _render_bounded_page_png(self, page: pymupdf.Page) -> tuple[bytes, int, int]:
        rect = page.rect
        requested_scale = self._settings.ocr_render_dpi / 72.0
        longest_pt = max(float(rect.width), float(rect.height), 1.0)
        max_scale = float(self._settings.ocr_max_image_dimension) / longest_pt
        scale = max(0.25, min(requested_scale, max_scale))
        matrix = pymupdf.Matrix(scale, scale)  # type: ignore[no-untyped-call]
        pixmap = page.get_pixmap(matrix=matrix, alpha=False)
        png_bytes = pixmap.tobytes("png")  # type: ignore[no-untyped-call]
        return png_bytes, int(pixmap.width), int(pixmap.height)

    def _extract_pdf(
        self,
        *,
        raw_bytes: bytes,
        document_title: str | None,
    ) -> ExtractedDocumentResult:
        try:
            doc = pymupdf.Document(stream=raw_bytes, filetype="pdf")  # type: ignore[no-untyped-call]
        except Exception as exc:
            raise DocumentExtractionError(
                code="PDF_OPEN_FAILED",
                message="PDF document could not be opened during extraction.",
                retryable=False,
            ) from exc

        try:
            if doc.needs_pass:
                raise DocumentExtractionError(
                    code="ENCRYPTED_DOCUMENT_UNSUPPORTED",
                    message="Password-protected PDF documents cannot be extracted.",
                    retryable=False,
                )
            total_pages = int(doc.page_count)
            if total_pages <= 0 or total_pages > self._settings.max_document_pages:
                raise DocumentExtractionError(
                    code="PDF_PAGE_LIMIT_EXCEEDED",
                    message=(
                        f"PDF page count ({total_pages}) falls outside allowed limits "
                        f"(1..{self._settings.max_document_pages})."
                    ),
                    retryable=False,
                )

            raw_meta = doc.metadata or {}
            author = (raw_meta.get("author") or "").strip()[:255] or None
            embedded_title = (raw_meta.get("title") or "").strip()[:300] or None
            subject = (raw_meta.get("subject") or "").strip()[:300] or None
            creator = (raw_meta.get("creator") or "").strip()[:200] or None
            producer = (raw_meta.get("producer") or "").strip()[:200] or None
            source_created = parse_pdf_timestamp(raw_meta.get("creationDate"))
            source_updated = parse_pdf_timestamp(raw_meta.get("modDate"))

            pages_out: list[ExtractedPageData] = []
            warnings: list[str] = []
            digital_pages_used = 0
            ocr_pages_used = 0
            truncated_pages_count = 0
            partial_failure = False

            for zero_idx in range(total_pages):
                page_number = zero_idx + 1
                page = doc.load_page(zero_idx)  # type: ignore[no-untyped-call]
                digital_text = (page.get_text("text", sort=True) or "").strip()
                images_count = len(page.get_images(full=False))
                drawings_count = len(page.get_drawings())

                min_chars = self._settings.ocr_min_text_chars_per_page
                needs_ocr = (
                    images_count > 0 and len(digital_text) < min_chars
                ) or (len(digital_text) == 0 and drawings_count > 0)

                if not needs_ocr:
                    if digital_text:
                        digital_pages_used += 1
                        outcome = PageExtractionOutcome.DIGITAL_TEXT.value
                    else:
                        outcome = PageExtractionOutcome.EMPTY.value
                    pages_out.append(
                        ExtractedPageData(
                            page_number=page_number,
                            extraction_outcome=outcome,
                            ocr_applied=False,
                            ocr_truncated=False,
                            text_content=digital_text,
                            structured_metadata={
                                "image_count": images_count,
                                "drawing_count": drawings_count,
                                "digital_char_count": len(digital_text),
                            },
                        )
                    )
                    continue

                if ocr_pages_used >= self._settings.ocr_max_pages_per_document:
                    partial_failure = True
                    warnings.append(f"page_{page_number}_ocr_skipped_limit")
                    pages_out.append(
                        ExtractedPageData(
                            page_number=page_number,
                            extraction_outcome=PageExtractionOutcome.SKIPPED_LIMIT.value,
                            ocr_applied=False,
                            ocr_truncated=False,
                            text_content=digital_text,
                            structured_metadata={
                                "image_count": images_count,
                                "drawing_count": drawings_count,
                                "skipped_reason": "ocr_max_pages_per_document",
                            },
                        )
                    )
                    continue

                png_bytes, img_w, img_h = self._render_bounded_page_png(page)
                try:
                    ocr_res = self._ocr_service.extract_page_text(
                        OCRPageRequest(
                            page_number=page_number,
                            image_bytes=png_bytes,
                            image_width=img_w,
                            image_height=img_h,
                            document_title=document_title,
                        )
                    )
                except OCRExecutionError as exc:
                    raise DocumentExtractionError(
                        code=exc.code,
                        message=exc.message,
                        retryable=exc.retryable,
                    ) from exc

                ocr_pages_used += 1
                if digital_text and ocr_res.text and digital_text != ocr_res.text:
                    combined_text = f"{digital_text}\n{ocr_res.text}".strip()
                    digital_pages_used += 1
                elif ocr_res.text:
                    combined_text = ocr_res.text
                else:
                    combined_text = digital_text

                page_meta: dict[str, Any] = {
                    "ocr_model": ocr_res.model_name,
                    "ocr_duration_ms": ocr_res.duration_ms,
                    "done_reason": ocr_res.done_reason,
                    "prompt_eval_count": ocr_res.prompt_eval_count,
                    "eval_count": ocr_res.eval_count,
                    "image_width": img_w,
                    "image_height": img_h,
                    "image_count": images_count,
                }
                for warn in ocr_res.warnings:
                    warnings.append(f"page_{page_number}_{warn}")

                if ocr_res.truncated:
                    truncated_pages_count += 1
                    partial_failure = True
                    outcome = PageExtractionOutcome.OCR_TRUNCATED.value
                    trunc_warn = f"page_{page_number}_ocr_truncated"
                    if trunc_warn not in warnings:
                        warnings.append(trunc_warn)
                elif combined_text:
                    outcome = PageExtractionOutcome.OCR_SUCCEEDED.value
                else:
                    outcome = PageExtractionOutcome.EMPTY.value

                pages_out.append(
                    ExtractedPageData(
                        page_number=page_number,
                        extraction_outcome=outcome,
                        ocr_applied=True,
                        ocr_truncated=ocr_res.truncated,
                        text_content=combined_text,
                        structured_metadata=page_meta,
                    )
                )

            full_text = "\n\n".join(p.text_content for p in pages_out if p.text_content.strip())
            if not full_text.strip():
                warnings.append("document_contained_no_extractable_text")

            if ocr_pages_used > 0 and digital_pages_used > 0:
                method = DocumentExtractionMethod.PYMUPDF_AND_OCR.value
            elif ocr_pages_used > 0:
                method = DocumentExtractionMethod.GLM_OCR.value
            else:
                method = DocumentExtractionMethod.PYMUPDF_TEXT.value

            status = (
                EvidenceProcessingStatus.PARTIALLY_EXTRACTED.value
                if (partial_failure or truncated_pages_count > 0)
                else EvidenceProcessingStatus.EXTRACTED.value
            )

            compact_meta: dict[str, Any] = {
                "document_format": "pdf",
                "page_count": total_pages,
                "digital_pages_count": digital_pages_used,
                "ocr_pages_count": ocr_pages_used,
                "truncated_pages_count": truncated_pages_count,
                "word_count": _count_words(full_text),
            }
            if embedded_title:
                compact_meta["embedded_title"] = embedded_title
            if subject:
                compact_meta["subject"] = subject
            if creator:
                compact_meta["creator"] = creator
            if producer:
                compact_meta["producer"] = producer

            return ExtractedDocumentResult(
                processing_status=status,
                extraction_method=method,
                page_count=total_pages,
                ocr_pages_count=ocr_pages_used,
                truncated_pages_count=truncated_pages_count,
                extracted_text=full_text,
                source_created_at=source_created,
                source_updated_at=source_updated,
                source_author_identity=author,
                metadata_json=compact_meta,
                warnings=tuple(warnings),
                pages=tuple(pages_out),
            )
        finally:
            doc.close()  # type: ignore[no-untyped-call]

    def _extract_docx(self, *, raw_bytes: bytes) -> ExtractedDocumentResult:
        try:
            document = docx.Document(io.BytesIO(raw_bytes))
        except Exception as exc:
            raise DocumentExtractionError(
                code="DOCX_OPEN_FAILED",
                message="DOCX document could not be parsed during extraction.",
                retryable=False,
            ) from exc

        props = document.core_properties
        author = (props.author or "").strip()[:255] or None
        embedded_title = (props.title or "").strip()[:300] or None
        subject = (props.subject or "").strip()[:300] or None
        source_created = _ensure_utc(props.created)
        source_updated = _ensure_utc(props.modified)

        blocks: list[tuple[bool, str]] = []
        heading_count = 0
        paragraph_count = 0
        table_count = 0

        for child in document.element.body.iterchildren():
            if isinstance(child, CT_P):
                para = Paragraph(child, document)
                raw_text = para.text.strip()
                if not raw_text:
                    continue
                style_name = (para.style.name or "").strip() if para.style else ""
                heading_match = _DOCX_HEADING_STYLE_RE.match(style_name)
                if heading_match:
                    level = min(max(int(heading_match.group(1)), 1), 6)
                    blocks.append((True, f"{'#' * level} {raw_text}"))
                    heading_count += 1
                elif style_name.lower() == "title":
                    blocks.append((True, f"# {raw_text}"))
                    heading_count += 1
                else:
                    blocks.append((False, raw_text))
                    paragraph_count += 1
            elif isinstance(child, CT_Tbl):
                table = Table(child, document)
                table_lines: list[str] = []
                for row in table.rows:
                    cells = [" ".join(cell.text.split()) for cell in row.cells]
                    if any(cells):
                        table_lines.append("| " + " | ".join(cells) + " |")
                if table_lines:
                    blocks.append((False, "\n".join(table_lines)))
                    table_count += 1

        # Group ordered blocks into bounded logical sections while preserving sequence.
        sections: list[str] = []
        current_parts: list[str] = []
        current_chars = 0
        for is_heading, block_text in blocks:
            would_exceed = current_chars > 0 and (
                current_chars + len(block_text) > _DOCX_SECTION_TARGET_CHARS
                or (is_heading and current_chars >= 1200)
            )
            if would_exceed:
                sections.append("\n\n".join(current_parts))
                current_parts = []
                current_chars = 0
            current_parts.append(block_text)
            current_chars += len(block_text)

        if current_parts:
            sections.append("\n\n".join(current_parts))
        if not sections:
            sections = [""]

        pages_out = [
            ExtractedPageData(
                page_number=idx,
                extraction_outcome=(
                    PageExtractionOutcome.DIGITAL_TEXT.value
                    if sec.strip()
                    else PageExtractionOutcome.EMPTY.value
                ),
                ocr_applied=False,
                ocr_truncated=False,
                text_content=sec,
                structured_metadata={
                    "section_index": idx,
                    "section_format": "docx_flow",
                },
            )
            for idx, sec in enumerate(sections, start=1)
        ]

        full_text = "\n\n".join(sec for sec in sections if sec.strip())
        warnings: list[str] = []
        if not full_text.strip():
            warnings.append("document_contained_no_extractable_text")

        compact_meta: dict[str, Any] = {
            "document_format": "docx",
            "section_count": len(pages_out),
            "heading_count": heading_count,
            "paragraph_count": paragraph_count,
            "table_count": table_count,
            "word_count": _count_words(full_text),
        }
        if embedded_title:
            compact_meta["embedded_title"] = embedded_title
        if subject:
            compact_meta["subject"] = subject

        return ExtractedDocumentResult(
            processing_status=EvidenceProcessingStatus.EXTRACTED.value,
            extraction_method=DocumentExtractionMethod.PYTHON_DOCX.value,
            page_count=len(pages_out),
            ocr_pages_count=0,
            truncated_pages_count=0,
            extracted_text=full_text,
            source_created_at=source_created,
            source_updated_at=source_updated,
            source_author_identity=author,
            metadata_json=compact_meta,
            warnings=tuple(warnings),
            pages=tuple(pages_out),
        )
