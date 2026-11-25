"""Integration tests for CFG bridge methods."""

from __future__ import annotations

from pathlib import Path

from backend.bridge.api import BridgeApi
from backend.core.app_shell import bootstrap_runtime


def test_cfg_bridge_end_to_end_onboarding_and_settings(tmp_path: Path) -> None:
    runtime = bootstrap_runtime(workspace_root=tmp_path, institution_slug="cfg_bridge")
    try:
        api = BridgeApi(runtime=runtime)

        status = api.invoke(
            {"method": "cfg.onboarding.status", "request_id": "c-1", "payload": {}}
        )
        assert status["ok"] is True
        assert status["data"]["needs_onboarding"] is True

        created = api.invoke(
            {
                "method": "cfg.first_run.setup",
                "request_id": "c-2",
                "payload": {
                    "name": "SMPN 1 Nusantara",
                    "npsn": "00112233",
                    "timezone": "Asia/Jakarta",
                    "level_preset": "SMP/MTs",
                    "academic_year_label": "2026/2027",
                },
            }
        )
        assert created["ok"] is True
        inst_id = created["data"]["institution"]["id"]

        bad_settings = api.invoke(
            {
                "method": "cfg.settings.update",
                "request_id": "c-3",
                "payload": {
                    "institution_id": inst_id,
                    "expected_revision": 1,
                    "settings": {
                        "default_paper_size": "A4",
                        "solver_time_limit_sec": 1,
                    },
                },
            }
        )
        assert bad_settings["ok"] is False
        assert bad_settings["error"]["code"] == "VALIDATION"

        preview = api.invoke(
            {
                "method": "cfg.number_policy.preview",
                "request_id": "c-4",
                "payload": {
                    "policy": {
                        "participant": {
                            "prefix": "SAS",
                            "separator": "-",
                            "padding": 4,
                            "start_seq": 10,
                            "reset_scope": "event",
                        },
                        "document": {
                            "pattern": "{seq}/{series}/{exam_code}/{year}",
                            "padding": 3,
                            "reset_scope": "year",
                        },
                    },
                    "series": "UJ",
                    "exam_code": "SAS",
                    "year": "2026",
                    "count": 2,
                },
            }
        )
        assert preview["ok"] is True
        assert preview["data"]["participant_samples"] == ["SAS-0010", "SAS-0011"]
    finally:
        runtime.shutdown()
