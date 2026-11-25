"""Typed bridge API exposed to PyWebView."""

from __future__ import annotations

import importlib.metadata
import platform
import sys
from typing import Any

import sqlalchemy
from ortools.sat.python import cp_model
from pydantic import ValidationError as PydanticValidationError

from backend.bridge.registry import MethodRegistry
from backend.bridge.schemas import BridgeRequest, EmptyPayload, JobIdPayload
from backend.core.app_shell import AppRuntime
from backend.core.errors import AppError
from backend.core.logging import reset_correlation_id, set_correlation_id
from backend.modules.cfg.schemas import (
    AcademicYearSavePayload,
    ExamTypeSavePayload,
    FirstRunPayload,
    InstitutionSavePayload,
    InstitutionScopedPayload,
    LevelApplyPresetPayload,
    LevelSavePayload,
    LogoUploadPayload,
    NumberPolicyPreviewPayload,
    NumberPolicySavePayload,
    ScopedDeletePayload,
    SettingsResetPayload,
    SettingsUpdatePayload,
)
from backend.modules.cfg.service import CfgService, preview_numbers
from backend.modules.com.schemas import (
    CommitteeMemberAssignPayload,
    CommitteeMemberRemovePayload,
    CommitteeRoleDeletePayload,
    CommitteeRoleSavePayload,
    ComScopedPayload,
    MeetingAttendanceSavePayload,
    MeetingDeletePayload,
    MeetingSavePayload,
    ProgramKerjaSavePayload,
    SignatoryDeletePayload,
    SignatorySavePayload,
)
from backend.modules.com.service import ComService
from backend.modules.doc.schemas import (
    DocBatchPayload,
    DocGeneratePayload,
    DocReprintPayload,
    DocScopedPayload,
)
from backend.modules.doc.service import DocService
from backend.modules.evt.schemas import (
    ExamClonePayload,
    ExamCreatePayload,
    ExamGroupSavePayload,
    ExamListPayload,
    ExamRequirementDeletePayload,
    ExamRequirementSavePayload,
    ExamScopedPayload,
    ExamTransitionPayload,
    NumberingGeneratePayload,
    NumberingOverridePayload,
)
from backend.modules.evt.service import EvtService
from backend.modules.exp.schemas import (
    ExpScopedPayload,
    HandoverRecordPayload,
    MatrixGeneratePayload,
    PrintComputePayload,
    PrintOverridePayload,
    SubmissionItemSavePayload,
    SubmissionReceivePayload,
    SubmissionReviewPayload,
)
from backend.modules.exp.service import ExpService
from backend.modules.fin.schemas import (
    BudgetCategoryArchivePayload,
    BudgetCategorySavePayload,
    BudgetLineSavePayload,
    BudgetVersionActionPayload,
    FinScopedPayload,
    HonorPayPayload,
    HonorRuleSavePayload,
    LedgerActionPayload,
    LedgerSavePayload,
)
from backend.modules.fin.service import FinService
from backend.modules.lpj.schemas import (
    LpjAttachmentSavePayload,
    LpjCreateVersionPayload,
    LpjEvaluationSavePayload,
    LpjExportPayload,
    LpjFinalizePayload,
    LpjScopedPayload,
    LpjSectionSavePayload,
)
from backend.modules.lpj.service import LpjService
from backend.modules.mst.schemas import (
    ClassSavePayload,
    DataQualityPayload,
    EnrollmentSavePayload,
    ExportMasterPayload,
    ImportCommitPayload,
    ImportPreviewPayload,
    MasterListPayload,
    RoomSavePayload,
    ScopedEntityDeletePayload,
    StaffSavePayload,
    StudentSavePayload,
    SubjectSavePayload,
    TeachingAssignmentSavePayload,
)
from backend.modules.mst.service import MstService
from backend.modules.ops.schemas import (
    ClosingCompletePayload,
    CommitteeAttendancePayload,
    IncidentRecordPayload,
    MakeupCreatePayload,
    OpsScopedPayload,
    RoomSessionStatePayload,
    SessionReportPayload,
    StaffAttendancePayload,
    StudentAttendancePayload,
)
from backend.modules.ops.service import OpsService
from backend.modules.rom.schemas import (
    RoomLayoutUpdatePayload,
    SeatingPrintContextPayload,
    SeatingScopedPayload,
    SeatingSolvePayload,
    SeatLockPayload,
    SeatSwapPayload,
)
from backend.modules.rom.service import RomService
from backend.modules.sch.schemas import (
    InvigilationAssignPayload,
    InvigilationScopedPayload,
    InvigilationSolvePayload,
    ReserveAssignPayload,
    ReserveDeletePayload,
    SlotConfigSavePayload,
    StaffAvailabilityDeletePayload,
    StaffAvailabilitySavePayload,
    StaffProfileSavePayload,
)
from backend.modules.sch.service import SchService
from backend.modules.ses.schemas import (
    AutoSchedulePayload,
    CalendarUpdatePayload,
    PaperAssignPayload,
    PaperLockPayload,
    PlanCreatePayload,
    PlanListPayload,
    PlanPublishPayload,
    PlanScopedPayload,
    SessionDeletePayload,
    SessionSavePayload,
)
from backend.modules.ses.service import SesService
from backend.modules.tpl.schemas import (
    LetterheadImagePayload,
    LetterheadManualPayload,
    TemplateDocxValidatePayload,
    TemplateSavePayload,
    ThemeProfileSavePayload,
    TplScopedPayload,
)
from backend.modules.tpl.service import TplService
from backend.modules.tsk.schemas import (
    ApplyPresetPayload,
    TaskDeletePayload,
    TaskDependencyDeletePayload,
    TaskDependencyPayload,
    TaskEvidencePayload,
    TaskSavePayload,
    TskScopedPayload,
)
from backend.modules.tsk.service import TskService


