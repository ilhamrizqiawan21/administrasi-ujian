"""Bounded background job runner with cooperative cancellation and atomic outputs."""

from __future__ import annotations

import os
import threading
import uuid
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal

from backend.core.errors import ConflictError, NotFoundError

JobStatus = Literal[
    "queued", "running", "succeeded", "failed", "cancelled", "interrupted"
]


class JobCancelledError(Exception):
    """Raised cooperatively inside a job when cancellation is requested."""


@dataclass
class JobContext:
    """Execution handle passed to job worker functions."""

    job_id: str
    cancel_event: threading.Event
    _on_progress: Callable[[str, int, int], None]

    def check_cancelled(self) -> None:
        if self.cancel_event.is_set():
            raise JobCancelledError("Pekerjaan dibatalkan oleh pengguna.")

    def report_progress(self, phase: str, current: int, total: int) -> None:
        self.check_cancelled()
        self._on_progress(phase, current, total)


@dataclass
class JobRecord:
    """In-memory snapshot of a tracked background job."""

    job_id: str
    job_type: str
    scope_key: str | None
    status: JobStatus = "queued"
    phase: str = "Menunggu antrean"
    current: int = 0
    total: int = 0
    result: dict[str, Any] | None = None
    error_code: str | None = None
    error_message: str | None = None
    cancel_event: threading.Event = field(default_factory=threading.Event, repr=False)

    def to_dict(self) -> dict[str, Any]:
        return {
            "job_id": self.job_id,
            "job_type": self.job_type,
            "scope_key": self.scope_key,
            "status": self.status,
            "phase": self.phase,
            "current": self.current,
            "total": self.total,
            "result": self.result,
            "error_code": self.error_code,
            "error_message": self.error_message,
        }


def atomic_write_bytes(target_path: Path, data: bytes, *, temp_dir: Path) -> Path:
    """Write bytes to temp file and atomically replace target_path."""
    temp_dir.mkdir(parents=True, exist_ok=True)
    target_path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = temp_dir / f".tmp_{uuid.uuid4().hex}_{target_path.name}"
    try:
        tmp_path.write_bytes(data)
        os.replace(tmp_path, target_path)
    except Exception:
        if tmp_path.exists():
            tmp_path.unlink(missing_ok=True)
        raise
    return target_path


class JobRunner:
    """Bounded worker pool enforcing one active mutating job per scope."""

    def __init__(self, max_workers: int = 2) -> None:
        self._executor = ThreadPoolExecutor(
            max_workers=max_workers, thread_name_prefix="uc-job"
        )
        self._lock = threading.Lock()
        self._jobs: dict[str, JobRecord] = {}
        self._active_scopes: dict[str, str] = {}
        self._shutdown = False

    def submit(
        self,
        job_type: str,
        fn: Callable[[JobContext], dict[str, Any]],
        *,
        scope_key: str | None = None,
    ) -> JobRecord:
        with self._lock:
            if self._shutdown:
                raise ConflictError("Aplikasi sedang ditutup; pekerjaan ditolak.")
            if scope_key is not None and scope_key in self._active_scopes:
                raise ConflictError(
                    "Masih ada pekerjaan aktif pada ruang lingkup yang sama."
                )
            job_id = uuid.uuid4().hex
            record = JobRecord(job_id=job_id, job_type=job_type, scope_key=scope_key)
            self._jobs[job_id] = record
            if scope_key is not None:
                self._active_scopes[scope_key] = job_id

        self._executor.submit(self._run_job, job_id, fn)
        return record

    def _update_progress(
        self, job_id: str, phase: str, current: int, total: int
    ) -> None:
        with self._lock:
            rec = self._jobs.get(job_id)
            if rec is not None and rec.status == "running":
                rec.phase = phase
                rec.current = current
                rec.total = total

    def _run_job(self, job_id: str, fn: Callable[[JobContext], dict[str, Any]]) -> None:
        with self._lock:
            rec = self._jobs[job_id]
            if rec.cancel_event.is_set():
                rec.status = "cancelled"
                rec.phase = "Dibatalkan"
                self._release_scope_locked(rec)
                return
            rec.status = "running"
            rec.phase = "Memproses"
            cancel_event = rec.cancel_event

        ctx = JobContext(
            job_id=job_id,
            cancel_event=cancel_event,
            _on_progress=lambda p, c, t: self._update_progress(job_id, p, c, t),
        )
        try:
            result = fn(ctx)
            with self._lock:
                if cancel_event.is_set():
                    rec.status = "cancelled"
                    rec.phase = "Dibatalkan"
                else:
                    rec.status = "succeeded"
                    rec.phase = "Selesai"
                    rec.result = result
                self._release_scope_locked(rec)
        except JobCancelledError:
            with self._lock:
                rec.status = "cancelled"
                rec.phase = "Dibatalkan"
                self._release_scope_locked(rec)
        except Exception as exc:
            with self._lock:
                rec.status = "failed"
                rec.phase = "Gagal"
                rec.error_code = "INTERNAL"
                rec.error_message = str(exc)
                self._release_scope_locked(rec)

    def _release_scope_locked(self, rec: JobRecord) -> None:
        if rec.scope_key is not None and self._active_scopes.get(rec.scope_key) == (
            rec.job_id
        ):
            del self._active_scopes[rec.scope_key]

    def get_status(self, job_id: str) -> dict[str, Any]:
        with self._lock:
            rec = self._jobs.get(job_id)
            if rec is None:
                raise NotFoundError(f"Pekerjaan '{job_id}' tidak ditemukan.")
            return rec.to_dict()

    def cancel(self, job_id: str) -> dict[str, Any]:
        with self._lock:
            rec = self._jobs.get(job_id)
            if rec is None:
                raise NotFoundError(f"Pekerjaan '{job_id}' tidak ditemukan.")
            rec.cancel_event.set()
            if rec.status == "queued":
                rec.status = "cancelled"
                rec.phase = "Dibatalkan"
                self._release_scope_locked(rec)
            return rec.to_dict()

    def shutdown(self, *, wait: bool = True) -> None:
        with self._lock:
            self._shutdown = True
            for rec in self._jobs.values():
                if rec.status in ("queued", "running"):
                    rec.cancel_event.set()
        self._executor.shutdown(wait=wait)
