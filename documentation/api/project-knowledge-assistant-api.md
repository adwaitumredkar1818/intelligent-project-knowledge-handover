# Project Knowledge Assistant — REST API Reference

**Platform**: The Handover  
**Base Path**: `/api/v1/projects/{project_id}/assistant`  
**Authentication**: HTTP Bearer (FastAPI-managed JWT access token)  
**Date**: 2026-11-13  

---

## Endpoint Catalog

| Method | Endpoint | Required Permission | Description |
| :--- | :--- | :--- | :--- |
| `GET` | `/conversations` | `assistant.read` | List conversations for the current user and project |
| `POST` | `/conversations` | `assistant.chat` | Create a new conversation thread |
| `GET` | `/conversations/{id}` | `assistant.read` | Retrieve full conversation details with message history |
| `DELETE` | `/conversations/{id}` | `assistant.chat` | Archive/delete a conversation thread |
| `POST` | `/conversations/{id}/messages` | `assistant.chat` | Submit a question and receive an evidence-grounded answer |
| `POST` | `/messages/{id}/feedback` | `assistant.feedback` | Submit helpfulness and accuracy feedback on an answer |
| `GET` | `/diagnostics/retrieval/{run_id}` | `assistant.read` | Inspect RRF retrieval run telemetry, candidates, and ACL filters |
| `GET` | `/suggestions` | `assistant.read` | Generate proactive, contextual question suggestions |

---

## Detailed Payload Specifications

### 1. Create Conversation: `POST /conversations`
**Request Body**:
```json
{
  "title": "Database Architecture & ADR Inquiries",
  "metadata_json": {
    "tags": ["architecture", "postgresql"]
  }
}
```

**Response (201 Created)**:
```json
{
  "id": "c1a2e3f4-5678-90ab-cdef-1234567890ab",
  "organisation_id": "9caf2764-9ef8-4ac1-897e-579c9a271807",
  "project_id": "a1b2c3d4-e5f6-7a8b-9c0d-1e2f3a4b5c6d",
  "user_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
  "title": "Database Architecture & ADR Inquiries",
  "status": "active",
  "message_count": 0,
  "created_at": "2026-11-13T14:00:00Z",
  "updated_at": "2026-11-13T14:00:00Z"
}
```

---

### 2. Submit Question: `POST /conversations/{id}/messages`
**Request Body**:
```json
{
  "question": "Why did the team choose PostgreSQL over MongoDB for canonical storage?",
  "override_query_type": null,
  "filters": {
    "source_types": ["document", "commit", "issue"],
    "knowledge_categories": ["architecture_decision"]
  }
}
```

**Response (200 OK)**:
```json
{
  "conversation_id": "c1a2e3f4-5678-90ab-cdef-1234567890ab",
  "message_id": "f5e4d3c2-b1a0-9876-5432-10fedcba9876",
  "answer": "The team chose PostgreSQL 16 as the canonical relational database due to its native ACID transaction support, JSONB document capabilities, and mature row-level security policies [S1]. An alternative proposal to use MongoDB was rejected because multi-entity ACID consistency across knowledge items and audit logs was a non-negotiable project requirement [S2].",
  "status": "answered",
  "detected_query_type": "decision_rationale",
  "extracted_entities": {
    "jira_keys": [],
    "commit_shas": [],
    "pr_numbers": [],
    "file_paths": [],
    "mentions": []
  },
  "claims": [
    {
      "claim_text": "The team chose PostgreSQL 16 as the canonical relational database due to its native ACID transaction support, JSONB document capabilities, and mature row-level security policies",
      "citations": ["S1"],
      "confidence": 0.95
    },
    {
      "claim_text": "An alternative proposal to use MongoDB was rejected because multi-entity ACID consistency across knowledge items and audit logs was a non-negotiable project requirement",
      "citations": ["S2"],
      "confidence": 0.92
    }
  ],
  "citations": [
    {
      "citation_label": "S1",
      "evidence_item_id": "d0e1f2a3-b4c5-6789-0123-456789abcdef",
      "chunk_id": "e1f2a3b4-c5d6-7890-1234-567890abcdef",
      "source_platform": "document",
      "title": "ADR 001: Canonical Database Selection",
      "source_url": null,
      "author": "Alice Smith",
      "timestamp": "2026-10-15T10:00:00Z",
      "excerpt": "PostgreSQL 16 was selected as canonical database due to native ACID guarantees, JSONB support, and mature row-level security."
    },
    {
      "citation_label": "S2",
      "evidence_item_id": "a1b2c3d4-e5f6-7890-1234-567890abcdef",
      "chunk_id": null,
      "source_platform": "document",
      "title": "Database Evaluation Matrix",
      "source_url": null,
      "author": "Bob Jones",
      "timestamp": "2026-10-14T14:30:00Z",
      "excerpt": "MongoDB evaluation: lacks cross-collection transactions needed for audit logs without performance penalties."
    }
  ],
  "retrieval_run_id": "87654321-abcd-ef01-2345-6789abcdef01",
  "latency_ms": 385.2,
  "created_at": "2026-11-13T14:00:02Z"
}
```

---

### 3. Record Feedback: `POST /messages/{id}/feedback`
**Request Body**:
```json
{
  "feedback_type": "helpful",
  "rating": 5,
  "comment": "Accurately surfaced the specific ADR and rationale.",
  "metadata_json": {}
}
```

**Response (201 Created)**:
```json
{
  "id": "11223344-5566-7788-99aa-bbccddeeff00",
  "message_id": "f5e4d3c2-b1a0-9876-5432-10fedcba9876",
  "user_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
  "feedback_type": "helpful",
  "rating": 5,
  "comment": "Accurately surfaced the specific ADR and rationale.",
  "created_at": "2026-11-13T14:00:10Z"
}
```

---

### 4. Retrieval Diagnostics: `GET /diagnostics/retrieval/{run_id}`
**Response (200 OK)**:
```json
{
  "id": "87654321-abcd-ef01-2345-6789abcdef01",
  "conversation_id": "c1a2e3f4-5678-90ab-cdef-1234567890ab",
  "message_id": "f5e4d3c2-b1a0-9876-5432-10fedcba9876",
  "query_raw": "Why did the team choose PostgreSQL over MongoDB for canonical storage?",
  "detected_query_type": "decision_rationale",
  "vector_candidates_count": 4,
  "fts_candidates_count": 3,
  "structured_candidates_count": 2,
  "fused_candidates_count": 5,
  "filtered_restricted_count": 1,
  "final_context_count": 4,
  "retrieval_latency_ms": 42.8,
  "rerank_latency_ms": 5.1,
  "total_latency_ms": 47.9,
  "created_at": "2026-11-13T14:00:01Z"
}
```
