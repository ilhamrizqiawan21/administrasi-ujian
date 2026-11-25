"""Integration tests for EVT bridge methods."""

from __future__ import annotations

from pathlib import Path

from backend.bridge.api import BridgeApi
from backend.core.app_shell import bootstrap_runtime


def test_evt_bridge_create_number_and_dashboard(tmp_path: Path) -> None:
    runtime = bootstrap_runtime(workspace_root=tmp_path, institution_slug="evt_bridge")
    try:
        api = BridgeApi(runtime=runtime)
        inst = api.invoke(
            {
                "method": "cfg.first_run.setup",
                "request_id": "e-1",
                "payload": {
                    "name": "SMA Bridge",
                    "level_preset": "SMA/MA",
                    "academic_year_label": "2026/2027",
                },
            }
        )["data"]["institution"]
        inst_id = inst["id"]
        year_id = api.invoke(
            {
                "method": "cfg.years.list",
                "request_id": "e-2",
                "payload": {"institution_id": inst_id},
            }
        )["data"]["items"][0]["id"]
        et_id = api.invoke(
            {
                "method": "cfg.exam_types.list",
                "request_id": "e-3",
                "payload": {"institution_id": inst_id},
            }
        )["data"]["items"][0]["id"]

        api.invoke(
            {
                "method": "mst.students.save",
                "request_id": "e-4",
                "payload": {
                    "institution_id": inst_id,
                    "nis": "0101",
                    "full_name": "Hana Safitri",
                },
            }
        )
        api.invoke(
            {
                "method": "mst.rooms.save",
                "request_id": "e-5",
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
                "request_id": "e-6",
                "payload": {
                    "institution_id": inst_id,
                    "code": "IND",
                    "name": "Bahasa Indonesia",
                },
            }
        )

        created = api.invoke(
            {
                "method": "evt.exams.create",
                "request_id": "e-7",
                "payload": {
                    "institution_id": inst_id,
                    "year_id": year_id,
                    "exam_type_id": et_id,
                    "title": "SAS Ganjil Bridge",
                    "semester_label": "Ganjil",
                    "starts_on": "2026-11-30",
                    "ends_on": "2026-12-08",
                },
            }
        )
        assert created["ok"] is True
        exam_id = created["data"]["exam"]["id"]

        dash = api.invoke(
            {
                "method": "evt.exams.dashboard",
                "request_id": "e-8",
                "payload": {"institution_id": inst_id, "exam_id": exam_id},
            }
        )
        assert dash["ok"] is True
        assert dash["data"]["counts"]["participants"] == 1
        assert dash["data"]["counts"]["rooms"] == 1
    finally:
        runtime.shutdown()
