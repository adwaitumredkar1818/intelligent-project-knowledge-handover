"""Extract and re-index the Proposal PDF cleanly into the database and ChromaDB."""

import fitz  # PyMuPDF
import hashlib
from pathlib import Path
import uuid
import sys

# Ensure backend is on sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

from app.core.config import get_settings
from app.core.security import utc_now
from app.db.session import create_db_engine, create_session_factory, session_scope
from app.models.enums import (
    BackgroundJobStatus,
    BackgroundJobType,
    EvidenceIndexingStatus,
    EvidenceProcessingStatus,
    PageExtractionOutcome,
)
from app.models.evidence import EvidenceContent, EvidenceItem, EvidencePageContent
from app.models.job import BackgroundJob
from app.repositories.chunk import EvidenceChunkRepository
from app.repositories.evidence import EvidenceRepository
from app.services.chunking import ChunkingService
from app.services.embedding import OllamaEmbeddingService
from app.services.indexing_worker import IndexingWorkerService
from app.services.storage_factory import build_storage_backend
from app.services.vector_store import ChromaV2HttpVectorStore
from sqlalchemy import select

PDF_PATH = Path(r"C:\Users\Shubham\.gemini\antigravity\brain\f1e70b6b-09c5-4a12-819b-9553d61aef02\.user_uploaded\media_1794543741307_a86c0f13.pdf")
EVIDENCE_ID = uuid.UUID("2f858a12-c0c6-4ba7-9992-008fca250aa3")

settings = get_settings()
engine = create_db_engine(settings)
factory = create_session_factory(engine)

# 1. Read PDF
doc = fitz.open(PDF_PATH)
total_pages = len(doc)
full_text = []
pages_data = []

for i, page in enumerate(doc):
    page_text = page.get_text().strip()
    full_text.append(f"--- PAGE {i+1} ---\n{page_text}")
    pages_data.append((i + 1, page_text))

combined_text = "\n\n".join(full_text)
print(f"Read PDF: {total_pages} pages, {len(combined_text)} characters.")

# 2. Store encrypted file in storage backend
storage = build_storage_backend(settings)
raw_bytes = PDF_PATH.read_bytes()
file_hash = hashlib.sha256(raw_bytes).hexdigest()

with session_scope(factory) as session:
    ev = session.execute(select(EvidenceItem).where(EvidenceItem.id == EVIDENCE_ID)).scalar_one()
    
    # Write encrypted bytes to storage
    stored_meta = storage.store_encrypted_bytes(
        organisation_id=ev.organisation_id,
        project_id=ev.project_id,
        data=raw_bytes,
    )
    
    ev.storage_object_key = stored_meta.storage_object_key
    ev.storage_provider = stored_meta.storage_provider
    ev.encryption_algorithm = stored_meta.encryption_algorithm
    ev.encryption_key_id = stored_meta.encryption_key_id
    ev.content_hash = file_hash
    ev.file_size_bytes = len(raw_bytes)
    ev.page_count = total_pages
    ev.processing_status = EvidenceProcessingStatus.EXTRACTED.value
    ev.indexing_status = EvidenceIndexingStatus.QUEUED.value
    
    # Update EvidenceContent
    content = session.execute(select(EvidenceContent).where(EvidenceContent.evidence_id == ev.id)).scalar_one_or_none()
    if not content:
        content = EvidenceContent(
            evidence_id=ev.id,
            extracted_text=combined_text,
            char_count=len(combined_text),
            word_count=len(combined_text.split()),
        )
        session.add(content)
    else:
        content.extracted_text = combined_text
        content.char_count = len(combined_text)
        content.word_count = len(combined_text.split())

    # Clear and recreate pages
    session.query(EvidencePageContent).filter(EvidencePageContent.evidence_id == ev.id).delete()
    for p_num, p_text in pages_data:
        p_row = EvidencePageContent(
            evidence_id=ev.id,
            page_number=p_num,
            text_content=p_text,
            char_count=len(p_text),
            extraction_outcome=PageExtractionOutcome.DIGITAL_TEXT.value if p_text else PageExtractionOutcome.EMPTY.value,
            ocr_applied=False,
            ocr_truncated=False,
            structured_metadata={},
        )
        session.add(p_row)
        
    # Queue indexing job
    job = BackgroundJob(
        organisation_id=ev.organisation_id,
        project_id=ev.project_id,
        evidence_id=ev.id,
        triggered_by_user_id=ev.uploaded_by_user_id,
        job_type=BackgroundJobType.EVIDENCE_INDEXING.value,
        status=BackgroundJobStatus.QUEUED.value,
        priority=100,
        payload_json={"evidence_id": str(ev.id)},
    )
    session.add(job)
    session.commit()
    print("Updated EvidenceItem, EvidenceContent, EvidencePageContent and queued EVIDENCE_INDEXING job.")

# 3. Run Indexing Worker to embed and index PDF into ChromaDB
chunking_svc = ChunkingService(settings=settings.chunking)
embedding_svc = OllamaEmbeddingService(
    base_url=settings.ollama.base_url,
    model=settings.ollama.embedding_model,
    batch_size=settings.embedding.batch_size,
    expected_dimensions=settings.embedding.expected_dimensions,
    timeout_seconds=settings.embedding.timeout_seconds,
)
vector_store = ChromaV2HttpVectorStore(
    base_url=settings.chroma.base_url,
    tenant=settings.chroma.tenant,
    database=settings.chroma.database,
    collection_prefix=settings.chroma.collection_prefix,
    embedding_model=settings.ollama.embedding_model,
    index_version=settings.chroma.index_version,
    expected_dimensions=settings.embedding.expected_dimensions,
    auth_token=settings.chroma.auth_token.get_secret_value() if settings.chroma.auth_token else None,
    request_timeout_seconds=settings.chroma.request_timeout_seconds,
)
indexing_worker = IndexingWorkerService(
    session_factory=factory,
    chunking_service=chunking_svc,
    embedding_service=embedding_svc,
    vector_store=vector_store,
    ingestion_settings=settings.ingestion,
    extraction_settings=settings.extraction,
    llm_model_name=settings.ollama.llm_model,
    worker_id="pdf-index-worker",
)

indexing_worker.process_next_job()
print("PDF successfully indexed into ChromaDB!")
