"""Transactional service layer for SES-01..SES-07."""

from __future__ import annotations

import hashlib
import json
import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy.orm import Session, sessionmaker

from backend.core.db import session_scope
from backend.core.errors import AppError, ConflictError, NotFoundError, ValidationError
from backend.modules.cfg.repository import CfgRepository
from backend.modules.evt.models import AuditEvent, Exam
from backend.modules.evt.repository import EvtRepository
from backend.modules.ses.models import ExamSession, Plan, RoomPaper, RoomSession
from backend.modules.ses.repository import SesRepository
from backend.modules.ses.schemas import (
    AutoSchedulePayload,
    CalendarRules,
    CalendarUpdatePayload,
    PaperAssignPayload,
    PaperLockPayload,
    PlanCreatePayload,
    PlanPublishPayload,
    PlanScopedPayload,
    SessionDeletePayload,
    SessionSavePayload,
    local_to_utc_interval,
)
from backend.modules.ses.solver import solve_timetable
from backend.modules.ses.validator import (
    PaperAssignmentInfo,
    RequirementInfo,
    RoomInfo,
    SessionInfo,
    intervals_overlap,
    validate_plan_schedule,
)


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()


def _new_id() -> str:
    return uuid.uuid4().hex


def _check_revision(actual: int, expected: int | None) -> None:
    if expected is not None and actual != expected:
        raise AppError(
            "STALE_REVISION",
            "Draf jadwal telah berubah. Muat ulang sebelum menyimpan.",
        )


def _serialize_plan(plan: Plan) -> dict[str, Any]:
    return {
        "id": plan.id,
        "exam_id": plan.exam_id,
        "version": plan.version,
        "state": plan.state,
        "parent_id": plan.parent_id,
        "input_hash": plan.input_hash,
        "calendar": json.loads(plan.rules_json),
        "published_at": plan.published_at,
        "revision": plan.revision,
    }


def _serialize_session(s: ExamSession) -> dict[str, Any]:
    return {
        "id": s.id,
        "plan_id": s.plan_id,
        "label": s.label,
        "local_date": s.local_date,
        "starts_at": s.starts_at,
        "ends_at": s.ends_at,
        "start_local": s.start_local,
        "end_local": s.end_local,
        "sort_order": s.sort_order,
        "mode": s.mode,
        "revision": s.revision,
    }


