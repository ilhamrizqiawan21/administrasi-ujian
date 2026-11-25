"""Repository layer for SES plans, sessions, room_sessions, and room_papers."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.modules.ses.models import ExamSession, Plan, RoomPaper, RoomSession


class SesRepository:
    """Data access helpers for timetable planning."""

    def list_plans(self, session: Session, exam_id: str) -> list[Plan]:
        return list(
            session.scalars(
                select(Plan)
                .where(Plan.exam_id == exam_id)
                .order_by(Plan.version.desc())
            )
        )

    def get_plan(self, session: Session, exam_id: str, plan_id: str) -> Plan | None:
        return session.scalar(
            select(Plan).where(Plan.id == plan_id, Plan.exam_id == exam_id)
        )

    def list_sessions(self, session: Session, plan_id: str) -> list[ExamSession]:
        return list(
            session.scalars(
                select(ExamSession)
                .where(ExamSession.plan_id == plan_id)
                .order_by(
                    ExamSession.local_date.asc(),
                    ExamSession.sort_order.asc(),
                    ExamSession.starts_at.asc(),
                )
            )
        )

    def get_exam_session(
        self, session: Session, plan_id: str, session_id: str
    ) -> ExamSession | None:
        return session.scalar(
            select(ExamSession).where(
                ExamSession.id == session_id, ExamSession.plan_id == plan_id
            )
        )

    def list_room_sessions(self, session: Session, plan_id: str) -> list[RoomSession]:
        return list(
            session.scalars(select(RoomSession).where(RoomSession.plan_id == plan_id))
        )

    def get_room_session(
        self, session: Session, plan_id: str, session_id: str, exam_room_id: str
    ) -> RoomSession | None:
        return session.scalar(
            select(RoomSession).where(
                RoomSession.plan_id == plan_id,
                RoomSession.session_id == session_id,
                RoomSession.exam_room_id == exam_room_id,
            )
        )

    def list_room_papers_for_plan(
        self, session: Session, plan_id: str
    ) -> list[RoomPaper]:
        rs_ids = select(RoomSession.id).where(RoomSession.plan_id == plan_id)
        return list(
            session.scalars(
                select(RoomPaper).where(RoomPaper.room_session_id.in_(rs_ids))
            )
        )

    def get_room_paper(self, session: Session, paper_id: str) -> RoomPaper | None:
        return session.get(RoomPaper, paper_id)
