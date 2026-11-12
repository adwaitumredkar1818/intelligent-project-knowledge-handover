# The Handover — Frontend Integration Contract

## 1. Overview
This document defines the stable HTTP API contract, request schemas, response shapes, and controlled status codes consumed by the future Next.js frontend application.

- **Base URL**: `http://localhost:8000/api/v1` (configured via `NEXT_PUBLIC_API_BASE_URL`)
- **Authentication**: Bearer JWT in `Authorization: Bearer <token>` header, plus HttpOnly session cookie for token refresh.
- **Correlation ID**: Frontend passes `X-Request-ID` or receives a server-generated UUID in response headers.
- **Error Format**: Canonical `ErrorResponse` schema with HTTP status, machine-readable code, user-friendly message, and optional details list.

---

## 2. Global Navigation Contracts

### 2.1 Current User & Tenant Context
- `GET /api/v1/auth/me`: Returns authenticated user profile and platform roles.
- `GET /api/v1/organisations`: Returns organizations where the user is an active member.
- `GET /api/v1/organisations/{organisation_id}/projects`: Returns projects visible to the user for the top-bar project selector.

---

## 3. Project Workspace API Contracts

### 3.1 Project Details & Context
- `GET /api/v1/projects/{project_id}`
```json
{
  "id": "123e4567-e89b-12d3-a456-426614174000",
  "organisation_id": "123e4567-e89b-12d3-a456-426614174001",
  "name": "Platform Modernization",
  "slug": "platform-modernization",
  "description": "Core architecture transition",
  "status": "active",
  "visibility": "organisation",
  "owner_id": "123e4567-e89b-12d3-a456-426614174002",
  "created_by_id": "123e4567-e89b-12d3-a456-426614174002",
  "start_date": "2026-01-01",
  "target_completion_date": "2026-06-30",
  "created_at": "2026-01-01T00:00:00Z",
  "updated_at": "2026-01-01T00:00:00Z",
  "archived_at": null,
  "caller_permissions": [
    "project.read",
    "project.manage",
    "evidence.read",
    "evidence.upload"
  ]
}
```

### 3.2 Dashboard Overview Aggregation
- `GET /api/v1/projects/{project_id}/overview`
```json
{
  "project_summary": {
    "project_id": "123e4567-e89b-12d3-a456-426614174000",
    "name": "Platform Modernization",
    "status": "active",
    "workflow_stage": "ingestion",
    "owner": { "id": "uuid", "full_name": "Michael Brown", "email": "michael@example.com" },
    "departing_member": { "id": "uuid", "full_name": "Alex Chen", "email": "alex@example.com" },
    "successor": { "id": "uuid", "full_name": "Daniel Taylor", "email": "daniel@example.com" },
    "start_date": "2026-01-01",
    "target_completion_date": "2026-06-30"
  },
  "connected_sources": {
    "total_sources": 3,
    "active_providers": ["github", "pdf", "docx"],
    "health_status": "healthy",
    "last_synced_at": "2026-11-12T10:00:00Z"
  },
  "evidence_overview": {
    "total_records": 142,
    "by_provider": {
      "github": 85,
      "jira": 0,
      "pdf": 42,
      "docx": 15
    },
    "by_status": {
      "extracted": 138,
      "processing": 2,
      "failed": 2
    },
    "document_count": 5
  },
  "knowledge_overview": {
    "decisions_count": 0,
    "tasks_count": 0,
    "risks_count": 0,
    "responsibilities_count": 0,
    "dependencies_count": 0,
    "availability": "not_implemented"
  },
  "attention_required": [
    {
      "id": "alert-1",
      "type": "processing_failure",
      "message": "Failed to extract text from scan-notes.pdf: invalid page header",
      "resource_id": "123e4567-e89b-12d3-a456-426614174099"
    }
  ],
  "recent_activity": [
    {
      "id": "act-1",
      "event_type": "evidence_uploaded",
      "description": "Alex Chen uploaded Architecture_v2.pdf",
      "timestamp": "2026-11-12T09:45:00Z"
    }
  ],
  "team_ownership": [
    {
      "user_id": "uuid",
      "full_name": "Alex Chen",
      "role": "project_member",
      "responsibility_description": "Lead architect for auth and backend storage"
    }
  ]
}
```

---

## 4. Evidence Workspace API Contracts

### 4.1 Connected Sources (Panel A)
- `GET /api/v1/projects/{project_id}/sources`
```json
{
  "sources": [
    {
      "mapping_id": "123e4567-e89b-12d3-a456-426614174010",
      "provider": "github",
      "account_identifier": "alexchen",
      "resource_name": "alexchen/platform-core",
      "sync_status": "completed",
      "last_synced_at": "2026-11-12T10:00:00Z",
      "sync_error": null,
      "is_active": true
    },
    {
      "mapping_id": "123e4567-e89b-12d3-a456-426614174011",
      "provider": "jira",
      "account_identifier": "alex@example.com",
      "resource_name": "Jira: PMOD",
      "sync_status": "idle",
      "last_synced_at": null,
      "sync_error": null,
      "is_active": false
    }
  ],
  "document_summary": {
    "total_documents": 5,
    "pdf_count": 3,
    "docx_count": 2,
    "last_upload_at": "2026-11-12T09:45:00Z"
  }
}
```

### 4.2 Evidence Library (Panel B)
- `GET /api/v1/projects/{project_id}/evidence?limit=20&offset=0&provider=github`
```json
{
  "total": 85,
  "limit": 20,
  "offset": 0,
  "items": [
    {
      "id": "123e4567-e89b-12d3-a456-426614174050",
      "title": "PR #42: Implement Argon2id password hashing",
      "provider": "github",
      "record_type": "pull_request",
      "author": "alexchen",
      "source_url": "https://github.com/org/repo/pull/42",
      "source_created_at": "2026-10-15T14:30:00Z",
      "ingested_at": "2026-11-12T10:00:00Z",
      "processing_status": "extracted",
      "verification_status": "unverified"
    }
  ]
}
```

### 4.3 Evidence Details (Panel C)
- `GET /api/v1/evidence/{evidence_id}`
```json
{
  "id": "123e4567-e89b-12d3-a456-426614174050",
  "project_id": "123e4567-e89b-12d3-a456-426614174000",
  "title": "PR #42: Implement Argon2id password hashing",
  "provider": "github",
  "record_type": "pull_request",
  "external_source_id": "pr:42",
  "source_url": "https://github.com/org/repo/pull/42",
  "author": "alexchen",
  "source_created_at": "2026-10-15T14:30:00Z",
  "source_updated_at": "2026-10-16T09:15:00Z",
  "ingested_at": "2026-11-12T10:00:00Z",
  "processing_status": "extracted",
  "verification_status": "unverified",
  "content_hash": "a1b2c3d4e5...",
  "document_file": null,
  "extracted_chunks": [
    {
      "chunk_index": 0,
      "page_number": null,
      "section_heading": "Description",
      "content_text": "Replaced PBKDF2 with Argon2id for password hashing in accordance with security guidance...",
      "indexing_status": "indexed"
    }
  ],
  "raw_metadata": {
    "pr_number": 42,
    "merged": true,
    "merge_commit_sha": "abc12345"
  }
}
```
