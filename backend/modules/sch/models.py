"""SQLAlchemy ORM models for SCH (invigilation scheduling)."""

from __future__ import annotations

from sqlalchemy import ForeignKey, Index, Integer, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from backend.core.db import Base


class StaffAvailability(Base):
    __tablename__ = "staff_availability"
    __table_args__ = (Index("ix_staff_avail_exam_person", "exam_id", "exam_person_id"),)

    id: Mapped[str] = mapped_column(Text, primary_key=True)
    exam_id: Mapped[str] = mapped_column(
        Text, ForeignKey("exams.id", ondelete="CASCADE"), nullable=False
    )
    exam_person_id: Mapped[str] = mapped_column(
        Text, ForeignKey("exam_people.id", ondelete="CASCADE"), nullable=False
    )
    starts_at: Mapped[str] = mapped_column(Text, nullable=False)
    ends_at: Mapped[str] = mapped_column(Text, nullable=False)
    state: Mapped[str] = mapped_column(Text, nullable=False, default="unavailable")
    reason: Mapped[str] = mapped_column(Text, nullable=False, default="")
    revision: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    created_at: Mapped[str] = mapped_column(Text, nullable=False)
    updated_at: Mapped[str] = mapped_column(Text, nullable=False)


class StaffProfile(Base):
    __tablename__ = "staff_profiles"
    __table_args__ = (
        UniqueConstraint(
            "exam_id", "exam_person_id", name="uq_staff_profile_exam_person"
        ),
    )

    id: Mapped[str] = mapped_column(Text, primary_key=True)
    exam_id: Mapped[str] = mapped_column(
        Text, ForeignKey("exams.id", ondelete="CASCADE"), nullable=False
    )
    exam_person_id: Mapped[str] = mapped_column(
        Text, ForeignKey("exam_people.id", ondelete="CASCADE"), nullable=False
    )
    max_daily: Mapped[int | None] = mapped_column(Integer, nullable=True)
    max_total: Mapped[int | None] = mapped_column(Integer, nullable=True)
    target_weight_pct: Mapped[int] = mapped_column(Integer, nullable=False, default=100)
    role_skills_json: Mapped[str] = mapped_column(
        Text, nullable=False, default='["primary","secondary"]'
    )
    revision: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    created_at: Mapped[str] = mapped_column(Text, nullable=False)
    updated_at: Mapped[str] = mapped_column(Text, nullable=False)


class InvigilationSlot(Base):
    __tablename__ = "invigilation_slots"
    __table_args__ = (
        UniqueConstraint(
            "room_session_id", "role_code", "slot_index", name="uq_inv_slot_rs_role_idx"
        ),
        Index("ix_inv_slots_plan", "plan_id"),
    )

    id: Mapped[str] = mapped_column(Text, primary_key=True)
    plan_id: Mapped[str] = mapped_column(
        Text, ForeignKey("plans.id", ondelete="CASCADE"), nullable=False
    )
    room_session_id: Mapped[str] = mapped_column(
        Text, ForeignKey("room_sessions.id", ondelete="CASCADE"), nullable=False
    )
    role_code: Mapped[str] = mapped_column(Text, nullable=False)
    slot_index: Mapped[int] = mapped_column(Integer, nullable=False)
    revision: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    created_at: Mapped[str] = mapped_column(Text, nullable=False)
    updated_at: Mapped[str] = mapped_column(Text, nullable=False)


class Invigilation(Base):
    __tablename__ = "invigilations"
    __table_args__ = (
        UniqueConstraint("plan_id", "slot_id", name="uq_inv_plan_slot"),
        Index("ix_invigilations_plan", "plan_id"),
    )

    id: Mapped[str] = mapped_column(Text, primary_key=True)
    plan_id: Mapped[str] = mapped_column(
        Text, ForeignKey("plans.id", ondelete="CASCADE"), nullable=False
    )
    slot_id: Mapped[str] = mapped_column(
        Text, ForeignKey("invigilation_slots.id", ondelete="CASCADE"), nullable=False
    )
    exam_person_id: Mapped[str] = mapped_column(
        Text, ForeignKey("exam_people.id", ondelete="CASCADE"), nullable=False
    )
    locked: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    revision: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    created_at: Mapped[str] = mapped_column(Text, nullable=False)
    updated_at: Mapped[str] = mapped_column(Text, nullable=False)


class InvigilationReserve(Base):
    __tablename__ = "invigilation_reserves"
    __table_args__ = (
        UniqueConstraint(
            "plan_id", "session_id", "exam_person_id", name="uq_inv_res_plan_sess_pers"
        ),
    )

    id: Mapped[str] = mapped_column(Text, primary_key=True)
    plan_id: Mapped[str] = mapped_column(
        Text, ForeignKey("plans.id", ondelete="CASCADE"), nullable=False
    )
    session_id: Mapped[str] = mapped_column(
        Text, ForeignKey("sessions.id", ondelete="CASCADE"), nullable=False
    )
    exam_person_id: Mapped[str] = mapped_column(
        Text, ForeignKey("exam_people.id", ondelete="CASCADE"), nullable=False
    )
    locked: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    revision: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    created_at: Mapped[str] = mapped_column(Text, nullable=False)
    updated_at: Mapped[str] = mapped_column(Text, nullable=False)


class SolverRun(Base):
    __tablename__ = "solver_runs"
    __table_args__ = (Index("ix_solver_runs_plan", "plan_id"),)

    id: Mapped[str] = mapped_column(Text, primary_key=True)
    exam_id: Mapped[str] = mapped_column(
        Text, ForeignKey("exams.id", ondelete="CASCADE"), nullable=False
    )
    plan_id: Mapped[str] = mapped_column(
        Text, ForeignKey("plans.id", ondelete="CASCADE"), nullable=False
    )
    kind: Mapped[str] = mapped_column(Text, nullable=False)
    input_hash: Mapped[str] = mapped_column(Text, nullable=False)
    seed: Mapped[int] = mapped_column(Integer, nullable=False)
    solver_version: Mapped[str] = mapped_column(Text, nullable=False)
    weights_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    status: Mapped[str] = mapped_column(Text, nullable=False)
    score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    diagnostics_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    created_at: Mapped[str] = mapped_column(Text, nullable=False)
