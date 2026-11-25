"""Transactional service layer for MST-01..MST-08."""

from __future__ import annotations

import base64
import json
import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker

from backend.core.db import session_scope
from backend.core.errors import AppError, ConflictError, NotFoundError, ValidationError
from backend.core.jobs import atomic_write_bytes
from backend.core.paths import WorkspacePaths
from backend.modules.cfg.repository import CfgRepository
from backend.modules.mst.models import (
    Enrollment,
    Room,
    SchoolClass,
    Staff,
    Student,
    Subject,
    TeachingAssignment,
)
from backend.modules.mst.repository import MstRepository
from backend.modules.mst.schemas import (
    ClassSavePayload,
    DataQualityPayload,
    DuplicatePolicy,
    EnrollmentSavePayload,
    ExportMasterPayload,
    ImportCommitPayload,
    ImportPreviewPayload,
    MasterKind,
    MasterListPayload,
    RoomLayoutConfig,
    RoomSavePayload,
    ScopedEntityDeletePayload,
    StaffSavePayload,
    StudentSavePayload,
    SubjectSavePayload,
    TeachingAssignmentSavePayload,
    build_room_stats,
)
from backend.modules.mst.xlsx_io import build_xlsx_bytes, parse_xlsx_rows


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()


def _new_id() -> str:
    return uuid.uuid4().hex


def _check_revision(actual: int, expected: int | None) -> None:
    if expected is not None and actual != expected:
        raise AppError(
            "STALE_REVISION",
            "Data telah diubah oleh proses lain. Muat ulang sebelum menyimpan.",
        )


def _serialize_student(s: Student) -> dict[str, Any]:
    return {
        "id": s.id,
        "institution_id": s.institution_id,
        "nis": s.nis,
        "nisn": s.nisn,
        "full_name": s.full_name,
        "gender": s.gender,
        "photo_asset_id": s.photo_asset_id,
        "accommodation": json.loads(s.accommodation_json),
        "active": bool(s.active),
        "revision": s.revision,
    }


def _serialize_staff(st: Staff) -> dict[str, Any]:
    return {
        "id": st.id,
        "institution_id": st.institution_id,
        "staff_code": st.staff_code,
        "nip": st.nip,
        "full_name": st.full_name,
        "role": st.role,
        "active": bool(st.active),
        "revision": st.revision,
    }


def _serialize_class(cls_row: SchoolClass) -> dict[str, Any]:
    return {
        "id": cls_row.id,
        "institution_id": cls_row.institution_id,
        "year_id": cls_row.year_id,
        "level_id": cls_row.level_id,
        "name": cls_row.name,
        "program": cls_row.program,
        "revision": cls_row.revision,
    }


def _serialize_subject(subj: Subject) -> dict[str, Any]:
    return {
        "id": subj.id,
        "institution_id": subj.institution_id,
        "code": subj.code,
        "name": subj.name,
        "category": subj.category,
        "revision": subj.revision,
    }


def _serialize_room(room: Room) -> dict[str, Any]:
    layout = RoomLayoutConfig.model_validate_json(room.layout_json)
    return {
        "id": room.id,
        "institution_id": room.institution_id,
        "code": room.code,
        "name": room.name,
        "mode": room.mode,
        "capacity_limit": room.capacity_limit,
        "layout": layout.model_dump(),
        "stats": build_room_stats(layout, room.capacity_limit),
        "revision": room.revision,
    }


