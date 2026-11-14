# Performance Architecture — The Handover Platform

## 1. Overview & Architectural Principles

The Handover platform's performance architecture provides high throughput, low latency, and deterministic memory limits while strictly preserving data integrity, authorization boundaries, and canonical storage rules.

```
+-----------------------------------------------------------------------------------+
|                                Next.js Frontend                                   |
|   +---------------------------------------------------------------------------+   |
|   |   TanStack Query Client (staleTime: 60s, gcTime: 5m, Request Deduplication)  |   |
|   +---------------------------------------------------------------------------+   |
+------------------------------------------+----------------------------------------+
                                           | HTTP / REST
                                           v
+-----------------------------------------------------------------------------------+
|                                FastAPI Backend                                    |
|   +---------------------------------------------------------------------------+   |
|   |                       Multi-Layer Caching Layer                           |   |
|   |    - Redis Connection Pool (redis:7.2-alpine, 256MB LRU, Fail-Open)       |   |
|   |    - Strict Tenant & RBAC Namespaced Cache Keys (SHA-256 digested)        |   |
|   |    - Instant Invalidation on Membership & Evidence Mutations              |   |
|   +---------------------+-------------------------------+---------------------+   |
|                         |                               |                         |
|                         v                               v                         |
|   +----------------------------+   +----------------------------+   +-------------+
|   |   PostgreSQL 16 (Canonical)|   |   ChromaDB (HTTP Vectors)  |   | Ollama Run  |
|   |   - Psycopg 3 Pool         |   |   - Project-Isolated Clust |   | nomic-embed |
|   |   - Tsvector Full-Text     |   |   - SHA-256 Vector Cache   |   | glm-ocr:lat |
|   +----------------------------+   +----------------------------+   +-------------+
+-----------------------------------------------------------------------------------+
```

### Core Architecture Tenants:
1. **PostgreSQL Is Authoritative**: PostgreSQL is the sole system of record for all state, entity relationships, and audit trails. Redis is purely an optimization layer.
2. **Fail-Open Resilience**: If Redis becomes unavailable, the system transparently degrades to direct PostgreSQL and Ollama execution with zero request interruption or error surfacing.
3. **No Cross-Tenant / Cross-User Leakage**: Cache keys incorporate both `project_id` and `user_id` wherever permissions, source access lists (ACLs), or role scopes apply.
4. **Deterministic Local Execution**: Works seamlessly in local Windows environments with local Ollama, Dockerized Redis, ChromaDB, and PostgreSQL.

---

## 2. Multi-Layer Caching Topology

| Layer | Technology | TTL Policy | Invalidation Trigger |
| :--- | :--- | :--- | :--- |
| **Frontend UI** | TanStack Query (`@tanstack/react-query`) | 60 seconds | Route navigation, mutation invalidation |
| **API Dashboard** | Redis Key `dash:overview:proj:{id}:user:{uid}` | 30 seconds | Project membership changes, new evidence |
| **RBAC Permissions** | Redis Key `rbac:perm:proj:{id}:user:{uid}` | 60 seconds | Role updates, membership revocation |
| **Search Queries** | Redis Key `search:proj:{id}:user:{uid}:q:{hash}`| 45 seconds | Project re-indexing, evidence addition |
| **Chunk Embeddings** | Redis Key `emb:chash:{hash}:m:{model}:d:{dim}` | 30 days | Immutable (keyed by text content hash) |
| **OCR Pages** | Redis Key `ocr:chash:{hash}:p:{page}:eng:{eng}` | 30 days | Immutable (keyed by image content hash) |

---

## 3. Observability & Memory Management

The platform exposes an internal lightweight metrics endpoint at `/api/v1/metrics`:
- **Process RSS Memory**: Real-time memory consumption measured via `psutil`.
- **Cache Hit / Miss Ratio**: Dynamic hit/miss counting and operation latency tracking.
- **Redis Connection Status**: Live server connectivity and memory utilization.
