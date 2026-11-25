"""Integration tests for MST bridge methods."""

from __future__ import annotations

from pathlib import Path

from backend.bridge.api import BridgeApi
from backend.core.app_shell import bootstrap_runtime


def test_mst_bridge_crud_and_data_quality(tmp_path: Path) -> None:
    runtime = bootstrap_runtime(workspace_root=tmp_path, institution_slug="mst_bridge")
    try:
        api = BridgeApi(runtime=runtime)
        inst_res = api.invoke(
            {
                "method": "cfg.first_run.setup",
                "request_id": "m-1",
                "payload": {
                    "name": "SMPN Bridge",
                    "level_preset": "SMP/MTs",
                    "academic_year_label": "2026/2027",
                },
            }
        )
        inst_id = inst_res["data"]["institution"]["id"]

        st_res = api.invoke(
            {
                "method": "mst.students.save",
                "request_id": "m-2",
                "payload": {
                    "institution_id": inst_id,
                    "nis": "0010",
                    "nisn": "",
                    "full_name": "Siti Aulia",
                },
            }
        )
        assert st_res["ok"] is True
        assert st_res["data"]["student"]["nis"] == "0010"
        assert len(st_res["data"]["warnings"]) == 1

        listed = api.invoke(
            {
                "method": "mst.students.list",
                "request_id": "m-3",
                "payload": {"institution_id": inst_id, "query": "0010"},
            }
        )
        assert listed["ok"] is True
        assert listed["data"]["total"] == 1

        quality = api.invoke(
            {
                "method": "mst.quality.report",
                "request_id": "m-4",
                "payload": {"institution_id": inst_id},
            }
        )
        assert quality["ok"] is True
        assert quality["data"]["total_issues"] >= 1
    finally:
        runtime.shutdown()
