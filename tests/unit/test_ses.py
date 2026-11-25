"""Unit tests for SES-01..SES-07 timetable, validator, revisions, and CP-SAT solver."""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest

from backend.core.app_shell import AppRuntime, bootstrap_runtime
from backend.core.errors import AppError, ConflictError, ValidationError
from backend.modules.cfg.schemas import FirstRunPayload
from backend.modules.cfg.service import CfgService
from backend.modules.evt.schemas import ExamCreatePayload
from backend.modules.evt.service import EvtService
from backend.modules.mst.schemas import (
    ClassSavePayload,
    EnrollmentSavePayload,
    RoomLayoutConfig,
    RoomSavePayload,
    StudentSavePayload,
    SubjectSavePayload,
)
from backend.modules.mst.service import MstService
from backend.modules.ses.schemas import (
    AutoSchedulePayload,
    BreakWindow,
    CalendarRules,
    CalendarUpdatePayload,
    PaperAssignPayload,
    PaperLockPayload,
    PlanCreatePayload,
    PlanPublishPayload,
    PlanScopedPayload,
    SessionSavePayload,
)
from backend.modules.ses.service import SesService


@pytest.fixture()
def ses_env(tmp_path: Path) -> Iterator[dict[str, Any]]:
    runtime: AppRuntime = bootstrap_runtime(
        workspace_root=tmp_path, institution_slug="ses_unit"
    )
    cfg = CfgService(runtime.session_factory, runtime.paths)
    mst = MstService(runtime.session_factory, runtime.paths)
    evt = EvtService(runtime.session_factory)
    ses = SesService(runtime.session_factory)

    inst = cfg.first_run_setup(
        FirstRunPayload(
            name="MTs SES",
            level_preset="SMP/MTs",
            academic_year_label="2026/2027",
        )
    )["institution"]
    inst_id = str(inst["id"])
    year_id = str(cfg.list_years(inst_id)["items"][0]["id"])
    level_id = str(cfg.list_levels(inst_id)["items"][0]["id"])
    et_id = str(cfg.list_exam_types(inst_id)["items"][0]["id"])

    cls_a = mst.save_class(
        ClassSavePayload(
            institution_id=inst_id, year_id=year_id, level_id=level_id, name="VII-A"
        )
    )["class_item"]
    s1 = mst.save_student(
        StudentSavePayload(institution_id=inst_id, nis="0001", full_name="Nabila")
    )["student"]
    mst.save_enrollment(
        EnrollmentSavePayload(
            institution_id=inst_id,
            student_id=s1["id"],
            class_id=cls_a["id"],
            year_id=year_id,
        )
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
        SubjectSavePayload(institution_id=inst_id, code="BIN", name="B. Indonesia")
    )
    mst.save_subject(
        SubjectSavePayload(institution_id=inst_id, code="MAT", name="Matematika")
    )

    exam = evt.create_exam(
        ExamCreatePayload(
            institution_id=inst_id,
            year_id=year_id,
            exam_type_id=et_id,
            title="SAS Ganjil",
            semester_label="Ganjil",
            starts_on="2026-11-30",
            ends_on="2026-12-08",
        )
    )["exam"]

    yield {
        "evt": evt,
        "ses": ses,
        "inst_id": inst_id,
        "exam": exam,
    }
    runtime.shutdown()


def test_calendar_rules_and_distinct_overlapping_sessions_detected(
    ses_env: dict[str, Any],
) -> None:
    ses: SesService = ses_env["ses"]
    inst_id = str(ses_env["inst_id"])
    exam_id = str(ses_env["exam"]["id"])

    plan = ses.create_plan_draft(
        PlanCreatePayload(institution_id=inst_id, exam_id=exam_id)
    )["plan"]

    plan = ses.update_calendar(
        CalendarUpdatePayload(
            institution_id=inst_id,
            exam_id=exam_id,
            plan_id=plan["id"],
            expected_revision=plan["revision"],
            calendar=CalendarRules(
                holidays=["2026-12-01"],
                break_windows=[BreakWindow(start_local="09:00", end_local="09:30")],
            ),
        )
    )["plan"]

    # Overnight rejected
    with pytest.raises(ValidationError):
        ses.save_session(
            SessionSavePayload(
                institution_id=inst_id,
                exam_id=exam_id,
                plan_id=plan["id"],
                label="Malam",
                local_date="2026-11-30",
                start_local="22:00",
                end_local="01:00",
            )
        )

    # Holiday rejected
    with pytest.raises(ValidationError):
        ses.save_session(
            SessionSavePayload(
                institution_id=inst_id,
                exam_id=exam_id,
                plan_id=plan["id"],
                label="Libur",
                local_date="2026-12-01",
                start_local="07:30",
                end_local="09:00",
            )
        )

    # Break window overlap rejected
    with pytest.raises(ValidationError):
        ses.save_session(
            SessionSavePayload(
                institution_id=inst_id,
                exam_id=exam_id,
                plan_id=plan["id"],
                label="Nabrak Istirahat",
                local_date="2026-11-30",
                start_local="08:00",
                end_local="09:30",
            )
        )

    # Two distinct sessions with overlapping intervals detected
    ses.save_session(
        SessionSavePayload(
            institution_id=inst_id,
            exam_id=exam_id,
            plan_id=plan["id"],
            label="Sesi A",
            local_date="2026-11-30",
            start_local="07:30",
            end_local="09:00",
        )
    )
    ses.save_session(
        SessionSavePayload(
            institution_id=inst_id,
            exam_id=exam_id,
            plan_id=plan["id"],
            label="Sesi B",
            local_date="2026-11-30",
            start_local="08:00",
            end_local="09:00",
        )
    )
    detail = ses.get_plan_detail(
        PlanScopedPayload(institution_id=inst_id, exam_id=exam_id, plan_id=plan["id"])
    )
    assert len(detail["session_overlaps"]) == 1


