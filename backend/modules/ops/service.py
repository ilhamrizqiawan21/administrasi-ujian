"""Transactional service layer for OPS-01..OPS-08."""

from __future__ import annotations

import json
import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy.orm import Session, sessionmaker

from backend.core.db import session_scope
from backend.core.errors import ConflictError, NotFoundError
from backend.modules.cfg.repository import CfgRepository
from backend.modules.evt.models import Exam
from backend.modules.evt.repository import EvtRepository
from backend.modules.exp.repository import ExpRepository
from backend.modules.ops.models import (
    CommitteeAttendance,
    Incident,
    MakeupLink,
    ParticipantAttendance,
    RoomSessionState,
    SessionReport,
    StaffAttendance,
)
from backend.modules.ops.repository import OpsRepository
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
from backend.modules.rom.repository import RomRepository
from backend.modules.sch.repository import SchRepository
from backend.modules.sch.validator import intervals_overlap
from backend.modules.ses.models import Plan
from backend.modules.ses.repository import SesRepository


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()


def _new_id() -> str:
    return uuid.uuid4().hex


def derive_attendance_counts(states: list[str]) -> dict[str, int]:
    """Derive counts keeping unrecorded strictly distinct from absent (OPS-01)."""
    counts = {
        "total": len(states),
        "unrecorded": 0,
        "present": 0,
        "sick": 0,
        "excused": 0,
        "absent": 0,
        "late": 0,
    }
    for st in states:
        if st in counts:
            counts[st] += 1
        else:
            counts["unrecorded"] += 1
    return counts


