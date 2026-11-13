# Phase B3 Architecture Recommendation & Hardening Roadmap
## Definitive Governance Specification for Database Security Hardening

**Platform:** The Handover (*Intelligent Project Knowledge Reconstruction & Handover Platform*)  
**Database Target:** Hosted PostgreSQL 17.11 on Supabase (`aws-1-ap-southeast-2.pooler.supabase.com:5432`)  
**Audit Phase:** Phase B2.1 Technical Reassessment & Strategic Roadmap  
**Date:** 2026-11-13  
**Auditor Roles:** Principal Database Architect, Security Engineer, Lead Backend Architect  

---

## 1. Baseline Security Protections Currently Active

Before designing additional controls, we explicitly document the extensive security mechanisms already verified as operational across The Handover platform:

1. **FastAPI Sole Identity Authority:**
   Platform authentication is managed entirely in FastAPI using Argon2id password hashing, 60-minute JWT access tokens, and SHA-256 hashed refresh session rotation stored in `HttpOnly`, `SameSite=Lax`, `Secure` cookies. Supabase Auth is completely decoupled from platform identity.
2. **PostgreSQL-Backed RBAC:**
   The `RbacService` evaluates permissions across Platform, Organisation, and Project scopes with dynamic parent-organisation membership verification, preventing orphan project access.
