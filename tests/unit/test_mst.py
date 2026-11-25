"""Unit tests for MST-01..MST-08 master data, XLSX import/export, and data quality."""

from __future__ import annotations

import base64
import io
from collections.abc import Iterator
from pathlib import Path

import pytest
from openpyxl import Workbook, load_workbook

from backend.core.app_shell import AppRuntime, bootstrap_runtime
from backend.core.errors import ConflictError, ValidationError
from backend.modules.cfg.schemas import AcademicYearSavePayload, FirstRunPayload
from backend.modules.cfg.service import CfgService
from backend.modules.mst.schemas import (
    ClassSavePayload,
    DataQualityPayload,
    EnrollmentSavePayload,
    ExportMasterPayload,
    ImportCommitPayload,
    ImportPreviewPayload,
    MasterListPayload,
    RoomLayoutConfig,
    RoomSavePayload,
    ScopedEntityDeletePayload,
    StaffSavePayload,
    StudentSavePayload,
    SubjectSavePayload,
    TeachingAssignmentSavePayload,
)
from backend.modules.mst.service import MstService


@pytest.fixture()
def mst_env(tmp_path: Path) -> Iterator[tuple[CfgService, MstService, str, str, str]]:
    runtime: AppRuntime = bootstrap_runtime(
        workspace_root=tmp_path, institution_slug="mst_unit"
    )
    cfg = CfgService(runtime.session_factory, runtime.paths)
    mst = MstService(runtime.session_factory, runtime.paths)
    inst = cfg.first_run_setup(
        FirstRunPayload(
            name="MTs Negeri Uji",
            level_preset="SMP/MTs",
            academic_year_label="2026/2027",
        )
    )["institution"]
    inst_id = str(inst["id"])
    year_id = str(cfg.list_years(inst_id)["items"][0]["id"])
    level_id = str(cfg.list_levels(inst_id)["items"][0]["id"])
    yield cfg, mst, inst_id, year_id, level_id
    runtime.shutdown()


def _make_xlsx_base64(headers: list[str], rows: list[list[object]]) -> str:
    wb = Workbook()
    ws = wb.active
    assert ws is not None
    ws.append(headers)
    for r in rows:
        ws.append(r)
    buf = io.BytesIO()
    wb.save(buf)
    return base64.b64encode(buf.getvalue()).decode("ascii")


def test_students_leading_zero_duplicate_nis_and_delete_protection(
    mst_env: tuple[CfgService, MstService, str, str, str],
) -> None:
    _, mst, inst_id, year_id, level_id = mst_env
    res1 = mst.save_student(
        StudentSavePayload(
            institution_id=inst_id,
            nis="0001",
            nisn=None,
            full_name="Peserta 01",
        )
    )
    assert res1["student"]["nis"] == "0001"
    assert len(res1["warnings"]) == 1

    with pytest.raises(ConflictError):
        mst.save_student(
            StudentSavePayload(
                institution_id=inst_id,
                nis="0001",
                nisn="0000000002",
                full_name="Duplikat NIS",
            )
        )

    cls_item = mst.save_class(
        ClassSavePayload(
            institution_id=inst_id,
            year_id=year_id,
            level_id=level_id,
            name="VII-A",
        )
    )["class_item"]
    mst.save_enrollment(
        EnrollmentSavePayload(
            institution_id=inst_id,
            student_id=res1["student"]["id"],
            class_id=cls_item["id"],
            year_id=year_id,
        )
    )

    with pytest.raises(ConflictError):
        mst.delete_student(
            ScopedEntityDeletePayload(institution_id=inst_id, id=res1["student"]["id"])
        )


def test_external_staff_without_nip_and_class_same_label_different_year(
    mst_env: tuple[CfgService, MstService, str, str, str],
) -> None:
    cfg, mst, inst_id, year_id, level_id = mst_env
    ext = mst.save_staff(
        StaffSavePayload(
            institution_id=inst_id,
            staff_code="EXT01",
            nip=None,
            full_name="Pengawas Silang",
            role="external_invigilator",
        )
    )["staff"]
    assert ext["nip"] is None

    with pytest.raises(ConflictError):
        mst.save_staff(
            StaffSavePayload(
                institution_id=inst_id,
                staff_code="EXT01",
                full_name="Duplikat Kode",
            )
        )

    year2 = cfg.save_year(
        AcademicYearSavePayload(institution_id=inst_id, label="2027/2028")
    )["year"]
    c1 = mst.save_class(
        ClassSavePayload(
            institution_id=inst_id, year_id=year_id, level_id=level_id, name="VII-A"
        )
    )["class_item"]
    c2 = mst.save_class(
        ClassSavePayload(
            institution_id=inst_id,
            year_id=year2["id"],
            level_id=level_id,
            name="VII-A",
        )
    )["class_item"]
    assert c1["id"] != c2["id"]


