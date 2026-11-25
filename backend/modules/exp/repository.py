"""Repository helpers for EXP-01..EXP-06."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.modules.exp.models import (
    Handover,
    PrintQuantity,
    SubmissionItem,
    SubmissionVersion,
)


class ExpRepository:
    """Data-access layer for expedition and material management."""

    def list_items(self, session: Session, exam_id: str) -> list[SubmissionItem]:
        stmt = (
            select(SubmissionItem)
            .where(SubmissionItem.exam_id == exam_id)
            .order_by(
                SubmissionItem.class_label,
                SubmissionItem.subject_label,
                SubmissionItem.type_code,
            )
        )
        return list(session.scalars(stmt))

    def get_item(
        self, session: Session, exam_id: str, item_id: str
    ) -> SubmissionItem | None:
        stmt = select(SubmissionItem).where(
            SubmissionItem.exam_id == exam_id, SubmissionItem.id == item_id
        )
        return session.scalar(stmt)

    def list_versions(self, session: Session, item_id: str) -> list[SubmissionVersion]:
        stmt = (
            select(SubmissionVersion)
            .where(SubmissionVersion.item_id == item_id)
            .order_by(SubmissionVersion.version.desc())
        )
        return list(session.scalars(stmt))

    def list_print_quantities(
        self, session: Session, exam_id: str
    ) -> list[PrintQuantity]:
        stmt = select(PrintQuantity).where(PrintQuantity.exam_id == exam_id)
        return list(session.scalars(stmt))

    def get_print_quantity(
        self, session: Session, exam_id: str, pq_id: str
    ) -> PrintQuantity | None:
        stmt = select(PrintQuantity).where(
            PrintQuantity.exam_id == exam_id, PrintQuantity.id == pq_id
        )
        return session.scalar(stmt)

    def list_handovers(self, session: Session, exam_id: str) -> list[Handover]:
        stmt = (
            select(Handover)
            .where(Handover.exam_id == exam_id)
            .order_by(Handover.handed_at.desc())
        )
        return list(session.scalars(stmt))
