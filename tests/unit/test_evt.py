"""Unit tests for EVT-01..EVT-07."""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest

from backend.core.app_shell import AppRuntime, bootstrap_runtime
from backend.core.errors import AppError, ConflictError, ValidationError
from backend.modules.cfg.schemas import FirstRunPayload
from backend.modules.cfg.service import CfgService
from backend.modules.evt.schemas import (
    ExamClonePayload,
    ExamCreatePayload,
    ExamRequirementSavePayload,
    ExamScopedPayload,
    ExamTransitionPayload,
    NumberingGeneratePayload,
    NumberingOverridePayload,
)
from backend.modules.evt.service import EvtService
from backend.modules.mst.schemas import (
    ClassSavePayload,
    EnrollmentSavePayload,
    RoomLayoutConfig,
    RoomSavePayload,
    StaffSavePayload,
    StudentSavePayload,
    SubjectSavePayload,
)
from backend.modules.mst.service import MstService


@pytest.fixture()
def evt_env(tmp_path: Path) -> Iterator[dict[str, Any]]:
    runtime: AppRuntime = bootstrap_runtime(
        workspace_root=tmp_path, institution_slug="evt_unit"
    )
    cfg = CfgService(runtime.session_factory, runtime.paths)
    mst = MstService(runtime.session_factory, runtime.paths)
    evt = EvtService(runtime.session_factory)

    inst = cfg.first_run_setup(
        FirstRunPayload(
            name="MTs EVT",
            level_preset="SMP/MTs",
            academic_year_label="2026/2027",
        )
    )["institution"]
    inst_id = str(inst["id"])
    year_id = str(cfg.list_years(inst_id)["items"][0]["id"])
    level_id = str(cfg.list_levels(inst_id)["items"][0]["id"])
    exam_type_id = str(cfg.list_exam_types(inst_id)["items"][0]["id"])

    cls_a = mst.save_class(
        ClassSavePayload(
            institution_id=inst_id, year_id=year_id, level_id=level_id, name="VII-A"
        )
    )["class_item"]
    cls_b = mst.save_class(
        ClassSavePayload(
            institution_id=inst_id, year_id=year_id, level_id=level_id, name="VII-B"
        )
    )["class_item"]

    s1 = mst.save_student(
        StudentSavePayload(institution_id=inst_id, nis="0001", full_name="Nabila Putri")
    )["student"]
    s2 = mst.save_student(
        StudentSavePayload(institution_id=inst_id, nis="0002", full_name="Raka Aditya")
    )["student"]
    mst.save_enrollment(
        EnrollmentSavePayload(
            institution_id=inst_id,
            student_id=s1["id"],
            class_id=cls_a["id"],
            year_id=year_id,
        )
    )
    mst.save_enrollment(
        EnrollmentSavePayload(
            institution_id=inst_id,
            student_id=s2["id"],
            class_id=cls_b["id"],
            year_id=year_id,
        )
    )
    mst.save_staff(
        StaffSavePayload(institution_id=inst_id, staff_code="G01", full_name="Ahmad")
    )
    mst.save_room(
        RoomSavePayload(
            institution_id=inst_id,
            code="R01",
            name="Ruang 01",
            capacity_limit=12,
            layout=RoomLayoutConfig(rows=3, cols=4, seats_per_desk=1),
        )
    )
    mst.save_subject(
        SubjectSavePayload(institution_id=inst_id, code="BIN", name="Bahasa Indonesia")
    )

    yield {
        "cfg": cfg,
        "mst": mst,
        "evt": evt,
        "inst_id": inst_id,
        "year_id": year_id,
        "exam_type_id": exam_type_id,
        "cls_a_id": cls_a["id"],
        "s1_id": s1["id"],
    }
    runtime.shutdown()


def test_event_wizard_selection_and_snapshot_isolation(
    evt_env: dict[str, object],
) -> None:
    evt: EvtService = evt_env["evt"]  # type: ignore[assignment]
    mst: MstService = evt_env["mst"]  # type: ignore[assignment]
    inst_id = str(evt_env["inst_id"])

    with pytest.raises(ValueError):
        ExamCreatePayload(
            institution_id=inst_id,
            year_id=str(evt_env["year_id"]),
            exam_type_id=str(evt_env["exam_type_id"]),
            title="SAS Ganjil",
            semester_label="Ganjil",
            starts_on="2026-12-08",
            ends_on="2026-11-30",
        )

    exam = evt.create_exam(
        ExamCreatePayload(
            institution_id=inst_id,
            year_id=str(evt_env["year_id"]),
            exam_type_id=str(evt_env["exam_type_id"]),
            title="SAS Ganjil",
            semester_label="Ganjil",
            starts_on="2026-11-30",
            ends_on="2026-12-08",
            selected_class_ids=[str(evt_env["cls_a_id"])],
        )
    )["exam"]

    parts = evt.list_participants(
        ExamScopedPayload(institution_id=inst_id, exam_id=exam["id"])
    )["items"]
    assert len(parts) == 1
    assert parts[0]["display_name"] == "Nabila Putri"

    mst.save_student(
        StudentSavePayload(
            institution_id=inst_id,
            id=str(evt_env["s1_id"]),
            expected_revision=1,
            nis="0001",
            full_name="Nama Berubah Di Master",
        )
    )
    parts_after = evt.list_participants(
        ExamScopedPayload(institution_id=inst_id, exam_id=exam["id"])
    )["items"]
    assert parts_after[0]["display_name"] == "Nabila Putri"


