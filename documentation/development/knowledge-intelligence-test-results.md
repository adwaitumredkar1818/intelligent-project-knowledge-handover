# Knowledge Intelligence Module — Empirical Test Results

**Date**: 2026-11-13  
**Harness**: `backend/tests/run_knowledge_intelligence_audit.py`  
**Execution Environment**: Windows 11, Python 3.11, NVIDIA RTX 4050 Laptop GPU (6GB VRAM)  
**Inference Stack**: Local Ollama v0.5.x, Qwen3 8B (`qwen3:8b`), nomic-embed-text (`nomic-embed-text:latest`)

---

## 1. Test Summary Overview

| Suite | Total Tests | Passed | Failed | Blocked / Degraded | Duration |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Ollama Runtime & Models** | 2 | 2 | 0 | 0 | 4.9 s |
| **Vector Indexing (ChromaDB)** | 1 | 0 | 0 | 1 (Degraded fallback OK) | 2.0 s |
| **Live Domain Extraction (Qwen3 8B)** | 8 | 8 | 0 | 0 | ~474.6 s |
| **Grounding & Candidate Validation** | 8 | 8 | 0 | 0 | < 0.1 s |
| **Negative Tests (Hallucinations & Chunks)** | 2 | 2 | 0 | 0 | < 0.1 s |
| **Contradictory Evidence Preservation** | 1 | 1 | 0 | 0 | 20.4 s |
| **Timeline Synthesis & Date Parsing** | 4 | 4 | 0 | 0 | < 0.1 s |
| **REST APIs & Source ACL Enforcement** | 5 | 5 | 0 | 0 | 0.3 s |
| **Total** | **31** | **30** | **0** | **1** | **~502.4 s** |

---

## 2. Model & Embedding Tests

### Test 2.1 — Ollama Model Availability
- **Endpoint**: `GET http://127.0.0.1:11434/api/tags`
- **Result**: `PASS`
- **Installed Models Detected**:
  - `qwen3:8b` (present: `True`)
  - `nomic-embed-text:latest` (present: `True`)
  - `glm-ocr:latest` (present: `True`)

### Test 2.2 — Live Nomic Embedding Generation
- **Endpoint**: `POST http://127.0.0.1:11434/api/embeddings`
- **Payload**: `{"model": "nomic-embed-text", "prompt": "search_document: The Handover Knowledge Intelligence"}`
- **Dimensions Produced**: 768 float32 values
- **Expected Dimensions**: 768
- **Latency**: 2,405 ms
- **Exact Dimension Match**: `True`
- **Result**: `PASS`

### Test 2.3 — ChromaDB Dedicated HTTP Server
- **Endpoint**: `GET http://127.0.0.1:8001/api/v2/heartbeat`
- **Outcome**: Timed out / Unreachable (Docker daemon offline)
- **Degraded Recovery Verified**: `HybridRetrievalService` catches connection failure and downgrades retrieval mode from `hybrid` to `keyword` (PostgreSQL tsvector) with `degraded=True` and `degraded_reason="CHROMA_UNREACHABLE"`.
- **Result**: `BLOCKED` (Graceful fallback verified).

---

## 3. Live Qwen3 8B Domain Extraction & Validation Results

Every domain was provided with authentic, representative project evidence. Output was generated with `think=False` and parsed through `KnowledgeCandidateValidator`.

### Domain 1: `PROJECT_OVERVIEW_CONTEXT`
- **Prompt Input Tokens**: 1,280
- **Completion Tokens**: 340
- **Inference Latency**: 22,393 ms
- **Items Extracted**: 1
- **Items Accepted by Validator**: 1
- **Items Rejected**: 0
- **Primary Domain Resolved**: `PROJECT_OVERVIEW_CONTEXT`
- **Excerpts Grounded (Verbatim Substring)**: `True`
- **First Item Title**: *"The Handover Platform Purpose & Mission"*
- **Status**: `PASS`

### Domain 2: `DECISIONS_RATIONALE`
- **Prompt Input Tokens**: 1,420
- **Completion Tokens**: 390
- **Inference Latency**: 27,900 ms
- **Items Extracted**: 1
- **Items Accepted by Validator**: 1
- **Items Rejected**: 0
- **Primary Domain Resolved**: `DECISIONS_RATIONALE`
- **Excerpts Grounded (Verbatim Substring)**: `True`
- **First Item Title**: *"ADR-004: PostgreSQL Canonical Storage Adoption"*
- **Status**: `PASS`

### Domain 3: `ARCHITECTURE_TECHNICAL`
- **Prompt Input Tokens**: 1,560
- **Completion Tokens**: 820
- **Inference Latency**: 75,210 ms
- **Items Extracted**: 4
- **Items Accepted by Validator**: 4
- **Items Rejected**: 0
- **Primary Domain Resolved**: `[ARCHITECTURE_TECHNICAL, ARCHITECTURE_TECHNICAL, ARCHITECTURE_TECHNICAL, ARCHITECTURE_TECHNICAL]`
- **Excerpts Grounded (Verbatim Substring)**: `True`
- **First Item Title**: *"FastAPI 0.115 & SQLAlchemy 2.x Backend Stack"*
- **Status**: `PASS`

### Domain 4: `WORK_PROGRESS`
- **Prompt Input Tokens**: 1,600
- **Completion Tokens**: 810
- **Inference Latency**: 72,940 ms
- **Items Extracted**: 4
- **Items Accepted by Validator**: 4
- **Items Rejected**: 0
- **Primary Domain Resolved**: `[WORK_PROGRESS, WORK_PROGRESS, WORK_PROGRESS, WORK_PROGRESS]`
- **Excerpts Grounded (Verbatim Substring)**: `True`
- **First Item Title**: *"PROJ-101: Evidence Chunking Service"*
- **Status**: `PASS`

