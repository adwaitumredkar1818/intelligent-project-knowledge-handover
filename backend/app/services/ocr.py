"""Replaceable OCR service abstraction and native Ollama `glm-ocr:latest` adapter."""

from __future__ import annotations

import base64
import logging
import re
import threading
import time
from dataclasses import dataclass
from typing import Any, Protocol

import httpx

from app.core.cache import CacheKeys, CachePolicies, CacheService

logger = logging.getLogger("app.services.ocr")

# Local single-GPU guardrail: run OCR inference sequentially to prevent overlapping
# model memory pressure with Qwen3 8B or concurrent page OCR floods.
_OLLAMA_INFERENCE_LOCK = threading.Lock()
_REPETITION_LOOP_RE = re.compile(r"(.)\1{39,}")


@dataclass(frozen=True, slots=True)
class OCRPageRequest:
    """Bounded single-page image payload sent to an OCR engine."""

    page_number: int
    image_bytes: bytes
    image_width: int
    image_height: int
    document_title: str | None = None


@dataclass(frozen=True, slots=True)
class OCRPageResult:
    """Structured OCR output preserving model telemetry and truncation detection."""

    page_number: int
    text: str
    model_name: str
    truncated: bool
    done_reason: str | None
    prompt_eval_count: int | None
    eval_count: int | None
    duration_ms: int
    warnings: tuple[str, ...] = ()


class OCRExecutionError(RuntimeError):
    """Explicit sanitised failure raised when an OCR backend call fails."""

    def __init__(self, *, code: str, message: str, retryable: bool = True) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.retryable = retryable


class OCRService(Protocol):
    """Replaceable OCR boundary separating extraction pipelines from Ollama/glm-ocr."""

    @property
    def model_name(self) -> str:
        """Identifier of the underlying OCR model or engine."""

    def extract_page_text(self, request: OCRPageRequest) -> OCRPageResult:
        """Extract text from one bounded page image."""


def _detect_suspicious_ocr_output(text: str) -> list[str]:
    warnings: list[str] = []
    stripped = text.strip()
    if not stripped:
        warnings.append("ocr_empty_output")
        return warnings
    if _REPETITION_LOOP_RE.search(stripped):
        warnings.append("ocr_repetitive_output_detected")
    return warnings


