"""Repository layer for ROM seats, plan_seat_assignments, and sittings."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.modules.rom.models import ParticipantSitting, PlanSeatAssignment, Seat


class RomRepository:
    """Data access helpers for room allocation and denah."""

    def list_seats(
        self, session: Session, plan_id: str, *, exam_room_id: str | None = None
    ) -> list[Seat]:
        stmt = select(Seat).where(Seat.plan_id == plan_id)
        if exam_room_id is not None:
            stmt = stmt.where(Seat.exam_room_id == exam_room_id)
        return list(
            session.scalars(
                stmt.order_by(
                    Seat.exam_room_id.asc(),
                    Seat.desk_row.asc(),
                    Seat.desk_col.asc(),
                    Seat.seat_index.asc(),
                )
            )
        )

    def get_seat(self, session: Session, plan_id: str, seat_id: str) -> Seat | None:
        return session.scalar(
            select(Seat).where(Seat.id == seat_id, Seat.plan_id == plan_id)
        )

    def list_plan_assignments(
        self, session: Session, plan_id: str
    ) -> list[PlanSeatAssignment]:
        return list(
            session.scalars(
                select(PlanSeatAssignment).where(PlanSeatAssignment.plan_id == plan_id)
            )
        )

    def get_assignment_by_seat(
        self, session: Session, plan_id: str, seat_id: str
    ) -> PlanSeatAssignment | None:
        return session.scalar(
            select(PlanSeatAssignment).where(
                PlanSeatAssignment.plan_id == plan_id,
                PlanSeatAssignment.seat_id == seat_id,
            )
        )

    def list_sittings(self, session: Session, plan_id: str) -> list[ParticipantSitting]:
        return list(
            session.scalars(
                select(ParticipantSitting).where(ParticipantSitting.plan_id == plan_id)
            )
        )
