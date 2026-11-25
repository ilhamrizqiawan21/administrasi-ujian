"""Repository helpers for TPL-01..TPL-06."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.modules.tpl.models import Letterhead, TemplateRecord, ThemeProfile


class TplRepository:
    """Data-access layer for templates, letterheads, and theme profiles."""

    def list_letterheads(
        self, session: Session, institution_id: str
    ) -> list[Letterhead]:
        stmt = (
            select(Letterhead)
            .where(Letterhead.institution_id == institution_id)
            .order_by(Letterhead.version.desc())
        )
        return list(session.scalars(stmt))

    def list_templates(
        self, session: Session, institution_id: str
    ) -> list[TemplateRecord]:
        stmt = (
            select(TemplateRecord)
            .where(
                (TemplateRecord.institution_id == institution_id)
                | (TemplateRecord.institution_id.is_(None))
            )
            .order_by(TemplateRecord.doc_type, TemplateRecord.version.desc())
        )
        return list(session.scalars(stmt))

    def list_theme_profiles(
        self, session: Session, institution_id: str
    ) -> list[ThemeProfile]:
        stmt = (
            select(ThemeProfile)
            .where(ThemeProfile.institution_id == institution_id)
            .order_by(ThemeProfile.version.desc())
        )
        return list(session.scalars(stmt))
