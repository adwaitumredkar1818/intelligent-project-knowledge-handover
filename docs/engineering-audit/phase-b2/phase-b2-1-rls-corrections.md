# Phase B2.1: PostgreSQL RLS Semantics & Architecture Corrections

**Platform:** The Handover (*Intelligent Project Knowledge Reconstruction & Handover Platform*)  
**Database Target:** Hosted PostgreSQL 17.11 on Supabase (`aws-1-ap-southeast-2.pooler.supabase.com:5432`)  
**Audit Phase:** Phase B2.1 Technical Reassessment  
**Date:** 2026-11-13  
**Auditor Roles:** Principal Database Architect, PostgreSQL Internals Specialist, Security Engineer  

---

## 1. Executive Summary & Purpose of Reassessment

The Phase B2 report identified key catalog facts regarding Supabase roles, but contained critical conceptual inaccuracies regarding PostgreSQL Row Level Security (RLS) execution semantics, policy combination logic, and the practical effect of `FORCE ROW LEVEL SECURITY`. Consequently, proposed migration `0013_rls_hardening.py` was **rejected**.

This document establishes the precise mathematical and operational behavior of PostgreSQL RLS internals, corrects all inaccurate assertions from the initial design, and provides the rigorous technical baseline necessary for evaluating runtime-role architectures.

---

## 2. Granular Correction of PostgreSQL RLS Semantics

### 2.1 The Absolute Precedence of `BYPASSRLS`
In PostgreSQL, the `BYPASSRLS` clause (`rolbypassrls` in catalog `pg_roles`) is a server-level privilege assigned to roles.

```sql
-- Direct catalog inspection from Handover's live database:
SELECT rolname, rolsuper, rolbypassrls 
FROM pg_roles 
WHERE rolname IN ('postgres', 'service_role', 'anon', 'authenticated', 'supabase_admin');

-- Live Database Result:
-- postgres       | rolsuper: false | rolbypassrls: TRUE
-- service_role   | rolsuper: false | rolbypassrls: TRUE
-- supabase_admin | rolsuper: true  | rolbypassrls: TRUE
-- anon           | rolsuper: false | rolbypassrls: false
-- authenticated  | rolsuper: false | rolbypassrls: false
```

#### Behavioral Rule:
When a query is planned and executed under a role with `rolbypassrls = true`:
- The PostgreSQL query rewriter **completely skips RLS clause generation**.
- The query execution engine **evaluates zero RLS security quals**.
- The role accesses all rows in the table subject only to standard Discretionary Access Control (table-level `GRANT`s).
- **Correction:** The application backend connecting as `postgres` does not merely bypass policies because it owns the tables; it bypasses policies because it holds the explicit `BYPASSRLS` attribute.

---

### 2.2 Table-Owner Semantics & The Exact Boundary of `FORCE ROW LEVEL SECURITY`

In standard PostgreSQL:
1. When RLS is enabled on a table (`ALTER TABLE <table> ENABLE ROW LEVEL SECURITY;`), row security is enforced on all normal roles.
2. The **table owner** (`tableowner` in `pg_tables`, which is `postgres` for all 56 tables) is exempted by default.
3. To subject the table owner to RLS policies, PostgreSQL provides `ALTER TABLE <table> FORCE ROW LEVEL SECURITY;`.

#### The Critical Limitation of `FORCE ROW LEVEL SECURITY`:
PostgreSQL documentation states verbatim:
> *"FORCE ROW LEVEL SECURITY: This causes row security policies to be applied to table owners. (Normal users are always subject to row security anyway.) **Note that this does NOT affect superusers, nor does it affect roles with the BYPASSRLS attribute.**"*

#### Concrete Implication for Handover:
Because role `postgres` possesses `rolbypassrls = true`, executing `ALTER TABLE <table> FORCE ROW LEVEL SECURITY` on Handover's tables has **ZERO EFFECT on the `postgres` role**. 
- Even with `FORCE ROW LEVEL SECURITY` enabled on all 56 tables, queries executed by FastAPI or the background worker connecting as `postgres` will **never be subjected to any RLS policy**.
- Any proposal claiming that `FORCE ROW LEVEL SECURITY` enables row-level tenant enforcement for the existing `postgres` application connection is **factually false under PostgreSQL engine semantics**.

---

### 2.3 Permissive vs. Restrictive Policy Combination Logic

PostgreSQL supports two policy modes: `AS PERMISSIVE` (the default) and `AS RESTRICTIVE`. Understanding how they combine using boolean logic is essential.

#### The Policy Combination Algorithm:
Let $R$ be a candidate row in table $T$ accessed via action $A$ (SELECT, INSERT, UPDATE, DELETE).
- Let $P_1, P_2, \dots, P_n$ be all matching **PERMISSIVE** policies for the active role.
- Let $K_1, K_2, \dots, K_m$ be all matching **RESTRICTIVE** policies for the active role.

The row $R$ is visible/accessible if and only if:
$$\text{Access Granted} = \left( \bigvee_{i=1}^n P_i(R) \right) \land \left( \bigwedge_{j=1}^m K_j(R) \right)$$

