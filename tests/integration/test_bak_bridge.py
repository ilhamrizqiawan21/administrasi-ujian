"""Integration tests for BAK-01..BAK-04 via BridgeApi."""

from __future__ import annotations

import zipfile
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from sqlalchemy import text

from backend.bridge.api import BridgeApi
from backend.core.app_shell import bootstrap_runtime
from backend.core.db import session_scope


def _call(
    api: BridgeApi, method: str, payload: dict[str, Any] | None = None
) -> dict[str, Any]:
    return api.invoke(
        {"request_id": f"req-{method}", "method": method, "payload": payload or {}}
    )


def test_bak_bridge_end_to_end(tmp_path: Path) -> None:
    runtime = bootstrap_runtime(workspace_root=tmp_path, institution_slug="bak_bridge")
    api = BridgeApi(runtime=runtime)

    inst_id = _call(
        api,
        "cfg.first_run.setup",
        {
            "name": "SMPN 3 Harapan",
            "level_preset": "SMP/MTs",
            "academic_year_label": "2026/2027",
        },
    )["data"]["institution"]["id"]

    # Add an asset & a student before backup
    asset_file = runtime.paths.assets_dir / "logo_test.png"
    asset_file.parent.mkdir(parents=True, exist_ok=True)
    asset_file.write_bytes(b"PNGDATA")

    _call(
        api,
        "mst.students.save",
        {
            "institution_id": inst_id,
            "nis": "00100",
            "full_name": "Siti Aminah",
            "active": True,
        },
    )

    # BAK-01: Create and verify backup ZIP
    bak_res = _call(api, "bak.create", {"institution_id": inst_id, "kind": "manual"})
    assert bak_res["ok"] is True, bak_res
    bak_id = bak_res["data"]["id"]
    bak_path = bak_res["data"]["file_path"]

    verify_res = _call(
        api, "bak.verify", {"institution_id": inst_id, "backup_id": bak_id}
    )
    assert verify_res["ok"] is True
    assert verify_res["data"]["valid"] is True
    assert verify_res["data"]["counts"]["students"] == 1

    # BAK-02: Schedule settings, failure visibility, and safe retention
    sched_save = _call(
        api,
        "bak.schedule.save",
        {
            "institution_id": inst_id,
            "auto_on_startup": True,
            "auto_on_close": False,
            "retention_count": 1,
        },
    )
    assert sched_save["ok"] is True
    assert sched_save["data"]["retention_count"] == 1

    sched_fail = _call(
        api,
        "bak.schedule.run",
        {"institution_id": inst_id, "trigger": "startup", "simulate_failure": True},
    )
    assert sched_fail["ok"] is True
    assert sched_fail["data"]["status"] == "failed"
    assert "Simulasi" in sched_fail["data"]["error"]

    sched_ok = _call(
        api,
        "bak.schedule.run",
        {"institution_id": inst_id, "trigger": "startup", "simulate_failure": False},
    )
    assert sched_ok["ok"] is True
    assert sched_ok["data"]["status"] == "ok"
    listed_baks = _call(api, "bak.list", {"institution_id": inst_id})["data"]["items"]
    assert len(listed_baks) >= 1  # Last good backup retained

    # BAK-03: Corrupt backup leaves current DB unchanged; valid backup restores cleanly
    corrupt_zip = runtime.paths.backups_dir / "corrupt.zip"
    with zipfile.ZipFile(corrupt_zip, "w") as zf:
        zf.writestr(
            "manifest.json", '{"db": {"path": "db/database.sqlite", "sha256": "bad"}}'
        )
        zf.writestr("db/database.sqlite", b"not-a-sqlite-db")

    corrupt_preview = _call(
        api,
        "bak.restore.preview",
        {"institution_id": inst_id, "file_path": "backups/corrupt.zip"},
    )
    assert corrupt_preview["ok"] is True
    assert corrupt_preview["data"]["can_restore"] is False

    corrupt_apply = _call(
        api,
        "bak.restore.apply",
        {"institution_id": inst_id, "file_path": "backups/corrupt.zip"},
    )
    assert corrupt_apply["ok"] is False

    # Mutate DB (add second student), then restore from original valid backup
    _call(
        api,
        "mst.students.save",
        {
            "institution_id": inst_id,
            "nis": "00200",
            "full_name": "Agus Salim",
            "active": True,
        },
    )
    students_before = _call(api, "mst.students.list", {"institution_id": inst_id})[
        "data"
    ]["items"]
    assert len(students_before) == 2

    valid_apply = _call(
        api,
        "bak.restore.apply",
        {"institution_id": inst_id, "file_path": bak_path},
    )
    assert valid_apply["ok"] is True, valid_apply
    assert valid_apply["data"]["restored"] is True
    students_after = _call(api, "mst.students.list", {"institution_id": inst_id})[
        "data"
    ]["items"]
    assert len(students_after) == 1
    assert students_after[0]["full_name"] == "Siti Aminah"

    # BAK-04: Crash simulation (interrupted job + .tmp_ file) -> diagnose & repair
    now = datetime.now(UTC).isoformat()
    with session_scope(runtime.session_factory) as session:
        session.execute(
            text(
                "INSERT INTO jobs (id, job_type, status, progress, "
                "error_code, created_at, updated_at) "
                "VALUES ('job-crash-1', 'solver', 'running', 45, NULL, :now, :now)"
            ),
            {"now": now},
        )
    stale_tmp = runtime.paths.temp_dir / ".tmp_crash_artifact.pdf"
    stale_tmp.parent.mkdir(parents=True, exist_ok=True)
    stale_tmp.write_bytes(b"partial")

    diag = _call(api, "bak.recovery.diagnose", {"institution_id": inst_id})
    assert diag["ok"] is True
    assert diag["data"]["healthy"] is False
    assert len(diag["data"]["interrupted_jobs"]) == 1
    assert len(diag["data"]["temp_files"]) == 1

    repair = _call(
        api,
        "bak.recovery.repair",
        {
            "institution_id": inst_id,
            "clean_temp_files": True,
            "mark_interrupted_jobs": True,
        },
    )
    assert repair["ok"] is True
    assert repair["data"]["cleaned_jobs"] == 1
    assert repair["data"]["cleaned_temp_files"] == 1
    assert repair["data"]["diagnostics"]["healthy"] is True