class MstService:
    """Application service for MST-01..MST-08."""

    def __init__(
        self,
        session_factory: sessionmaker[Session],
        paths: WorkspacePaths,
    ) -> None:
        self._session_factory = session_factory
        self._paths = paths
        self._repo = MstRepository()
        self._cfg_repo = CfgRepository()
        self._import_previews: dict[str, dict[str, Any]] = {}

    def _require_institution(self, session: Session, institution_id: str) -> None:
        if self._cfg_repo.get_institution(session, institution_id) is None:
            raise NotFoundError("Lembaga tidak ditemukan.")

    # --- MST-01 Students ---
    def list_students(self, payload: MasterListPayload) -> dict[str, Any]:
        with session_scope(self._session_factory) as session:
            self._require_institution(session, payload.institution_id)
            rows, total = self._repo.list_students(
                session,
                payload.institution_id,
                query=payload.query,
                active_only=payload.active_only,
                page=payload.page,
                page_size=payload.page_size,
            )
            enrollments = {
                e.student_id: e.class_id
                for e in self._repo.list_enrollments(
                    session, payload.institution_id, year_id=payload.year_id
                )
            }
            items = []
            for row in rows:
                item = _serialize_student(row)
                item["class_id"] = enrollments.get(row.id)
                items.append(item)
            return {
                "items": items,
                "total": total,
                "page": payload.page,
                "page_size": payload.page_size,
            }

    def save_student(self, payload: StudentSavePayload) -> dict[str, Any]:
        now = _now_iso()
        warnings: list[str] = []
        with session_scope(self._session_factory) as session:
            self._require_institution(session, payload.institution_id)
            if not payload.nisn:
                warnings.append("NISN kosong (diperbolehkan, lengkapi sebelum ekspor).")
            else:
                dup_nisn = [
                    s
                    for s in self._repo.list_all_students(
                        session, payload.institution_id
                    )
                    if s.nisn == payload.nisn and s.id != payload.id
                ]
                if dup_nisn:
                    warnings.append(
                        f"NISN '{payload.nisn}' juga dipakai oleh siswa lain."
                    )

            try:
                if payload.id is None:
                    student = Student(
                        id=_new_id(),
                        institution_id=payload.institution_id,
                        nis=payload.nis,
                        nisn=payload.nisn,
                        full_name=payload.full_name,
                        gender=payload.gender or None,
                        accommodation_json=payload.accommodation.model_dump_json(),
                        active=1 if payload.active else 0,
                        revision=1,
                        created_at=now,
                        updated_at=now,
                    )
                    session.add(student)
                    session.flush()
                    return {
                        "student": _serialize_student(student),
                        "warnings": warnings,
                    }

                existing = self._repo.get_student(
                    session, payload.institution_id, payload.id
                )
                if existing is None:
                    raise NotFoundError("Siswa tidak ditemukan.")
                _check_revision(existing.revision, payload.expected_revision)
                existing.nis = payload.nis
                existing.nisn = payload.nisn
                existing.full_name = payload.full_name
                existing.gender = payload.gender or None
                existing.accommodation_json = payload.accommodation.model_dump_json()
                existing.active = 1 if payload.active else 0
                existing.revision += 1
                existing.updated_at = now
                session.flush()
                return {"student": _serialize_student(existing), "warnings": warnings}
            except IntegrityError as exc:
                raise ConflictError(
                    "NIS siswa sudah terdaftar pada lembaga ini."
                ) from exc

    def delete_student(self, payload: ScopedEntityDeletePayload) -> dict[str, Any]:
        with session_scope(self._session_factory) as session:
            student = self._repo.get_student(
                session, payload.institution_id, payload.id
            )
            if student is None:
                raise NotFoundError("Siswa tidak ditemukan.")
            if self._repo.count_student_references(session, student.id) > 0:
                raise ConflictError(
                    "Siswa tidak dapat dihapus karena sudah memiliki "
                    "riwayat rombel/kegiatan."
                )
            session.delete(student)
            return {"deleted": True, "id": payload.id}

    # --- MST-02 Staff ---
    def list_staff(self, payload: MasterListPayload) -> dict[str, Any]:
        with session_scope(self._session_factory) as session:
            self._require_institution(session, payload.institution_id)
            rows, total = self._repo.list_staff(
                session,
                payload.institution_id,
                query=payload.query,
                active_only=payload.active_only,
                page=payload.page,
                page_size=payload.page_size,
            )
            return {
                "items": [_serialize_staff(row) for row in rows],
                "total": total,
                "page": payload.page,
                "page_size": payload.page_size,
            }

    def save_staff(self, payload: StaffSavePayload) -> dict[str, Any]:
        now = _now_iso()
        with session_scope(self._session_factory) as session:
            self._require_institution(session, payload.institution_id)
            try:
                if payload.id is None:
                    staff_row = Staff(
                        id=_new_id(),
                        institution_id=payload.institution_id,
                        staff_code=payload.staff_code,
                        nip=payload.nip,
                        full_name=payload.full_name,
                        role=payload.role,
                        active=1 if payload.active else 0,
                        revision=1,
                        created_at=now,
                        updated_at=now,
                    )
                    session.add(staff_row)
                    session.flush()
                    return {"staff": _serialize_staff(staff_row)}

                existing = self._repo.get_staff(
                    session, payload.institution_id, payload.id
                )
                if existing is None:
                    raise NotFoundError("Staf/guru tidak ditemukan.")
                _check_revision(existing.revision, payload.expected_revision)
                existing.staff_code = payload.staff_code
                existing.nip = payload.nip
                existing.full_name = payload.full_name
                existing.role = payload.role
                existing.active = 1 if payload.active else 0
                existing.revision += 1
                existing.updated_at = now
                session.flush()
                return {"staff": _serialize_staff(existing)}
            except IntegrityError as exc:
                raise ConflictError(
                    "Kode staf sudah digunakan di lembaga ini."
                ) from exc

    def delete_staff(self, payload: ScopedEntityDeletePayload) -> dict[str, Any]:
        with session_scope(self._session_factory) as session:
            staff_row = self._repo.get_staff(
                session, payload.institution_id, payload.id
            )
            if staff_row is None:
                raise NotFoundError("Staf/guru tidak ditemukan.")
            if self._repo.count_staff_references(session, staff_row.id) > 0:
                raise ConflictError(
                    "Staf tidak dapat dihapus karena terhubung dengan "
                    "penugasan mengajar."
                )
            session.delete(staff_row)
            return {"deleted": True, "id": payload.id}

    # --- MST-03 Classes & Enrollments ---
    def list_classes(self, payload: MasterListPayload) -> dict[str, Any]:
        with session_scope(self._session_factory) as session:
            self._require_institution(session, payload.institution_id)
            classes = self._repo.list_classes(
                session, payload.institution_id, year_id=payload.year_id
            )
            return {"items": [_serialize_class(c) for c in classes]}

    def save_class(self, payload: ClassSavePayload) -> dict[str, Any]:
        now = _now_iso()
        with session_scope(self._session_factory) as session:
            self._require_institution(session, payload.institution_id)
            if (
                self._cfg_repo.get_year(
                    session, payload.institution_id, payload.year_id
                )
                is None
            ):
                raise NotFoundError("Tahun ajaran tidak ditemukan pada lembaga ini.")
            if (
                self._cfg_repo.get_level(
                    session, payload.institution_id, payload.level_id
                )
                is None
            ):
                raise NotFoundError("Tingkatan tidak ditemukan pada lembaga ini.")
            try:
                if payload.id is None:
                    cls_row = SchoolClass(
                        id=_new_id(),
                        institution_id=payload.institution_id,
                        year_id=payload.year_id,
                        level_id=payload.level_id,
                        name=payload.name,
                        program=payload.program.strip() if payload.program else None,
                        revision=1,
                        created_at=now,
                        updated_at=now,
                    )
                    session.add(cls_row)
                    session.flush()
                    return {"class_item": _serialize_class(cls_row)}

                existing = self._repo.get_class(
                    session, payload.institution_id, payload.id
                )
                if existing is None:
                    raise NotFoundError("Kelas tidak ditemukan.")
                _check_revision(existing.revision, payload.expected_revision)
                existing.year_id = payload.year_id
                existing.level_id = payload.level_id
                existing.name = payload.name
                existing.program = payload.program.strip() if payload.program else None
                existing.revision += 1
                existing.updated_at = now
                session.flush()
                return {"class_item": _serialize_class(existing)}
            except IntegrityError as exc:
                raise ConflictError(
                    "Nama kelas pada tahun ajaran dan tingkatan tersebut sudah ada."
                ) from exc

    def save_enrollment(self, payload: EnrollmentSavePayload) -> dict[str, Any]:
        now = _now_iso()
        with session_scope(self._session_factory) as session:
            self._require_institution(session, payload.institution_id)
            if (
                self._repo.get_student(
                    session, payload.institution_id, payload.student_id
                )
                is None
            ):
                raise NotFoundError("Siswa tidak ditemukan.")
            cls_row = self._repo.get_class(
                session, payload.institution_id, payload.class_id
            )
            if cls_row is None or cls_row.year_id != payload.year_id:
                raise ValidationError("Kelas tujuan tidak sesuai tahun ajaran.")

            existing = self._repo.get_enrollment(
                session, payload.institution_id, payload.student_id, payload.year_id
            )
            if existing is None:
                enrollment = Enrollment(
                    id=_new_id(),
                    institution_id=payload.institution_id,
                    student_id=payload.student_id,
                    class_id=payload.class_id,
                    year_id=payload.year_id,
                    status=payload.status,
                    revision=1,
                    created_at=now,
                    updated_at=now,
                )
                session.add(enrollment)
                session.flush()
                return {"enrollment_id": enrollment.id, "class_id": enrollment.class_id}

            existing.class_id = payload.class_id
            existing.status = payload.status
            existing.revision += 1
            existing.updated_at = now
            session.flush()
            return {"enrollment_id": existing.id, "class_id": existing.class_id}

    # --- MST-04 Subjects & Teaching Assignments ---
    def list_subjects(self, payload: MasterListPayload) -> dict[str, Any]:
        with session_scope(self._session_factory) as session:
            self._require_institution(session, payload.institution_id)
            subjects = self._repo.list_subjects(
                session, payload.institution_id, query=payload.query
            )
            assignments = self._repo.list_teaching_assignments(
                session, payload.institution_id
            )
            classes = self._repo.list_classes(session, payload.institution_id)
            warnings: list[str] = []
            if subjects and classes:
                assigned_pairs = {(ta.class_id, ta.subject_id) for ta in assignments}
                missing_pairs = len(subjects) * len(classes) - len(assigned_pairs)
                if missing_pairs > 0:
                    warnings.append(
                        f"{missing_pairs} pasangan kelas-mapel belum memiliki "
                        "guru pengampu (diperlukan untuk aturan hindari mapel sendiri)."
                    )
            return {
                "items": [_serialize_subject(s) for s in subjects],
                "assignments": [
                    {
                        "id": ta.id,
                        "staff_id": ta.staff_id,
                        "class_id": ta.class_id,
                        "subject_id": ta.subject_id,
                    }
                    for ta in assignments
                ],
                "warnings": warnings,
            }

    def save_subject(self, payload: SubjectSavePayload) -> dict[str, Any]:
        now = _now_iso()
        with session_scope(self._session_factory) as session:
            self._require_institution(session, payload.institution_id)
            try:
                if payload.id is None:
                    subj = Subject(
                        id=_new_id(),
                        institution_id=payload.institution_id,
                        code=payload.code,
                        name=payload.name.strip(),
                        category=payload.category.strip() if payload.category else None,
                        revision=1,
                        created_at=now,
                        updated_at=now,
                    )
                    session.add(subj)
                    session.flush()
                    return {"subject": _serialize_subject(subj)}

                existing = self._repo.get_subject(
                    session, payload.institution_id, payload.id
                )
                if existing is None:
                    raise NotFoundError("Mata pelajaran tidak ditemukan.")
                _check_revision(existing.revision, payload.expected_revision)
                existing.code = payload.code
                existing.name = payload.name.strip()
                existing.category = (
                    payload.category.strip() if payload.category else None
                )
                existing.revision += 1
                existing.updated_at = now
                session.flush()
                return {"subject": _serialize_subject(existing)}
            except IntegrityError as exc:
                raise ConflictError("Kode mata pelajaran sudah terdaftar.") from exc

    def save_teaching_assignment(
        self, payload: TeachingAssignmentSavePayload
    ) -> dict[str, Any]:
        now = _now_iso()
        with session_scope(self._session_factory) as session:
            self._require_institution(session, payload.institution_id)
            if (
                self._repo.get_staff(session, payload.institution_id, payload.staff_id)
                is None
            ):
                raise NotFoundError("Guru/staf tidak ditemukan.")
            if (
                self._repo.get_class(session, payload.institution_id, payload.class_id)
                is None
            ):
                raise NotFoundError("Kelas tidak ditemukan.")
            if (
                self._repo.get_subject(
                    session, payload.institution_id, payload.subject_id
                )
                is None
            ):
                raise NotFoundError("Mata pelajaran tidak ditemukan.")
            try:
                ta = TeachingAssignment(
                    id=_new_id(),
                    institution_id=payload.institution_id,
                    staff_id=payload.staff_id,
                    class_id=payload.class_id,
                    subject_id=payload.subject_id,
                    revision=1,
                    created_at=now,
                    updated_at=now,
                )
                session.add(ta)
                session.flush()
                return {"id": ta.id}
            except IntegrityError as exc:
                raise ConflictError("Relasi guru-kelas-mapel sudah terdaftar.") from exc

    def delete_teaching_assignment(
        self, payload: ScopedEntityDeletePayload
    ) -> dict[str, Any]:
        with session_scope(self._session_factory) as session:
            ta = self._repo.get_teaching_assignment(
                session, payload.institution_id, payload.id
            )
            if ta is None:
                raise NotFoundError("Relasi mengajar tidak ditemukan.")
            session.delete(ta)
            return {"deleted": True, "id": payload.id}

    # --- MST-05 Rooms ---
    def list_rooms(self, payload: MasterListPayload) -> dict[str, Any]:
        with session_scope(self._session_factory) as session:
            self._require_institution(session, payload.institution_id)
            rooms = self._repo.list_rooms(
                session, payload.institution_id, query=payload.query
            )
            return {"items": [_serialize_room(r) for r in rooms]}

    def save_room(self, payload: RoomSavePayload) -> dict[str, Any]:
        now = _now_iso()
        with session_scope(self._session_factory) as session:
            self._require_institution(session, payload.institution_id)
            try:
                if payload.id is None:
                    room = Room(
                        id=_new_id(),
                        institution_id=payload.institution_id,
                        code=payload.code,
                        name=payload.name.strip(),
                        mode=payload.mode,
                        capacity_limit=payload.capacity_limit,
                        layout_json=payload.layout.model_dump_json(),
                        revision=1,
                        created_at=now,
                        updated_at=now,
                    )
                    session.add(room)
                    session.flush()
                    return {"room": _serialize_room(room)}

                existing = self._repo.get_room(
                    session, payload.institution_id, payload.id
                )
                if existing is None:
                    raise NotFoundError("Ruang ujian tidak ditemukan.")
                _check_revision(existing.revision, payload.expected_revision)
                existing.code = payload.code
                existing.name = payload.name.strip()
                existing.mode = payload.mode
                existing.capacity_limit = payload.capacity_limit
                existing.layout_json = payload.layout.model_dump_json()
                existing.revision += 1
                existing.updated_at = now
                session.flush()
                return {"room": _serialize_room(existing)}
            except IntegrityError as exc:
                raise ConflictError(
                    "Kode ruang sudah digunakan di lembaga ini."
                ) from exc

    # --- MST-06 XLSX Import Wizard ---
    def preview_import(self, payload: ImportPreviewPayload) -> dict[str, Any]:
        headers, parsed_rows, warnings = parse_xlsx_rows(payload.content_base64)
        mapping = payload.mapping or {h: h.lower() for h in headers}

        with session_scope(self._session_factory) as session:
            self._require_institution(session, payload.institution_id)
            existing_keys = self._existing_natural_keys(
                session, payload.institution_id, payload.kind
            )

        seen_in_file: set[str] = set()
        valid_rows: list[dict[str, Any]] = []
        duplicate_rows: list[dict[str, Any]] = []
        error_rows: list[dict[str, Any]] = []

        for raw in parsed_rows:
            row_num = int(raw["row_number"])
            if raw["formula_columns"]:
                cols = ", ".join(raw["formula_columns"])
                error_rows.append(
                    {
                        "row_number": row_num,
                        "error": f"Sel formula ditolak pada kolom: {cols}",
                    }
                )
                continue

            mapped: dict[str, str] = {}
            for src_col, target_field in mapping.items():
                if target_field and src_col in raw["values"]:
                    mapped[target_field] = raw["values"][src_col]

            natural_key, validated_or_err = self._validate_import_row(
                payload.kind, mapped
            )
            if isinstance(validated_or_err, str):
                error_rows.append({"row_number": row_num, "error": validated_or_err})
                continue

            if natural_key:
                if natural_key in seen_in_file:
                    error_rows.append(
                        {
                            "row_number": row_num,
                            "error": f"Duplikat kunci '{natural_key}' di dalam berkas.",
                        }
                    )
                    continue
                seen_in_file.add(natural_key)

                if natural_key in existing_keys:
                    duplicate_rows.append(
                        {
                            "row_number": row_num,
                            "key": natural_key,
                            "data": validated_or_err,
                        }
                    )
                    continue

            valid_rows.append(
                {
                    "row_number": row_num,
                    "key": natural_key,
                    "data": validated_or_err,
                }
            )

        preview_id = _new_id()
        self._import_previews[preview_id] = {
            "institution_id": payload.institution_id,
            "kind": payload.kind,
            "valid_rows": valid_rows,
            "duplicate_rows": duplicate_rows,
            "error_rows": error_rows,
        }
        return {
            "preview_id": preview_id,
            "headers": headers,
            "warnings": warnings,
            "counts": {
                "total": len(parsed_rows),
                "valid": len(valid_rows),
                "duplicate": len(duplicate_rows),
                "invalid": len(error_rows),
            },
            "sample_valid": valid_rows[:10],
            "sample_duplicates": duplicate_rows[:10],
            "error_rows": error_rows,
        }

    def commit_import(self, payload: ImportCommitPayload) -> dict[str, Any]:
        preview = self._import_previews.get(payload.preview_id)
        if preview is None or preview["institution_id"] != payload.institution_id:
            raise NotFoundError("Pratinjau impor tidak ditemukan atau kedaluwarsa.")

        if preview["error_rows"] and not payload.skip_invalid_rows:
            raise ValidationError(
                f"Terdapat {len(preview['error_rows'])} baris tidak valid; "
                "perbaiki berkas atau aktifkan lewati baris gagal."
            )

        if preview["duplicate_rows"] and payload.duplicate_policy == "fail":
            raise ConflictError(
                f"Terdapat {len(preview['duplicate_rows'])} baris duplikat "
                "dengan kebijakan 'fail'."
            )

        kind: MasterKind = preview["kind"]
        now = _now_iso()
        inserted = 0
        updated = 0
        skipped = len(preview["error_rows"])

        with session_scope(self._session_factory) as session:
            self._require_institution(session, payload.institution_id)
            for item in preview["valid_rows"]:
                self._insert_import_row(
                    session, payload.institution_id, kind, item["data"], now
                )
                inserted += 1

            for dup in preview["duplicate_rows"]:
                policy: DuplicatePolicy = payload.duplicate_policy
                if policy == "skip":
                    skipped += 1
                    continue
                if policy == "update":
                    self._update_import_row(
                        session,
                        payload.institution_id,
                        kind,
                        dup["key"],
                        dup["data"],
                        now,
                    )
                    updated += 1

        del self._import_previews[payload.preview_id]
        return {
            "committed": True,
            "inserted": inserted,
            "updated": updated,
            "skipped": skipped,
        }

    def _existing_natural_keys(
        self, session: Session, institution_id: str, kind: MasterKind
    ) -> set[str]:
        if kind == "students":
            return {
                s.nis
                for s in self._repo.list_all_students(session, institution_id)
                if s.nis
            }
        if kind == "staff":
            return {
                st.staff_code
                for st in self._repo.list_all_staff(session, institution_id)
            }
        if kind == "subjects":
            return {
                sub.code for sub in self._repo.list_subjects(session, institution_id)
            }
        if kind == "rooms":
            return {r.code for r in self._repo.list_rooms(session, institution_id)}
        return set()

    def _validate_import_row(
        self, kind: MasterKind, mapped: dict[str, str]
    ) -> tuple[str | None, dict[str, Any] | str]:
        try:
            if kind == "students":
                name = (mapped.get("full_name") or mapped.get("name") or "").strip()
                nis = (mapped.get("nis") or "").strip() or None
                nisn = (mapped.get("nisn") or "").strip() or None
                if len(name) < 2:
                    return None, "Nama siswa wajib diisi minimal 2 karakter."
                return nis, {"nis": nis, "nisn": nisn, "full_name": name}
            if kind == "staff":
                code = (
                    (mapped.get("staff_code") or mapped.get("code") or "")
                    .strip()
                    .upper()
                )
                name = (mapped.get("full_name") or mapped.get("name") or "").strip()
                nip = (mapped.get("nip") or "").strip() or None
                role = (mapped.get("role") or "teacher").strip()
                if not code or len(name) < 2:
                    return None, "Kode staf dan nama wajib diisi."
                if role not in ("teacher", "tu", "external_invigilator"):
                    return None, f"Peran staf '{role}' tidak valid."
                return code, {
                    "staff_code": code,
                    "nip": nip,
                    "full_name": name,
                    "role": role,
                }
            if kind == "subjects":
                code = (mapped.get("code") or "").strip().upper()
                name = (mapped.get("name") or "").strip()
                if not code or len(name) < 2:
                    return None, "Kode dan nama mapel wajib diisi."
                return code, {"code": code, "name": name}
            if kind == "rooms":
                code = (mapped.get("code") or "").strip().upper()
                name = (mapped.get("name") or "").strip()
                rows = int(mapped.get("rows") or "4")
                cols = int(mapped.get("columns") or mapped.get("cols") or "5")
                seats = int(mapped.get("seats_per_desk") or "1")
                cap = int(
                    mapped.get("capacity")
                    or mapped.get("capacity_limit")
                    or rows * cols * seats
                )
                layout = RoomLayoutConfig(rows=rows, cols=cols, seats_per_desk=seats)
                if cap > layout.enabled_seat_count:
                    return None, "Kapasitas melebihi total kursi layout."
                return code, {
                    "code": code,
                    "name": name or code,
                    "capacity_limit": cap,
                    "layout_json": layout.model_dump_json(),
                }
            return None, f"Jenis impor '{kind}' tidak didukung."
        except (ValueError, TypeError) as exc:
            return None, f"Format nilai tidak valid: {exc}"

    def _insert_import_row(
        self,
        session: Session,
        institution_id: str,
        kind: MasterKind,
        data: dict[str, Any],
        now: str,
    ) -> None:
        if kind == "students":
            session.add(
                Student(
                    id=_new_id(),
                    institution_id=institution_id,
                    nis=data["nis"],
                    nisn=data["nisn"],
                    full_name=data["full_name"],
                    accommodation_json="{}",
                    active=1,
                    revision=1,
                    created_at=now,
                    updated_at=now,
                )
            )
        elif kind == "staff":
            session.add(
                Staff(
                    id=_new_id(),
                    institution_id=institution_id,
                    staff_code=data["staff_code"],
                    nip=data["nip"],
                    full_name=data["full_name"],
                    role=data["role"],
                    active=1,
                    revision=1,
                    created_at=now,
                    updated_at=now,
                )
            )
        elif kind == "subjects":
            session.add(
                Subject(
                    id=_new_id(),
                    institution_id=institution_id,
                    code=data["code"],
                    name=data["name"],
                    revision=1,
                    created_at=now,
                    updated_at=now,
                )
            )
        elif kind == "rooms":
            session.add(
                Room(
                    id=_new_id(),
                    institution_id=institution_id,
                    code=data["code"],
                    name=data["name"],
                    mode="paper",
                    capacity_limit=data["capacity_limit"],
                    layout_json=data["layout_json"],
                    revision=1,
                    created_at=now,
                    updated_at=now,
                )
            )

    def _update_import_row(
        self,
        session: Session,
        institution_id: str,
        kind: MasterKind,
        key: str,
        data: dict[str, Any],
        now: str,
    ) -> None:
        if kind == "students":
            row = self._repo.get_student_by_nis(session, institution_id, key)
            if row is not None:
                row.nisn = data["nisn"]
                row.full_name = data["full_name"]
                row.revision += 1
                row.updated_at = now
        elif kind == "staff":
            row_st = self._repo.get_staff_by_code(session, institution_id, key)
            if row_st is not None:
                row_st.nip = data["nip"]
                row_st.full_name = data["full_name"]
                row_st.role = data["role"]
                row_st.revision += 1
                row_st.updated_at = now
        elif kind == "subjects":
            row_sub = self._repo.get_subject_by_code(session, institution_id, key)
            if row_sub is not None:
                row_sub.name = data["name"]
                row_sub.revision += 1
                row_sub.updated_at = now
        elif kind == "rooms":
            row_room = self._repo.get_room_by_code(session, institution_id, key)
            if row_room is not None:
                row_room.name = data["name"]
                row_room.capacity_limit = data["capacity_limit"]
                row_room.layout_json = data["layout_json"]
                row_room.revision += 1
                row_room.updated_at = now

    # --- MST-07 Export Masters ---
    def export_xlsx(self, payload: ExportMasterPayload) -> dict[str, Any]:
        export_rows: list[dict[str, Any]] = []
        with session_scope(self._session_factory) as session:
            self._require_institution(session, payload.institution_id)
            if payload.kind == "students":
                rows_st, _ = self._repo.list_students(
                    session,
                    payload.institution_id,
                    query=payload.query,
                    active_only=payload.active_only,
                    page=1,
                    page_size=50000,
                )
                columns = [
                    ("nis", "NIS"),
                    ("nisn", "NISN"),
                    ("full_name", "Nama Lengkap"),
                    ("gender", "Jenis Kelamin"),
                    ("active", "Status"),
                ]
                export_rows = [
                    {
                        "nis": s.nis or "",
                        "nisn": s.nisn or "",
                        "full_name": s.full_name,
                        "gender": s.gender or "",
                        "active": "Aktif" if s.active else "Nonaktif",
                    }
                    for s in rows_st
                ]
            elif payload.kind == "staff":
                rows_sf, _ = self._repo.list_staff(
                    session,
                    payload.institution_id,
                    query=payload.query,
                    active_only=payload.active_only,
                    page=1,
                    page_size=50000,
                )
                columns = [
                    ("staff_code", "Kode Staf"),
                    ("nip", "NIP"),
                    ("full_name", "Nama Lengkap"),
                    ("role", "Peran"),
                ]
                export_rows = [
                    {
                        "staff_code": st.staff_code,
                        "nip": st.nip or "",
                        "full_name": st.full_name,
                        "role": st.role,
                    }
                    for st in rows_sf
                ]
            elif payload.kind == "subjects":
                rows_sb = self._repo.list_subjects(
                    session, payload.institution_id, query=payload.query
                )
                columns = [
                    ("code", "Kode Mapel"),
                    ("name", "Nama Mapel"),
                    ("category", "Kategori"),
                ]
                export_rows = [
                    {
                        "code": sb.code,
                        "name": sb.name,
                        "category": sb.category or "",
                    }
                    for sb in rows_sb
                ]
            elif payload.kind == "rooms":
                rows_rm = self._repo.list_rooms(
                    session, payload.institution_id, query=payload.query
                )
                columns = [
                    ("code", "Kode Ruang"),
                    ("name", "Nama Ruang"),
                    ("mode", "Mode"),
                    ("capacity_limit", "Kapasitas"),
                ]
                export_rows = [
                    {
                        "code": rm.code,
                        "name": rm.name,
                        "mode": rm.mode,
                        "capacity_limit": rm.capacity_limit,
                    }
                    for rm in rows_rm
                ]
            else:
                raise ValidationError(f"Ekspor untuk '{payload.kind}' tidak tersedia.")

        xlsx_bytes = build_xlsx_bytes(
            sheet_title=payload.kind.capitalize(),
            columns=columns,
            rows=export_rows,
        )
        filename = f"master_{payload.kind}_{_new_id()[:8]}.xlsx"
        target = self._paths.exports_dir / filename
        atomic_write_bytes(target, xlsx_bytes, temp_dir=self._paths.temp_dir)
        return {
            "filename": filename,
            "relative_path": f"exports/{filename}",
            "row_count": len(export_rows),
            "content_base64": base64.b64encode(xlsx_bytes).decode("ascii"),
        }

    # --- MST-08 Data Quality ---
    def data_quality_report(self, payload: DataQualityPayload) -> dict[str, Any]:
        issues: list[dict[str, Any]] = []
        with session_scope(self._session_factory) as session:
            self._require_institution(session, payload.institution_id)
            students = self._repo.list_all_students(session, payload.institution_id)
            enrollments = self._repo.list_enrollments(
                session, payload.institution_id, year_id=payload.year_id
            )
            enrolled_student_ids = {
                e.student_id for e in enrollments if e.status == "active"
            }

            nisn_seen: dict[str, list[Student]] = {}
            for s in students:
                if s.active and not s.nisn:
                    issues.append(
                        {
                            "id": f"missing-nisn-{s.id}",
                            "severity": "warning",
                            "kind": "missing_nisn",
                            "entity_type": "student",
                            "entity_id": s.id,
                            "message": f"Siswa '{s.full_name}' belum memiliki NISN.",
                            "fix_route": "/master",
                        }
                    )
                if s.nisn:
                    nisn_seen.setdefault(s.nisn, []).append(s)
                if s.active and s.id not in enrolled_student_ids:
                    issues.append(
                        {
                            "id": f"unenrolled-{s.id}",
                            "severity": "warning",
                            "kind": "unenrolled_student",
                            "entity_type": "student",
                            "entity_id": s.id,
                            "message": (
                                f"Siswa aktif '{s.full_name}' belum ditempatkan "
                                "di rombel."
                            ),
                            "fix_route": "/master",
                        }
                    )

            for nisn, group in nisn_seen.items():
                if len(group) > 1:
                    names = ", ".join(st.full_name for st in group)
                    issues.append(
                        {
                            "id": f"dup-nisn-{nisn}",
                            "severity": "error",
                            "kind": "duplicate_nisn",
                            "entity_type": "student",
                            "entity_id": group[0].id,
                            "message": f"NISN '{nisn}' duplikat pada: {names}.",
                            "fix_route": "/master",
                        }
                    )

            classes = self._repo.list_classes(
                session, payload.institution_id, year_id=payload.year_id
            )
            subjects = self._repo.list_subjects(session, payload.institution_id)
            tas = self._repo.list_teaching_assignments(session, payload.institution_id)
            ta_pairs = {(ta.class_id, ta.subject_id) for ta in tas}
            for cls_row in classes:
                for subj in subjects:
                    if (cls_row.id, subj.id) not in ta_pairs:
                        issues.append(
                            {
                                "id": f"ta-gap-{cls_row.id}-{subj.id}",
                                "severity": "warning",
                                "kind": "missing_teaching_assignment",
                                "entity_type": "subject",
                                "entity_id": subj.id,
                                "message": (
                                    f"Belum ada pengampu untuk {subj.name} "
                                    f"di kelas {cls_row.name}."
                                ),
                                "fix_route": "/master",
                            }
                        )

        return {
            "total_issues": len(issues),
            "issues": issues,
        }
