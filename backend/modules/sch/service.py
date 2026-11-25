"""Transactional service layer for SCH-01..SCH-08."""

from __future__ import annotations

import importlib.metadata
import json
import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy.orm import Session, sessionmaker

from backend.core.db import session_scope
from backend.core.errors import AppError, ConflictError, NotFoundError
from backend.modules.cfg.repository import CfgRepository
from backend.modules.evt.models import Exam
from backend.modules.evt.repository import EvtRepository
from backend.modules.mst.repository import MstRepository
from backend.modules.sch.models import (
    Invigilation,
    InvigilationReserve,
    InvigilationSlot,
    SolverRun,
    StaffAvailability,
    StaffProfile,
)
from backend.modules.sch.repository import SchRepository
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
from backend.modules.sch.solver import solve_invigilation
from backend.modules.sch.validator import (
    ReserveCandidate,
    SlotCandidate,
    StaffCandidate,
    validate_invigilation_schedule,
)
from backend.modules.ses.models import Plan
from backend.modules.ses.repository import SesRepository


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()


def _new_id() -> str:
    return uuid.uuid4().hex


def _check_revision(actual: int, expected: int) -> None:
    if actual != expected:
        raise AppError(
            "STALE_REVISION",
            "Draf jadwal pengawas telah diubah. Muat ulang sebelum menyimpan.",
        )


