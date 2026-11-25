"""Repository helpers for COM-01..COM-06."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.modules.com.models import (
    CommitteeMember,
    CommitteeRole,
    ExamSignatory,
    Meeting,
    MeetingAttendance,
    ProgramKerja,
)


class ComRepository:
    """Data-access layer for committee, meetings, program kerja, and signatories."""

    def list_roles(self, session: Session, exam_id: str) -> list[CommitteeRole]:
        stmt = (
            select(CommitteeRole)
            .where(CommitteeRole.exam_id == exam_id)
            .order_by(CommitteeRole.sort_order, CommitteeRole.name)
        )
        return list(session.scalars(stmt))

    def get_role(
        self, session: Session, exam_id: str, role_id: str
    ) -> CommitteeRole | None:
        stmt = select(CommitteeRole).where(
            CommitteeRole.exam_id == exam_id, CommitteeRole.id == role_id
        )
        return session.scalar(stmt)

    def list_members(self, session: Session, exam_id: str) -> list[CommitteeMember]:
        stmt = select(CommitteeMember).where(CommitteeMember.exam_id == exam_id)
        return list(session.scalars(stmt))

    def get_member(
        self, session: Session, exam_id: str, member_id: str
    ) -> CommitteeMember | None:
        stmt = select(CommitteeMember).where(
            CommitteeMember.exam_id == exam_id, CommitteeMember.id == member_id
        )
        return session.scalar(stmt)

    def get_program_kerja(self, session: Session, exam_id: str) -> ProgramKerja | None:
        stmt = select(ProgramKerja).where(ProgramKerja.exam_id == exam_id)
        return session.scalar(stmt)

    def list_meetings(self, session: Session, exam_id: str) -> list[Meeting]:
        stmt = (
            select(Meeting)
            .where(Meeting.exam_id == exam_id)
            .order_by(Meeting.meeting_date, Meeting.start_time)
        )
        return list(session.scalars(stmt))

    def get_meeting(
        self, session: Session, exam_id: str, meeting_id: str
    ) -> Meeting | None:
        stmt = select(Meeting).where(
            Meeting.exam_id == exam_id, Meeting.id == meeting_id
        )
        return session.scalar(stmt)

    def list_meeting_attendance(
        self, session: Session, meeting_id: str
    ) -> list[MeetingAttendance]:
        stmt = select(MeetingAttendance).where(
            MeetingAttendance.meeting_id == meeting_id
        )
        return list(session.scalars(stmt))

    def get_meeting_attendance_person(
        self, session: Session, meeting_id: str, exam_person_id: str
    ) -> MeetingAttendance | None:
        stmt = select(MeetingAttendance).where(
            MeetingAttendance.meeting_id == meeting_id,
            MeetingAttendance.exam_person_id == exam_person_id,
        )
        return session.scalar(stmt)

    def list_signatories(self, session: Session, exam_id: str) -> list[ExamSignatory]:
        stmt = (
            select(ExamSignatory)
            .where(ExamSignatory.exam_id == exam_id)
            .order_by(ExamSignatory.sort_order, ExamSignatory.role_key)
        )
        return list(session.scalars(stmt))

    def get_signatory_by_key(
        self, session: Session, exam_id: str, role_key: str
    ) -> ExamSignatory | None:
        stmt = select(ExamSignatory).where(
            ExamSignatory.exam_id == exam_id, ExamSignatory.role_key == role_key
        )
        return session.scalar(stmt)

    def get_signatory(
        self, session: Session, exam_id: str, signatory_id: str
    ) -> ExamSignatory | None:
        stmt = select(ExamSignatory).where(
            ExamSignatory.exam_id == exam_id, ExamSignatory.id == signatory_id
        )
        return session.scalar(stmt)
