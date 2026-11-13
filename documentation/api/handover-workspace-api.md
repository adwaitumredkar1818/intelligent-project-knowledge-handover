# Handover Workspace — REST API Reference

**Platform**: The Handover  
**Base Path**: `/api/v1/projects/{project_id}/handover`  
**Authentication**: HTTP Bearer (FastAPI-managed JWT access token)  
**Date**: 2026-11-13  

---

## Endpoint Catalog

| Method | Endpoint | Required Permission | Description |
| :--- | :--- | :--- | :--- |
| `GET` | `/cases` | `handover.read` | List handover cases with pagination and filters |
| `POST` | `/cases` | `handover.create` | Create a new handover case |
| `GET` | `/cases/{case_id}` | `handover.read` | Get comprehensive case details |
| `PATCH` | `/cases/{case_id}` | `handover.edit` | Update case metadata |
| `POST` | `/cases/{case_id}/assemble` | `handover.compile` | Assemble a new immutable package version |
| `GET` | `/cases/{case_id}/versions` | `handover.read` | List all package versions for a case |
| `GET` | `/cases/{case_id}/versions/{version_id}` | `handover.read` | Get version details, sections, and links |
| `POST` | `/cases/{case_id}/readiness` | `handover.readiness.assess` | Run 9-category readiness evaluation |
| `GET` | `/cases/{case_id}/readiness/{version_id}` | `handover.read` | Get latest readiness assessment summary |
| `POST` | `/cases/{case_id}/checklists/generate` | `handover.edit` | Generate transition checklists |
| `GET` | `/cases/{case_id}/checklists` | `handover.read` | List checklists and items for a case |
| `PATCH` | `/checklists/items/{item_id}` | `handover.edit` | Update checklist item completion status |
| `POST` | `/cases/{case_id}/responsibilities` | `handover.edit` | Define responsibility transfer mappings |
| `GET` | `/cases/{case_id}/responsibilities` | `handover.read` | List mapped responsibilities |
| `PATCH` | `/responsibilities/{transfer_id}` | `handover.edit` | Update responsibility transfer status |
| `POST` | `/cases/{case_id}/signoffs` | `handover.review` | Submit human sign-off (Phase 1, 2, or 3) |
| `GET` | `/cases/{case_id}/signoffs` | `handover.read` | List sign-offs recorded for a case |
| `POST` | `/cases/{case_id}/deliver` | `handover.deliver` | Deliver approved package to successors |
| `POST` | `/deliveries/{delivery_id}/acknowledge` | `handover.acknowledge` | Successor receipt acknowledgement |
| `POST` | `/cases/{case_id}/transfer-ownership` | `handover.transfer` | Execute explicit project ownership transfer |
| `POST` | `/ownership-transfers/{transfer_id}/rollback` | `handover.admin` | Rollback an ownership transfer |
| `POST` | `/cases/{case_id}/narrative/draft` | `handover.edit` | Draft AI narrative for a section |
| `PATCH` | `/sections/{section_id}` | `handover.edit` | Edit section content and summary |
| `GET` | `/eligibility/{target_type}/{target_id}` | `handover.read` | Pre-check downstream handover eligibility |

---

## Detailed Payload Specifications

### 1. Create Case: `POST /cases`
**Request Body**:
```json
{
  "title": "Backend Engineering Lead Handover",
  "description": "Knowledge transfer from departing lead engineer to successor.",
  "departing_member_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
  "successor_id": "7ca85f64-5717-4562-b3fc-2c963f66afb7",
  "metadata_json": {}
}
```
**Response (201 Created)**:
```json
{
  "id": "e0e89849-d7ee-45df-bb78-756ef2ca8d07",
  "organisation_id": "9caf2764-9ef8-4ac1-897e-579c9a271807",
  "project_id": "a1b2c3d4-e5f6-7a8b-9c0d-1e2f3a4b5c6d",
  "title": "Backend Engineering Lead Handover",
  "description": "Knowledge transfer from departing lead engineer to successor.",
  "status": "draft",
  "departing_member_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
  "successor_id": "7ca85f64-5717-4562-b3fc-2c963f66afb7",
  "created_by_user_id": "1fa85f64-5717-4562-b3fc-2c963f66afa1",
  "metadata_json": {},
  "created_at": "2026-11-13T17:30:00Z",
  "updated_at": "2026-11-13T17:30:00Z"
}
```

### 2. Assemble Package: `POST /cases/{case_id}/assemble`
**Request Body**:
```json
{
  "assembly_notes": "Initial milestone compilation of verified Q4 architectural decisions.",
  "include_domains": null,
  "exclude_knowledge_item_ids": null,
  "exclude_relationship_ids": null
}
```
**Response (201 Created)**:
```json
{
  "id": "f5e89849-d7ee-45df-bb78-756ef2ca8d08",
  "package_id": "b2e89849-d7ee-45df-bb78-756ef2ca8d09",
  "version_number": 1,
  "assembly_notes": "Initial milestone compilation of verified Q4 architectural decisions.",
  "is_current": true,
  "created_at": "2026-11-13T17:35:00Z"
}
```

### 3. Submit Sign-Off: `POST /cases/{case_id}/signoffs`
**Request Body**:
```json
{
  "version_id": "f5e89849-d7ee-45df-bb78-756ef2ca8d08",
  "signoff_type": "reviewer_approval",
  "decision": "approved",
  "comments": "All 8 domains reviewed; verified architectural decisions backed by source PRs."
}
```
**Response (201 Created)**:
```json
{
  "id": "a9e89849-d7ee-45df-bb78-756ef2ca8d10",
  "case_id": "e0e89849-d7ee-45df-bb78-756ef2ca8d07",
  "version_id": "f5e89849-d7ee-45df-bb78-756ef2ca8d08",
  "signoff_type": "reviewer_approval",
  "signer_user_id": "1fa85f64-5717-4562-b3fc-2c963f66afa1",
  "decision": "approved",
  "comments": "All 8 domains reviewed; verified architectural decisions backed by source PRs.",
  "signed_at": "2026-11-13T17:40:00Z",
  "created_at": "2026-11-13T17:40:00Z"
}
```
