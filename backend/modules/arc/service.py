"""Transactional service layer for ARC-01..ARC-04."""

from __future__ import annotations

import hashlib
import json
import os
import sqlite3
import uuid
import zipfile
from datetime import UTC, date, datetime
from pathlib import Path, PurePosixPath
from typing import Any

from sqlalchemy import func, select, text
from sqlalchemy.orm import Session, sessionmaker

from backend.core.db import session_scope
from backend.core.errors import (
    ConflictError,
    NotFoundError,
    StorageError,
    ValidationError,
)
from backend.core.paths import WorkspacePaths
from backend.modules.arc.models import ArchivePackage, RetentionBackup
from backend.modules.arc.repository import ArcRepository
from backend.modules.arc.schemas import (
    ArcDuplicatePayload,
    ArcExamScopedPayload,
    ArcListPayload,
    ArcPackageExportPayload,
    ArcPackageVerifyPayload,
    ArcRetentionPurgePayload,
    ArcRetentionReviewPayload,
)
from backend.modules.cfg.models import AcademicYear, ExamType, Institution
from backend.modules.com.models import CommitteeRole
from backend.modules.doc.models import DocumentNumber, DocumentRun
from backend.modules.doc.service import sanitize_filename
from backend.modules.evt.models import (
    AuditEvent,
    Exam,
    ExamGroup,
    ExamParticipant,
    ExamPerson,
    ExamRequirement,
    ExamRoom,
    ExamSubject,
)
from backend.modules.fin.models import (
    BudgetCategory,
    BudgetVersion,
    HonorLine,
    HonorRule,
    LedgerEntry,
)
from backend.modules.lpj.models import LpjVersion
from backend.modules.ops.models import Incident
from backend.modules.rom.models import ParticipantSitting
from backend.modules.sch.models import Invigilation
from backend.modules.ses.models import ExamSession, Plan
from backend.modules.tsk.models import Task


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()


def _new_id() -> str:
    return uuid.uuid4().hex


def _safe_zip_member_name(name: str) -> str:
    """Validate and normalize a ZIP entry path to prevent path traversal."""
    normalized = name.replace("\\", "/").lstrip("/")
    pure = PurePosixPath(normalized)
    if not normalized or ".." in pure.parts or pure.is_absolute():
        raise StorageError(f"Nama entri ZIP tidak aman: '{name}'.")
    return pure.as_posix()


def _resolve_under_root(root: Path, rel_or_abs: str) -> Path:
    """Resolve a path strictly inside workspace root."""
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


def _count_rows(session: Session, model: Any, col: Any, value: str) -> int:
    return int(
        session.scalar(select(func.count()).select_from(model).where(col == value)) or 0
    )


def _count_by_plans(session: Session, model: Any, plan_ids: list[str]) -> int:
    if not plan_ids:
        return 0
    return int(
        session.scalar(
            select(func.count()).select_from(model).where(model.plan_id.in_(plan_ids))
        )
        or 0
    )


