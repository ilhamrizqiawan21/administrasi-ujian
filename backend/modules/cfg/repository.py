"""Repository layer for CFG models (scoped by institution_id, no commits)."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.modules.cfg.models import (
    AcademicYear,
    Asset,
    ExamType,
    Institution,
    Level,
    Setting,
)


class CfgRepository:
    """Data access helpers for CFG tables."""

    def list_institutions(self, session: Session) -> list[Institution]:
        stmt = (
            select(Institution)
            .where(Institution.archived_at.is_(None))
            .order_by(Institution.created_at.asc())
        )
        return list(session.scalars(stmt))

    def get_institution(
        self, session: Session, institution_id: str
    ) -> Institution | None:
        return session.get(Institution, institution_id)

    def get_asset(
        self, session: Session, institution_id: str, asset_id: str
    ) -> Asset | None:
        stmt = select(Asset).where(
            Asset.id == asset_id, Asset.institution_id == institution_id
        )
        return session.scalar(stmt)

    def list_years(self, session: Session, institution_id: str) -> list[AcademicYear]:
        stmt = (
            select(AcademicYear)
            .where(AcademicYear.institution_id == institution_id)
            .order_by(AcademicYear.label.desc())
        )
        return list(session.scalars(stmt))

    def get_year(
        self, session: Session, institution_id: str, year_id: str
    ) -> AcademicYear | None:
        stmt = select(AcademicYear).where(
            AcademicYear.id == year_id, AcademicYear.institution_id == institution_id
        )
        return session.scalar(stmt)

    def list_levels(self, session: Session, institution_id: str) -> list[Level]:
        stmt = (
            select(Level)
            .where(Level.institution_id == institution_id)
            .order_by(Level.sort_order.asc(), Level.label.asc())
        )
        return list(session.scalars(stmt))

    def get_level(
        self, session: Session, institution_id: str, level_id: str
    ) -> Level | None:
        stmt = select(Level).where(
            Level.id == level_id, Level.institution_id == institution_id
        )
        return session.scalar(stmt)

    def list_exam_types(self, session: Session, institution_id: str) -> list[ExamType]:
        stmt = (
            select(ExamType)
            .where(ExamType.institution_id == institution_id)
            .order_by(ExamType.code.asc())
        )
        return list(session.scalars(stmt))

    def get_exam_type(
        self, session: Session, institution_id: str, exam_type_id: str
    ) -> ExamType | None:
        stmt = select(ExamType).where(
            ExamType.id == exam_type_id, ExamType.institution_id == institution_id
        )
        return session.scalar(stmt)

    def get_setting(
        self, session: Session, institution_id: str, key: str
    ) -> Setting | None:
        stmt = select(Setting).where(
            Setting.institution_id == institution_id, Setting.key == key
        )
        return session.scalar(stmt)
