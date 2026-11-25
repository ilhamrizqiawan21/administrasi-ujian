"""Unit tests for FND-04..FND-07 core modules."""

from __future__ import annotations

import json
import os
import stat
import threading
import time
from pathlib import Path

import pytest

from backend.core.errors import ConflictError, StorageError
from backend.core.jobs import JobContext, JobRunner, atomic_write_bytes
from backend.core.logging import (
    configure_logging,
    redact_mapping,
    redact_text,
    reset_correlation_id,
    set_correlation_id,
)
from backend.core.paths import (
    WorkspaceLock,
    ensure_writable_workspace,
    resolve_workspace_paths,
)


def test_workspace_lock_blocks_second_instance(tmp_path: Path) -> None:
    lock_file = tmp_path / ".workspace.lock"
    lock1 = WorkspaceLock(lock_file)
    lock2 = WorkspaceLock(lock_file)
    lock1.acquire()
    try:
        with pytest.raises(StorageError) as exc_info:
            lock2.acquire()
        assert exc_info.value.code == "CONFLICT"
    finally:
        lock1.release()

    lock2.acquire()
    lock2.release()


def test_readonly_workspace_rejected(tmp_path: Path) -> None:
    if os.geteuid() == 0:
        pytest.skip("Root ignores directory read-only permissions.")
    ro_root = tmp_path / "readonly_ws"
    ro_root.mkdir()
    os.chmod(ro_root, stat.S_IRUSR | stat.S_IXUSR)
    try:
        paths = resolve_workspace_paths(ro_root)
        with pytest.raises(StorageError) as exc_info:
            ensure_writable_workspace(paths)
        assert exc_info.value.code == "PERMISSION_DENIED"
    finally:
        os.chmod(ro_root, stat.S_IRWXU)


def test_logging_redacts_pii_and_paths(tmp_path: Path) -> None:
    logger = configure_logging(tmp_path / "logs")
    tok = set_correlation_id("corr-123")
    try:
        logger.info(
            "Student imported from /home/operator/data/siswa.xlsx",
            extra={
                "extra_data": {
                    "nisn": "0071234501",
                    "nama": "Nabila Putri",
                    "path": "C:\\Users\\Operator\\Documents\\ujian.sqlite",
                }
            },
        )
    finally:
        reset_correlation_id(tok)

    log_line = (tmp_path / "logs" / "app.log").read_text(encoding="utf-8").strip()
    record = json.loads(log_line)
    assert record["correlation_id"] == "corr-123"
    assert "/home/operator" not in record["message"]
    assert "[REDACTED_PATH]" in record["message"]
    assert record["data"]["nisn"] == "[REDACTED]"
    assert record["data"]["nama"] == "[REDACTED]"
    assert record["data"]["path"] == "[REDACTED_PATH]"
    assert redact_text("NISN 0071234501") == "NISN [REDACTED_ID]"
    assert redact_mapping({"token": "abc"}) == {"token": "[REDACTED]"}


def test_job_runner_cancel_and_scope_guard(tmp_path: Path) -> None:
    runner = JobRunner(max_workers=2)
    started = threading.Event()
    output_file = tmp_path / "published.txt"

    def long_job(ctx: JobContext) -> dict[str, object]:
        started.set()
        for step in range(20):
            ctx.report_progress("Menghitung", step + 1, 20)
            time.sleep(0.02)
        atomic_write_bytes(output_file, b"published", temp_dir=tmp_path / "tmp")
        return {"written": True}

    try:
        rec = runner.submit("solver", long_job, scope_key="plan-1")
        assert started.wait(timeout=2.0)

        with pytest.raises(ConflictError):
            runner.submit("solver", long_job, scope_key="plan-1")

        runner.cancel(rec.job_id)
        deadline = time.monotonic() + 2.0
        status = runner.get_status(rec.job_id)
        while status["status"] in ("queued", "running") and time.monotonic() < deadline:
            time.sleep(0.02)
            status = runner.get_status(rec.job_id)

        assert status["status"] == "cancelled"
        assert not output_file.exists()
    finally:
        runner.shutdown(wait=True)
