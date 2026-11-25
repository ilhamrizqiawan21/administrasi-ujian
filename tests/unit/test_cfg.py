"""Unit tests for CFG-01..CFG-06 domain rules and validators."""

from __future__ import annotations

import base64
import io
from collections.abc import Iterator
from pathlib import Path

import pytest
from PIL import Image

from backend.core.app_shell import AppRuntime, bootstrap_runtime
from backend.core.errors import AppError, ConflictError, ValidationError
from backend.modules.cfg.schemas import (
    ExamTypeSavePayload,
    FirstRunPayload,
    LevelSavePayload,
    LogoUploadPayload,
    NumberPolicyConfig,
    NumberPolicyPreviewPayload,
    SettingsResetPayload,
    SettingsUpdatePayload,
    TypedSettingsConfig,
)
from backend.modules.cfg.service import (
    CfgService,
    preview_numbers,
    validate_unique_numbers,
)


@pytest.fixture()
def cfg_env(tmp_path: Path) -> Iterator[tuple[AppRuntime, CfgService]]:
    runtime = bootstrap_runtime(workspace_root=tmp_path, institution_slug="cfg_unit")
    service = CfgService(runtime.session_factory, runtime.paths)
    yield runtime, service
    runtime.shutdown()


def test_first_run_atomic_and_rollback_on_invalid(
    cfg_env: tuple[AppRuntime, CfgService],
) -> None:
    _, service = cfg_env
    assert service.get_onboarding_status()["needs_onboarding"] is True

    with pytest.raises(ValidationError):
        service.first_run_setup(
            FirstRunPayload(
                name="PKBM Harapan",
                level_preset="Kustom",
                custom_levels=[],
                academic_year_label="2026/2027",
            )
        )
    assert service.get_onboarding_status()["needs_onboarding"] is True

    res = service.first_run_setup(
        FirstRunPayload(
            name="MTs Nusantara",
            npsn="00234567",
            level_preset="SMP/MTs",
            academic_year_label="2026/2027",
        )
    )
    inst = res["institution"]
    assert inst["npsn"] == "00234567"
    assert service.get_onboarding_status()["needs_onboarding"] is False

    levels = service.list_levels(inst["id"])["items"]
    assert [lvl["label"] for lvl in levels] == ["VII", "VIII", "IX"]


def test_institution_isolation_and_logo_validation(
    cfg_env: tuple[AppRuntime, CfgService],
) -> None:
    _, service = cfg_env
    s1 = service.first_run_setup(
        FirstRunPayload(
            name="SD Satu",
            level_preset="SD/MI",
            academic_year_label="2026/2027",
        )
    )["institution"]
    s2 = service.first_run_setup(
        FirstRunPayload(
            name="SMA Dua",
            level_preset="SMA/MA",
            academic_year_label="2026/2027",
        )
    )["institution"]

    s1_levels = [lvl["label"] for lvl in service.list_levels(s1["id"])["items"]]
    s2_levels = [lvl["label"] for lvl in service.list_levels(s2["id"])["items"]]
    assert s1_levels == ["I", "II", "III", "IV", "V", "VI"]
    assert s2_levels == ["X", "XI", "XII"]

    with pytest.raises(AppError) as bad_logo:
        service.upload_logo(
            LogoUploadPayload(
                institution_id=s1["id"],
                expected_revision=s1["revision"],
                filename="fake.png",
                content_base64=base64.b64encode(b"not-an-image").decode("ascii"),
            )
        )
    assert bad_logo.value.code == "FILE_INVALID"

    buf = io.BytesIO()
    Image.new("RGBA", (32, 32), (34, 103, 123, 255)).save(buf, format="PNG")
    updated = service.upload_logo(
        LogoUploadPayload(
            institution_id=s1["id"],
            expected_revision=s1["revision"],
            filename="logo.png",
            content_base64=base64.b64encode(buf.getvalue()).decode("ascii"),
        )
    )["institution"]
    assert updated["logo_asset_id"] is not None
    assert updated["revision"] == 2


def test_non_numeric_levels_and_custom_exam_type(
    cfg_env: tuple[AppRuntime, CfgService],
) -> None:
    _, service = cfg_env
    inst = service.first_run_setup(
        FirstRunPayload(
            name="Pesantren Al-Hikmah",
            level_preset="Kustom",
            custom_levels=["Tahfidz", "Wustha"],
            academic_year_label="2026/2027",
        )
    )["institution"]

    custom_lvl = service.save_level(
        LevelSavePayload(
            institution_id=inst["id"],
            label="Ulya",
            sort_order=3,
        )
    )["level"]
    assert custom_lvl["label"] == "Ulya"

    et = service.save_exam_type(
        ExamTypeSavePayload(
            institution_id=inst["id"],
            code="MUNA",
            label="Munaqosyah Tahfidz",
            mode_default="practice",
        )
    )["exam_type"]
    assert et["code"] == "MUNA"
    codes = [item["code"] for item in service.list_exam_types(inst["id"])["items"]]
    assert "MUNA" in codes


def test_number_policy_blocks_duplicates_and_missing_values() -> None:
    policy = NumberPolicyConfig.model_validate(
        {
            "participant": {
                "prefix": "UC",
                "separator": "-",
                "padding": 4,
                "start_seq": 1,
                "reset_scope": "event",
            },
            "document": {
                "pattern": "{seq}/{series}/{exam_code}/{year}",
                "padding": 3,
                "reset_scope": "year",
            },
        }
    )

    with pytest.raises(ValidationError):
        preview_numbers(
            NumberPolicyPreviewPayload(
                policy=policy, series="PAN", exam_code="", year="2026"
            )
        )

    preview = preview_numbers(
        NumberPolicyPreviewPayload(
            policy=policy, series="PAN", exam_code="SAS", year="2026", count=2
        )
    )
    assert preview["participant_samples"] == ["UC-0001", "UC-0002"]
    assert preview["document_samples"] == ["001/PAN/SAS/2026", "002/PAN/SAS/2026"]

    with pytest.raises(ConflictError):
        validate_unique_numbers(["UC-0001", "UC-0001"])


def test_typed_settings_validation_revision_and_reset(
    cfg_env: tuple[AppRuntime, CfgService],
) -> None:
    _, service = cfg_env
    inst = service.first_run_setup(
        FirstRunPayload(
            name="SMK Karya",
            level_preset="SMK",
            academic_year_label="2026/2027",
        )
    )["institution"]

    current = service.get_settings(inst["id"])
    assert current["revision"] == 1

    updated = service.update_settings(
        SettingsUpdatePayload(
            institution_id=inst["id"],
            expected_revision=1,
            settings=TypedSettingsConfig.model_validate(
                {
                    "default_paper_size": "F4",
                    "solver_time_limit_sec": 90,
                    "allow_part_time_weights": True,
                    "extension_fields": [
                        {
                            "key": "asal_rayon",
                            "label": "Asal Rayon",
                            "scope": "student",
                            "field_type": "string",
                            "required": False,
                        }
                    ],
                }
            ),
        )
    )
    assert updated["revision"] == 2
    assert updated["settings"]["default_paper_size"] == "F4"

    with pytest.raises(AppError) as stale:
        service.update_settings(
            SettingsUpdatePayload(
                institution_id=inst["id"],
                expected_revision=1,
                settings=TypedSettingsConfig(),
            )
        )
    assert stale.value.code == "STALE_REVISION"

    reset_res = service.reset_settings(
        SettingsResetPayload(institution_id=inst["id"], expected_revision=2)
    )
    assert reset_res["revision"] == 3
    assert reset_res["settings"]["default_paper_size"] == "A4"
