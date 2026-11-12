# The Handover — Backend Domain Boundaries

## 1. Modular Separation Architecture

The Handover backend adheres to strict separation of concerns across 11 architectural domains:

```text
backend/app/
├── api/                  # 1. API routes & dependency injection
├── core/                 # 2. Config, Security, RBAC catalog, Middleware, Exceptions
├── db/                   # 3. SQLAlchemy session & engine lifecycle
├── models/               # 4. Canonical ORM entity definitions
├── schemas/              # 5. Pydantic v2 validation contracts
├── repositories/         # 6. Database query abstractions & persistence
└── services/             # 7. Business logic & domain orchestration
```

---

## 2. Eleven Canonical Sub-Domains

| Domain Module | Primary Responsibilities | Boundaries & Constraints |
| :--- | :--- | :--- |
| **1. Authentication & Identity** | Registration, login, password hashing, JWT creation, HttpOnly refresh cookies, token rotation, session revocation. | Never touches business logic of projects or evidence. Strictly manages user identity. |
| **2. RBAC & Authorization** | Platform, Organization, and Project permission catalogs, role assignments, context resolution dependencies. | Enforced in `deps.py` and service layers before entity queries execute. |
| **3. Organisation Domain** | Multi-tenant tenant boundaries, organization lifecycle, organization membership, invitations. | Owns the root tenant container for all projects. |
| **4. Project Workspace Domain** | Project creation, configuration, status, member rosters, transition participants, dashboard overview aggregation. | Scoped strictly inside an organization. Does not directly handle document parsing. |
| **5. Source Integrations** | GitHub, Jira, and Slack connectors, OAuth flow, token encryption, resource discovery. | Handles upstream API communication; isolates network failures from core application state. |
| **6. Document Ingestion** | File validation, SHA-256 deduplication, encrypted disk storage, PyMuPDF parsing, GLM OCR. | Does not make business decisions on project status. Produces raw text and page chunks. |
| **7. Evidence Management** | Canonical evidence library, details view, filtering, provenance preservation, source ACL enforcement. | Sole authoritative gateway for reading and querying project evidence. |
| **8. Background Processing** | Asynchronous job claiming, execution, retry tracking, lease expiration, model inference locking. | Lightweight Python worker backed by PostgreSQL; no Redis/Celery dependency. |
| **9. Embedding & Retrieval** | Hybrid retrieval combining PostgreSQL full-text search and ChromaDB vector search (`nomic-embed-text`). | Secondary retrieval index; fully rebuildable from PostgreSQL evidence records. |
| **10. Audit Logging** | Immutable audit records for authentication, member changes, source mapping, and access denials. | Write-only audit log; records actor, target, outcome, IP address, and correlation ID. |
| **11. System Health & Probes** | Liveness, readiness, PostgreSQL ping, Ollama status, ChromaDB status. | Read-only infrastructure diagnostics. |
