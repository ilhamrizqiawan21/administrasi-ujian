"""SQLAlchemy ORM models for EXP (submissions, print quantities, handovers)."""

from __future__ import annotations

from sqlalchemy import ForeignKey, Index, Integer, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from backend.core.db import Base


class SubmissionItem(Base):
    __tablename__ = "submission_items"
    __table_args__ = (
        UniqueConstraint(
            "exam_id",
            "subject_label",
            "class_label",
            "type_code",
            name="uq_sub_item_key",
        ),
        Index("ix_sub_items_exam", "exam_id"),
    )

    id: Mapped[str] = mapped_column(Text, primary_key=True)
    exam_id: Mapped[str] = mapped_column(
        Text, ForeignKey("exams.id", ondelete="CASCADE"), nullable=False
    )
    requirement_id: Mapped[str | None] = mapped_column(
        Text, ForeignKey("exam_requirements.id", ondelete="CASCADE"), nullable=True
    )
    subject_label: Mapped[str] = mapped_column(Text, nullable=False)
    class_label: Mapped[str] = mapped_column(Text, nullable=False)
    type_code: Mapped[str] = mapped_column(Text, nullable=False)
    owner_id: Mapped[str | None] = mapped_column(
        Text, ForeignKey("exam_people.id", ondelete="SET NULL"), nullable=True
    )
    due_date: Mapped[str] = mapped_column(Text, nullable=False, default="")
    state: Mapped[str] = mapped_column(Text, nullable=False, default="missing")
    current_version: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    revision: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    created_at: Mapped[str] = mapped_column(Text, nullable=False)
    updated_at: Mapped[str] = mapped_column(Text, nullable=False)


class SubmissionVersion(Base):
    __tablename__ = "submission_versions"
    __table_args__ = (
        UniqueConstraint("item_id", "version", name="uq_sub_ver_item_ver"),
    )

    id: Mapped[str] = mapped_column(Text, primary_key=True)
    item_id: Mapped[str] = mapped_column(
        Text, ForeignKey("submission_items.id", ondelete="CASCADE"), nullable=False
    )
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    asset_id: Mapped[str] = mapped_column(Text, nullable=False, default="")
    received_at: Mapped[str] = mapped_column(Text, nullable=False)
    reviewer_id: Mapped[str | None] = mapped_column(
        Text, ForeignKey("exam_people.id", ondelete="SET NULL"), nullable=True
    )
    state: Mapped[str] = mapped_column(Text, nullable=False)
    note: Mapped[str] = mapped_column(Text, nullable=False, default="")
    created_at: Mapped[str] = mapped_column(Text, nullable=False)


class PrintQuantity(Base):
    __tablename__ = "print_quantities"
    __table_args__ = (
        UniqueConstraint(
            "room_session_id", "requirement_id", name="uq_print_qty_rs_req"
        ),
    )

    id: Mapped[str] = mapped_column(Text, primary_key=True)
    exam_id: Mapped[str] = mapped_column(
        Text, ForeignKey("exams.id", ondelete="CASCADE"), nullable=False
    )
    plan_id: Mapped[str] = mapped_column(
        Text, ForeignKey("plans.id", ondelete="CASCADE"), nullable=False
    )
    room_session_id: Mapped[str] = mapped_column(
        Text, ForeignKey("room_sessions.id", ondelete="CASCADE"), nullable=False
    )
    requirement_id: Mapped[str] = mapped_column(
        Text, ForeignKey("exam_requirements.id", ondelete="CASCADE"), nullable=False
    )
    roster_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    reserve_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    override_qty: Mapped[int | None] = mapped_column(Integer, nullable=True)
    exclude_cbt: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    revision: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    created_at: Mapped[str] = mapped_column(Text, nullable=False)
    updated_at: Mapped[str] = mapped_column(Text, nullable=False)


class Handover(Base):
    __tablename__ = "handovers"

    id: Mapped[str] = mapped_column(Text, primary_key=True)
    exam_id: Mapped[str] = mapped_column(
        Text, ForeignKey("exams.id", ondelete="CASCADE"), nullable=False
    )
    room_session_id: Mapped[str | None] = mapped_column(
        Text, ForeignKey("room_sessions.id", ondelete="SET NULL"), nullable=True
    )
    kind: Mapped[str] = mapped_column(Text, nullable=False)
    material_type: Mapped[str] = mapped_column(Text, nullable=False)
    expected_qty: Mapped[int] = mapped_column(Integer, nullable=False)
    actual_qty: Mapped[int] = mapped_column(Integer, nullable=False)
    discrepancy: Mapped[int] = mapped_column(Integer, nullable=False)
    from_person_name: Mapped[str] = mapped_column(Text, nullable=False)
    to_person_name: Mapped[str] = mapped_column(Text, nullable=False)
    handed_at: Mapped[str] = mapped_column(Text, nullable=False)
    note: Mapped[str] = mapped_column(Text, nullable=False, default="")
    created_at: Mapped[str] = mapped_column(Text, nullable=False)
