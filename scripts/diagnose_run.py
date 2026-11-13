from app.core.config import get_settings
from app.db.session import create_db_engine, create_session_factory, session_scope
from sqlalchemy import text

settings = get_settings()
engine = create_db_engine(settings)
factory = create_session_factory(engine)

with session_scope(factory) as s:
    rows = s.execute(text("SELECT pid, state, query, wait_event_type, wait_event FROM pg_stat_activity WHERE state != 'idle'")).fetchall()
    for r in rows:
        print(f"PID: {r[0]} | State: {r[1]} | Wait: {r[3]}:{r[4]}\nQuery:\n{r[2]}\n---")
