# Memory Optimization & Resource Bounds — The Handover Platform

## 1. Principles of Deterministic Resource Consumption

The Handover platform is engineered to run reliably on developer workstations (Windows 11 with 6GB-8GB VRAM GPUs) as well as containerized cloud instances.

## 2. Implemented Memory Protections

### 1. Bounded Streaming File Ingestion
- Uploaded PDF, DOCX, and text files are processed via streaming chunks (64KB buffer) rather than reading entire gigabyte-scale documents into memory.
- Text extraction pages are processed sequentially with PyMuPDF, releasing page text structures promptly.

### 2. Batch Embedding Bounds
- The `OllamaEmbeddingService` enforces a strict batch size (`batch_size=8`) and deduplicates chunks via SHA-256 before generating embeddings.
- Identical text chunks across documents or re-indexed runs are fulfilled directly from Redis, bypassing Ollama memory allocation and GPU compute.

### 3. Redis Memory Limits
- Redis is configured with `maxmemory 256mb` and `maxmemory-policy allkeys-lru`.
- This ensures Redis never exceeds its allotted container memory and automatically evicts oldest cache keys during peak load.

### 4. Connection Pool Boundaries
- Database connections: bounded Psycopg 3 connection pool (`max_overflow=10`, `pool_size=20`).
- Redis connections: bounded connection pool (`max_connections=20`, `socket_timeout=2.0s`).
