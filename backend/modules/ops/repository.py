"""Repository helpers for OPS-01..OPS-08."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.modules.ops.models import (
    CommitteeAttendance,
    Incident,
    MakeupLink,
    ParticipantAttendance,
    RoomSessionState,
    SessionReport,
    StaffAttendance,
)


class OpsRepository:
    """Data-access layer for exam execution operations."""

    def list_room_session_states(
        self, session: Session, plan_id: str
    ) -> list[RoomSessionState]:
        stmt = select(RoomSessionState).where(RoomSessionState.plan_id == plan_id)
        return list(session.scalars(stmt))

    def get_room_session_state(
        self, session: Session, room_session_id: str
    ) -> RoomSessionState | None:
        stmt = select(RoomSessionState).where(
            RoomSessionState.room_session_id == room_session_id
        )
        return session.scalar(stmt)

    def list_participant_attendance(
        self, session: Session, exam_id: str
    ) -> list[ParticipantAttendance]:
        stmt = select(ParticipantAttendance).where(
            ParticipantAttendance.exam_id == exam_id
        )
        return list(session.scalars(stmt))

    def get_participant_attendance(
        self, session: Session, sitting_id: str
    ) -> ParticipantAttendance | None:
        stmt = select(ParticipantAttendance).where(
            ParticipantAttendance.sitting_id == sitting_id
        )
        return session.scalar(stmt)

    def list_staff_attendance(
        self, session: Session, exam_id: str
    ) -> list[StaffAttendance]:
        stmt = select(StaffAttendance).where(StaffAttendance.exam_id == exam_id)
        return list(session.scalars(stmt))

    def get_staff_attendance(
        self, session: Session, slot_id: str
    ) -> StaffAttendance | None:
        stmt = select(StaffAttendance).where(StaffAttendance.slot_id == slot_id)
        return session.scalar(stmt)

    def list_committee_attendance(
        self, session: Session, exam_id: str
    ) -> list[CommitteeAttendance]:
        stmt = (
            select(CommitteeAttendance)
            .where(CommitteeAttendance.exam_id == exam_id)
            .order_by(CommitteeAttendance.att_date, CommitteeAttendance.shift)
        )
        return list(session.scalars(stmt))

    def get_committee_attendance(
        self,
        session: Session,
        exam_id: str,
        att_date: str,
        shift: str,
        exam_person_id: str,
    ) -> CommitteeAttendance | None:
        stmt = select(CommitteeAttendance).where(
            CommitteeAttendance.exam_id == exam_id,
            CommitteeAttendance.att_date == att_date,
            CommitteeAttendance.shift == shift,
            CommitteeAttendance.exam_person_id == exam_person_id,
        )
        return session.scalar(stmt)

    def list_session_reports(
        self, session: Session, exam_id: str
    ) -> list[SessionReport]:
        stmt = select(SessionReport).where(SessionReport.exam_id == exam_id)
        return list(session.scalars(stmt))

    def get_session_report(
        self, session: Session, room_session_id: str
    ) -> SessionReport | None:
        stmt = select(SessionReport).where(
            SessionReport.room_session_id == room_session_id
        )
        return session.scalar(stmt)

    def list_incidents(self, session: Session, exam_id: str) -> list[Incident]:
        stmt = (
            select(Incident)
            .where(Incident.exam_id == exam_id)
            .order_by(Incident.recorded_at.desc())
        )
        return list(session.scalars(stmt))

    def list_makeup_links(self, session: Session, exam_id: str) -> list[MakeupLink]:
        stmt = select(MakeupLink).where(MakeupLink.exam_id == exam_id)
        return list(session.scalars(stmt))
