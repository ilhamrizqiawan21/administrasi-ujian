"""Integration tests for SES bridge methods."""

from __future__ import annotations

from pathlib import Path

from backend.bridge.api import BridgeApi
from backend.core.app_shell import bootstrap_runtime


def test_ses_bridge_create_validate_and_publish(tmp_path: Path) -> None:
    runtime = bootstrap_runtime(workspace_root=tmp_path, institution_slug="ses_bridge")
    try:
        api = BridgeApi(runtime=runtime)
        inst_id = api.invoke(
            {
                "method": "cfg.first_run.setup",
                "request_id": "s-1",
                "payload": {
                    "name": "MTs Bridge SES",
                    "level_preset": "SMP/MTs",
                    "academic_year_label": "2026/2027",
                },
            }
        )["data"]["institution"]["id"]
        year_id = api.invoke(
            {
                "method": "cfg.years.list",
                "request_id": "s-2",
                "payload": {"institution_id": inst_id},
            }
        )["data"]["items"][0]["id"]
        et_id = api.invoke(
            {
                "method": "cfg.exam_types.list",
                "request_id": "s-3",
                "payload": {"institution_id": inst_id},
            }
        )["data"]["items"][0]["id"]

        api.invoke(
            {
                "method": "mst.students.save",
                "request_id": "s-4",
                "payload": {
                    "institution_id": inst_id,
                    "nis": "0001",
                    "full_name": "Ali",
                },
            }
        )
        api.invoke(
            {
                "method": "mst.rooms.save",
                "request_id": "s-5",
                "payload": {
                    "institution_id": inst_id,
                    "code": "R01",
                    "name": "Ruang 01",
                    "capacity_limit": 20,
                },
            }
        )
        api.invoke(
            {
                "method": "mst.subjects.save",
                "request_id": "s-6",
                "payload": {
                    "institution_id": inst_id,
                    "code": "MAT",
                    "name": "Matematika",
                },
            }
        )
        exam_id = api.invoke(
            {
                "method": "evt.exams.create",
                "request_id": "s-7",
                "payload": {
                    "institution_id": inst_id,
                    "year_id": year_id,
                    "exam_type_id": et_id,
                    "title": "SAS",
                    "semester_label": "Ganjil",
                    "starts_on": "2026-11-30",
                    "ends_on": "2026-12-08",
                },
            }
        )["data"]["exam"]["id"]

        plan = api.invoke(
            {
                "method": "ses.plans.create",
                "request_id": "s-8",
                "payload": {"institution_id": inst_id, "exam_id": exam_id},
            }
        )["data"]["plan"]

        api.invoke(
            {
                "method": "ses.sessions.save",
                "request_id": "s-9",
                "payload": {
                    "institution_id": inst_id,
                    "exam_id": exam_id,
                    "plan_id": plan["id"],
                    "label": "Sesi 1",
                    "local_date": "2026-11-30",
                    "start_local": "07:30",
                    "end_local": "09:00",
                },
            }
        )
        auto = api.invoke(
            {
                "method": "ses.schedule.auto_generate",
                "request_id": "s-10",
                "payload": {
                    "institution_id": inst_id,
                    "exam_id": exam_id,
                    "plan_id": plan["id"],
                    "expected_revision": 2,
                },
            }
        )
        assert auto["ok"] is True
        assert auto["data"]["ok"] is True

        val = api.invoke(
            {
                "method": "ses.plans.validate",
                "request_id": "s-11",
                "payload": {
                    "institution_id": inst_id,
                    "exam_id": exam_id,
                    "plan_id": plan["id"],
                },
            }
        )
        assert val["data"]["valid"] is True
    finally:
        runtime.shutdown()
