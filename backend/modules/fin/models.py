"""SQLAlchemy ORM models for FIN (budget, ledger, honorarium)."""

from __future__ import annotations

from sqlalchemy import ForeignKey, Index, Integer, Text, UniqueConstraint, text
from sqlalchemy.orm import Mapped, mapped_column

from backend.core.db import Base


class BudgetCategory(Base):
    __tablename__ = "budget_categories"
    __table_args__ = (
        UniqueConstraint("exam_id", "label", name="uq_budget_cat_exam_label"),
    )

    id: Mapped[str] = mapped_column(Text, primary_key=True)
    exam_id: Mapped[str] = mapped_column(
        Text, ForeignKey("exams.id", ondelete="CASCADE"), nullable=False
    )
    label: Mapped[str] = mapped_column(Text, nullable=False)
    parent_id: Mapped[str | None] = mapped_column(
        Text, ForeignKey("budget_categories.id", ondelete="SET NULL"), nullable=True
    )
    source_fund: Mapped[str] = mapped_column(Text, nullable=False, default="BOS")
    default_unit: Mapped[str] = mapped_column(Text, nullable=False, default="paket")
    archived: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    revision: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    created_at: Mapped[str] = mapped_column(Text, nullable=False)


class BudgetVersion(Base):
    __tablename__ = "budget_versions"
    __table_args__ = (
        UniqueConstraint("exam_id", "number", name="uq_budget_ver_exam_num"),
    )

    id: Mapped[str] = mapped_column(Text, primary_key=True)
    exam_id: Mapped[str] = mapped_column(
        Text, ForeignKey("exams.id", ondelete="CASCADE"), nullable=False
    )
    number: Mapped[int] = mapped_column(Integer, nullable=False)
    state: Mapped[str] = mapped_column(Text, nullable=False, default="draft")
    approved_at: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[str] = mapped_column(Text, nullable=False)


class BudgetLine(Base):
    __tablename__ = "budget_lines"

    id: Mapped[str] = mapped_column(Text, primary_key=True)
    budget_version_id: Mapped[str] = mapped_column(
        Text, ForeignKey("budget_versions.id", ondelete="CASCADE"), nullable=False
    )
    category_id: Mapped[str] = mapped_column(
        Text, ForeignKey("budget_categories.id", ondelete="RESTRICT"), nullable=False
    )
    description: Mapped[str] = mapped_column(Text, nullable=False)
    qty_decimal: Mapped[str] = mapped_column(Text, nullable=False)
    unit: Mapped[str] = mapped_column(Text, nullable=False)
    unit_rate_idr: Mapped[int] = mapped_column(Integer, nullable=False)
    amount_idr: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[str] = mapped_column(Text, nullable=False)


class LedgerEntry(Base):
    __tablename__ = "ledger_entries"
    __table_args__ = (
        Index(
            "uq_ledger_source_key",
            "source_key",
            unique=True,
            sqlite_where=text("source_key IS NOT NULL"),
        ),
        Index(
            "uq_ledger_reverses_id",
            "reverses_id",
            unique=True,
            sqlite_where=text("reverses_id IS NOT NULL"),
        ),
    )

    id: Mapped[str] = mapped_column(Text, primary_key=True)
    exam_id: Mapped[str] = mapped_column(
        Text, ForeignKey("exams.id", ondelete="CASCADE"), nullable=False
    )
    category_id: Mapped[str] = mapped_column(
        Text, ForeignKey("budget_categories.id", ondelete="RESTRICT"), nullable=False
    )
    kind: Mapped[str] = mapped_column(Text, nullable=False)
    amount_idr: Mapped[int] = mapped_column(Integer, nullable=False)
    entry_date: Mapped[str] = mapped_column(Text, nullable=False)
    reference: Mapped[str] = mapped_column(Text, nullable=False, default="")
    payee: Mapped[str] = mapped_column(Text, nullable=False, default="")
    attachment_asset_id: Mapped[str | None] = mapped_column(Text, nullable=True)
    state: Mapped[str] = mapped_column(Text, nullable=False, default="draft")
    reverses_id: Mapped[str | None] = mapped_column(
        Text, ForeignKey("ledger_entries.id", ondelete="RESTRICT"), nullable=True
    )
    source_key: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[str] = mapped_column(Text, nullable=False)
    posted_at: Mapped[str | None] = mapped_column(Text, nullable=True)


class HonorRule(Base):
    __tablename__ = "honor_rules"

    id: Mapped[str] = mapped_column(Text, primary_key=True)
    exam_id: Mapped[str] = mapped_column(
        Text, ForeignKey("exams.id", ondelete="CASCADE"), nullable=False
    )
    role_code: Mapped[str] = mapped_column(Text, nullable=False)
    unit_type: Mapped[str] = mapped_column(Text, nullable=False, default="session")
    rate_idr: Mapped[int] = mapped_column(Integer, nullable=False)
    effective_date: Mapped[str] = mapped_column(Text, nullable=False)
    active: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    created_at: Mapped[str] = mapped_column(Text, nullable=False)


class HonorLine(Base):
    __tablename__ = "honor_lines"
    __table_args__ = (
        UniqueConstraint(
            "exam_id",
            "source_type",
            "source_id",
            "role_code",
            name="uq_honor_source_role",
        ),
    )

    id: Mapped[str] = mapped_column(Text, primary_key=True)
    exam_id: Mapped[str] = mapped_column(
        Text, ForeignKey("exams.id", ondelete="CASCADE"), nullable=False
    )
    exam_person_id: Mapped[str] = mapped_column(
        Text, ForeignKey("exam_people.id", ondelete="CASCADE"), nullable=False
    )
    source_type: Mapped[str] = mapped_column(Text, nullable=False)
    source_id: Mapped[str] = mapped_column(Text, nullable=False)
    role_code: Mapped[str] = mapped_column(Text, nullable=False)
    rate_idr: Mapped[int] = mapped_column(Integer, nullable=False)
    qty: Mapped[int] = mapped_column(Integer, nullable=False)
    amount_idr: Mapped[int] = mapped_column(Integer, nullable=False)
    state: Mapped[str] = mapped_column(Text, nullable=False, default="draft")
    ledger_entry_id: Mapped[str | None] = mapped_column(
        Text, ForeignKey("ledger_entries.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[str] = mapped_column(Text, nullable=False)
