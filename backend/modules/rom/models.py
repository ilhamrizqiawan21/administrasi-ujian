"""SQLAlchemy ORM models for ROM (seats, assignments, sittings)."""

from __future__ import annotations

from sqlalchemy import ForeignKey, Integer, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from backend.core.db import Base


class Seat(Base):
    __tablename__ = "seats"
    __table_args__ = (
        UniqueConstraint("plan_id", "exam_room_id", "seat_code", name="uq_seat_code"),
    )

    id: Mapped[str] = mapped_column(Text, primary_key=True)
    plan_id: Mapped[str] = mapped_column(
        Text, ForeignKey("plans.id", ondelete="CASCADE"), nullable=False
    )
    exam_room_id: Mapped[str] = mapped_column(
        Text, ForeignKey("exam_rooms.id", ondelete="CASCADE"), nullable=False
    )
    seat_code: Mapped[str] = mapped_column(Text, nullable=False)
    desk_row: Mapped[int] = mapped_column(Integer, nullable=False)
    desk_col: Mapped[int] = mapped_column(Integer, nullable=False)
    seat_index: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    enabled: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    accessible: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    revision: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    created_at: Mapped[str] = mapped_column(Text, nullable=False)
    updated_at: Mapped[str] = mapped_column(Text, nullable=False)


class PlanSeatAssignment(Base):
    __tablename__ = "plan_seat_assignments"
    __table_args__ = (
        UniqueConstraint("plan_id", "participant_id", name="uq_plan_seat_part"),
        UniqueConstraint("plan_id", "seat_id", name="uq_plan_seat_occ"),
    )

    id: Mapped[str] = mapped_column(Text, primary_key=True)
    plan_id: Mapped[str] = mapped_column(
        Text, ForeignKey("plans.id", ondelete="CASCADE"), nullable=False
    )
    participant_id: Mapped[str] = mapped_column(
        Text, ForeignKey("exam_participants.id", ondelete="CASCADE"), nullable=False
    )
    exam_room_id: Mapped[str] = mapped_column(
        Text, ForeignKey("exam_rooms.id", ondelete="CASCADE"), nullable=False
    )
    seat_id: Mapped[str] = mapped_column(
        Text, ForeignKey("seats.id", ondelete="CASCADE"), nullable=False
    )
    locked: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    revision: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    created_at: Mapped[str] = mapped_column(Text, nullable=False)
    updated_at: Mapped[str] = mapped_column(Text, nullable=False)


class ParticipantSitting(Base):
    __tablename__ = "participant_sittings"
    __table_args__ = (
        UniqueConstraint(
            "plan_id", "participant_id", "requirement_id", name="uq_sitting_part_req"
        ),
        UniqueConstraint("room_session_id", "seat_id", name="uq_sitting_rs_seat"),
    )

    id: Mapped[str] = mapped_column(Text, primary_key=True)
    plan_id: Mapped[str] = mapped_column(
        Text, ForeignKey("plans.id", ondelete="CASCADE"), nullable=False
    )
    room_session_id: Mapped[str] = mapped_column(
        Text, ForeignKey("room_sessions.id", ondelete="CASCADE"), nullable=False
    )
    participant_id: Mapped[str] = mapped_column(
        Text, ForeignKey("exam_participants.id", ondelete="CASCADE"), nullable=False
    )
    requirement_id: Mapped[str] = mapped_column(
        Text, ForeignKey("exam_requirements.id", ondelete="CASCADE"), nullable=False
    )
    seat_id: Mapped[str] = mapped_column(
        Text, ForeignKey("seats.id", ondelete="RESTRICT"), nullable=False
    )
    locked: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    revision: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    created_at: Mapped[str] = mapped_column(Text, nullable=False)
    updated_at: Mapped[str] = mapped_column(Text, nullable=False)
