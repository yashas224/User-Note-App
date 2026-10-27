from collections.abc import Iterator

from sqlalchemy import Engine, create_engine, event
from sqlalchemy.orm import Session, sessionmaker

from user_note.backend.core.config import settings


def _set_foreign_keys_pragma(dbapi_conn, _record) -> None:
    cursor = dbapi_conn.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


def enable_sqlite_foreign_keys(engine: Engine) -> None:
    # Per engine, not on the Engine class, so Alembic's migration engine keeps
    # foreign keys off as batch mode requires.
    if engine.dialect.name == "sqlite":
        event.listen(engine, "connect", _set_foreign_keys_pragma)


engine = create_engine(settings.DATABASE_URL, connect_args={"check_same_thread": False})
enable_sqlite_foreign_keys(engine)


SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def get_db() -> Iterator[Session]:
    with SessionLocal() as db:
        yield db