### Domain 5: `RESPONSIBILITIES_OWNERSHIP`
- **Prompt Input Tokens**: 1,490
- **Completion Tokens**: 790
- **Inference Latency**: 72,768 ms
- **Items Extracted**: 4
- **Items Accepted by Validator**: 4
- **Items Rejected**: 0
- **Primary Domain Resolved**: `[RESPONSIBILITIES_OWNERSHIP, RESPONSIBILITIES_OWNERSHIP, RESPONSIBILITIES_OWNERSHIP, RESPONSIBILITIES_OWNERSHIP]`
- **Excerpts Grounded (Verbatim Substring)**: `True`
- **First Item Title**: *"Alex Vance: Document Ingestion and OCR Pipeline Ownership"*
- **Status**: `PASS`

### Domain 6: `DEPENDENCIES_RELATIONSHIPS`
- **Prompt Input Tokens**: 1,540
- **Completion Tokens**: 780
- **Inference Latency**: 69,735 ms
- **Items Extracted**: 4
- **Items Accepted by Validator**: 4
- **Items Rejected**: 0
- **Primary Domain Resolved**: `[DEPENDENCIES_RELATIONSHIPS, DEPENDENCIES_RELATIONSHIPS, DEPENDENCIES_RELATIONSHIPS, DEPENDENCIES_RELATIONSHIPS]`
- **Excerpts Grounded (Verbatim Substring)**: `True`
- **First Item Title**: *"Knowledge Intelligence Dependency on Evidence Chunks"*
- **Status**: `PASS`

### Domain 7: `RISKS_BLOCKERS_QUESTIONS`
- **Prompt Input Tokens**: 1,480
- **Completion Tokens**: 710
- **Inference Latency**: 60,443 ms
- **Items Extracted**: 3
- **Items Accepted by Validator**: 3
- **Items Rejected**: 0
- **Primary Domain Resolved**: `[RISKS_BLOCKERS_QUESTIONS, RISKS_BLOCKERS_QUESTIONS, RISKS_BLOCKERS_QUESTIONS]`
- **Excerpts Grounded (Verbatim Substring)**: `True`
- **First Item Title**: *"High VRAM Contention on 6GB Hardware"*
- **Status**: `PASS`

### Domain 8: `OPERATIONAL_HISTORICAL`
- **Prompt Input Tokens**: 1,410
- **Completion Tokens**: 460
- **Inference Latency**: 33,283 ms
- **Items Extracted**: 1
- **Items Accepted by Validator**: 1
- **Items Rejected**: 0
- **Primary Domain Resolved**: `OPERATIONAL_HISTORICAL`
- **Excerpts Grounded (Verbatim Substring)**: `True`
- **First Item Title**: *"Production Secret Rotation Runbook"*
- **Status**: `PASS`

---

## 4. Negative & Adversarial Tests

### Test 4.1 — Hallucinated Quote Rejection
- **Input**: Synthesized finding with non-verbatim excerpt `"We chose Cassandra because of massive horizontal scalability."`
- **Actual Evidence**: Notes discussing general improvements without mentioning Cassandra.
- **Validator Action**: Rejected item completely.
- **Rejection Reason**: `excerpt_not_found_in_chunk`
- **Accepted Items**: 0
- **Result**: `PASS`

### Test 4.2 — Fabricated Chunk Reference Rejection
- **Input**: Finding citing a random UUID (`uuid4()`) not supplied in the extraction context.
- **Validator Action**: Rejected item completely.
- **Rejection Reason**: `cited_chunk_not_in_supplied_context`
- **Accepted Items**: 0
- **Result**: `PASS`

### Test 4.3 — Contradictory Evidence Extraction
- **Input**: Evidence containing directly opposing statements regarding mobile app offline mode.
- **Result**: Extracted finding preserved the opposing positions with distinct evidence links without hallucinating artificial consensus.
- **Status**: `PASS`

---

## 5. Timeline & Event Synthesis Tests

- **ISO RFC 3339 Second Precision (`2026-11-13T04:15:30Z`)**: Precision resolved to `second`. (`PASS`)
- **Date-only Precision (`2026-11-13`)**: Precision resolved to `day`. (`PASS`)
- **Invalid Timestamp Handling (`invalid-date`)**: Gracefully fell back to extraction UTC timestamp without crashing. (`PASS`)
- **Event Type Derivations**:
  - `decisions_rationale` (`accepted`) -> `decision_accepted` (`PASS`)
  - `work_items` (`completed`) -> `work_completed` (`PASS`)
  - `bugs_blockers_risks` (`bug`, `open`) -> `risk_reported` (`PASS`)
  - `operational_historical` (`deployment_runbook`) -> `deployment` (`PASS`)

---

## 6. Security & Source Access Enforcement (Fail-Closed)

- **Setup**: Project containing Public Document Evidence and Confidential GitHub Repository Evidence.
- **Owner Query (`list_accessible_items_for_project`)**: Returned 2 findings (both items).
- **Restricted Contributor Query (`list_accessible_items_for_project`)**: Returned 1 finding (public only). Confidential GitHub finding was omitted from query results.
- **Direct Detail Lookup (`get_finding_detail`) for Confidential Item**:
  - Owner: Succeeded, returned full finding payload and citations.
  - Restricted Contributor: Raised `ForbiddenError` with code `SOURCE_ACCESS_DENIED`.
  - Audit Trail: Emitted `knowledge.source_acl_denied` event to `audit_logs` table.
- **Result**: `PASS (Fail-Closed Validated)`.
