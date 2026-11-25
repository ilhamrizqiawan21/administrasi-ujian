"""Integration tests for OPS-01..OPS-08 via BridgeApi."""

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


def test_ops_bridge_end_to_end(tmp_path: Path) -> None:
    runtime = bootstrap_runtime(workspace_root=tmp_path, institution_slug="ops_bridge")
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
    lvl_id = _call(api, "cfg.levels.list", {"institution_id": inst_id})["data"][
        "items"
    ][0]["id"]

    cls_id = _call(
        api,
        "mst.classes.save",
        {
            "institution_id": inst_id,
            "year_id": year_id,
            "level_id": lvl_id,
            "name": "7A",
        },
    )["data"]["class_item"]["id"]
    st_id = _call(
        api,
        "mst.students.save",
        {"institution_id": inst_id, "nis": "1001", "full_name": "Siswa 1"},
    )["data"]["student"]["id"]
    _call(
        api,
        "mst.enrollments.save",
        {
            "institution_id": inst_id,
            "year_id": year_id,
            "student_id": st_id,
            "class_id": cls_id,
        },
    )
    _call(
        api,
        "mst.staff.save",
        {
            "institution_id": inst_id,
            "staff_code": "G01",
            "full_name": "Guru 1",
            "role": "teacher",
        },
    )
    _call(
        api,
        "mst.subjects.save",
        {"institution_id": inst_id, "code": "MAT", "name": "Matematika"},
    )
    _call(
        api,
        "mst.rooms.save",
        {
            "institution_id": inst_id,
            "code": "R01",
            "name": "Ruang 01",
            "capacity_limit": 10,
            "mode": "paper",
        },
    )

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

    plan = _call(
        api, "ses.plans.create", {"institution_id": inst_id, "exam_id": exam_id}
    )
    plan_id = plan["data"]["plan"]["id"]
    _call(
        api,
        "ses.sessions.save",
        {
            "institution_id": inst_id,
            "exam_id": exam_id,
            "plan_id": plan_id,
            "label": "Sesi 1",
            "local_date": "2026-12-01",
            "start_local": "07:30",
            "end_local": "09:00",
        },
    )
    _call(
        api,
        "ses.schedule.auto_generate",
        {
            "institution_id": inst_id,
            "exam_id": exam_id,
            "plan_id": plan_id,
            "expected_revision": plan["data"]["plan"]["revision"] + 1,
        },
    )

    # Seat students so participant_sittings exist
    rom_detail = _call(
        api,
        "rom.seating.detail",
        {"institution_id": inst_id, "exam_id": exam_id, "plan_id": plan_id},
    )
    _call(
        api,
        "rom.seating.solve",
        {
            "institution_id": inst_id,
            "exam_id": exam_id,
            "plan_id": plan_id,
            "expected_revision": rom_detail["data"]["plan_revision"],
        },
    )

    detail = _call(
        api,
        "ops.detail",
        {"institution_id": inst_id, "exam_id": exam_id, "plan_id": plan_id},
    )
    assert detail["ok"] is True
    rs_id = detail["data"]["room_sessions"][0]["room_session_id"]
    sitting_id = detail["data"]["room_sessions"][0]["sittings"][0]["sitting_id"]
    staff_id = detail["data"]["staff"][0]["id"]

    # OPS-08: closing blocked while attendance unrecorded and report unfinalized
    bad_close = _call(
        api,
        "ops.closing.complete",
        {"institution_id": inst_id, "exam_id": exam_id, "plan_id": plan_id},
    )
    assert bad_close["ok"] is False
    assert bad_close["error"]["code"] == "CONFLICT"

    # OPS-02 & OPS-07: mark absent -> create makeup -> original absence preserved
    att = _call(
        api,
        "ops.students.attendance",
        {
            "institution_id": inst_id,
            "exam_id": exam_id,
            "sitting_ids": [sitting_id],
            "state": "absent",
        },
    )
    assert att["ok"] is True

    mk = _call(
        api,
        "ops.makeup.create",
        {
            "institution_id": inst_id,
            "exam_id": exam_id,
            "plan_id": plan_id,
            "original_sitting_id": sitting_id,
            "target_room_session_id": rs_id,
            "reason": "Sakit dengan surat dokter",
        },
    )
    assert mk["ok"] is True

    # OPS-04: committee attendance
    ca = _call(
        api,
        "ops.committee.attendance",
        {
            "institution_id": inst_id,
            "exam_id": exam_id,
            "att_date": "2026-12-01",
            "shift": "Pagi",
            "exam_person_id": staff_id,
            "state": "present",
        },
    )
    assert ca["ok"] is True

    # OPS-06: confidential incident hidden unless requested
    inc = _call(
        api,
        "ops.incidents.record",
        {
            "institution_id": inst_id,
            "exam_id": exam_id,
            "room_session_id": rs_id,
            "type_code": "violation",
            "severity": "medium",
            "note": "Catatan rahasia siswa",
            "confidential": True,
        },
    )
    assert inc["ok"] is True
    detail_pub = _call(
        api,
        "ops.detail",
        {
            "institution_id": inst_id,
            "exam_id": exam_id,
            "plan_id": plan_id,
            "include_confidential": False,
        },
    )
    assert (
        detail_pub["data"]["incidents"][0]["note"] == "[Catatan rahasia disembunyikan]"
    )

    # OPS-05: finalize report -> immutable -> closing succeeds
    fin = _call(
        api,
        "ops.reports.finalize",
        {
            "institution_id": inst_id,
            "exam_id": exam_id,
            "plan_id": plan_id,
            "room_session_id": rs_id,
            "remarks": "Berjalan tertib",
            "signer_name": "Guru 1",
        },
    )
    assert fin["ok"] is True
    assert fin["data"]["finalized"] is True

    edit_fin = _call(
        api,
        "ops.reports.save",
        {
            "institution_id": inst_id,
            "exam_id": exam_id,
            "plan_id": plan_id,
            "room_session_id": rs_id,
            "remarks": "Diubah",
        },
    )
    assert edit_fin["ok"] is False
    assert edit_fin["error"]["code"] == "CONFLICT"

    ok_close = _call(
        api,
        "ops.closing.complete",
        {"institution_id": inst_id, "exam_id": exam_id, "plan_id": plan_id},
    )
    assert ok_close["ok"] is True
    assert ok_close["data"]["closed"] is True
