"""Integration tests for SCH-01..SCH-08 via BridgeApi."""

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


def _setup_sch(tmp_path: Path) -> tuple[BridgeApi, str, str, str, list[str]]:
    runtime = bootstrap_runtime(workspace_root=tmp_path, institution_slug="sch_bridge")
    api = BridgeApi(runtime=runtime)

    inst = _call(
        api,
        "cfg.first_run.setup",
        {
            "name": "SMPN 1 Nusantara",
            "level_preset": "SMP/MTs",
            "academic_year_label": "2026/2027",
        },
    )
    inst_id = inst["data"]["institution"]["id"]
    year_id = _call(api, "cfg.years.list", {"institution_id": inst_id})["data"][
        "items"
    ][0]["id"]
    et_id = _call(api, "cfg.exam_types.list", {"institution_id": inst_id})["data"][
        "items"
    ][0]["id"]
    lvl_id = _call(api, "cfg.levels.list", {"institution_id": inst_id})["data"][
        "items"
    ][0]["id"]

    cls = _call(
        api,
        "mst.classes.save",
        {
            "institution_id": inst_id,
            "year_id": year_id,
            "level_id": lvl_id,
            "name": "7A",
        },
    )
    cls_id = cls["data"]["class_item"]["id"]

    st = _call(
        api,
        "mst.students.save",
        {"institution_id": inst_id, "nis": "1001", "full_name": "Siswa 1"},
    )
    _call(
        api,
        "mst.enrollments.save",
        {
            "institution_id": inst_id,
            "year_id": year_id,
            "student_id": st["data"]["student"]["id"],
            "class_id": cls_id,
        },
    )

    for i in range(1, 4):
        res = _call(
            api,
            "mst.staff.save",
            {
                "institution_id": inst_id,
                "staff_code": f"G0{i}",
                "full_name": f"Guru {i}",
                "role": "teacher",
            },
        )
        assert res["ok"] is True

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

    ex = _call(
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
    )
    exam_id = ex["data"]["exam"]["id"]

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

    detail = _call(
        api,
        "sch.invigilation.detail",
        {"institution_id": inst_id, "exam_id": exam_id, "plan_id": plan_id},
    )
    assert detail["ok"] is True
    staff_ids = [p["id"] for p in detail["data"]["staff"]]
    assert len(staff_ids) == 3
    return api, inst_id, exam_id, plan_id, staff_ids


def test_sch_bridge_end_to_end(tmp_path: Path) -> None:
    api, inst_id, exam_id, plan_id, staff_ids = _setup_sch(tmp_path)

    # SCH-01: availability & profile
    av = _call(
        api,
        "sch.availability.save",
        {
            "institution_id": inst_id,
            "exam_id": exam_id,
            "exam_person_id": staff_ids[0],
            "starts_at": "2026-12-01T00:00:00+00:00",
            "ends_at": "2026-12-01T03:00:00+00:00",
            "state": "unavailable",
            "reason": "Rapat dinas",
        },
    )
    assert av["ok"] is True

    prof = _call(
        api,
        "sch.profiles.save",
        {
            "institution_id": inst_id,
            "exam_id": exam_id,
            "exam_person_id": staff_ids[1],
            "max_daily": 2,
            "max_total": 5,
            "target_weight_pct": 50,
            "role_skills": ["primary", "secondary"],
        },
    )
    assert prof["ok"] is True

    detail = _call(
        api,
        "sch.invigilation.detail",
        {"institution_id": inst_id, "exam_id": exam_id, "plan_id": plan_id},
    )
    rev = detail["data"]["plan_revision"]
    rs_id = detail["data"]["slots"][0]["room_session_id"]
    ses_id = detail["data"]["slots"][0]["session_id"]

    # SCH-02: configure slots (1 primary + 1 secondary)
    cfg = _call(
        api,
        "sch.slots.configure",
        {
            "institution_id": inst_id,
            "exam_id": exam_id,
            "plan_id": plan_id,
            "expected_revision": rev,
            "room_session_id": rs_id,
            "primary_count": 1,
            "secondary_count": 1,
            "proctor_count": 0,
        },
    )
    assert cfg["ok"] is True
    rev = cfg["data"]["plan_revision"]

    # SCH-04: solve invigilation
    solved = _call(
        api,
        "sch.invigilation.solve",
        {
            "institution_id": inst_id,
            "exam_id": exam_id,
            "plan_id": plan_id,
            "expected_revision": rev,
        },
    )
    assert solved["ok"] is True
    assert solved["data"]["ok"] is True
    assert solved["data"]["validation"]["valid"] is True
    rev = solved["data"]["plan_revision"]

    # Staff 0 was unavailable, so staff 1 and staff 2 must be assigned
    detail2 = _call(
        api,
        "sch.invigilation.detail",
        {"institution_id": inst_id, "exam_id": exam_id, "plan_id": plan_id},
    )
    assigned_ids = {s["exam_person_id"] for s in detail2["data"]["slots"]}
    assert assigned_ids == {staff_ids[1], staff_ids[2]}

    # SCH-06: manual replace with unavailable staff rejected
    slot_id = detail2["data"]["slots"][0]["id"]
    bad_assign = _call(
        api,
        "sch.invigilation.assign",
        {
            "institution_id": inst_id,
            "exam_id": exam_id,
            "plan_id": plan_id,
            "expected_revision": rev,
            "slot_id": slot_id,
            "exam_person_id": staff_ids[0],
            "locked": True,
        },
    )
    assert bad_assign["ok"] is False
    assert bad_assign["error"]["code"] == "CONFLICT"

    # SCH-08: reserve conflict with active staff rejected
    bad_res = _call(
        api,
        "sch.reserves.assign",
        {
            "institution_id": inst_id,
            "exam_id": exam_id,
            "plan_id": plan_id,
            "expected_revision": rev,
            "session_id": ses_id,
            "exam_person_id": staff_ids[1],
        },
    )
    assert bad_res["ok"] is False
    assert bad_res["error"]["code"] == "CONFLICT"

    # SCH-07: publish plan
    pub = _call(
        api,
        "ses.plans.publish",
        {
            "institution_id": inst_id,
            "exam_id": exam_id,
            "plan_id": plan_id,
            "expected_revision": rev,
        },
    )
    assert pub["ok"] is True
