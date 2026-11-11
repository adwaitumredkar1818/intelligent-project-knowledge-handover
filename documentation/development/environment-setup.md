# Environment Setup Guide

> **Current Phase Notice:** **Phase 2.2 (Platform Authentication, Identity & RBAC)** is complete: Docker infrastructure (**PostgreSQL** and **ChromaDB**), native Windows **Ollama** (`qwen3:8b`, `glm-ocr:latest`, `nomic-embed-text`), the Next.js TypeScript runtime (`frontend/`), the FastAPI backend foundation (`backend/app/`, `infrastructure/database/migrations/`), and platform authentication, refresh-session rotation, and scope-separated RBAC (`0002_auth_identity_rbac`) are implemented and verified. Organisations, project workspaces, source integrations, ingestion, and AI/RAG endpoints are not yet implemented.

---

## 1. Prerequisites (Confirmed Platform Tooling)

Ensure the following tools are installed on your development workstation:

| Tool | Requirement / Role | Notes |
| :--- | :--- | :--- |
| **Git** | Version control | Repository tracks `main` branch; ignores `.env`, `backend/.venv/`, `frontend/node_modules/`, and local `graphify-out/` |
| **Docker Desktop & Docker Compose** | Local container orchestration | Runs PostgreSQL (`postgres:16-alpine`) and ChromaDB (`chromadb/chroma:latest`) now, and backend/worker/frontend containers in later phases. *On Windows, if `docker` is not on your shell `PATH`, add `%LOCALAPPDATA%\Programs\DockerDesktop\resources\bin` (or `C:\Program Files\Docker\Docker\resources\bin`).* |
| **Existing Native Ollama (Windows Host)** | Local LLM, embedding & initial OCR runtime | Runs natively on the host at `127.0.0.1:11434` (do **not** containerise Ollama); hosts `qwen3:8b`, `nomic-embed-text`, and `glm-ocr:latest` |
| **Python 3.11** | Backend & worker runtime | Verified with Python `3.11.9`; provides FastAPI, Uvicorn, Pydantic, **SQLAlchemy 2.x**, **Alembic**, **Psycopg 3 (`psycopg`)**, HTTPX, and `python-dotenv` |
| **Node.js & npm** | Frontend runtime | Verified with Node.js `v26.13.0` and npm `11.19.1`; runs Next.js, React, TypeScript, Tailwind CSS, shadcn/ui-compatible setup, and Lucide Icons |

---

## 2. Local AI, Embedding & OCR Models (Confirmed)

All initial local inference runs through the **native Ollama installation on the Windows host** (do **not** containerise Ollama and do **not** introduce vLLM or another OCR runtime at this stage):

1. **Benchmark LLM**: `qwen3:8b` (`OLLAMA_LLM_MODEL=qwen3:8b`)
2. **Embedding Model**: `nomic-embed-text` (`OLLAMA_EMBEDDING_MODEL=nomic-embed-text`)
3. **Initial OCR Model**: `glm-ocr:latest` (`OLLAMA_OCR_MODEL=glm-ocr:latest`), consumed through a replaceable backend OCR service abstraction.

Verify available models on the Windows host:
```powershell
ollama list
```

> **Critical Rule:** `OLLAMA_EMBEDDING_MODEL` must remain identical across ingestion indexing and RAG query retrieval. Changing this model requires re-indexing all chunks from PostgreSQL into ChromaDB.

---

## 3. Environment Variables Reference

Copy `.env.example` to `.env` before starting Docker Compose. **Never commit `.env` to Git.**

### 3.1 Group 1: Mandatory Local Development Variables

Required to boot core services and configure local persistence/security:

