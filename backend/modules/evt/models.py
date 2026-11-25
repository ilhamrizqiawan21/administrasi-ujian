"""SQLAlchemy ORM models for EVT and audit_events."""

from __future__ import annotations

from sqlalchemy import ForeignKey, Index, Integer, Text, UniqueConstraint, text
from sqlalchemy.orm import Mapped, mapped_column

from backend.core.db import Base


class Exam(Base):
    __tablename__ = "exams"

    id: Mapped[str] = mapped_column(Text, primary_key=True)
    institution_id: Mapped[str] = mapped_column(
        Text, ForeignKey("institutions.id", ondelete="RESTRICT"), nullable=False
    )
    year_id: Mapped[str] = mapped_column(
        Text, ForeignKey("academic_years.id", ondelete="RESTRICT"), nullable=False
    )
    exam_type_id: Mapped[str] = mapped_column(
        Text, ForeignKey("exam_types.id", ondelete="RESTRICT"), nullable=False
    )
    title: Mapped[str] = mapped_column(Text, nullable=False)
    semester_label: Mapped[str] = mapped_column(Text, nullable=False)
    mode: Mapped[str] = mapped_column(Text, nullable=False, default="paper")
    starts_on: Mapped[str] = mapped_column(Text, nullable=False)
    ends_on: Mapped[str] = mapped_column(Text, nullable=False)
    state: Mapped[str] = mapped_column(Text, nullable=False, default="DRAFT")
    config_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    active_plan_id: Mapped[str | None] = mapped_column(Text, nullable=True)
    revision: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    created_at: Mapped[str] = mapped_column(Text, nullable=False)
    updated_at: Mapped[str] = mapped_column(Text, nullable=False)


class ExamPerson(Base):
    __tablename__ = "exam_people"
    __table_args__ = (
        Index(
            "uq_exam_person_source",
            "exam_id",
            "kind",
            "source_id",
            unique=True,
            sqlite_where=text("source_id IS NOT NULL"),
        ),
    )

    id: Mapped[str] = mapped_column(Text, primary_key=True)
    exam_id: Mapped[str] = mapped_column(
        Text, ForeignKey("exams.id", ondelete="CASCADE"), nullable=False
    )
    source_id: Mapped[str | None] = mapped_column(Text, nullable=True)
    kind: Mapped[str] = mapped_column(Text, nullable=False)
    code: Mapped[str] = mapped_column(Text, nullable=False)
    display_name: Mapped[str] = mapped_column(Text, nullable=False)
    level_label: Mapped[str | None] = mapped_column(Text, nullable=True)
    class_label: Mapped[str | None] = mapped_column(Text, nullable=True)
    photo_asset_id: Mapped[str | None] = mapped_column(Text, nullable=True)
    snapshot_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    revision: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    created_at: Mapped[str] = mapped_column(Text, nullable=False)
    updated_at: Mapped[str] = mapped_column(Text, nullable=False)


class ExamParticipant(Base):
    __tablename__ = "exam_participants"
    __table_args__ = (
        UniqueConstraint("exam_id", "exam_person_id", name="uq_exampart_person"),
        Index(
            "uq_exampart_number",
            "exam_id",
            "participant_number",
            unique=True,
            sqlite_where=text(
                "participant_number IS NOT NULL AND participant_number != ''"
            ),
        ),
    )

    id: Mapped[str] = mapped_column(Text, primary_key=True)
    exam_id: Mapped[str] = mapped_column(
        Text, ForeignKey("exams.id", ondelete="CASCADE"), nullable=False
    )
    exam_person_id: Mapped[str] = mapped_column(
        Text, ForeignKey("exam_people.id", ondelete="CASCADE"), nullable=False
    )
    participant_number: Mapped[str | None] = mapped_column(Text, nullable=True)
    eligibility: Mapped[str] = mapped_column(Text, nullable=False, default="eligible")
    accommodation_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    revision: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    created_at: Mapped[str] = mapped_column(Text, nullable=False)
    updated_at: Mapped[str] = mapped_column(Text, nullable=False)


