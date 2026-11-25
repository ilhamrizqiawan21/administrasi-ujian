"""Repository helpers for FIN-01..FIN-08."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.modules.fin.models import (
    BudgetCategory,
    BudgetLine,
    BudgetVersion,
    HonorLine,
    HonorRule,
    LedgerEntry,
)


class FinRepository:
    """Data-access layer for budget, ledger, and honorarium."""

    def list_categories(self, session: Session, exam_id: str) -> list[BudgetCategory]:
        stmt = (
            select(BudgetCategory)
            .where(BudgetCategory.exam_id == exam_id)
            .order_by(BudgetCategory.label)
        )
        return list(session.scalars(stmt))

    def get_category(
        self, session: Session, exam_id: str, cat_id: str
    ) -> BudgetCategory | None:
        stmt = select(BudgetCategory).where(
            BudgetCategory.exam_id == exam_id, BudgetCategory.id == cat_id
        )
        return session.scalar(stmt)

    def list_budget_versions(
        self, session: Session, exam_id: str
    ) -> list[BudgetVersion]:
        stmt = (
            select(BudgetVersion)
            .where(BudgetVersion.exam_id == exam_id)
            .order_by(BudgetVersion.number.desc())
        )
        return list(session.scalars(stmt))

    def get_budget_version(
        self, session: Session, exam_id: str, ver_id: str
    ) -> BudgetVersion | None:
        stmt = select(BudgetVersion).where(
            BudgetVersion.exam_id == exam_id, BudgetVersion.id == ver_id
        )
        return session.scalar(stmt)

    def list_budget_lines(
        self, session: Session, budget_version_id: str
    ) -> list[BudgetLine]:
        stmt = select(BudgetLine).where(
            BudgetLine.budget_version_id == budget_version_id
        )
        return list(session.scalars(stmt))

    def list_ledger_entries(self, session: Session, exam_id: str) -> list[LedgerEntry]:
        stmt = (
            select(LedgerEntry)
            .where(LedgerEntry.exam_id == exam_id)
            .order_by(LedgerEntry.entry_date, LedgerEntry.created_at)
        )
        return list(session.scalars(stmt))

    def get_ledger_entry(
        self, session: Session, exam_id: str, entry_id: str
    ) -> LedgerEntry | None:
        stmt = select(LedgerEntry).where(
            LedgerEntry.exam_id == exam_id, LedgerEntry.id == entry_id
        )
        return session.scalar(stmt)

    def list_honor_rules(self, session: Session, exam_id: str) -> list[HonorRule]:
        stmt = (
            select(HonorRule)
            .where(HonorRule.exam_id == exam_id)
            .order_by(HonorRule.effective_date.desc())
        )
        return list(session.scalars(stmt))

    def list_honor_lines(self, session: Session, exam_id: str) -> list[HonorLine]:
        stmt = select(HonorLine).where(HonorLine.exam_id == exam_id)
        return list(session.scalars(stmt))

    def get_honor_line(
        self, session: Session, exam_id: str, line_id: str
    ) -> HonorLine | None:
        stmt = select(HonorLine).where(
            HonorLine.exam_id == exam_id, HonorLine.id == line_id
        )
        return session.scalar(stmt)
