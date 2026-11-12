# ADR 0002: Supabase Storage as Private Document Store

## Status
Accepted

## Context
Project knowledge reconstruction requires ingesting and preserving original PDF, DOCX, and other technical documentation files. Originally, these files were stored on local disk under `backend/data/uploads`. To provide robust, scalable, cloud-backed object storage while preserving strict privacy, Supabase Storage is designated as the private document object store.

## Decision
1. **Private Bucket**: All documents are stored in a private Supabase Storage bucket (`project-evidence`). No public access is permitted.
2. **FastAPI Mediation**: Document uploads and downloads flow through FastAPI. The frontend never directly accesses Supabase Storage with service-role keys.
3. **Application-Level Encryption Preserved**: The existing application-level AES-256-GCM encryption is retained. Uploaded files are encrypted before persisting to Supabase Storage and decrypted during ingestion processing or authenticated download streaming.
4. **Opaque Object Paths**: Object paths follow the convention:
   `organisations/{org_uuid}/projects/{project_uuid}/evidence/{evidence_uuid}/{opaque_uuid}.enc`
   Raw user filenames are stored only in PostgreSQL evidence metadata.
5. **Short-Lived Signed URLs / Streaming**: Downloads and previews require explicit project and evidence permission verification before generating short-lived (e.g. 60-second) signed URLs or direct streaming.

## Consequences
- Protects confidential organizational documents even against direct bucket scanning.
- Decouples storage persistence from host container filesystems.
