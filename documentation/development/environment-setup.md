# Environment Setup Guide

> **Current Phase Notice:** **Phase 2.6 (AI Knowledge Reconstruction & Structured Intelligence Extraction)** is complete alongside **Phases 2.1–2.5**: Docker infrastructure (**PostgreSQL** and **ChromaDB**), native Windows **Ollama** (`qwen3:8b`, `glm-ocr:latest`, `nomic-embed-text`), the Next.js TypeScript runtime (`frontend/`), the FastAPI backend foundation (`backend/app/`, `infrastructure/database/migrations/`), platform authentication & RBAC (`0002_auth_identity_rbac`), organisations & project workspaces (`0003_org_project_workspaces`), encrypted PDF/DOCX ingestion & GLM OCR (`0004_evidence_ingestion`), delegated per-user GitHub/Jira OAuth 2.0 connectors & sync execution (`0005_source_integrations`), chunking, PG `TSVECTOR`/`GIN` FTS, `nomic-embed-text`, ChromaDB HTTP v2 indexing & hybrid retrieval (`0006_evidence_chunks_and_fts`), and replaceable `StructuredLLMClient` (`OllamaLLMClient` / `qwen3:8b` with `OLLAMA_LLM_THINK=false`), fail-closed `NO EVIDENCE -> NO CLAIM` knowledge reconstruction (`ReconstructionWorkerService`), conservative deduplication, and staleness tracking (`0007_knowledge_reconstruction`) are implemented and verified. Knowledge relationships, verification review workflows, handover generation, and assistant synthesis belong to subsequent phases.

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
| `POSTGRES_HOST` | Backend / Worker / Infra | No | `localhost` | Hostname for local Docker Postgres (`localhost` from host, `postgres` in Docker); kept for Docker fallback when `DATABASE_URL` points to Supabase |
| `POSTGRES_PORT` | Backend / Worker / Infra | No | `5432` | Loopback host port bound by local Docker PostgreSQL (`127.0.0.1:${POSTGRES_PORT}:5432`) |
| `POSTGRES_DB` | Backend / Worker / Infra | No | `knowledge_handover` | Local Docker PostgreSQL database name (required by `docker-compose.yml`) |
| `POSTGRES_USER` | Backend / Worker / Infra | No | `postgres` | Local Docker PostgreSQL username (required by `docker-compose.yml`) |
| `POSTGRES_PASSWORD` | Backend / Worker / Infra | **Yes** | *(replace locally)* | Local Docker PostgreSQL password (required by `docker-compose.yml`; never commit) |
| `DATABASE_URL` | Backend / Worker / Alembic | **Yes** | `postgresql+psycopg://...` | Active SQLAlchemy 2.x + Psycopg 3 connection URL (points to Supabase Session Pooler or local Docker PostgreSQL; special password characters must be percent-encoded) |
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
| `GITHUB_AUTH_BASE_URL` | Backend | No | `https://github.com` | GitHub OAuth authorize & token exchange base URL |
| `GITHUB_API_BASE_URL` | Backend / Worker | No | `https://api.github.com` | GitHub REST API base URL |
| `GITHUB_CLIENT_ID` | Backend | No | *(empty)* | GitHub OAuth app client ID *(required only when `GITHUB_ENABLED=true`)* |
| `GITHUB_CLIENT_SECRET` | Backend | **Yes** | *(empty)* | GitHub OAuth app client secret *(required only when `GITHUB_ENABLED=true`)* |
| `GITHUB_REDIRECT_URI` | Backend | No | `http://localhost:8000/api/v1/integrations/github/callback` | GitHub delegated OAuth callback |
| `GITHUB_OAUTH_MODE` | Backend | No | `github_app` | OAuth app mode (`github_app` default least privilege vs `oauth_app`) |
| `GITHUB_OAUTH_SCOPES` | Backend | No | `read:user user:email` | Requested GitHub OAuth scopes when `GITHUB_OAUTH_MODE=oauth_app` |
| `GITHUB_ALLOW_CLASSIC_PRIVATE_REPO_SCOPE` | Backend | No | `false` | Explicitly strips classic write-capable `repo` scope unless opted in |
| `JIRA_ENABLED` | Backend / Worker | No | `false` | Enable Jira API integration (initial source priority when enabled) |
| `JIRA_AUTH_BASE_URL` | Backend | No | `https://auth.atlassian.com` | Atlassian OAuth 2.0 base URL |
| `JIRA_API_BASE_URL` | Backend | No | `https://api.atlassian.com` | Jira Cloud REST API base URL |
| `JIRA_CLIENT_ID` | Backend | No | *(empty)* | Jira OAuth 2.0 (3LO) client ID *(required only when `JIRA_ENABLED=true`)* |
| `JIRA_CLIENT_SECRET` | Backend | **Yes** | *(empty)* | Jira OAuth 2.0 (3LO) client secret *(required only when `JIRA_ENABLED=true`)* |
| `JIRA_REDIRECT_URI` | Backend | No | `http://localhost:8000/api/v1/integrations/jira/callback` | Jira delegated OAuth callback |
| `JIRA_OAUTH_SCOPES` | Backend | No | `read:jira-work read:jira-user offline_access` | Read-only Atlassian 3LO scopes requested during consent |
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
| `MAX_DOCUMENT_PAGES` | Backend / Worker | No | `200` | Maximum allowed page count for uploaded PDF documents |
| `OLLAMA_OCR_NUM_CTX` | Worker | No | `8192` | Explicit context window passed to Ollama `glm-ocr:latest` requests |
| `OLLAMA_OCR_NUM_PREDICT` | Worker | No | `4096` | Maximum tokens generated per page during OCR inference (triggers truncation flag if hit) |
| `OLLAMA_OCR_TIMEOUT_SECONDS` | Worker | No | `120` | HTTP timeout in seconds for each Ollama page OCR inference call |
| `OCR_RENDER_DPI` | Worker | No | `150` | Target DPI when rasterizing scanned/sparse-text PDF pages for OCR |
| `OCR_MAX_IMAGE_DIMENSION` | Worker | No | `2048` | Upper width/height pixel bound for rasterized page images sent to OCR |
| `OCR_MIN_TEXT_CHARS_PER_PAGE` | Worker | No | `40` | Minimum digital text chars per PDF page before an image-bearing page routes to OCR |
| `OCR_MAX_PAGES_PER_DOCUMENT` | Worker | No | `40` | Maximum OCR-processed pages per document before remaining sparse pages record `skipped_limit` (`partially_extracted`) |
| `WORKER_POLL_INTERVAL_SECONDS` | Worker | No | `5` | Polling interval (seconds) for the PostgreSQL-backed Python worker |
| `WORKER_MAX_ATTEMPTS` | Backend / Worker | No | `3` | Maximum retry attempts before a failed job transitions to `failed` |
| `WORKER_RETRY_BASE_SECONDS` | Worker | No | `15` | Base backoff interval in seconds (`base * 2^(attempt-1)`) before retrying retryable failures |
| `WORKER_LEASE_SECONDS` | Worker | No | `300` | Job lock lease duration in seconds before stale `running` jobs are reclaimed |
| `OAUTH_STATE_EXPIRE_MINUTES` | Backend | No | `10` | Lifetime (minutes) of single-use PKCE `oauth_states` records |
| `INTEGRATION_HTTP_TIMEOUT_SECONDS` | Backend / Worker | No | `20` | HTTPX timeout in seconds for external GitHub & Jira API requests |
| `INTEGRATION_SYNC_MAX_ITEMS_PER_RUN` | Backend / Worker | No | `250` | Upper cap on synced items discovered per source sync run |
| `INTEGRATION_ALLOWED_POST_AUTH_REDIRECTS` | Backend | No | *(empty)* | Comma-separated allowlisted post-OAuth redirect URL prefixes/origins (alongside `CORS_ALLOWED_ORIGINS`) |
| `GITHUB_DEFAULT_COMMITS_LIMIT` | Worker | No | `50` | Default maximum commits ingested per GitHub sync run |
| `GITHUB_DEFAULT_DOCS_LIMIT` | Worker | No | `20` | Default maximum README/Markdown/ADR docs ingested per GitHub sync run |
| `POSTGRES_SSL_MODE` | Backend / Worker / Alembic | No | `prefer` | PostgreSQL TLS mode (`prefer` for local Docker; `require` required for Supabase PostgreSQL, or `verify-full` with a Supabase root CA certificate) |
| `CHROMA_AUTH_TOKEN` | Backend / Worker / Infra | **Yes** | *(empty)* | Reserved for reverse-proxy/gateway authentication in shared deployments *(not used natively by local `chromadb/chroma:latest` 1.4.4)* |
| `CHROMA_TENANT` | Backend / Worker | No | `default_tenant` | ChromaDB HTTP v2 tenant scope for vector collection API calls |
| `CHROMA_DATABASE` | Backend / Worker | No | `default_database` | ChromaDB HTTP v2 database scope for vector collection API calls |
| `CHROMA_INDEX_VERSION` | Backend / Worker | No | `v1` | Index schema/chunking version suffix embedded in Chroma collection name (`${CHROMA_COLLECTION_PREFIX}_evidence_chunks_${OLLAMA_EMBEDDING_MODEL}_${CHROMA_INDEX_VERSION}`) |
| `CHROMA_REQUEST_TIMEOUT_SECONDS` | Backend / Worker | No | `15.0` | HTTP timeout in seconds for ChromaDB HTTP v2 upsert, query, delete, and health calls |
| `CHUNK_TARGET_CHARS` | Worker | No | `1100` | Target chunk size in characters (~340 tokens for `nomic-embed-text`) |
| `CHUNK_MAX_CHARS` | Worker | No | `1400` | Maximum chunk size ceiling before sentence/paragraph splitting (`CHUNK_MIN_CHARS <= TARGET <= MAX`) |
| `CHUNK_OVERLAP_CHARS` | Worker | No | `150` | Character overlap carried between consecutive split text segments (`< CHUNK_TARGET_CHARS`) |
| `CHUNK_MIN_CHARS` | Worker | No | `120` | Minimum trailing chunk threshold before merging short adjacent segments |
| `EMBEDDING_BATCH_SIZE` | Worker | No | `8` | Number of chunks embedded per Ollama `/api/embed` batch call |
| `EMBEDDING_EXPECTED_DIMENSIONS` | Backend / Worker | No | `768` | Expected embedding vector dimensionality enforced for `nomic-embed-text` compatibility checks |
| `EMBEDDING_TIMEOUT_SECONDS` | Backend / Worker | No | `60.0` | HTTP timeout in seconds for Ollama `/api/embed` calls |
| `RETRIEVAL_DEFAULT_TOP_K` | Backend | No | `10` | Default result limit returned by `POST /projects/{project_id}/search` |
| `RETRIEVAL_MAX_TOP_K` | Backend | No | `50` | Maximum allowed `top_k` per search request |
| `RETRIEVAL_CANDIDATE_MULTIPLIER` | Backend | No | `4` | Per-channel candidate overfetch factor prior to RRF fusion & PG ACL post-revalidation |
| `RETRIEVAL_MIN_CANDIDATE_LIMIT` | Backend | No | `40` | Floor on per-channel FTS / vector candidate fetch count |
| `RETRIEVAL_RRF_K` | Backend | No | `60` | Reciprocal Rank Fusion dampening constant (`weight / (k + rank)`) |
| `RETRIEVAL_SEMANTIC_WEIGHT` | Backend | No | `1.0` | Weight applied to ChromaDB semantic rank during RRF fusion |
| `RETRIEVAL_KEYWORD_WEIGHT` | Backend | No | `1.0` | Weight applied to PostgreSQL FTS rank during RRF fusion |
| `RETRIEVAL_MIN_SEMANTIC_SIMILARITY` | Backend | No | `0.15` | Minimum cosine similarity filter before RRF fusion *(subject to Phase 8 real-evidence calibration)* |
| `RETRIEVAL_MIN_KEYWORD_SCORE` | Backend | No | `0.0` | Minimum normalised PG FTS keyword score threshold *(subject to Phase 8 calibration)* |
| `RETRIEVAL_MIN_HYBRID_SCORE` | Backend | No | `0.0` | Minimum normalised hybrid RRF score threshold *(subject to Phase 8 calibration)* |
| `OLLAMA_LLM_NUM_CTX` | Worker | No | `8192` | Explicit context window (`num_ctx`) passed to Ollama `qwen3:8b` extraction requests |
| `OLLAMA_LLM_NUM_PREDICT` | Worker | No | `2048` | Maximum generated tokens (`num_predict`) per Ollama extraction batch (checked for truncation) |
| `OLLAMA_LLM_TEMPERATURE` | Worker | No | `0.1` | Low sampling temperature for structured JSON knowledge extraction |
| `OLLAMA_LLM_TIMEOUT_SECONDS` | Worker | No | `120.0` | HTTP timeout in seconds for each Ollama `/api/chat` structured extraction call |
| `OLLAMA_LLM_THINK` | Worker | No | `false` | Disables Qwen3 reasoning trace tokens via Ollama `think: false` for fast strict JSON responses |
| `EXTRACTION_PROMPT_VERSION` | Worker | No | `p2.6-v1` | Prompt contract version recorded on `knowledge_extraction_runs` and `knowledge_items` |
| `EXTRACTION_MAX_RETRIES` | Worker | No | `2` | Invalid-JSON repair prompt retry budget per batch prior to failing an item |
| `EXTRACTION_MAX_CHUNKS_PER_BATCH` | Worker | No | `6` | Maximum chunks from a single evidence item grouped into one LLM extraction batch |
| `EXTRACTION_MAX_CHARS_PER_BATCH` | Worker | No | `5500` | Maximum prompt character payload per extraction batch within `OLLAMA_LLM_NUM_CTX` |
| `EXTRACTION_AUTO_REEXTRACT_ON_UPDATE` | Worker | No | `false` | When `true`, automatically queues `knowledge_reconstruction` after re-indexing marks existing claims stale |

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

