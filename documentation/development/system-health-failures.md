# System Health Failures & Remediation Log — The Handover Platform

**Product**: The Handover — Intelligent Project Knowledge Reconstruction & Handover Platform  
**Audit Date**: November 13, 2026  
**Auditor**: Antigravity System Audit Agent  
**Environment**: Local Windows 11 Development Environment

---

## 1. Executive Summary of Discovered Failures

During the comprehensive system health audit across all 35 technical sections and 27 component domains, a total of **8 specific issues** were identified, reproduced, and documented. Three of these were runtime blockers encountered in the frontend/API integration and have already been remediated during this audit turn. Five remaining issues represent code quality, typing, schema drift, or configuration deficiencies prioritized for subsequent remediation.

Zero data corruption, zero credential leaks, and zero security boundaries were breached.

---

## 2. Failure Details & Root Cause Analysis

### Issue 1: 422 Unprocessable Entity on `/api/v1/auth/register`
- **Severity**: HIGH (Registration Blocker)
- **Status**: **RESOLVED**
- **Location**: `backend/app/schemas/auth.py`, `frontend/src/lib/api.ts`, `frontend/src/components/auth/AuthModal.tsx`
- **Reproduction**:
  Attempting to register a user with password `<12` characters (e.g. `Password123!`) triggered HTTP 422 Unprocessable Entity.
- **Root Cause**:
  Backend `UserRegisterRequest` enforces strict password rules:
  1. Minimum 12 characters (`_PASSWORD_MIN_LENGTH = 12`)
  2. At least one uppercase letter
  3. At least one lowercase letter
  4. At least one digit
  5. At least one special symbol
  The frontend UI did not inform the user of these 5 requirements, and `src/lib/api.ts` was not unwrapping backend validation error arrays (`error.details`), showing only generic `"Unprocessable Entity"`.
- **Sanitized Error Log**:
  ```text
  POST /api/v1/auth/register HTTP/1.1 -> 422 Unprocessable Entity
  {"error":{"code":"VALIDATION_ERROR","message":"Request validation failed","details":[{"field":"password","message":"Password must be at least 12 characters long"}]}}
  ```
- **Remediation Implemented**:
  1. Updated `frontend/src/lib/api.ts` to parse nested Pydantic detail lists.
  2. Enhanced `AuthModal.tsx` with dynamic, real-time password requirement checklist that turns green as criteria are satisfied, plus a password visibility toggle.

---

### Issue 2: "No Active Organisation Selected" on Project Creation
- **Severity**: HIGH (Project Workspace Blocker)
- **Status**: **RESOLVED**
- **Location**: `frontend/src/components/modals/CreateProjectModal.tsx`, `frontend/src/lib/api.ts`
- **Reproduction**:
  A freshly registered user logging in and attempting to create their first project was blocked by an alert banner: `"No active organisation selected"`.
- **Root Cause**:
  In The Handover's multi-tenant architecture, projects strictly belong to an `Organisation`. A newly registered user has zero organizations. `CreateProjectModal.tsx` required `activeOrg.id` to be present before allowing creation, but lacked any UI affordance to input an organization name or create one inline. Furthermore, `api.organisations.list()` returned `{ items: [...] }` which was not automatically unwrapped by the frontend helper.
- **Sanitized UI Error**:
  ```text
  [!] No active organisation selected
  Project Name: Handover
  Description: Handing knowledge to someone
  [Create Project button disabled]
  ```
- **Remediation Implemented**:
  1. Added `unwrapList` helper in `frontend/src/lib/api.ts` to handle both raw arrays and `{ items: [...] }` envelopes.
  2. Added inline "Organisation Name" input to `CreateProjectModal.tsx` when no organization exists.
  3. Created `CreateOrganisationModal.tsx` for explicit organisation management.
  4. Added organisation switcher dropdown in `TopNav.tsx` and `Sidebar.tsx`.

---

### Issue 3: HTTP 405 Method Not Allowed on `GET /organisations/{org_id}/sources`
- **Severity**: MEDIUM (Evidence Center API Failure)
- **Status**: **RESOLVED**
- **Location**: `backend/app/api/routes/sources.py:188`
- **Reproduction**:
  Frontend calling `api.sources.listOrgConnections(orgId)` received HTTP 405 Method Not Allowed.
- **Root Cause**:
  `sources.py` only had `@router.post("/organisations/{organisation_id}/sources")` registered. The corresponding `GET` endpoint had not been registered in that route module.
- **Sanitized Error Log**:
  ```text
  INFO: 127.0.0.1:56890 - "GET /api/v1/organisations/790117a0-0937-4d7a-b922-29fcfa36e395/sources HTTP/1.1" 405 Method Not Allowed
  ApiError: Method Not Allowed at request (src/lib/api.ts:96:11)
  ```
- **Remediation Implemented**:
  Added `@router.get("/organisations/{organisation_id}/sources", response_model=SourceConnectionListResponse)` to `backend/app/api/routes/sources.py` with proper RBAC permission checks (`require_organisation_permission("sources:read")`) and database querying.

---

