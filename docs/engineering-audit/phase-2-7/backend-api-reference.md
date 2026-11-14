# Phase 2.7 Audit: Backend API Reference

**Document**: `docs/engineering-audit/phase-2-7/backend-api-reference.md`  
**Phase**: 2.7 — Complete Knowledge Intelligence Engine  
**Module**: Module I — Backend API Endpoints  
**Status**: APPROVED & VERIFIED  

---

## 1. Executive Summary

This document catalogues the complete set of REST API endpoints implemented and verified for Phase 2.7 Knowledge Intelligence. The endpoints are housed across two routers:
1. `backend/app/api/v1/endpoints/relationships.py` (Graph, Traceability, Dependencies, Timeline, Identity Resolution)
2. `backend/app/api/v1/endpoints/knowledge_intelligence.py` (Knowledge Summaries, Domains, Reconstructed Findings)

All endpoints enforce JWT Bearer authentication, PostgreSQL project RBAC, and pre-retrieval source ACL filtering.

---

## 2. Relationships & Graph Intelligence Endpoints

| Method | Path | Description | Access / RBAC |
| :--- | :--- | :--- | :--- |
| `GET` | `/api/v1/projects/{project_id}/relationships/graph` | Returns nodes and edges filtered by entity types, depth, and confidence | Project Member |
| `GET` | `/api/v1/projects/{project_id}/relationships/entities` | Paginated search of entities with filter by type and status | Project Member |
| `GET` | `/api/v1/projects/{project_id}/relationships/entities/{entity_id}` | Detailed entity inspection with adjacent edges and evidence | Project Member |
| `GET` | `/api/v1/projects/{project_id}/relationships/traceability` | 5-stage decision-to-implementation chains with missing links | Project Member |
| `GET` | `/api/v1/projects/{project_id}/relationships/dependencies` | Directed dependency graph, cycle detection list, and root blockers | Project Member |
| `GET` | `/api/v1/projects/{project_id}/relationships/timeline` | Chronological event stream with occurrence timestamp resolution | Project Member |
| `GET` | `/api/v1/projects/{project_id}/identity-resolution/candidates` | Candidate entity merge pairs requiring human review | Project Member |
| `POST`| `/api/v1/projects/{project_id}/identity-resolution/review` | Accept or reject an identity merge candidate | Project Admin / Lead |

---

## 3. Knowledge Intelligence Endpoints

| Method | Path | Description | Access / RBAC |
| :--- | :--- | :--- | :--- |
| `GET` | `/api/v1/projects/{project_id}/knowledge-intelligence/summary` | High-level summary of findings, domains, and verification metrics | Project Member |
| `GET` | `/api/v1/projects/{project_id}/knowledge-intelligence/domains` | Reconstructed metrics partitioned across all 8 canonical domains | Project Member |
| `GET` | `/api/v1/projects/{project_id}/knowledge-intelligence/findings` | Paginated list of reconstructed knowledge findings with source citations | Project Member |
| `GET` | `/api/v1/projects/{project_id}/knowledge-intelligence/findings/{id}` | Deep dive inspection of an individual finding with raw evidence | Project Member |
| `POST`| `/api/v1/projects/{project_id}/knowledge-intelligence/findings/{id}/verify` | Human review verification action (verify, reject, flag conflict) | Project Member |

---

## 4. Error Handling & Status Codes

- `200 OK`: Successful retrieval or update.
- `400 Bad Request`: Invalid parameters or invalid entity IDs.
- `401 Unauthorized`: Missing or expired JWT token.
- `403 Forbidden`: User lacks project membership or requested entity is restricted by source ACL.
- `404 Not Found`: Project, entity, or finding does not exist.
- `422 Unprocessable Entity`: Request payload schema validation failure.
