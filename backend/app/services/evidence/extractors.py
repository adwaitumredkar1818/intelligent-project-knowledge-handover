"""Document extraction services for PDF (PyMuPDF + GLM OCR) and DOCX (python-docx)."""

from __future__ import annotations

import io
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

import docx
import httpx
import pymupdf  # PyMuPDF

logger = logging.getLogger("app.evidence.extraction")


@dataclass
class ExtractedChunk:
    """A semantic or size-bounded chunk with provenance metadata."""

    content: str
    chunk_index: int
    page_number: int | None = None
    heading_path: str | None = None
    word_count: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class ExtractionResult:
    """Complete document extraction result."""

    full_text: str
    markdown_content: str
    page_count: int
    chunks: list[ExtractedChunk]
    detected_metadata: dict[str, Any]
    ocr_applied: bool = False
    notes: list[str] = field(default_factory=list)


class BaseOcrClient(ABC):
    """Abstract interface for optical character recognition of scanned document pages."""

    @abstractmethod
    def run_ocr_on_image(self, image_bytes: bytes) -> str:
        """Process image bytes and return recognized text."""
        ...


class OllamaGlmOcrClient(BaseOcrClient):
    """Local Ollama OCR client utilizing `glm-ocr:latest` behind a replaceable abstraction."""

    def __init__(
        self,
        base_url: str = "http://localhost:11434",
        model: str = "glm-ocr:latest",
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._model = model

    def run_ocr_on_image(self, image_bytes: bytes) -> str:
        """Send page image bytes to Ollama OCR model via HTTP."""
        import base64

        try:
            b64_image = base64.b64encode(image_bytes).decode("utf-8")
            with httpx.Client(timeout=10.0) as client:
                prompt_text = (
                    "Extract all readable text, titles, and table contents from this document page."
                )
                resp = client.post(
                    f"{self._base_url}/api/generate",
                    json={
                        "model": self._model,
                        "prompt": prompt_text,
                        "images": [b64_image],
                        "stream": False,
                    },
                )
                if resp.status_code == 200:
                    data = resp.json()
                    return str(data.get("response", "")).strip()
                logger.warning(
                    "Ollama OCR endpoint returned non-200 status %d: %s",
                    resp.status_code,
                    resp.text[:200],
                )
                return ""
        except Exception as exc:
            logger.info("Ollama OCR client unreachable (%s); falling back cleanly", exc)
            return ""


class TextChunker:
    """Splits structured text into bounded chunks with overlap and boundary preservation."""

    def __init__(self, target_chars: int = 800, overlap_chars: int = 100) -> None:
        self.target_chars = target_chars
        self.overlap_chars = overlap_chars

    def chunk_document_pages(
        self,
        pages: list[tuple[int, str, str | None]],
    ) -> list[ExtractedChunk]:
        """Chunk a list of (page_number, text, heading) preserving page boundaries."""
        chunks: list[ExtractedChunk] = []
        chunk_idx = 0

        for page_num, page_text, heading in pages:
            clean_text = page_text.strip()
            if not clean_text:
                continue

            if len(clean_text) <= self.target_chars:
                words = len(clean_text.split())
                chunks.append(
                    ExtractedChunk(
                        content=clean_text,
                        chunk_index=chunk_idx,
                        page_number=page_num,
                        heading_path=heading,
                        word_count=words,
                    )
                )
                chunk_idx += 1
            else:
                # Split large page text into overlapping windows
                start = 0
                while start < len(clean_text):
                    end = start + self.target_chars
                    if end < len(clean_text):
                        # Try to find a paragraph or sentence break
                        break_pos = clean_text.rfind("\n", start + self.target_chars // 2, end)
                        if break_pos == -1:
                            break_pos = clean_text.rfind(". ", start + self.target_chars // 2, end)
                        if break_pos != -1:
                            end = break_pos + 1
                    slice_text = clean_text[start:end].strip()
                    if slice_text:
                        chunks.append(
                            ExtractedChunk(
                                content=slice_text,
                                chunk_index=chunk_idx,
                                page_number=page_num,
                                heading_path=heading,
                                word_count=len(slice_text.split()),
                            )
                        )
                        chunk_idx += 1
                    start = max(start + 1, end - self.overlap_chars)

        return chunks


class PdfExtractor:
    """Extracts text, structural headings, tables, and scanned pages from PDF documents."""

    def __init__(self, ocr_client: BaseOcrClient | None = None) -> None:
        self._ocr_client = ocr_client or OllamaGlmOcrClient()
        self._chunker = TextChunker()

    def extract(self, pdf_bytes: bytes, filename: str = "document.pdf") -> ExtractionResult:
        """Extract text and metadata from PDF bytes."""
        doc = pymupdf.open(stream=pdf_bytes, filetype="pdf")  # type: ignore[no-untyped-call]
        page_count = len(doc)
        full_text_parts: list[str] = []
        page_records: list[tuple[int, str, str | None]] = []
        ocr_applied = False
        notes: list[str] = []

        doc_meta = doc.metadata or {}
        extracted_meta: dict[str, Any] = {
            "title": doc_meta.get("title") or filename,
            "author": doc_meta.get("author") or "Unknown",
            "subject": doc_meta.get("subject") or "",
            "keywords": doc_meta.get("keywords") or "",
            "format": "pdf",
            "page_count": page_count,
        }

        for page_idx in range(page_count):
            page_num = page_idx + 1
            page = doc.load_page(page_idx)  # type: ignore[no-untyped-call]
            text = page.get_text("text").strip()

            # If page text is very sparse (< 20 characters), check if it's a scanned page
            if len(text) < 20 and self._ocr_client is not None:
                try:
                    pix = page.get_pixmap(dpi=150)
                    img_bytes = pix.tobytes("png")
                    ocr_text = self._ocr_client.run_ocr_on_image(img_bytes)
                    if ocr_text:
                        text = f"[OCR Extracted Page {page_num}]\n{ocr_text}"
                        ocr_applied = True
                        notes.append(f"Applied OCR to scanned page {page_num}")
                except Exception as exc:
                    logger.debug("Failed OCR processing on page %d: %s", page_num, exc)

            if not text:
                text = f"[Page {page_num}: No readable text or images found]"

            full_text_parts.append(f"--- Page {page_num} ---\n{text}")
            page_records.append((page_num, text, f"Page {page_num}"))

        combined_full_text = "\n\n".join(full_text_parts)
        chunks = self._chunker.chunk_document_pages(page_records)

        return ExtractionResult(
            full_text=combined_full_text,
            markdown_content=combined_full_text,
            page_count=page_count,
            chunks=chunks,
            detected_metadata=extracted_meta,
            ocr_applied=ocr_applied,
            notes=notes,
        )


class DocxExtractor:
    """Extracts structured text, headings, and tables from Word (.docx) files."""

    def __init__(self) -> None:
        self._chunker = TextChunker()

    def extract(self, docx_bytes: bytes, filename: str = "document.docx") -> ExtractionResult:
        """Extract text and metadata from DOCX bytes."""
        stream = io.BytesIO(docx_bytes)
        doc = docx.Document(stream)

        text_parts: list[str] = []
        page_records: list[tuple[int, str, str | None]] = []
        current_heading: str | None = None
        current_section_texts: list[str] = []
        section_idx = 1

        for para in doc.paragraphs:
            text = para.text.strip()
            if not text:
                continue

            # Detect headings by style
            style_name = para.style.name.lower() if para.style else ""
            if "heading" in style_name or style_name.startswith("title"):
                if current_section_texts:
                    sec_text = "\n\n".join(current_section_texts)
                    page_records.append((section_idx, sec_text, current_heading))
                    section_idx += 1
                    current_section_texts = []
                current_heading = text
                text_parts.append(f"\n### {text}\n")
            else:
                current_section_texts.append(text)
                text_parts.append(text)

        # Process tables
        for table_idx, table in enumerate(doc.tables, start=1):
            table_rows: list[str] = []
            for row in table.rows:
                cells = [cell.text.strip().replace("\n", " ") for cell in row.cells]
                table_rows.append(" | ".join(cells))
            if table_rows:
                table_str = f"\n[Table {table_idx}]\n" + "\n".join(table_rows)
                current_section_texts.append(table_str)
                text_parts.append(table_str)

        if current_section_texts:
            sec_text = "\n\n".join(current_section_texts)
            page_records.append((section_idx, sec_text, current_heading))

        combined_full_text = "\n\n".join(text_parts)
        chunks = self._chunker.chunk_document_pages(page_records)

        # Basic metadata
        core_props = doc.core_properties
        detected_meta = {
            "title": core_props.title or filename,
            "author": core_props.author or "Unknown",
            "subject": core_props.subject or "",
            "keywords": core_props.keywords or "",
            "format": "docx",
        }

        return ExtractionResult(
            full_text=combined_full_text,
            markdown_content=combined_full_text,
            page_count=max(1, section_idx),
            chunks=chunks,
            detected_metadata=detected_meta,
            ocr_applied=False,
            notes=[],
        )