### Issue 4: Undefined Name `Any` in Background Worker
- **Severity**: LOW (Static Analysis Failure)
- **Status**: **OPEN** (Fix identified)
- **Location**: `backend/app/worker.py:39:26`
- **Reproduction**:
  Running `ruff check app` or `mypy app` flagged `F821 Undefined name 'Any'` at line 39.
- **Root Cause**:
  `app/worker.py` defined `def __init__(self, session_factory: Any, ...)` inside `SyncWorker`, but `from typing import Any` was not imported at the top of the module.
- **Sanitized Log**:
  ```text
  app\worker.py:39:26: F821 Undefined name `Any`
  app\worker.py:39: error: Name "Any" is not defined [name-defined]
  ```
- **Remediation Plan**:
  Add `Any` to `from typing import ...` in `backend/app/worker.py`.

---

### Issue 5: Database vs Model Alembic Schema Drift
- **Severity**: LOW (Schema Maintenance)
- **Status**: **OPEN** (Non-breaking)
- **Location**: `backend/app/models/workspace.py`, `backend/app/models/vector_index.py`
- **Reproduction**:
  Running `alembic check` revealed two discrepancies:
  1. `project_transitions.source_scope`: Database column is `JSONB`, while SQLAlchemy model is `JSON`.
  2. `project_vector_indexes`: Database index name is `ix_project_vector_indexes_org`, while SQLAlchemy model specifies `ix_project_vector_indexes_organisation_id`.
- **Sanitized Log**:
  ```text
  FAILED: Target database is not up to date with the model, 2 differences were found:
  - Table 'project_transitions', column 'source_scope': type difference JSONB vs JSON
  - Table 'project_vector_indexes': index name difference 'ix_project_vector_indexes_org' vs 'ix_project_vector_indexes_organisation_id'
  ```
- **Root Cause**:
  PostgreSQL migration `0001_initial_schema.py` used `postgresql.JSONB` for performance, but SQLAlchemy model used generic `JSON`. Index was renamed in migration `0009` without updating the model attribute.
- **Remediation Plan**:
  Update `workspace.py` to use `postgresql.JSONB` and harmonize the index name in `vector_index.py`.

---

### Issue 6: GLM OCR Trailing Repetition Tokens
- **Severity**: LOW (OCR Output Cleanliness)
- **Status**: **OPEN** (Mitigated by Guardrail)
- **Location**: `backend/app/services/ocr.py:20`
- **Reproduction**:
  During live Ollama execution of `glm-ocr:latest` on a single-page document, the OCR engine produced 7,115 characters, consisting of the correct 3 lines of text followed by repeated separator dashes (`---`).
- **Root Cause**:
  `glm-ocr` is a vision-language model that occasionally fails to emit an EOS (End Of Sequence) token when encountering empty white space on document borders, resulting in repetitive token generation until max predict tokens is reached.
- **Sanitized Log**:
  ```text
  Extracted text (7115 chars):
  THE HANDOVER KNOWLEDGE AUDIT 2026
  Confidential Verification Pipeline
  Page 1 of 1
  ---
  ---
  ```
- **Remediation Plan**:
  The existing regex guardrail `_REPETITION_LOOP_RE = re.compile(r"(.)\1{39,}")` in `ocr.py` successfully detects repetitive loops. Enhance post-processing in `extract_page_text` to automatically truncate output when repeating punctuation sequences exceed 10 repetitions.

---

### Issue 7: Frontend ESLint Type & Effect Warnings
- **Severity**: LOW (Code Hygiene)
- **Status**: **OPEN**
- **Location**: `frontend/src/context/LiveAppContext.tsx`, `frontend/src/components/modals/*`
- **Reproduction**:
  Running `npm run lint` reported 69 problems (30 errors, 39 warnings).
- **Root Cause**:
  1. TypeScript strict typing: Multiple `catch (err: any)` blocks use explicit `any` instead of `unknown`.
  2. React 19 Compiler rules: Synchronous `setState` inside `useEffect` in `LiveAppContext.tsx` and `CreateProjectModal.tsx` trigger `react-hooks/set-state-in-effect`.
- **Sanitized Log**:
  ```text
  D:\Handover\frontend\src\context\LiveAppContext.tsx:373:7: Avoid calling setState() directly within an effect react-hooks/set-state-in-effect
  D:\Handover\frontend\src\lib\api.ts:68:20: Unexpected any. Specify a different type @typescript-eslint/no-explicit-any
  ```
- **Remediation Plan**:
  1. Replace `err: any` with `err: unknown` and type-guard with `err instanceof Error ? err.message : String(err)`.
  2. Refactor state initialization to derive state or use lazy state initializers rather than synchronous `useEffect` setStates.

---

### Issue 8: Python Mypy Strict Type Incompatibilities
- **Severity**: LOW (Type Safety)
- **Status**: **OPEN**
- **Location**: `backend/app/services/supabase_storage.py`, `backend/app/services/auth.py`, `backend/app/api/deps.py`
- **Reproduction**:
  Running `mypy app` returned 12 errors across 6 files out of 108 files checked.
- **Root Cause**:
  Minor type annotations differences (e.g. `str | None` passed to `str` parameter in `verify_password`, missing parameter type annotations in `sources.py`).
- **Remediation Plan**:
  Add explicit type casts and type annotations to satisfy mypy strict mode.
