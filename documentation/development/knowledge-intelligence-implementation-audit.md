# Knowledge Intelligence Implementation Audit

**Product**: The Handover — Intelligent Project Knowledge Reconstruction & Handover Platform  
**Module**: Module 3 — Knowledge Intelligence  
**Audit Date**: November 13, 2026  
**Auditor**: Antigravity Software Engineering Agent  
**Objective**: Comprehensive codebase audit of all existing infrastructure, ingestion, extraction, validation, and retrieval systems to establish the architectural baseline and gap analysis for the 8-domain Knowledge Intelligence backend.

---

## 1. Executive Summary & Architectural Verification

The repository contains a mature, enterprise-grade foundation for knowledge extraction and provenance tracking originally designed during Phase 2.6. Rather than starting from scratch, the Knowledge Intelligence system must build upon this foundation.

### Core Architectural Principle
> **AI EXTRACTS KNOWLEDGE. EVIDENCE SUPPORTS IT. AUTHORISED HUMANS VALIDATE IT.**

The existing implementation already adheres strictly to the rule `NO EVIDENCE -> NO CLAIM`:
1. It validates candidate claims extracted by Qwen3 against specific `EvidenceChunk` IDs.
2. It verifies that quoted excerpts match the chunk text verbatim (exact or normalized whitespace).
3. It rejects ungrounded or hallucinated citations at the backend boundary before database insertion.
4. It enforces source-level access control (`Project Membership != Source Access`) so that users only see knowledge derived from evidence they are authorized to access.

However, the current system was built around **6 categories** (`decisions_rationale`, `work_items`, `responsibilities_ownership`, `technical_architecture`, `bugs_blockers_risks`, `dependencies`). To achieve the canonical vision of The Handover, it must be upgraded to **8 canonical product domains** with a central domain registry, compatibility mapping, 2 new domain prompt pipelines (`PROJECT_OVERVIEW_CONTEXT`, `OPERATIONAL_HISTORICAL`), an updated PostgreSQL schema/constraint, and cross-domain Project Timeline synthesis.

---

## 2. Detailed Audit of the 21 Architectural Capabilities

### 1. Evidence Ingestion
- **Existing Models**: `EvidenceItem`, `DocumentFile`, `EvidenceContent` in `backend/app/models/evidence.py`.
- **Existing Services**: `EvidenceService` in `backend/app/services/evidence.py`, `DocumentExtractionService` in `backend/app/services/document_extraction.py`.
- **Existing APIs**: `POST /api/v1/projects/{project_id}/evidence/upload`, `GET /api/v1/projects/{project_id}/evidence`.
- **Worker Job**: `BackgroundJobType.DOCUMENT_INGESTION` processed by `IngestionWorkerService` in `backend/app/services/ingestion_worker.py`.
- **Existing Tests**: `backend/tests/test_upload_and_dedup_api.py`, `backend/tests/test_document_extraction_and_ocr.py`.
- **Current Status**: `PASS` (Fully implemented and operational).
- **Missing Functionality**: None.
- **Required Modifications**: None. Ingestion supplies immutable evidence items and chunk records directly to Knowledge Intelligence.

### 2. Evidence Metadata
- **Existing Models**: `EvidenceItem` fields: `source_type`, `source_provider`, `source_external_id`, `source_url`, `source_author_identity`, `source_created_at`, `source_updated_at`, `extracted_at`, `content_hash`, `acl_scope`, `source_access_policy_id`.
- **Existing Services**: Repository access via `EvidenceRepository` in `backend/app/repositories/evidence.py`.
- **Current Status**: `PASS` (Fully implemented).
- **Missing Functionality**: None.
- **Required Modifications**: None. Metadata is preserved and propagated to `KnowledgeEvidenceLink`.

### 3. Evidence Chunks
- **Existing Models**: `EvidenceChunk` in `backend/app/models/evidence.py`.
- **Existing Services**: `ChunkingService` in `backend/app/services/chunking.py`.
- **Chunk Parameters**: 500-token sliding window with 50-token overlap, retaining `page_number`, `section_title`, `char_start`, `char_end`, `chunk_content_hash`.
- **Existing Tests**: `backend/tests/test_chunking_service.py`.
- **Current Status**: `PASS` (Fully implemented).
- **Missing Functionality**: None.
- **Required Modifications**: None. Chunks provide bounded contexts (`<evidence_chunk ...>`) for LLM prompts.