| Variable | Scope | Secret? | Default / Example | Description |
| :--- | :--- | :--- | :--- | :--- |
| `APP_ENV` | Backend | No | `development` | Environment mode (`development`, `test`, `production`) |
| `LOG_LEVEL` | Backend / Worker | No | `INFO` | Structured logging verbosity |
| `BACKEND_HOST` | Backend | No | `0.0.0.0` | FastAPI bind address |
| `BACKEND_PORT` | Backend | No | `8000` | FastAPI HTTP port |
| `CORS_ALLOWED_ORIGINS` | Backend | No | `http://localhost:3000` | Allowed frontend origin(s) for CORS & cookie origin checks |
| `NEXT_PUBLIC_API_BASE_URL` | Frontend | **No** | `http://localhost:8000/api/v1` | Public backend API base URL. **Never place secrets in `NEXT_PUBLIC_*` variables.** |
| `POSTGRES_HOST` | Backend / Worker / Infra | No | `localhost` | Hostname from Windows host (`localhost`); Docker containers **must** use `postgres` |
| `POSTGRES_PORT` | Backend / Worker / Infra | No | `5432` | Loopback host port bound by PostgreSQL (`127.0.0.1:${POSTGRES_PORT}:5432`) |
| `POSTGRES_DB` | Backend / Worker / Infra | No | `knowledge_handover` | Canonical PostgreSQL database name |
| `POSTGRES_USER` | Backend / Worker / Infra | No | `postgres` | PostgreSQL username |
| `POSTGRES_PASSWORD` | Backend / Worker / Infra | **Yes** | *(replace locally)* | PostgreSQL password (required by `docker-compose.yml`; never commit) |
| `DATABASE_URL` | Backend / Worker / Alembic | **Yes** | `postgresql+psycopg://...` | SQLAlchemy 2.x + Psycopg 3 (`psycopg`) connection URL |
| `CHROMA_HOST` | Backend / Worker / Infra | No | `localhost` | Hostname from Windows host (`localhost`); Docker containers **must** use `chromadb` |
| `CHROMA_PORT` | Backend / Worker / Infra | No | `8001` | Loopback host port mapped to ChromaDB's internal port `8000` (`127.0.0.1:${CHROMA_PORT}:8000`) |
| `CHROMA_COLLECTION_PREFIX` | Backend / Worker | No | `ipkrh` | Prefix for ChromaDB collections |
| `OLLAMA_BASE_URL` | Backend / Worker | No | `http://localhost:11434` | Windows host URL (`http://localhost:11434`); Docker containers **must** use `http://host.docker.internal:11434` |
| `OLLAMA_LLM_MODEL` | Backend / Worker | No | `qwen3:8b` | Local LLM model tag |
| `OLLAMA_EMBEDDING_MODEL` | Backend / Worker | No | `nomic-embed-text` | Embedding model tag (identical for indexing & retrieval) |
| `OLLAMA_OCR_MODEL` | Backend / Worker | No | `glm-ocr:latest` | Initial OCR model hosted in native Ollama via backend OCR abstraction |
| `JWT_SECRET_KEY` | Backend | **Yes** | *(generate random ≥32 bytes)* | Signing secret for FastAPI-managed short-lived JWT access tokens |
| `JWT_ALGORITHM` | Backend | No | `HS256` | JWT signing algorithm |
| `JWT_ACCESS_TOKEN_EXPIRE_MINUTES` | Backend | No | `15` | Access token lifetime (minutes) |
| `JWT_REFRESH_TOKEN_EXPIRE_DAYS` | Backend | No | `7` | Refresh token lifetime (days; transported in `HttpOnly` cookie only) |
| `TOKEN_ENCRYPTION_KEY` | Backend / Worker | **Yes** | *(generate 32-byte key)* | Symmetric key for encrypting external source OAuth tokens in PostgreSQL |
| `FILE_ENCRYPTION_KEY` | Backend / Worker | **Yes** | *(generate 32-byte key)* | Symmetric key for local at-rest encryption of uploaded files *(replaced by KMS in production)* |
| `UPLOAD_STORAGE_PATH` | Backend / Worker | No | `./data/uploads` | Private backend/worker directory for encrypted uploads, strictly outside frontend directories |

### 3.2 Group 2: Optional Source Integrations (Disabled by Default)

**Developers do NOT need to populate client IDs, secrets, or tokens for any integration while its `*_ENABLED` flag is `false`.**

