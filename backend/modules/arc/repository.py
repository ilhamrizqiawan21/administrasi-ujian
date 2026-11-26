"""Repository layer for ARC-01..ARC-04."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.modules.arc.models import ArchivePackage, RetentionBackup
from backend.modules.evt.models import Exam


class ArcRepository:
    def list_exams(
        self,
        session: Session,
        institution_id: str,
        *,
        year_id: str | None = None,
        exam_type_id: str | None = None,
        state: str | None = None,
    ) -> list[Exam]:
        stmt = select(Exam).where(Exam.institution_id == institution_id)
        if year_id:
            stmt = stmt.where(Exam.year_id == year_id)
        if exam_type_id:
            stmt = stmt.where(Exam.exam_type_id == exam_type_id)
        if state:
            stmt = stmt.where(Exam.state == state)
        stmt = stmt.order_by(Exam.starts_on.desc(), Exam.created_at.desc())
        return list(session.scalars(stmt).all())

    def list_packages(self, session: Session, exam_id: str) -> list[ArchivePackage]:
        return list(
            session.scalars(
                select(ArchivePackage)
                .where(ArchivePackage.exam_id == exam_id)
                .order_by(ArchivePackage.created_at.desc())
            ).all()
        )

    def get_package(self, session: Session, package_id: str) -> ArchivePackage | None:
        return session.get(ArchivePackage, package_id)

    def list_backups(
        self, session: Session, institution_id: str
    ) -> list[RetentionBackup]:
        return list(
            session.scalars(
                select(RetentionBackup)
                .where(RetentionBackup.institution_id == institution_id)
                .order_by(RetentionBackup.created_at.desc())
            ).all()
        )
