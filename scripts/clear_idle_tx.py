from app.core.config import get_settings
from app.db.session import create_db_engine, create_session_factory, session_scope
from sqlalchemy import text

settings = get_settings()
engine = create_db_engine(settings)
factory = create_session_factory(engine)

with session_scope(factory) as s:
    rows = s.execute(text("""
        SELECT pid, state, state_change, query
        FROM pg_stat_activity
        WHERE state = 'idle in transaction'
        AND pid != pg_backend_pid();
    """)).fetchall()
    for r in rows:
        print("Terminating idle in transaction pid:", r[0])
        s.execute(text(f"SELECT pg_terminate_backend({r[0]})"))
    s.commit()
    print("Done clearing idle transactions.")