| Variable | Scope | Secret? | Default / Example | Description |
| :--- | :--- | :--- | :--- | :--- |
| `GITHUB_ENABLED` | Backend / Worker | No | `false` | Enable GitHub API integration (initial source priority when enabled) |
| `GITHUB_API_BASE_URL` | Backend / Worker | No | `https://api.github.com` | GitHub REST API base URL |
| `GITHUB_CLIENT_ID` | Backend | No | *(empty)* | GitHub OAuth app client ID *(required only when `GITHUB_ENABLED=true`)* |
| `GITHUB_CLIENT_SECRET` | Backend | **Yes** | *(empty)* | GitHub OAuth app client secret *(required only when `GITHUB_ENABLED=true`)* |
| `GITHUB_REDIRECT_URI` | Backend | No | `http://localhost:8000/api/v1/integrations/github/callback` | GitHub delegated OAuth callback |
| `JIRA_ENABLED` | Backend / Worker | No | `false` | Enable Jira API integration (initial source priority when enabled) |
| `JIRA_AUTH_BASE_URL` | Backend | No | `https://auth.atlassian.com` | Atlassian OAuth 2.0 base URL |
| `JIRA_API_BASE_URL` | Backend | No | `https://api.atlassian.com` | Jira Cloud REST API base URL |
| `JIRA_CLIENT_ID` | Backend | No | *(empty)* | Jira OAuth 2.0 (3LO) client ID *(required only when `JIRA_ENABLED=true`)* |
| `JIRA_CLIENT_SECRET` | Backend | **Yes** | *(empty)* | Jira OAuth 2.0 (3LO) client secret *(required only when `JIRA_ENABLED=true`)* |
| `JIRA_REDIRECT_URI` | Backend | No | `http://localhost:8000/api/v1/integrations/jira/callback` | Jira delegated OAuth callback |
| `SLACK_ENABLED` | Backend / Worker | No | `false` | Optional MVP gate — keep `false` until workspace auth, API scope review & retention are confirmed |
| `SLACK_API_BASE_URL` | Backend / Worker | No | `https://slack.com/api` | Slack Web API base URL |
| `SLACK_CLIENT_ID` | Backend | No | *(empty)* | Slack app client ID *(required only when `SLACK_ENABLED=true`)* |
| `SLACK_CLIENT_SECRET` | Backend | **Yes** | *(empty)* | Slack app client secret *(required only when `SLACK_ENABLED=true`)* |
| `SLACK_SIGNING_SECRET` | Backend | **Yes** | *(empty)* | Slack request signing secret *(required only when `SLACK_ENABLED=true`)* |
| `SLACK_REDIRECT_URI` | Backend | No | `http://localhost:8000/api/v1/integrations/slack/callback` | Slack delegated OAuth callback |

### 3.3 Group 3: Deployment-Specific & Tuning Variables

| Variable | Scope | Secret? | Default / Example | Description |
| :--- | :--- | :--- | :--- | :--- |
| `APP_NAME` | Backend | No | `"Intelligent Project Knowledge Reconstruction & Handover Platform"` | Service display name |
| `COOKIE_SECURE` | Backend | No | `false` | Set `true` in all HTTPS staging/production deployments (`false` for `http://localhost` only) |
| `JWT_ISSUER` | Backend | No | `ipkrh-platform` | Canonical `iss` claim enforced on platform JWT access tokens |
| `JWT_AUDIENCE` | Backend | No | `ipkrh-api` | Canonical `aud` claim enforced on platform JWT access tokens |
| `AUTH_RATE_LIMIT_ENABLED` | Backend | No | `true` | Enable pluggable rate-limiting hook on auth mutation/credential endpoints |
| `AUTH_RATE_LIMIT_MAX_ATTEMPTS` | Backend | No | `20` | Maximum attempts per rate-limit window before returning `429 Too Many Requests` |
| `AUTH_RATE_LIMIT_WINDOW_SECONDS` | Backend | No | `60` | Sliding window duration in seconds for authentication rate limiting |
| `COOKIE_SAMESITE` | Backend | No | `lax` | `SameSite` policy (`lax` or `strict`) for `HttpOnly` refresh token cookies |
| `COOKIE_DOMAIN` | Backend | No | *(empty)* | Cookie domain override for non-localhost deployments |
| `MAX_UPLOAD_SIZE_MB` | Backend | No | `50` | Maximum allowed single upload file size in megabytes |
| `WORKER_POLL_INTERVAL_SECONDS` | Worker | No | `5` | Polling interval (seconds) for the PostgreSQL-backed Python worker |
| `WORKER_MAX_ATTEMPTS` | Worker | No | `3` | Maximum retry attempts before moving a failed job to `dead_letter` |
| `POSTGRES_SSL_MODE` | Backend / Worker | No | `prefer` | PostgreSQL TLS mode (`require` / `verify-full` recommended in production) |
| `CHROMA_AUTH_TOKEN` | Backend / Worker / Infra | **Yes** | *(empty)* | Reserved for reverse-proxy/gateway authentication in shared deployments *(not used natively by local `chromadb/chroma:latest` 1.4.4)* |

