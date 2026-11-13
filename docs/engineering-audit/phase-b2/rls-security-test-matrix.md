# RLS Security Test Matrix & Verification Specification

**Platform:** The Handover (*Intelligent Project Knowledge Reconstruction & Handover Platform*)  
**Database Target:** Hosted PostgreSQL 17.11 on Supabase (`aws-1-ap-southeast-2.pooler.supabase.com:5432`)  
**Audit Phase:** Phase B2.1 Technical Reassessment  
**Date:** 2026-11-13  
**Auditor Roles:** Senior Security Engineer, QA Architect  

---

## 1. Overview & Test Objectives

This document establishes the comprehensive security test matrix required to validate the database security hardening of The Handover platform. The matrix spans 11 discrete attack scenarios across four architectural layers:
1. **External Gateway Tier:** Supabase PostgREST API probes.
2. **Database Engine Tier:** PostgreSQL Row Level Security (RLS) and Discretionary Access Control (DAC).
3. **Application Service Tier:** FastAPI RBAC, tenant resolution, and dynamic source-level ACL checks.
4. **Worker & Infrastructure Tier:** Supavisor connection pooling and background worker concurrency.

---

## 2. Comprehensive Security Test Matrix (11 Scenarios)

| Test ID | Security Scenario | Threat Vector / Failure Mode | Primary Enforcement Layer | Secondary / Backstop Layer | Test Inputs & Execution Preconditions | Expected Outcome & Assertion |
|---|---|---|---|---|---|---|
| **SEC-01** | **Cross-Organisation Access** | User belonging to Org A attempts to read or modify Org B's projects, evidence, or handovers | FastAPI `RbacService` (`resolve_organisation_context`) | PostgreSQL RLS / DB Isolation | Authenticated JWT for User A; HTTP request to `/api/v1/organisations/{org_b_id}/projects` | **HTTP 404 Not Found** (fails closed; does not disclose Org B existence) |
| **SEC-02** | **Cross-Project Access** | Member of Project 1 attempts to query items in Project 2 (within same or different Org) | FastAPI `RbacService` (`resolve_project_context`) | Dynamic SQLAlchemy `.where(project_id == ...)` | Authenticated JWT for User A (member of P1 only); GET `/api/v1/projects/{p2_id}/evidence` | **HTTP 404 Not Found** (tenant membership dependency rejects access) |
| **SEC-03** | **Unauthorized Evidence Access (Rule #2)** | Member of Project 1 attempts to read private GitHub/Jira evidence connected by another user | FastAPI `SourceAccessPolicyService` | Backend encrypted streaming download proxy | User A has project membership but no delegated source grant; GET `/api/v1/projects/{p1_id}/evidence/{ev_id}/download` | **HTTP 403 Forbidden** (source ACL pre-check fails closed; zero payload streamed) |
| **SEC-04** | **Unauthorized Knowledge Retrieval (RAG)** | Hybrid RAG query attempts to retrieve chunks derived from restricted private sources | `HybridRetrievalService` (Source ACL candidate pre-filtering) | ChromaDB project collection isolation | User queries `/api/v1/projects/{p1_id}/retrieval`; candidate chunks originate from private repo without User grant | Restricted chunks are **filtered out before LLM prompt injection**; zero citations returned |
| **SEC-05** | **Worker Processing Isolation** | Background composite worker processing jobs for Org A bleeds data/logs into Org B | `CompositeWorkerService` job lease isolation | Database transaction boundaries | Concurrently queue document extraction for Org A and sync run for Org B | Jobs process in distinct transactions; all created chunks retain explicit, immutable `project_id` |
| **SEC-06** | **API Role Direct SQL Access** | Attacker attempts direct PostgreSQL query as `anon` or `authenticated` (simulating stolen DB role) | PostgreSQL Discretionary Access Control (DAC) | PostgreSQL RLS (Default Deny) | Direct SQL connection via psycopg assuming role `anon`: `SELECT * FROM users;` | **ERROR: permission denied for schema public** (or 0 rows returned if schema USAGE granted) |
| **SEC-07** | **PostgREST Direct API Access** | External internet caller queries Supabase REST API (`/rest/v1/*`) with or without keys | Supabase PostgREST Gateway | PostgreSQL RLS (`ENABLE RLS` on all 56 tables) | Probes to `/rest/v1/users`, `/rest/v1/projects`, `/rest/v1/evidence_items` with no key, dummy key, or valid anon key | **HTTP 401 Unauthorized** (Gateway) or **HTTP 200 with `[]`** (RLS blocks all rows) |
| **SEC-08** | **Connection-Pool Context Leakage** | Pooled database connection retains state/variables across requests in Supavisor session mode | SQLAlchemy engine `pool_pre_ping=True` and transactional session scoping | Connection checkout reset | Request 1 executes query; Request 2 reuses pooled connection from different tenant | `SHOW ALL` or session variables on Request 2 show zero residual state from Request 1 |
| **SEC-09** | **Missing Tenant Context** | Request is submitted without required `organisation_id` or `project_id` path parameters | FastAPI dependency injection & Pydantic schema validation | Route pattern matching | HTTP requests with missing, malformed, or empty UUIDs (e.g. `/api/v1/projects//evidence`) | **HTTP 422 Unprocessable Entity** or **HTTP 404 Not Found** |
| **SEC-10** | **Forged Tenant Context** | User modifies request payload to assert ownership of a project they do not belong to | FastAPI `RbacService` (`require_project_permissions`) | SQLAlchemy model foreign key validation | User A submits POST `/api/v1/projects/{p1_id}/verification/cases` with payload referencing Org B | **HTTP 403 Forbidden** or **HTTP 404 Not Found**; request rejected before DB write |
| **SEC-11** | **Migration & Admin Role Compatibility** | Administrative DDL or migration scripts fail due to RLS interference or restricted grants | Role `postgres` table ownership and `BYPASSRLS` | Alembic `env.py` configuration | Execute `alembic heads`, `alembic history`, and DDL operations connecting as `postgres` | **Exit Code 0**; DDL succeeds unimpeded with zero RLS qualification interference |

---

## 3. Automated Test Harness Execution Blueprint

When security hardening is applied, these 11 scenarios will be verified using the automated test suite:

```bash
# 1. Verify Application RBAC, Tenant Isolation & Source ACLs (SEC-01 through SEC-05, SEC-09, SEC-10)
backend/.venv/Scripts/pytest.exe backend/tests/test_tenant_isolation.py -v
backend/.venv/Scripts/pytest.exe backend/tests/test_evidence_isolation.py -v
backend/.venv/Scripts/pytest.exe backend/tests/test_retrieval_security_and_api.py -v

# 2. Verify Live PostgreSQL Connectivity, Tables & Schemas (SEC-06, SEC-11)
backend/.venv/Scripts/pytest.exe backend/tests/test_live_postgres.py -v

# 3. Verify PostgREST External Gateway & RLS Blockade (SEC-07)
backend/.venv/Scripts/python.exe scratch/probe_supabase_api.py

# 4. Verify Full Platform Regression & Verification Center (All Systems)
backend/.venv/Scripts/pytest.exe backend/tests/test_verification_center.py -v
backend/.venv/Scripts/pytest.exe backend/tests/test_auth_api.py backend/tests/test_health_endpoints.py -v
```