def test_subjects_teaching_assignment_and_room_capacity_cap(
    mst_env: tuple[CfgService, MstService, str, str, str],
) -> None:
    _, mst, inst_id, year_id, level_id = mst_env
    cls_item = mst.save_class(
        ClassSavePayload(
            institution_id=inst_id, year_id=year_id, level_id=level_id, name="VII-A"
        )
    )["class_item"]
    subj = mst.save_subject(
        SubjectSavePayload(institution_id=inst_id, code="MAT", name="Matematika")
    )["subject"]
    assert (
        len(mst.list_subjects(MasterListPayload(institution_id=inst_id))["warnings"])
        == 1
    )

    teacher = mst.save_staff(
        StaffSavePayload(institution_id=inst_id, staff_code="G01", full_name="Guru Mat")
    )["staff"]
    mst.save_teaching_assignment(
        TeachingAssignmentSavePayload(
            institution_id=inst_id,
            staff_id=teacher["id"],
            class_id=cls_item["id"],
            subject_id=subj["id"],
        )
    )
    assert (
        mst.list_subjects(MasterListPayload(institution_id=inst_id))["warnings"] == []
    )

    with pytest.raises(ValueError):
        RoomSavePayload(
            institution_id=inst_id,
            code="R01",
            name="Ruang 01",
            capacity_limit=15,
            layout=RoomLayoutConfig(rows=3, cols=4, seats_per_desk=1),
        )

    room = mst.save_room(
        RoomSavePayload(
            institution_id=inst_id,
            code="R01",
            name="Ruang 01",
            capacity_limit=10,
            layout=RoomLayoutConfig(
                rows=3, cols=4, seats_per_desk=1, disabled_cells=["R3C4"]
            ),
        )
    )["room"]
    assert room["stats"]["enabled_seats"] == 11
    assert room["stats"]["effective_capacity"] == 10


def test_xlsx_import_export_leading_zero_and_formula_injection(
    mst_env: tuple[CfgService, MstService, str, str, str],
) -> None:
    _, mst, inst_id, _, _ = mst_env
    b64 = _make_xlsx_base64(
        ["nis", "nisn", "full_name"],
        [
            ["0001", "0000000001", "Nabila Putri"],
            ["0002", "0000000002", "=cmd|'/C calc'!A0"],
            ["0003", "0000000003", "Raka Aditya"],
        ],
    )
    preview = mst.preview_import(
        ImportPreviewPayload(
            institution_id=inst_id,
            kind="students",
            filename="students.xlsx",
            content_base64=b64,
        )
    )
    assert preview["counts"]["valid"] == 2
    assert preview["counts"]["invalid"] == 1

    with pytest.raises(ValidationError):
        mst.commit_import(
            ImportCommitPayload(
                institution_id=inst_id,
                preview_id=preview["preview_id"],
                skip_invalid_rows=False,
            )
        )

    committed = mst.commit_import(
        ImportCommitPayload(
            institution_id=inst_id,
            preview_id=preview["preview_id"],
            skip_invalid_rows=True,
        )
    )
    assert committed["inserted"] == 2

    mst.save_student(
        StudentSavePayload(
            institution_id=inst_id,
            nis="0004",
            nisn="0000000004",
            full_name="=SUM(A1:A2)",
        )
    )
    exported = mst.export_xlsx(
        ExportMasterPayload(institution_id=inst_id, kind="students")
    )
    assert exported["row_count"] == 3

    wb = load_workbook(io.BytesIO(base64.b64decode(exported["content_base64"])))
    ws = wb.active
    assert ws is not None
    exported_rows = list(ws.iter_rows(min_row=2, values_only=True))
    assert exported_rows[0][0] == "0004"
    assert exported_rows[0][2] == "'=SUM(A1:A2)"
    assert exported_rows[1][0] == "0001"
    assert exported_rows[1][1] == "0000000001"

    quality = mst.data_quality_report(DataQualityPayload(institution_id=inst_id))
    assert quality["total_issues"] >= 3
