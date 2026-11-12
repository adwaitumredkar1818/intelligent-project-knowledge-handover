# ADR 0004: Ollama as the Sole Local AI Inference Runtime

## Status
Accepted

## Context
The Handover operates on private organizational codebases, architecture documents, issues, and discussions. Using cloud AI APIs risks confidential intellectual property leakage and external vendor lock-in. A local AI inference runtime running directly on the development/host machine ensures total data sovereignty.

## Decision
1. **Ollama on Host**: Ollama runs natively on the Windows host (`http://127.0.0.1:11434` or `http://host.docker.internal:11434`), providing local GPU/CPU hardware acceleration without cloud transmission.
2. **Standardized Model Roster**:
   - **Qwen3 8B** (`qwen3:8b`): Structured knowledge extraction, architectural analysis, decision rationale reconstruction, and risk identification via structured JSON outputs.
   - **GLM OCR** (`glm-ocr:latest`): Optical character recognition for scanned/image-based PDF pages behind an intelligent fallback abstraction (machine-readable pages extracted first via PyMuPDF).
   - **Nomic Embed Text** (`nomic-embed-text`): Unified 768-dimensional semantic embeddings for all evidence chunks.
3. **Sequential Execution Coordinator**: To prevent VRAM exhaustion on local hardware (e.g. RTX 4050 6GB VRAM / 16GB RAM), a centralized inference coordinator enforces `OLLAMA_MAX_CONCURRENT_AI_JOBS=1`. Qwen3 and GLM OCR are never loaded simultaneously.

## Consequences
- Complete zero-data-leakage architecture.
- Predictable VRAM footprint and reliable execution on consumer hardware.