#### 5.1.1 Managed Supabase PostgreSQL Configuration & Local Fallback

FastAPI, the background worker, and Alembic all connect through `DATABASE_URL` (requiring the `postgresql+psycopg://` SQLAlchemy + Psycopg 3 scheme) and `POSTGRES_SSL_MODE`.

- **Configuring Supabase PostgreSQL in root `.env`**:
  1. Use the Supabase **Shared Pooler (Session mode, port `5432`)** connection string converted to the `postgresql+psycopg://` driver prefix:
     ```dotenv
     DATABASE_URL=postgresql+psycopg://postgres.<project-ref>:<url-encoded-password>@<region>.pooler.supabase.com:5432/postgres
     POSTGRES_SSL_MODE=require
     ```
  2. **Percent-encoding special characters in passwords:** Characters such as `@`, `#`, `:`, `/`, `?`, and `%` break URL parsing unless percent-encoded (for example, `#` -> `%23`, `@` -> `%40`). You can generate a safe encoded string locally without printing it to logs:
     ```powershell
     .\backend\.venv\Scripts\python.exe -c "import getpass, urllib.parse; print(urllib.parse.quote(getpass.getpass('DB password: '), safe=''))"
     ```
  3. **Keep local Docker fallback intact:** Leave `POSTGRES_HOST`, `POSTGRES_PORT`, `POSTGRES_DB`, `POSTGRES_USER`, and `POSTGRES_PASSWORD` populated in `.env` so `docker compose --env-file .env -f infrastructure/docker/docker-compose.yml` continues to run `ipkrh-postgres` cleanly without modifying `ipkrh_postgres_data`. To switch back to local Docker PostgreSQL, set:
     ```dotenv
     DATABASE_URL=postgresql+psycopg://<POSTGRES_USER>:<POSTGRES_PASSWORD>@localhost:5432/<POSTGRES_DB>
     POSTGRES_SSL_MODE=prefer
     ```
