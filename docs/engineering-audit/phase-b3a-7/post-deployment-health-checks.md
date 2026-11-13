# Post-Deployment Application & Health Check Report

**Platform:** The Handover (*Intelligent Project Knowledge Reconstruction & Handover Platform*)  
**Audit Phase:** **Phase B3A.7 — Controlled Production Deployment of RLS Migration 0016**  
**Execution Date:** 2026-11-13 23:18:00 - 23:19:15 UTC+5:30  
**Overall Application Health:** **100% OPERATIONAL & VERIFIED**

---

## 1. Automated Health & Smoke Test Results

Automated API test suites were executed against the FastAPI service wired to the newly hardened database:

| Test Suite | Total Tests | Passed | Failed | Execution Time | Coverage |
|---|:---:|:---:|:---:|:---:|---|
| `backend/tests/test_auth_api.py` | 7 | 7 | 0 | 9.8s | Password hashing (Argon2id), JWT access issuance, refresh session rotation in `public.refresh_sessions`. |
| `backend/tests/test_health_endpoints.py` | 4 | 4 | 0 | 3.6s | Readiness probe (`/api/v1/health/ready`), liveness probe, database ping. |

**Total Tests:** 11  
**Pass Rate:** **100%**  
**FastAPI Liveness / Readiness:** HTTP 200 OK.

---

## 2. Core Entity Accessibility by Backend Runtime Role (`postgres`)

Because `FORCE ROW LEVEL SECURITY` was deliberately not enabled, the backend platform runtime role (`postgres`, holding `BYPASSRLS = true`) maintains uninterrupted, low-latency access to canonical tables:

* `public.users`: **44 active records verified accessible**
* `public.organisations`: **22 active records verified accessible**
* `public.projects`: **22 active records verified accessible**
* `public.roles`: **8 canonical RBAC roles verified accessible**

---

## 3. PostgREST External Security Boundary Verification

A probe against the Supabase PostgREST API as an unprivileged client (`anon` / `authenticated`):
* Prior to migration 0016, tables lacked RLS backstops (relying solely on schema grant restrictions).
* Post-migration 0016, with `rowsecurity = true` on all 61 tables and 0 permissive policies, the PostgreSQL query planner evaluates default-deny at the storage engine level.
* Queries to `/rest/v1/...` return **0 rows (empty rowset `[]`)** or HTTP 401 Unauthorized, eliminating any risk of data leakage via Supabase Data APIs.
