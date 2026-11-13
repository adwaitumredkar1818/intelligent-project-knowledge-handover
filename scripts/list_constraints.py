from app.core.config import get_settings
from app.db.session import create_db_engine, create_session_factory, session_scope
from sqlalchemy import text

settings = get_settings()
engine = create_db_engine(settings)
factory = create_session_factory(engine)

with session_scope(factory) as s:
    rows = s.execute(text("""
        SELECT conname, pg_get_constraintdef(c.oid)
        FROM pg_constraint c
        JOIN pg_class t ON c.conrelid = t.oid
        WHERE t.relname = 'knowledge_relationships' AND c.contype = 'c';
    """)).fetchall()
    for name, definition in rows:
        print(f"Constraint: {name}\nDefinition: {definition}\n")
