"""Repository layer for LPJ-01..LPJ-05."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.modules.lpj.models import LpjAttachment, LpjEvaluation, LpjVersion


class LpjRepository:
    def list_versions(self, session: Session, exam_id: str) -> list[LpjVersion]:
        return list(
            session.scalars(
                select(LpjVersion)
                .where(LpjVersion.exam_id == exam_id)
                .order_by(LpjVersion.version.desc())
            ).all()
        )

    def get_version(self, session: Session, version_id: str) -> LpjVersion | None:
        return session.get(LpjVersion, version_id)

    def max_version_number(self, session: Session, exam_id: str) -> int:
        rows = self.list_versions(session, exam_id)
        return max((r.version for r in rows), default=0)

    def list_evaluations(
        self, session: Session, lpj_version_id: str
    ) -> list[LpjEvaluation]:
        return list(
            session.scalars(
                select(LpjEvaluation)
                .where(LpjEvaluation.lpj_version_id == lpj_version_id)
                .order_by(
                    LpjEvaluation.sort_order.asc(), LpjEvaluation.created_at.asc()
                )
            ).all()
        )

    def get_evaluation(self, session: Session, eval_id: str) -> LpjEvaluation | None:
        return session.get(LpjEvaluation, eval_id)

    def list_attachments(
        self, session: Session, lpj_version_id: str
    ) -> list[LpjAttachment]:
        return list(
            session.scalars(
                select(LpjAttachment)
                .where(LpjAttachment.lpj_version_id == lpj_version_id)
                .order_by(
                    LpjAttachment.sort_order.asc(), LpjAttachment.created_at.asc()
                )
            ).all()
        )

    def get_attachment(self, session: Session, att_id: str) -> LpjAttachment | None:
        return session.get(LpjAttachment, att_id)
