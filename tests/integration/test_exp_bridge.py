"""Integration tests for EXP-01..EXP-06 via BridgeApi."""

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


def test_exp_bridge_end_to_end(tmp_path: Path) -> None:
    runtime = bootstrap_runtime(workspace_root=tmp_path, institution_slug="exp_bridge")
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

    # EXP-01: generate matrix & add custom item, reject duplicate
    mat = _call(
        api,
        "exp.matrix.generate",
        {"institution_id": inst_id, "exam_id": exam_id},
    )
    assert mat["ok"] is True
    assert mat["data"]["created_count"] == 5

    custom = _call(
        api,
        "exp.items.save",
        {
            "institution_id": inst_id,
            "exam_id": exam_id,
            "subject_label": "Matematika",
            "class_label": "7A",
            "type_code": "rubrik_praktik",
        },
    )
    assert custom["ok"] is True

    dup = _call(
        api,
        "exp.items.save",
        {
            "institution_id": inst_id,
            "exam_id": exam_id,
            "subject_label": "Matematika",
            "class_label": "7A",
            "type_code": "rubrik_praktik",
        },
    )
    assert dup["ok"] is False
    assert dup["error"]["code"] == "CONFLICT"

    detail = _call(api, "exp.detail", {"institution_id": inst_id, "exam_id": exam_id})
    item_id = detail["data"]["items"][0]["id"]

    # EXP-02 & EXP-03: receive -> valid -> replacement invalidates -> invalid rejected
    rec1 = _call(
        api,
        "exp.submissions.receive",
        {
            "institution_id": inst_id,
            "exam_id": exam_id,
            "item_id": item_id,
            "asset_id": "naskah-v1.docx",
            "received_at": "2026-11-25T08:00:00+00:00",
        },
    )
    assert rec1["data"]["version"] == 1

    bad_rev = _call(
        api,
        "exp.submissions.review",
        {
            "institution_id": inst_id,
            "exam_id": exam_id,
            "item_id": item_id,
            "new_state": "ready",
        },
    )
    assert bad_rev["ok"] is False
    assert bad_rev["error"]["code"] == "CONFLICT"

    ok_val = _call(
        api,
        "exp.submissions.review",
        {
            "institution_id": inst_id,
            "exam_id": exam_id,
            "item_id": item_id,
            "new_state": "valid",
        },
    )
    assert ok_val["ok"] is True

    rec2 = _call(
        api,
        "exp.submissions.receive",
        {
            "institution_id": inst_id,
            "exam_id": exam_id,
            "item_id": item_id,
            "asset_id": "naskah-v2.docx",
            "received_at": "2026-11-25T09:00:00+00:00",
        },
    )
    assert rec2["data"]["state"] == "received"
    assert rec2["data"]["version"] == 3

    # EXP-04: print quantities + override
    pq = _call(
        api,
        "exp.print.compute",
        {
            "institution_id": inst_id,
            "exam_id": exam_id,
            "plan_id": plan_id,
            "reserve_per_room": 2,
            "exclude_cbt": True,
        },
    )
    assert pq["ok"] is True
    assert pq["data"]["computed_count"] >= 1

    # EXP-05: handover with mismatch flagged
    ho = _call(
        api,
        "exp.handovers.record",
        {
            "institution_id": inst_id,
            "exam_id": exam_id,
            "kind": "out",
            "material_type": "Naskah MAT",
            "expected_qty": 10,
            "actual_qty": 9,
            "from_person_name": "Panitia",
            "to_person_name": "Pengawas R01",
            "handed_at": "2026-12-01T07:00:00+00:00",
        },
    )
    assert ho["ok"] is True
    assert ho["data"]["mismatch"] is True
    assert ho["data"]["discrepancy"] == -1
