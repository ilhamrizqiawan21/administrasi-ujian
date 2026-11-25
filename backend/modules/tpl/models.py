"""SQLAlchemy ORM models for TPL (letterheads, templates, theme_profiles)."""

from __future__ import annotations

from sqlalchemy import ForeignKey, Index, Integer, Text
from sqlalchemy.orm import Mapped, mapped_column

from backend.core.db import Base


class Letterhead(Base):
    __tablename__ = "letterheads"
    __table_args__ = (Index("ix_letterheads_inst", "institution_id"),)

    id: Mapped[str] = mapped_column(Text, primary_key=True)
    institution_id: Mapped[str] = mapped_column(
        Text, ForeignKey("institutions.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(Text, nullable=False)
    mode: Mapped[str] = mapped_column(Text, nullable=False, default="manual")
    config_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    asset_id: Mapped[str | None] = mapped_column(Text, nullable=True)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    active: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    created_at: Mapped[str] = mapped_column(Text, nullable=False)


class TemplateRecord(Base):
    __tablename__ = "templates"
    __table_args__ = (Index("ix_templates_inst_type", "institution_id", "doc_type"),)

    id: Mapped[str] = mapped_column(Text, primary_key=True)
    institution_id: Mapped[str | None] = mapped_column(
        Text, ForeignKey("institutions.id", ondelete="CASCADE"), nullable=True
    )
    doc_type: Mapped[str] = mapped_column(Text, nullable=False)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    engine: Mapped[str] = mapped_column(Text, nullable=False, default="reportlab")
    asset_id: Mapped[str | None] = mapped_column(Text, nullable=True)
    layout_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    mapping_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    active: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    created_at: Mapped[str] = mapped_column(Text, nullable=False)


class ThemeProfile(Base):
    __tablename__ = "theme_profiles"

    id: Mapped[str] = mapped_column(Text, primary_key=True)
    institution_id: Mapped[str] = mapped_column(
        Text, ForeignKey("institutions.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(Text, nullable=False)
    tokens_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    active: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    created_at: Mapped[str] = mapped_column(Text, nullable=False)
