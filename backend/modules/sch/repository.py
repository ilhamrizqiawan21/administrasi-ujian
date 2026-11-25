"""Repository helpers for SCH-01..SCH-08."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.modules.sch.models import (
    Invigilation,
    InvigilationReserve,
    InvigilationSlot,
    SolverRun,
    StaffAvailability,
    StaffProfile,
)


class SchRepository:
    """Data-access layer for invigilation scheduling."""

    def list_availability(
        self, session: Session, exam_id: str
    ) -> list[StaffAvailability]:
        stmt = (
            select(StaffAvailability)
            .where(StaffAvailability.exam_id == exam_id)
            .order_by(StaffAvailability.starts_at)
        )
        return list(session.scalars(stmt))

    def get_availability(
        self, session: Session, exam_id: str, availability_id: str
    ) -> StaffAvailability | None:
        stmt = select(StaffAvailability).where(
            StaffAvailability.exam_id == exam_id,
            StaffAvailability.id == availability_id,
        )
        return session.scalar(stmt)

    def list_profiles(self, session: Session, exam_id: str) -> list[StaffProfile]:
        stmt = select(StaffProfile).where(StaffProfile.exam_id == exam_id)
        return list(session.scalars(stmt))

    def get_profile(
        self, session: Session, exam_id: str, exam_person_id: str
    ) -> StaffProfile | None:
        stmt = select(StaffProfile).where(
            StaffProfile.exam_id == exam_id,
            StaffProfile.exam_person_id == exam_person_id,
        )
        return session.scalar(stmt)

    def list_slots(self, session: Session, plan_id: str) -> list[InvigilationSlot]:
        stmt = (
            select(InvigilationSlot)
            .where(InvigilationSlot.plan_id == plan_id)
            .order_by(
                InvigilationSlot.room_session_id,
                InvigilationSlot.role_code,
                InvigilationSlot.slot_index,
            )
        )
        return list(session.scalars(stmt))

    def list_slots_for_room_session(
        self, session: Session, plan_id: str, room_session_id: str
    ) -> list[InvigilationSlot]:
        stmt = (
            select(InvigilationSlot)
            .where(
                InvigilationSlot.plan_id == plan_id,
                InvigilationSlot.room_session_id == room_session_id,
            )
            .order_by(InvigilationSlot.role_code, InvigilationSlot.slot_index)
        )
        return list(session.scalars(stmt))

    def get_slot(
        self, session: Session, plan_id: str, slot_id: str
    ) -> InvigilationSlot | None:
        stmt = select(InvigilationSlot).where(
            InvigilationSlot.plan_id == plan_id,
            InvigilationSlot.id == slot_id,
        )
        return session.scalar(stmt)

    def list_invigilations(self, session: Session, plan_id: str) -> list[Invigilation]:
        stmt = select(Invigilation).where(Invigilation.plan_id == plan_id)
        return list(session.scalars(stmt))

    def get_invigilation_by_slot(
        self, session: Session, plan_id: str, slot_id: str
    ) -> Invigilation | None:
        stmt = select(Invigilation).where(
            Invigilation.plan_id == plan_id,
            Invigilation.slot_id == slot_id,
        )
        return session.scalar(stmt)

    def list_reserves(
        self, session: Session, plan_id: str
    ) -> list[InvigilationReserve]:
        stmt = select(InvigilationReserve).where(InvigilationReserve.plan_id == plan_id)
        return list(session.scalars(stmt))

    def get_reserve(
        self, session: Session, plan_id: str, reserve_id: str
    ) -> InvigilationReserve | None:
        stmt = select(InvigilationReserve).where(
            InvigilationReserve.plan_id == plan_id,
            InvigilationReserve.id == reserve_id,
        )
        return session.scalar(stmt)

    def list_solver_runs(self, session: Session, plan_id: str) -> list[SolverRun]:
        stmt = (
            select(SolverRun)
            .where(SolverRun.plan_id == plan_id)
            .order_by(SolverRun.created_at.desc())
        )
        return list(session.scalars(stmt))