def test_numbering_collision_stale_cards_and_lifecycle_audit(
    evt_env: dict[str, object],
) -> None:
    evt: EvtService = evt_env["evt"]  # type: ignore[assignment]
    inst_id = str(evt_env["inst_id"])
    exam = evt.create_exam(
        ExamCreatePayload(
            institution_id=inst_id,
            year_id=str(evt_env["year_id"]),
            exam_type_id=str(evt_env["exam_type_id"]),
            title="SAS Penuh",
            semester_label="Ganjil",
            starts_on="2026-11-30",
            ends_on="2026-12-08",
        )
    )["exam"]

    with pytest.raises(ConflictError):
        evt.transition_state(
            ExamTransitionPayload(
                institution_id=inst_id,
                exam_id=exam["id"],
                expected_revision=exam["revision"],
                target_state="READY",
            )
        )

    numbered = evt.generate_participant_numbers(
        NumberingGeneratePayload(
            institution_id=inst_id,
            exam_id=exam["id"],
            expected_revision=exam["revision"],
            prefix="UC",
            padding=4,
            start_seq=1,
            mark_cards_printed=True,
        )
    )
    assert numbered["assigned_count"] == 2
    exam = numbered["exam"]

    parts = evt.list_participants(
        ExamScopedPayload(institution_id=inst_id, exam_id=exam["id"])
    )["items"]
    with pytest.raises(ConflictError):
        evt.override_participant_number(
            NumberingOverridePayload(
                institution_id=inst_id,
                exam_id=exam["id"],
                participant_id=parts[1]["id"],
                expected_revision=exam["revision"],
                participant_number=parts[0]["participant_number"],
            )
        )

    over = evt.override_participant_number(
        NumberingOverridePayload(
            institution_id=inst_id,
            exam_id=exam["id"],
            participant_id=parts[1]["id"],
            expected_revision=exam["revision"],
            participant_number="UC-0099",
        )
    )
    assert over["cards_stale"] is True
    exam = over["exam"]

    ready = evt.transition_state(
        ExamTransitionPayload(
            institution_id=inst_id,
            exam_id=exam["id"],
            expected_revision=exam["revision"],
            target_state="READY",
        )
    )["exam"]
    assert ready["state"] == "READY"

    with pytest.raises(ValidationError):
        evt.transition_state(
            ExamTransitionPayload(
                institution_id=inst_id,
                exam_id=exam["id"],
                expected_revision=ready["revision"],
                target_state="PREPARATION",
                reason="",
            )
        )

    reopened = evt.transition_state(
        ExamTransitionPayload(
            institution_id=inst_id,
            exam_id=exam["id"],
            expected_revision=ready["revision"],
            target_state="PREPARATION",
            reason="Perlu tambah peserta mutasi",
        )
    )["exam"]
    assert reopened["state"] == "PREPARATION"
    assert reopened["config"]["documents_stale"] is True

    archived = evt.transition_state(
        ExamTransitionPayload(
            institution_id=inst_id,
            exam_id=exam["id"],
            expected_revision=reopened["revision"],
            target_state="ARCHIVED",
        )
    )["exam"]
    with pytest.raises(AppError) as ro_err:
        evt.generate_participant_numbers(
            NumberingGeneratePayload(
                institution_id=inst_id,
                exam_id=exam["id"],
                expected_revision=archived["revision"],
                prefix="UC",
            )
        )
    assert ro_err.value.code == "PERMISSION_DENIED"


def test_groups_duplicate_requirement_clone_and_dashboard(
    evt_env: dict[str, object],
) -> None:
    evt: EvtService = evt_env["evt"]  # type: ignore[assignment]
    inst_id = str(evt_env["inst_id"])
    exam = evt.create_exam(
        ExamCreatePayload(
            institution_id=inst_id,
            year_id=str(evt_env["year_id"]),
            exam_type_id=str(evt_env["exam_type_id"]),
            title="STS Ganjil",
            semester_label="Ganjil",
            starts_on="2026-10-01",
            ends_on="2026-10-05",
        )
    )["exam"]

    grp_info = evt.list_groups(
        ExamScopedPayload(institution_id=inst_id, exam_id=exam["id"])
    )
    grp_id = grp_info["groups"][0]["id"]
    subj_id = grp_info["subjects"][0]["id"]

    with pytest.raises(ConflictError):
        evt.save_requirement(
            ExamRequirementSavePayload(
                institution_id=inst_id,
                exam_id=exam["id"],
                group_id=grp_id,
                exam_subject_id=subj_id,
                attempt_no=1,
            )
        )

    dash = evt.get_dashboard(
        ExamScopedPayload(institution_id=inst_id, exam_id=exam["id"])
    )
    assert dash["counts"]["participants"] == 2
    assert dash["counts"]["rooms"] == 1

    cloned = evt.clone_event(
        ExamClonePayload(
            institution_id=inst_id,
            source_exam_id=exam["id"],
            title="STS Genap",
            semester_label="Genap",
            starts_on="2027-03-01",
            ends_on="2027-03-05",
        )
    )["exam"]
    assert cloned["state"] == "DRAFT"
    cloned_parts = evt.list_participants(
        ExamScopedPayload(institution_id=inst_id, exam_id=cloned["id"])
    )["items"]
    assert cloned_parts == []