class OpsService:
    """Application service for Exam Execution Operations (OPS-01..OPS-08)."""

    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._session_factory = session_factory
        self._repo = OpsRepository()
        self._evt_repo = EvtRepository()
        self._ses_repo = SesRepository()
        self._rom_repo = RomRepository()
        self._sch_repo = SchRepository()
        self._exp_repo = ExpRepository()
        self._cfg_repo = CfgRepository()

    def _require_plan(
        self, session: Session, institution_id: str, exam_id: str, plan_id: str
    ) -> tuple[Exam, Plan]:
        if self._cfg_repo.get_institution(session, institution_id) is None:
            raise NotFoundError("Lembaga tidak ditemukan.")
        exam = self._evt_repo.get_exam(session, institution_id, exam_id)
        if exam is None:
            raise NotFoundError("Kegiatan ujian tidak ditemukan.")
        plan = self._ses_repo.get_plan(session, exam.id, plan_id)
        if plan is None:
            raise NotFoundError("Rencana jadwal tidak ditemukan.")
        return exam, plan

    def get_detail(self, payload: OpsScopedPayload) -> dict[str, Any]:
        with session_scope(self._session_factory) as session:
            exam, plan = self._require_plan(
                session, payload.institution_id, payload.exam_id, payload.plan_id
            )
            sessions_map = {
                s.id: s for s in self._ses_repo.list_sessions(session, plan.id)
            }
            rooms_map = {r.id: r for r in self._evt_repo.list_rooms(session, exam.id)}
            people_map = {p.id: p for p in self._evt_repo.list_people(session, exam.id)}
            parts = {
                pt.id: pt for pt in self._evt_repo.list_participants(session, exam.id)
            }

            rs_states = {
                st.room_session_id: st
                for st in self._repo.list_room_session_states(session, plan.id)
            }
            att_by_sitting = {
                a.sitting_id: a
                for a in self._repo.list_participant_attendance(session, exam.id)
            }
            reports_map = {
                r.room_session_id: r
                for r in self._repo.list_session_reports(session, exam.id)
            }

            sittings = self._rom_repo.list_sittings(session, plan.id)
            sittings_by_rs: dict[str, list[dict[str, Any]]] = {}
            for sit in sittings:
                att = att_by_sitting.get(sit.id)
                pt = parts.get(sit.participant_id)
                person = people_map.get(pt.exam_person_id) if pt else None
                state = att.state if att else "unrecorded"
                sittings_by_rs.setdefault(sit.room_session_id, []).append(
                    {
                        "sitting_id": sit.id,
                        "participant_id": sit.participant_id,
                        "participant_number": pt.participant_number if pt else None,
                        "display_name": person.display_name if person else "",
                        "state": state,
                        "note": att.note if att else "",
                    }
                )

            room_sessions_out = []
            for rs in self._ses_repo.list_room_sessions(session, plan.id):
                ses = sessions_map.get(rs.session_id)
                rm = rooms_map.get(rs.exam_room_id)
                rs_sits = sittings_by_rs.get(rs.id, [])
                counts = derive_attendance_counts([s["state"] for s in rs_sits])
                st_row = rs_states.get(rs.id)
                rep = reports_map.get(rs.id)
                room_sessions_out.append(
                    {
                        "room_session_id": rs.id,
                        "session_id": rs.session_id,
                        "session_label": ses.label if ses else "",
                        "local_date": ses.local_date if ses else "",
                        "room_code": rm.code if rm else "",
                        "room_name": rm.name if rm else "",
                        "actual_state": st_row.actual_state if st_row else "scheduled",
                        "counts": counts,
                        "sittings": rs_sits,
                        "report": {
                            "remarks": rep.remarks if rep else "",
                            "finalized_at": rep.finalized_at if rep else None,
                        },
                    }
                )

            staff_att_map = {
                sa.slot_id: sa
                for sa in self._repo.list_staff_attendance(session, exam.id)
            }
            inv_by_slot = {
                inv.slot_id: inv.exam_person_id
                for inv in self._sch_repo.list_invigilations(session, plan.id)
            }
            slots_out = []
            for sl in self._sch_repo.list_slots(session, plan.id):
                planned_id = inv_by_slot.get(sl.id)
                sa = staff_att_map.get(sl.id)
                actual_id = sa.actual_person_id if sa else planned_id
                slots_out.append(
                    {
                        "slot_id": sl.id,
                        "room_session_id": sl.room_session_id,
                        "role_code": sl.role_code,
                        "planned_person_id": planned_id,
                        "planned_name": (
                            people_map[planned_id].display_name
                            if planned_id and planned_id in people_map
                            else None
                        ),
                        "actual_person_id": actual_id,
                        "actual_name": (
                            people_map[actual_id].display_name
                            if actual_id and actual_id in people_map
                            else None
                        ),
                        "state": sa.state if sa else "unrecorded",
                    }
                )

            com_att_out = [
                {
                    "id": ca.id,
                    "att_date": ca.att_date,
                    "shift": ca.shift,
                    "exam_person_id": ca.exam_person_id,
                    "person_name": (
                        people_map[ca.exam_person_id].display_name
                        if ca.exam_person_id in people_map
                        else ""
                    ),
                    "state": ca.state,
                    "note": ca.note,
                }
                for ca in self._repo.list_committee_attendance(session, exam.id)
            ]

            incidents_out = []
            for inc in self._repo.list_incidents(session, exam.id):
                if inc.confidential and not payload.include_confidential:
                    note_val = "[Catatan rahasia disembunyikan]"
                else:
                    note_val = inc.note
                incidents_out.append(
                    {
                        "id": inc.id,
                        "room_session_id": inc.room_session_id,
                        "type_code": inc.type_code,
                        "severity": inc.severity,
                        "note": note_val,
                        "resolution": inc.resolution,
                        "confidential": bool(inc.confidential),
                        "recorded_at": inc.recorded_at,
                    }
                )

            makeups_out = [
                {
                    "id": mk.id,
                    "original_sitting_id": mk.original_sitting_id,
                    "target_room_session_id": mk.target_room_session_id,
                    "reason": mk.reason,
                }
                for mk in self._repo.list_makeup_links(session, exam.id)
            ]

            return {
                "staff": [
                    {"id": p.id, "code": p.code, "display_name": p.display_name}
                    for p in people_map.values()
                    if p.kind == "staff"
                ],
                "room_sessions": room_sessions_out,
                "staff_slots": slots_out,
                "committee_attendance": com_att_out,
                "incidents": incidents_out,
                "makeups": makeups_out,
            }

    def update_room_session_state(
        self, payload: RoomSessionStatePayload
    ) -> dict[str, Any]:
        now = _now_iso()
        with session_scope(self._session_factory) as session:
            _, plan = self._require_plan(
                session, payload.institution_id, payload.exam_id, payload.plan_id
            )
            st = self._repo.get_room_session_state(session, payload.room_session_id)
            if st is None:
                st = RoomSessionState(
                    id=_new_id(),
                    plan_id=plan.id,
                    room_session_id=payload.room_session_id,
                    actual_state=payload.actual_state,
                    started_at=now if payload.actual_state == "in_progress" else None,
                    finished_at=now if payload.actual_state == "finished" else None,
                    updated_at=now,
                )
                session.add(st)
            else:
                st.actual_state = payload.actual_state
                if payload.actual_state == "in_progress" and st.started_at is None:
                    st.started_at = now
                if payload.actual_state == "finished":
                    st.finished_at = now
                st.updated_at = now
            session.flush()
            return {"actual_state": st.actual_state}

    def mark_student_attendance(
        self, payload: StudentAttendancePayload
    ) -> dict[str, Any]:
        now = _now_iso()
        with session_scope(self._session_factory) as session:
            if self._cfg_repo.get_institution(session, payload.institution_id) is None:
                raise NotFoundError("Lembaga tidak ditemukan.")
            exam = self._evt_repo.get_exam(
                session, payload.institution_id, payload.exam_id
            )
            if exam is None:
                raise NotFoundError("Kegiatan ujian tidak ditemukan.")

            updated = 0
            for sid in set(payload.sitting_ids):
                att = self._repo.get_participant_attendance(session, sid)
                if att is None:
                    session.add(
                        ParticipantAttendance(
                            id=_new_id(),
                            exam_id=exam.id,
                            sitting_id=sid,
                            state=payload.state,
                            recorded_at=now,
                            note=payload.note,
                            revision=1,
                            updated_at=now,
                        )
                    )
                else:
                    att.state = payload.state
                    att.note = payload.note
                    att.recorded_at = now
                    att.revision += 1
                    att.updated_at = now
                updated += 1
            session.flush()
            return {"updated_count": updated}

    def mark_staff_attendance(self, payload: StaffAttendancePayload) -> dict[str, Any]:
        now = _now_iso()
        with session_scope(self._session_factory) as session:
            exam, plan = self._require_plan(
                session, payload.institution_id, payload.exam_id, payload.plan_id
            )
            slot = self._sch_repo.get_slot(session, plan.id, payload.slot_id)
            if slot is None:
                raise NotFoundError("Slot pengawas tidak ditemukan.")

            inv = self._sch_repo.get_invigilation_by_slot(session, plan.id, slot.id)
            planned_id = inv.exam_person_id if inv else None
            actual_id = payload.actual_person_id or planned_id

            # OPS-03: validate replacement has no overlap in the same interval
            if payload.state == "substituted" and actual_id:
                rs_map = {
                    rs.id: rs
                    for rs in self._ses_repo.list_room_sessions(session, plan.id)
                }
                ses_map = {
                    s.id: s for s in self._ses_repo.list_sessions(session, plan.id)
                }
                target_rs = rs_map.get(slot.room_session_id)
                target_ses = ses_map.get(target_rs.session_id) if target_rs else None
                if target_ses:
                    t_start = datetime.fromisoformat(target_ses.starts_at)
                    t_end = datetime.fromisoformat(target_ses.ends_at)
                    all_slots = {
                        s.id: s for s in self._sch_repo.list_slots(session, plan.id)
                    }
                    staff_att_map = {
                        sa.slot_id: sa
                        for sa in self._repo.list_staff_attendance(session, exam.id)
                    }
                    for other_inv in self._sch_repo.list_invigilations(
                        session, plan.id
                    ):
                        if other_inv.slot_id == slot.id:
                            continue
                        sa_other = staff_att_map.get(other_inv.slot_id)
                        eff_pid = (
                            sa_other.actual_person_id
                            if sa_other and sa_other.actual_person_id
                            else other_inv.exam_person_id
                        )
                        if eff_pid != actual_id:
                            continue
                        o_slot = all_slots.get(other_inv.slot_id)
                        o_rs = rs_map.get(o_slot.room_session_id) if o_slot else None
                        o_ses = ses_map.get(o_rs.session_id) if o_rs else None
                        if o_ses and intervals_overlap(
                            t_start,
                            t_end,
                            datetime.fromisoformat(o_ses.starts_at),
                            datetime.fromisoformat(o_ses.ends_at),
                        ):
                            raise ConflictError(
                                "Pengganti pengawas bentrok waktu dengan tugas lain."
                            )

            existing = self._repo.get_staff_attendance(session, slot.id)
            if existing is None:
                session.add(
                    StaffAttendance(
                        id=_new_id(),
                        exam_id=exam.id,
                        slot_id=slot.id,
                        planned_person_id=planned_id,
                        actual_person_id=actual_id,
                        state=payload.state,
                        recorded_at=now,
                        approved_by=payload.approved_by,
                        note=payload.note,
                        revision=1,
                        updated_at=now,
                    )
                )
            else:
                existing.actual_person_id = actual_id
                existing.state = payload.state
                existing.approved_by = payload.approved_by
                existing.note = payload.note
                existing.recorded_at = now
                existing.revision += 1
                existing.updated_at = now
            session.flush()
            return {"state": payload.state, "actual_person_id": actual_id}

    def mark_committee_attendance(
        self, payload: CommitteeAttendancePayload
    ) -> dict[str, Any]:
        now = _now_iso()
        with session_scope(self._session_factory) as session:
            if self._cfg_repo.get_institution(session, payload.institution_id) is None:
                raise NotFoundError("Lembaga tidak ditemukan.")
            exam = self._evt_repo.get_exam(
                session, payload.institution_id, payload.exam_id
            )
            if exam is None:
                raise NotFoundError("Kegiatan ujian tidak ditemukan.")

            existing = self._repo.get_committee_attendance(
                session,
                exam.id,
                payload.att_date,
                payload.shift,
                payload.exam_person_id,
            )
            if existing is None:
                ca = CommitteeAttendance(
                    id=_new_id(),
                    exam_id=exam.id,
                    att_date=payload.att_date,
                    shift=payload.shift,
                    exam_person_id=payload.exam_person_id,
                    state=payload.state,
                    note=payload.note,
                    recorded_at=now,
                    updated_at=now,
                )
                session.add(ca)
                session.flush()
                return {"id": ca.id}
            existing.state = payload.state
            existing.note = payload.note
            existing.recorded_at = now
            existing.updated_at = now
            session.flush()
            return {"id": existing.id}

    def save_session_report(
        self, payload: SessionReportPayload, *, finalize: bool = False
    ) -> dict[str, Any]:
        now = _now_iso()
        with session_scope(self._session_factory) as session:
            exam, plan = self._require_plan(
                session, payload.institution_id, payload.exam_id, payload.plan_id
            )
            rep = self._repo.get_session_report(session, payload.room_session_id)
            if rep is not None and rep.finalized_at is not None:
                raise ConflictError(
                    "Berita acara yang sudah difinalisasi bersifat beku."
                )

            att_by_sitting = {
                a.sitting_id: a
                for a in self._repo.list_participant_attendance(session, exam.id)
            }
            sittings = [
                s
                for s in self._rom_repo.list_sittings(session, plan.id)
                if s.room_session_id == payload.room_session_id
            ]
            counts = derive_attendance_counts(
                [
                    att_by_sitting[s.id].state
                    if s.id in att_by_sitting
                    else "unrecorded"
                    for s in sittings
                ]
            )
            warnings: list[str] = []
            if counts["unrecorded"] > 0:
                warnings.append(
                    f"Masih ada {counts['unrecorded']} peserta belum dicatat."
                )

            signer_json = json.dumps({"signer_name": payload.signer_name})
            counts_json = json.dumps(counts)
            if rep is None:
                rep = SessionReport(
                    id=_new_id(),
                    exam_id=exam.id,
                    room_session_id=payload.room_session_id,
                    remarks=payload.remarks,
                    signer_snapshot_json=signer_json,
                    counts_snapshot_json=counts_json,
                    finalized_at=now if finalize else None,
                    revision=1,
                    updated_at=now,
                )
                session.add(rep)
            else:
                rep.remarks = payload.remarks
                rep.signer_snapshot_json = signer_json
                rep.counts_snapshot_json = counts_json
                if finalize:
                    rep.finalized_at = now
                rep.revision += 1
                rep.updated_at = now
            session.flush()
            return {
                "id": rep.id,
                "finalized": rep.finalized_at is not None,
                "warnings": warnings,
            }

    def record_incident(self, payload: IncidentRecordPayload) -> dict[str, Any]:
        now = _now_iso()
        with session_scope(self._session_factory) as session:
            if self._cfg_repo.get_institution(session, payload.institution_id) is None:
                raise NotFoundError("Lembaga tidak ditemukan.")
            exam = self._evt_repo.get_exam(
                session, payload.institution_id, payload.exam_id
            )
            if exam is None:
                raise NotFoundError("Kegiatan ujian tidak ditemukan.")
            inc = Incident(
                id=_new_id(),
                exam_id=exam.id,
                room_session_id=payload.room_session_id,
                type_code=payload.type_code,
                severity=payload.severity,
                participant_id=payload.participant_id,
                note=payload.note,
                resolution=payload.resolution,
                confidential=1 if payload.confidential else 0,
                recorded_at=now,
                created_at=now,
            )
            session.add(inc)
            session.flush()
            return {"id": inc.id}

    def create_makeup(self, payload: MakeupCreatePayload) -> dict[str, Any]:
        now = _now_iso()
        with session_scope(self._session_factory) as session:
            exam, plan = self._require_plan(
                session, payload.institution_id, payload.exam_id, payload.plan_id
            )
            att = self._repo.get_participant_attendance(
                session, payload.original_sitting_id
            )
            if att is None or att.state not in ("absent", "sick", "excused"):
                raise ConflictError(
                    "Susulan hanya untuk peserta tidak hadir/sakit/izin."
                )
            existing_links = self._repo.list_makeup_links(session, exam.id)
            if any(
                mk.original_sitting_id == payload.original_sitting_id
                for mk in existing_links
            ):
                raise ConflictError(
                    "Peserta pada sesi ini sudah memiliki jadwal susulan."
                )
            if not any(
                rs.id == payload.target_room_session_id
                for rs in self._ses_repo.list_room_sessions(session, plan.id)
            ):
                raise NotFoundError("Sesi ruang tujuan susulan tidak ditemukan.")

            mk = MakeupLink(
                id=_new_id(),
                exam_id=exam.id,
                original_sitting_id=payload.original_sitting_id,
                makeup_sitting_id=None,
                target_room_session_id=payload.target_room_session_id,
                reason=payload.reason,
                created_at=now,
            )
            session.add(mk)
            session.flush()
            return {"id": mk.id}

    def complete_closing(self, payload: ClosingCompletePayload) -> dict[str, Any]:
        with session_scope(self._session_factory) as session:
            exam, plan = self._require_plan(
                session, payload.institution_id, payload.exam_id, payload.plan_id
            )
            blockers: list[str] = []
            if payload.require_all_attendance:
                att_by_sitting = {
                    a.sitting_id: a
                    for a in self._repo.list_participant_attendance(session, exam.id)
                }
                unrec = sum(
                    1
                    for s in self._rom_repo.list_sittings(session, plan.id)
                    if s.id not in att_by_sitting
                    or att_by_sitting[s.id].state == "unrecorded"
                )
                if unrec > 0:
                    blockers.append(
                        f"Masih ada {unrec} kehadiran peserta belum dicatat."
                    )

            if payload.require_all_reports_final:
                reps = {
                    r.room_session_id: r
                    for r in self._repo.list_session_reports(session, exam.id)
                }
                unfin = sum(
                    1
                    for rs in self._ses_repo.list_room_sessions(session, plan.id)
                    if rs.id not in reps or reps[rs.id].finalized_at is None
                )
                if unfin > 0:
                    blockers.append(
                        f"Masih ada {unfin} berita acara ruang belum difinalisasi."
                    )

            if blockers:
                raise ConflictError(" ".join(blockers))
            return {"closed": True}
