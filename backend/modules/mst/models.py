"""SQLAlchemy ORM models for MST master data tables."""

from __future__ import annotations

from sqlalchemy import ForeignKey, Index, Integer, Text, UniqueConstraint, text
from sqlalchemy.orm import Mapped, mapped_column

from backend.core.db import Base


class SchoolClass(Base):
    __tablename__ = "classes"
    __table_args__ = (
        UniqueConstraint(
            "year_id", "level_id", "name", name="uq_class_year_level_name"
        ),
    )

    id: Mapped[str] = mapped_column(Text, primary_key=True)
    institution_id: Mapped[str] = mapped_column(
        Text, ForeignKey("institutions.id", ondelete="RESTRICT"), nullable=False
    )
    year_id: Mapped[str] = mapped_column(
        Text, ForeignKey("academic_years.id", ondelete="RESTRICT"), nullable=False
    )
    level_id: Mapped[str] = mapped_column(
        Text, ForeignKey("levels.id", ondelete="RESTRICT"), nullable=False
    )
    name: Mapped[str] = mapped_column(Text, nullable=False)
    program: Mapped[str | None] = mapped_column(Text, nullable=True)
    revision: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    created_at: Mapped[str] = mapped_column(Text, nullable=False)
    updated_at: Mapped[str] = mapped_column(Text, nullable=False)


class Student(Base):
    __tablename__ = "students"
    __table_args__ = (
        Index(
            "uq_student_inst_nis",
            "institution_id",
            "nis",
            unique=True,
            sqlite_where=text("nis IS NOT NULL AND nis != ''"),
        ),
    )

    id: Mapped[str] = mapped_column(Text, primary_key=True)
    institution_id: Mapped[str] = mapped_column(
        Text, ForeignKey("institutions.id", ondelete="RESTRICT"), nullable=False
    )
    nis: Mapped[str | None] = mapped_column(Text, nullable=True)
    nisn: Mapped[str | None] = mapped_column(Text, nullable=True)
    full_name: Mapped[str] = mapped_column(Text, nullable=False)
    gender: Mapped[str | None] = mapped_column(Text, nullable=True)
    photo_asset_id: Mapped[str | None] = mapped_column(
        Text, ForeignKey("assets.id", ondelete="SET NULL"), nullable=True
    )
    accommodation_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    active: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    revision: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    created_at: Mapped[str] = mapped_column(Text, nullable=False)
    updated_at: Mapped[str] = mapped_column(Text, nullable=False)


class Enrollment(Base):
    __tablename__ = "enrollments"
    __table_args__ = (
        UniqueConstraint("student_id", "year_id", name="uq_enrollment_student_year"),
    )

    id: Mapped[str] = mapped_column(Text, primary_key=True)
    institution_id: Mapped[str] = mapped_column(
        Text, ForeignKey("institutions.id", ondelete="RESTRICT"), nullable=False
    )
    student_id: Mapped[str] = mapped_column(
        Text, ForeignKey("students.id", ondelete="RESTRICT"), nullable=False
    )
    class_id: Mapped[str] = mapped_column(
        Text, ForeignKey("classes.id", ondelete="RESTRICT"), nullable=False
    )
    year_id: Mapped[str] = mapped_column(
        Text, ForeignKey("academic_years.id", ondelete="RESTRICT"), nullable=False
    )
    status: Mapped[str] = mapped_column(Text, nullable=False, default="active")
    revision: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    created_at: Mapped[str] = mapped_column(Text, nullable=False)
    updated_at: Mapped[str] = mapped_column(Text, nullable=False)


class Staff(Base):
    __tablename__ = "staff"
    __table_args__ = (
        UniqueConstraint("institution_id", "staff_code", name="uq_staff_inst_code"),
    )

    id: Mapped[str] = mapped_column(Text, primary_key=True)
    institution_id: Mapped[str] = mapped_column(
        Text, ForeignKey("institutions.id", ondelete="RESTRICT"), nullable=False
    )
    staff_code: Mapped[str] = mapped_column(Text, nullable=False)
    nip: Mapped[str | None] = mapped_column(Text, nullable=True)
    full_name: Mapped[str] = mapped_column(Text, nullable=False)
    role: Mapped[str] = mapped_column(Text, nullable=False, default="teacher")
    active: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    revision: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    created_at: Mapped[str] = mapped_column(Text, nullable=False)
    updated_at: Mapped[str] = mapped_column(Text, nullable=False)


class Subject(Base):
    __tablename__ = "subjects"
    __table_args__ = (
        UniqueConstraint("institution_id", "code", name="uq_subject_inst_code"),
    )

    id: Mapped[str] = mapped_column(Text, primary_key=True)
    institution_id: Mapped[str] = mapped_column(
        Text, ForeignKey("institutions.id", ondelete="RESTRICT"), nullable=False
    )
    code: Mapped[str] = mapped_column(Text, nullable=False)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    category: Mapped[str | None] = mapped_column(Text, nullable=True)
    revision: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    created_at: Mapped[str] = mapped_column(Text, nullable=False)
    updated_at: Mapped[str] = mapped_column(Text, nullable=False)


class TeachingAssignment(Base):
    __tablename__ = "teaching_assignments"
    __table_args__ = (
        UniqueConstraint(
            "staff_id", "class_id", "subject_id", name="uq_teaching_triple"
        ),
    )

    id: Mapped[str] = mapped_column(Text, primary_key=True)
    institution_id: Mapped[str] = mapped_column(
        Text, ForeignKey("institutions.id", ondelete="RESTRICT"), nullable=False
    )
    staff_id: Mapped[str] = mapped_column(
        Text, ForeignKey("staff.id", ondelete="RESTRICT"), nullable=False
    )
    class_id: Mapped[str] = mapped_column(
        Text, ForeignKey("classes.id", ondelete="RESTRICT"), nullable=False
    )
    subject_id: Mapped[str] = mapped_column(
        Text, ForeignKey("subjects.id", ondelete="RESTRICT"), nullable=False
    )
    revision: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    created_at: Mapped[str] = mapped_column(Text, nullable=False)
    updated_at: Mapped[str] = mapped_column(Text, nullable=False)


class Room(Base):
    __tablename__ = "rooms"
    __table_args__ = (
        UniqueConstraint("institution_id", "code", name="uq_room_inst_code"),
    )

    id: Mapped[str] = mapped_column(Text, primary_key=True)
    institution_id: Mapped[str] = mapped_column(
        Text, ForeignKey("institutions.id", ondelete="RESTRICT"), nullable=False
    )
    code: Mapped[str] = mapped_column(Text, nullable=False)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    mode: Mapped[str] = mapped_column(Text, nullable=False, default="paper")
    capacity_limit: Mapped[int] = mapped_column(Integer, nullable=False)
    layout_json: Mapped[str] = mapped_column(Text, nullable=False)
    revision: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    created_at: Mapped[str] = mapped_column(Text, nullable=False)
    updated_at: Mapped[str] = mapped_column(Text, nullable=False)
