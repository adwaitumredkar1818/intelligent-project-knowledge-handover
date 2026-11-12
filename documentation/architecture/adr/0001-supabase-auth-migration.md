# ADR 0001: Supabase Auth as Sole Platform Identity Provider

## Status
Accepted

## Context
The Handover previously implemented a custom FastAPI-managed authentication authority with Argon2id password hashing, short-lived JWTs, and refresh tokens stored in PostgreSQL. To standardize identity management, enable secure session rotation, support email verification, password reset workflows, and future social authentication while reducing authentication maintenance burden, Supabase Auth is adopted as the sole platform identity provider.

## Decision
1. **Supabase Auth as Sole Identity Authority**: Supabase Auth handles user registration, login, logout, password resets, email verification, session refresh, and token issuance via PKCE flow.
2. **FastAPI Asymmetric JWT Verification**: The FastAPI backend validates Supabase-issued access tokens by verifying signatures against Supabase JWKS public keys (`SUPABASE_JWKS_URL`), verifying issuer (`SUPABASE_JWT_ISSUER`), audience (`SUPABASE_JWT_AUDIENCE`), expiry, and subject.
3. **Internal User Mapping**: The internal PostgreSQL `users` table remains authoritative for application relationships (organizations, projects, memberships, audit logs). A `supabase_auth_id` column maps Supabase identities to internal user UUIDs. Existing internal users are linked safely during verified login.
4. **PostgreSQL RBAC Preservation**: Application roles and project-level permissions remain strictly evaluated in PostgreSQL. Roles are never inferred from client-editable user metadata.
5. **No Parallel Authentication**: Legacy custom auth endpoints (`/auth/register`, `/auth/login`, etc.) are safely deprecated in favor of Supabase Auth.

## Consequences
- Requires Supabase project configuration (`SUPABASE_URL`, `SUPABASE_SECRET_KEY`, `SUPABASE_JWKS_URL`, `NEXT_PUBLIC_SUPABASE_URL`, `NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY`).
- Eliminates local credential storage vulnerabilities.
- Next.js frontend uses `@supabase/supabase-js` and `@supabase/ssr` with cookie-based session management.
