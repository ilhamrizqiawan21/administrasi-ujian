"""Integration tests for ROM-01..ROM-08 via BridgeApi."""

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


def _setup_exam_plan(tmp_path: Path) -> tuple[BridgeApi, str, str, str, str]:
    runtime = bootstrap_runtime(workspace_root=tmp_path, institution_slug="rom_bridge")
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
    assert inst["ok"] is True
    inst_id = inst["data"]["institution"]["id"]

    year_id = _call(api, "cfg.years.list", {"institution_id": inst_id})["data"][
        "items"
    ][0]["id"]
    et_id = _call(api, "cfg.exam_types.list", {"institution_id": inst_id})["data"][
        "items"
    ][0]["id"]
    levels = _call(api, "cfg.levels.list", {"institution_id": inst_id})["data"]["items"]
    lvl7_id = levels[0]["id"]
    lvl8_id = levels[1]["id"]

    # Create 2 classes (grade 7 & grade 8)
    cls7 = _call(
        api,
        "mst.classes.save",
        {
            "institution_id": inst_id,
            "year_id": year_id,
            "level_id": lvl7_id,
            "name": "7A",
        },
    )
    assert cls7["ok"] is True
    cls7_id = cls7["data"]["class_item"]["id"]

    cls8 = _call(
        api,
        "mst.classes.save",
        {
            "institution_id": inst_id,
            "year_id": year_id,
            "level_id": lvl8_id,
            "name": "8A",
        },
    )
    assert cls8["ok"] is True
    cls8_id = cls8["data"]["class_item"]["id"]

    # Create 4 students and enroll them
    for idx, (cid, acc) in enumerate(
        [(cls7_id, True), (cls7_id, False), (cls8_id, False), (cls8_id, False)],
        start=1,
    ):
        st = _call(
            api,
            "mst.students.save",
            {
                "institution_id": inst_id,
                "nis": f"200{idx}",
                "full_name": f"Siswa {idx}",
                "accommodation": {"accessible_seat": acc},
            },
        )
        assert st["ok"] is True
        enr = _call(
            api,
            "mst.enrollments.save",
            {
                "institution_id": inst_id,
                "year_id": year_id,
                "student_id": st["data"]["student"]["id"],
                "class_id": cid,
            },
        )
        assert enr["ok"] is True

    # Create 1 subject so timetable can publish
    subj = _call(
        api,
        "mst.subjects.save",
        {
            "institution_id": inst_id,
            "code": "MAT",
            "name": "Matematika",
        },
    )
    assert subj["ok"] is True

    # Create 1 room
    rm = _call(
        api,
        "mst.rooms.save",
        {
            "institution_id": inst_id,
            "code": "R01",
            "name": "Ruang 01",
            "capacity_limit": 6,
            "mode": "paper",
            "layout": {
                "rows": 2,
                "cols": 3,
                "seats_per_desk": 1,
                "disabled_cells": [],
                "accessible_seats": ["R1C1S1"],
                "board_position": "top",
            },
        },
    )
    assert rm["ok"] is True

    # Create exam (auto-snapshots)
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
    assert ex["ok"] is True
    exam_id = ex["data"]["exam"]["id"]

    plan = _call(
        api,
        "ses.plans.create",
        {"institution_id": inst_id, "exam_id": exam_id},
    )
    assert plan["ok"] is True, plan
    plan_id = plan["data"]["plan"]["id"]

    sess = _call(
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
    assert sess["ok"] is True

    auto = _call(
        api,
        "ses.schedule.auto_generate",
        {
            "institution_id": inst_id,
            "exam_id": exam_id,
            "plan_id": plan_id,
            "expected_revision": plan["data"]["plan"]["revision"] + 1,
        },
    )
    assert auto["ok"] is True

    init_detail = _call(
        api,
        "rom.seating.detail",
        {"institution_id": inst_id, "exam_id": exam_id, "plan_id": plan_id},
    )
    assert init_detail["ok"] is True
    exam_room_id = init_detail["data"]["rooms"][0]["id"]
    return api, inst_id, exam_id, plan_id, exam_room_id


def test_rom_bridge_end_to_end(tmp_path: Path) -> None:
    api, inst_id, exam_id, plan_id, exam_room_id = _setup_exam_plan(tmp_path)

    # ROM-01: update room layout
    upd = _call(
        api,
        "rom.rooms.update_layout",
        {
            "institution_id": inst_id,
            "exam_id": exam_id,
            "plan_id": plan_id,
            "exam_room_id": exam_room_id,
            "rows": 2,
            "cols": 3,
            "seats_per_desk": 1,
            "capacity_limit": 5,
            "disabled_cells": ["R2C3"],
            "accessible_seats": ["R1C1S1"],
            "board_position": "bottom",
        },
    )
    assert upd["ok"] is True
    assert upd["data"]["room_id"] == exam_room_id

    # Detail
    detail = _call(
        api,
        "rom.seating.detail",
        {"institution_id": inst_id, "exam_id": exam_id, "plan_id": plan_id},
    )
    assert detail["ok"] is True
    rev = detail["data"]["plan_revision"]
    assert len(detail["data"]["seats"]) == 6
    disabled_seat = [s for s in detail["data"]["seats"] if s["seat_code"] == "R2C3S1"][
        0
    ]
    assert disabled_seat["enabled"] == 0

    # ROM-04: solve seating
    solved = _call(
        api,
        "rom.seating.solve",
        {
            "institution_id": inst_id,
            "exam_id": exam_id,
            "plan_id": plan_id,
            "expected_revision": rev,
            "policy": {
                "mode": "mix_grade",
                "hard_mix_grade": True,
                "require_accessible": True,
            },
        },
    )
    assert solved["ok"] is True
    assert solved["data"]["ok"] is True
    assert solved["data"]["validation"]["valid"] is True
    rev = solved["data"]["plan_revision"]

    detail2 = _call(
        api,
        "rom.seating.detail",
        {"institution_id": inst_id, "exam_id": exam_id, "plan_id": plan_id},
    )
    occupied = [s for s in detail2["data"]["seats"] if s["participant"] is not None]
    assert len(occupied) == 4
    acc_seat = [s for s in occupied if s["seat_code"] == "R1C1S1"][0]
    assert acc_seat["participant"]["display_name"] == "Siswa 1"

    # ROM-07: lock seat and verify swap rejection
    lock_res = _call(
        api,
        "rom.seats.lock",
        {
            "institution_id": inst_id,
            "exam_id": exam_id,
            "plan_id": plan_id,
            "seat_id": occupied[0]["id"],
            "locked": True,
        },
    )
    assert lock_res["ok"] is True
    rev = lock_res["data"]["plan_revision"]

    swap_locked = _call(
        api,
        "rom.seats.swap",
        {
            "institution_id": inst_id,
            "exam_id": exam_id,
            "plan_id": plan_id,
            "expected_revision": rev,
            "source_seat_id": occupied[0]["id"],
            "target_seat_id": occupied[1]["id"],
        },
    )
    assert swap_locked["ok"] is False
    assert swap_locked["error"]["code"] == "CONFLICT"

    # Unlock and swap two seats (non-hard mode so any valid swap works)
    unlock_res = _call(
        api,
        "rom.seats.lock",
        {
            "institution_id": inst_id,
            "exam_id": exam_id,
            "plan_id": plan_id,
            "seat_id": occupied[0]["id"],
            "locked": False,
        },
    )
    assert unlock_res["ok"] is True
    rev = unlock_res["data"]["plan_revision"]

    empty_enabled = [
        s
        for s in detail2["data"]["seats"]
        if s["enabled"] == 1 and s["participant"] is None
    ][0]
    swap_ok = _call(
        api,
        "rom.seats.swap",
        {
            "institution_id": inst_id,
            "exam_id": exam_id,
            "plan_id": plan_id,
            "expected_revision": rev,
            "source_seat_id": occupied[1]["id"],
            "target_seat_id": empty_enabled["id"],
            "policy": {"require_accessible": False},
        },
    )
    assert swap_ok["ok"] is True
    rev = swap_ok["data"]["plan_revision"]

    # ROM-08: publish & print context
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
    assert pub["ok"] is True, pub

    print_ctx = _call(
        api,
        "rom.seating.print_context",
        {
            "institution_id": inst_id,
            "exam_id": exam_id,
            "plan_id": plan_id,
            "exam_room_id": exam_room_id,
            "include_names": True,
        },
    )
    assert print_ctx["ok"] is True
    assert print_ctx["data"]["plan_state"] == "published"
    assert print_ctx["data"]["board_position"] == "bottom"
    assert any(d["display_name"] is not None for d in print_ctx["data"]["desks"])

    # Published plan cannot be mutated
    mut_pub = _call(
        api,
        "rom.seating.solve",
        {
            "institution_id": inst_id,
            "exam_id": exam_id,
            "plan_id": plan_id,
            "expected_revision": rev + 1,
        },
    )
    assert mut_pub["ok"] is False
    assert mut_pub["error"]["code"] == "CONFLICT"
