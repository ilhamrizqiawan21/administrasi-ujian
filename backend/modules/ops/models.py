"""SQLAlchemy ORM models for OPS (attendance, reports, incidents, make-up)."""

from __future__ import annotations

from sqlalchemy import ForeignKey, Integer, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from backend.core.db import Base


class RoomSessionState(Base):
    __tablename__ = "room_session_states"

    id: Mapped[str] = mapped_column(Text, primary_key=True)
    plan_id: Mapped[str] = mapped_column(
        Text, ForeignKey("plans.id", ondelete="CASCADE"), nullable=False
    )
    room_session_id: Mapped[str] = mapped_column(
        Text,
        ForeignKey("room_sessions.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    actual_state: Mapped[str] = mapped_column(Text, nullable=False, default="scheduled")
    started_at: Mapped[str | None] = mapped_column(Text, nullable=True)
    finished_at: Mapped[str | None] = mapped_column(Text, nullable=True)
    updated_at: Mapped[str] = mapped_column(Text, nullable=False)


class ParticipantAttendance(Base):
    __tablename__ = "participant_attendance"

    id: Mapped[str] = mapped_column(Text, primary_key=True)
    exam_id: Mapped[str] = mapped_column(
        Text, ForeignKey("exams.id", ondelete="CASCADE"), nullable=False
    )
    sitting_id: Mapped[str] = mapped_column(
        Text,
        ForeignKey("participant_sittings.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    state: Mapped[str] = mapped_column(Text, nullable=False, default="unrecorded")
    recorded_at: Mapped[str] = mapped_column(Text, nullable=False)
    note: Mapped[str] = mapped_column(Text, nullable=False, default="")
    revision: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    updated_at: Mapped[str] = mapped_column(Text, nullable=False)


class StaffAttendance(Base):
    __tablename__ = "staff_attendance"

    id: Mapped[str] = mapped_column(Text, primary_key=True)
    exam_id: Mapped[str] = mapped_column(
        Text, ForeignKey("exams.id", ondelete="CASCADE"), nullable=False
    )
    slot_id: Mapped[str] = mapped_column(
        Text,
        ForeignKey("invigilation_slots.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    planned_person_id: Mapped[str | None] = mapped_column(
        Text, ForeignKey("exam_people.id", ondelete="SET NULL"), nullable=True
    )
    actual_person_id: Mapped[str | None] = mapped_column(
        Text, ForeignKey("exam_people.id", ondelete="SET NULL"), nullable=True
    )
    state: Mapped[str] = mapped_column(Text, nullable=False, default="unrecorded")
    recorded_at: Mapped[str] = mapped_column(Text, nullable=False)
    approved_by: Mapped[str] = mapped_column(Text, nullable=False, default="")
    note: Mapped[str] = mapped_column(Text, nullable=False, default="")
    revision: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    updated_at: Mapped[str] = mapped_column(Text, nullable=False)


class CommitteeAttendance(Base):
    __tablename__ = "committee_attendance"
    __table_args__ = (
        UniqueConstraint(
            "exam_id",
            "att_date",
            "shift",
            "exam_person_id",
            name="uq_com_att_day_shift",
        ),
    )

    id: Mapped[str] = mapped_column(Text, primary_key=True)
    exam_id: Mapped[str] = mapped_column(
        Text, ForeignKey("exams.id", ondelete="CASCADE"), nullable=False
    )
    att_date: Mapped[str] = mapped_column(Text, nullable=False)
    shift: Mapped[str] = mapped_column(Text, nullable=False)
    exam_person_id: Mapped[str] = mapped_column(
        Text, ForeignKey("exam_people.id", ondelete="CASCADE"), nullable=False
    )
    state: Mapped[str] = mapped_column(Text, nullable=False, default="present")
    note: Mapped[str] = mapped_column(Text, nullable=False, default="")
    recorded_at: Mapped[str] = mapped_column(Text, nullable=False)
    updated_at: Mapped[str] = mapped_column(Text, nullable=False)


class SessionReport(Base):
    __tablename__ = "session_reports"

    id: Mapped[str] = mapped_column(Text, primary_key=True)
    exam_id: Mapped[str] = mapped_column(
        Text, ForeignKey("exams.id", ondelete="CASCADE"), nullable=False
    )
    room_session_id: Mapped[str] = mapped_column(
        Text,
        ForeignKey("room_sessions.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    remarks: Mapped[str] = mapped_column(Text, nullable=False, default="")
    signer_snapshot_json: Mapped[str] = mapped_column(
        Text, nullable=False, default="{}"
    )
    counts_snapshot_json: Mapped[str] = mapped_column(
        Text, nullable=False, default="{}"
    )
    finalized_at: Mapped[str | None] = mapped_column(Text, nullable=True)
    revision: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    updated_at: Mapped[str] = mapped_column(Text, nullable=False)


class Incident(Base):
    __tablename__ = "incidents"

    id: Mapped[str] = mapped_column(Text, primary_key=True)
    exam_id: Mapped[str] = mapped_column(
        Text, ForeignKey("exams.id", ondelete="CASCADE"), nullable=False
    )
    room_session_id: Mapped[str] = mapped_column(
        Text, ForeignKey("room_sessions.id", ondelete="CASCADE"), nullable=False
    )
    type_code: Mapped[str] = mapped_column(Text, nullable=False)
    severity: Mapped[str] = mapped_column(Text, nullable=False, default="low")
    participant_id: Mapped[str | None] = mapped_column(
        Text, ForeignKey("exam_participants.id", ondelete="SET NULL"), nullable=True
    )
    note: Mapped[str] = mapped_column(Text, nullable=False)
    resolution: Mapped[str] = mapped_column(Text, nullable=False, default="")
    confidential: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    recorded_at: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[str] = mapped_column(Text, nullable=False)


class MakeupLink(Base):
    __tablename__ = "makeup_links"

    id: Mapped[str] = mapped_column(Text, primary_key=True)
    exam_id: Mapped[str] = mapped_column(
        Text, ForeignKey("exams.id", ondelete="CASCADE"), nullable=False
    )
    original_sitting_id: Mapped[str] = mapped_column(
        Text,
        ForeignKey("participant_sittings.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    makeup_sitting_id: Mapped[str | None] = mapped_column(
        Text,
        ForeignKey("participant_sittings.id", ondelete="SET NULL"),
        nullable=True,
    )
    target_room_session_id: Mapped[str] = mapped_column(
        Text, ForeignKey("room_sessions.id", ondelete="CASCADE"), nullable=False
    )
    reason: Mapped[str] = mapped_column(Text, nullable=False, default="")
    created_at: Mapped[str] = mapped_column(Text, nullable=False)