class ExamRoom(Base):
    __tablename__ = "exam_rooms"
    __table_args__ = (UniqueConstraint("exam_id", "code", name="uq_examroom_code"),)

    id: Mapped[str] = mapped_column(Text, primary_key=True)
    exam_id: Mapped[str] = mapped_column(
        Text, ForeignKey("exams.id", ondelete="CASCADE"), nullable=False
    )
    source_room_id: Mapped[str | None] = mapped_column(Text, nullable=True)
    code: Mapped[str] = mapped_column(Text, nullable=False)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    layout_json: Mapped[str] = mapped_column(Text, nullable=False)
    capacity_limit: Mapped[int] = mapped_column(Integer, nullable=False)
    mode: Mapped[str] = mapped_column(Text, nullable=False)
    revision: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    created_at: Mapped[str] = mapped_column(Text, nullable=False)
    updated_at: Mapped[str] = mapped_column(Text, nullable=False)


class ExamSubject(Base):
    __tablename__ = "exam_subjects"
    __table_args__ = (UniqueConstraint("exam_id", "code", name="uq_examsubj_code"),)

    id: Mapped[str] = mapped_column(Text, primary_key=True)
    exam_id: Mapped[str] = mapped_column(
        Text, ForeignKey("exams.id", ondelete="CASCADE"), nullable=False
    )
    source_subject_id: Mapped[str | None] = mapped_column(Text, nullable=True)
    code: Mapped[str] = mapped_column(Text, nullable=False)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    revision: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    created_at: Mapped[str] = mapped_column(Text, nullable=False)
    updated_at: Mapped[str] = mapped_column(Text, nullable=False)


class ExamGroup(Base):
    __tablename__ = "exam_groups"
    __table_args__ = (UniqueConstraint("exam_id", "label", name="uq_examgroup_label"),)

    id: Mapped[str] = mapped_column(Text, primary_key=True)
    exam_id: Mapped[str] = mapped_column(
        Text, ForeignKey("exams.id", ondelete="CASCADE"), nullable=False
    )
    label: Mapped[str] = mapped_column(Text, nullable=False)
    rule_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    revision: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    created_at: Mapped[str] = mapped_column(Text, nullable=False)
    updated_at: Mapped[str] = mapped_column(Text, nullable=False)


class GroupMember(Base):
    __tablename__ = "group_members"
    __table_args__ = (
        UniqueConstraint("group_id", "participant_id", name="uq_group_member"),
    )

    id: Mapped[str] = mapped_column(Text, primary_key=True)
    group_id: Mapped[str] = mapped_column(
        Text, ForeignKey("exam_groups.id", ondelete="CASCADE"), nullable=False
    )
    participant_id: Mapped[str] = mapped_column(
        Text, ForeignKey("exam_participants.id", ondelete="CASCADE"), nullable=False
    )
    revision: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    created_at: Mapped[str] = mapped_column(Text, nullable=False)
    updated_at: Mapped[str] = mapped_column(Text, nullable=False)


class ExamRequirement(Base):
    __tablename__ = "exam_requirements"
    __table_args__ = (
        UniqueConstraint(
            "group_id",
            "exam_subject_id",
            "attempt_no",
            name="uq_examreq_group_subj_attempt",
        ),
    )

    id: Mapped[str] = mapped_column(Text, primary_key=True)
    group_id: Mapped[str] = mapped_column(
        Text, ForeignKey("exam_groups.id", ondelete="CASCADE"), nullable=False
    )
    exam_subject_id: Mapped[str] = mapped_column(
        Text, ForeignKey("exam_subjects.id", ondelete="CASCADE"), nullable=False
    )
    attempt_no: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    duration_min: Mapped[int] = mapped_column(Integer, nullable=False, default=90)
    mode: Mapped[str] = mapped_column(Text, nullable=False, default="paper")
    eligible_sessions_json: Mapped[str] = mapped_column(
        Text, nullable=False, default="[]"
    )
    revision: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    created_at: Mapped[str] = mapped_column(Text, nullable=False)
    updated_at: Mapped[str] = mapped_column(Text, nullable=False)


class AuditEvent(Base):
    __tablename__ = "audit_events"

    id: Mapped[str] = mapped_column(Text, primary_key=True)
    institution_id: Mapped[str] = mapped_column(
        Text, ForeignKey("institutions.id", ondelete="RESTRICT"), nullable=False
    )
    exam_id: Mapped[str | None] = mapped_column(Text, nullable=True)
    actor: Mapped[str] = mapped_column(Text, nullable=False, default="operator")
    action: Mapped[str] = mapped_column(Text, nullable=False)
    entity_type: Mapped[str] = mapped_column(Text, nullable=False)
    entity_id: Mapped[str] = mapped_column(Text, nullable=False)
    at: Mapped[str] = mapped_column(Text, nullable=False)
    change_summary_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    correlation_id: Mapped[str] = mapped_column(Text, nullable=False, default="-")
