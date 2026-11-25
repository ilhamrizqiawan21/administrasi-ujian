"""Transactional service layer for ROM-01..ROM-08."""

from __future__ import annotations

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
from backend.modules.mst.schemas import RoomLayoutConfig
from backend.modules.rom.models import ParticipantSitting, PlanSeatAssignment, Seat
from backend.modules.rom.repository import RomRepository
from backend.modules.rom.schemas import (
    RoomLayoutUpdatePayload,
    SeatingPrintContextPayload,
    SeatingScopedPayload,
    SeatingSolvePayload,
    SeatLockPayload,
    SeatSwapPayload,
)
from backend.modules.rom.solver import solve_seating
from backend.modules.rom.validator import (
    ParticipantCandidate,
    SeatCandidate,
    validate_seating_allocation,
)
from backend.modules.ses.models import Plan
from backend.modules.ses.repository import SesRepository
from backend.modules.ses.service import SesService


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()


def _new_id() -> str:
    return uuid.uuid4().hex


def _check_revision(actual: int, expected: int) -> None:
    if actual != expected:
        raise AppError(
            "STALE_REVISION",
            "Draf denah telah diubah. Muat ulang sebelum menyimpan.",
        )


class RomService:
    """Application service for Room Allocation and Denah (ROM-01..ROM-08)."""

    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._session_factory = session_factory
        self._repo = RomRepository()
        self._evt_repo = EvtRepository()
        self._ses_repo = SesRepository()
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

    def _ensure_seats_for_plan(self, session: Session, exam: Exam, plan: Plan) -> None:
        existing = self._repo.list_seats(session, plan.id)
        if existing:
            return
        now = _now_iso()
        for rm in self._evt_repo.list_rooms(session, exam.id):
            layout = RoomLayoutConfig.model_validate_json(rm.layout_json)
            disabled = set(layout.disabled_cells)
            accessible = set(layout.accessible_seats)
            for r in range(1, layout.rows + 1):
                for c in range(1, layout.cols + 1):
                    for s in range(1, layout.seats_per_desk + 1):
                        code = f"R{r}C{c}S{s}"
                        cell_code = f"R{r}C{c}"
                        is_enabled = code not in disabled and cell_code not in disabled
                        is_acc = code in accessible or cell_code in accessible
                        session.add(
                            Seat(
                                id=_new_id(),
                                plan_id=plan.id,
                                exam_room_id=rm.id,
                                seat_code=code,
                                desk_row=r,
                                desk_col=c,
                                seat_index=s,
                                enabled=1 if is_enabled else 0,
                                accessible=1 if is_acc else 0,
                                revision=1,
                                created_at=now,
                                updated_at=now,
                            )
                        )
        session.flush()

    def update_room_layout(self, payload: RoomLayoutUpdatePayload) -> dict[str, Any]:
        now = _now_iso()
        with session_scope(self._session_factory) as session:
            exam, plan = self._require_plan(
                session, payload.institution_id, payload.exam_id, payload.plan_id
            )
            if plan.state in ("published", "superseded"):
                raise ConflictError("Versi terbit tidak dapat diubah; buat draf baru.")

            rooms_map = {
                rm.id: rm for rm in self._evt_repo.list_rooms(session, exam.id)
            }
            room = rooms_map.get(payload.exam_room_id)
            if room is None:
                raise NotFoundError("Ruang kegiatan tidak ditemukan.")

            layout = RoomLayoutConfig(
                rows=payload.rows,
                cols=payload.cols,
                seats_per_desk=payload.seats_per_desk,
                disabled_cells=payload.disabled_cells,
                accessible_seats=payload.accessible_seats,
                board_position=payload.board_position,
            )
            room.layout_json = layout.model_dump_json()
            room.capacity_limit = payload.capacity_limit
            room.revision += 1
            room.updated_at = now

            # Rebuild seats for this room in draft plan
            for old_seat in self._repo.list_seats(
                session, plan.id, exam_room_id=room.id
            ):
                session.delete(old_seat)
            session.flush()

            disabled = set(layout.disabled_cells)
            accessible = set(layout.accessible_seats)
            for r in range(1, layout.rows + 1):
                for c in range(1, layout.cols + 1):
                    for s in range(1, layout.seats_per_desk + 1):
                        code = f"R{r}C{c}S{s}"
                        cell_code = f"R{r}C{c}"
                        is_enabled = code not in disabled and cell_code not in disabled
                        is_acc = code in accessible or cell_code in accessible
                        session.add(
                            Seat(
                                id=_new_id(),
                                plan_id=plan.id,
                                exam_room_id=room.id,
                                seat_code=code,
                                desk_row=r,
                                desk_col=c,
                                seat_index=s,
                                enabled=1 if is_enabled else 0,
                                accessible=1 if is_acc else 0,
                                revision=1,
                                created_at=now,
                                updated_at=now,
                            )
                        )
            plan.input_hash = SesService(self._session_factory).compute_exam_input_hash(
                session, exam
            )
            plan.state = "draft"
            plan.revision += 1
            plan.updated_at = now
            session.flush()
            return {"room_id": room.id, "plan_revision": plan.revision}

    def get_seating_detail(self, payload: SeatingScopedPayload) -> dict[str, Any]:
        with session_scope(self._session_factory) as session:
            exam, plan = self._require_plan(
                session, payload.institution_id, payload.exam_id, payload.plan_id
            )
            self._ensure_seats_for_plan(session, exam, plan)
            part_cands, seat_cands, room_caps, rooms_meta = self._build_candidates(
                session, exam, plan
            )
            assigns = self._repo.list_plan_assignments(session, plan.id)
            assign_map = {a.participant_id: a.seat_id for a in assigns}
            locked_seat_ids = {a.seat_id for a in assigns if a.locked}

            validation = validate_seating_allocation(
                participants=part_cands,
                seats=seat_cands,
                room_caps=room_caps,
                assignments=assign_map,
            )

            seat_to_part = {a.seat_id: a.participant_id for a in assigns}
            seats_out = []
            for s in seat_cands.values():
                pid = seat_to_part.get(s.id)
                part = part_cands.get(pid) if pid else None
                seats_out.append(
                    {
                        "id": s.id,
                        "exam_room_id": s.exam_room_id,
                        "seat_code": s.seat_code,
                        "desk_row": s.desk_row,
                        "desk_col": s.desk_col,
                        "seat_index": s.seat_index,
                        "enabled": s.enabled,
                        "accessible": s.accessible,
                        "locked": s.id in locked_seat_ids,
                        "participant": (
                            {
                                "id": part.id,
                                "participant_number": part.participant_number,
                                "display_name": part.display_name,
                                "level_label": part.level_label,
                                "class_label": part.class_label,
                            }
                            if part
                            else None
                        ),
                    }
                )

            return {
                "plan_id": plan.id,
                "plan_state": plan.state,
                "plan_revision": plan.revision,
                "rooms": rooms_meta,
                "seats": seats_out,
                "validation": validation,
            }

    def solve_plan_seating(self, payload: SeatingSolvePayload) -> dict[str, Any]:
        now = _now_iso()
        with session_scope(self._session_factory) as session:
            exam, plan = self._require_plan(
                session, payload.institution_id, payload.exam_id, payload.plan_id
            )
            if plan.state in ("published", "superseded"):
                raise ConflictError("Versi terbit tidak dapat diubah; buat draf baru.")
            _check_revision(plan.revision, payload.expected_revision)

            self._ensure_seats_for_plan(session, exam, plan)
            part_cands, seat_cands, room_caps, _ = self._build_candidates(
                session, exam, plan
            )
            existing_assigns = self._repo.list_plan_assignments(session, plan.id)
            locked_map = {
                a.participant_id: a.seat_id for a in existing_assigns if a.locked
            }

            result = solve_seating(
                participants=list(part_cands.values()),
                seats=list(seat_cands.values()),
                room_caps=room_caps,
                locked_assignments=locked_map,
                policy=payload.policy,
                time_limit_sec=payload.time_limit_sec,
                seed=payload.seed,
            )
            if result["status"] not in ("OPTIMAL", "FEASIBLE"):
                return {
                    "ok": False,
                    "status": result["status"],
                    "diagnostics": result["diagnostics"],
                }

            assignments: dict[str, str] = result["assignments"]
            validation = validate_seating_allocation(
                participants=part_cands,
                seats=seat_cands,
                room_caps=room_caps,
                assignments=assignments,
                hard_mix_grade=payload.policy.hard_mix_grade,
                hard_mix_class=payload.policy.hard_mix_class,
                require_accessible=payload.policy.require_accessible,
                diagonal_adjacent=payload.policy.diagonal_adjacent,
            )
            if not validation["valid"]:
                raise ConflictError(validation["hard_conflicts"][0]["message"])

            for old_a in existing_assigns:
                session.delete(old_a)
            session.flush()

            for pid, sid in assignments.items():
                seat = seat_cands[sid]
                session.add(
                    PlanSeatAssignment(
                        id=_new_id(),
                        plan_id=plan.id,
                        participant_id=pid,
                        exam_room_id=seat.exam_room_id,
                        seat_id=sid,
                        locked=1 if pid in locked_map else 0,
                        revision=1,
                        created_at=now,
                        updated_at=now,
                    )
                )
            session.flush()
            self._sync_participant_sittings(session, exam, plan, assignments, now)

            plan.state = "draft"
            plan.revision += 1
            plan.updated_at = now
            session.flush()
            return {
                "ok": True,
                "status": result["status"],
                "plan_revision": plan.revision,
                "validation": validation,
            }

    def swap_seats(self, payload: SeatSwapPayload) -> dict[str, Any]:
        now = _now_iso()
        with session_scope(self._session_factory) as session:
            exam, plan = self._require_plan(
                session, payload.institution_id, payload.exam_id, payload.plan_id
            )
            if plan.state in ("published", "superseded"):
                raise ConflictError("Versi terbit tidak dapat diubah; buat draf baru.")
            _check_revision(plan.revision, payload.expected_revision)

            src_seat = self._repo.get_seat(session, plan.id, payload.source_seat_id)
            dst_seat = self._repo.get_seat(session, plan.id, payload.target_seat_id)
            if src_seat is None or dst_seat is None:
                raise NotFoundError("Kursi sumber atau tujuan tidak ditemukan.")
            if not src_seat.enabled or not dst_seat.enabled:
                raise ConflictError("Kursi nonaktif tidak dapat ditukar.")

            src_assign = self._repo.get_assignment_by_seat(
                session, plan.id, src_seat.id
            )
            dst_assign = self._repo.get_assignment_by_seat(
                session, plan.id, dst_seat.id
            )
            if (src_assign and src_assign.locked) or (dst_assign and dst_assign.locked):
                raise ConflictError("Kursi terkunci tidak dapat ditukar.")
            if src_assign is None and dst_assign is None:
                raise ConflictError("Kedua kursi kosong; tidak ada yang ditukar.")

            part_cands, seat_cands, room_caps, _ = self._build_candidates(
                session, exam, plan
            )
            all_assigns = self._repo.list_plan_assignments(session, plan.id)
            candidate_map = {a.participant_id: a.seat_id for a in all_assigns}
            if src_assign:
                candidate_map[src_assign.participant_id] = dst_seat.id
            if dst_assign:
                candidate_map[dst_assign.participant_id] = src_seat.id

            validation = validate_seating_allocation(
                participants=part_cands,
                seats=seat_cands,
                room_caps=room_caps,
                assignments=candidate_map,
                hard_mix_grade=payload.policy.hard_mix_grade,
                hard_mix_class=payload.policy.hard_mix_class,
                require_accessible=payload.policy.require_accessible,
                diagonal_adjacent=payload.policy.diagonal_adjacent,
            )
            if not validation["valid"]:
                raise ConflictError(validation["hard_conflicts"][0]["message"])

            if src_assign and dst_assign:
                # Temporary clear to satisfy UQ(plan_id, seat_id) in SQLite
                src_pid = src_assign.participant_id
                dst_pid = dst_assign.participant_id
                session.delete(src_assign)
                session.delete(dst_assign)
                session.flush()
                session.add(
                    PlanSeatAssignment(
                        id=_new_id(),
                        plan_id=plan.id,
                        participant_id=src_pid,
                        exam_room_id=dst_seat.exam_room_id,
                        seat_id=dst_seat.id,
                        locked=0,
                        revision=1,
                        created_at=now,
                        updated_at=now,
                    )
                )
                session.add(
                    PlanSeatAssignment(
                        id=_new_id(),
                        plan_id=plan.id,
                        participant_id=dst_pid,
                        exam_room_id=src_seat.exam_room_id,
                        seat_id=src_seat.id,
                        locked=0,
                        revision=1,
                        created_at=now,
                        updated_at=now,
                    )
                )
            elif src_assign:
                src_assign.seat_id = dst_seat.id
                src_assign.exam_room_id = dst_seat.exam_room_id
                src_assign.revision += 1
                src_assign.updated_at = now
            elif dst_assign:
                dst_assign.seat_id = src_seat.id
                dst_assign.exam_room_id = src_seat.exam_room_id
                dst_assign.revision += 1
                dst_assign.updated_at = now

            session.flush()
            self._sync_participant_sittings(session, exam, plan, candidate_map, now)
            plan.state = "draft"
            plan.revision += 1
            plan.updated_at = now
            session.flush()
            return {"plan_revision": plan.revision, "validation": validation}

    def set_seat_lock(self, payload: SeatLockPayload) -> dict[str, Any]:
        now = _now_iso()
        with session_scope(self._session_factory) as session:
            exam, plan = self._require_plan(
                session, payload.institution_id, payload.exam_id, payload.plan_id
            )
            if plan.state in ("published", "superseded"):
                raise ConflictError("Versi terbit tidak dapat diubah.")
            assign = self._repo.get_assignment_by_seat(
                session, plan.id, payload.seat_id
            )
            if assign is None:
                raise NotFoundError("Kursi belum terisi peserta.")
            assign.locked = 1 if payload.locked else 0
            assign.revision += 1
            assign.updated_at = now
            plan.revision += 1
            plan.updated_at = now
            session.flush()
            return {"locked": bool(assign.locked), "plan_revision": plan.revision}

    def get_print_context(self, payload: SeatingPrintContextPayload) -> dict[str, Any]:
        with session_scope(self._session_factory) as session:
            exam, plan = self._require_plan(
                session, payload.institution_id, payload.exam_id, payload.plan_id
            )
            rooms = {rm.id: rm for rm in self._evt_repo.list_rooms(session, exam.id)}
            room = rooms.get(payload.exam_room_id)
            if room is None:
                raise NotFoundError("Ruang tidak ditemukan.")

            layout = RoomLayoutConfig.model_validate_json(room.layout_json)
            part_cands, seat_cands, _, _ = self._build_candidates(session, exam, plan)
            seat_to_part = {
                a.seat_id: a.participant_id
                for a in self._repo.list_plan_assignments(session, plan.id)
                if a.exam_room_id == room.id
            }

            desks = []
            for s in seat_cands.values():
                if s.exam_room_id != room.id:
                    continue
                pid = seat_to_part.get(s.id)
                part = part_cands.get(pid) if pid else None
                desks.append(
                    {
                        "seat_code": s.seat_code,
                        "row": s.desk_row,
                        "col": s.desk_col,
                        "seat_index": s.seat_index,
                        "enabled": s.enabled,
                        "accessible": s.accessible,
                        "participant_number": part.participant_number if part else None,
                        "display_name": (
                            part.display_name
                            if (part and payload.include_names)
                            else None
                        ),
                        "level_label": part.level_label if part else None,
                        "class_label": part.class_label if part else None,
                    }
                )

            return {
                "exam_title": exam.title,
                "plan_version": plan.version,
                "plan_state": plan.state,
                "room_code": room.code,
                "room_name": room.name,
                "board_position": layout.board_position,
                "rows": layout.rows,
                "cols": layout.cols,
                "desks": desks,
            }

    def _build_candidates(
        self, session: Session, exam: Exam, plan: Plan
    ) -> tuple[
        dict[str, ParticipantCandidate],
        dict[str, SeatCandidate],
        dict[str, int],
        list[dict[str, Any]],
    ]:
        people = {
            p.id: p
            for p in self._evt_repo.list_people(session, exam.id, kind="student")
        }
        part_cands: dict[str, ParticipantCandidate] = {}
        for pt in self._evt_repo.list_participants(session, exam.id):
            if pt.eligibility != "eligible":
                continue
            person = people.get(pt.exam_person_id)
            if person is None:
                continue
            acc = json.loads(pt.accommodation_json)
            part_cands[pt.id] = ParticipantCandidate(
                id=pt.id,
                code=person.code,
                display_name=person.display_name,
                participant_number=pt.participant_number,
                level_label=person.level_label or "",
                class_label=person.class_label or "",
                needs_accessible=bool(acc.get("accessible_seat", False)),
            )

        rooms_rows = self._evt_repo.list_rooms(session, exam.id)
        room_caps = {r.id: r.capacity_limit for r in rooms_rows}
        room_codes = {r.id: r.code for r in rooms_rows}
        seats_rows = self._repo.list_seats(session, plan.id)
        seat_cands = {
            s.id: SeatCandidate(
                id=s.id,
                exam_room_id=s.exam_room_id,
                room_code=room_codes.get(s.exam_room_id, ""),
                seat_code=s.seat_code,
                desk_row=s.desk_row,
                desk_col=s.desk_col,
                seat_index=s.seat_index,
                enabled=bool(s.enabled),
                accessible=bool(s.accessible),
            )
            for s in seats_rows
        }

        rooms_meta = []
        for rm in rooms_rows:
            layout = RoomLayoutConfig.model_validate_json(rm.layout_json)
            rooms_meta.append(
                {
                    "id": rm.id,
                    "code": rm.code,
                    "name": rm.name,
                    "mode": rm.mode,
                    "capacity_limit": rm.capacity_limit,
                    "rows": layout.rows,
                    "cols": layout.cols,
                    "seats_per_desk": layout.seats_per_desk,
                    "board_position": layout.board_position,
                }
            )
        return part_cands, seat_cands, room_caps, rooms_meta

    def _sync_participant_sittings(
        self,
        session: Session,
        exam: Exam,
        plan: Plan,
        assignments: dict[str, str],
        now: str,
    ) -> None:
        for old_sit in self._repo.list_sittings(session, plan.id):
            session.delete(old_sit)
        session.flush()

        papers = self._ses_repo.list_room_papers_for_plan(session, plan.id)
        if not papers:
            return
        rs_by_id = {
            rs.id: rs for rs in self._ses_repo.list_room_sessions(session, plan.id)
        }
        group_members: dict[str, list[str]] = {}
        for grp in self._evt_repo.list_groups(session, exam.id):
            group_members[grp.id] = [
                m.participant_id
                for m in self._evt_repo.list_group_members(session, grp.id)
            ]

        for rp in papers:
            rs = rs_by_id.get(rp.room_session_id)
            if rs is None:
                continue
            for pid in group_members.get(rp.group_id, []):
                sid = assignments.get(pid)
                if sid is None:
                    continue
                session.add(
                    ParticipantSitting(
                        id=_new_id(),
                        plan_id=plan.id,
                        room_session_id=rs.id,
                        participant_id=pid,
                        requirement_id=rp.requirement_id,
                        seat_id=sid,
                        locked=0,
                        revision=1,
                        created_at=now,
                        updated_at=now,
                    )
                )
        session.flush()