---

## 4. Docker Infrastructure Operations (Phase 1.1)

Run all Compose commands from the repository root passing `--env-file .env` so Docker Compose loads root `.env` safely without placing a duplicate `.env` inside `infrastructure/docker/`:

### 4.1 Validate Configuration & Start Services

```powershell
# Validate rendered Compose configuration
docker compose --env-file .env -f infrastructure/docker/docker-compose.yml config -q

# Start PostgreSQL and ChromaDB in detached mode
docker compose --env-file .env -f infrastructure/docker/docker-compose.yml up -d
```

### 4.2 Stop Services Safely (Preserving Volumes)

> **Data Safety Warning:** **NEVER** run `docker compose down -v` in normal workflows—the `-v` flag deletes `ipkrh_postgres_data` and `ipkrh_chroma_data`.

```powershell
# Stop running containers without removing them
docker compose --env-file .env -f infrastructure/docker/docker-compose.yml stop

# Or stop and remove containers/network while preserving named volumes
docker compose --env-file .env -f infrastructure/docker/docker-compose.yml down
```

### 4.3 Inspect Service Health & Logs

```powershell
# View running containers, ports, and health status
docker compose --env-file .env -f infrastructure/docker/docker-compose.yml ps

# Inspect detailed Docker health check output
docker inspect --format '{{.Name}} | Status={{.State.Status}} | Health={{.State.Health.Status}}' ipkrh-postgres ipkrh-chromadb

# Tail logs for both services or a single service
docker compose --env-file .env -f infrastructure/docker/docker-compose.yml logs -f postgres chromadb
docker compose --env-file .env -f infrastructure/docker/docker-compose.yml logs --tail 100 postgres
```

---

## 5. Connecting to Services & Native Ollama

### 5.1 Connecting to PostgreSQL

- **From Windows host (e.g., local Python tools, DBeaver, pgAdmin)**:
  - Host: `127.0.0.1` (loopback-only binding; not exposed on external network interfaces)
  - Port: `5432` (or `POSTGRES_PORT` from `.env`)
  - Database / User / Password: `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD` from `.env`
  - Connection test via `pg_isready` and `psql` inside the container (replace `postgres` / `knowledge_handover` if overridden in `.env`):
    ```powershell
    docker compose --env-file .env -f infrastructure/docker/docker-compose.yml exec -T postgres pg_isready -U postgres -d knowledge_handover
    docker compose --env-file .env -f infrastructure/docker/docker-compose.yml exec -T postgres psql -U postgres -d knowledge_handover -t -A -c "SELECT current_database(), current_user, version();"
    ```
- **From future Docker containers (`backend` / `worker`) on `ipkrh_network`**:
  - Use Docker service name **`postgres`** on internal port **`5432`**:
    `postgresql+psycopg://<POSTGRES_USER>:<POSTGRES_PASSWORD>@postgres:5432/<POSTGRES_DB>`

### 5.2 Accessing ChromaDB

- **From Windows host**:
  - Endpoint: `http://127.0.0.1:8001` (mapped from container port `8000`; host port `8001` avoids colliding with FastAPI on `8000`)
  - Heartbeat check (`chromadb/chroma:latest` v1.4.4 exposes the v2 API; `/api/v1/heartbeat` returns `410 Gone`):
    ```powershell
    Invoke-RestMethod -Uri "http://127.0.0.1:8001/api/v2/heartbeat"
    ```
- **From future Docker containers (`backend` / `worker`) on `ipkrh_network`**:
  - Use Docker service name **`chromadb`** and **internal container port `8000`**:
    `http://chromadb:8000`
