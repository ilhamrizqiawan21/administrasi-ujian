"""SQLAlchemy ORM models for TSK (tasks and task_dependencies)."""

from __future__ import annotations

from sqlalchemy import ForeignKey, Index, Integer, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from backend.core.db import Base


class Task(Base):
    __tablename__ = "tasks"
    __table_args__ = (Index("ix_tasks_exam", "exam_id"),)

    id: Mapped[str] = mapped_column(Text, primary_key=True)
    exam_id: Mapped[str] = mapped_column(
        Text, ForeignKey("exams.id", ondelete="CASCADE"), nullable=False
    )
    phase: Mapped[str] = mapped_column(Text, nullable=False, default="preparation")
    title: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")
    pic_id: Mapped[str | None] = mapped_column(
        Text, ForeignKey("exam_people.id", ondelete="SET NULL"), nullable=True
    )
    priority: Mapped[str] = mapped_column(Text, nullable=False, default="medium")
    due_date: Mapped[str] = mapped_column(Text, nullable=False)
    state: Mapped[str] = mapped_column(Text, nullable=False, default="todo")
    blocked_reason: Mapped[str] = mapped_column(Text, nullable=False, default="")
    parent_id: Mapped[str | None] = mapped_column(
        Text, ForeignKey("tasks.id", ondelete="SET NULL"), nullable=True
    )
    evidence_asset_id: Mapped[str | None] = mapped_column(Text, nullable=True)
    evidence_note: Mapped[str] = mapped_column(Text, nullable=False, default="")
    completed_at: Mapped[str | None] = mapped_column(Text, nullable=True)
    completed_by: Mapped[str | None] = mapped_column(Text, nullable=True)
    revision: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    created_at: Mapped[str] = mapped_column(Text, nullable=False)
    updated_at: Mapped[str] = mapped_column(Text, nullable=False)


class TaskDependency(Base):
    __tablename__ = "task_dependencies"
    __table_args__ = (
        UniqueConstraint("task_id", "prerequisite_id", name="uq_task_dep_pair"),
    )

    id: Mapped[str] = mapped_column(Text, primary_key=True)
    exam_id: Mapped[str] = mapped_column(
        Text, ForeignKey("exams.id", ondelete="CASCADE"), nullable=False
    )
    task_id: Mapped[str] = mapped_column(
        Text, ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False
    )
    prerequisite_id: Mapped[str] = mapped_column(
        Text, ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False
    )
    created_at: Mapped[str] = mapped_column(Text, nullable=False)