class SchService:
    """Application service for Invigilation Scheduling (SCH-01..SCH-08)."""

    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._session_factory = session_factory
        self._repo = SchRepository()
        self._evt_repo = EvtRepository()
        self._ses_repo = SesRepository()
        self._cfg_repo = CfgRepository()
        self._mst_repo = MstRepository()

    def _require_exam(
        self, session: Session, institution_id: str, exam_id: str
    ) -> Exam:
        if self._cfg_repo.get_institution(session, institution_id) is None:
            raise NotFoundError("Lembaga tidak ditemukan.")
        exam = self._evt_repo.get_exam(session, institution_id, exam_id)
        if exam is None:
            raise NotFoundError("Kegiatan ujian tidak ditemukan.")
        return exam

    def _require_plan(
        self, session: Session, institution_id: str, exam_id: str, plan_id: str
    ) -> tuple[Exam, Plan]:
        exam = self._require_exam(session, institution_id, exam_id)
        plan = self._ses_repo.get_plan(session, exam.id, plan_id)
        if plan is None:
            raise NotFoundError("Rencana jadwal tidak ditemukan.")
        return exam, plan

    def _ensure_default_slots(
        self, session: Session, plan: Plan
    ) -> list[InvigilationSlot]:
        existing = self._repo.list_slots(session, plan.id)
        existing_rs_ids = {s.room_session_id for s in existing}
        now = _now_iso()
        added = False
        for rs in self._ses_repo.list_room_sessions(session, plan.id):
            if rs.id in existing_rs_ids:
                continue
            for idx in range(1, max(1, rs.required_staff_count) + 1):
                role = "primary" if idx == 1 else "secondary"
                session.add(
                    InvigilationSlot(
                        id=_new_id(),
                        plan_id=plan.id,
                        room_session_id=rs.id,
                        role_code=role,
                        slot_index=idx,
                        revision=1,
                        created_at=now,
                        updated_at=now,
                    )
                )
                added = True
        if added:
            session.flush()
            return self._repo.list_slots(session, plan.id)
        return existing

    def _build_candidates(
        self, session: Session, exam: Exam, plan: Plan
    ) -> tuple[
        dict[str, StaffCandidate],
        dict[str, SlotCandidate],
        list[ReserveCandidate],
        dict[str, str],
    ]:
        staff_people = self._evt_repo.list_people(session, exam.id, kind="staff")
        avail_rows = self._repo.list_availability(session, exam.id)
        avail_by_person: dict[str, list[tuple[datetime, datetime]]] = {}
        for av in avail_rows:
            if av.state == "unavailable":
                avail_by_person.setdefault(av.exam_person_id, []).append(
                    (
                        datetime.fromisoformat(av.starts_at),
                        datetime.fromisoformat(av.ends_at),
                    )
                )

        profiles_by_person = {
            pr.exam_person_id: pr for pr in self._repo.list_profiles(session, exam.id)
        }

        # Teaching assignments from MST for own-class / own-subject checks
        ta_rows = self._mst_repo.list_teaching_assignments(session, exam.institution_id)
        cls_by_id = {
            c.id: c.name
            for c in self._mst_repo.list_classes(session, exam.institution_id)
            if c.year_id == exam.year_id
        }
        subj_by_id = {
            s.id: s.code
            for s in self._mst_repo.list_subjects(session, exam.institution_id)
        }
        taught_classes_by_src: dict[str, set[str]] = {}
        taught_subjs_by_src: dict[str, set[str]] = {}
        for ta in ta_rows:
            cname = cls_by_id.get(ta.class_id)
            scode = subj_by_id.get(ta.subject_id)
            if cname:
                taught_classes_by_src.setdefault(ta.staff_id, set()).add(cname)
            if scode:
                taught_subjs_by_src.setdefault(ta.staff_id, set()).add(scode)

        staff_cands: dict[str, StaffCandidate] = {}
        for p in staff_people:
            prof = profiles_by_person.get(p.id)
            skills = (
                set(json.loads(prof.role_skills_json))
                if prof
                else {"primary", "secondary"}
            )
            staff_cands[p.id] = StaffCandidate(
                id=p.id,
                code=p.code,
                display_name=p.display_name,
                role_skills=skills,
                max_daily=prof.max_daily if prof else None,
                max_total=prof.max_total if prof else None,
                target_weight_pct=prof.target_weight_pct if prof else 100,
                unavailable_intervals=avail_by_person.get(p.id, []),
                taught_classes=taught_classes_by_src.get(p.source_id or "", set()),
                taught_subjects=taught_subjs_by_src.get(p.source_id or "", set()),
            )

        sessions_map = {s.id: s for s in self._ses_repo.list_sessions(session, plan.id)}
        rooms_map = {r.id: r for r in self._evt_repo.list_rooms(session, exam.id)}
        rs_map = {
            rs.id: rs for rs in self._ses_repo.list_room_sessions(session, plan.id)
        }

        groups_map = {g.id: g for g in self._evt_repo.list_groups(session, exam.id)}
        exam_subjs_map = {
            es.id: es.code for es in self._evt_repo.list_subjects(session, exam.id)
        }
        reqs_map: dict[str, str] = {}
        for g in groups_map.values():
            for req in self._evt_repo.list_requirements(session, g.id):
                reqs_map[req.id] = exam_subjs_map.get(req.exam_subject_id, "")

        rs_classes: dict[str, set[str]] = {}
        rs_subjs: dict[str, set[str]] = {}
        for rp in self._ses_repo.list_room_papers_for_plan(session, plan.id):
            grp = groups_map.get(rp.group_id)
            if grp and grp.label:
                rs_classes.setdefault(rp.room_session_id, set()).add(grp.label)
            sc = reqs_map.get(rp.requirement_id)
            if sc:
                rs_subjs.setdefault(rp.room_session_id, set()).add(sc)

        slot_rows = self._ensure_default_slots(session, plan)
        slot_cands: dict[str, SlotCandidate] = {}
        for sl in slot_rows:
            rs = rs_map.get(sl.room_session_id)
            if rs is None:
                continue
            ses = sessions_map.get(rs.session_id)
            rm = rooms_map.get(rs.exam_room_id)
            if ses is None or rm is None:
                continue
            slot_cands[sl.id] = SlotCandidate(
                id=sl.id,
                room_session_id=rs.id,
                session_id=ses.id,
                session_label=ses.label,
                local_date=ses.local_date,
                starts_at=datetime.fromisoformat(ses.starts_at),
                ends_at=datetime.fromisoformat(ses.ends_at),
                room_code=rm.code,
                role_code=sl.role_code,
                slot_index=sl.slot_index,
                class_labels=rs_classes.get(rs.id, set()),
                subject_codes=rs_subjs.get(rs.id, set()),
            )

        reserves_cands: list[ReserveCandidate] = []
        for rv in self._repo.list_reserves(session, plan.id):
            ses = sessions_map.get(rv.session_id)
            if ses is None:
                continue
            reserves_cands.append(
                ReserveCandidate(
                    id=rv.id,
                    session_id=ses.id,
                    session_label=ses.label,
                    starts_at=datetime.fromisoformat(ses.starts_at),
                    ends_at=datetime.fromisoformat(ses.ends_at),
                    exam_person_id=rv.exam_person_id,
                )
            )

        assign_map = {
            inv.slot_id: inv.exam_person_id
            for inv in self._repo.list_invigilations(session, plan.id)
        }
        return staff_cands, slot_cands, reserves_cands, assign_map

    def get_invigilation_detail(
        self, payload: InvigilationScopedPayload
    ) -> dict[str, Any]:
        with session_scope(self._session_factory) as session:
            exam, plan = self._require_plan(
                session, payload.institution_id, payload.exam_id, payload.plan_id
            )
            staff_cands, slot_cands, reserve_cands, assign_map = self._build_candidates(
                session, exam, plan
            )
            inv_rows = {
                inv.slot_id: inv
                for inv in self._repo.list_invigilations(session, plan.id)
            }
            validation = validate_invigilation_schedule(
                staff=staff_cands,
                slots=slot_cands,
                assignments=assign_map,
                reserves=reserve_cands,
                hard_avoid_own_class=True,
                hard_avoid_own_subject=False,
                hard_max_daily=True,
                hard_max_total=True,
            )

            avail_out = [
                {
                    "id": av.id,
                    "exam_person_id": av.exam_person_id,
                    "starts_at": av.starts_at,
                    "ends_at": av.ends_at,
                    "state": av.state,
                    "reason": av.reason,
                }
                for av in self._repo.list_availability(session, exam.id)
            ]

            slots_out = []
            for sl in slot_cands.values():
                inv = inv_rows.get(sl.id)
                person = staff_cands.get(inv.exam_person_id) if inv else None
                slots_out.append(
                    {
                        "id": sl.id,
                        "room_session_id": sl.room_session_id,
                        "session_id": sl.session_id,
                        "session_label": sl.session_label,
                        "local_date": sl.local_date,
                        "room_code": sl.room_code,
                        "role_code": sl.role_code,
                        "slot_index": sl.slot_index,
                        "exam_person_id": inv.exam_person_id if inv else None,
                        "person_name": person.display_name if person else None,
                        "locked": bool(inv.locked) if inv else False,
                    }
                )

            reserves_out = [
                {
                    "id": rv.id,
                    "session_id": rv.session_id,
                    "session_label": rv.session_label,
                    "exam_person_id": rv.exam_person_id,
                    "person_name": (
                        staff_cands[rv.exam_person_id].display_name
                        if rv.exam_person_id in staff_cands
                        else ""
                    ),
                }
                for rv in reserve_cands
            ]

            staff_out = [
                {
                    "id": p.id,
                    "code": p.code,
                    "display_name": p.display_name,
                    "role_skills": sorted(p.role_skills),
                    "max_daily": p.max_daily,
                    "max_total": p.max_total,
                    "target_weight_pct": p.target_weight_pct,
                }
                for p in staff_cands.values()
            ]

            return {
                "plan_id": plan.id,
                "plan_state": plan.state,
                "plan_revision": plan.revision,
                "staff": staff_out,
                "availability": avail_out,
                "slots": slots_out,
                "reserves": reserves_out,
                "validation": validation,
            }

    def save_availability(
        self, payload: StaffAvailabilitySavePayload
    ) -> dict[str, Any]:
        now = _now_iso()
        with session_scope(self._session_factory) as session:
            exam = self._require_exam(session, payload.institution_id, payload.exam_id)
            av = StaffAvailability(
                id=_new_id(),
                exam_id=exam.id,
                exam_person_id=payload.exam_person_id,
                starts_at=payload.starts_at,
                ends_at=payload.ends_at,
                state=payload.state,
                reason=payload.reason,
                revision=1,
                created_at=now,
                updated_at=now,
            )
            session.add(av)
            session.flush()
            return {"id": av.id}

    def delete_availability(
        self, payload: StaffAvailabilityDeletePayload
    ) -> dict[str, Any]:
        with session_scope(self._session_factory) as session:
            exam = self._require_exam(session, payload.institution_id, payload.exam_id)
            av = self._repo.get_availability(session, exam.id, payload.availability_id)
            if av is None:
                raise NotFoundError("Data ketersediaan tidak ditemukan.")
            session.delete(av)
            session.flush()
            return {"deleted": True}

    def save_staff_profile(self, payload: StaffProfileSavePayload) -> dict[str, Any]:
        now = _now_iso()
        with session_scope(self._session_factory) as session:
            exam = self._require_exam(session, payload.institution_id, payload.exam_id)
            existing = self._repo.get_profile(session, exam.id, payload.exam_person_id)
            skills_json = json.dumps(sorted(set(payload.role_skills)))
            if existing is None:
                prof = StaffProfile(
                    id=_new_id(),
                    exam_id=exam.id,
                    exam_person_id=payload.exam_person_id,
                    max_daily=payload.max_daily,
                    max_total=payload.max_total,
                    target_weight_pct=payload.target_weight_pct,
                    role_skills_json=skills_json,
                    revision=1,
                    created_at=now,
                    updated_at=now,
                )
                session.add(prof)
            else:
                existing.max_daily = payload.max_daily
                existing.max_total = payload.max_total
                existing.target_weight_pct = payload.target_weight_pct
                existing.role_skills_json = skills_json
                existing.revision += 1
                existing.updated_at = now
            session.flush()
            return {"saved": True}

    def configure_slots(self, payload: SlotConfigSavePayload) -> dict[str, Any]:
        now = _now_iso()
        with session_scope(self._session_factory) as session:
            _, plan = self._require_plan(
                session, payload.institution_id, payload.exam_id, payload.plan_id
            )
            if plan.state in ("published", "superseded"):
                raise ConflictError("Versi terbit tidak dapat diubah; buat draf baru.")
            _check_revision(plan.revision, payload.expected_revision)

            rs = next(
                (
                    item
                    for item in self._ses_repo.list_room_sessions(session, plan.id)
                    if item.id == payload.room_session_id
                ),
                None,
            )
            if rs is None:
                raise NotFoundError("Sesi ruang tidak ditemukan.")

            for old in self._repo.list_slots_for_room_session(session, plan.id, rs.id):
                session.delete(old)
            session.flush()

            counts = [
                ("primary", payload.primary_count),
                ("secondary", payload.secondary_count),
                ("proctor", payload.proctor_count),
            ]
            for role, cnt in counts:
                for idx in range(1, cnt + 1):
                    session.add(
                        InvigilationSlot(
                            id=_new_id(),
                            plan_id=plan.id,
                            room_session_id=rs.id,
                            role_code=role,
                            slot_index=idx,
                            revision=1,
                            created_at=now,
                            updated_at=now,
                        )
                    )
            rs.required_staff_count = (
                payload.primary_count + payload.secondary_count + payload.proctor_count
            )
            plan.state = "draft"
            plan.revision += 1
            plan.updated_at = now
            session.flush()
            return {"plan_revision": plan.revision}

    def solve_plan_invigilation(
        self, payload: InvigilationSolvePayload
    ) -> dict[str, Any]:
        now = _now_iso()
        with session_scope(self._session_factory) as session:
            exam, plan = self._require_plan(
                session, payload.institution_id, payload.exam_id, payload.plan_id
            )
            if plan.state in ("published", "superseded"):
                raise ConflictError("Versi terbit tidak dapat diubah; buat draf baru.")
            _check_revision(plan.revision, payload.expected_revision)

            staff_cands, slot_cands, reserve_cands, _ = self._build_candidates(
                session, exam, plan
            )
            existing_invs = self._repo.list_invigilations(session, plan.id)
            locked_map = {
                inv.slot_id: inv.exam_person_id for inv in existing_invs if inv.locked
            }

            res = solve_invigilation(
                staff=list(staff_cands.values()),
                slots=list(slot_cands.values()),
                locked_assignments=locked_map,
                rules=payload.rules,
                time_limit_sec=payload.time_limit_sec,
                seed=payload.seed,
            )

            session.add(
                SolverRun(
                    id=_new_id(),
                    exam_id=exam.id,
                    plan_id=plan.id,
                    kind="invigilation",
                    input_hash=plan.input_hash,
                    seed=payload.seed,
                    solver_version=importlib.metadata.version("ortools"),
                    weights_json=payload.rules.model_dump_json(),
                    status=res["status"],
                    score=res["objective"],
                    diagnostics_json=json.dumps(res["diagnostics"]),
                    created_at=now,
                )
            )

            if res["status"] not in ("OPTIMAL", "FEASIBLE"):
                session.flush()
                return {
                    "ok": False,
                    "status": res["status"],
                    "diagnostics": res["diagnostics"],
                }

            assignments: dict[str, str] = res["assignments"]
            validation = validate_invigilation_schedule(
                staff=staff_cands,
                slots=slot_cands,
                assignments=assignments,
                reserves=reserve_cands,
                hard_avoid_own_class=payload.rules.hard_avoid_own_class,
                hard_avoid_own_subject=payload.rules.hard_avoid_own_subject,
                hard_max_daily=payload.rules.hard_max_daily,
                hard_max_total=payload.rules.hard_max_total,
            )
            if not validation["valid"]:
                raise ConflictError(validation["hard_conflicts"][0]["message"])

            for old in existing_invs:
                session.delete(old)
            session.flush()

            for sid, pid in assignments.items():
                session.add(
                    Invigilation(
                        id=_new_id(),
                        plan_id=plan.id,
                        slot_id=sid,
                        exam_person_id=pid,
                        locked=1 if sid in locked_map else 0,
                        revision=1,
                        created_at=now,
                        updated_at=now,
                    )
                )

            plan.state = "draft"
            plan.revision += 1
            plan.updated_at = now
            session.flush()
            return {
                "ok": True,
                "status": res["status"],
                "plan_revision": plan.revision,
                "validation": validation,
            }

    def assign_invigilator(self, payload: InvigilationAssignPayload) -> dict[str, Any]:
        now = _now_iso()
        with session_scope(self._session_factory) as session:
            exam, plan = self._require_plan(
                session, payload.institution_id, payload.exam_id, payload.plan_id
            )
            if plan.state in ("published", "superseded"):
                raise ConflictError("Versi terbit tidak dapat diubah; buat draf baru.")
            _check_revision(plan.revision, payload.expected_revision)

            slot = self._repo.get_slot(session, plan.id, payload.slot_id)
            if slot is None:
                raise NotFoundError("Slot pengawas tidak ditemukan.")

            existing = self._repo.get_invigilation_by_slot(session, plan.id, slot.id)
            if payload.exam_person_id is None:
                if existing is not None:
                    session.delete(existing)
                plan.revision += 1
                plan.updated_at = now
                session.flush()
                return {"plan_revision": plan.revision}

            staff_cands, slot_cands, reserve_cands, assign_map = self._build_candidates(
                session, exam, plan
            )
            assign_map[slot.id] = payload.exam_person_id
            # Validate only assigned slots for manual edit (don't fail on other empty)
            assigned_slots = {
                sid: sc for sid, sc in slot_cands.items() if sid in assign_map
            }
            validation = validate_invigilation_schedule(
                staff=staff_cands,
                slots=assigned_slots,
                assignments=assign_map,
                reserves=reserve_cands,
                hard_avoid_own_class=payload.rules.hard_avoid_own_class,
                hard_avoid_own_subject=payload.rules.hard_avoid_own_subject,
                hard_max_daily=payload.rules.hard_max_daily,
                hard_max_total=payload.rules.hard_max_total,
            )
            if not validation["valid"]:
                raise ConflictError(validation["hard_conflicts"][0]["message"])

            if existing is None:
                session.add(
                    Invigilation(
                        id=_new_id(),
                        plan_id=plan.id,
                        slot_id=slot.id,
                        exam_person_id=payload.exam_person_id,
                        locked=1 if payload.locked else 0,
                        revision=1,
                        created_at=now,
                        updated_at=now,
                    )
                )
            else:
                existing.exam_person_id = payload.exam_person_id
                existing.locked = 1 if payload.locked else 0
                existing.revision += 1
                existing.updated_at = now

            plan.state = "draft"
            plan.revision += 1
            plan.updated_at = now
            session.flush()
            return {"plan_revision": plan.revision, "validation": validation}

    def assign_reserve(self, payload: ReserveAssignPayload) -> dict[str, Any]:
        now = _now_iso()
        with session_scope(self._session_factory) as session:
            exam, plan = self._require_plan(
                session, payload.institution_id, payload.exam_id, payload.plan_id
            )
            if plan.state in ("published", "superseded"):
                raise ConflictError("Versi terbit tidak dapat diubah; buat draf baru.")
            _check_revision(plan.revision, payload.expected_revision)

            ses = self._ses_repo.get_exam_session(session, plan.id, payload.session_id)
            if ses is None:
                raise NotFoundError("Sesi tidak ditemukan.")

            staff_cands, slot_cands, reserve_cands, assign_map = self._build_candidates(
                session, exam, plan
            )
            new_res = ReserveCandidate(
                id="candidate",
                session_id=ses.id,
                session_label=ses.label,
                starts_at=datetime.fromisoformat(ses.starts_at),
                ends_at=datetime.fromisoformat(ses.ends_at),
                exam_person_id=payload.exam_person_id,
            )
            assigned_slots = {
                sid: sc for sid, sc in slot_cands.items() if sid in assign_map
            }
            validation = validate_invigilation_schedule(
                staff=staff_cands,
                slots=assigned_slots,
                assignments=assign_map,
                reserves=[*reserve_cands, new_res],
                hard_avoid_own_class=True,
                hard_avoid_own_subject=False,
                hard_max_daily=True,
                hard_max_total=True,
            )
            if not validation["valid"]:
                raise ConflictError(validation["hard_conflicts"][0]["message"])

            rv = InvigilationReserve(
                id=_new_id(),
                plan_id=plan.id,
                session_id=ses.id,
                exam_person_id=payload.exam_person_id,
                locked=0,
                revision=1,
                created_at=now,
                updated_at=now,
            )
            session.add(rv)
            plan.revision += 1
            plan.updated_at = now
            session.flush()
            return {"id": rv.id, "plan_revision": plan.revision}

    def remove_reserve(self, payload: ReserveDeletePayload) -> dict[str, Any]:
        now = _now_iso()
        with session_scope(self._session_factory) as session:
            _, plan = self._require_plan(
                session, payload.institution_id, payload.exam_id, payload.plan_id
            )
            if plan.state in ("published", "superseded"):
                raise ConflictError("Versi terbit tidak dapat diubah; buat draf baru.")
            _check_revision(plan.revision, payload.expected_revision)

            rv = self._repo.get_reserve(session, plan.id, payload.reserve_id)
            if rv is None:
                raise NotFoundError("Data cadangan tidak ditemukan.")
            session.delete(rv)
            plan.revision += 1
            plan.updated_at = now
            session.flush()
            return {"deleted": True, "plan_revision": plan.revision}