- **Security Note**: `chromadb/chroma:latest` (`chroma 1.4.4` single-node server) does not include native built-in token authentication inside the container binary. Local access is restricted via `127.0.0.1` loopback binding and `ipkrh_network` isolation; shared/production deployments must enforce `CHROMA_AUTH_TOKEN` via an authenticated reverse proxy.

### 5.3 Connecting to Native Windows Ollama from Docker Containers

> **Important Container Networking Rule:** Inside any Docker container, `localhost` and `127.0.0.1` refer to **that container itself**, never the Windows host and never sibling containers.

- **From Windows host**: `OLLAMA_BASE_URL=http://localhost:11434`
- **From Docker containers (`backend` / `worker`)**: Set `OLLAMA_BASE_URL=http://host.docker.internal:11434` (Docker Desktop on Windows routes `host.docker.internal` to the host machine).
- **Host Firewall / Ollama Bind Tip**: By default, Ollama on Windows listens on `127.0.0.1:11434` and Docker Desktop forwards `host.docker.internal` traffic cleanly to the host. Verify from inside a container on `ipkrh_network`:
  ```powershell
  @'
  exec 3<>/dev/tcp/host.docker.internal/11434
  printf "GET /api/tags HTTP/1.0\r\nHost: host.docker.internal\r\n\r\n" >&3
  cat <&3
  '@ -replace "`r","" | docker run --rm -i --network ipkrh_network --entrypoint bash chromadb/chroma:latest -s
  ```

---

## 6. Backing Up & Restoring Persistent Data

Named Docker volumes (`ipkrh_postgres_data`, `ipkrh_chroma_data`) persist across container restarts and `docker compose down`.

### 6.1 PostgreSQL Backup & Restore

> **PowerShell Tip:** Avoid PowerShell `>` redirection for binary `.dump` files, as PowerShell encodes stdout streams and can corrupt binary dumps. Create the dump inside the container and copy it out with `docker cp`.

```powershell
# Create backups directory locally (ignored if placed under ./data or ./tmp, or keep outside repo)
New-Item -ItemType Directory -Force -Path ./tmp/backups | Out-Null

# Backup (custom binary format inside container -> copy to host)
docker compose --env-file .env -f infrastructure/docker/docker-compose.yml exec -T postgres pg_dump -U postgres -d knowledge_handover -Fc -f /tmp/pg_backup.dump
docker cp ipkrh-postgres:/tmp/pg_backup.dump ./tmp/backups/pg_backup.dump
docker compose --env-file .env -f infrastructure/docker/docker-compose.yml exec -T postgres rm -f /tmp/pg_backup.dump

# Restore (copy dump into container -> pg_restore into clean/target DB)
docker cp ./tmp/backups/pg_backup.dump ipkrh-postgres:/tmp/pg_backup.dump
docker compose --env-file .env -f infrastructure/docker/docker-compose.yml exec -T postgres pg_restore -U postgres -d knowledge_handover --clean --if-exists /tmp/pg_backup.dump
docker compose --env-file .env -f infrastructure/docker/docker-compose.yml exec -T postgres rm -f /tmp/pg_backup.dump
```

### 6.2 ChromaDB Volume Backup & Restore

*(Reminder: PostgreSQL is canonical, and ChromaDB embeddings remain deterministically rebuildable from PostgreSQL `evidence_chunks` once Phase 1.2+ indexing is implemented.)*

```powershell
# Backup ChromaDB named volume (/data) using a temporary Alpine container
docker run --rm -v ipkrh_chroma_data:/data:ro -v "${PWD}/tmp/backups:/backup" alpine tar czf /backup/chroma_backup.tar.gz -C /data .

# Restore ChromaDB named volume (stop chromadb first so files are not mutated mid-restore)
docker compose --env-file .env -f infrastructure/docker/docker-compose.yml stop chromadb
docker run --rm -v ipkrh_chroma_data:/data -v "${PWD}/tmp/backups:/backup" alpine sh -c "rm -rf /data/* && tar xzf /backup/chroma_backup.tar.gz -C /data"
docker compose --env-file .env -f infrastructure/docker/docker-compose.yml start chromadb
```

---

## 7. Backend & Frontend Runtime Setup (Phase 1.2)

### 7.1 Backend Python 3.11 Environment (`backend/`)

Dependency definitions live in [`backend/pyproject.toml`](../../backend/pyproject.toml) (with separated optional dependency groups for future phases) and pinned reproducible baseline versions in [`backend/requirements.txt`](../../backend/requirements.txt).

```powershell
# 1. Create the Python 3.11 virtual environment from the repository root
py -3.11 -m venv backend\.venv