class OllamaGLMOCRService:
    """Native Ollama adapter executing `glm-ocr:latest` with explicit context limits."""

    def __init__(
        self,
        *,
        base_url: str,
        model: str = "glm-ocr:latest",
        num_ctx: int = 8192,
        num_predict: int = 4096,
        timeout_seconds: float = 120.0,
        http_client: httpx.Client | None = None,
        cache_service: CacheService | None = None,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._model = model.strip()
        self._num_ctx = max(2048, num_ctx)
        self._num_predict = max(256, num_predict)
        self._timeout_seconds = timeout_seconds
        self._http_client = http_client
        self._cache_service = cache_service

    @property
    def model_name(self) -> str:
        return self._model

    def extract_page_text(self, request: OCRPageRequest) -> OCRPageResult:
        import hashlib
        img_hash = hashlib.sha256(request.image_bytes).hexdigest()
        cache_key = CacheKeys.ocr_page(
            content_hash=img_hash,
            page_number=request.page_number,
            engine=self._model,
            preprocess_version="v1",
        )

        if self._cache_service is not None:
            cached_data = self._cache_service.get(cache_key)
            if cached_data is not None and isinstance(cached_data, dict):
                return OCRPageResult(
                    page_number=request.page_number,
                    text=cached_data.get("text", ""),
                    model_name=self._model,
                    truncated=cached_data.get("truncated", False),
                    done_reason="cached",
                    prompt_eval_count=0,
                    eval_count=0,
                    duration_ms=0,
                    warnings=tuple(cached_data.get("warnings", ())),
                )

        encoded_image = base64.b64encode(request.image_bytes).decode("ascii")
        prompt = (
            "Transcribe all readable text, headings, lists, and table rows from this "
            "document page accurately in natural reading order. Preserve line breaks and "
            "return only the extracted text without commentary."
        )
        payload = {
            "model": self._model,
            "prompt": prompt,
            "images": [encoded_image],
            "stream": False,
            "options": {
                "num_ctx": self._num_ctx,
                "num_predict": self._num_predict,
                "temperature": 0.0,
            },
        }

        started = time.perf_counter()
        raw_response: dict[str, Any]
        with _OLLAMA_INFERENCE_LOCK:
            try:
                if self._http_client is not None:
                    resp = self._http_client.post(
                        f"{self._base_url}/api/generate",
                        json=payload,
                        timeout=self._timeout_seconds,
                    )
                else:
                    with httpx.Client(timeout=self._timeout_seconds) as client:
                        resp = client.post(
                            f"{self._base_url}/api/generate",
                            json=payload,
                        )
            except httpx.TimeoutException as exc:
                raise OCRExecutionError(
                    code="OCR_TIMEOUT",
                    message=f"OCR inference timed out on page {request.page_number}.",
                    retryable=True,
                ) from exc
            except httpx.HTTPError as exc:
                raise OCRExecutionError(
                    code="OCR_UNAVAILABLE",
                    message="Local Ollama OCR service is unavailable.",
                    retryable=True,
                ) from exc

        elapsed_ms = int((time.perf_counter() - started) * 1000)

        if resp.status_code >= 500:
            raise OCRExecutionError(
                code="OCR_UPSTREAM_ERROR",
                message=f"OCR service returned HTTP {resp.status_code}.",
                retryable=True,
            )
        if resp.status_code >= 400:
            raise OCRExecutionError(
                code="OCR_REQUEST_REJECTED",
                message=f"OCR service rejected page {request.page_number} ({resp.status_code}).",
                retryable=False,
            )

        try:
            raw_response = resp.json()
        except ValueError as exc:
            raise OCRExecutionError(
                code="OCR_INVALID_RESPONSE",
                message="OCR service returned non-JSON output.",
                retryable=True,
            ) from exc

        if not isinstance(raw_response, dict):
            raise OCRExecutionError(
                code="OCR_INVALID_RESPONSE",
                message="OCR service returned an invalid payload shape.",
                retryable=True,
            )

        if raw_response.get("error"):
            raise OCRExecutionError(
                code="OCR_MODEL_ERROR",
                message=f"OCR model reported an error: {str(raw_response['error'])[:200]}",
                retryable=False,
            )

        text = str(raw_response.get("response") or "").strip()
        done = bool(raw_response.get("done", False))
        raw_reason = raw_response.get("done_reason")
        done_reason = str(raw_reason) if raw_reason is not None else None
        prompt_eval_count = (
            int(raw_response["prompt_eval_count"])
            if raw_response.get("prompt_eval_count") is not None
            else None
        )
        eval_count = (
            int(raw_response["eval_count"])
            if raw_response.get("eval_count") is not None
            else None
        )

        warnings = _detect_suspicious_ocr_output(text)
        truncated = False
        if not done or done_reason == "length":
            truncated = True
            warnings.append("ocr_output_truncated")
        if eval_count is not None and eval_count >= self._num_predict:
            truncated = True
            if "ocr_output_truncated" not in warnings:
                warnings.append("ocr_output_hit_num_predict")
        if prompt_eval_count is not None and prompt_eval_count >= int(self._num_ctx * 0.95):
            warnings.append("ocr_prompt_near_ctx_limit")

        logger.info(
            "Completed page OCR via Ollama.",
            extra={
                "page_number": request.page_number,
                "ocr_model": self._model,
                "ocr_num_ctx": self._num_ctx,
                "ocr_truncated": truncated,
                "done_reason": done_reason,
                "duration_ms": elapsed_ms,
                "char_count": len(text),
            },
        )

        result = OCRPageResult(
            page_number=request.page_number,
            text=text,
            model_name=self._model,
            truncated=truncated,
            done_reason=done_reason,
            prompt_eval_count=prompt_eval_count,
            eval_count=eval_count,
            duration_ms=elapsed_ms,
            warnings=tuple(warnings),
        )

        if self._cache_service is not None and not truncated:
            self._cache_service.set(
                cache_key,
                {
                    "text": text,
                    "truncated": truncated,
                    "warnings": list(warnings),
                },
                policy=CachePolicies.OCR_RESULT,
            )

        return result
