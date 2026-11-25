"""SQLAlchemy ORM models for LPJ (lpj_versions, lpj_evaluations, lpj_attachments)."""

from __future__ import annotations

from sqlalchemy import ForeignKey, Integer, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from backend.core.db import Base


class LpjVersion(Base):
    __tablename__ = "lpj_versions"
    __table_args__ = (
        UniqueConstraint("exam_id", "version", name="uq_lpj_ver_exam_num"),
    )

    id: Mapped[str] = mapped_column(Text, primary_key=True)
    institution_id: Mapped[str] = mapped_column(
        Text, ForeignKey("institutions.id", ondelete="CASCADE"), nullable=False
    )
    exam_id: Mapped[str] = mapped_column(
        Text, ForeignKey("exams.id", ondelete="CASCADE"), nullable=False
    )
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    state: Mapped[str] = mapped_column(Text, nullable=False, default="draft")
    title: Mapped[str] = mapped_column(Text, nullable=False)
    sections_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    snapshot_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    doc_run_id: Mapped[str | None] = mapped_column(
        Text, ForeignKey("document_runs.id", ondelete="SET NULL"), nullable=True
    )
    finalized_at: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[str] = mapped_column(Text, nullable=False)
    updated_at: Mapped[str] = mapped_column(Text, nullable=False)


class LpjEvaluation(Base):
    __tablename__ = "lpj_evaluations"

    id: Mapped[str] = mapped_column(Text, primary_key=True)
    lpj_version_id: Mapped[str] = mapped_column(
        Text, ForeignKey("lpj_versions.id", ondelete="CASCADE"), nullable=False
    )
    incident_id: Mapped[str | None] = mapped_column(
        Text, ForeignKey("incidents.id", ondelete="SET NULL"), nullable=True
    )
    issue_title: Mapped[str] = mapped_column(Text, nullable=False)
    resolution: Mapped[str] = mapped_column(Text, nullable=False, default="")
    recommendation: Mapped[str] = mapped_column(Text, nullable=False, default="")
    pic_name: Mapped[str] = mapped_column(Text, nullable=False, default="")
    notes: Mapped[str] = mapped_column(Text, nullable=False, default="")
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    created_at: Mapped[str] = mapped_column(Text, nullable=False)


class LpjAttachment(Base):
    __tablename__ = "lpj_attachments"

    id: Mapped[str] = mapped_column(Text, primary_key=True)
    lpj_version_id: Mapped[str] = mapped_column(
        Text, ForeignKey("lpj_versions.id", ondelete="CASCADE"), nullable=False
    )
    doc_run_id: Mapped[str | None] = mapped_column(
        Text, ForeignKey("document_runs.id", ondelete="SET NULL"), nullable=True
    )
    title: Mapped[str] = mapped_column(Text, nullable=False)
    file_path: Mapped[str] = mapped_column(Text, nullable=False, default="")
    included: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    exclusion_reason: Mapped[str] = mapped_column(Text, nullable=False, default="")
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    created_at: Mapped[str] = mapped_column(Text, nullable=False)
