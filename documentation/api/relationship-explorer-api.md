# The Handover — Relationship Explorer REST API Reference

**Base Path**: `/api/v1/projects/{project_id}/relationships`  
**Authentication**: Platform Bearer JWT Access Token  
**Authorization**: RBAC Scope Check + Read-Time Source ACL Verification  

---

## Endpoints Summary

| Method | Endpoint | Permission | Description |
| :--- | :--- | :--- | :--- |
| `GET` | `/graph` | `project.read` | React Flow formatted knowledge graph projection |
| `GET` | `/entities` | `project.read` | Paginated listing of visible entities |
| `GET` | `/entities/{entity_id}` | `project.read` | Node detail inspection with adjacent relationships |
| `GET` | `/` | `project.read` | Paginated listing of visible relationships |
| `GET` | `/traceability` | `project.read` | 5-stage decision traceability chains listing |
| `GET` | `/traceability/{decision_id}` | `project.read` | Single decision traceability chain analysis |
| `GET` | `/dependencies` | `project.read` | Directed dependency hierarchy & cycle analysis |
| `GET` | `/timeline` | `project.read` | Chronological event stream with precision metadata |
| `POST`| `/timeline` | `project.manage`| Record manual timeline event or milestone |
| `GET` | `/identities/candidates` | `project.read` | List candidate multi-source identity matches |
| `GET` | `/identities/candidates/{id}`| `project.read` | Get candidate pair detail and signal score |
| `POST`| `/identities/candidates/{id}/review` | `project.manage` | Human review: accept (merge) or reject candidate |
| `POST`| `/identities/candidates/{id}/revert` | `project.manage` | Revert accepted merge, restoring canonical status |
| `POST`| `/reconstruct` | `project.manage`| Trigger background relationship reconstruction run |
| `GET` | `/runs` | `project.read` | List historical reconstruction runs & metrics |
| `GET` | `/runs/{run_id}` | `project.read` | Get single reconstruction run telemetry |
| `GET` | `/{relationship_id}` | `project.read` | Get single relationship details and provenance |
| `GET` | `/{relationship_id}/evidence` | `project.read` | Get supporting evidence citations for an edge |
| `POST`| `/{relationship_id}/submit-for-review` | `project.manage` | Human verification decision (verify/reject/dispute) |

---

## Sample Payloads

### 1. `GET /graph`
Query Parameters:
- `center_node_id` (optional UUID)
- `depth` (integer, 1-5, default 2)
- `entity_type` (optional string filter)
- `verification_status` (optional string filter)
- `limit_nodes` (integer, default 250, max 1000)
- `limit_edges` (integer, default 500, max 2000)

Response (`200 OK`):
```json
{
  "nodes": [
    {
      "id": "e45f956d-e069-42b7-bdc1-40beeb47b2c0",
      "type": "customNode",
      "data": {
        "label": "ADR-002 GraphQL vs REST",
        "entityType": "decision",
        "sourceProvider": "document_upload",
        "verificationStatus": "verified",
        "isRootBlocker": false
      },
      "position": { "x": 0, "y": 0 }
    }
  ],
  "edges": [
    {
      "id": "d047814b-ef5c-4d56-a19d-7df462e08cf4",
      "source": "e45f956d-e069-42b7-bdc1-40beeb47b2c0",
      "target": "c928fbf1-a472-46bb-9cb8-82ab87dc67b4",
      "label": "AFFECTS_COMPONENT",
      "style": { "strokeDasharray": "0" },
      "data": {
        "relationshipType": "AFFECTS_COMPONENT",
        "basis": "explicit",
        "verificationStatus": "verified",
        "confidence": 1.0
      }
    }
  ],
  "total_nodes": 1,
  "total_edges": 1
}
```

### 2. `POST /{relationship_id}/submit-for-review`
Request Body:
```json
{
  "action": "verify",
  "note": "Confirmed by Lead Software Architect after sprint review."
}
```
Response (`200 OK`):
```json
{
  "id": "d047814b-ef5c-4d56-a19d-7df462e08cf4",
  "source_entity_id": "e45f956d-e069-42b7-bdc1-40beeb47b2c0",
  "target_entity_id": "c928fbf1-a472-46bb-9cb8-82ab87dc67b4",
  "relationship_type": "AFFECTS_COMPONENT",
  "relationship_basis": "explicit",
  "verification_status": "verified",
  "confidence_score": 1.0,
  "review_notes": "Confirmed by Lead Software Architect after sprint review."
}
```

### 3. `GET /dependencies`
Response (`200 OK`):
```json
{
  "nodes": [...],
  "edges": [...],
  "cycles_detected": false,
  "cycles": [],
  "root_blocker_ids": ["c928fbf1-a472-46bb-9cb8-82ab87dc67b4"],
  "total_dependencies": 12
}
```