class SesService:
    """Application service for Exam Timetable & Plan Revisions."""

    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._session_factory = session_factory
        self._repo = SesRepository()
        self._evt_repo = EvtRepository()
        self._cfg_repo = CfgRepository()

    def compute_exam_input_hash(self, session: Session, exam: Exam) -> str:
        rooms = self._evt_repo.list_rooms(session, exam.id)
        groups = self._evt_repo.list_groups(session, exam.id)
        parts = self._evt_repo.list_participants(session, exam.id)
        reqs = [
            {
                "id": r.id,
                "group_id": r.group_id,
                "subj": r.exam_subject_id,
                "dur": r.duration_min,
                "mode": r.mode,
            }
            for g in groups
            for r in self._evt_repo.list_requirements(session, g.id)
        ]
        snapshot_obj = {
            "exam_revision": exam.revision,
            "rooms": [(r.id, r.capacity_limit, r.mode) for r in rooms],
            "participants": [(p.id, p.eligibility) for p in parts],
            "requirements": reqs,
        }
        return hashlib.sha256(
            json.dumps(snapshot_obj, sort_keys=True).encode("utf-8")
        ).hexdigest()

    def _require_exam_and_tz(
        self, session: Session, institution_id: str, exam_id: str
    ) -> tuple[Exam, str]:
        inst = self._cfg_repo.get_institution(session, institution_id)
        if inst is None:
            raise NotFoundError("Lembaga tidak ditemukan.")
        exam = self._evt_repo.get_exam(session, institution_id, exam_id)
        if exam is None:
            raise NotFoundError("Kegiatan ujian tidak ditemukan.")
        return exam, inst.timezone

    def _require_draft_plan(self, session: Session, exam: Exam, plan_id: str) -> Plan:
        plan = self._repo.get_plan(session, exam.id, plan_id)
        if plan is None:
            raise NotFoundError("Revisi rencana jadwal tidak ditemukan.")
        if plan.state in ("published", "superseded"):
            raise ConflictError(
                "Versi terbit/terarsip tidak dapat diubah; buat draf revisi baru."
            )
        return plan

    def list_plans(self, institution_id: str, exam_id: str) -> dict[str, Any]:
        with session_scope(self._session_factory) as session:
            exam, _ = self._require_exam_and_tz(session, institution_id, exam_id)
            plans = self._repo.list_plans(session, exam.id)
            return {"items": [_serialize_plan(p) for p in plans]}

    def create_plan_draft(self, payload: PlanCreatePayload) -> dict[str, Any]:
        now = _now_iso()
        with session_scope(self._session_factory) as session:
            exam, _ = self._require_exam_and_tz(
                session, payload.institution_id, payload.exam_id
            )
            if exam.state == "ARCHIVED":
                raise AppError("PERMISSION_DENIED", "Kegiatan sudah diarsipkan.")

            existing = self._repo.list_plans(session, exam.id)
            next_version = max((p.version for p in existing), default=0) + 1
            input_hash = self.compute_exam_input_hash(session, exam)

            parent_rules = json.dumps(CalendarRules().model_dump())
            parent_plan = None
            if payload.clone_from_plan_id:
                parent_plan = self._repo.get_plan(
                    session, exam.id, payload.clone_from_plan_id
                )
                if parent_plan is None:
                    raise NotFoundError("Rencana sumber tidak ditemukan.")
                parent_rules = parent_plan.rules_json

            plan = Plan(
                id=_new_id(),
                exam_id=exam.id,
                version=next_version,
                state="draft",
                parent_id=parent_plan.id if parent_plan else exam.active_plan_id,
                input_hash=input_hash,
                rules_json=parent_rules,
                revision=1,
                created_at=now,
                updated_at=now,
            )
            session.add(plan)
            session.flush()

            if parent_plan is not None:
                ses_map: dict[str, str] = {}
                for old_ses in self._repo.list_sessions(session, parent_plan.id):
                    new_ses_id = _new_id()
                    ses_map[old_ses.id] = new_ses_id
                    session.add(
                        ExamSession(
                            id=new_ses_id,
                            plan_id=plan.id,
                            label=old_ses.label,
                            local_date=old_ses.local_date,
                            starts_at=old_ses.starts_at,
                            ends_at=old_ses.ends_at,
                            start_local=old_ses.start_local,
                            end_local=old_ses.end_local,
                            sort_order=old_ses.sort_order,
                            mode=old_ses.mode,
                            revision=1,
                            created_at=now,
                            updated_at=now,
                        )
                    )
                session.flush()
                rs_map: dict[str, str] = {}
                for old_rs in self._repo.list_room_sessions(session, parent_plan.id):
                    new_rs_id = _new_id()
                    rs_map[old_rs.id] = new_rs_id
                    session.add(
                        RoomSession(
                            id=new_rs_id,
                            plan_id=plan.id,
                            session_id=ses_map[old_rs.session_id],
                            exam_room_id=old_rs.exam_room_id,
                            required_staff_count=old_rs.required_staff_count,
                            revision=1,
                            created_at=now,
                            updated_at=now,
                        )
                    )
                session.flush()
                for old_rp in self._repo.list_room_papers_for_plan(
                    session, parent_plan.id
                ):
                    session.add(
                        RoomPaper(
                            id=_new_id(),
                            room_session_id=rs_map[old_rp.room_session_id],
                            requirement_id=old_rp.requirement_id,
                            group_id=old_rp.group_id,
                            locked=old_rp.locked,
                            revision=1,
                            created_at=now,
                            updated_at=now,
                        )
                    )
                session.flush()

            return {"plan": _serialize_plan(plan)}

    def update_calendar(self, payload: CalendarUpdatePayload) -> dict[str, Any]:
        now = _now_iso()
        with session_scope(self._session_factory) as session:
            exam, _ = self._require_exam_and_tz(
                session, payload.institution_id, payload.exam_id
            )
            plan = self._require_draft_plan(session, exam, payload.plan_id)
            _check_revision(plan.revision, payload.expected_revision)

            plan.rules_json = payload.calendar.model_dump_json()
            plan.state = "draft"
            plan.revision += 1
            plan.updated_at = now
            session.flush()
            return {"plan": _serialize_plan(plan)}

    def get_plan_detail(self, payload: PlanScopedPayload) -> dict[str, Any]:
        with session_scope(self._session_factory) as session:
            exam, _ = self._require_exam_and_tz(
                session, payload.institution_id, payload.exam_id
            )
            plan = self._repo.get_plan(session, exam.id, payload.plan_id)
            if plan is None:
                raise NotFoundError("Rencana jadwal tidak ditemukan.")

            sessions_rows = self._repo.list_sessions(session, plan.id)
            rooms_rows = self._evt_repo.list_rooms(session, exam.id)
            groups_rows = self._evt_repo.list_groups(session, exam.id)
            subjects_map = {
                s.id: s for s in self._evt_repo.list_subjects(session, exam.id)
            }
            rs_by_id = {
                rs.id: rs for rs in self._repo.list_room_sessions(session, plan.id)
            }
            papers_rows = self._repo.list_room_papers_for_plan(session, plan.id)

            session_overlaps: list[dict[str, Any]] = []
            for i, sa in enumerate(sessions_rows):
                for sb in sessions_rows[i + 1 :]:
                    if intervals_overlap(
                        datetime.fromisoformat(sa.starts_at),
                        datetime.fromisoformat(sa.ends_at),
                        datetime.fromisoformat(sb.starts_at),
                        datetime.fromisoformat(sb.ends_at),
                    ):
                        session_overlaps.append(
                            {
                                "session_a_id": sa.id,
                                "session_b_id": sb.id,
                                "message": (
                                    f"Interval '{sa.label}' dan '{sb.label}' "
                                    "saling tumpang tindih."
                                ),
                            }
                        )

            req_list = []
            for grp in groups_rows:
                for r in self._evt_repo.list_requirements(session, grp.id):
                    subj = subjects_map.get(r.exam_subject_id)
                    req_list.append(
                        {
                            "id": r.id,
                            "group_id": grp.id,
                            "group_label": grp.label,
                            "exam_subject_id": r.exam_subject_id,
                            "subject_code": subj.code if subj else "",
                            "subject_name": subj.name if subj else "",
                            "duration_min": r.duration_min,
                            "mode": r.mode,
                        }
                    )

            paper_items = []
            for rp in papers_rows:
                rs = rs_by_id.get(rp.room_session_id)
                if rs is None:
                    continue
                paper_items.append(
                    {
                        "id": rp.id,
                        "room_session_id": rp.room_session_id,
                        "session_id": rs.session_id,
                        "exam_room_id": rs.exam_room_id,
                        "requirement_id": rp.requirement_id,
                        "group_id": rp.group_id,
                        "locked": bool(rp.locked),
                    }
                )

            return {
                "plan": _serialize_plan(plan),
                "sessions": [_serialize_session(s) for s in sessions_rows],
                "session_overlaps": session_overlaps,
                "rooms": [
                    {
                        "id": rm.id,
                        "code": rm.code,
                        "name": rm.name,
                        "mode": rm.mode,
                        "capacity_limit": rm.capacity_limit,
                    }
                    for rm in rooms_rows
                ],
                "requirements": req_list,
                "papers": paper_items,
            }

    def save_session(self, payload: SessionSavePayload) -> dict[str, Any]:
        now = _now_iso()
        with session_scope(self._session_factory) as session:
            exam, tz_name = self._require_exam_and_tz(
                session, payload.institution_id, payload.exam_id
            )
            plan = self._require_draft_plan(session, exam, payload.plan_id)
            calendar = CalendarRules.model_validate_json(plan.rules_json)

            try:
                start_utc, end_utc = local_to_utc_interval(
                    payload.local_date,
                    payload.start_local,
                    payload.end_local,
                    tz_name,
                    allow_overnight=calendar.allow_overnight,
                )
            except ValueError as exc:
                raise ValidationError(str(exc)) from exc

            if payload.local_date in set(calendar.holidays):
                raise ValidationError(
                    f"Tanggal {payload.local_date} terdaftar sebagai hari libur."
                )

            for bw in calendar.break_windows:
                if bw.local_date and bw.local_date != payload.local_date:
                    continue
                if (
                    payload.start_local < bw.end_local
                    and bw.start_local < payload.end_local
                ):
                    raise ValidationError(
                        "Jam sesi bertabrakan dengan waktu istirahat "
                        f"({bw.start_local}–{bw.end_local})."
                    )

            if payload.id is None:
                ses = ExamSession(
                    id=_new_id(),
                    plan_id=plan.id,
                    label=payload.label.strip(),
                    local_date=payload.local_date,
                    starts_at=start_utc.isoformat(),
                    ends_at=end_utc.isoformat(),
                    start_local=payload.start_local,
                    end_local=payload.end_local,
                    sort_order=payload.sort_order,
                    mode=payload.mode,
                    revision=1,
                    created_at=now,
                    updated_at=now,
                )
                session.add(ses)
            else:
                existing_ses = self._repo.get_exam_session(session, plan.id, payload.id)
                if existing_ses is None:
                    raise NotFoundError("Sesi tidak ditemukan.")
                existing_ses.label = payload.label.strip()
                existing_ses.local_date = payload.local_date
                existing_ses.starts_at = start_utc.isoformat()
                existing_ses.ends_at = end_utc.isoformat()
                existing_ses.start_local = payload.start_local
                existing_ses.end_local = payload.end_local
                existing_ses.sort_order = payload.sort_order
                existing_ses.mode = payload.mode
                existing_ses.revision += 1
                existing_ses.updated_at = now
                ses = existing_ses

            plan.state = "draft"
            plan.revision += 1
            plan.updated_at = now
            session.flush()
            return {"session": _serialize_session(ses), "plan_revision": plan.revision}

    def delete_session(self, payload: SessionDeletePayload) -> dict[str, Any]:
        now = _now_iso()
        with session_scope(self._session_factory) as session:
            exam, _ = self._require_exam_and_tz(
                session, payload.institution_id, payload.exam_id
            )
            plan = self._require_draft_plan(session, exam, payload.plan_id)
            ses = self._repo.get_exam_session(session, plan.id, payload.session_id)
            if ses is None:
                raise NotFoundError("Sesi tidak ditemukan.")
            session.delete(ses)
            plan.state = "draft"
            plan.revision += 1
            plan.updated_at = now
            session.flush()
            return {"deleted": True, "plan_revision": plan.revision}

    def assign_paper(self, payload: PaperAssignPayload) -> dict[str, Any]:
        now = _now_iso()
        with session_scope(self._session_factory) as session:
            exam, _ = self._require_exam_and_tz(
                session, payload.institution_id, payload.exam_id
            )
            plan = self._require_draft_plan(session, exam, payload.plan_id)
            _check_revision(plan.revision, payload.expected_revision)

            ses = self._repo.get_exam_session(session, plan.id, payload.session_id)
            if ses is None:
                raise NotFoundError("Sesi tidak ditemukan.")

            rooms_map = {
                rm.id: rm for rm in self._evt_repo.list_rooms(session, exam.id)
            }
            if payload.exam_room_id not in rooms_map:
                raise NotFoundError("Ruang ujian tidak ditemukan.")

            groups = self._evt_repo.list_groups(session, exam.id)
            target_req = None
            for grp in groups:
                for r in self._evt_repo.list_requirements(session, grp.id):
                    if r.id == payload.requirement_id:
                        target_req = r
                        break
            if target_req is None:
                raise NotFoundError("Kebutuhan ujian tidak ditemukan.")

            existing_papers = self._repo.list_room_papers_for_plan(session, plan.id)
            for ep in existing_papers:
                if ep.requirement_id == payload.requirement_id and ep.locked:
                    raise ConflictError(
                        "Penempatan mapel ini terkunci dan tidak dapat dipindahkan."
                    )

            # Check candidate placement against validator BEFORE modifying DB
            rs = self._repo.get_room_session(
                session, plan.id, payload.session_id, payload.exam_room_id
            )
            if rs is None:
                rs = RoomSession(
                    id=_new_id(),
                    plan_id=plan.id,
                    session_id=payload.session_id,
                    exam_room_id=payload.exam_room_id,
                    required_staff_count=1,
                    revision=1,
                    created_at=now,
                    updated_at=now,
                )
                session.add(rs)
                session.flush()

            for ep in existing_papers:
                if ep.requirement_id == payload.requirement_id:
                    session.delete(ep)
            session.flush()

            new_paper = RoomPaper(
                id=_new_id(),
                room_session_id=rs.id,
                requirement_id=target_req.id,
                group_id=target_req.group_id,
                locked=0,
                revision=1,
                created_at=now,
                updated_at=now,
            )
            session.add(new_paper)
            session.flush()

            conflicts = [
                c
                for c in self._run_validator(session, exam, plan)
                if c["code"] != "UNASSIGNED_PAPER"
            ]
            if conflicts:
                raise ConflictError(conflicts[0]["message"])

            plan.state = "draft"
            plan.revision += 1
            plan.updated_at = now
            session.flush()
            return {"paper_id": new_paper.id, "plan_revision": plan.revision}

    def set_paper_lock(self, payload: PaperLockPayload) -> dict[str, Any]:
        now = _now_iso()
        with session_scope(self._session_factory) as session:
            exam, _ = self._require_exam_and_tz(
                session, payload.institution_id, payload.exam_id
            )
            plan = self._require_draft_plan(session, exam, payload.plan_id)
            paper = self._repo.get_room_paper(session, payload.paper_id)
            if paper is None:
                raise NotFoundError("Penempatan mapel tidak ditemukan.")
            paper.locked = 1 if payload.locked else 0
            paper.revision += 1
            paper.updated_at = now
            plan.revision += 1
            plan.updated_at = now
            session.flush()
            return {"locked": bool(paper.locked), "plan_revision": plan.revision}

    def validate_plan(self, payload: PlanScopedPayload) -> dict[str, Any]:
        now = _now_iso()
        with session_scope(self._session_factory) as session:
            exam, _ = self._require_exam_and_tz(
                session, payload.institution_id, payload.exam_id
            )
            plan = self._repo.get_plan(session, exam.id, payload.plan_id)
            if plan is None:
                raise NotFoundError("Rencana jadwal tidak ditemukan.")

            conflicts = self._run_validator(session, exam, plan)
            if not conflicts and plan.state == "draft":
                plan.state = "validated"
                plan.revision += 1
                plan.updated_at = now
                session.flush()

            return {
                "valid": len(conflicts) == 0,
                "conflicts": conflicts,
                "plan": _serialize_plan(plan),
            }

    def publish_plan(self, payload: PlanPublishPayload) -> dict[str, Any]:
        now = _now_iso()
        with session_scope(self._session_factory) as session:
            exam, _ = self._require_exam_and_tz(
                session, payload.institution_id, payload.exam_id
            )
            plan = self._require_draft_plan(session, exam, payload.plan_id)
            _check_revision(plan.revision, payload.expected_revision)

            current_hash = self.compute_exam_input_hash(session, exam)
            if current_hash != plan.input_hash:
                raise AppError(
                    "STALE_REVISION",
                    "Data sumber kegiatan berubah sejak draf dibuat. "
                    "Buat draf baru atau perbarui jadwal terlebih dahulu.",
                )

            conflicts = self._run_validator(session, exam, plan)
            if conflicts:
                raise ConflictError(
                    f"Jadwal belum valid untuk diterbitkan: {conflicts[0]['message']}"
                )

            for other in self._repo.list_plans(session, exam.id):
                if other.state == "published" and other.id != plan.id:
                    other.state = "superseded"
                    other.revision += 1
                    other.updated_at = now

            plan.state = "published"
            plan.published_at = now
            plan.revision += 1
            plan.updated_at = now
            exam.active_plan_id = plan.id
            exam.revision += 1
            exam.updated_at = now

            session.add(
                AuditEvent(
                    id=_new_id(),
                    institution_id=exam.institution_id,
                    exam_id=exam.id,
                    actor="operator",
                    action="plan.publish",
                    entity_type="plan",
                    entity_id=plan.id,
                    at=now,
                    change_summary_json=json.dumps({"version": plan.version}),
                    correlation_id="-",
                )
            )
            session.flush()
            return {"plan": _serialize_plan(plan)}

    def auto_generate_schedule(self, payload: AutoSchedulePayload) -> dict[str, Any]:
        now = _now_iso()
        with session_scope(self._session_factory) as session:
            exam, _ = self._require_exam_and_tz(
                session, payload.institution_id, payload.exam_id
            )
            plan = self._require_draft_plan(session, exam, payload.plan_id)
            _check_revision(plan.revision, payload.expected_revision)

            sessions_map, rooms_map, reqs_map, papers_list, calendar = (
                self._build_validator_inputs(session, exam, plan)
            )
            locked_papers = [p for p in papers_list if p.locked]

            result = solve_timetable(
                sessions=sessions_map,
                rooms=rooms_map,
                requirements=reqs_map,
                locked_papers=locked_papers,
                holidays=set(calendar.holidays),
                break_windows=[bw.model_dump() for bw in calendar.break_windows],
                time_limit_sec=payload.time_limit_sec,
                seed=payload.seed,
            )
            if result["status"] not in ("OPTIMAL", "FEASIBLE"):
                return {
                    "ok": False,
                    "status": result["status"],
                    "diagnostics": result["diagnostics"],
                }

            # Clear non-locked assignments and materialize draft solution
            locked_req_ids = {lp.requirement_id for lp in locked_papers}
            for rp in self._repo.list_room_papers_for_plan(session, plan.id):
                if rp.requirement_id not in locked_req_ids:
                    session.delete(rp)
            session.flush()

            for item in result["assignments"]:
                req_id = str(item["requirement_id"])
                if req_id in locked_req_ids:
                    continue
                ses_id = str(item["session_id"])
                room_id = str(item["exam_room_id"])
                rs = self._repo.get_room_session(session, plan.id, ses_id, room_id)
                if rs is None:
                    rs = RoomSession(
                        id=_new_id(),
                        plan_id=plan.id,
                        session_id=ses_id,
                        exam_room_id=room_id,
                        required_staff_count=1,
                        revision=1,
                        created_at=now,
                        updated_at=now,
                    )
                    session.add(rs)
                    session.flush()
                session.add(
                    RoomPaper(
                        id=_new_id(),
                        room_session_id=rs.id,
                        requirement_id=req_id,
                        group_id=reqs_map[req_id].group_id,
                        locked=0,
                        revision=1,
                        created_at=now,
                        updated_at=now,
                    )
                )
            session.flush()

            conflicts = self._run_validator(session, exam, plan)
            if conflicts:
                raise ConflictError(
                    f"Hasil solver gagal validasi independen: {conflicts[0]['message']}"
                )

            plan.state = "draft"
            plan.revision += 1
            plan.updated_at = now
            session.flush()
            return {
                "ok": True,
                "status": result["status"],
                "assigned_count": len(result["assignments"]),
                "plan": _serialize_plan(plan),
            }

    def _build_validator_inputs(
        self, session: Session, exam: Exam, plan: Plan
    ) -> tuple[
        dict[str, SessionInfo],
        dict[str, RoomInfo],
        dict[str, RequirementInfo],
        list[PaperAssignmentInfo],
        CalendarRules,
    ]:
        calendar = CalendarRules.model_validate_json(plan.rules_json)
        sessions_map = {
            s.id: SessionInfo(
                id=s.id,
                label=s.label,
                local_date=s.local_date,
                start_local=s.start_local,
                end_local=s.end_local,
                starts_at=datetime.fromisoformat(s.starts_at),
                ends_at=datetime.fromisoformat(s.ends_at),
                mode=s.mode,
            )
            for s in self._repo.list_sessions(session, plan.id)
        }
        rooms_map = {
            r.id: RoomInfo(
                id=r.id,
                code=r.code,
                mode=r.mode,
                capacity_limit=r.capacity_limit,
            )
            for r in self._evt_repo.list_rooms(session, exam.id)
        }
        subjects_map = {
            sb.id: sb for sb in self._evt_repo.list_subjects(session, exam.id)
        }
        reqs_map: dict[str, RequirementInfo] = {}
        for grp in self._evt_repo.list_groups(session, exam.id):
            pids = frozenset(
                m.participant_id
                for m in self._evt_repo.list_group_members(session, grp.id)
            )
            for req in self._evt_repo.list_requirements(session, grp.id):
                subj = subjects_map.get(req.exam_subject_id)
                reqs_map[req.id] = RequirementInfo(
                    id=req.id,
                    group_id=grp.id,
                    group_label=grp.label,
                    subject_id=req.exam_subject_id,
                    subject_code=subj.code if subj else "",
                    duration_min=req.duration_min,
                    mode=req.mode,
                    participant_ids=pids,
                )

        rs_map = {rs.id: rs for rs in self._repo.list_room_sessions(session, plan.id)}
        papers_list = []
        for rp in self._repo.list_room_papers_for_plan(session, plan.id):
            rs = rs_map.get(rp.room_session_id)
            if rs is None:
                continue
            papers_list.append(
                PaperAssignmentInfo(
                    paper_id=rp.id,
                    room_session_id=rp.room_session_id,
                    session_id=rs.session_id,
                    exam_room_id=rs.exam_room_id,
                    requirement_id=rp.requirement_id,
                    group_id=rp.group_id,
                    locked=bool(rp.locked),
                )
            )

        return sessions_map, rooms_map, reqs_map, papers_list, calendar

    def _run_validator(
        self, session: Session, exam: Exam, plan: Plan
    ) -> list[dict[str, Any]]:
        sessions_map, rooms_map, reqs_map, papers_list, calendar = (
            self._build_validator_inputs(session, exam, plan)
        )
        return validate_plan_schedule(
            sessions=sessions_map,
            rooms=rooms_map,
            requirements=reqs_map,
            papers=papers_list,
            holidays=set(calendar.holidays),
            break_windows=[bw.model_dump() for bw in calendar.break_windows],
        )
