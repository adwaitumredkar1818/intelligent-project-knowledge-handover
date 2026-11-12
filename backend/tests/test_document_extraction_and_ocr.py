"""Unit tests for PDF/DOCX extraction, scanned-page triage, and Ollama GLM OCR checks."""

from __future__ import annotations

import io
import json

import docx
import httpx
import pymupdf
import pytest

from app.core.config import IngestionSettings
from app.models.enums import (
    DocumentExtractionMethod,
    EvidenceCategory,
    EvidenceProcessingStatus,
    PageExtractionOutcome,
)
from app.services.document_extraction import DocumentExtractionService
from app.services.ocr import (
    OCRExecutionError,
    OCRPageRequest,
    OCRPageResult,
    OllamaGLMOCRService,
)


class _StubOCRService:
    def __init__(
        self,
        *,
        text_by_page: dict[int, str],
        truncated_pages: set[int] | None = None,
    ) -> None:
        self.model_name = "stub-glm-ocr"
        self.calls: list[OCRPageRequest] = []
        self._text_by_page = text_by_page
        self._truncated_pages = truncated_pages or set()

    def extract_page_text(self, request: OCRPageRequest) -> OCRPageResult:
        self.calls.append(request)
        truncated = request.page_number in self._truncated_pages
        return OCRPageResult(
            page_number=request.page_number,
            text=self._text_by_page.get(request.page_number, ""),
            model_name=self.model_name,
            truncated=truncated,
            done_reason="length" if truncated else "stop",
            prompt_eval_count=600,
            eval_count=4096 if truncated else 120,
            duration_ms=42,
            warnings=("ocr_output_truncated",) if truncated else (),
        )


def _render_text_as_png_bytes(lines: list[str]) -> bytes:
    """Render synthetic lines into a clean PNG raster image in memory."""
    temp_doc = pymupdf.Document()  # type: ignore[no-untyped-call]
    try:
        temp_page = temp_doc.new_page(width=595, height=400)
        y = 72
        for line in lines:
            temp_page.insert_text((48, y), line, fontsize=16)
            y += 28
        matrix = pymupdf.Matrix(2.0, 2.0)  # type: ignore[no-untyped-call]
        pix = temp_page.get_pixmap(matrix=matrix, alpha=False)
        return bytes(pix.tobytes("png"))  # type: ignore[no-untyped-call]
    finally:
        temp_doc.close()  # type: ignore[no-untyped-call]


def _make_mixed_pdf(
    digital_text: str,
    scanned_lines: list[str],
    extra_scanned_pages: int = 0,
) -> bytes:
    doc = pymupdf.Document()  # type: ignore[no-untyped-call]
    try:
        doc.set_metadata(
            {
                "title": "Handover Spec",
                "author": "Alice Architect",
                "creationDate": "D:20261110123000Z",
            }
        )
        p1 = doc.new_page()
        p1.insert_text(
            (72, 72),
            digital_text,
        )

        img_bytes = _render_text_as_png_bytes(scanned_lines)
        for _ in range(1 + extra_scanned_pages):
            p_scan = doc.new_page()
            p_scan.insert_image(p_scan.rect, stream=img_bytes)  # type: ignore[no-untyped-call]
        return bytes(doc.tobytes())  # type: ignore[no-untyped-call]
    finally:
        doc.close()  # type: ignore[no-untyped-call]


def test_pdf_extraction_uses_pymupdf_for_digital_pages_and_ocr_only_for_scanned() -> None:
    pdf_bytes = _make_mixed_pdf(
        digital_text=(
            "Decision ADR-104: PostgreSQL remains canonical store for project handovers "
            "and ChromaDB holds rebuildable semantic embeddings only."
        ),
        scanned_lines=["Scanned Runbook Step 1: Rotate keys safely."],
    )
    stub_ocr = _StubOCRService(text_by_page={2: "Scanned Runbook Step 1: Rotate keys safely."})
    service = DocumentExtractionService(
        ocr_service=stub_ocr,
        ingestion_settings=IngestionSettings(ocr_min_text_chars_per_page=40),
    )

    result = service.extract_document(
        category=EvidenceCategory.PDF_DOCUMENT.value,
        raw_bytes=pdf_bytes,
        document_title="handover.pdf",
    )

    assert result.processing_status == EvidenceProcessingStatus.EXTRACTED.value
    assert result.extraction_method == DocumentExtractionMethod.PYMUPDF_AND_OCR.value
    assert result.page_count == 2
    assert result.ocr_pages_count == 1
    assert result.truncated_pages_count == 0
    assert result.source_author_identity == "Alice Architect"
    assert result.source_created_at is not None
    assert len(stub_ocr.calls) == 1
    assert stub_ocr.calls[0].page_number == 2
    assert result.pages[0].extraction_outcome == PageExtractionOutcome.DIGITAL_TEXT.value
    assert result.pages[1].extraction_outcome == PageExtractionOutcome.OCR_SUCCEEDED.value
    assert "ADR-104" in result.extracted_text
    assert "Rotate keys safely" in result.extracted_text