def _ok(request_id: str, data: Any) -> dict[str, Any]:
    return {"ok": True, "request_id": request_id, "data": data}


def _err(
    request_id: str,
    code: str,
    message: str,
    *,
    field_errors: dict[str, str] | None = None,
    details: dict[str, Any] | None = None,
    retryable: bool = False,
) -> dict[str, Any]:
    error_obj: dict[str, Any] = {
        "code": code,
        "message": message,
        "retryable": retryable,
    }
    if field_errors:
        error_obj["field_errors"] = field_errors
    if details:
        error_obj["details"] = details
    return {"ok": False, "request_id": request_id, "error": error_obj}


def _pkg_version(name: str) -> str:
    try:
        return importlib.metadata.version(name)
    except importlib.metadata.PackageNotFoundError:
        return "unknown"


def _handle_app_info(_payload: EmptyPayload) -> dict[str, Any]:
    return {
        "app_version": "0.1.0",
        "bridge_version": "1",
        "python_version": sys.version.split()[0],
        "platform": platform.platform(),
        "packages": {
            "pywebview": _pkg_version("pywebview"),
            "ortools": _pkg_version("ortools"),
            "sqlalchemy": _pkg_version("sqlalchemy"),
            "alembic": _pkg_version("alembic"),
            "pydantic": _pkg_version("pydantic"),
            "docxtpl": _pkg_version("docxtpl"),
            "reportlab": _pkg_version("reportlab"),
            "openpyxl": _pkg_version("openpyxl"),
        },
    }


def _verify_sqlite_fk() -> bool:
    engine = sqlalchemy.create_engine("sqlite:///:memory:")

    @sqlalchemy.event.listens_for(engine, "connect")
    def _enable_fk(dbapi_conn: Any, _record: Any) -> None:
        dbapi_conn.execute("PRAGMA foreign_keys=ON")

    with engine.begin() as conn:
        conn.execute(sqlalchemy.text("CREATE TABLE parent (id TEXT PRIMARY KEY)"))
        conn.execute(
            sqlalchemy.text(
                "CREATE TABLE child ("
                "id TEXT PRIMARY KEY, "
                "parent_id TEXT NOT NULL REFERENCES parent(id)"
                ")"
            )
        )
        try:
            conn.execute(sqlalchemy.text("INSERT INTO child VALUES ('c1', 'missing')"))
            return False
        except sqlalchemy.exc.IntegrityError:
            return True


