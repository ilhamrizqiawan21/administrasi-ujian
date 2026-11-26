"""Transactional service layer for BAK-01..BAK-04."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import sqlite3
import uuid
import zipfile
from datetime import UTC, datetime
from pathlib import Path, PurePosixPath
from typing import Any

from sqlalchemy import func, select, text
from sqlalchemy.orm import Session, sessionmaker

from backend.core.db import session_scope
from backend.core.errors import ConflictError, NotFoundError, StorageError
from backend.core.paths import WorkspacePaths
from backend.modules.bak.models import BackupRecord, BackupScheduleSetting
from backend.modules.bak.repository import BakRepository
from backend.modules.bak.schemas import (
    BakCreatePayload,
    BakRecoveryPayload,
    BakRestorePayload,
    BakScheduleRunPayload,
    BakScheduleSavePayload,
    BakScopedPayload,
    BakVerifyPayload,
)
from backend.modules.cfg.models import Institution
from backend.modules.doc.models import DocumentRun
from backend.modules.doc.service import sanitize_filename
from backend.modules.evt.models import AuditEvent, Exam
from backend.modules.mst.models import Staff, Student


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()


def _new_id() -> str:
    return uuid.uuid4().hex


def _safe_zip_member(name: str) -> str:
    normalized = name.replace("\\", "/").lstrip("/")
    pure = PurePosixPath(normalized)
    if not normalized or ".." in pure.parts or pure.is_absolute():
        raise StorageError(f"Nama entri ZIP tidak aman: '{name}'.")
    return pure.as_posix()


def _resolve_under_root(root: Path, rel_or_abs: str) -> Path:
    root_resolved = root.resolve()
    candidate = Path(rel_or_abs)
    resolved = (
        candidate.resolve()
        if candidate.is_absolute()
        else (root_resolved / candidate).resolve()
    )
    try:
        resolved.relative_to(root_resolved)
    except ValueError as exc:
        raise StorageError("Akses path di luar workspace ditolak.") from exc
    return resolved


def _parse_json_dict(raw: str) -> dict[str, Any]:
    try:
        parsed = json.loads(raw)
        return parsed if isinstance(parsed, dict) else {}
    except ValueError:
        return {}


def _current_schema_revision(session: Session) -> str:
    try:
        row = session.execute(text("SELECT version_num FROM alembic_version")).scalar()
        return str(row or "")
    except Exception:
        return ""


class BakService:
    """Service for Backup, Schedule, Restore Wizard, and Crash Recovery."""

    def __init__(
        self,
        session_factory: sessionmaker[Session],
        paths: WorkspacePaths,
    ) -> None:
        self._session_factory = session_factory
        self._paths = paths
        self._repo = BakRepository()

    def _require_institution(
        self, session: Session, institution_id: str
    ) -> Institution:
        inst = session.get(Institution, institution_id)
        if inst is None:
            raise NotFoundError("Lembaga tidak ditemukan.")
        return inst

    def _append_audit(
        self,
        session: Session,
        *,
        institution_id: str,
        action: str,
        entity_type: str,
        entity_id: str,
        summary: dict[str, Any],
    ) -> None:
        session.add(
            AuditEvent(
                id=_new_id(),
                institution_id=institution_id,
                exam_id=None,
                actor="operator",
                action=action,
                entity_type=entity_type,
                entity_id=entity_id,
                at=_now_iso(),
                change_summary_json=json.dumps(summary, ensure_ascii=False),
                correlation_id="-",
            )
        )

    def _stage_sqlite_snapshot(self, session: Session, dest_sqlite: Path) -> None:
        """Use SQLite backup API to create a consistent DB snapshot."""
        dest_sqlite.parent.mkdir(parents=True, exist_ok=True)
        raw_conn = session.connection().connection.dbapi_connection
        if not isinstance(raw_conn, sqlite3.Connection):
            raise StorageError("Koneksi SQLite tidak tersedia untuk backup.")
        dst = sqlite3.connect(str(dest_sqlite))
        try:
            raw_conn.backup(dst)
        finally:
            dst.close()

    def _build_backup_zip(
        self,
        session: Session,
        *,
        institution_id: str,
        kind: str,
        output_filename: str | None = None,
    ) -> BackupRecord:
        self._paths.backups_dir.mkdir(parents=True, exist_ok=True)
        self._paths.temp_dir.mkdir(parents=True, exist_ok=True)

        stage_id = _new_id()
        stage_db = self._paths.temp_dir / f".stage_bak_{stage_id}.sqlite"
        stamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
        raw_name = output_filename or f"backup_{kind}_{stamp}_{stage_id[:6]}.zip"
        safe_name = sanitize_filename(raw_name)
        if not safe_name.lower().endswith(".zip"):
            safe_name = f"{safe_name}.zip"

        final_zip = self._paths.backups_dir / safe_name
        temp_zip = self._paths.temp_dir / f".tmp_{stage_id}_{safe_name}"

        try:
            self._stage_sqlite_snapshot(session, stage_db)
            db_bytes = stage_db.read_bytes()
            db_hash = hashlib.sha256(db_bytes).hexdigest()

            asset_entries: list[tuple[str, bytes, str]] = []
            if self._paths.assets_dir.exists():
                for asset_path in sorted(self._paths.assets_dir.rglob("*")):
                    if not asset_path.is_file():
                        continue
                    rel = asset_path.relative_to(self._paths.assets_dir).as_posix()
                    member = _safe_zip_member(f"assets/{rel}")
                    raw_asset = asset_path.read_bytes()
                    asset_hash = hashlib.sha256(raw_asset).hexdigest()
                    asset_entries.append((member, raw_asset, asset_hash))

            schema_rev = _current_schema_revision(session)
            counts = {
                "institutions": int(
                    session.scalar(select(func.count()).select_from(Institution)) or 0
                ),
                "students": int(
                    session.scalar(select(func.count()).select_from(Student)) or 0
                ),
                "staff": int(
                    session.scalar(select(func.count()).select_from(Staff)) or 0
                ),
                "exams": int(
                    session.scalar(select(func.count()).select_from(Exam)) or 0
                ),
                "documents": int(
                    session.scalar(select(func.count()).select_from(DocumentRun)) or 0
                ),
            }
            manifest = {
                "schema_version": "1.0",
                "app_version": "0.1.0",
                "schema_revision": schema_rev,
                "institution_id": institution_id,
                "kind": kind,
                "created_at": _now_iso(),
                "db": {
                    "path": "db/database.sqlite",
                    "sha256": db_hash,
                    "byte_size": len(db_bytes),
                },
                "assets": [
                    {
                        "path": member,
                        "sha256": asset_hash,
                        "byte_size": len(raw_asset),
                    }
                    for member, raw_asset, asset_hash in asset_entries
                ],
                "counts": counts,
            }
            manifest_bytes = json.dumps(manifest, indent=2, ensure_ascii=False).encode(
                "utf-8"
            )

            with zipfile.ZipFile(
                temp_zip, mode="w", compression=zipfile.ZIP_DEFLATED
            ) as zf:
                zf.writestr("manifest.json", manifest_bytes)
                zf.writestr("db/database.sqlite", db_bytes)
                for member, raw_asset, _ in asset_entries:
                    zf.writestr(member, raw_asset)

            os.replace(temp_zip, final_zip)
            zip_bytes = final_zip.read_bytes()
            zip_sha = hashlib.sha256(zip_bytes).hexdigest()
            rel_zip = final_zip.relative_to(self._paths.root).as_posix()

            rec = BackupRecord(
                id=_new_id(),
                institution_id=institution_id,
                kind=kind,
                file_path=rel_zip,
                sha256=zip_sha,
                byte_size=len(zip_bytes),
                schema_revision=schema_rev,
                status="valid",
                error_message="",
                manifest_json=manifest_bytes.decode("utf-8"),
                created_at=_now_iso(),
            )
            session.add(rec)
            return rec
        finally:
            stage_db.unlink(missing_ok=True)
            temp_zip.unlink(missing_ok=True)

    def create_backup(self, payload: BakCreatePayload) -> dict[str, Any]:
        """Create a consistent SQLite + assets atomic ZIP backup (BAK-01)."""
        with session_scope(self._session_factory) as session:
            self._require_institution(session, payload.institution_id)
            rec = self._build_backup_zip(
                session,
                institution_id=payload.institution_id,
                kind=payload.kind,
                output_filename=payload.output_filename,
            )
            self._append_audit(
                session,
                institution_id=payload.institution_id,
                action="bak.create",
                entity_type="backup_record",
                entity_id=rec.id,
                summary={"kind": rec.kind, "file_path": rec.file_path},
            )
            return self._serialize_backup(rec)

    def _serialize_backup(self, rec: BackupRecord) -> dict[str, Any]:
        exists = False
        try:
            exists = _resolve_under_root(self._paths.root, rec.file_path).exists()
        except StorageError:
            exists = False
        return {
            "id": rec.id,
            "institution_id": rec.institution_id,
            "kind": rec.kind,
            "file_path": rec.file_path,
            "sha256": rec.sha256,
            "byte_size": rec.byte_size,
            "schema_revision": rec.schema_revision,
            "status": rec.status,
            "error_message": rec.error_message,
            "exists_on_disk": exists,
            "created_at": rec.created_at,
        }

    def list_backups(self, payload: BakScopedPayload) -> dict[str, Any]:
        """List recorded backups for an institution (BAK-01)."""
        with session_scope(self._session_factory) as session:
            self._require_institution(session, payload.institution_id)
            rows = self._repo.list_backups(session, payload.institution_id)
            return {"items": [self._serialize_backup(r) for r in rows]}

    def _inspect_backup_zip(self, zip_path: Path) -> dict[str, Any]:
        """Validate ZIP entries, checksums, SQLite integrity, and counts."""
        errors: list[str] = []
        manifest: dict[str, Any] = {}
        counts: dict[str, int] = {}

        if not zip_path.exists() or not zip_path.is_file():
            return {
                "valid": False,
                "errors": ["File backup ZIP tidak ditemukan."],
                "manifest": {},
                "counts": {},
            }

        stage_db = self._paths.temp_dir / f".verify_{_new_id()}.sqlite"
        self._paths.temp_dir.mkdir(parents=True, exist_ok=True)

        try:
            with zipfile.ZipFile(zip_path, mode="r") as zf:
                names = zf.namelist()
                for info in zf.infolist():
                    try:
                        _safe_zip_member(info.filename)
                    except StorageError as exc:
                        errors.append(str(exc))
                    if (info.external_attr >> 16) & 0o170000 == 0o120000:
                        errors.append(f"Symlink di dalam ZIP ditolak: {info.filename}")

                if "manifest.json" not in names:
                    errors.append("manifest.json tidak ditemukan di dalam ZIP.")
                else:
                    manifest = _parse_json_dict(
                        zf.read("manifest.json").decode("utf-8")
                    )
                    db_meta = manifest.get("db", {})
                    if not isinstance(db_meta, dict):
                        errors.append("Metadata db pada manifest tidak valid.")
                    else:
                        db_member = str(db_meta.get("path", "db/database.sqlite"))
                        expected_db_hash = str(db_meta.get("sha256", ""))
                        if db_member not in names:
                            errors.append(f"Database hilang dari ZIP: {db_member}")
                        else:
                            db_bytes = zf.read(db_member)
                            actual_db_hash = hashlib.sha256(db_bytes).hexdigest()
                            if actual_db_hash != expected_db_hash:
                                errors.append("Checksum database tidak cocok.")
                            else:
                                stage_db.write_bytes(db_bytes)
                                conn = sqlite3.connect(str(stage_db))
                                try:
                                    qc = conn.execute("PRAGMA quick_check").fetchone()
                                    fkc = conn.execute(
                                        "PRAGMA foreign_key_check"
                                    ).fetchall()
                                    if not qc or qc[0] != "ok":
                                        errors.append(
                                            "SQLite quick_check gagal pada backup."
                                        )
                                    if fkc:
                                        errors.append(
                                            "Deteksi pelanggaran foreign key "
                                            "pada backup."
                                        )
                                    for tbl in (
                                        "institutions",
                                        "students",
                                        "staff",
                                        "exams",
                                        "document_runs",
                                    ):
                                        try:
                                            cnt = conn.execute(
                                                f"SELECT COUNT(*) FROM {tbl}"
                                            ).fetchone()
                                            counts[tbl] = int(cnt[0]) if cnt else 0
                                        except sqlite3.Error:
                                            counts[tbl] = 0
                                finally:
                                    conn.close()

                    assets_meta = manifest.get("assets", [])
                    if isinstance(assets_meta, list):
                        for item in assets_meta:
                            if not isinstance(item, dict):
                                continue
                            rel = str(item.get("path", ""))
                            expected_hash = str(item.get("sha256", ""))
                            if rel not in names:
                                errors.append(f"Aset hilang dari ZIP: {rel}")
                                continue
                            actual_hash = hashlib.sha256(zf.read(rel)).hexdigest()
                            if actual_hash != expected_hash:
                                errors.append(f"Checksum aset tidak cocok: {rel}")
        except (zipfile.BadZipFile, OSError, UnicodeDecodeError) as exc:
            errors.append(f"File backup rusak atau bukan ZIP valid: {exc}")
        finally:
            stage_db.unlink(missing_ok=True)

        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "manifest": manifest,
            "counts": counts,
        }

    def verify_backup(self, payload: BakVerifyPayload) -> dict[str, Any]:
        """Verify backup ZIP integrity and checksums (BAK-01)."""
        with session_scope(self._session_factory) as session:
            self._require_institution(session, payload.institution_id)
            target_path_str = payload.file_path
            if payload.backup_id:
                rec = self._repo.get_backup(session, payload.backup_id)
                if rec is None or rec.institution_id != payload.institution_id:
                    raise NotFoundError("Catatan backup tidak ditemukan.")
                target_path_str = rec.file_path
            if not target_path_str:
                raise NotFoundError("Path atau ID backup wajib diisi.")
            zip_path = _resolve_under_root(self._paths.root, target_path_str)
            result = self._inspect_backup_zip(zip_path)
            return {
                "file_path": target_path_str,
                "valid": result["valid"],
                "errors": result["errors"],
                "manifest": result["manifest"],
                "counts": result["counts"],
            }

    def get_schedule(self, payload: BakScopedPayload) -> dict[str, Any]:
        """Get backup schedule & retention settings (BAK-02)."""
        with session_scope(self._session_factory) as session:
            self._require_institution(session, payload.institution_id)
            setting = self._repo.get_schedule(session, payload.institution_id)
            if setting is None:
                return {
                    "institution_id": payload.institution_id,
                    "auto_on_startup": True,
                    "auto_on_close": True,
                    "retention_count": 7,
                    "last_run_at": None,
                    "last_status": "idle",
                    "last_error": "",
                }
            return {
                "institution_id": setting.institution_id,
                "auto_on_startup": bool(setting.auto_on_startup),
                "auto_on_close": bool(setting.auto_on_close),
                "retention_count": setting.retention_count,
                "last_run_at": setting.last_run_at,
                "last_status": setting.last_status,
                "last_error": setting.last_error,
            }

    def save_schedule(self, payload: BakScheduleSavePayload) -> dict[str, Any]:
        """Save backup schedule & retention settings (BAK-02)."""
        now = _now_iso()
        with session_scope(self._session_factory) as session:
            self._require_institution(session, payload.institution_id)
            setting = self._repo.get_schedule(session, payload.institution_id)
            if setting is None:
                setting = BackupScheduleSetting(
                    institution_id=payload.institution_id,
                    auto_on_startup=1 if payload.auto_on_startup else 0,
                    auto_on_close=1 if payload.auto_on_close else 0,
                    retention_count=payload.retention_count,
                    last_run_at=None,
                    last_status="idle",
                    last_error="",
                    updated_at=now,
                )
                session.add(setting)
            else:
                setting.auto_on_startup = 1 if payload.auto_on_startup else 0
                setting.auto_on_close = 1 if payload.auto_on_close else 0
                setting.retention_count = payload.retention_count
                setting.updated_at = now
            session.flush()
            return {
                "institution_id": setting.institution_id,
                "auto_on_startup": bool(setting.auto_on_startup),
                "auto_on_close": bool(setting.auto_on_close),
                "retention_count": setting.retention_count,
                "last_run_at": setting.last_run_at,
                "last_status": setting.last_status,
                "last_error": setting.last_error,
            }

    def run_scheduled_backup(self, payload: BakScheduleRunPayload) -> dict[str, Any]:
        """Execute periodic backup without deleting last good backup (BAK-02)."""
        now = _now_iso()
        with session_scope(self._session_factory) as session:
            self._require_institution(session, payload.institution_id)
            setting = self._repo.get_schedule(session, payload.institution_id)
            if setting is None:
                setting = BackupScheduleSetting(
                    institution_id=payload.institution_id,
                    auto_on_startup=1,
                    auto_on_close=1,
                    retention_count=7,
                    last_run_at=None,
                    last_status="idle",
                    last_error="",
                    updated_at=now,
                )
                session.add(setting)
                session.flush()

            if payload.simulate_failure:
                setting.last_run_at = now
                setting.last_status = "failed"
                setting.last_error = "Simulasi kegagalan backup terjadwal."
                setting.updated_at = now
                return {
                    "executed": False,
                    "status": "failed",
                    "error": setting.last_error,
                    "pruned_count": 0,
                }

            kind = (
                "scheduled_startup"
                if payload.trigger == "startup"
                else "scheduled_close"
            )
            rec = self._build_backup_zip(
                session, institution_id=payload.institution_id, kind=kind
            )
            setting.last_run_at = now
            setting.last_status = "ok"
            setting.last_error = ""
            setting.updated_at = now

            all_valid = [
                r
                for r in self._repo.list_backups(session, payload.institution_id)
                if r.status == "valid"
            ]
            keep_n = max(1, setting.retention_count)
            pruned_count = 0
            for old in all_valid[keep_n:]:
                try:
                    p = _resolve_under_root(self._paths.root, old.file_path)
                    p.unlink(missing_ok=True)
                except StorageError:
                    pass
                session.delete(old)
                pruned_count += 1

            return {
                "executed": True,
                "status": "ok",
                "backup": self._serialize_backup(rec),
                "pruned_count": pruned_count,
            }

    def preview_restore(self, payload: BakRestorePayload) -> dict[str, Any]:
        """Validate backup ZIP and preview restore counts (BAK-03)."""
        with session_scope(self._session_factory) as session:
            self._require_institution(session, payload.institution_id)
            zip_path = _resolve_under_root(self._paths.root, payload.file_path)
            inspected = self._inspect_backup_zip(zip_path)
            return {
                "file_path": payload.file_path,
                "can_restore": inspected["valid"],
                "errors": inspected["errors"],
                "manifest": inspected["manifest"],
                "counts": inspected["counts"],
            }

    def apply_restore(self, payload: BakRestorePayload) -> dict[str, Any]:
        """Backup current state, stage & validate, then swap DB & assets (BAK-03)."""
        zip_path = _resolve_under_root(self._paths.root, payload.file_path)
        inspected = self._inspect_backup_zip(zip_path)
        if not inspected["valid"]:
            raise ConflictError(
                "Backup tidak valid atau rusak; database saat ini tidak diubah: "
                + "; ".join(inspected["errors"])
            )

        stage_dir = self._paths.temp_dir / f".restore_stage_{_new_id()}"
        stage_db = stage_dir / "database.sqlite"
        stage_assets = stage_dir / "assets"

        with session_scope(self._session_factory) as session:
            self._require_institution(session, payload.institution_id)
            pre_bak = self._build_backup_zip(
                session, institution_id=payload.institution_id, kind="pre_restore"
            )

            try:
                stage_dir.mkdir(parents=True, exist_ok=True)
                with zipfile.ZipFile(zip_path, mode="r") as zf:
                    manifest = _parse_json_dict(
                        zf.read("manifest.json").decode("utf-8")
                    )
                    db_member = str(
                        manifest.get("db", {}).get("path", "db/database.sqlite")
                    )
                    stage_db.write_bytes(zf.read(db_member))
                    for info in zf.infolist():
                        safe_member = _safe_zip_member(info.filename)
                        if safe_member.startswith("assets/") and not info.is_dir():
                            rel_asset = safe_member[len("assets/") :]
                            target_asset = _resolve_under_root(stage_assets, rel_asset)
                            target_asset.parent.mkdir(parents=True, exist_ok=True)
                            target_asset.write_bytes(zf.read(info.filename))

                raw_conn = session.connection().connection.dbapi_connection
                if not isinstance(raw_conn, sqlite3.Connection):
                    raise StorageError("Koneksi SQLite tidak tersedia untuk restore.")
                src_conn = sqlite3.connect(str(stage_db))
                try:
                    src_conn.backup(raw_conn)
                finally:
                    src_conn.close()

                qc = session.execute(text("PRAGMA quick_check")).fetchone()
                fkc = session.execute(text("PRAGMA foreign_key_check")).fetchall()
                if not qc or qc[0] != "ok" or fkc:
                    raise ConflictError(
                        "Verifikasi integritas pasca-restore gagal; "
                        "transaksi dibatalkan."
                    )

                if stage_assets.exists():
                    self._paths.assets_dir.mkdir(parents=True, exist_ok=True)
                    for asset_file in stage_assets.rglob("*"):
                        if not asset_file.is_file():
                            continue
                        rel = asset_file.relative_to(stage_assets)
                        dest = self._paths.assets_dir / rel
                        dest.parent.mkdir(parents=True, exist_ok=True)
                        shutil.copy2(asset_file, dest)

                return {
                    "restored": True,
                    "source_file_path": payload.file_path,
                    "pre_restore_backup": self._serialize_backup(pre_bak),
                    "counts": inspected["counts"],
                }
            finally:
                shutil.rmtree(stage_dir, ignore_errors=True)

    def diagnose_recovery(self, payload: BakScopedPayload) -> dict[str, Any]:
        """Inspect DB integrity, interrupted jobs, and temp artifacts (BAK-04)."""
        with session_scope(self._session_factory) as session:
            self._require_institution(session, payload.institution_id)
            qc = session.execute(text("PRAGMA quick_check")).fetchone()
            fkc = session.execute(text("PRAGMA foreign_key_check")).fetchall()
            integrity_ok = bool(qc and qc[0] == "ok")
            fk_ok = len(fkc) == 0

            stale_jobs = session.execute(
                text(
                    "SELECT id, job_type, status, updated_at FROM jobs "
                    "WHERE status IN ('queued', 'running')"
                )
            ).fetchall()
            interrupted_jobs = [
                {
                    "id": str(row[0]),
                    "job_type": str(row[1]),
                    "status": str(row[2]),
                    "updated_at": str(row[3]),
                }
                for row in stale_jobs
            ]

            temp_files: list[str] = []
            for base_dir in (self._paths.temp_dir, self._paths.exports_dir):
                if base_dir.exists():
                    for p in base_dir.rglob(".tmp_*"):
                        temp_files.append(p.relative_to(self._paths.root).as_posix())

            missing_docs: list[str] = []
            for doc in session.scalars(
                select(DocumentRun).where(
                    DocumentRun.institution_id == payload.institution_id
                )
            ).all():
                try:
                    resolved = _resolve_under_root(self._paths.root, doc.output_path)
                    if not resolved.exists():
                        missing_docs.append(doc.output_path)
                except StorageError:
                    missing_docs.append(doc.output_path)

            guidance: list[str] = []
            if interrupted_jobs:
                guidance.append(
                    f"Ditemukan {len(interrupted_jobs)} job terhenti; "
                    "jalankan pembersihan untuk menandai status interrupted."
                )
            if temp_files:
                guidance.append(
                    f"Ditemukan {len(temp_files)} file sementara (.tmp_*); "
                    "bersihkan agar tidak menyisakan artefak parsial."
                )
            if not integrity_ok or not fk_ok:
                guidance.append(
                    "Integritas database bermasalah; gunakan Wizard Restore "
                    "dari backup valid terakhir."
                )
            if not guidance:
                guidance.append(
                    "Sistem sehat: tidak ada job terhenti, file sementara, "
                    "atau pelanggaran integritas."
                )

            return {
                "healthy": integrity_ok
                and fk_ok
                and len(interrupted_jobs) == 0
                and len(temp_files) == 0,
                "integrity_ok": integrity_ok,
                "foreign_keys_ok": fk_ok,
                "interrupted_jobs": interrupted_jobs,
                "temp_files": temp_files,
                "missing_document_outputs": missing_docs,
                "guidance": guidance,
            }

    def repair_recovery(self, payload: BakRecoveryPayload) -> dict[str, Any]:
        """Clean interrupted jobs & temp files safely (BAK-04)."""
        now = _now_iso()
        cleaned_jobs = 0
        cleaned_files = 0

        with session_scope(self._session_factory) as session:
            self._require_institution(session, payload.institution_id)
            if payload.mark_interrupted_jobs:
                res = session.execute(
                    text(
                        "UPDATE jobs SET status = 'interrupted', "
                        "error_code = 'INTERRUPTED_RECOVERY', updated_at = :now "
                        "WHERE status IN ('queued', 'running')"
                    ),
                    {"now": now},
                )
                cleaned_jobs = int(getattr(res, "rowcount", 0) or 0)

            if payload.clean_temp_files:
                for base_dir in (self._paths.temp_dir, self._paths.exports_dir):
                    if base_dir.exists():
                        for p in list(base_dir.rglob(".tmp_*")):
                            if p.is_file():
                                p.unlink(missing_ok=True)
                                cleaned_files += 1
                            elif p.is_dir():
                                shutil.rmtree(p, ignore_errors=True)
                                cleaned_files += 1

            self._append_audit(
                session,
                institution_id=payload.institution_id,
                action="bak.recovery.repair",
                entity_type="workspace",
                entity_id=payload.institution_id,
                summary={
                    "cleaned_jobs": cleaned_jobs,
                    "cleaned_temp_files": cleaned_files,
                },
            )

        diag = self.diagnose_recovery(
            BakScopedPayload(institution_id=payload.institution_id)
        )
        return {
            "cleaned_jobs": cleaned_jobs,
            "cleaned_temp_files": cleaned_files,
            "diagnostics": diag,
        }
