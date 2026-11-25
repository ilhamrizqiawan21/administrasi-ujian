"""Workspace storage paths, permission checks, and single-instance OS lock."""

from __future__ import annotations

import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import IO

from platformdirs import user_data_dir

from backend.core.errors import StorageError


@dataclass(frozen=True)
class WorkspacePaths:
    """Resolved local storage directories for an institution workspace."""

    root: Path
    config_dir: Path
    db_dir: Path
    assets_dir: Path
    backups_dir: Path
    exports_dir: Path
    logs_dir: Path
    temp_dir: Path
    lock_file: Path

    def db_file(self, institution_slug: str = "default") -> Path:
        safe_slug = "".join(
            ch for ch in institution_slug if ch.isalnum() or ch in ("-", "_")
        )
        if not safe_slug:
            safe_slug = "default"
        return self.db_dir / f"{safe_slug}.sqlite"


def resolve_workspace_paths(custom_root: Path | None = None) -> WorkspacePaths:
    """Build workspace directory layout under local app data or custom root."""
    root = (
        custom_root.resolve()
        if custom_root is not None
        else Path(user_data_dir("UjianCerdas", appauthor=False)).resolve()
    )
    return WorkspacePaths(
        root=root,
        config_dir=root / "config",
        db_dir=root / "db",
        assets_dir=root / "assets",
        backups_dir=root / "backups",
        exports_dir=root / "exports",
        logs_dir=root / "logs",
        temp_dir=root / "temp",
        lock_file=root / ".workspace.lock",
    )


def ensure_writable_workspace(paths: WorkspacePaths) -> None:
    """Create workspace directories and verify write/delete permissions."""
    dirs = (
        paths.root,
        paths.config_dir,
        paths.db_dir,
        paths.assets_dir,
        paths.backups_dir,
        paths.exports_dir,
        paths.logs_dir,
        paths.temp_dir,
    )
    try:
        for directory in dirs:
            directory.mkdir(parents=True, exist_ok=True)
        probe = paths.temp_dir / f".write_probe_{os.getpid()}"
        probe.write_text("ok", encoding="utf-8")
        probe.unlink()
    except OSError as exc:
        raise StorageError(
            "Folder workspace tidak dapat ditulis atau hanya-baca.",
            code="PERMISSION_DENIED",
        ) from exc


class WorkspaceLock:
    """Non-blocking OS file lock ensuring single active writer per workspace."""

    def __init__(self, lock_path: Path) -> None:
        self._lock_path = lock_path
        self._fh: IO[str] | None = None

    def acquire(self) -> None:
        if self._fh is not None:
            return
        self._lock_path.parent.mkdir(parents=True, exist_ok=True)
        fh = self._lock_path.open("a+", encoding="utf-8")
        try:
            if sys.platform == "win32":
                import msvcrt

                fh.seek(0)
                msvcrt.locking(fh.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl

                fcntl.flock(fh.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            fh.seek(0)
            fh.truncate()
            fh.write(str(os.getpid()))
            fh.flush()
            self._fh = fh
        except OSError as exc:
            fh.close()
            raise StorageError(
                "Workspace sedang digunakan oleh instance aplikasi lain.",
                code="CONFLICT",
            ) from exc

    def release(self) -> None:
        if self._fh is None:
            return
        try:
            if sys.platform == "win32":
                import msvcrt

                self._fh.seek(0)
                msvcrt.locking(self._fh.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                import fcntl

                fcntl.flock(self._fh.fileno(), fcntl.LOCK_UN)
        finally:
            self._fh.close()
            self._fh = None
