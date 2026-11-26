"""SQLAlchemy ORM models for ARC (archive_packages, retention_backups)."""

from __future__ import annotations

from sqlalchemy import ForeignKey, Index, Integer, Text
from sqlalchemy.orm import Mapped, mapped_column

from backend.core.db import Base


class ArchivePackage(Base):
    __tablename__ = "archive_packages"
    __table_args__ = (Index("ix_arc_pkg_exam", "exam_id"),)

    id: Mapped[str] = mapped_column(Text, primary_key=True)
    institution_id: Mapped[str] = mapped_column(
        Text, ForeignKey("institutions.id", ondelete="CASCADE"), nullable=False
    )
    exam_id: Mapped[str] = mapped_column(
        Text, ForeignKey("exams.id", ondelete="CASCADE"), nullable=False
    )
    file_path: Mapped[str] = mapped_column(Text, nullable=False)
    sha256: Mapped[str] = mapped_column(Text, nullable=False)
    file_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    include_personal_info: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0
    )
    manifest_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    created_at: Mapped[str] = mapped_column(Text, nullable=False)


class RetentionBackup(Base):
    __tablename__ = "retention_backups"
    __table_args__ = (Index("ix_ret_bak_inst", "institution_id"),)

    id: Mapped[str] = mapped_column(Text, primary_key=True)
    institution_id: Mapped[str] = mapped_column(
        Text, ForeignKey("institutions.id", ondelete="CASCADE"), nullable=False
    )
    exam_id: Mapped[str | None] = mapped_column(Text, nullable=True)
    exam_title: Mapped[str] = mapped_column(Text, nullable=False, default="")
    file_path: Mapped[str] = mapped_column(Text, nullable=False)
    sha256: Mapped[str] = mapped_column(Text, nullable=False)
    byte_size: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    authorized_by: Mapped[str] = mapped_column(Text, nullable=False, default="")
    created_at: Mapped[str] = mapped_column(Text, nullable=False)