1. **Permissive policies are combined with boolean `OR`**: Access is granted if *at least one* permissive policy evaluates to `true`.
2. **Restrictive policies are combined with boolean `AND`**: *Every* restrictive policy must evaluate to `true`, and they must also satisfy the permissive clause.
3. **Default-Deny Rule**: If RLS is enabled on table $T$ and there are **zero** permissive policies applicable to role $U$, the permissive clause evaluates to `false` ($\bigvee \emptyset = \text{false}$). Therefore, **access is denied by default without creating any policy**.

---

### 2.4 The Fallacy of `USING (false)` as an "Explicit Deny"

In the rejected Phase B2 proposal, the following policy was drafted:
```sql
-- INCORRECT DESIGN IN PHASE B2:
CREATE POLICY "deny_anon_access" ON public.users
FOR ALL TO anon
USING (false)
WITH CHECK (false);
```

#### Why This Design Was Flawed:
1. **It is NOT an Explicit Deny:** Because `AS RESTRICTIVE` was omitted, this policy defaults to `AS PERMISSIVE`.
   - In boolean logic: $\text{Permissive Clause} = (\text{false} \lor P_2 \lor \dots \lor P_n)$.
   - If another permissive policy $P_2$ evaluates to `true` (e.g. from an extension, Supabase Auth integration, or subsequent migration), `(false OR true) = true`. Access would be **ALLOWED**.
2. **It is Redundant Under Default-Deny:** When RLS is enabled on a table, if no policies are granted to `anon`, the engine **already denies all access by default**. Creating an empty permissive policy that returns `false` accomplishes nothing beyond cluttering the catalog.
3. **The True Explicit Deny Pattern:** If the objective is to create an absolute deny that overrides any current or future permissive policy, it **must** be declared `AS RESTRICTIVE`:
   ```sql
   -- CORRECT EXPLICIT RESTRICTIVE OVERRIDE:
   CREATE POLICY "strict_deny_anon" ON public.users
   AS RESTRICTIVE
   FOR ALL TO anon
   USING (false)
   WITH CHECK (false);
   ```
   Because restrictive policies combine with `AND`, $(\text{Permissive}) \land \text{false} = \text{false}$, guaranteeing an unconditional block regardless of any other policy.

---

### 2.5 The Fallacy of Policies Targeting `postgres` and `service_role`

In the rejected Phase B2 proposal, the following policy was drafted:
```sql
-- INCORRECT DESIGN IN PHASE B2:
CREATE POLICY "allow_postgres_service" ON public.users
FOR ALL TO postgres, service_role
USING (true)
WITH CHECK (true);
```

#### Why This Policy is Dead Code:
1. Both `postgres` and `service_role` have `rolbypassrls = true`.
2. The PostgreSQL query planner inspects `pg_roles.rolbypassrls` before checking `pg_policy`.
3. Seeing `rolbypassrls = true`, the planner **bypasses RLS entirely**.
4. The policy `"allow_postgres_service"` is **never read, never parsed, and never executed** during any query run by `postgres` or `service_role`.
5. Claiming this policy "permits backend operational access" is completely inaccurate; the backend has access solely because its connection role bypasses RLS at the database engine level.

---

## 3. Comprehensive Summary of Phase B2 Misconceptions vs. PostgreSQL Reality

| Phase B2 Claim / Proposal | PostgreSQL Technical Reality | Severity of Error | Correct Engineering Assessment |
|---|---|---|---|
| *"FORCE RLS forces policies to apply to `postgres`"* | `FORCE RLS` applies only to table owners lacking `BYPASSRLS`. `postgres` has `BYPASSRLS = true`, so it is completely immune to `FORCE RLS`. | **High** | The existing `postgres` connection cannot be constrained by RLS policies under any table configuration. |
| *"Policy `FOR ALL TO anon USING (false)` acts as an explicit DENY"* | It is a default `PERMISSIVE` policy. It evaluates to `false` in an `OR` chain. If any other permissive policy evaluates to `true`, access is permitted. | **High** | To create an absolute deny that cannot be overridden by other policies, `AS RESTRICTIVE` is mandatory. Furthermore, no policy is needed for default-deny. |
| *"Policy `allow_postgres_service USING (true)` ensures backend access"* | `postgres` and `service_role` have `BYPASSRLS = true`. The engine skips policy evaluation entirely for these roles. | **Medium** | The policy is completely inert dead code in the catalog. |
| *"RLS on `postgres` provides defense-in-depth against SQL injection"* | Because `postgres` bypasses RLS, an injected query running on the application connection will also bypass RLS and can read all rows across all tenants. | **High** | RLS on `postgres` provides **zero protection** against SQL injection or application-level tenant isolation bugs. |
| *"All 56 tables can share a generic allow/deny policy template"* | Different tables have fundamentally different scopes (Platform Global, Org Scoped, Project Scoped, User Scoped, System Queue). A single blanket policy structure fails to address actual tenant boundaries. | **Medium** | Tables must be classified by domain with explicit, tailored policies for each tenant tier. |
