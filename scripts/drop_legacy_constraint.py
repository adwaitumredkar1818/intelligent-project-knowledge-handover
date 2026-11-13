from app.core.config import get_settings
from app.db.session import create_db_engine, create_session_factory, session_scope
from sqlalchemy import text

settings = get_settings()
engine = create_db_engine(settings)
factory = create_session_factory(engine)

with session_scope(factory) as s:
    print("Dropping legacy constraint ck_knowledge_relationships_ck_relationship_type_valid...")
    s.execute(text("ALTER TABLE knowledge_relationships DROP CONSTRAINT IF EXISTS ck_knowledge_relationships_ck_relationship_type_valid;"))
    s.commit()
    print("Dropped successfully!")
