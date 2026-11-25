"""Repository helpers for DOC-01..DOC-09."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.modules.doc.models import DocumentNumber, DocumentRun


class DocRepository:
    """Data-access layer for document runs and number registry."""

    def list_runs(self, session: Session, exam_id: str) -> list[DocumentRun]:
        stmt = (
            select(DocumentRun)
            .where(DocumentRun.exam_id == exam_id)
            .order_by(DocumentRun.generated_at.desc())
        )
        return list(session.scalars(stmt))

    def get_run(
        self, session: Session, exam_id: str, run_id: str
    ) -> DocumentRun | None:
        stmt = select(DocumentRun).where(
            DocumentRun.exam_id == exam_id, DocumentRun.id == run_id
        )
        return session.scalar(stmt)

    def list_numbers(
        self, session: Session, institution_id: str, series: str
    ) -> list[DocumentNumber]:
        stmt = (
            select(DocumentNumber)
            .where(
                DocumentNumber.institution_id == institution_id,
                DocumentNumber.series == series,
            )
            .order_by(DocumentNumber.sequence.desc())
        )
        return list(session.scalars(stmt))