def test_assign_lock_publish_stale_and_auto_solver(ses_env: dict[str, Any]) -> None:
    evt: EvtService = ses_env["evt"]
    ses: SesService = ses_env["ses"]
    inst_id = str(ses_env["inst_id"])
    exam_id = str(ses_env["exam"]["id"])

    plan = ses.create_plan_draft(
        PlanCreatePayload(institution_id=inst_id, exam_id=exam_id)
    )["plan"]

    s1 = ses.save_session(
        SessionSavePayload(
            institution_id=inst_id,
            exam_id=exam_id,
            plan_id=plan["id"],
            label="Sesi 1",
            local_date="2026-11-30",
            start_local="07:30",
            end_local="09:00",
            sort_order=1,
        )
    )["session"]
    s2 = ses.save_session(
        SessionSavePayload(
            institution_id=inst_id,
            exam_id=exam_id,
            plan_id=plan["id"],
            label="Sesi 2",
            local_date="2026-11-30",
            start_local="09:30",
            end_local="11:00",
            sort_order=2,
        )
    )["session"]

    detail = ses.get_plan_detail(
        PlanScopedPayload(institution_id=inst_id, exam_id=exam_id, plan_id=plan["id"])
    )
    room_id = detail["rooms"][0]["id"]
    reqs = detail["requirements"]
    assert len(reqs) == 2

    # Assign req[0] to s1 and lock it
    assigned = ses.assign_paper(
        PaperAssignPayload(
            institution_id=inst_id,
            exam_id=exam_id,
            plan_id=plan["id"],
            expected_revision=detail["plan"]["revision"],
            requirement_id=reqs[0]["id"],
            session_id=s1["id"],
            exam_room_id=room_id,
        )
    )
    lock_res = ses.set_paper_lock(
        PaperLockPayload(
            institution_id=inst_id,
            exam_id=exam_id,
            plan_id=plan["id"],
            paper_id=assigned["paper_id"],
            locked=True,
        )
    )

    # Moving locked paper fails
    with pytest.raises(ConflictError):
        ses.assign_paper(
            PaperAssignPayload(
                institution_id=inst_id,
                exam_id=exam_id,
                plan_id=plan["id"],
                expected_revision=lock_res["plan_revision"],
                requirement_id=reqs[0]["id"],
                session_id=s2["id"],
                exam_room_id=room_id,
            )
        )

    # Validation fails while req[1] is unassigned
    val_fail = ses.validate_plan(
        PlanScopedPayload(institution_id=inst_id, exam_id=exam_id, plan_id=plan["id"])
    )
    assert val_fail["valid"] is False
    assert val_fail["conflicts"][0]["code"] == "UNASSIGNED_PAPER"

    # CP-SAT auto-generate fills req[1] while respecting locked req[0]
    auto_res = ses.auto_generate_schedule(
        AutoSchedulePayload(
            institution_id=inst_id,
            exam_id=exam_id,
            plan_id=plan["id"],
            expected_revision=lock_res["plan_revision"],
        )
    )
    assert auto_res["ok"] is True
    assert auto_res["assigned_count"] == 2

    val_ok = ses.validate_plan(
        PlanScopedPayload(institution_id=inst_id, exam_id=exam_id, plan_id=plan["id"])
    )
    assert val_ok["valid"] is True
    assert val_ok["plan"]["state"] == "validated"

    # Publish atomically
    pub = ses.publish_plan(
        PlanPublishPayload(
            institution_id=inst_id,
            exam_id=exam_id,
            plan_id=plan["id"],
            expected_revision=val_ok["plan"]["revision"],
        )
    )["plan"]
    assert pub["state"] == "published"

    # Clone draft v2 and test stale input blocking publish when exam changes
    draft2 = ses.create_plan_draft(
        PlanCreatePayload(
            institution_id=inst_id,
            exam_id=exam_id,
            clone_from_plan_id=pub["id"],
        )
    )["plan"]
    assert draft2["version"] == 2

    # Mutate exam revision via numbering
    from backend.modules.evt.schemas import NumberingGeneratePayload

    evt.generate_participant_numbers(
        NumberingGeneratePayload(
            institution_id=inst_id,
            exam_id=exam_id,
            expected_revision=2,
            prefix="UC",
        )
    )
    with pytest.raises(AppError) as stale_err:
        ses.publish_plan(
            PlanPublishPayload(
                institution_id=inst_id,
                exam_id=exam_id,
                plan_id=draft2["id"],
                expected_revision=draft2["revision"],
            )
        )
    assert stale_err.value.code == "STALE_REVISION"
