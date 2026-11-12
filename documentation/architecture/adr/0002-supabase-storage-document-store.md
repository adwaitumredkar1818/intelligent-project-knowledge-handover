# ADR 0002: Supabase Storage as Private Document Store

## Status
Accepted (Updated in Phase 2.9 for Dual-Provider Selection & Backend-Mediated Streaming)

## Context
Project knowledge reconstruction requires ingesting and preserving original PDF, DOCX, and scanned technical documents. Local development uses `LocalPrivateStorageBackend` (`UPLOAD_STORAGE_PATH`), whereas persistent cloud-backed object storage requires a private Supabase Storage bucket (`project-evidence`) without altering PostgreSQL provenance metadata, background worker decryption, or read-time source ACL enforcement.

## Decision
1. **Explicit Storage Provider Selection (`STORAGE_PROVIDER`)**: FastAPI (`deps.py`) and the background worker (`worker.py`) construct storage via the shared `build_storage_backend()` factory:
   - `local_encrypted` (default): local encrypted directory under `UPLOAD_STORAGE_PATH` (`encryption_key_id = "local-v1"`).
   - `supabase_storage`: private Supabase Storage bucket configured via `SUPABASE_URL`, server-only `SUPABASE_SERVICE_ROLE_KEY`, and `SUPABASE_STORAGE_BUCKET` (default `project-evidence`; `encryption_key_id = "supabase-v1"`). Publishable/anon keys (`sb_publishable_*`) are explicitly rejected.
2. **Strictly Private Bucket**: The `project-evidence` bucket must be created with public access disabled and no anonymous read/write RLS policies. FastAPI and the worker authenticate strictly via `SUPABASE_SERVICE_ROLE_KEY` over HTTPS (`x-upsert: false`).
3. **Canonical Application-Level AES-256-GCM Encryption Preserved**: Both storage backends reuse a single canonical AES-256-GCM + HKDF-SHA256 envelope format (`IPKRH1\x01` + 12-byte random nonce + ciphertext + 16-byte GCM tag; `35` bytes total overhead) derived from `FILE_ENCRYPTION_KEY`, with AAD bound to `<organisation_id>:<project_id>:<storage_object_key>`. Ciphertext size and `key_id` are verified on decryption alongside HTTP `Content-Length`.
4. **Opaque Object Keys**: Object paths use opaque UUID segments only:
   `<organisation_id>/<project_id>/<object_uuid>.enc`
   Raw user filenames remain strictly in PostgreSQL `evidence_items.original_filename`. Internal `storage_provider` and `storage_object_key` fields are excluded from API responses.
5. **Backend-Mediated Streaming Downloads Only (No Signed URLs)**: Neither public URLs nor Supabase Storage signed URLs are generated or returned to clients. All downloads stream plaintext bytes exclusively through `GET /api/v1/evidence/{evidence_id}/download` after FastAPI JWT verification, tenant isolation, and PostgreSQL source ACL validation (`SourceAccessPolicyService`).

## Consequences
- Confidential documents remain AES-256-GCM encrypted at rest even inside Supabase Storage.
- Zero Supabase Storage credentials or signed URLs are ever exposed to browser JavaScript or Next.js public env vars.
- Both FastAPI and the Python worker remain storage-agnostic through `StorageBackend` and `build_storage_backend()`.
