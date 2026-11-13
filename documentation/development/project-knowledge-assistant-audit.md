# Project Knowledge Assistant — Existing Implementation Audit

**Platform**: The Handover (Intelligent Project Knowledge Reconstruction & Handover Platform)  
**Module**: Project Knowledge Assistant (Module 5 / AI Assistant Area)  
**Date**: November 2026  
**Status**: Stage 1 Audit Complete

---

## 1. Executive Summary

This audit assesses the readiness of all existing repository layers for the **Project Knowledge Assistant**, a permission-aware, evidence-grounded AI assistant designed to answer project questions using actual reconstructed knowledge, relationship graphs, original evidence records, and verification decisions.

The assistant is strictly read-only and uses:
- **Canonical PostgreSQL**: Data store for conversations, messages, citations, retrieval logs, user feedback, and ACL checks.
- **Dedicated ChromaDB HTTP service**: Project-isolated vector collections storing 768-dim embeddings (`nomic-embed-text:latest`).
- **Ollama on Windows**: Local inference runtime running `qwen3:8b` (structured answer generation) and `nomic-embed-text:latest` (query vectorisation), coordinated under `_OLLAMA_INFERENCE_LOCK`.
- **Hybrid Retrieval**: PostgreSQL FTS + ChromaDB semantic vector search combined via Reciprocal Rank Fusion (RRF), enriched with structured Knowledge Intelligence (8 domains), Relationship Explorer graphs, and Project Timeline events.

---

## 2. 30-Capability Repository Audit Matrix

| # | Capability / Subsystem | Existing Models & Code | Existing Services & APIs | Actual Implementation Status | Missing / Required Integration Work |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **1** | **Platform Auth & JWT** | `User`, `RefreshSession` (`app/models/auth.py`, `user.py`) | `create_access_token`, `decode_access_token`, `get_current_principal` (`app/core/security.py`, `app/api/deps.py`) | **Complete and verified** | Validate session family and project context on every assistant request. |
| **2** | **User Profiles** | `User` (`app/models/user.py`) | `UserRepository`, `UserService` | **Complete and verified** | Associate conversation creation with `principal.user_id`. |
| **3** | **Organisations & Projects** | `Organisation`, `Project` (`app/models/organisation.py`, `project.py`) | `OrganisationService`, `ProjectService`, `ProjectRepository` | **Complete and verified** | Multi-tenant isolation; conversations strictly bounded to `project_id` and `organisation_id`. |
| **4** | **Project Membership & RBAC** | `ProjectMembership`, `Role`, `RolePermission` (`app/models/rbac.py`) | `RbacService`, `require_project_permission` (`app/services/rbac.py`) | **Complete and verified** | Add `assistant.*` permissions to `rbac_catalog.py` and seed into PostgreSQL via Alembic. |
| **5** | **Source-Level Permissions (ACLs)** | `SourceAccessPolicy`, `SourceCredential` (`app/models/integration.py`) | `SourceAccessPolicyService` (`app/services/integrations/access_policy.py`) | **Complete and verified** | Critical: filter candidate evidence at read time before LLM context construction. |
| **6** | **Evidence Workspace** | `EvidenceItem` (`app/models/evidence.py`) | `EvidenceItemRepository`, `EvidenceService` (`app/services/evidence.py`) | **Complete and verified** | Provide raw evidence metadata, source URLs, and author attribution for citations. |
| **7** | **Evidence Records** | `EvidenceItem` with `acl_scope`, `source_type`, `category` | Storage factory, streaming download endpoints | **Complete and verified** | Verify active status and unrevoked access before returning excerpts. |
| **8** | **Evidence Chunking** | `EvidenceChunk` (`app/models/evidence.py`) | `EvidenceChunkRepository`, `ChunkingService` (`app/services/chunking.py`) | **Complete and verified** | Fetch chunk excerpts, page numbers, character offsets, and section titles for grounding. |
| **9** | **PDF Extraction** | PyMuPDF pipeline | `DocumentExtractionService` (`app/services/document_extraction.py`) | **Complete and verified** | Bounded excerpt extraction with page references. |
| **10** | **DOCX Extraction** | `python-docx` extraction pipeline | `DocumentExtractionService` | **Complete and verified** | Section-aware chunk extraction. |
| **11** | **GLM OCR** | `glm-ocr:latest` on Ollama | `OCRService` (`app/services/ocr.py`) | **Complete and verified** | Scanned document OCR runs during ingestion; assistant accesses extracted chunks only. |
| **12** | **GitHub Ingestion** | `github_commits`, `github_pull_requests`, `github_issues` | `GitHubIntegrationService` (`app/services/integrations/github.py`) | **Complete and verified** | Support GitHub PR/commit queries and PR-to-decision linking. |
| **13** | **Jira Ingestion** | `jira_issues`, `jira_components` | `JiraIntegrationService` (`app/services/integrations/jira.py`) | **Complete and verified** | Support Jira key lookups and task status verification. |
| **14** | **Slack Ingestion** | `slack_messages`, `slack_channels` | `SlackIntegrationService` (`app/services/integrations/slack.py`) | **Implemented but incomplete** | Where configured, channel privacy must be enforced at retrieval time. |
| **15** | **PostgreSQL FTS** | `tsvector` and GIN index on `evidence_chunks.tsv` | `EvidenceChunkRepository.keyword_search` (`app/repositories/chunk.py`) | **Complete and verified** | Direct SQL ACL filtering with exact identifier and phrase matching. |
| **16** | **Nomic Embeddings** | `nomic-embed-text:latest` (768-dim) | `EmbeddingService` (`app/services/embedding.py`) | **Complete and verified** | Query vector generation with identical preprocessing and dimension validation. |
| **17** | **ChromaDB Project Collections** | Dedicated HTTP mode, isolated `project_{uuid}` collections | `VectorStoreClient` (`app/services/vector_store.py`) | **Complete and verified** | Query returns candidate IDs and scores; contents verified in PostgreSQL. |
| **18** | **Hybrid Retrieval Engine** | RRF fusion of FTS + Chroma | `HybridRetrievalService` (`app/services/retrieval.py`) | **Complete and verified** | Connect retrieval service into assistant query execution pipeline. |
| **19** | **Knowledge Intelligence** | `KnowledgeItem`, `KnowledgeDomain` (8 domains) | `KnowledgeIntelligenceService` (`app/services/knowledge_intelligence.py`) | **Complete and verified** | Query routing across 8 domains and structured knowledge retrieval. |
| **20** | **8 Knowledge Domains** | Canonical domains defined in `KnowledgeDomain` enum | `KnowledgeDomainService` (`app/services/knowledge_domains.py`) | **Complete and verified** | Domain-filtered retrieval and cross-domain synthesis. |
| **21** | **Knowledge Evidence Links** | `KnowledgeEvidenceLink` (`app/models/knowledge.py`) | `KnowledgeRepository` | **Complete and verified** | Direct citation tracing from reconstructed knowledge back to primary chunks. |
| **22** | **Knowledge Verification** | `VerificationCase`, `VerificationIssue` (`app/models/verification.py`) | `VerificationEngineService`, `VerificationReviewService` | **Complete and verified** | Distinguish `human_verified` / `approved` from unverified candidates; surface conflicts. |
| **23** | **Relationship Explorer** | `RelationshipItem`, `EntityNode` (`app/models/relationship.py`) | `RelationshipDiscoveryService`, `RelationshipCoordinatorService` | **Complete and verified** | Bounded multi-hop graph expansion (e.g. Decision -> WorkItem -> PR -> Commit). |
| **24** | **Project Timeline** | `TimelineEvent` records | `TimelineService` (`app/services/timeline.py`) | **Complete and verified** | Event chronological queries with source timestamps. |
| **25** | **Background Workers** | PostgreSQL-backed job queue | `IndexingWorker`, `ReconstructionWorker` (`app/services/`) | **Complete and verified** | Synchronous API response for chat queries; worker used for heavy background re-indexing. |
| **26** | **Ollama Qwen3 Service** | `qwen3:8b` structured inference | `StructuredLLMClient`, `OllamaQwenClient` (`app/services/llm.py`) | **Complete and verified** | Strict Pydantic JSON schema output for assistant answer, claims, and citations. |
| **27** | **Inference Scheduler** | `_OLLAMA_INFERENCE_LOCK` (`OLLAMA_MAX_CONCURRENT_AI_JOBS=1`) | Native Windows Ollama adapter | **Complete and verified** | Prevents VRAM exhaustion on RTX 4050 (6GB) during concurrent LLM requests. |
| **28** | **Audit Logging** | `audit_logs` table | `AuditService` (`app/services/audit.py`) | **Complete and verified** | Log assistant interactions, retrieval runs, and permission denial events. |
| **29** | **Assistant Conversations** | *None* | *None* | **Missing** | Implement `assistant_conversations`, `assistant_messages`, `assistant_citations`, `assistant_retrieval_runs`, `assistant_feedback`. |
| **30** | **Handover Workspace** | `HandoverCase`, `HandoverPackageVersion` (`app/models/handover.py`) | `HandoverCaseService`, `PackageAssemblyService`, `HandoverSignoffService` | **Complete and verified** | Support authorized queries regarding approved handover versions and responsibility transfers. |

