"""SQLAlchemy ORM models for BAK (backup_records, backup_schedule_settings)."""

from __future__ import annotations

from sqlalchemy import ForeignKey, Index, Integer, Text
from sqlalchemy.orm import Mapped, mapped_column

from backend.core.db import Base


class BackupRecord(Base):
    __tablename__ = "backup_records"
    __table_args__ = (Index("ix_bak_rec_inst", "institution_id"),)

    id: Mapped[str] = mapped_column(Text, primary_key=True)
    institution_id: Mapped[str] = mapped_column(
        Text, ForeignKey("institutions.id", ondelete="CASCADE"), nullable=False
    )
    kind: Mapped[str] = mapped_column(Text, nullable=False, default="manual")
    file_path: Mapped[str] = mapped_column(Text, nullable=False)
    sha256: Mapped[str] = mapped_column(Text, nullable=False)
    byte_size: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    schema_revision: Mapped[str] = mapped_column(Text, nullable=False, default="")
    status: Mapped[str] = mapped_column(Text, nullable=False, default="valid")
    error_message: Mapped[str] = mapped_column(Text, nullable=False, default="")
    manifest_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    created_at: Mapped[str] = mapped_column(Text, nullable=False)


class BackupScheduleSetting(Base):
    __tablename__ = "backup_schedule_settings"

    institution_id: Mapped[str] = mapped_column(
        Text, ForeignKey("institutions.id", ondelete="CASCADE"), primary_key=True
    )
    auto_on_startup: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    auto_on_close: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    retention_count: Mapped[int] = mapped_column(Integer, nullable=False, default=7)
    last_run_at: Mapped[str | None] = mapped_column(Text, nullable=True)
    last_status: Mapped[str] = mapped_column(Text, nullable=False, default="idle")
    last_error: Mapped[str] = mapped_column(Text, nullable=False, default="")
    updated_at: Mapped[str] = mapped_column(Text, nullable=False)
