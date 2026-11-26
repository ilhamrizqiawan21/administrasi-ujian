"""Repository layer for BAK-01..BAK-04."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.modules.bak.models import BackupRecord, BackupScheduleSetting


class BakRepository:
    def list_backups(self, session: Session, institution_id: str) -> list[BackupRecord]:
        return list(
            session.scalars(
                select(BackupRecord)
                .where(BackupRecord.institution_id == institution_id)
                .order_by(BackupRecord.created_at.desc())
            ).all()
        )

    def get_backup(self, session: Session, backup_id: str) -> BackupRecord | None:
        return session.get(BackupRecord, backup_id)

    def get_schedule(
        self, session: Session, institution_id: str
    ) -> BackupScheduleSetting | None:
        return session.get(BackupScheduleSetting, institution_id)