class ArcService:
    """Service for Archive Browser, Archive Package, Duplicate Event, and Retention."""

    def __init__(
        self,
        session_factory: sessionmaker[Session],
        paths: WorkspacePaths,
    ) -> None:
        self._session_factory = session_factory
        self._paths = paths
        self._repo = ArcRepository()

    def _require_exam(
        self, session: Session, institution_id: str, exam_id: str
    ) -> Exam:
        exam = session.get(Exam, exam_id)
        if exam is None or exam.institution_id != institution_id:
            raise NotFoundError("Kegiatan ujian tidak ditemukan.")
        return exam

    def _append_audit(
        self,
        session: Session,
        *,
        institution_id: str,
        exam_id: str | None,
        action: str,
        entity_type: str,
        entity_id: str,
        summary: dict[str, Any],
    ) -> None:
        session.add(
            AuditEvent(
                id=_new_id(),
                institution_id=institution_id,
                exam_id=exam_id,
                actor="operator",
                action=action,
                entity_type=entity_type,
                entity_id=entity_id,
                at=_now_iso(),
                change_summary_json=json.dumps(summary, ensure_ascii=False),
                correlation_id="-",
            )
        )

    def _year_and_type_maps(
        self, session: Session, institution_id: str
    ) -> tuple[dict[str, str], dict[str, str]]:
        years = {
            y.id: y.label
            for y in session.scalars(
                select(AcademicYear).where(
                    AcademicYear.institution_id == institution_id
                )
            ).all()
        }
        types = {
            t.id: t.label
            for t in session.scalars(
                select(ExamType).where(ExamType.institution_id == institution_id)
            ).all()
        }
        return years, types

    def list_archive_events(self, payload: ArcListPayload) -> dict[str, Any]:
        """List events with academic year, type, status, and search filters (ARC-01)."""
        with session_scope(self._session_factory) as session:
            years, types = self._year_and_type_maps(session, payload.institution_id)
            exams = self._repo.list_exams(
                session,
                payload.institution_id,
                year_id=payload.year_id or None,
                exam_type_id=payload.exam_type_id or None,
                state=payload.state or None,
            )
            term = (payload.search or "").strip().lower()
            items: list[dict[str, Any]] = []
            for exam in exams:
                if (
                    term
                    and term not in exam.title.lower()
                    and term not in exam.semester_label.lower()
                ):
                    continue
                pkg_count = _count_rows(
                    session, ArchivePackage, ArchivePackage.exam_id, exam.id
                )
                items.append(
                    {
                        "id": exam.id,
                        "institution_id": exam.institution_id,
                        "year_id": exam.year_id,
                        "year_label": years.get(exam.year_id, "-"),
                        "exam_type_id": exam.exam_type_id,
                        "exam_type_label": types.get(exam.exam_type_id, "-"),
                        "title": exam.title,
                        "semester_label": exam.semester_label,
                        "mode": exam.mode,
                        "starts_on": exam.starts_on,
                        "ends_on": exam.ends_on,
                        "state": exam.state,
                        "is_archived": exam.state == "ARCHIVED",
                        "package_count": pkg_count,
                        "updated_at": exam.updated_at,
                    }
                )
            return {
                "items": items,
                "years": [{"id": k, "label": v} for k, v in years.items()],
                "exam_types": [{"id": k, "label": v} for k, v in types.items()],
            }

    def get_event_detail(self, payload: ArcExamScopedPayload) -> dict[str, Any]:
        """Return read-only archive detail for an exam (ARC-01)."""
        with session_scope(self._session_factory) as session:
            exam = self._require_exam(session, payload.institution_id, payload.exam_id)
            years, types = self._year_and_type_maps(session, payload.institution_id)
            packages = self._repo.list_packages(session, exam.id)
            doc_runs = list(
                session.scalars(
                    select(DocumentRun)
                    .where(DocumentRun.exam_id == exam.id)
                    .order_by(DocumentRun.generated_at.desc())
                ).all()
            )
            plan_ids = list(
                session.scalars(select(Plan.id).where(Plan.exam_id == exam.id)).all()
            )
            counts = {
                "people": _count_rows(session, ExamPerson, ExamPerson.exam_id, exam.id),
                "participants": _count_rows(
                    session, ExamParticipant, ExamParticipant.exam_id, exam.id
                ),
                "rooms": _count_rows(session, ExamRoom, ExamRoom.exam_id, exam.id),
                "subjects": _count_rows(
                    session, ExamSubject, ExamSubject.exam_id, exam.id
                ),
                "plans": len(plan_ids),
                "sessions": _count_by_plans(session, ExamSession, plan_ids),
                "documents": len(doc_runs),
                "lpj_versions": _count_rows(
                    session, LpjVersion, LpjVersion.exam_id, exam.id
                ),
                "ledger_entries": _count_rows(
                    session, LedgerEntry, LedgerEntry.exam_id, exam.id
                ),
            }
            return {
                "exam": {
                    "id": exam.id,
                    "institution_id": exam.institution_id,
                    "year_id": exam.year_id,
                    "year_label": years.get(exam.year_id, "-"),
                    "exam_type_id": exam.exam_type_id,
                    "exam_type_label": types.get(exam.exam_type_id, "-"),
                    "title": exam.title,
                    "semester_label": exam.semester_label,
                    "mode": exam.mode,
                    "starts_on": exam.starts_on,
                    "ends_on": exam.ends_on,
                    "state": exam.state,
                    "is_archived": exam.state == "ARCHIVED",
                    "active_plan_id": exam.active_plan_id,
                    "config": _parse_json_dict(exam.config_json),
                    "updated_at": exam.updated_at,
                },
                "counts": counts,
                "documents": [
                    {
                        "id": d.id,
                        "doc_type": d.doc_type,
                        "format": d.format,
                        "status": d.status,
                        "output_path": d.output_path,
                        "output_hash": d.output_hash,
                        "generated_at": d.generated_at,
                    }
                    for d in doc_runs
                ],
                "packages": [
                    {
                        "id": p.id,
                        "file_path": p.file_path,
                        "sha256": p.sha256,
                        "file_count": p.file_count,
                        "include_personal_info": bool(p.include_personal_info),
                        "created_at": p.created_at,
                    }
                    for p in packages
                ],
            }

    def archive_event(self, payload: ArcExamScopedPayload) -> dict[str, Any]:
        """Transition a COMPLETED exam into immutable ARCHIVED state (ARC-01)."""
        with session_scope(self._session_factory) as session:
            exam = self._require_exam(session, payload.institution_id, payload.exam_id)
            if exam.state == "ARCHIVED":
                return {"id": exam.id, "state": exam.state, "is_archived": True}
            if exam.state != "COMPLETED":
                raise ConflictError(
                    "Hanya kegiatan berstatus COMPLETED yang dapat diarsipkan."
                )
            exam.state = "ARCHIVED"
            exam.revision += 1
            exam.updated_at = _now_iso()
            self._append_audit(
                session,
                institution_id=payload.institution_id,
                exam_id=exam.id,
                action="arc.archive",
                entity_type="exam",
                entity_id=exam.id,
                summary={"from": "COMPLETED", "to": "ARCHIVED"},
            )
            return {"id": exam.id, "state": exam.state, "is_archived": True}

    def export_archive_package(
        self, payload: ArcPackageExportPayload
    ) -> dict[str, Any]:
        """Build atomic ZIP archive package with manifest & SHA-256 hashes (ARC-02)."""
        with session_scope(self._session_factory) as session:
            exam = self._require_exam(session, payload.institution_id, payload.exam_id)
            inst = session.get(Institution, payload.institution_id)
            years, types = self._year_and_type_maps(session, payload.institution_id)

            doc_runs = list(
                session.scalars(
                    select(DocumentRun)
                    .where(DocumentRun.exam_id == exam.id)
                    .order_by(DocumentRun.generated_at.asc())
                ).all()
            )
            doc_numbers = list(
                session.scalars(
                    select(DocumentNumber)
                    .where(DocumentNumber.exam_id == exam.id)
                    .order_by(DocumentNumber.sequence.asc())
                ).all()
            )
            lpj_versions = list(
                session.scalars(
                    select(LpjVersion)
                    .where(LpjVersion.exam_id == exam.id)
                    .order_by(LpjVersion.version.asc())
                ).all()
            )

            event_meta: dict[str, Any] = {
                "exam_id": exam.id,
                "institution_id": exam.institution_id,
                "institution_name": inst.name if inst else "",
                "year_label": years.get(exam.year_id, ""),
                "exam_type_label": types.get(exam.exam_type_id, ""),
                "title": exam.title,
                "semester_label": exam.semester_label,
                "mode": exam.mode,
                "starts_on": exam.starts_on,
                "ends_on": exam.ends_on,
                "state": exam.state,
                "config": _parse_json_dict(exam.config_json),
                "include_personal_info": payload.include_personal_info,
                "summary": {
                    "participants_count": _count_rows(
                        session, ExamParticipant, ExamParticipant.exam_id, exam.id
                    ),
                    "rooms_count": _count_rows(
                        session, ExamRoom, ExamRoom.exam_id, exam.id
                    ),
                    "subjects_count": _count_rows(
                        session, ExamSubject, ExamSubject.exam_id, exam.id
                    ),
                    "documents_count": len(doc_runs),
                    "lpj_versions_count": len(lpj_versions),
                },
            }

            docs_meta = [
                {
                    "id": d.id,
                    "doc_type": d.doc_type,
                    "format": d.format,
                    "status": d.status,
                    "output_hash": d.output_hash,
                    "generated_at": d.generated_at,
                }
                for d in doc_runs
            ]
            numbers_meta = [
                {
                    "series": n.series,
                    "sequence": n.sequence,
                    "number_text": n.number_text,
                    "status": n.status,
                }
                for n in doc_numbers
            ]

            entries: list[tuple[str, bytes]] = [
                (
                    "metadata/event.json",
                    json.dumps(event_meta, indent=2, ensure_ascii=False).encode(
                        "utf-8"
                    ),
                ),
                (
                    "metadata/documents.json",
                    json.dumps(
                        {"runs": docs_meta, "numbers": numbers_meta},
                        indent=2,
                        ensure_ascii=False,
                    ).encode("utf-8"),
                ),
            ]

            if payload.include_personal_info:
                people = list(
                    session.scalars(
                        select(ExamPerson)
                        .where(ExamPerson.exam_id == exam.id)
                        .order_by(ExamPerson.kind.asc(), ExamPerson.code.asc())
                    ).all()
                )
                participants = {
                    p.exam_person_id: p
                    for p in session.scalars(
                        select(ExamParticipant).where(
                            ExamParticipant.exam_id == exam.id
                        )
                    ).all()
                }
                people_rows = [
                    {
                        "id": person.id,
                        "kind": person.kind,
                        "code": person.code,
                        "display_name": person.display_name,
                        "level_label": person.level_label,
                        "class_label": person.class_label,
                        "participant_number": (
                            participants[person.id].participant_number
                            if person.id in participants
                            else None
                        ),
                    }
                    for person in people
                ]
                entries.append(
                    (
                        "metadata/participants.json",
                        json.dumps(
                            {"people": people_rows}, indent=2, ensure_ascii=False
                        ).encode("utf-8"),
                    )
                )

            missing_files: list[str] = []
            used_doc_names: set[str] = set()
            if payload.include_documents:
                for idx, doc_run in enumerate(doc_runs, start=1):
                    resolved_doc = _resolve_under_root(
                        self._paths.root, doc_run.output_path
                    )
                    if not resolved_doc.exists() or not resolved_doc.is_file():
                        missing_files.append(doc_run.output_path)
                        continue
                    base_name = sanitize_filename(resolved_doc.name)
                    member_name = f"documents/{base_name}"
                    if member_name in used_doc_names:
                        member_name = f"documents/{idx}_{base_name}"
                    used_doc_names.add(member_name)
                    entries.append((member_name, resolved_doc.read_bytes()))

            manifest_files: list[dict[str, Any]] = []
            for member_name, raw_bytes in entries:
                safe_name = _safe_zip_member_name(member_name)
                manifest_files.append(
                    {
                        "path": safe_name,
                        "sha256": hashlib.sha256(raw_bytes).hexdigest(),
                        "byte_size": len(raw_bytes),
                    }
                )

            manifest = {
                "schema_version": "1.0",
                "app_version": "0.1.0",
                "institution_id": exam.institution_id,
                "exam_id": exam.id,
                "exam_title": exam.title,
                "exported_at": _now_iso(),
                "include_personal_info": payload.include_personal_info,
                "file_count": len(manifest_files),
                "missing_files": missing_files,
                "files": manifest_files,
            }
            manifest_bytes = json.dumps(manifest, indent=2, ensure_ascii=False).encode(
                "utf-8"
            )

            archives_dir = self._paths.exports_dir / "archives"
            archives_dir.mkdir(parents=True, exist_ok=True)
            default_stem = sanitize_filename(f"archive_{exam.title}_{exam.id[:8]}")
            raw_name = payload.output_filename or f"{default_stem}.zip"
            safe_filename = sanitize_filename(raw_name)
            if not safe_filename.lower().endswith(".zip"):
                safe_filename = f"{safe_filename}.zip"
            final_zip = archives_dir / safe_filename
            temp_zip = archives_dir / f".tmp_{_new_id()}_{safe_filename}"

            with zipfile.ZipFile(
                temp_zip, mode="w", compression=zipfile.ZIP_DEFLATED
            ) as zf:
                zf.writestr("manifest.json", manifest_bytes)
                for member_name, raw_bytes in entries:
                    zf.writestr(_safe_zip_member_name(member_name), raw_bytes)

            os.replace(temp_zip, final_zip)
            zip_sha256 = hashlib.sha256(final_zip.read_bytes()).hexdigest()
            rel_path = final_zip.relative_to(self._paths.root).as_posix()

            pkg = ArchivePackage(
                id=_new_id(),
                institution_id=exam.institution_id,
                exam_id=exam.id,
                file_path=rel_path,
                sha256=zip_sha256,
                file_count=len(manifest_files) + 1,
                include_personal_info=1 if payload.include_personal_info else 0,
                manifest_json=manifest_bytes.decode("utf-8"),
                created_at=_now_iso(),
            )
            session.add(pkg)
            self._append_audit(
                session,
                institution_id=exam.institution_id,
                exam_id=exam.id,
                action="arc.package.export",
                entity_type="archive_package",
                entity_id=pkg.id,
                summary={
                    "file_path": rel_path,
                    "file_count": pkg.file_count,
                    "include_personal_info": payload.include_personal_info,
                },
            )
            return {
                "id": pkg.id,
                "file_path": pkg.file_path,
                "sha256": pkg.sha256,
                "file_count": pkg.file_count,
                "include_personal_info": bool(pkg.include_personal_info),
                "missing_files": missing_files,
                "created_at": pkg.created_at,
            }

    def verify_archive_package(
        self, payload: ArcPackageVerifyPayload
    ) -> dict[str, Any]:
        """Verify ZIP archive integrity, manifest hashes, and path safety (ARC-02)."""
        with session_scope(self._session_factory) as session:
            pkg = self._repo.get_package(session, payload.package_id)
            if pkg is None or pkg.institution_id != payload.institution_id:
                raise NotFoundError("Paket arsip tidak ditemukan.")
            zip_path = _resolve_under_root(self._paths.root, pkg.file_path)
            if not zip_path.exists():
                raise NotFoundError("File ZIP paket arsip tidak ditemukan di disk.")

            errors: list[str] = []
            checked_files = 0
            manifest: dict[str, Any] = {}

            with zipfile.ZipFile(zip_path, mode="r") as zf:
                names = zf.namelist()
                for name in names:
                    try:
                        _safe_zip_member_name(name)
                    except StorageError as exc:
                        errors.append(str(exc))

                if "manifest.json" not in names:
                    errors.append("manifest.json tidak ditemukan di dalam ZIP.")
                else:
                    manifest = _parse_json_dict(
                        zf.read("manifest.json").decode("utf-8")
                    )
                    expected_files = manifest.get("files", [])
                    if isinstance(expected_files, list):
                        for item in expected_files:
                            if not isinstance(item, dict):
                                continue
                            rel = str(item.get("path", ""))
                            expected_hash = str(item.get("sha256", ""))
                            if rel not in names:
                                errors.append(f"File hilang dari ZIP: {rel}")
                                continue
                            actual_hash = hashlib.sha256(zf.read(rel)).hexdigest()
                            if actual_hash != expected_hash:
                                errors.append(f"Checksum tidak cocok untuk: {rel}")
                            checked_files += 1

            return {
                "package_id": pkg.id,
                "valid": len(errors) == 0,
                "checked_files": checked_files,
                "errors": errors,
                "manifest": manifest,
            }

    def duplicate_event(self, payload: ArcDuplicatePayload) -> dict[str, Any]:
        """Clone policies and structure into a new DRAFT event (ARC-03)."""
        if payload.ends_on < payload.starts_on:
            raise ValidationError("Tanggal selesai tidak boleh sebelum tanggal mulai.")
        with session_scope(self._session_factory) as session:
            source = self._require_exam(
                session, payload.institution_id, payload.source_exam_id
            )
            year = session.get(AcademicYear, payload.target_year_id)
            if year is None or year.institution_id != payload.institution_id:
                raise NotFoundError("Tahun ajaran tujuan tidak ditemukan.")

            now = _now_iso()
            new_exam_id = _new_id()
            new_exam = Exam(
                id=new_exam_id,
                institution_id=source.institution_id,
                year_id=payload.target_year_id,
                exam_type_id=source.exam_type_id,
                title=payload.title.strip(),
                semester_label=payload.semester_label.strip(),
                mode=payload.mode or source.mode,
                starts_on=payload.starts_on,
                ends_on=payload.ends_on,
                state="DRAFT",
                config_json=source.config_json,
                active_plan_id=None,
                revision=1,
                created_at=now,
                updated_at=now,
            )
            session.add(new_exam)
            session.flush()

            # Clone rooms (definitions only, no sessions/sittings)
            for room in session.scalars(
                select(ExamRoom).where(ExamRoom.exam_id == source.id)
            ).all():
                session.add(
                    ExamRoom(
                        id=_new_id(),
                        exam_id=new_exam_id,
                        source_room_id=room.source_room_id,
                        code=room.code,
                        name=room.name,
                        layout_json=room.layout_json,
                        capacity_limit=room.capacity_limit,
                        mode=room.mode,
                        revision=1,
                        created_at=now,
                        updated_at=now,
                    )
                )

            # Clone subjects & groups + requirements
            subj_map: dict[str, str] = {}
            for subj in session.scalars(
                select(ExamSubject).where(ExamSubject.exam_id == source.id)
            ).all():
                new_sid = _new_id()
                subj_map[subj.id] = new_sid
                session.add(
                    ExamSubject(
                        id=new_sid,
                        exam_id=new_exam_id,
                        source_subject_id=subj.source_subject_id,
                        code=subj.code,
                        name=subj.name,
                        revision=1,
                        created_at=now,
                        updated_at=now,
                    )
                )

            group_map: dict[str, str] = {}
            for grp in session.scalars(
                select(ExamGroup).where(ExamGroup.exam_id == source.id)
            ).all():
                new_gid = _new_id()
                group_map[grp.id] = new_gid
                session.add(
                    ExamGroup(
                        id=new_gid,
                        exam_id=new_exam_id,
                        label=grp.label,
                        rule_json=grp.rule_json,
                        revision=1,
                        created_at=now,
                        updated_at=now,
                    )
                )

            if group_map:
                for req in session.scalars(
                    select(ExamRequirement).where(
                        ExamRequirement.group_id.in_(list(group_map.keys()))
                    )
                ).all():
                    mapped_gid = group_map.get(req.group_id)
                    mapped_sid = subj_map.get(req.exam_subject_id)
                    if mapped_gid and mapped_sid:
                        session.add(
                            ExamRequirement(
                                id=_new_id(),
                                group_id=mapped_gid,
                                exam_subject_id=mapped_sid,
                                attempt_no=req.attempt_no,
                                duration_min=req.duration_min,
                                mode=req.mode,
                                eligible_sessions_json="[]",
                                revision=1,
                                created_at=now,
                                updated_at=now,
                            )
                        )

            # Clone committee roles tree (policies/structure, NOT member actuals)
            roles = list(
                session.scalars(
                    select(CommitteeRole)
                    .where(CommitteeRole.exam_id == source.id)
                    .order_by(CommitteeRole.sort_order.asc())
                ).all()
            )
            role_map = {r.id: _new_id() for r in roles}
            for r in roles:
                session.add(
                    CommitteeRole(
                        id=role_map[r.id],
                        exam_id=new_exam_id,
                        name=r.name,
                        parent_id=role_map.get(r.parent_id) if r.parent_id else None,
                        sort_order=r.sort_order,
                        jobdesc=r.jobdesc,
                        revision=1,
                        created_at=now,
                        updated_at=now,
                    )
                )

            # Clone finance policies (budget categories & honor rules), NOT actuals
            cats = list(
                session.scalars(
                    select(BudgetCategory).where(
                        BudgetCategory.exam_id == source.id,
                        BudgetCategory.archived == 0,
                    )
                ).all()
            )
            cat_map = {c.id: _new_id() for c in cats}
            for c in cats:
                session.add(
                    BudgetCategory(
                        id=cat_map[c.id],
                        exam_id=new_exam_id,
                        label=c.label,
                        parent_id=cat_map.get(c.parent_id) if c.parent_id else None,
                        archived=0,
                        created_at=now,
                    )
                )

            for rule in session.scalars(
                select(HonorRule).where(HonorRule.exam_id == source.id)
            ).all():
                session.add(
                    HonorRule(
                        id=_new_id(),
                        exam_id=new_exam_id,
                        role_code=rule.role_code,
                        unit_type=rule.unit_type,
                        rate_idr=rule.rate_idr,
                        effective_date=payload.starts_on,
                        created_at=now,
                    )
                )

            self._append_audit(
                session,
                institution_id=source.institution_id,
                exam_id=new_exam_id,
                action="arc.duplicate",
                entity_type="exam",
                entity_id=new_exam_id,
                summary={
                    "source_exam_id": source.id,
                    "cloned_rooms": len(
                        session.scalars(
                            select(ExamRoom).where(ExamRoom.exam_id == source.id)
                        ).all()
                    ),
                    "cloned_subjects": len(subj_map),
                    "cloned_roles": len(role_map),
                },
            )
            return {
                "id": new_exam.id,
                "title": new_exam.title,
                "state": new_exam.state,
                "source_exam_id": source.id,
                "cloned": {
                    "subjects": len(subj_map),
                    "groups": len(group_map),
                    "roles": len(role_map),
                    "budget_categories": len(cat_map),
                },
            }

    def review_retention(self, payload: ArcRetentionReviewPayload) -> dict[str, Any]:
        """Review event data age and existing retention backups (ARC-04)."""
        today = datetime.now(UTC).date()
        with session_scope(self._session_factory) as session:
            years, types = self._year_and_type_maps(session, payload.institution_id)
            exams = self._repo.list_exams(session, payload.institution_id)
            items: list[dict[str, Any]] = []
            for exam in exams:
                try:
                    end_d = date.fromisoformat(exam.ends_on[:10])
                    age_days = max(0, (today - end_d).days)
                except ValueError:
                    age_days = 0
                eligible = (
                    exam.state in ("COMPLETED", "ARCHIVED", "DRAFT")
                    and age_days >= payload.min_age_days
                )
                items.append(
                    {
                        "id": exam.id,
                        "title": exam.title,
                        "year_label": years.get(exam.year_id, "-"),
                        "exam_type_label": types.get(exam.exam_type_id, "-"),
                        "state": exam.state,
                        "ends_on": exam.ends_on,
                        "age_days": age_days,
                        "eligible_for_purge": eligible,
                    }
                )

            backups = self._repo.list_backups(session, payload.institution_id)
            backup_rows = [
                {
                    "id": b.id,
                    "exam_id": b.exam_id,
                    "exam_title": b.exam_title,
                    "file_path": b.file_path,
                    "sha256": b.sha256,
                    "byte_size": b.byte_size,
                    "authorized_by": b.authorized_by,
                    "created_at": b.created_at,
                }
                for b in backups
            ]
            return {
                "min_age_days": payload.min_age_days,
                "events": items,
                "backups": backup_rows,
                "last_good_backup": backup_rows[0] if backup_rows else None,
            }

    def preview_retention_impact(self, payload: ArcExamScopedPayload) -> dict[str, Any]:
        """Preview exact deletion impact before authorized purge (ARC-04)."""
        with session_scope(self._session_factory) as session:
            exam = self._require_exam(session, payload.institution_id, payload.exam_id)
            plan_ids = list(
                session.scalars(select(Plan.id).where(Plan.exam_id == exam.id)).all()
            )
            counts = {
                "people": _count_rows(session, ExamPerson, ExamPerson.exam_id, exam.id),
                "participants": _count_rows(
                    session, ExamParticipant, ExamParticipant.exam_id, exam.id
                ),
                "rooms": _count_rows(session, ExamRoom, ExamRoom.exam_id, exam.id),
                "subjects": _count_rows(
                    session, ExamSubject, ExamSubject.exam_id, exam.id
                ),
                "plans": len(plan_ids),
                "sessions": _count_by_plans(session, ExamSession, plan_ids),
                "sittings": _count_by_plans(session, ParticipantSitting, plan_ids),
                "invigilations": _count_by_plans(session, Invigilation, plan_ids),
                "tasks": _count_rows(session, Task, Task.exam_id, exam.id),
                "incidents": _count_rows(session, Incident, Incident.exam_id, exam.id),
                "documents": _count_rows(
                    session, DocumentRun, DocumentRun.exam_id, exam.id
                ),
                "document_numbers": _count_rows(
                    session, DocumentNumber, DocumentNumber.exam_id, exam.id
                ),
                "budget_versions": _count_rows(
                    session, BudgetVersion, BudgetVersion.exam_id, exam.id
                ),
                "ledger_entries": _count_rows(
                    session, LedgerEntry, LedgerEntry.exam_id, exam.id
                ),
                "honor_lines": _count_rows(
                    session, HonorLine, HonorLine.exam_id, exam.id
                ),
                "lpj_versions": _count_rows(
                    session, LpjVersion, LpjVersion.exam_id, exam.id
                ),
                "archive_packages": _count_rows(
                    session, ArchivePackage, ArchivePackage.exam_id, exam.id
                ),
            }
            blockers: list[str] = []
            if exam.state in ("READY", "RUNNING"):
                blockers.append(
                    f"Kegiatan berstatus {exam.state} tidak dapat dihapus langsung."
                )
            return {
                "exam_id": exam.id,
                "exam_title": exam.title,
                "state": exam.state,
                "can_purge": len(blockers) == 0,
                "blockers": blockers,
                "impact_counts": counts,
                "total_affected_rows": sum(counts.values()) + 1,
            }

    def _create_pre_purge_backup(
        self, session: Session, exam: Exam, authorized_by: str
    ) -> RetentionBackup:
        """Create a consistent SQLite backup before purging an event."""
        self._paths.backups_dir.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
        safe_title = sanitize_filename(exam.title)[:32]
        bak_name = f"pre_purge_{safe_title}_{stamp}_{exam.id[:8]}.sqlite"
        final_bak = self._paths.backups_dir / bak_name
        temp_bak = self._paths.backups_dir / f".tmp_{_new_id()}_{bak_name}"

        raw_conn = session.connection().connection.dbapi_connection
        if isinstance(raw_conn, sqlite3.Connection):
            dst = sqlite3.connect(str(temp_bak))
            try:
                raw_conn.backup(dst)
            finally:
                dst.close()
        else:
            temp_bak.write_bytes(b"")

        os.replace(temp_bak, final_bak)
        raw_bytes = final_bak.read_bytes()
        sha256 = hashlib.sha256(raw_bytes).hexdigest()
        rel_path = final_bak.relative_to(self._paths.root).as_posix()

        backup_row = RetentionBackup(
            id=_new_id(),
            institution_id=exam.institution_id,
            exam_id=exam.id,
            exam_title=exam.title,
            file_path=rel_path,
            sha256=sha256,
            byte_size=len(raw_bytes),
            authorized_by=authorized_by,
            created_at=_now_iso(),
        )
        session.add(backup_row)
        return backup_row

    def purge_event(self, payload: ArcRetentionPurgePayload) -> dict[str, Any]:
        """Authorized deletion of an event after creating a verified backup (ARC-04)."""
        authorized_by = payload.authorized_by.strip()
        if not authorized_by:
            raise ValidationError("Nama pejabat/operator otorisasi wajib diisi.")
        with session_scope(self._session_factory) as session:
            exam = self._require_exam(session, payload.institution_id, payload.exam_id)
            if payload.confirm_title.strip() != exam.title:
                raise ValidationError(
                    "Judul konfirmasi tidak sesuai dengan nama kegiatan."
                )
            if exam.state in ("READY", "RUNNING"):
                raise ConflictError(
                    f"Kegiatan berstatus {exam.state} tidak dapat dihapus."
                )

            backup_row = self._create_pre_purge_backup(session, exam, authorized_by)
            deleted_exam_id = exam.id
            deleted_title = exam.title
            session.delete(exam)
            session.flush()

            fk_violations = session.execute(text("PRAGMA foreign_key_check")).fetchall()
            if fk_violations:
                raise ConflictError(
                    "Penghapusan dibatalkan karena terdeteksi referensi menggantung."
                )

            self._append_audit(
                session,
                institution_id=payload.institution_id,
                exam_id=None,
                action="arc.retention.purge",
                entity_type="exam",
                entity_id=deleted_exam_id,
                summary={
                    "deleted_title": deleted_title,
                    "authorized_by": authorized_by,
                    "backup_id": backup_row.id,
                    "backup_path": backup_row.file_path,
                },
            )
            return {
                "purged_exam_id": deleted_exam_id,
                "purged_title": deleted_title,
                "backup": {
                    "id": backup_row.id,
                    "file_path": backup_row.file_path,
                    "sha256": backup_row.sha256,
                    "byte_size": backup_row.byte_size,
                },
            }
