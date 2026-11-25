"""Programmatic Alembic migration runner with migration lock."""

from __future__ import annotations

from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import Engine

from backend.core.paths import WorkspaceLock


def run_migrations(engine: Engine, *, lock_path: Path | None = None) -> None:
    """Apply Alembic migrations up to head under an optional migration lock."""
    migrations_dir = Path(__file__).resolve().parent.parent / "migrations"
    cfg = Config()
    cfg.set_main_option("script_location", str(migrations_dir))

    lock = WorkspaceLock(lock_path) if lock_path is not None else None
    if lock is not None:
        lock.acquire()
    try:
        with engine.begin() as connection:
            cfg.attributes["connection"] = connection
            command.upgrade(cfg, "head")
    finally:
        if lock is not None:
            lock.release()