- **SSL Requirements**:
  - `POSTGRES_SSL_MODE=require` must be set when connecting to Supabase PostgreSQL (`backend/app/db/session.py` automatically passes `sslmode` and `connect_timeout=5` to Psycopg 3 unless overridden in `DATABASE_URL`).
  - `require` enforces TLS encryption over the network; note that `verify-ca` / `verify-full` additionally require supplying Supabase's root CA certificate (`sslrootcert`) because Supabase's pooler certificate chain is signed by Supabase's own CA rather than the OS default trust store.
  - Production mode (`APP_ENV=production`) explicitly rejects `POSTGRES_SSL_MODE=disable` and `?sslmode=disable`.
- **Read-Only Connection & SSL Verification**:
  - Run the repository verification script after updating `.env` (never prints credentials or URLs):
    ```powershell
    .\backend\.venv\Scripts\python.exe scripts\verify_db_connection.py --require-ssl
    ```
  - This executes `SELECT current_database(), current_user, version(), now();`, checks `pgconn.ssl_in_use`, and reports the current `alembic_version` without modifying any database state.
- **Migration Connection Requirements (Alembic Safety)**:
  - [`infrastructure/database/migrations/env.py`](../../infrastructure/database/migrations/env.py) loads `DATABASE_URL` and `POSTGRES_SSL_MODE` dynamically via `Settings` and uses `sqlalchemy.pool.NullPool` so migration connections close immediately after completion.
  - Always point Alembic at Supabase **Session mode (port `5432`)** or a **Direct PostgreSQL connection**, **never** Transaction pooler mode (port `6543`), because Alembic relies on transactional DDL, session-scoped locks, and Psycopg 3 server-side prepared statements.
  - Never run `alembic upgrade head`, stamp `alembic_version`, or alter production tables against a live Supabase project until connectivity is verified and schema migration approval is confirmed.

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
python -c "import fastapi, uvicorn, pydantic, pydantic_settings, sqlalchemy, psycopg, alembic, httpx, dotenv, jwt, pwdlib, pymupdf, docx, cryptography; print('Backend baseline imports OK')"
```

- **Core Runtime Dependencies** (`backend/requirements.txt`): `fastapi`, `uvicorn[standard]`, `pydantic`, `pydantic-settings`, `sqlalchemy`, `psycopg[binary]`, `alembic`, `httpx`, `python-dotenv`, `pyjwt`, `pwdlib[argon2]`, plus Phase 2.4A document/crypto packages `pymupdf`, `python-docx`, `python-multipart`, and `cryptography`.
- **Separated Optional Dependency Groups** (do **not** install prematurely; install only as their phases start):
  - `documents`: promoted into core dependencies in Phase 2.4A (`pymupdf`, `python-docx`, `python-multipart`)
  - `embeddings-rag`: `chromadb-client`
  - `integrations-security`: `cryptography` promoted in Phase 2.4A for at-rest file encryption; reserve for future OAuth/connector dependencies
  - `worker`: lightweight worker utilities *(no Redis or Celery)*
  - `dev`: `pytest`, `ruff`, `mypy` *(installed for verification)*
- **Re-locking Base Dependencies** (when updating `backend/pyproject.toml`):
  ```powershell
  uv pip compile backend\pyproject.toml --python-version 3.11 -o backend\requirements.txt
  ```
# - **Running the FastAPI Application, Composite Ingestion/Sync/Indexing/Reconstruction Worker & Database Checks (Phase 2.6)**:
  ```powershell
  cd backend

  # Validate Alembic state & apply migrations (requires healthy ipkrh-postgres)
  ..\backend\.venv\Scripts\alembic.exe upgrade head
  ..\backend\.venv\Scripts\alembic.exe current
  ..\backend\.venv\Scripts\alembic.exe check

  # Run lint, strict typing, and test suite
  ..\backend\.venv\Scripts\ruff.exe check app tests ..\infrastructure\database\migrations
  ..\backend\.venv\Scripts\mypy.exe app tests ..\infrastructure\database\migrations\env.py ..\infrastructure\database\migrations\versions\20261111_0002_auth_identity_rbac.py ..\infrastructure\database\migrations\versions\20261111_0003_org_project_workspaces.py ..\infrastructure\database\migrations\versions\20261111_0004_evidence_ingestion.py ..\infrastructure\database\migrations\versions\20261111_0005_source_integrations.py ..\infrastructure\database\migrations\versions\20261112_0006_evidence_chunks_and_fts.py ..\infrastructure\database\migrations\versions\20261112_0007_knowledge_reconstruction.py
  ..\backend\.venv\Scripts\pytest.exe -v

  # Run lightweight PostgreSQL-backed CompositeWorkerService (`document_ingestion` + `source_sync` + `evidence_indexing` + `knowledge_reconstruction`)
  ..\backend\.venv\Scripts\python.exe -m app.worker --once
  ..\backend\.venv\Scripts\python.exe -m app.worker

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