# 2. Activate the virtual environment in PowerShell
.\backend\.venv\Scripts\Activate.ps1

# 3. Install pinned baseline packages (and optional dev quality tools)
python -m pip install --upgrade pip
python -m pip install -r backend\requirements.txt
python -m pip install pytest ruff mypy

# 4. Verify baseline imports
python -c "import fastapi, uvicorn, pydantic, pydantic_settings, sqlalchemy, psycopg, alembic, httpx, dotenv, jwt, pwdlib; print('Backend baseline imports OK')"
```

- **Baseline Runtime Dependencies** (`backend/requirements.txt`): `fastapi`, `uvicorn[standard]`, `pydantic`, `pydantic-settings`, `sqlalchemy`, `psycopg[binary]`, `alembic`, `httpx`, `python-dotenv`, `pyjwt`, `pwdlib[argon2]`.
- **Separated Optional Dependency Groups** (do **not** install prematurely; install only as their phases start):
  - `documents`: `pymupdf`, `python-docx`, `python-multipart`
  - `embeddings-rag`: `chromadb-client`
  - `integrations-security`: `cryptography` *(deferred for external OAuth source token encryption)*
  - `worker`: lightweight worker utilities *(no Redis or Celery)*
  - `dev`: `pytest`, `ruff`, `mypy` *(installed for Phase 2.1–2.2 verification)*
- **Re-locking Base Dependencies** (when updating `backend/pyproject.toml`):
  ```powershell
  uv pip compile backend\pyproject.toml --python-version 3.11 -o backend\requirements.txt
  ```
- **Running the FastAPI Application & Database Checks (Phase 2.2)**:
  ```powershell
  cd backend

  # Validate Alembic state & apply migrations (requires healthy ipkrh-postgres)
  ..\backend\.venv\Scripts\alembic.exe upgrade head
  ..\backend\.venv\Scripts\alembic.exe current
  ..\backend\.venv\Scripts\alembic.exe check

  # Run lint, strict typing, and test suite
  ..\backend\.venv\Scripts\ruff.exe check app tests ..\infrastructure\database\migrations
  ..\backend\.venv\Scripts\mypy.exe app tests ..\infrastructure\database\migrations\env.py ..\infrastructure\database\migrations\versions\20261111_0002_auth_identity_rbac.py
  ..\backend\.venv\Scripts\pytest.exe -v

  # Start FastAPI HTTP server independently (http://127.0.0.1:8000)
  ..\backend\.venv\Scripts\uvicorn.exe app.main:app --host 127.0.0.1 --port 8000
  ```

### 7.2 Frontend Next.js Environment (`frontend/`)

The frontend runtime uses Next.js (`16.4.6`), React (`19.3.0`), TypeScript (strict mode), Tailwind CSS (`4.3.3`), a shadcn/ui-compatible configuration (`frontend/components.json` + `frontend/src/lib/utils.ts`), Lucide Icons (`lucide-react`), ESLint, and Prettier.

> **Windows Path Note (`&` Character):** Because this workspace folder name contains `&` (`Intelligent Project Knowledge Reconstruction & Handover Platform`), Windows `.cmd` shims inside `node_modules/.bin/*.cmd` split the path on `&` when invoked directly. All scripts in [`frontend/package.json`](../../frontend/package.json) invoke `node ./node_modules/...` directly so `npm run ...` works reliably on both Windows and Linux/Docker.

```powershell
cd frontend

# Install dependencies cleanly from package-lock.json
npm ci

# Verify formatting, linting, strict TypeScript, and production build
npm run format:check
npm run lint
npm run typecheck
npm run build

# Run the Next.js development server independently (http://localhost:3000)
npm run dev
```

- **Frontend Secret Hygiene**: Keep all secrets strictly in backend environment variables (`.env`). Only `NEXT_PUBLIC_API_BASE_URL` is intended for public client API routing.