def test_truncated_ocr_marks_document_partially_extracted_and_respects_page_cap() -> None:
    pdf_bytes = _make_mixed_pdf(
        digital_text="Overview section with sufficient digital text content to skip OCR pass.",
        scanned_lines=["Scanned appendix table row 1."],
        extra_scanned_pages=1,
    )
    stub_ocr = _StubOCRService(
        text_by_page={2: "Partial truncated output..."},
        truncated_pages={2},
    )
    service = DocumentExtractionService(
        ocr_service=stub_ocr,
        ingestion_settings=IngestionSettings(
            ocr_min_text_chars_per_page=40,
            ocr_max_pages_per_document=1,
        ),
    )

    result = service.extract_document(
        category=EvidenceCategory.PDF_DOCUMENT.value,
        raw_bytes=pdf_bytes,
    )

    assert result.processing_status == EvidenceProcessingStatus.PARTIALLY_EXTRACTED.value
    assert result.truncated_pages_count == 1
    assert result.pages[1].extraction_outcome == PageExtractionOutcome.OCR_TRUNCATED.value
    assert result.pages[1].ocr_truncated is True
    assert result.pages[2].extraction_outcome == PageExtractionOutcome.SKIPPED_LIMIT.value
    assert any("ocr_truncated" in w for w in result.warnings)
    assert any("skipped_limit" in w for w in result.warnings)


def test_docx_extraction_preserves_headings_paragraphs_and_tables_in_order() -> None:
    document = docx.Document()
    document.core_properties.author = "Bob Maintainer"
    document.core_properties.title = "Incident Response Guide"
    document.add_heading("1. Incident Triage", level=1)
    document.add_paragraph("Always inspect PostgreSQL worker job status before restarting.")
    table = document.add_table(rows=2, cols=2)
    table.cell(0, 0).text = "Service"
    table.cell(0, 1).text = "Owner"
    table.cell(1, 0).text = "Ingestion Worker"
    table.cell(1, 1).text = "Platform Team"
    document.add_heading("2. Escalation Path", level=2)
    document.add_paragraph("Contact reviewer before approving handover.")

    buf = io.BytesIO()
    document.save(buf)

    service = DocumentExtractionService(
        ocr_service=_StubOCRService(text_by_page={}),
        ingestion_settings=IngestionSettings(),
    )
    result = service.extract_document(
        category=EvidenceCategory.DOCX_DOCUMENT.value,
        raw_bytes=buf.getvalue(),
    )

    assert result.processing_status == EvidenceProcessingStatus.EXTRACTED.value
    assert result.extraction_method == DocumentExtractionMethod.PYTHON_DOCX.value
    assert result.source_author_identity == "Bob Maintainer"
    assert result.metadata_json["table_count"] == 1
    assert result.metadata_json["heading_count"] == 2
    idx_h1 = result.extracted_text.index("# 1. Incident Triage")
    idx_tbl = result.extracted_text.index("| Ingestion Worker | Platform Team |")
    idx_h2 = result.extracted_text.index("## 2. Escalation Path")
    assert idx_h1 < idx_tbl < idx_h2


def test_ollama_glm_ocr_adapter_sends_explicit_num_ctx_and_detects_truncation() -> None:
    captured_requests: list[dict[str, object]] = []

    def _handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content.decode("utf-8"))
        captured_requests.append(body)
        if len(captured_requests) == 1:
            return httpx.Response(
                200,
                json={
                    "response": "Truncated transcription stopping mid sentence",
                    "done": True,
                    "done_reason": "length",
                    "prompt_eval_count": 1100,
                    "eval_count": 4096,
                },
            )
        return httpx.Response(503, json={"error": "model overloaded"})

    client = httpx.Client(transport=httpx.MockTransport(_handler))
    ocr = OllamaGLMOCRService(
        base_url="http://127.0.0.1:11434",
        model="glm-ocr:latest",
        num_ctx=8192,
        num_predict=4096,
        http_client=client,
    )

    first = ocr.extract_page_text(
        OCRPageRequest(
            page_number=1,
            image_bytes=b"fake-png-bytes",
            image_width=800,
            image_height=1000,
        )
    )
    assert captured_requests[0]["model"] == "glm-ocr:latest"
    options = captured_requests[0]["options"]
    assert isinstance(options, dict)
    assert options["num_ctx"] == 8192
    assert first.truncated is True
    assert first.done_reason == "length"
    assert "ocr_output_truncated" in first.warnings

    with pytest.raises(OCRExecutionError) as exc_info:
        ocr.extract_page_text(
            OCRPageRequest(
                page_number=2,
                image_bytes=b"fake-png-bytes",
                image_width=800,
                image_height=1000,
            )
        )
    assert exc_info.value.retryable is True
    assert exc_info.value.code == "OCR_UPSTREAM_ERROR"