3. **Mandatory Source-Level ACL Filtering (AGENTS.md Rule #2):**
   Project membership is explicitly decoupled from source access. Delegated OAuth tokens (GitHub, Jira, Slack) and Personal Access Tokens are verified at read time via `SourceAccessPolicyService` before any document, chunk, or finding is returned or entered into an LLM prompt.
4. **Dual-Provider Private Encrypted Storage:**
   All uploaded document payloads are envelope-encrypted with AES-256-GCM before reaching disk or the private Supabase Storage bucket (`project-evidence`). Direct downloads are impossible; all file retrieval is mediated through backend streaming endpoints that enforce source ACLs.
5. **PostgREST Gateway Enforcement:**
   Empirical probes confirm that unauthenticated calls to Supabase PostgREST endpoints return `401 Unauthorized`.
6. **Discretionary Access Control (DAC):**
   PostgreSQL system catalog queries confirm that roles `anon` and `authenticated` have `USAGE = False` on schema `public` and hold **0 table privileges** across all 56 public tables.
7. **Project-Isolated Vector Store:**
   ChromaDB operates with strictly one collection per Handover project (`handover_{project_id}`), preventing cross-project embedding retrieval.

---

## 2. Identified Security Gaps & Systemic Risks

Despite the strong application-tier controls above, two infrastructure security gaps remain:

1. **Absence of Row Level Security (The Single-Point-of-Failure Gap):**
   All 56 public base tables currently run with Row Level Security **disabled** (`relrowsecurity = False`). If an operator, third-party script, or dashboard toggle ever executes `GRANT USAGE ON SCHEMA public TO anon, authenticated;`, the Discretionary Access Control boundary collapses, and all 56 tables become readable via PostgREST.
2. **Internal Application-Connection Bypass:**
   Because the backend connects as role `postgres` (which holds `rolbypassrls = True`), the database engine does not enforce row security on queries originating from the application. Multi-tenancy relies exclusively on application code and SQLAlchemy `.where()` clauses. While parameterization prevents SQL injection, the database itself does not provide secondary row-level containment for the `postgres` user.

---

## 3. Definitive Architectural Recommendations

### Recommendation 1: Implement Row Level Security (Perimeter Defense-in-Depth)
- **Verdict: YES, RLS MUST BE ENABLED ON ALL 56 PUBLIC BASE TABLES.**
- RLS should not attempt to replace FastAPI authorization or source ACL filtering. Instead, RLS must act as an **impenetrable external perimeter** that permanently neutralizes the Supabase PostgREST Data API.

### Recommendation 2: Adopt Runtime Role Alternative A (Perimeter RLS with Current `postgres` Connection)
- **Verdict: ADOPT ALTERNATIVE A FOR PHASE B3.**
- **Technical Justification:**
  1. **Zero Connection Pooler Risk:** Fully compatible with Supavisor session mode on port 5432.
  2. **Zero Query Latency Overhead:** Because `postgres` has `BYPASSRLS = True`, the PostgreSQL query planner evaluates zero RLS quals for application queries, resulting in **0 ms latency overhead**.
  3. **Preserves AGENTS.md Rule #2:** Fine-grained source ACL checks continue to be evaluated accurately in Python service layers, avoiding the severe risk of over-permissive project leaks in SQL.
  4. **Unimpaired Background Workers:** The composite worker processes multi-tenant background batches without role switching or transaction context contention.
  5. **Clean Alembic Compatibility:** Alembic runs DDL seamlessly as the table owner.

---

## 4. Provider-Side Configurations to Confirm Before Alternative B

Transitioning to a dedicated unprivileged application role (Alternative B, e.g. `handover_app`) is **deferred** pending provider-side verification:

1. **Supavisor Custom Pooler User Verification:**
   - In hosted Supabase, the Supavisor connection pooler authenticates users formatted as `<user>.<project_ref>`.
   - The user/administrator must verify via the Supabase Dashboard or Supabase Support whether Supavisor supports pooling connections for custom roles created via SQL, or whether pooler authentication is restricted exclusively to `postgres`.
2. **Supabase PostgREST Public Schema Exposure:**
   - In Supabase Dashboard $\to$ `Project Settings` $\to$ `API`, verify that "Exposed schemas" does not expose internal or unmanaged schemas.

---

## 5. Prerequisites Before Migration `0013_rls_hardening.py` Can Be Authorized

To authorize the creation and execution of migration `0013_rls_hardening.py`, the following four engineering conditions must be satisfied:

### Condition 1: Elimination of Flawed Phase B2 Design Patterns
- The proposed migration must **NOT** include redundant permissive `USING (false)` policies.
- The proposed migration must **NOT** include inert `allow_postgres_service` policies targeting `BYPASSRLS` roles.

### Condition 2: Correct Declarative Hardening DDL Specification
The migration must implement clean, mathematically sound PostgreSQL RLS semantics:
```python
def upgrade() -> None:
  # 1. Enable Row Level Security across all 56 base tables
  for table in _ALL_56_PUBLIC_BASE_TABLES:
    op.execute(f"ALTER TABLE public.{table} ENABLE ROW LEVEL SECURITY;")
    # Explicit restrictive deny guarantees that even if a permissive policy
    # is accidentally created in the future, access remains locked down.
    op.execute(f"""
            CREATE POLICY "strict_deny_anon" ON public.{table}
            AS RESTRICTIVE
            FOR ALL TO anon
            USING (false)
            WITH CHECK (false);
        """)
    op.execute(f"""
            CREATE POLICY "strict_deny_authenticated" ON public.{table}
            AS RESTRICTIVE
            FOR ALL TO authenticated
            USING (false)
            WITH CHECK (false);
        """)

  # 2. Reinforce Discretionary Access Control (DAC)
  op.execute("REVOKE ALL ON ALL TABLES IN SCHEMA public FROM anon, authenticated;")
  op.execute(
      "REVOKE ALL ON ALL SEQUENCES IN SCHEMA public FROM anon, authenticated;"
  )
  op.execute(
      "REVOKE ALL ON ALL FUNCTIONS IN SCHEMA public FROM anon, authenticated;"
  )
  op.execute(
      "REVOKE USAGE, CREATE ON SCHEMA public FROM anon, authenticated, public;"
  )


def downgrade() -> None:
  for table in _ALL_56_PUBLIC_BASE_TABLES:
    op.execute(
        f'DROP POLICY IF EXISTS "strict_deny_authenticated" ON public.{table};'
    )
    op.execute(f'DROP POLICY IF EXISTS "strict_deny_anon" ON public.{table};')
    op.execute(f"ALTER TABLE public.{table} DISABLE ROW LEVEL SECURITY;")
```

### Condition 3: Full Reversibility
The migration must be 100% reversible via standard `alembic downgrade 0012_verification_center`.

### Condition 4: Explicit User Approval
Execution must occur only after explicit user approval of this Phase B2.1 reassessment package.