### 4. PDF and DOCX Extraction
- **Existing Services**: `DocumentExtractionService` in `backend/app/services/document_extraction.py` using PyMuPDF (fitz) and `python-docx`.
- **Existing Tests**: `backend/tests/test_document_extraction_and_ocr.py`.
- **Current Status**: `PASS` (Fully implemented).
- **Missing Functionality**: None.
- **Required Modifications**: None.

### 5. GLM OCR
- **Existing Service**: `OllamaGLMOCRService` in `backend/app/services/ocr.py`.
- **Model**: `glm-ocr:latest` on local Ollama runtime.
- **Guardrails**: `_OLLAMA_INFERENCE_LOCK` for single-GPU synchronization, `_detect_suspicious_ocr_output` for repetition detection.
- **Current Status**: `PASS` (Live tested on rendered pages).
- **Missing Functionality**: None.
- **Required Modifications**: None.

### 6. GitHub Ingestion
- **Existing Service**: `GitHubIntegrationService` in `backend/app/services/integrations/github.py`.
- **Auth Modes**: Fine-grained Personal Access Token (PAT) read-only mode active; OAuth App mode prepared.
- **Ingestion Scope**: Commits, pull requests, issues, and diff summaries.
- **Existing Tests**: `backend/tests/test_github_integration.py`.
- **Current Status**: `PASS` (PAT operational; OAuth unconfigured).
- **Missing Functionality**: None.
- **Required Modifications**: None.

### 7. Jira Ingestion
- **Existing Service**: `JiraIntegrationService` in `backend/app/services/integrations/jira.py`.
- **Auth Modes**: API token mode active; Atlassian OAuth 2.0 (3LO) prepared.
- **Ingestion Scope**: Issues, descriptions, comments, transition histories.
- **Existing Tests**: `backend/tests/test_jira_integration.py`.
- **Current Status**: `PASS` (Token operational; OAuth unconfigured).
- **Missing Functionality**: None.
- **Required Modifications**: None.

### 8. Slack Ingestion
- **Existing Service**: `SlackIntegrationService` in `backend/app/services/integrations/slack.py`.
- **Auth Modes**: Bot Token (`xoxb-`) and OAuth v2 implemented.
- **Current Status**: `NOT CONFIGURED` (Service ready; live credentials unset).
- **Missing Functionality**: Live credentials.
- **Required Modifications**: None for backend architecture.

### 9. Nomic Embedding Generation
- **Existing Service**: `OllamaEmbeddingService` in `backend/app/services/embedding.py`.
- **Model**: `nomic-embed-text:latest` (768 dimensions).
- **Telemetry**: 352ms/item batch latency; verified cosine similarity discrimination.
- **Current Status**: `PASS` (Live verified).
- **Missing Functionality**: None.
- **Required Modifications**: None.

### 10. ChromaDB Project Collections
- **Existing Service**: `ChromaV2HttpVectorStore` in `backend/app/services/vector_store.py`.
- **Partitioning**: Project-isolated collection `ipkrh_evidence_chunks_nomic-embed-text_v1`.
- **Telemetry**: HTTP REST v2 adapter, verified cosine search, deterministic vector IDs (`{evidence_id}:{chunk_index}`).
- **Current Status**: `PASS` (Live verified).
- **Missing Functionality**: None.
- **Required Modifications**: None.

### 11. Hybrid Retrieval
- **Existing Service**: `RetrievalService` in `backend/app/services/retrieval.py`.
- **Algorithm**: Reciprocal Rank Fusion (RRF) combining ChromaDB vector similarity and PostgreSQL `tsvector` FTS (`ts_rank_cd`).
- **Security**: Pre-retrieval source ACL filtering pruning inaccessible candidate chunks.
- **Existing Tests**: `backend/tests/test_retrieval_security_and_api.py`, `backend/tests/test_pg_fts_and_live_evaluation.py`.
- **Current Status**: `PASS` (Fully implemented).
- **Missing Functionality**: None.
- **Required Modifications**: None. Can be queried to retrieve targeted evidence chunks when initiating domain extraction.

### 12. PostgreSQL-Backed Workers
- **Existing Service**: `CompositeWorkerService` in `backend/app/worker.py`, `ReconstructionWorkerService` in `backend/app/services/reconstruction_worker.py`.
- **Job Models**: `BackgroundJob` in `backend/app/models/job.py`.
- **Concurrency**: Lease-based locking (`worker_id`, `lease_expires_at`), attempt counters, exponential backoff.
- **Existing Tests**: `backend/tests/test_worker_lifecycle.py`, `backend/tests/test_indexing_worker_and_recovery.py`.
- **Current Status**: `PASS` (Fully implemented).
- **Missing Functionality**: Worker needs to support 8 canonical domain job payloads.
- **Required Modifications**: Expand category processing loop in `ReconstructionWorkerService` to handle the 8 canonical domains.

