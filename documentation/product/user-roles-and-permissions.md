# The Handover — User Roles and Permissions

## 1. Scope-Separated RBAC Architecture

The Handover implements a three-tier scope-separated Role-Based Access Control model:

```text
┌────────────────────────────────────────────────────────┐
│                    PLATFORM SCOPE                      │
│   Roles: platform_admin, standard_user                 │
├────────────────────────────────────────────────────────┤
│                  ORGANISATION SCOPE                    │
│   Roles: org_owner, org_admin, org_member              │
├────────────────────────────────────────────────────────┤
│                    PROJECT SCOPE                       │
│   Roles: project_manager, project_member, reviewer     │
└────────────────────────────────────────────────────────┘
```

---

## 2. Platform Roles
- **`platform_admin`**: Full platform authority. Can inspect all tenant organizations, manage platform users, configure system-wide settings, and view system-level audit logs.
- **`standard_user`**: Baseline platform account. Granted upon verified registration. Can authenticate, manage their own profile, create organizations, or accept organization invitations.

---

## 3. Organisation Roles
- **`org_owner`**: Creator or primary authority of an Organization. Can update organization profile, configure organization billing/settings, invite members, promote/demote admins, delete or archive the organization, and access all member projects.
- **`org_admin`**: Administrative delegate within an Organization. Can manage organization members, create projects, manage project memberships, and configure global source integrations.
- **`org_member`**: Standard member of an Organization. Can be assigned to individual projects. Cannot create projects unless granted explicit `project.create` permission.

---

## 4. Project Roles
- **`project_manager`**: Oversees project execution and handover configuration.
  - Can configure project settings and lifecycle status.
  - Can assign project members and project roles.
  - Can configure Transition Participants (departing member & successor).
  - Can map connected sources (GitHub repositories, Jira projects) to the project.
  - Can initiate and monitor source synchronisation and file uploads.
  - Can view all project evidence and overview dashboard metrics.
- **`reviewer`**: Technical lead or subject matter expert.
  - Can inspect candidate findings and evidence.
  - Can resolve contradictory evidence and mark findings as verified.
  - Has authority to approve or reject final handover packages.
- **`project_member`**: Team participant (including departing members and incoming successors).
  - Can view permitted project evidence and verified knowledge.
  - Can upload project documents.
  - Can interact with the Project Knowledge Assistant within their permission scope.

---

## 5. Permissions Catalog

| Permission Code | Scope | Description |
| :--- | :--- | :--- |
| `user.read` | Platform | View platform user profiles |
| `user.manage` | Platform | Modify user status, lock accounts |
| `role.read` | Platform | Read platform roles and permissions catalog |
| `role.manage` | Platform | Assign or modify user platform roles |
| `organisation.create` | Platform | Create new multi-tenant organizations |
| `organisation.read` | Organisation | View organization details and member roster |
| `organisation.manage` | Organisation | Update organization profile and lifecycle status |
| `organisation.members.manage` | Organisation | Invite, update, or remove organization members |
| `project.create` | Organisation | Create new project workspaces inside the org |
| `project.read` | Project | View project details, members, and dashboard overview |
| `project.manage` | Project | Edit project metadata, visibility, status, or archive |
| `project.members.read` | Project | View assigned project team members and roles |
| `project.members.manage` | Project | Assign, update, or remove project members |
| `project.transition.manage` | Project | Configure departing member, successor, and capture scope |
| `evidence.read` | Project | Search, filter, and view permitted project evidence |
| `evidence.upload` | Project | Upload PDF and DOCX documents to the project |
| `evidence.manage` | Project | Delete or reprocess project evidence |
| `source.connect` | Project | Connect external GitHub/Jira accounts and map resources |
| `source.sync` | Project | Trigger manual or incremental sync jobs |
| `handover.review` | Project | Verify findings, resolve conflicts, approve handovers |

---

## 6. Critical Security Boundary: Project Membership != Source Access

A fundamental architectural requirement of The Handover is the explicit separation of Project Membership from External Source Access:
1. **Delegated Source Credentials**: When a user (e.g., Alex) connects their GitHub or Jira account and maps a repository/project to The Handover, the system records Alex's OAuth credential and access scope.
2. **Read-Time Access Control**: When another project member (e.g., Daniel) attempts to view an evidence item originating from a private GitHub repository, the backend re-verifies Daniel's personal access to that specific source.
3. **Fail-Closed Policy**: If Daniel's credentials cannot be verified or Daniel lacks access to that private repository, the backend rejects the request with HTTP 403 Forbidden.
4. **Zero Metadata Leaks**: Evidence search and count aggregations exclude records for which the requesting user lacks source access, preventing information disclosure through record counts or snippet previews.
