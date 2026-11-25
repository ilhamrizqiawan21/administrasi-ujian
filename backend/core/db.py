"""SQLAlchemy 2 database bootstrap, pragmas, session scope, and health check."""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Any

import sqlalchemy
from sqlalchemy import Engine, event, text
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker


class Base(DeclarativeBase):
    """Declarative base for all Ujian Cerdas ORM models."""


def create_sqlite_engine(
    db_path: Path | str,
    *,
    enable_wal: bool = True,
) -> Engine:
    """Create SQLite engine with foreign_keys=ON and busy_timeout configured."""
    url = (
        "sqlite:///:memory:"
        if str(db_path) == ":memory:"
        else f"sqlite:///{Path(db_path).resolve()}"
    )
    engine = sqlalchemy.create_engine(
        url,
        connect_args={"check_same_thread": False},
        future=True,
    )

    @event.listens_for(engine, "connect")
    def _configure_sqlite_pragmas(dbapi_conn: Any, _record: Any) -> None:
        cursor = dbapi_conn.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.execute("PRAGMA busy_timeout=5000")
        if enable_wal and str(db_path) != ":memory:":
            cursor.execute("PRAGMA journal_mode=WAL")
        cursor.close()

    return engine


def create_session_factory(engine: Engine) -> sessionmaker[Session]:
    """Return a non-autoflush/non-autocommit session factory."""
    return sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


@contextmanager
def session_scope(factory: sessionmaker[Session]) -> Iterator[Session]:
    """Provide a transactional scope around a series of operations."""
    session = factory()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def db_health_check(engine: Engine) -> dict[str, Any]:
    """Verify database connectivity, foreign_keys pragma, and integrity."""
    with engine.connect() as conn:
        fk_row = conn.execute(text("PRAGMA foreign_keys")).scalar_one()
        integrity = conn.execute(text("PRAGMA quick_check")).scalar_one()
    return {
        "ok": bool(fk_row == 1 and integrity == "ok"),
        "foreign_keys": int(fk_row),
        "integrity": str(integrity),
    }
