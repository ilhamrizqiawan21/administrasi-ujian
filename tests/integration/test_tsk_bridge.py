"""Integration tests for TSK-01..TSK-05 via BridgeApi."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from backend.bridge.api import BridgeApi
from backend.core.app_shell import bootstrap_runtime


def _call(
    api: BridgeApi, method: str, payload: dict[str, Any] | None = None
) -> dict[str, Any]:
    return api.invoke(
        {"request_id": f"req-{method}", "method": method, "payload": payload or {}}
    )


def test_tsk_bridge_end_to_end(tmp_path: Path) -> None:
    runtime = bootstrap_runtime(workspace_root=tmp_path, institution_slug="tsk_bridge")
    api = BridgeApi(runtime=runtime)

    inst_id = _call(
        api,
        "cfg.first_run.setup",
        {
            "name": "SMPN 1 Nusantara",
            "level_preset": "SMP/MTs",
            "academic_year_label": "2026/2027",
        },
    )["data"]["institution"]["id"]
    year_id = _call(api, "cfg.years.list", {"institution_id": inst_id})["data"][
        "items"
    ][0]["id"]
    et_id = _call(api, "cfg.exam_types.list", {"institution_id": inst_id})["data"][
        "items"
    ][0]["id"]

    exam_id = _call(
        api,
        "evt.exams.create",
        {
            "institution_id": inst_id,
            "year_id": year_id,
            "exam_type_id": et_id,
            "title": "PAS Ganjil",
            "semester_label": "Ganjil",
            "starts_on": "2026-12-01",
            "ends_on": "2026-12-05",
        },
    )["data"]["exam"]["id"]

    # TSK-01: apply preset
    preset = _call(
        api,
        "tsk.presets.apply",
        {"institution_id": inst_id, "exam_id": exam_id, "preset_key": "standard_exam"},
    )
    assert preset["ok"] is True
    assert preset["data"]["created_count"] == 6

    detail = _call(api, "tsk.detail", {"institution_id": inst_id, "exam_id": exam_id})
    tasks = detail["data"]["tasks"]
    assert len(tasks) == 6
    assert all(t["missing_pic"] is True for t in tasks)
    # Offset -14 from 2026-12-01 -> 2026-11-17
    assert any(t["due_date"] == "2026-11-17" for t in tasks)

    t1 = tasks[0]
    t2 = tasks[1]

    # TSK-03: dependency t2 depends on t1; cycle rejected; completion policy enforced
    dep = _call(
        api,
        "tsk.dependencies.add",
        {
            "institution_id": inst_id,
            "exam_id": exam_id,
            "task_id": t2["id"],
            "prerequisite_id": t1["id"],
        },
    )
    assert dep["ok"] is True

    cycle = _call(
        api,
        "tsk.dependencies.add",
        {
            "institution_id": inst_id,
            "exam_id": exam_id,
            "task_id": t1["id"],
            "prerequisite_id": t2["id"],
        },
    )
    assert cycle["ok"] is False
    assert cycle["error"]["code"] == "CONFLICT"

    blocked_done = _call(
        api,
        "tsk.tasks.save",
        {
            "institution_id": inst_id,
            "exam_id": exam_id,
            "id": t2["id"],
            "phase": t2["phase"],
            "title": t2["title"],
            "due_date": t2["due_date"],
            "state": "done",
        },
    )
    assert blocked_done["ok"] is False
    assert blocked_done["error"]["code"] == "CONFLICT"

    # TSK-05: attach evidence and mark t1 done, then t2 can be marked done
    ev = _call(
        api,
        "tsk.evidence.attach",
        {
            "institution_id": inst_id,
            "exam_id": exam_id,
            "task_id": t1["id"],
            "evidence_asset_id": "assets/notulen-rapat.pdf",
            "evidence_note": "Sudah ditandatangani",
            "completed_by": "Ketua Panitia",
            "mark_done": True,
        },
    )
    assert ev["ok"] is True
    assert ev["data"]["state"] == "done"

    t2_done = _call(
        api,
        "tsk.tasks.save",
        {
            "institution_id": inst_id,
            "exam_id": exam_id,
            "id": t2["id"],
            "phase": t2["phase"],
            "title": t2["title"],
            "due_date": t2["due_date"],
            "state": "done",
        },
    )
    assert t2_done["ok"] is True
