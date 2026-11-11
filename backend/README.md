# Backend Application Foundation (`backend/`)

Python 3.11 + FastAPI backend runtime for the **Intelligent Project Knowledge Reconstruction & Handover Platform**.

> **Current Stage (Phase 2.2 — Platform Authentication, Identity & RBAC):** Core application skeleton, centralised Pydantic Settings (reading root `.env`), structured correlation-ID and security logging, safe exception handling, SQLAlchemy 2.x + Psycopg 3 PostgreSQL engine/session management, Alembic migrations (`0001_initial_baseline`, `0002_auth_identity_rbac`), infrastructure health/readiness endpoints, and platform authentication, refresh-session rotation, user lifecycle, and scope-separated RBAC endpoints under `/api/v1` are implemented and verified. Organisations, project workspaces, source connectors, document ingestion, worker execution, ChromaDB pipelines, and AI/RAG endpoints belong to subsequent phases and are not yet implemented.

---

## Application Structure (`backend/app/`)

```text
backend/
├── app/
│   ├── api/
│   │   ├── deps.py                # FastAPI dependencies (settings, DB, HTTPX, JWT principal, RBAC, rate limit)
│   │   ├── routes/
│   │   │   ├── auth.py            # /api/v1/auth endpoints (register, login, refresh, logout, me, sessions)
│   │   │   ├── health.py          # Infrastructure liveness and readiness routes
│   │   │   └── users.py           # /api/v1/users & /api/v1/roles admin lifecycle endpoints
│   │   └── v1/router.py           # Versioned /api/v1 router assembly
│   ├── core/
│   │   ├── config.py              # Pydantic Settings with separated DB, ChromaDB, Ollama & Security blocks
│   │   ├── exceptions.py          # Typed AppError hierarchy + sanitised error handlers & cookie cleanup
│   │   ├── logging.py             # Single-line structured JSON logger with correlation ID & secret redaction
│   │   ├── middleware.py          # X-Request-ID correlation, request timing log & baseline security headers
│   │   ├── rate_limit.py          # Pluggable rate-limiter protocol & in-memory sliding-window backend
│   │   ├── rbac_catalog.py        # Scope-separated system roles & permissions catalog (15 perms, 7 roles)
│   │   ├── security.py            # Argon2id hashing, JWT creation/decoding, HttpOnly cookies & CSRF Origin check
│   │   └── validators.py          # Shared UTC datetime helpers, email normalisation & password strength checks
│   ├── db/
│   │   ├── base.py                # SQLAlchemy 2.x DeclarativeBase + PostgreSQL naming convention
│   │   └── session.py             # Psycopg 3 engine lifecycle, session factory, connectivity ping
│   ├── models/                    # ORM models (User, RefreshSession, Role, Permission, RolePermission, UserRole)
│   ├── repositories/
│   │   ├── auth.py                # RefreshSession persistence, rotation, family revocation & reuse detection
│   │   ├── rbac.py                # Role, Permission, RolePermission & UserRole queries/assignments
│   │   ├── system.py              # Database connectivity probe repository
│   │   └── user.py                # User identity persistence & lifecycle queries
│   ├── schemas/
│   │   ├── auth.py                # Auth request/response & session Pydantic v2 schemas
│   │   ├── common.py              # Canonical ErrorResponse / ErrorDetail schemas
│   │   ├── health.py              # HealthResponse & ReadinessResponse Pydantic v2 models
│   │   └── user.py                # User profile, admin user management & RBAC role/permission schemas
│   ├── services/
│   │   ├── auth.py                # Registration, login, token rotation, logout & self-session management
│   │   ├── health.py              # Orchestrates DB readiness + optional Ollama/ChromaDB probes
│   │   ├── rbac.py                # Role/permission lookup, bootstrap & assignment validation
│   │   └── user.py                # Admin user inspection, status lifecycle & role assignment orchestration
│   └── main.py                    # FastAPI app factory, lifespan disposal, CORS, middleware & rate limiter
├── tests/                         # Unit, isolated security/RBAC/migration & read-only live Postgres tests
├── alembic.ini                    # Alembic config pointing to ../infrastructure/database/migrations
├── pyproject.toml                 # Dependencies, optional phase groups, ruff, mypy (strict) & pytest config
└── requirements.txt               # Pinned baseline dependencies compiled with uv
```

---

## Setup & Local Execution

```powershell
# 1. Create and activate Python 3.11 virtual environment (from repository root)
py -3.11 -m venv backend\.venv
.\backend\.venv\Scripts\Activate.ps1

# 2. Install pinned baseline dependencies (and optional dev tools for lint/type/test)
python -m pip install --upgrade pip
python -m pip install -r backend\requirements.txt
python -m pip install pytest ruff mypy

# 3. Run FastAPI locally against Docker PostgreSQL/ChromaDB & native Windows Ollama
cd backend
uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

---

## Database & Alembic Migrations

Migration scripts live under [`../infrastructure/database/migrations/`](../infrastructure/database/migrations) as specified in [`../AGENTS.md`](../AGENTS.md), configured via [`alembic.ini`](alembic.ini) and reading `DATABASE_URL` dynamically from root `.env` via `Settings`:

```powershell
# Run from backend/ (with PostgreSQL container healthy)
alembic current
alembic history
alembic upgrade head
alembic check

# Or invoke from repository root:
.\backend\.venv\Scripts\alembic.exe -c backend\alembic.ini current
```

---

## Quality Checks & Tests

```powershell
cd backend
..\backend\.venv\Scripts\ruff.exe check app tests ..\infrastructure\database\migrations
..\backend\.venv\Scripts\mypy.exe app tests ..\infrastructure\database\migrations\env.py ..\infrastructure\database\migrations\versions\20261111_0002_auth_identity_rbac.py
..\backend\.venv\Scripts\pytest.exe -v
```

---

## Dependency Groups (`pyproject.toml`)

- **Baseline Runtime (`requirements.txt`)**: `fastapi`, `uvicorn[standard]`, `pydantic`, `pydantic-settings`, `sqlalchemy`, `psycopg[binary]`, `alembic`, `httpx`, `python-dotenv`, `pyjwt`, `pwdlib[argon2]`.
- **Separated Optional Groups** *(deferred until their implementation phases)*:
  - `documents`: `pymupdf`, `python-docx`, `python-multipart`
  - `embeddings-rag`: `chromadb-client`
  - `integrations-security`: `cryptography` *(deferred for external source OAuth token encryption)*
  - `worker`: lightweight PostgreSQL-backed worker utilities *(no Redis or Celery)*
  - `dev`: `pytest`, `ruff`, `mypy`