def _run_small_solver() -> dict[str, Any]:
    model = cp_model.CpModel()
    x = {
        (staff, slot): model.new_bool_var(f"x_{staff}_{slot}")
        for staff in range(4)
        for slot in range(2)
    }
    for slot in range(2):
        model.add(sum(x[(staff, slot)] for staff in range(4)) == 1)
    for staff in range(4):
        model.add(sum(x[(staff, slot)] for slot in range(2)) <= 1)
    model.add(x[(0, 0)] == 0)

    solver = cp_model.CpSolver()
    solver.parameters.num_workers = 1
    solver.parameters.max_time_in_seconds = 5.0
    status = solver.solve(model)

    assignments = [
        {"staff_index": staff, "slot_index": slot}
        for (staff, slot), var in x.items()
        if solver.value(var) == 1
    ]
    return {
        "solver_status": solver.status_name(status),
        "assignments": assignments,
    }


def _handle_solver_ping(_payload: EmptyPayload) -> dict[str, Any]:
    return {
        "fk_enforced": _verify_sqlite_fk(),
        **_run_small_solver(),
    }


class BridgeApi:
    """Single allowlisted entrypoint exposed to PyWebView JS context."""

    def __init__(self, runtime: AppRuntime | None = None) -> None:
        self._runtime = runtime
        self._registry = MethodRegistry()
        self._registry.register("app.info", EmptyPayload, _handle_app_info)
        self._registry.register("spike.solver_ping", EmptyPayload, _handle_solver_ping)
        self._registry.register(
            "cfg.number_policy.preview", NumberPolicyPreviewPayload, preview_numbers
        )

        if runtime is not None:
            self._registry.register(
                "app.health",
                EmptyPayload,
                lambda _p: runtime.health(),
            )
            self._registry.register(
                "jobs.status",
                JobIdPayload,
                lambda p: runtime.job_runner.get_status(p.job_id),
            )
            self._registry.register(
                "jobs.cancel",
                JobIdPayload,
                lambda p: runtime.job_runner.cancel(p.job_id),
            )
            self._register_cfg_methods(runtime)
            self._register_mst_methods(runtime)
            self._register_evt_methods(runtime)
            self._register_ses_methods(runtime)
            self._register_rom_methods(runtime)
            self._register_sch_methods(runtime)
            self._register_com_methods(runtime)
            self._register_tsk_methods(runtime)
            self._register_exp_methods(runtime)
            self._register_ops_methods(runtime)
            self._register_tpl_methods(runtime)
            self._register_doc_methods(runtime)
            self._register_fin_methods(runtime)
            self._register_lpj_methods(runtime)

    def _register_cfg_methods(self, runtime: AppRuntime) -> None:
        cfg = CfgService(runtime.session_factory, runtime.paths)
        self._registry.register(
            "cfg.onboarding.status",
            EmptyPayload,
            lambda _p: cfg.get_onboarding_status(),
        )
        self._registry.register(
            "cfg.first_run.setup", FirstRunPayload, cfg.first_run_setup
        )
        self._registry.register(
            "cfg.institutions.list", EmptyPayload, lambda _p: cfg.list_institutions()
        )
        self._registry.register(
            "cfg.institutions.save", InstitutionSavePayload, cfg.save_institution
        )
        self._registry.register(
            "cfg.institutions.upload_logo", LogoUploadPayload, cfg.upload_logo
        )
        self._registry.register(
            "cfg.years.list",
            InstitutionScopedPayload,
            lambda p: cfg.list_years(p.institution_id),
        )
        self._registry.register(
            "cfg.years.save", AcademicYearSavePayload, cfg.save_year
        )
        self._registry.register(
            "cfg.levels.list",
            InstitutionScopedPayload,
            lambda p: cfg.list_levels(p.institution_id),
        )
        self._registry.register(
            "cfg.levels.apply_preset", LevelApplyPresetPayload, cfg.apply_level_preset
        )
        self._registry.register("cfg.levels.save", LevelSavePayload, cfg.save_level)
        self._registry.register(
            "cfg.levels.delete", ScopedDeletePayload, cfg.delete_level
        )
        self._registry.register(
            "cfg.exam_types.list",
            InstitutionScopedPayload,
            lambda p: cfg.list_exam_types(p.institution_id),
        )
        self._registry.register(
            "cfg.exam_types.save", ExamTypeSavePayload, cfg.save_exam_type
        )
        self._registry.register(
            "cfg.exam_types.delete", ScopedDeletePayload, cfg.delete_exam_type
        )
        self._registry.register(
            "cfg.number_policy.get",
            InstitutionScopedPayload,
            lambda p: cfg.get_number_policy(p.institution_id),
        )
        self._registry.register(
            "cfg.number_policy.save", NumberPolicySavePayload, cfg.save_number_policy
        )
        self._registry.register(
            "cfg.settings.get",
            InstitutionScopedPayload,
            lambda p: cfg.get_settings(p.institution_id),
        )
        self._registry.register(
            "cfg.settings.update", SettingsUpdatePayload, cfg.update_settings
        )
        self._registry.register(
            "cfg.settings.reset", SettingsResetPayload, cfg.reset_settings
        )

    def _register_mst_methods(self, runtime: AppRuntime) -> None:
        mst = MstService(runtime.session_factory, runtime.paths)
        self._registry.register(
            "mst.students.list", MasterListPayload, mst.list_students
        )
        self._registry.register(
            "mst.students.save", StudentSavePayload, mst.save_student
        )
        self._registry.register(
            "mst.students.delete", ScopedEntityDeletePayload, mst.delete_student
        )
        self._registry.register("mst.staff.list", MasterListPayload, mst.list_staff)
        self._registry.register("mst.staff.save", StaffSavePayload, mst.save_staff)
        self._registry.register(
            "mst.staff.delete", ScopedEntityDeletePayload, mst.delete_staff
        )
        self._registry.register("mst.classes.list", MasterListPayload, mst.list_classes)
        self._registry.register("mst.classes.save", ClassSavePayload, mst.save_class)
        self._registry.register(
            "mst.enrollments.save", EnrollmentSavePayload, mst.save_enrollment
        )
        self._registry.register(
            "mst.subjects.list", MasterListPayload, mst.list_subjects
        )
        self._registry.register(
            "mst.subjects.save", SubjectSavePayload, mst.save_subject
        )
        self._registry.register(
            "mst.teaching_assignments.save",
            TeachingAssignmentSavePayload,
            mst.save_teaching_assignment,
        )
        self._registry.register(
            "mst.teaching_assignments.delete",
            ScopedEntityDeletePayload,
            mst.delete_teaching_assignment,
        )
        self._registry.register("mst.rooms.list", MasterListPayload, mst.list_rooms)
        self._registry.register("mst.rooms.save", RoomSavePayload, mst.save_room)
        self._registry.register(
            "mst.imports.preview", ImportPreviewPayload, mst.preview_import
        )
        self._registry.register(
            "mst.imports.commit", ImportCommitPayload, mst.commit_import
        )
        self._registry.register(
            "mst.exports.xlsx", ExportMasterPayload, mst.export_xlsx
        )
        self._registry.register(
            "mst.quality.report", DataQualityPayload, mst.data_quality_report
        )

    def _register_evt_methods(self, runtime: AppRuntime) -> None:
        evt = EvtService(runtime.session_factory)
        self._registry.register(
            "evt.exams.list",
            ExamListPayload,
            lambda p: evt.list_exams(p.institution_id),
        )
        self._registry.register("evt.exams.create", ExamCreatePayload, evt.create_exam)
        self._registry.register(
            "evt.exams.transition", ExamTransitionPayload, evt.transition_state
        )
        self._registry.register("evt.exams.clone", ExamClonePayload, evt.clone_event)
        self._registry.register(
            "evt.exams.dashboard", ExamScopedPayload, evt.get_dashboard
        )
        self._registry.register(
            "evt.participants.list", ExamScopedPayload, evt.list_participants
        )
        self._registry.register(
            "evt.numbering.generate",
            NumberingGeneratePayload,
            evt.generate_participant_numbers,
        )
        self._registry.register(
            "evt.numbering.override",
            NumberingOverridePayload,
            evt.override_participant_number,
        )
        self._registry.register("evt.groups.list", ExamScopedPayload, evt.list_groups)
        self._registry.register("evt.groups.save", ExamGroupSavePayload, evt.save_group)
        self._registry.register(
            "evt.requirements.save", ExamRequirementSavePayload, evt.save_requirement
        )
        self._registry.register(
            "evt.requirements.delete",
            ExamRequirementDeletePayload,
            evt.delete_requirement,
        )

    def _register_ses_methods(self, runtime: AppRuntime) -> None:
        ses = SesService(runtime.session_factory)
        self._registry.register(
            "ses.plans.list",
            PlanListPayload,
            lambda p: ses.list_plans(p.institution_id, p.exam_id),
        )
        self._registry.register(
            "ses.plans.create", PlanCreatePayload, ses.create_plan_draft
        )
        self._registry.register(
            "ses.plans.detail", PlanScopedPayload, ses.get_plan_detail
        )
        self._registry.register(
            "ses.calendar.update", CalendarUpdatePayload, ses.update_calendar
        )
        self._registry.register(
            "ses.sessions.save", SessionSavePayload, ses.save_session
        )
        self._registry.register(
            "ses.sessions.delete", SessionDeletePayload, ses.delete_session
        )
        self._registry.register(
            "ses.papers.assign", PaperAssignPayload, ses.assign_paper
        )
        self._registry.register("ses.papers.lock", PaperLockPayload, ses.set_paper_lock)
        self._registry.register(
            "ses.plans.validate", PlanScopedPayload, ses.validate_plan
        )
        self._registry.register(
            "ses.plans.publish", PlanPublishPayload, ses.publish_plan
        )
        self._registry.register(
            "ses.schedule.auto_generate",
            AutoSchedulePayload,
            ses.auto_generate_schedule,
        )

    def _register_rom_methods(self, runtime: AppRuntime) -> None:
        rom = RomService(runtime.session_factory)
        self._registry.register(
            "rom.rooms.update_layout",
            RoomLayoutUpdatePayload,
            rom.update_room_layout,
        )
        self._registry.register(
            "rom.seating.detail",
            SeatingScopedPayload,
            rom.get_seating_detail,
        )
        self._registry.register(
            "rom.seating.solve",
            SeatingSolvePayload,
            rom.solve_plan_seating,
        )
        self._registry.register(
            "rom.seats.swap",
            SeatSwapPayload,
            rom.swap_seats,
        )
        self._registry.register(
            "rom.seats.lock",
            SeatLockPayload,
            rom.set_seat_lock,
        )
        self._registry.register(
            "rom.seating.print_context",
            SeatingPrintContextPayload,
            rom.get_print_context,
        )

    def _register_sch_methods(self, runtime: AppRuntime) -> None:
        sch = SchService(runtime.session_factory)
        self._registry.register(
            "sch.invigilation.detail",
            InvigilationScopedPayload,
            sch.get_invigilation_detail,
        )
        self._registry.register(
            "sch.availability.save",
            StaffAvailabilitySavePayload,
            sch.save_availability,
        )
        self._registry.register(
            "sch.availability.delete",
            StaffAvailabilityDeletePayload,
            sch.delete_availability,
        )
        self._registry.register(
            "sch.profiles.save",
            StaffProfileSavePayload,
            sch.save_staff_profile,
        )
        self._registry.register(
            "sch.slots.configure",
            SlotConfigSavePayload,
            sch.configure_slots,
        )
        self._registry.register(
            "sch.invigilation.solve",
            InvigilationSolvePayload,
            sch.solve_plan_invigilation,
        )
        self._registry.register(
            "sch.invigilation.assign",
            InvigilationAssignPayload,
            sch.assign_invigilator,
        )
        self._registry.register(
            "sch.reserves.assign",
            ReserveAssignPayload,
            sch.assign_reserve,
        )
        self._registry.register(
            "sch.reserves.delete",
            ReserveDeletePayload,
            sch.remove_reserve,
        )

    def _register_com_methods(self, runtime: AppRuntime) -> None:
        com = ComService(runtime.session_factory)
        self._registry.register("com.detail", ComScopedPayload, com.get_detail)
        self._registry.register(
            "com.roles.save", CommitteeRoleSavePayload, com.save_role
        )
        self._registry.register(
            "com.roles.delete", CommitteeRoleDeletePayload, com.delete_role
        )
        self._registry.register(
            "com.members.assign", CommitteeMemberAssignPayload, com.assign_member
        )
        self._registry.register(
            "com.members.remove", CommitteeMemberRemovePayload, com.remove_member
        )
        self._registry.register(
            "com.program.save", ProgramKerjaSavePayload, com.save_program_kerja
        )
        self._registry.register(
            "com.meetings.save", MeetingSavePayload, com.save_meeting
        )
        self._registry.register(
            "com.meetings.delete", MeetingDeletePayload, com.delete_meeting
        )
        self._registry.register(
            "com.meetings.attendance.save",
            MeetingAttendanceSavePayload,
            com.save_meeting_attendance,
        )
        self._registry.register(
            "com.signatories.save", SignatorySavePayload, com.save_signatory
        )
        self._registry.register(
            "com.signatories.delete", SignatoryDeletePayload, com.delete_signatory
        )

    def _register_tsk_methods(self, runtime: AppRuntime) -> None:
        tsk = TskService(runtime.session_factory)
        self._registry.register("tsk.detail", TskScopedPayload, tsk.get_detail)
        self._registry.register(
            "tsk.presets.apply", ApplyPresetPayload, tsk.apply_preset
        )
        self._registry.register("tsk.tasks.save", TaskSavePayload, tsk.save_task)
        self._registry.register("tsk.tasks.delete", TaskDeletePayload, tsk.delete_task)
        self._registry.register(
            "tsk.dependencies.add", TaskDependencyPayload, tsk.add_dependency
        )
        self._registry.register(
            "tsk.dependencies.remove",
            TaskDependencyDeletePayload,
            tsk.remove_dependency,
        )
        self._registry.register(
            "tsk.evidence.attach", TaskEvidencePayload, tsk.attach_evidence
        )

    def _register_exp_methods(self, runtime: AppRuntime) -> None:
        exp = ExpService(runtime.session_factory)
        self._registry.register("exp.detail", ExpScopedPayload, exp.get_detail)
        self._registry.register(
            "exp.matrix.generate", MatrixGeneratePayload, exp.generate_matrix
        )
        self._registry.register(
            "exp.items.save", SubmissionItemSavePayload, exp.save_item
        )
        self._registry.register(
            "exp.submissions.receive",
            SubmissionReceivePayload,
            exp.receive_submission,
        )
        self._registry.register(
            "exp.submissions.review",
            SubmissionReviewPayload,
            exp.review_submission,
        )
        self._registry.register(
            "exp.print.compute", PrintComputePayload, exp.compute_print_quantities
        )
        self._registry.register(
            "exp.print.override", PrintOverridePayload, exp.override_print_quantity
        )
        self._registry.register(
            "exp.handovers.record", HandoverRecordPayload, exp.record_handover
        )

    def _register_ops_methods(self, runtime: AppRuntime) -> None:
        ops = OpsService(runtime.session_factory)
        self._registry.register("ops.detail", OpsScopedPayload, ops.get_detail)
        self._registry.register(
            "ops.room_session.state",
            RoomSessionStatePayload,
            ops.update_room_session_state,
        )
        self._registry.register(
            "ops.students.attendance",
            StudentAttendancePayload,
            ops.mark_student_attendance,
        )
        self._registry.register(
            "ops.staff.attendance",
            StaffAttendancePayload,
            ops.mark_staff_attendance,
        )
        self._registry.register(
            "ops.committee.attendance",
            CommitteeAttendancePayload,
            ops.mark_committee_attendance,
        )
        self._registry.register(
            "ops.reports.save",
            SessionReportPayload,
            lambda p: ops.save_session_report(p, finalize=False),
        )
        self._registry.register(
            "ops.reports.finalize",
            SessionReportPayload,
            lambda p: ops.save_session_report(p, finalize=True),
        )
        self._registry.register(
            "ops.incidents.record", IncidentRecordPayload, ops.record_incident
        )
        self._registry.register(
            "ops.makeup.create", MakeupCreatePayload, ops.create_makeup
        )
        self._registry.register(
            "ops.closing.complete", ClosingCompletePayload, ops.complete_closing
        )

    def _register_tpl_methods(self, runtime: AppRuntime) -> None:
        tpl = TplService(runtime.session_factory)
        self._registry.register("tpl.detail", TplScopedPayload, tpl.get_detail)
        self._registry.register(
            "tpl.letterheads.save_manual",
            LetterheadManualPayload,
            tpl.save_manual_letterhead,
        )
        self._registry.register(
            "tpl.letterheads.upload_image",
            LetterheadImagePayload,
            tpl.upload_image_letterhead,
        )
        self._registry.register(
            "tpl.templates.save", TemplateSavePayload, tpl.save_template
        )
        self._registry.register(
            "tpl.docx.validate",
            TemplateDocxValidatePayload,
            tpl.validate_docx_template,
        )
        self._registry.register(
            "tpl.themes.save", ThemeProfileSavePayload, tpl.save_theme_profile
        )

    def _register_doc_methods(self, runtime: AppRuntime) -> None:
        doc = DocService(runtime.session_factory, runtime.paths)
        self._registry.register("doc.detail", DocScopedPayload, doc.get_detail)
        self._registry.register(
            "doc.generate", DocGeneratePayload, doc.generate_document
        )
        self._registry.register("doc.batch", DocBatchPayload, doc.generate_batch)
        self._registry.register("doc.reprint", DocReprintPayload, doc.reprint_document)

    def _register_fin_methods(self, runtime: AppRuntime) -> None:
        fin = FinService(runtime.session_factory)
        self._registry.register("fin.detail", FinScopedPayload, fin.get_detail)
        self._registry.register(
            "fin.categories.save", BudgetCategorySavePayload, fin.save_category
        )
        self._registry.register(
            "fin.categories.archive", BudgetCategoryArchivePayload, fin.archive_category
        )
        self._registry.register(
            "fin.budget.create_version",
            BudgetVersionActionPayload,
            fin.create_budget_version,
        )
        self._registry.register(
            "fin.budget.save_line", BudgetLineSavePayload, fin.save_budget_line
        )
        self._registry.register(
            "fin.budget.approve", BudgetVersionActionPayload, fin.approve_budget_version
        )
        self._registry.register(
            "fin.ledger.save", LedgerSavePayload, fin.save_ledger_entry
        )
        self._registry.register(
            "fin.ledger.post", LedgerActionPayload, fin.post_ledger_entry
        )
        self._registry.register(
            "fin.ledger.reverse", LedgerActionPayload, fin.reverse_ledger_entry
        )
        self._registry.register(
            "fin.honor.save_rule", HonorRuleSavePayload, fin.save_honor_rule
        )
        self._registry.register(
            "fin.honor.generate", FinScopedPayload, fin.generate_honor_lines
        )
        self._registry.register("fin.honor.pay", HonorPayPayload, fin.pay_honor_line)

    def _register_lpj_methods(self, runtime: AppRuntime) -> None:
        lpj = LpjService(runtime.session_factory, runtime.paths)
        self._registry.register("lpj.detail", LpjScopedPayload, lpj.get_detail)
        self._registry.register(
            "lpj.versions.create", LpjCreateVersionPayload, lpj.create_version
        )
        self._registry.register(
            "lpj.sections.save", LpjSectionSavePayload, lpj.save_section
        )
        self._registry.register(
            "lpj.evaluations.save", LpjEvaluationSavePayload, lpj.save_evaluation
        )
        self._registry.register(
            "lpj.attachments.save", LpjAttachmentSavePayload, lpj.save_attachment
        )
        self._registry.register("lpj.finalize", LpjFinalizePayload, lpj.finalize)
        self._registry.register("lpj.export", LpjExportPayload, lpj.export)

    def invoke(self, raw_request: dict[str, Any]) -> dict[str, Any]:
        req_id = (
            str(raw_request.get("request_id", ""))
            if isinstance(raw_request, dict)
            else ""
        )
        try:
            req = BridgeRequest.model_validate(raw_request)
        except PydanticValidationError as exc:
            return _err(
                req_id or "invalid",
                "VALIDATION",
                f"Payload bridge tidak valid: {exc.error_count()} kesalahan.",
            )

        if self._registry.get(req.method) is None:
            return _err(
                req.request_id,
                "METHOD_NOT_ALLOWED",
                f"Metode '{req.method}' tidak terdaftar pada allowlist.",
            )

        token = set_correlation_id(req.request_id)
        try:
            data = self._registry.dispatch(req.method, req.payload)
            if self._runtime is not None:
                self._runtime.logger.info(
                    "bridge.invoke",
                    extra={"extra_data": {"method": req.method, "ok": True}},
                )
            return _ok(req.request_id, data)
        except AppError as exc:
            if self._runtime is not None:
                self._runtime.logger.warning(
                    "bridge.app_error",
                    extra={"extra_data": {"method": req.method, "code": exc.code}},
                )
            return _err(
                req.request_id,
                exc.code,
                exc.message,
                field_errors=exc.field_errors,
                details=exc.details,
                retryable=exc.retryable,
            )
        except Exception:
            if self._runtime is not None:
                self._runtime.logger.exception(
                    "bridge.internal_error",
                    extra={"extra_data": {"method": req.method}},
                )
            return _err(
                req.request_id,
                "INTERNAL",
                "Terjadi kesalahan internal saat memproses permintaan.",
                retryable=True,
            )
        finally:
            reset_correlation_id(token)