---

## 3. Gap Analysis & Architecture Directives

1. **New Database Persistence Required**:
   - `assistant_conversations`: Project-scoped, private by default to creator.
   - `assistant_messages`: Ordered conversation turns with structured answer status, model metadata, and latency telemetry.
   - `assistant_citations`: Claim-grounded references linking each response claim to valid `evidence_items` and `evidence_chunks`.
   - `assistant_retrieval_runs`: Diagnostic telemetry of query classification, retrieval strategy, candidate counts, and RRF rankings.
   - `assistant_feedback`: User ratings (helpful, not helpful, incorrect citation, etc.).
2. **Query Classification Layer**:
   - Deterministic pattern matcher + lightweight structured lookup supporting the 12 query types (Project Overview, Decision & Rationale, Technical Architecture, Work & Progress, Responsibility, Dependency, Risk & Problem, Operational & Historical, Timeline, Comparative, Multi-hop, Knowledge Gap).
3. **Structured vs Unstructured Query Routing**:
   - Exact counts, current work status, and entity lookups routed directly to PostgreSQL queries rather than hallucinated via generic prompts.
4. **Authoritative Citation Engine**:
   - Model outputs citation references using stable tokens (`[S1]`, `[S2]`).
   - Backend validates every citation against PostgreSQL before serving the response. Inaccessible, fabricated, or mismatched citations are rejected.
5. **Explicit Uncertainty & Abstention Engine**:
   - Categorizes answers into 8 distinct states: `ANSWERED`, `PARTIALLY_ANSWERED`, `INSUFFICIENT_EVIDENCE`, `CONFLICTED_EVIDENCE`, `OUTDATED_EVIDENCE`, `ACCESS_RESTRICTED`, `UNSUPPORTED_QUERY`, `PROCESSING_ERROR`.
   - Never guesses or uses document authorship as proof of approval.
6. **Prompt Injection Hardening**:
   - Delimited evidence blocks (`<project_evidence id="S1">...</project_evidence>`).
   - Retrieved text explicitly flagged as untrusted data.
   - Model prohibited from executing code, modifying database state, or making access control determinations.
