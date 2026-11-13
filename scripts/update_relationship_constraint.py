"""Update check constraint ck_relationship_type_valid on knowledge_relationships."""

from app.core.config import get_settings
from app.db.session import create_db_engine, create_session_factory, session_scope
from app.models.enums import RelationshipType
from sqlalchemy import text

settings = get_settings()
engine = create_db_engine(settings)
factory = create_session_factory(engine)

# Verbose legacy types
VERBOSE_TYPES = [
    "DECISION_REFERENCED_IN_DISCUSSION", "DECISION_RECORDED_IN_DOCUMENT",
    "DECISION_IMPLEMENTED_BY", "DECISION_AFFECTS_COMPONENT", "DECISION_SUPERSEDES",
    "DECISION_CONFLICTS_WITH", "WORK_ITEM_TRACKED_BY", "WORK_ITEM_IMPLEMENTED_BY",
    "WORK_ITEM_BLOCKED_BY", "WORK_ITEM_DEPENDS_ON", "WORK_ITEM_RELATED_TO",
    "WORK_ITEM_ADDRESSED_BY_COMMIT", "COMMIT_BELONGS_TO_PULL_REQUEST",
    "PULL_REQUEST_REFERENCES_ISSUE", "PULL_REQUEST_MODIFIES_COMPONENT",
    "COMMIT_MODIFIES_COMPONENT", "PULL_REQUEST_REVIEWED_BY", "PULL_REQUEST_AUTHORED_BY",
    "PERSON_AUTHORED", "PERSON_REVIEWED", "PERSON_ASSIGNED_TO",
    "PERSON_RESPONSIBLE_FOR", "PERSON_DISCUSSIONS_PARTICIPANT", "PERSON_CONTRIBUTED_TO",
    "COMPONENT_DEPENDS_ON", "COMPONENT_CALLS_COMPONENT", "COMPONENT_USES_SERVICE",
    "COMPONENT_STORES_DATA_IN", "COMPONENT_EXPOSES_API", "DOCUMENT_DESCRIBES_COMPONENT",
    "DOCUMENT_DESCRIBES_DECISION", "RISK_AFFECTS_COMPONENT", "BUG_FOUND_IN_COMPONENT",
    "RISK_BLOCKS_WORK_ITEM", "BUG_RELATED_TO_WORK_ITEM", "RISK_DEPENDS_ON_EXTERNAL_FACTOR",
    "KNOWLEDGE_SUPPORTED_BY_EVIDENCE", "KNOWLEDGE_CORROBORATED_BY",
    "DOCUMENT_REFERENCES_EVIDENCE", "DISCUSSION_REFERENCES_WORK_ITEM"
]

CANONICAL_TYPES = [rt.value for rt in RelationshipType]
ALL_TYPES = sorted(list(set(VERBOSE_TYPES + CANONICAL_TYPES)))

quoted_types = ", ".join(f"'{t}'" for t in ALL_TYPES)

with session_scope(factory) as session:
    print("Dropping old constraint...")
    session.execute(text("ALTER TABLE knowledge_relationships DROP CONSTRAINT IF EXISTS ck_relationship_type_valid;"))
    print("Adding unified constraint...")
    session.execute(text(f"ALTER TABLE knowledge_relationships ADD CONSTRAINT ck_relationship_type_valid CHECK (relationship_type IN ({quoted_types}));"))
    session.commit()
    print("Successfully updated ck_relationship_type_valid with", len(ALL_TYPES), "allowed types!")
