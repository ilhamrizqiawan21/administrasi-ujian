"""Integration tests for COM-01..COM-06 via BridgeApi."""

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


def test_com_bridge_end_to_end(tmp_path: Path) -> None:
    runtime = bootstrap_runtime(workspace_root=tmp_path, institution_slug="com_bridge")
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

    _call(
        api,
        "mst.staff.save",
        {
            "institution_id": inst_id,
            "staff_code": "G01",
            "full_name": "Drs. Ahmad",
            "role": "teacher",
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

    # COM-01: role CRUD + cycle rejection
    r1 = _call(
        api,
        "com.roles.save",
        {
            "institution_id": inst_id,
            "exam_id": exam_id,
            "name": "Ketua",
            "sort_order": 1,
        },
    )["data"]["id"]
    r2 = _call(
        api,
        "com.roles.save",
        {
            "institution_id": inst_id,
            "exam_id": exam_id,
            "name": "Sekretaris",
            "parent_id": r1,
            "sort_order": 2,
        },
    )["data"]["id"]

    cycle_res = _call(
        api,
        "com.roles.save",
        {
            "institution_id": inst_id,
            "exam_id": exam_id,
            "id": r1,
            "name": "Ketua",
            "parent_id": r2,
        },
    )
    assert cycle_res["ok"] is False
    assert cycle_res["error"]["code"] == "CONFLICT"

    detail = _call(api, "com.detail", {"institution_id": inst_id, "exam_id": exam_id})
    person_id = detail["data"]["staff"][0]["id"]

    # COM-02: assign member, reject duplicate in same role, allow multiple roles
    m1 = _call(
        api,
        "com.members.assign",
        {
            "institution_id": inst_id,
            "exam_id": exam_id,
            "role_id": r1,
            "exam_person_id": person_id,
            "appointed_on": "2026-11-25",
        },
    )
    assert m1["ok"] is True

    dup = _call(
        api,
        "com.members.assign",
        {
            "institution_id": inst_id,
            "exam_id": exam_id,
            "role_id": r1,
            "exam_person_id": person_id,
        },
    )
    assert dup["ok"] is False
    assert dup["error"]["code"] == "CONFLICT"

    m2 = _call(
        api,
        "com.members.assign",
        {
            "institution_id": inst_id,
            "exam_id": exam_id,
            "role_id": r2,
            "exam_person_id": person_id,
        },
    )
    assert m2["ok"] is True

    # COM-04: program kerja
    pk = _call(
        api,
        "com.program.save",
        {
            "institution_id": inst_id,
            "exam_id": exam_id,
            "basis_text": "SK Kepala Sekolah No. 01/2026",
            "objectives": ["Tertib administrasi"],
            "milestones": [{"label": "Rapat Koordinasi", "target_date": "2026-11-28"}],
            "sections": [{"title": "Pendahuluan", "body": "Pelaksanaan PAS"}],
        },
    )
    assert pk["ok"] is True

    # COM-05: meetings & attendance
    mt = _call(
        api,
        "com.meetings.save",
        {
            "institution_id": inst_id,
            "exam_id": exam_id,
            "title": "Rapat Persiapan",
            "meeting_date": "2026-11-28",
            "start_time": "09:00",
            "end_time": "10:30",
            "agenda": "Pembagian tugas",
            "decisions": ["Jadwal disetujui"],
        },
    )
    assert mt["ok"] is True
    att = _call(
        api,
        "com.meetings.attendance.save",
        {
            "institution_id": inst_id,
            "exam_id": exam_id,
            "meeting_id": mt["data"]["id"],
            "exam_person_id": person_id,
            "state": "present",
        },
    )
    assert att["ok"] is True

    # COM-06: signatories validation
    sig_missing = _call(
        api,
        "com.signatories.save",
        {
            "institution_id": inst_id,
            "exam_id": exam_id,
            "role_key": "headmaster",
            "role_label": "Kepala Sekolah",
            "signer_name": "",
            "signer_title": "Kepala Sekolah",
            "required": True,
        },
    )
    assert sig_missing["ok"] is True

    detail2 = _call(api, "com.detail", {"institution_id": inst_id, "exam_id": exam_id})
    assert detail2["data"]["signatory_validation"]["valid"] is False

    _call(
        api,
        "com.signatories.save",
        {
            "institution_id": inst_id,
            "exam_id": exam_id,
            "role_key": "headmaster",
            "role_label": "Kepala Sekolah",
            "signer_name": "Drs. Ahmad",
            "signer_title": "Kepala Sekolah",
            "required": True,
        },
    )
    detail3 = _call(api, "com.detail", {"institution_id": inst_id, "exam_id": exam_id})
    assert detail3["data"]["signatory_validation"]["valid"] is True
    assert len(detail3["data"]["org_tree"]) == 1
