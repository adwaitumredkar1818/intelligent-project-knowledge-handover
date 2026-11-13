"""Add 8 canonical knowledge domains, primary/secondary domain columns, and expanded support types.

Revision ID: 0010_knowledge_domains
Revises: 0009_supabase_and_vector_indexes
Create Date: 2026-11-13 04:30:00.000000
"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "0010_knowledge_domains"
down_revision: Union[str, None] = "0009_supabase_and_vector_indexes"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Allowed categories and domain identifiers in knowledge_items
_ALLOWED_CATEGORIES = (
    # Phase 2.6 legacy category names
    "'decisions_rationale'",
    "'work_items'",
    "'responsibilities_ownership'",
    "'technical_architecture'",
    "'bugs_blockers_risks'",
    "'dependencies'",
    # Lowercase canonical domain names
    "'project_overview_context'",
    "'work_progress'",
    "'architecture_technical'",
    "'dependencies_relationships'",
    "'risks_blockers_questions'",
    "'operational_historical'",
    # Uppercase canonical domain names
    "'PROJECT_OVERVIEW_CONTEXT'",
    "'DECISIONS_RATIONALE'",
    "'ARCHITECTURE_TECHNICAL'",
    "'WORK_PROGRESS'",
    "'RESPONSIBILITIES_OWNERSHIP'",
    "'DEPENDENCIES_RELATIONSHIPS'",
    "'RISKS_BLOCKERS_QUESTIONS'",
    "'OPERATIONAL_HISTORICAL'",
)

_ALLOWED_SUPPORT_TYPES = (
    "'direct'",
    "'direct_support'",
    "'corroborated'",
    "'corroboration'",
    "'interpretation'",
    "'context'",
    "'uncertain'",
    "'contradiction'",
)


def upgrade() -> None:
    # 1. Add primary_domain and secondary_domains to knowledge_items if not present
    op.execute(
        sa.text("""
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.columns 
                WHERE table_name='knowledge_items' AND column_name='primary_domain'
            ) THEN
                ALTER TABLE knowledge_items ADD COLUMN primary_domain VARCHAR(64);
            END IF;
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.columns 
                WHERE table_name='knowledge_items' AND column_name='secondary_domains'
            ) THEN
                ALTER TABLE knowledge_items ADD COLUMN secondary_domains JSONB NOT NULL DEFAULT '[]'::jsonb;
            END IF;
        END $$;
        """)
    )

    op.execute(
        sa.text("""
        CREATE INDEX IF NOT EXISTS ix_knowledge_items_project_primary_domain
        ON knowledge_items (project_id, primary_domain);
        """)
    )

    # 2. Update category check constraint on knowledge_items using explicit SQL
    category_list_sql = ", ".join(_ALLOWED_CATEGORIES)
    op.execute(
        sa.text("""
        ALTER TABLE knowledge_items DROP CONSTRAINT IF EXISTS ck_knowledge_items_knowledge_item_category;
        """)
    )
    op.execute(
        sa.text(f"""
        ALTER TABLE knowledge_items ADD CONSTRAINT ck_knowledge_items_knowledge_item_category
        CHECK (category IN ({category_list_sql}));
        """)
    )

    # 3. Backfill primary_domain for any existing records based on category
    op.execute(
        sa.text("""
        UPDATE knowledge_items
        SET primary_domain = CASE
            WHEN category IN ('decisions_rationale', 'DECISIONS_RATIONALE') THEN 'DECISIONS_RATIONALE'
            WHEN category IN ('work_items', 'work_progress', 'WORK_PROGRESS') THEN 'WORK_PROGRESS'
            WHEN category IN ('responsibilities_ownership', 'RESPONSIBILITIES_OWNERSHIP') THEN 'RESPONSIBILITIES_OWNERSHIP'
            WHEN category IN ('technical_architecture', 'architecture_technical', 'ARCHITECTURE_TECHNICAL') THEN 'ARCHITECTURE_TECHNICAL'
            WHEN category IN ('bugs_blockers_risks', 'risks_blockers_questions', 'RISKS_BLOCKERS_QUESTIONS') THEN 'RISKS_BLOCKERS_QUESTIONS'
            WHEN category IN ('dependencies', 'dependencies_relationships', 'DEPENDENCIES_RELATIONSHIPS') THEN 'DEPENDENCIES_RELATIONSHIPS'
            WHEN category IN ('project_overview_context', 'PROJECT_OVERVIEW_CONTEXT') THEN 'PROJECT_OVERVIEW_CONTEXT'
            WHEN category IN ('operational_historical', 'OPERATIONAL_HISTORICAL') THEN 'OPERATIONAL_HISTORICAL'
            ELSE category
        END
        WHERE primary_domain IS NULL;
        """)
    )

    # 4. Update support_type check constraint on knowledge_evidence_links using explicit SQL
    support_list_sql = ", ".join(_ALLOWED_SUPPORT_TYPES)
    op.execute(
        sa.text("""
        ALTER TABLE knowledge_evidence_links DROP CONSTRAINT IF EXISTS ck_knowledge_evidence_links_knowledge_evidence_link_sup_cf43;
        ALTER TABLE knowledge_evidence_links DROP CONSTRAINT IF EXISTS ck_knowledge_evidence_links_knowledge_evidence_link_support_type;
        """)
    )
    op.execute(
        sa.text(f"""
        ALTER TABLE knowledge_evidence_links ADD CONSTRAINT ck_knowledge_evidence_links_knowledge_evidence_link_support_type
        CHECK (support_type IN ({support_list_sql}));
        """)
    )


def downgrade() -> None:
    # 1. Restore old support_type constraint
    op.execute(
        sa.text("""
        ALTER TABLE knowledge_evidence_links DROP CONSTRAINT IF EXISTS ck_knowledge_evidence_links_knowledge_evidence_link_support_type;
        ALTER TABLE knowledge_evidence_links ADD CONSTRAINT ck_knowledge_evidence_links_knowledge_evidence_link_sup_cf43
        CHECK (support_type IN ('direct', 'corroborated', 'interpretation', 'uncertain'));
        """)
    )

    # 2. Restore old category constraint
    op.execute(
        sa.text("""
        ALTER TABLE knowledge_items DROP CONSTRAINT IF EXISTS ck_knowledge_items_knowledge_item_category;
        ALTER TABLE knowledge_items ADD CONSTRAINT ck_knowledge_items_knowledge_item_category
        CHECK (category IN ('decisions_rationale', 'work_items', 'responsibilities_ownership', 'technical_architecture', 'bugs_blockers_risks', 'dependencies'));
        """)
    )

    # 3. Drop primary_domain and secondary_domains
    op.execute(
        sa.text("""
        DROP INDEX IF EXISTS ix_knowledge_items_project_primary_domain;
        ALTER TABLE knowledge_items DROP COLUMN IF EXISTS secondary_domains;
        ALTER TABLE knowledge_items DROP COLUMN IF EXISTS primary_domain;
        """)
    )
