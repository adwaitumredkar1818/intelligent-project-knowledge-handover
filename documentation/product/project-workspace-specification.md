# The Handover — Project Workspace Specification

## 1. Module Overview & Responsibilities
The **Project Workspace** is the foundational container for managing project context, team participation, handover participant configuration, and the high-level dashboard. It encompasses:
- Multi-tenant organization scoping and project isolation.
- Project metadata, slug resolution, visibility controls, and lifecycle states.
- Team member roster, project roles, and responsibility descriptions.
- Transition participant configuration (departing knowledge owner and incoming successor).
- High-performance, grouped dashboard data aggregation.
- Chronological project activity feeds.

---

## 2. Information Architecture & Navigation
In accordance with the product layout, the Project Workspace powers three primary views under the `WORKSPACE` sidebar group:
1. `WORKSPACE > Overview`: The main project dashboard.
2. `WORKSPACE > Projects`: The project catalog and creation wizard.
3. `WORKSPACE > Team Members`: Team member roster, roles, and transition participant configuration.

---

## 3. Data Models & Entity Schema

### 3.1 Project Entity (`projects`)
- `id` (UUID, Primary Key)
- `organisation_id` (UUID, Foreign Key -> `organisations.id`, CASCADE)
- `name` (VARCHAR(200), Non-Null)
- `slug` (VARCHAR(120), Non-Null, unique within organization)
- `description` (TEXT, Nullable)
- `status` (VARCHAR(32), Enum: `planning`, `active`, `on_hold`, `completed`, `archived`)
- `visibility` (VARCHAR(32), Enum: `private`, `organisation`)
- `created_by_id` (UUID, Foreign Key -> `users.id`)
- `owner_id` (UUID, Foreign Key -> `users.id`)
- `start_date` (DATE, Nullable)
- `target_completion_date` (DATE, Nullable)
- `created_at` (TIMESTAMPTZ)
- `updated_at` (TIMESTAMPTZ)
- `archived_at` (TIMESTAMPTZ, Nullable)

### 3.2 Project Membership Entity (`project_memberships`)
- `id` (UUID, Primary Key)
- `project_id` (UUID, Foreign Key -> `projects.id`, CASCADE)
- `user_id` (UUID, Foreign Key -> `users.id`, CASCADE)
- `role_id` (UUID, Foreign Key -> `roles.id`)
- `status` (VARCHAR(32), Enum: `active`, `removed`)
- `responsibility_description` (TEXT, Nullable — primary area of responsibility)
- `assigned_by_id` (UUID, Foreign Key -> `users.id`, Nullable)
- `joined_at` (TIMESTAMPTZ)
- `created_at` (TIMESTAMPTZ)
- `updated_at` (TIMESTAMPTZ)

### 3.3 Project Transition Configuration (`project_transitions`)
- `id` (UUID, Primary Key)
- `project_id` (UUID, Foreign Key -> `projects.id`, CASCADE, Unique)
- `departing_user_id` (UUID, Foreign Key -> `users.id`, Non-Null)
- `successor_user_id` (UUID, Foreign Key -> `users.id`, Non-Null)
- `workflow_stage` (VARCHAR(64), Default `planning`, e.g., `planning`, `ingestion`, `reconstruction`, `verification`, `review`, `handover_ready`, `completed`)
- `handover_scope` (TEXT, Nullable — narrative definition of deliverables)
- `source_scope` (JSONB, Nullable — array of selected repository/project identifiers)
- `capture_start_date` (DATE, Nullable)
- `capture_end_date` (DATE, Nullable)
- `context_notes` (TEXT, Nullable)
- `created_at` (TIMESTAMPTZ)
- `updated_at` (TIMESTAMPTZ)

---

## 4. API Endpoints Specification

### 4.1 Project Management
- `POST /api/v1/organisations/{organisation_id}/projects`: Create a project workspace.
- `GET /api/v1/organisations/{organisation_id}/projects`: List permitted projects in an organization (search, status filter, pagination).
- `GET /api/v1/projects/{project_id}`: Get project details and user's resolved permissions.
- `PATCH /api/v1/projects/{project_id}`: Update project metadata, status, or owner.
- `POST /api/v1/projects/{project_id}/archive`: Soft-archive a project workspace.

### 4.2 Team Member Management
- `GET /api/v1/projects/{project_id}/members`: List project members with roles and responsibilities.
- `POST /api/v1/projects/{project_id}/members`: Add an organization member to the project.
- `PATCH /api/v1/projects/{project_id}/members/{user_id}`: Update project member role and responsibility notes.
- `DELETE /api/v1/projects/{project_id}/members/{user_id}`: Revoke a user's project membership.

### 4.3 Transition Participant Configuration
- `GET /api/v1/projects/{project_id}/transition`: Retrieve transition configuration, departing member, successor, stage, and capture dates.
- `PUT /api/v1/projects/{project_id}/transition`: Upsert transition configuration. Enforces that departing user != successor, both belong to the organization/project, and records an audit log.

### 4.4 Dashboard Overview Aggregation
- `GET /api/v1/projects/{project_id}/overview`: Aggregated dashboard response:
  - `project_summary`: id, name, status, owner, departing_member, successor, workflow_stage, dates.
  - `connected_sources`: total connected sources, active providers, health status, last sync timestamp.
  - `evidence_overview`: total items, count by provider (`github`, `jira`, `pdf`, `docx`), document count, processing status breakdown.
  - `knowledge_overview`: counts by category (decisions, tasks, risks, responsibilities, dependencies) with `availability: "not_implemented" | "available"`.
  - `attention_required`: list of active alerts (sync failures, extraction errors, stale sources, unverified conflicts).
  - `recent_activity`: recent 10 activity events (member additions, uploads, sync runs).
  - `team_ownership`: list of team members with configured responsibility descriptions.

### 4.5 Activity Feed
- `GET /api/v1/projects/{project_id}/activity`: Paginated chronological event feed derived from `audit_logs` and source sync jobs.