### 13. Ollama Inference Coordinator
- **Existing Implementation**: `_OLLAMA_INFERENCE_LOCK = threading.Lock()` in `backend/app/services/ocr.py` and `backend/app/services/llm.py`.
- **Purpose**: Prevents concurrent execution of Qwen3 8B (4.1 GB VRAM) and GLM OCR (2.3 GB VRAM) on RTX 4050 6GB VRAM.
- **Current Status**: `PASS` (Verified live; zero VRAM collisions).
- **Missing Functionality**: None.
- **Required Modifications**: None.

### 14. Qwen3 Structured Output Service
- **Existing Service**: `OllamaLLMClient` in `backend/app/services/llm.py`.
- **Mode**: JSON-constrained generation (`format="json"`) and system-prompt schema guidance.
- **Telemetry**: Verified 88 prompt tokens, 124 completion tokens in 9.2s on live hardware. Negative grounding check passed.
- **Current Status**: `PASS` (Live verified).
- **Missing Functionality**: None.
- **Required Modifications**: None. Used directly by the 8 domain prompts.

### 15. Existing Knowledge Extraction
- **Existing Implementation**: `KnowledgeReconstructionService` in `backend/app/services/knowledge.py`, `ReconstructionWorkerService` in `backend/app/services/reconstruction_worker.py`, `extraction_prompts.py`.
- **Current Categories**: 6 Phase 2.6 categories:
  - `decisions_rationale`
  - `work_items`
  - `responsibilities_ownership`
  - `technical_architecture`
  - `bugs_blockers_risks`
  - `dependencies`
- **Current Status**: `PASS` (Operational for 6 categories).
- **Missing Functionality**:
  1. Does not implement Domain 1: `PROJECT_OVERVIEW_CONTEXT` (Project Purpose, Objectives, Scope, Stakeholders, Constraints).
  2. Does not implement Domain 8: `OPERATIONAL_HISTORICAL` (Runbooks, deployment, configurations, past rejected approaches, historical incidents).
  3. Lacks a central domain registry mapping product domains to underlying schemas and legacy categories.
- **Required Modifications**:
  - Establish `KnowledgeDomain` enum and central registry.
  - Implement prompt templates and Pydantic schemas for `PROJECT_OVERVIEW_CONTEXT` and `OPERATIONAL_HISTORICAL`.
  - Update `ALL_EXTRACTION_CATEGORIES` / `ALL_KNOWLEDGE_DOMAINS`.

### 16. Knowledge Candidate Validation
- **Existing Implementation**: `KnowledgeCandidateValidator` in `backend/app/services/knowledge_validator.py`.
- **Validation Rules**:
  - Schema conformity via Pydantic candidate models.
  - Verbatim excerpt matching in cited chunk text (exact match or normalized whitespace).
  - Minimum excerpt length (12 chars).
  - Explicit severity check (`unspecified` unless explicit priority tokens are found).
  - Deterministic fingerprint calculation for deduplication.
- **Current Status**: `PASS` (Operational for 6 categories).
- **Missing Functionality**:
  - Candidate schemas and validation rules for `PROJECT_OVERVIEW_CONTEXT` and `OPERATIONAL_HISTORICAL`.
- **Required Modifications**:
  - Add `ProjectOverviewCandidate` and `OperationalHistoricalCandidate` schemas.
  - Register them in `_CANDIDATE_MODEL_BY_CATEGORY` / `_CANDIDATE_MODEL_BY_DOMAIN`.
  - Add domain-specific fingerprint algorithms.

### 17. Knowledge Evidence Links
- **Existing Models**: `KnowledgeEvidenceLink` in `backend/app/models/knowledge.py`.
- **Fields**: `knowledge_item_id`, `evidence_id`, `evidence_chunk_id`, `support_type`, `source_location_json`, `supporting_excerpt`, `excerpt_verified`, `excerpt_match_mode`, `source_metadata_json`.
- **Existing Tests**: `backend/tests/test_knowledge_validation_and_dedup.py`.
- **Current Status**: `PASS` (Fully implemented).
- **Missing Functionality**:
  - `support_type` check constraint in DB currently only permits `'direct', 'corroborated', 'interpretation', 'uncertain'`. Part 5 requires support for roles: `direct_support`, `corroboration`, `context`, `contradiction`.
