"""Repository layer for EVT models (scoped by institution_id and exam_id)."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.modules.evt.models import (
    AuditEvent,
    Exam,
    ExamGroup,
    ExamParticipant,
    ExamPerson,
    ExamRequirement,
    ExamRoom,
    ExamSubject,
    GroupMember,
)


class EvtRepository:
    """Data access helpers for exam workspace and snapshots."""

    def list_exams(self, session: Session, institution_id: str) -> list[Exam]:
        stmt = (
            select(Exam)
            .where(Exam.institution_id == institution_id)
            .order_by(Exam.starts_on.desc(), Exam.created_at.desc())
        )
        return list(session.scalars(stmt))

    def get_exam(
        self, session: Session, institution_id: str, exam_id: str
    ) -> Exam | None:
        return session.scalar(
            select(Exam).where(
                Exam.id == exam_id, Exam.institution_id == institution_id
            )
        )

    def list_people(
        self, session: Session, exam_id: str, *, kind: str | None = None
    ) -> list[ExamPerson]:
        stmt = select(ExamPerson).where(ExamPerson.exam_id == exam_id)
        if kind is not None:
            stmt = stmt.where(ExamPerson.kind == kind)
        return list(session.scalars(stmt.order_by(ExamPerson.display_name.asc())))

    def list_participants(
        self, session: Session, exam_id: str
    ) -> list[ExamParticipant]:
        return list(
            session.scalars(
                select(ExamParticipant).where(ExamParticipant.exam_id == exam_id)
            )
        )

    def get_participant(
        self, session: Session, exam_id: str, participant_id: str
    ) -> ExamParticipant | None:
        return session.scalar(
            select(ExamParticipant).where(
                ExamParticipant.id == participant_id, ExamParticipant.exam_id == exam_id
            )
        )

    def list_rooms(self, session: Session, exam_id: str) -> list[ExamRoom]:
        return list(
            session.scalars(
                select(ExamRoom)
                .where(ExamRoom.exam_id == exam_id)
                .order_by(ExamRoom.code.asc())
            )
        )

    def list_subjects(self, session: Session, exam_id: str) -> list[ExamSubject]:
        return list(
            session.scalars(
                select(ExamSubject)
                .where(ExamSubject.exam_id == exam_id)
                .order_by(ExamSubject.code.asc())
            )
        )

    def get_subject(
        self, session: Session, exam_id: str, exam_subject_id: str
    ) -> ExamSubject | None:
        return session.scalar(
            select(ExamSubject).where(
                ExamSubject.id == exam_subject_id, ExamSubject.exam_id == exam_id
            )
        )

    def list_groups(self, session: Session, exam_id: str) -> list[ExamGroup]:
        return list(
            session.scalars(
                select(ExamGroup)
                .where(ExamGroup.exam_id == exam_id)
                .order_by(ExamGroup.label.asc())
            )
        )

    def get_group(
        self, session: Session, exam_id: str, group_id: str
    ) -> ExamGroup | None:
        return session.scalar(
            select(ExamGroup).where(
                ExamGroup.id == group_id, ExamGroup.exam_id == exam_id
            )
        )

    def list_group_members(self, session: Session, group_id: str) -> list[GroupMember]:
        return list(
            session.scalars(select(GroupMember).where(GroupMember.group_id == group_id))
        )

    def list_requirements(
        self, session: Session, group_id: str
    ) -> list[ExamRequirement]:
        return list(
            session.scalars(
                select(ExamRequirement).where(ExamRequirement.group_id == group_id)
            )
        )

    def get_requirement(
        self, session: Session, requirement_id: str
    ) -> ExamRequirement | None:
        return session.get(ExamRequirement, requirement_id)

    def list_audit_events(self, session: Session, exam_id: str) -> list[AuditEvent]:
        return list(
            session.scalars(
                select(AuditEvent)
                .where(AuditEvent.exam_id == exam_id)
                .order_by(AuditEvent.at.desc())
            )
        )
