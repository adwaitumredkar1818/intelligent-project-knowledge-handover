# Background Worker Architecture — The Handover Platform

## 1. Overview

The platform uses a dedicated, lightweight Python background worker process backed by PostgreSQL durable job records (`FOR UPDATE SKIP LOCKED`).

```
+-------------------------------------------------------------+
|                      FastAPI Web App                        |
|   Creates Ingestion / Extraction / OCR Jobs in PostgreSQL   |
+------------------------------+------------------------------+
                               |
                               v
+-------------------------------------------------------------+
|                  PostgreSQL (Canonical)                     |
|     Table: `evidence_processing_jobs` / `reconstruction_jobs`|
|          Status: queued -> processing -> completed / failed |
+------------------------------+------------------------------+
                               |
                               | FOR UPDATE SKIP LOCKED
                               v
+-------------------------------------------------------------+
|                 Lightweight Python Worker                   |
|   - Concurrency bounds: OLLAMA_MAX_CONCURRENT_AI_JOBS=1     |
|   - Exponential backoff retry on transient errors           |
|   - Heartbeat tracking & stuck-job auto-recovery            |
+-------------------------------------------------------------+
```

## 2. Key Architecture Directives

1. **No External Message Brokers**: Celery, Redis Queues, and Kafka are intentionally omitted to avoid dual-state complexity and maintain strict audit trails in PostgreSQL.
2. **Transaction Isolation**: Jobs are claimed using atomic `SKIP LOCKED` queries, allowing multiple worker instances to run concurrently without duplicate execution.
3. **Inference Serialization**: Hardware-aware inference queue ensures local GPU (e.g., RTX 4050 6GB VRAM) never experiences VRAM out-of-memory errors between Qwen3 8B and GLM OCR models.
4. **Stuck Job Recovery**: Periodic background reap sweep recovers orphaned jobs whose heartbeats exceeded the maximum timeout.
