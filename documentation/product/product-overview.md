# The Handover — Product Overview

## 1. Product Identity
- **Product Name**: The Handover
- **Formal Product Description**: An Intelligent Project Knowledge Reconstruction & Handover Platform
- **Tagline**: Prevent Critical Knowledge From Leaving With People.
- **Application Slug**: `the-handover`
- **Application Name Setting**: `APP_NAME=The Handover`

---

## 2. Official Hackathon Problem Statement
When employees, researchers, developers, volunteers, or student team members leave a project, critical organisational knowledge frequently disappears with them. While traditional documentation may exist, the reasoning behind architecture and decisions, unfinished work, dependencies, recurring problems, blockers, and important operational contacts are scattered across:
- Git repositories (commits, diffs, branches, pull requests, code reviews)
- Task boards and issue tracking systems (Jira tasks, stories, bugs, epics, changelogs)
- Communication channels (discussions, meeting notes, incident reports)
- Technical documentation (architecture design records, specifications)
- Uploaded unstructured documents (PDF manuals, DOCX handbooks, scanned documents)

Traditional handover processes rely on manual exit memos and unstructured exit interviews. These fail because departing members lack the time or comprehensive recall to document every technical nuance, while incoming successors are overwhelmed with fragmented, context-free archives.

---

## 3. Product Mission & Value Proposition
**The Handover** is an organisational knowledge reconstruction platform. It is not another generic document storage bucket, issue tracker, or hallucinating conversational chatbot. Its objective is to connect authorised organisational sources, extract fragmented activity records, preserve cryptographic and source-level provenance, reconstruct latent relationships, surface uncertainties and conflicts, enable rigorous human verification, and compile role-appropriate handover packages for successors.

### Core Workflow
```text
CONNECT  ──▶  RECONSTRUCT  ──▶  VERIFY  ──▶  REVIEW  ──▶  HANDOVER
```

1. **CONNECT**: Authorise and ingest project records from GitHub, Jira, optional Slack (subject to feasibility, scopes, and retention), and uploaded documents (PDF, DOCX, scanned documents with OCR).
2. **RECONSTRUCT**: Store canonical records in PostgreSQL, index semantic vectors in ChromaDB (`nomic-embed-text`), extract candidate findings across eight knowledge domains using local Ollama (`qwen3:8b`), and map relationships.
3. **VERIFY**: Run automated consistency, attribution, conflict detection, and missing-information checks.
4. **REVIEW**: Authorised human reviewers (Tech Leads, Project Managers) inspect evidence in the Verification Center, resolve discrepancies, and promote candidates to Human-Verified Knowledge.
5. **HANDOVER**: Compile structured handover packages with readiness checklists, assign ownership to successors, obtain designated human sign-off, and enable successors to query project knowledge with evidence attribution.

---

## 4. Eight Core Knowledge Domains
The platform reconstructs and organises project state across eight domains:
1. **Decisions and their rationale**: Why specific architectures, libraries, or patterns were chosen over alternatives.
2. **Technical and architectural knowledge**: Component designs, data flows, API contracts, deployment topology, and constraints.
3. **Completed and unfinished work**: Shipped features, open PRs, pending refactors, technical debt, and backlog items.
4. **Responsibilities and ownership**: Who maintains specific modules, who acts as primary contact, and operational roles.
5. **Dependencies**: External APIs, internal shared services, runtime libraries, and third-party vendor dependencies.
6. **Bugs, blockers, and risks**: Known production vulnerabilities, unresolved defects, stability risks, and performance bottlenecks.
7. **Operational procedures**: Runbooks, deployment checklists, credential rotation, debugging guidelines, and incident playbooks.
8. **Historical discussions and context**: Key discussions, discarded proposals, trade-off debates, and evolution rationale.

---

## 5. Target User Types & Journeys

| User Type | Responsibilities & User Journey |
| :--- | :--- |
| **Departing Employee / Knowledge Owner** | Selects project, identifies ownership and responsibilities, authorises relevant sources (GitHub repos, Jira projects), uploads local notes/docs, responds to missing knowledge prompts, adds context. |
| **Incoming Employee / Successor** | Receives approved handover package, navigates project overview, inspects completed/pending work, reviews technical decisions, queries the evidence-grounded Project Knowledge Assistant, acknowledges receipt. |
| **Project Manager** | Creates project workspace, configures team members and roles, configures transition participants (departing member & successor), monitors connected source health, tracks handover readiness. |
| **Technical Lead / Reviewer** | Inspects candidate findings, validates technical decisions, examines conflicts and risk indicators, verifies supporting evidence links, approves or rejects handover packages. |
| **Organisation Administrator** | Manages multi-tenant organisation settings, enforces role-based access control (RBAC), manages global integrations and source permissions, audits system logs. |

---

## 6. Technology Architecture Baseline
- **Backend API**: Python 3.11, FastAPI, Pydantic v2, SQLAlchemy 2.x, Psycopg 3, HTTPX.
- **Structured Database**: PostgreSQL 16 (canonical store for all entities, relationships, FTS, audit logs, job records).
- **Vector Database**: ChromaDB (dedicated HTTP server mode, secondary rebuildable index).
- **Local AI & OCR**: Native Windows Ollama runtime (`qwen3:8b` for extraction/RAG, `nomic-embed-text` for 768-dim embeddings, `glm-ocr:latest` for scanned PDF pages).
- **Document Processing**: PyMuPDF for native text/table extraction, `python-docx` for Word documents, AES-encrypted private storage.
- **Frontend (Deferred)**: Next.js, React, TypeScript, Tailwind CSS, Lucide Icons, React Flow.
- **Background Worker**: Lightweight Python worker process backed by PostgreSQL job records (no Redis/Celery).

---

## 7. Product Boundaries & Non-Goals
- **Not a Replacement for Git or Jira**: The Handover aggregates and analyzes history; it does not replace source control or daily sprint tracking.
- **Not an Unsupervised AI Decision-Maker**: The LLM never approves handovers, decides official task status, overrides permissions, or fabricates facts without supporting evidence.
- **Not a Public Document Host**: Files are stored in encrypted private storage outside web-accessible roots.
- **Strict Permission Boundaries**: Project membership != Source access. Private source data is never leaked to project members lacking source credentials.
