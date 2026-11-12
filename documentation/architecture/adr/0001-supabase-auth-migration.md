# ADR 0001: Supabase Auth Evaluation & Retention of FastAPI-Managed Auth

## Status
Superseded (FastAPI-Managed Authentication Retained as Canonical in Phase 2.9)

## Context
During an intermediate prototype iteration, Supabase Auth was proposed to replace the platform's custom FastAPI-managed authentication authority. Upon architectural review prior to Phase 2.9 storage integration, adopting an external asymmetric JWT authority introduced dual-identity drift, risked bypassing PostgreSQL `RefreshSession` family revocation, and was rejected in favor of keeping platform identity strictly self-contained inside FastAPI and PostgreSQL.

## Decision (Current Canonical Architecture — Phase 2.9)
1. **FastAPI-Managed Platform Identity**: User registration (`/api/v1/auth/register`), login (`/api/v1/auth/login`), refresh rotation (`/api/v1/auth/refresh`), logout (`/api/v1/auth/logout`), and profile/session management remain exclusively managed by FastAPI using Argon2id password hashes (`pwdlib[argon2]`), short-lived HS256 JWT access tokens (`JWT_SECRET_KEY`), and SHA-256 `RefreshSession` tokens in `HttpOnly` cookies.
2. **Strict Non-Empty Password Hash Enforcement**: All FastAPI-created users require a non-empty `password_hash`, and `/api/v1/auth/login` safely rejects legacy rows with `password_hash IS NULL` without throwing 500 errors (`401 INVALID_CREDENTIALS`).
3. **No External Auth JWT Interception**: `get_current_principal()` rejects non-FastAPI tokens (`401 INVALID_ACCESS_TOKEN`) and never auto-provisions users from third-party JWT claims.
4. **PostgreSQL RBAC Authority**: Roles, permissions, organisation memberships, and project memberships remain evaluated exclusively in PostgreSQL.
5. **Zero-Migration Schema Compatibility**: The nullable `users.supabase_auth_id` column introduced in Alembic revision `0009_supabase_and_vector_indexes` is left intact as dormant schema to avoid mutating the live PostgreSQL database.

## Consequences
- No `@supabase/supabase-js`, `SUPABASE_JWKS_URL`, or `NEXT_PUBLIC_SUPABASE_*` variables exist in the codebase.
- Platform authentication stays completely independent of Supabase Storage connectivity (`STORAGE_PROVIDER`) and third-party source OAuth 2.0 integrations (GitHub, Jira).
