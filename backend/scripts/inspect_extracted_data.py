import json
import os
import sys

sys.path.insert(0, os.path.abspath("."))
from app.core.config import get_settings
from app.db.session import create_db_engine
from sqlalchemy import text

settings = get_settings()
engine = create_db_engine(settings)

with engine.connect() as conn:
    print("================================================================================")
    print("DETAILED SAMPLES FROM JIRA, GITHUB, AND UPLOADED DOCUMENTS")
    print("================================================================================")

    print("\n--- JIRA ISSUES (Sample) ---")
    jira_items = conn.execute(text("""
        SELECT ei.id, ei.title, ei.source_external_id, ei.metadata_json, ec.chunk_text
        FROM evidence_items ei
        LEFT JOIN evidence_chunks ec ON ec.evidence_id = ei.id
        WHERE ei.source_provider = 'jira'
        LIMIT 4
    """)).fetchall()
    for j in jira_items:
        print(f"• Key/Title: {j.title} ({j.source_external_id})")
        if j.chunk_text:
            print(f"  Extracted Content: \"{j.chunk_text[:160].strip()}\"...")
        if j.metadata_json:
            print(f"  Metadata: {json.dumps(j.metadata_json)[:140]}...")

    print("\n--- GITHUB COMMITS & REPO DOCS (Sample) ---")
    gh_items = conn.execute(text("""
        SELECT ei.id, ei.title, ei.category, ei.source_external_id, ec.chunk_text
        FROM evidence_items ei
        LEFT JOIN evidence_chunks ec ON ec.evidence_id = ei.id
        WHERE ei.source_provider = 'github'
        LIMIT 4
    """)).fetchall()
    for g in gh_items:
        print(f"• [{g.category.upper()}] {g.title}")
        print(f"  External ID: {g.source_external_id}")
        if g.chunk_text:
            print(f"  Extracted Content: \"{g.chunk_text[:160].strip()}\"...")

    print("\n--- UPLOADED DOCUMENTS (Sample) ---")
    doc_items = conn.execute(text("""
        SELECT ei.id, ei.title, ei.category, ec.section_title, ec.page_number, ec.chunk_text
        FROM evidence_items ei
        JOIN evidence_chunks ec ON ec.evidence_id = ei.id
        WHERE ei.source_type = 'document_upload'
        LIMIT 4
    """)).fetchall()
    for d in doc_items:
        print(f"• [{d.category.upper()}] \"{d.title}\" | Section: {d.section_title or 'General'} (Page: {d.page_number})")
        if d.chunk_text:
            print(f"  Extracted Text: \"{d.chunk_text[:160].strip()}\"...")

    print("\n================================================================================")
