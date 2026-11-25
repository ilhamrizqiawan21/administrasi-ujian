"""Application composition root, startup boundary, and orderly shutdown."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path

from sqlalchemy import Engine
from sqlalchemy.orm import Session, sessionmaker

from backend.core.db import (
    create_session_factory,
    create_sqlite_engine,
    db_health_check,
)
from backend.core.jobs import JobRunner
from backend.core.logging import configure_logging
from backend.core.migrations import run_migrations
from backend.core.paths import (
    WorkspaceLock,
    WorkspacePaths,
    ensure_writable_workspace,
    resolve_workspace_paths,
)


@dataclass
class AppRuntime:
    """Live runtime dependencies owned by the application shell."""

    paths: WorkspacePaths
    lock: WorkspaceLock
    engine: Engine
    session_factory: sessionmaker[Session]
    job_runner: JobRunner
    logger: logging.Logger
    closed: bool = False

    def health(self) -> dict[str, object]:
        return {
            "workspace_root": str(self.paths.root),
            "db": db_health_check(self.engine),
        }

    def shutdown(self) -> None:
        if self.closed:
            return
        self.closed = True
        try:
            self.job_runner.shutdown(wait=True)
        finally:
            try:
                self.engine.dispose()
            finally:
                self.lock.release()


def bootstrap_runtime(
    *,
    workspace_root: Path | None = None,
    institution_slug: str = "default",
) -> AppRuntime:
    """Initialize workspace paths, lock, logging, DB, migrations, and job runner."""
    paths = resolve_workspace_paths(workspace_root)
    ensure_writable_workspace(paths)

    lock = WorkspaceLock(paths.lock_file)
    lock.acquire()

    engine: Engine | None = None
    job_runner: JobRunner | None = None
    try:
        logger = configure_logging(paths.logs_dir)
        db_path = paths.db_file(institution_slug)
        engine = create_sqlite_engine(db_path)
        run_migrations(engine)
        session_factory = create_session_factory(engine)
        job_runner = JobRunner(max_workers=2)
        logger.info("Application runtime initialized")
        return AppRuntime(
            paths=paths,
            lock=lock,
            engine=engine,
            session_factory=session_factory,
            job_runner=job_runner,
            logger=logger,
        )
    except Exception:
        if job_runner is not None:
            job_runner.shutdown(wait=False)
        if engine is not None:
            engine.dispose()
        lock.release()
        raise
