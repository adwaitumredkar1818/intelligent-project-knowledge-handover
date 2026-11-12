"""Replaceable structured LLM service abstraction and native Ollama `qwen3:8b` adapter."""

from __future__ import annotations

import json
import logging
import re
import time
from dataclasses import dataclass
from typing import Any, Protocol

import httpx

from app.services.ocr import _OLLAMA_INFERENCE_LOCK

logger = logging.getLogger("app.services.llm")

_THINK_BLOCK_RE = re.compile(r"<think>.*?</think>", flags=re.DOTALL | re.IGNORECASE)
_CODE_FENCE_RE = re.compile(
    r"^\s*```(?:json)?\s*\n?(.*?)\n?\s*```\s*$",
    flags=re.DOTALL | re.IGNORECASE,
)


class LLMExecutionError(RuntimeError):
    """Typed, sanitised failure raised when structured LLM generation fails."""

    def __init__(
        self,
        *,
        code: str,
        message: str,
        retryable: bool = True,
        prompt_tokens: int = 0,
        completion_tokens: int = 0,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.retryable = retryable
        self.prompt_tokens = prompt_tokens
        self.completion_tokens = completion_tokens


@dataclass(frozen=True, slots=True)
class LLMChatMessage:
    """Role-delimited chat turn supplied to an LLM endpoint."""

    role: str
    content: str


@dataclass(frozen=True, slots=True)
class LLMGenerationRequest:
    """Bounded structured-JSON generation request."""

    system_prompt: str
    user_prompt: str
    json_schema: dict[str, Any] | None = None
    num_ctx: int | None = None
    num_predict: int | None = None
    temperature: float | None = None


@dataclass(frozen=True, slots=True)
class LLMGenerationResult:
    """Structured response carrying parsed JSON dict and model runtime telemetry."""

    parsed_json: dict[str, Any]
    raw_text: str
    model_name: str
    prompt_tokens: int
    completion_tokens: int
    duration_ms: int
    done_reason: str | None
    truncated: bool


class StructuredLLMClient(Protocol):
    """Replaceable abstraction decoupling knowledge extraction from Ollama/qwen3:8b."""

    @property
    def model_name(self) -> str:
        """Identifier of the configured LLM model."""

    def generate_json(self, request: LLMGenerationRequest) -> LLMGenerationResult:
        """Generate and parse a structured JSON object response."""


def parse_llm_json_object(raw_text: str) -> dict[str, Any]:
    """Extract and parse a JSON object cleanly from LLM output text."""
    cleaned = _THINK_BLOCK_RE.sub("", raw_text).strip()
    fence_match = _CODE_FENCE_RE.match(cleaned)
    if fence_match:
        cleaned = fence_match.group(1).strip()

    if not cleaned:
        raise LLMExecutionError(
            code="LLM_EMPTY_RESPONSE",
            message="LLM returned empty content when structured JSON was expected.",
            retryable=True,
        )

    try:
        loaded = json.loads(cleaned)
    except ValueError:
        start_idx = cleaned.find("{")
        end_idx = cleaned.rfind("}")
        if start_idx == -1 or end_idx <= start_idx:
            raise LLMExecutionError(
                code="LLM_INVALID_JSON",
                message="LLM output did not contain a valid JSON object.",
                retryable=True,
            ) from None
        candidate = cleaned[start_idx : end_idx + 1]
        try:
            loaded = json.loads(candidate)
        except ValueError as exc:
            raise LLMExecutionError(
                code="LLM_INVALID_JSON",
                message="LLM JSON object could not be parsed cleanly.",
                retryable=True,
            ) from exc

    if not isinstance(loaded, dict):
        raise LLMExecutionError(
            code="LLM_INVALID_JSON",
            message="LLM output parsed as JSON but root value was not an object.",
            retryable=True,
        )
    return loaded


class OllamaLLMClient:
    """Native Ollama `/api/chat` structured JSON adapter with GPU lock & safety bounds."""

    def __init__(
        self,
        *,
        base_url: str,
        model: str = "qwen3:8b",
        num_ctx: int = 8192,
        num_predict: int = 2048,
        temperature: float = 0.1,
        timeout_seconds: float = 120.0,
        think: bool = False,
        http_client: httpx.Client | None = None,
        http_transport: httpx.BaseTransport | None = None,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._model = model.strip()
        self._num_ctx = max(2048, int(num_ctx))
        self._num_predict = max(256, int(num_predict))
        self._temperature = float(temperature)
        self._timeout_seconds = max(1.0, float(timeout_seconds))
        self._think = bool(think)
        self._http_client = http_client
        self._http_transport = http_transport

    @property
    def model_name(self) -> str:
        return self._model

    def _post_chat(self, payload: dict[str, Any]) -> httpx.Response:
        if self._http_client is not None:
            return self._http_client.post(
                f"{self._base_url}/api/chat",
                json=payload,
                timeout=self._timeout_seconds,
            )
        with httpx.Client(
            timeout=self._timeout_seconds,
            transport=self._http_transport,
        ) as client:
            return client.post(
                f"{self._base_url}/api/chat",
                json=payload,
            )

    def generate_json(self, request: LLMGenerationRequest) -> LLMGenerationResult:
        payload: dict[str, Any] = {
            "model": self._model,
            "messages": [
                {"role": "system", "content": request.system_prompt},
                {"role": "user", "content": request.user_prompt},
            ],
            "stream": False,
            "think": self._think,
            "format": request.json_schema if request.json_schema is not None else "json",
            "options": {
                "num_ctx": request.num_ctx or self._num_ctx,
                "num_predict": request.num_predict or self._num_predict,
                "temperature": (
                    self._temperature if request.temperature is None else request.temperature
                ),
            },
        }

        started = time.perf_counter()
        with _OLLAMA_INFERENCE_LOCK:
            try:
                resp = self._post_chat(payload)
            except httpx.TimeoutException as exc:
                raise LLMExecutionError(
                    code="LLM_TIMEOUT",
                    message="Local Ollama LLM inference timed out.",
                    retryable=True,
                ) from exc
            except httpx.HTTPError as exc:
                raise LLMExecutionError(
                    code="LLM_UNAVAILABLE",
                    message="Local Ollama LLM runtime is unreachable.",
                    retryable=True,
                ) from exc

        elapsed_ms = int((time.perf_counter() - started) * 1000)

        if resp.status_code >= 500:
            raise LLMExecutionError(
                code="LLM_UPSTREAM_ERROR",
                message=f"Ollama LLM runtime returned HTTP {resp.status_code}.",
                retryable=True,
            )
        if resp.status_code >= 400:
            raise LLMExecutionError(
                code="LLM_REQUEST_REJECTED",
                message=f"Ollama LLM rejected structured request ({resp.status_code}).",
                retryable=False,
            )

        try:
            raw_json = resp.json()
        except ValueError as exc:
            raise LLMExecutionError(
                code="LLM_INVALID_RESPONSE",
                message="Ollama LLM endpoint returned non-JSON envelope.",
                retryable=True,
            ) from exc

        if not isinstance(raw_json, dict):
            raise LLMExecutionError(
                code="LLM_INVALID_RESPONSE",
                message="Ollama LLM endpoint returned unexpected payload type.",
                retryable=True,
            )

        if raw_json.get("error"):
            raise LLMExecutionError(
                code="LLM_MODEL_ERROR",
                message=f"Ollama LLM reported an error: {str(raw_json['error'])[:200]}",
                retryable=False,
            )

        prompt_tokens = max(0, int(raw_json.get("prompt_eval_count") or 0))
        completion_tokens = max(0, int(raw_json.get("eval_count") or 0))
        done_reason_raw = raw_json.get("done_reason")
        done_reason = str(done_reason_raw).strip() if done_reason_raw is not None else None
        truncated = done_reason == "length"

        message_obj = raw_json.get("message")
        raw_content = ""
        if isinstance(message_obj, dict):
            raw_content = str(message_obj.get("content") or "")
        elif "response" in raw_json:
            raw_content = str(raw_json.get("response") or "")

        try:
            parsed = parse_llm_json_object(raw_content)
        except LLMExecutionError as exc:
            if truncated:
                raise LLMExecutionError(
                    code="LLM_TRUNCATED",
                    message="LLM output exceeded max prediction tokens before finishing JSON.",
                    retryable=True,
                    prompt_tokens=prompt_tokens,
                    completion_tokens=completion_tokens,
                ) from exc
            raise LLMExecutionError(
                code=exc.code,
                message=exc.message,
                retryable=exc.retryable,
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
            ) from exc

        logger.debug(
            "Completed structured JSON generation via Ollama.",
            extra={
                "llm_model": self._model,
                "prompt_tokens": prompt_tokens,
                "completion_tokens": completion_tokens,
                "duration_ms": elapsed_ms,
                "done_reason": done_reason,
            },
        )
        return LLMGenerationResult(
            parsed_json=parsed,
            raw_text=raw_content,
            model_name=self._model,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            duration_ms=elapsed_ms,
            done_reason=done_reason,
            truncated=truncated,
        )
