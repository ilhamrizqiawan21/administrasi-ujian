"""SQLAlchemy ORM models for SES (plans, sessions, room_sessions, room_papers)."""

from __future__ import annotations

from sqlalchemy import ForeignKey, Integer, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from backend.core.db import Base


class Plan(Base):
    __tablename__ = "plans"
    __table_args__ = (UniqueConstraint("exam_id", "version", name="uq_plan_exam_ver"),)

    id: Mapped[str] = mapped_column(Text, primary_key=True)
    exam_id: Mapped[str] = mapped_column(
        Text, ForeignKey("exams.id", ondelete="CASCADE"), nullable=False
    )
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    state: Mapped[str] = mapped_column(Text, nullable=False, default="draft")
    parent_id: Mapped[str | None] = mapped_column(Text, nullable=True)
    input_hash: Mapped[str] = mapped_column(Text, nullable=False)
    rules_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    published_at: Mapped[str | None] = mapped_column(Text, nullable=True)
    revision: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    created_at: Mapped[str] = mapped_column(Text, nullable=False)
    updated_at: Mapped[str] = mapped_column(Text, nullable=False)


class ExamSession(Base):
    __tablename__ = "sessions"

    id: Mapped[str] = mapped_column(Text, primary_key=True)
    plan_id: Mapped[str] = mapped_column(
        Text, ForeignKey("plans.id", ondelete="CASCADE"), nullable=False
    )
    label: Mapped[str] = mapped_column(Text, nullable=False)
    local_date: Mapped[str] = mapped_column(Text, nullable=False)
    starts_at: Mapped[str] = mapped_column(Text, nullable=False)
    ends_at: Mapped[str] = mapped_column(Text, nullable=False)
    start_local: Mapped[str] = mapped_column(Text, nullable=False)
    end_local: Mapped[str] = mapped_column(Text, nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    mode: Mapped[str] = mapped_column(Text, nullable=False, default="paper")
    revision: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    created_at: Mapped[str] = mapped_column(Text, nullable=False)
    updated_at: Mapped[str] = mapped_column(Text, nullable=False)


class RoomSession(Base):
    __tablename__ = "room_sessions"
    __table_args__ = (
        UniqueConstraint(
            "plan_id", "session_id", "exam_room_id", name="uq_room_session"
        ),
    )

    id: Mapped[str] = mapped_column(Text, primary_key=True)
    plan_id: Mapped[str] = mapped_column(
        Text, ForeignKey("plans.id", ondelete="CASCADE"), nullable=False
    )
    session_id: Mapped[str] = mapped_column(
        Text, ForeignKey("sessions.id", ondelete="CASCADE"), nullable=False
    )
    exam_room_id: Mapped[str] = mapped_column(
        Text, ForeignKey("exam_rooms.id", ondelete="CASCADE"), nullable=False
    )
    required_staff_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=1
    )
    revision: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    created_at: Mapped[str] = mapped_column(Text, nullable=False)
    updated_at: Mapped[str] = mapped_column(Text, nullable=False)


class RoomPaper(Base):
    __tablename__ = "room_papers"
    __table_args__ = (
        UniqueConstraint("room_session_id", "requirement_id", name="uq_room_paper_req"),
    )

    id: Mapped[str] = mapped_column(Text, primary_key=True)
    room_session_id: Mapped[str] = mapped_column(
        Text, ForeignKey("room_sessions.id", ondelete="CASCADE"), nullable=False
    )
    requirement_id: Mapped[str] = mapped_column(
        Text, ForeignKey("exam_requirements.id", ondelete="CASCADE"), nullable=False
    )
    group_id: Mapped[str] = mapped_column(
        Text, ForeignKey("exam_groups.id", ondelete="CASCADE"), nullable=False
    )
    locked: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    revision: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    created_at: Mapped[str] = mapped_column(Text, nullable=False)
    updated_at: Mapped[str] = mapped_column(Text, nullable=False)