- **Required Modifications**:
  - Expand `knowledge_evidence_link_support_type` check constraint via Alembic migration to accept canonical roles (`direct_support`, `corroboration`, `context`, `contradiction`).

### 18. Cross-Source Entity Resolution
- **Existing Models**: `ProjectSourceMapping` in `backend/app/models/integration.py`.
- **Current Status**: `NOT IMPLEMENTED` (Phase 2.7).
- **Missing Functionality**: Automated entity linker between GitHub commits and Jira issues.
- **Required Modifications**: Out of scope for Knowledge Intelligence core backend, but data structures must preserve source identifiers (`exact_identifiers`, `related_references`).

### 19. Relationship Mapping
- **Existing Models**: Relational schema in PostgreSQL.
- **Existing Services**: Category 6 (`dependencies`) extracts dependency relationships (`source_item`, `target_item`, `dependency_type`, `direction`).
- **Current Status**: `PASS` (Relational representation).
- **Missing Functionality**: None for this phase.
- **Required Modifications**: Preserve dependency findings within `DEPENDENCIES_RELATIONSHIPS` domain.

### 20. Audit Logging
- **Existing Implementation**: `AuditService` in `backend/app/services/audit.py`, `AuditLog` in `backend/app/models/audit.py`.
- **Events Logged**: `knowledge_extraction.triggered`, `knowledge_extraction.completed`, `knowledge_item.created`, `knowledge_item.stale_detected`.
- **Current Status**: `PASS` (Operational).
- **Missing Functionality**: None.
- **Required Modifications**: Log domain-specific extraction triggers.

### 21. Authentication, RBAC and Source ACLs
- **Existing Implementation**: `RbacService` in `backend/app/services/rbac.py`, `SourceAccessPolicyService` in `backend/app/services/integrations/access_policy.py`, `_accessible_evidence_sql_clause` in `backend/app/repositories/knowledge.py`.
- **Critical Directive**: `Project Membership != Source Access`.
- **Current Status**: `PASS` (Exhaustively verified in `test_evidence_isolation.py`).
- **Missing Functionality**: None.
- **Required Modifications**: Ensure new Knowledge Intelligence endpoints (`/knowledge-intelligence/*`) apply the same strict read-time source ACL filtering.

---

## 3. Summary of Gaps & Required Upgrades

| Area | Current Phase 2.6 State | Target Knowledge Intelligence State | Required Modifications |
| :--- | :--- | :--- | :--- |
| **Domain Taxonomy** | 6 categories (`KnowledgeCategory` enum) | 8 canonical product domains (`KnowledgeDomain` enum) | Create central domain registry; map 6 legacy categories to canonical domains; add migration for check constraint. |
| **Domain 1: Project Overview & Context** | Not implemented | Full extraction pipeline (purpose, scope, stakeholders, constraints, terminology) | Create `ProjectOverviewCandidate` schema, prompt template `overview_context_v1`, validator rules. |
| **Domain 8: Operational & Historical** | Partial (some deployment notes in Category 4) | Dedicated operational and historical reconstruction pipeline | Create `OperationalHistoricalCandidate` schema, prompt template `operational_historical_v1`, validator rules. |
| **Project Timeline** | Not implemented | Cross-domain chronological event perspective | Create `ProjectTimelineEvent` schema and synthesis service derived from timestamped findings and evidence. |
| **Knowledge Intelligence APIs** | Basic Phase 2.6 `/projects/{id}/knowledge/*` routes | Full `/projects/{id}/knowledge-intelligence/*` endpoints | Add domain discovery, summary stats, findings listing with multi-domain filters, details, and timeline endpoints. |
| **Evidence Link Roles** | `direct`, `corroborated`, `interpretation`, `uncertain` | `direct_support`, `corroboration`, `context`, `contradiction` | Update check constraint in PostgreSQL and schema models to accept all canonical evidence roles. |
| **Database Check Constraints** | `knowledge_items.category` restricted to 6 legacy strings | Permissive of 8 canonical domains + 6 legacy strings | Alembic migration `0010_knowledge_domains_and_timeline.py` updating table check constraint. |

---

## 4. Audit Conclusion & Next Step

The existing Phase 2.6 architecture is robust, highly modular, and fully tested. We can achieve 100% compliance with the Knowledge Intelligence Master Directive by extending existing services, adding a central domain registry, implementing the 2 missing domain prompts/schemas, updating the check constraints via an Alembic migration, and surfacing the canonical Knowledge Intelligence APIs.

Proceeding to create `documentation/development/knowledge-intelligence-implementation-plan.md`.
