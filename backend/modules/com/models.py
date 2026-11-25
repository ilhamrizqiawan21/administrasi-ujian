"""SQLAlchemy ORM models for COM (committee, program kerja, meetings, signers)."""

from __future__ import annotations

from sqlalchemy import ForeignKey, Index, Integer, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from backend.core.db import Base


class CommitteeRole(Base):
    __tablename__ = "committee_roles"
    __table_args__ = (Index("ix_committee_roles_exam", "exam_id"),)

    id: Mapped[str] = mapped_column(Text, primary_key=True)
    exam_id: Mapped[str] = mapped_column(
        Text, ForeignKey("exams.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(Text, nullable=False)
    parent_id: Mapped[str | None] = mapped_column(
        Text, ForeignKey("committee_roles.id", ondelete="SET NULL"), nullable=True
    )
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    jobdesc: Mapped[str] = mapped_column(Text, nullable=False, default="")
    revision: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    created_at: Mapped[str] = mapped_column(Text, nullable=False)
    updated_at: Mapped[str] = mapped_column(Text, nullable=False)


class CommitteeMember(Base):
    __tablename__ = "committee_members"
    __table_args__ = (
        UniqueConstraint("role_id", "exam_person_id", name="uq_com_role_person"),
    )

    id: Mapped[str] = mapped_column(Text, primary_key=True)
    exam_id: Mapped[str] = mapped_column(
        Text, ForeignKey("exams.id", ondelete="CASCADE"), nullable=False
    )
    role_id: Mapped[str] = mapped_column(
        Text, ForeignKey("committee_roles.id", ondelete="CASCADE"), nullable=False
    )
    exam_person_id: Mapped[str] = mapped_column(
        Text, ForeignKey("exam_people.id", ondelete="CASCADE"), nullable=False
    )
    appointed_on: Mapped[str] = mapped_column(Text, nullable=False, default="")
    note: Mapped[str] = mapped_column(Text, nullable=False, default="")
    revision: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    created_at: Mapped[str] = mapped_column(Text, nullable=False)
    updated_at: Mapped[str] = mapped_column(Text, nullable=False)


class ProgramKerja(Base):
    __tablename__ = "program_kerja"

    id: Mapped[str] = mapped_column(Text, primary_key=True)
    exam_id: Mapped[str] = mapped_column(
        Text, ForeignKey("exams.id", ondelete="CASCADE"), nullable=False, unique=True
    )
    basis_text: Mapped[str] = mapped_column(Text, nullable=False, default="")
    objectives_json: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    milestones_json: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    sections_json: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    revision: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    created_at: Mapped[str] = mapped_column(Text, nullable=False)
    updated_at: Mapped[str] = mapped_column(Text, nullable=False)


class Meeting(Base):
    __tablename__ = "meetings"
    __table_args__ = (Index("ix_meetings_exam", "exam_id"),)

    id: Mapped[str] = mapped_column(Text, primary_key=True)
    exam_id: Mapped[str] = mapped_column(
        Text, ForeignKey("exams.id", ondelete="CASCADE"), nullable=False
    )
    title: Mapped[str] = mapped_column(Text, nullable=False)
    meeting_date: Mapped[str] = mapped_column(Text, nullable=False)
    start_time: Mapped[str] = mapped_column(Text, nullable=False)
    end_time: Mapped[str] = mapped_column(Text, nullable=False)
    location: Mapped[str] = mapped_column(Text, nullable=False, default="")
    agenda: Mapped[str] = mapped_column(Text, nullable=False, default="")
    minutes: Mapped[str] = mapped_column(Text, nullable=False, default="")
    decisions_json: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    revision: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    created_at: Mapped[str] = mapped_column(Text, nullable=False)
    updated_at: Mapped[str] = mapped_column(Text, nullable=False)


class MeetingAttendance(Base):
    __tablename__ = "meeting_attendance"
    __table_args__ = (
        UniqueConstraint(
            "meeting_id", "exam_person_id", name="uq_meeting_attendance_person"
        ),
    )

    id: Mapped[str] = mapped_column(Text, primary_key=True)
    meeting_id: Mapped[str] = mapped_column(
        Text, ForeignKey("meetings.id", ondelete="CASCADE"), nullable=False
    )
    exam_person_id: Mapped[str] = mapped_column(
        Text, ForeignKey("exam_people.id", ondelete="CASCADE"), nullable=False
    )
    state: Mapped[str] = mapped_column(Text, nullable=False, default="unrecorded")
    note: Mapped[str] = mapped_column(Text, nullable=False, default="")
    revision: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    created_at: Mapped[str] = mapped_column(Text, nullable=False)
    updated_at: Mapped[str] = mapped_column(Text, nullable=False)


class ExamSignatory(Base):
    __tablename__ = "exam_signatories"
    __table_args__ = (
        UniqueConstraint("exam_id", "role_key", name="uq_exam_signatory_key"),
    )

    id: Mapped[str] = mapped_column(Text, primary_key=True)
    exam_id: Mapped[str] = mapped_column(
        Text, ForeignKey("exams.id", ondelete="CASCADE"), nullable=False
    )
    role_key: Mapped[str] = mapped_column(Text, nullable=False)
    role_label: Mapped[str] = mapped_column(Text, nullable=False)
    exam_person_id: Mapped[str | None] = mapped_column(
        Text, ForeignKey("exam_people.id", ondelete="SET NULL"), nullable=True
    )
    signer_name: Mapped[str] = mapped_column(Text, nullable=False, default="")
    signer_title: Mapped[str] = mapped_column(Text, nullable=False, default="")
    signer_nip: Mapped[str] = mapped_column(Text, nullable=False, default="")
    signed_date: Mapped[str] = mapped_column(Text, nullable=False, default="")
    signature_asset_id: Mapped[str | None] = mapped_column(Text, nullable=True)
    required: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    revision: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    created_at: Mapped[str] = mapped_column(Text, nullable=False)
    updated_at: Mapped[str] = mapped_column(Text, nullable=False)
