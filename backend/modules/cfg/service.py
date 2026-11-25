"""Transactional service layer for CFG-01..CFG-06."""

from __future__ import annotations

import base64
import binascii
import hashlib
import io
import json
import uuid
from datetime import UTC, datetime
from typing import Any

from PIL import Image, UnidentifiedImageError
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker

from backend.core.db import session_scope
from backend.core.errors import AppError, ConflictError, NotFoundError, ValidationError
from backend.core.jobs import atomic_write_bytes
from backend.core.paths import WorkspacePaths
from backend.modules.cfg.models import (
    AcademicYear,
    Asset,
    ExamType,
    Institution,
    Level,
    Setting,
)
from backend.modules.cfg.presets import (
    DEFAULT_EXAM_TYPES,
    DEFAULT_NUMBER_POLICIES,
    DEFAULT_TYPED_SETTINGS,
    LEVEL_PRESETS,
)
from backend.modules.cfg.repository import CfgRepository
from backend.modules.cfg.schemas import (
    AcademicYearSavePayload,
    ExamTypeSavePayload,
    FirstRunPayload,
    InstitutionSavePayload,
    LevelApplyPresetPayload,
    LevelSavePayload,
    LogoUploadPayload,
    NumberPolicyConfig,
    NumberPolicyPreviewPayload,
    NumberPolicySavePayload,
    ScopedDeletePayload,
    SettingsResetPayload,
    SettingsUpdatePayload,
    TypedSettingsConfig,
)

_MAX_LOGO_BYTES = 2 * 1024 * 1024
_ALLOWED_IMAGE_FORMATS: dict[str, tuple[str, str]] = {
    "PNG": ("image/png", ".png"),
    "JPEG": ("image/jpeg", ".jpg"),
    "WEBP": ("image/webp", ".webp"),
}


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


def _serialize_institution(
    inst: Institution, asset: Asset | None = None
) -> dict[str, Any]:
    return {
        "id": inst.id,
        "name": inst.name,
        "short_name": inst.short_name,
        "npsn": inst.npsn,
        "nsm": inst.nsm,
        "address": inst.address,
        "timezone": inst.timezone,
        "logo_asset_id": inst.logo_asset_id,
        "logo_relative_path": asset.relative_path if asset else None,
        "revision": inst.revision,
        "created_at": inst.created_at,
        "updated_at": inst.updated_at,
    }


def _serialize_year(year: AcademicYear) -> dict[str, Any]:
    return {
        "id": year.id,
        "institution_id": year.institution_id,
        "label": year.label,
        "starts_on": year.starts_on,
        "ends_on": year.ends_on,
        "is_active": bool(year.is_active),
        "revision": year.revision,
    }


def _serialize_level(level: Level) -> dict[str, Any]:
    return {
        "id": level.id,
        "institution_id": level.institution_id,
        "label": level.label,
        "sort_order": level.sort_order,
        "revision": level.revision,
    }


def _serialize_exam_type(et: ExamType) -> dict[str, Any]:
    return {
        "id": et.id,
        "institution_id": et.institution_id,
        "code": et.code,
        "label": et.label,
        "mode_default": et.mode_default,
        "terminology": json.loads(et.terminology_json),
        "revision": et.revision,
    }


def validate_unique_numbers(numbers: list[str]) -> None:
    """Reject duplicate generated or manual identifier strings."""
    seen: set[str] = set()
    duplicates: list[str] = []
    for num in numbers:
        if num in seen:
            duplicates.append(num)
        seen.add(num)
    if duplicates:
        raise ConflictError(
            f"Nomor duplikat terdeteksi: {', '.join(sorted(set(duplicates)))}."
        )


def preview_numbers(payload: NumberPolicyPreviewPayload) -> dict[str, Any]:
    """Build deterministic number previews without guessing missing placeholders."""
    policy = payload.policy
    part_samples: list[str] = []
    for idx in range(payload.count):
        seq_val = policy.participant.start_seq + idx
        seq_str = str(seq_val).zfill(policy.participant.padding)
        part_samples.append(
            f"{policy.participant.prefix}{policy.participant.separator}{seq_str}"
        )
    validate_unique_numbers(part_samples)

    pattern = policy.document.pattern
    required_tokens = {
        token for token in ("series", "exam_code", "year") if f"{{{token}}}" in pattern
    }
    provided = {
        "series": payload.series.strip(),
        "exam_code": payload.exam_code.strip(),
        "year": payload.year.strip(),
    }
    missing = [tok for tok in sorted(required_tokens) if not provided[tok]]
    if missing:
        missing_text = ", ".join(missing)
        raise ValidationError(
            f"Nilai placeholder belum diisi (tidak boleh ditebak): {missing_text}.",
            field_errors={tok: "Wajib diisi untuk pratinjau" for tok in missing},
        )

    doc_samples: list[str] = []
    for idx in range(payload.count):
        seq_str = str(idx + 1).zfill(policy.document.padding)
        doc_samples.append(
            pattern.format(
                seq=seq_str,
                series=provided["series"],
                exam_code=provided["exam_code"],
                year=provided["year"],
            )
        )
    validate_unique_numbers(doc_samples)

    return {
        "participant_samples": part_samples,
        "document_samples": doc_samples,
    }


class CfgService:
    """Application service for CFG-01..CFG-06."""

    def __init__(
        self,
        session_factory: sessionmaker[Session],
        paths: WorkspacePaths,
    ) -> None:
        self._session_factory = session_factory
        self._paths = paths
        self._repo = CfgRepository()

    def get_onboarding_status(self) -> dict[str, Any]:
        with session_scope(self._session_factory) as session:
            institutions = self._repo.list_institutions(session)
            items = [
                _serialize_institution(
                    inst,
                    self._repo.get_asset(session, inst.id, inst.logo_asset_id)
                    if inst.logo_asset_id
                    else None,
                )
                for inst in institutions
            ]
            return {
                "needs_onboarding": len(items) == 0,
                "workspace_root": str(self._paths.root),
                "institutions": items,
                "level_presets": LEVEL_PRESETS,
            }

    def first_run_setup(self, payload: FirstRunPayload) -> dict[str, Any]:
        if payload.level_preset not in LEVEL_PRESETS:
            raise ValidationError(
                f"Preset jenjang '{payload.level_preset}' tidak dikenal.",
                field_errors={"level_preset": "Preset tidak valid"},
            )

        preset_labels = list(LEVEL_PRESETS[payload.level_preset])
        labels = [lbl.strip() for lbl in payload.custom_levels if lbl.strip()]
        if not labels:
            labels = preset_labels
        if not labels:
            raise ValidationError(
                "Minimal satu tingkatan/kelas wajib ditentukan.",
                field_errors={
                    "custom_levels": "Tambahkan minimal satu label tingkatan"
                },
            )

        now = _now_iso()
        inst_id = _new_id()
        with session_scope(self._session_factory) as session:
            inst = Institution(
                id=inst_id,
                name=payload.name,
                short_name=payload.short_name.strip() if payload.short_name else None,
                npsn=payload.npsn,
                nsm=payload.nsm,
                address=payload.address.strip() if payload.address else None,
                timezone=payload.timezone,
                revision=1,
                created_at=now,
                updated_at=now,
            )
            session.add(inst)
            session.flush()

            year = AcademicYear(
                id=_new_id(),
                institution_id=inst_id,
                label=payload.academic_year_label,
                is_active=1,
                revision=1,
                created_at=now,
                updated_at=now,
            )
            session.add(year)

            seen_levels: set[str] = set()
            for idx, lbl in enumerate(labels, start=1):
                if lbl in seen_levels:
                    raise ValidationError(f"Label tingkatan '{lbl}' duplikat.")
                seen_levels.add(lbl)
                session.add(
                    Level(
                        id=_new_id(),
                        institution_id=inst_id,
                        label=lbl,
                        sort_order=idx,
                        revision=1,
                        created_at=now,
                        updated_at=now,
                    )
                )

            for item in DEFAULT_EXAM_TYPES:
                session.add(
                    ExamType(
                        id=_new_id(),
                        institution_id=inst_id,
                        code=str(item["code"]),
                        label=str(item["label"]),
                        mode_default=str(item["mode_default"]),
                        terminology_json=json.dumps(item["terminology"]),
                        revision=1,
                        created_at=now,
                        updated_at=now,
                    )
                )

            session.add(
                Setting(
                    id=_new_id(),
                    institution_id=inst_id,
                    key="number_policies",
                    value_json=json.dumps(DEFAULT_NUMBER_POLICIES),
                    revision=1,
                    created_at=now,
                    updated_at=now,
                )
            )
            session.add(
                Setting(
                    id=_new_id(),
                    institution_id=inst_id,
                    key="typed_settings",
                    value_json=json.dumps(DEFAULT_TYPED_SETTINGS),
                    revision=1,
                    created_at=now,
                    updated_at=now,
                )
            )

            return {"institution": _serialize_institution(inst)}

    def list_institutions(self) -> dict[str, Any]:
        with session_scope(self._session_factory) as session:
            institutions = self._repo.list_institutions(session)
            return {
                "items": [
                    _serialize_institution(
                        inst,
                        self._repo.get_asset(session, inst.id, inst.logo_asset_id)
                        if inst.logo_asset_id
                        else None,
                    )
                    for inst in institutions
                ]
            }

    def save_institution(self, payload: InstitutionSavePayload) -> dict[str, Any]:
        now = _now_iso()
        with session_scope(self._session_factory) as session:
            if payload.id is None:
                inst = Institution(
                    id=_new_id(),
                    name=payload.name,
                    short_name=payload.short_name.strip()
                    if payload.short_name
                    else None,
                    npsn=payload.npsn,
                    nsm=payload.nsm,
                    address=payload.address.strip() if payload.address else None,
                    timezone=payload.timezone,
                    revision=1,
                    created_at=now,
                    updated_at=now,
                )
                session.add(inst)
                session.flush()
                return {"institution": _serialize_institution(inst)}

            existing_inst = self._repo.get_institution(session, payload.id)
            if existing_inst is None:
                raise NotFoundError("Lembaga tidak ditemukan.")
            _check_revision(existing_inst.revision, payload.expected_revision)

            existing_inst.name = payload.name
            existing_inst.short_name = (
                payload.short_name.strip() if payload.short_name else None
            )
            existing_inst.npsn = payload.npsn
            existing_inst.nsm = payload.nsm
            existing_inst.address = payload.address.strip() if payload.address else None
            existing_inst.timezone = payload.timezone
            existing_inst.revision += 1
            existing_inst.updated_at = now
            asset = (
                self._repo.get_asset(
                    session, existing_inst.id, existing_inst.logo_asset_id
                )
                if existing_inst.logo_asset_id
                else None
            )
            return {"institution": _serialize_institution(existing_inst, asset)}

    def upload_logo(self, payload: LogoUploadPayload) -> dict[str, Any]:
        try:
            raw_bytes = base64.b64decode(payload.content_base64, validate=True)
        except (binascii.Error, ValueError) as exc:
            raise AppError(
                "FILE_INVALID", "Format base64 berkas logo tidak valid."
            ) from exc

        if len(raw_bytes) == 0 or len(raw_bytes) > _MAX_LOGO_BYTES:
            raise AppError(
                "FILE_INVALID",
                "Ukuran berkas logo harus lebih dari 0 dan maksimal 2 MB.",
            )

        try:
            with Image.open(io.BytesIO(raw_bytes)) as img:
                img_format = (img.format or "").upper()
                if img_format not in _ALLOWED_IMAGE_FORMATS:
                    raise AppError(
                        "FILE_INVALID",
                        "Format logo harus berupa PNG, JPEG, atau WEBP.",
                    )
                img.verify()
        except AppError:
            raise
        except (UnidentifiedImageError, OSError, SyntaxError) as exc:
            raise AppError(
                "FILE_INVALID",
                "Berkas logo rusak atau bukan gambar yang valid.",
            ) from exc

        mime, ext = _ALLOWED_IMAGE_FORMATS[img_format]
        sha256_hex = hashlib.sha256(raw_bytes).hexdigest()
        asset_id = _new_id()
        rel_path = f"{asset_id}{ext}"
        target_path = self._paths.assets_dir / rel_path

        now = _now_iso()
        with session_scope(self._session_factory) as session:
            inst = self._repo.get_institution(session, payload.institution_id)
            if inst is None:
                raise NotFoundError("Lembaga tidak ditemukan.")
            _check_revision(inst.revision, payload.expected_revision)

            atomic_write_bytes(target_path, raw_bytes, temp_dir=self._paths.temp_dir)
            asset = Asset(
                id=asset_id,
                institution_id=inst.id,
                relative_path=rel_path,
                sha256=sha256_hex,
                mime=mime,
                byte_size=len(raw_bytes),
                purpose="institution_logo",
                revision=1,
                created_at=now,
                updated_at=now,
            )
            session.add(asset)
            session.flush()
            inst.logo_asset_id = asset.id
            inst.revision += 1
            inst.updated_at = now
            return {"institution": _serialize_institution(inst, asset)}

    def list_years(self, institution_id: str) -> dict[str, Any]:
        with session_scope(self._session_factory) as session:
            self._require_institution(session, institution_id)
            years = self._repo.list_years(session, institution_id)
            return {"items": [_serialize_year(y) for y in years]}

    def save_year(self, payload: AcademicYearSavePayload) -> dict[str, Any]:
        now = _now_iso()
        with session_scope(self._session_factory) as session:
            self._require_institution(session, payload.institution_id)
            try:
                if payload.id is None:
                    year = AcademicYear(
                        id=_new_id(),
                        institution_id=payload.institution_id,
                        label=payload.label.strip(),
                        starts_on=payload.starts_on,
                        ends_on=payload.ends_on,
                        is_active=1 if payload.is_active else 0,
                        revision=1,
                        created_at=now,
                        updated_at=now,
                    )
                    session.add(year)
                    session.flush()
                    return {"year": _serialize_year(year)}

                existing_year = self._repo.get_year(
                    session, payload.institution_id, payload.id
                )
                if existing_year is None:
                    raise NotFoundError("Tahun ajaran tidak ditemukan.")
                _check_revision(existing_year.revision, payload.expected_revision)
                existing_year.label = payload.label.strip()
                existing_year.starts_on = payload.starts_on
                existing_year.ends_on = payload.ends_on
                existing_year.is_active = 1 if payload.is_active else 0
                existing_year.revision += 1
                existing_year.updated_at = now
                session.flush()
                return {"year": _serialize_year(existing_year)}
            except IntegrityError as exc:
                raise ConflictError(
                    "Label tahun ajaran sudah ada di lembaga ini."
                ) from exc

    def list_levels(self, institution_id: str) -> dict[str, Any]:
        with session_scope(self._session_factory) as session:
            self._require_institution(session, institution_id)
            levels = self._repo.list_levels(session, institution_id)
            return {
                "items": [_serialize_level(lvl) for lvl in levels],
                "presets": LEVEL_PRESETS,
            }

    def apply_level_preset(self, payload: LevelApplyPresetPayload) -> dict[str, Any]:
        if payload.preset_name not in LEVEL_PRESETS:
            raise ValidationError(f"Preset '{payload.preset_name}' tidak ditemukan.")
        labels = LEVEL_PRESETS[payload.preset_name]
        if not labels:
            raise ValidationError("Preset Kustom tidak memiliki daftar otomatis.")

        now = _now_iso()
        with session_scope(self._session_factory) as session:
            self._require_institution(session, payload.institution_id)
            existing = {
                lvl.label: lvl
                for lvl in self._repo.list_levels(session, payload.institution_id)
            }
            next_order = (
                max((lvl.sort_order for lvl in existing.values()), default=0) + 1
            )
            for lbl in labels:
                if lbl not in existing:
                    session.add(
                        Level(
                            id=_new_id(),
                            institution_id=payload.institution_id,
                            label=lbl,
                            sort_order=next_order,
                            revision=1,
                            created_at=now,
                            updated_at=now,
                        )
                    )
                    next_order += 1
            session.flush()
            return {
                "items": [
                    _serialize_level(lvl)
                    for lvl in self._repo.list_levels(session, payload.institution_id)
                ]
            }

    def save_level(self, payload: LevelSavePayload) -> dict[str, Any]:
        now = _now_iso()
        with session_scope(self._session_factory) as session:
            self._require_institution(session, payload.institution_id)
            try:
                if payload.id is None:
                    lvl = Level(
                        id=_new_id(),
                        institution_id=payload.institution_id,
                        label=payload.label,
                        sort_order=payload.sort_order,
                        revision=1,
                        created_at=now,
                        updated_at=now,
                    )
                    session.add(lvl)
                    session.flush()
                    return {"level": _serialize_level(lvl)}

                existing_lvl = self._repo.get_level(
                    session, payload.institution_id, payload.id
                )
                if existing_lvl is None:
                    raise NotFoundError("Tingkatan tidak ditemukan.")
                _check_revision(existing_lvl.revision, payload.expected_revision)
                existing_lvl.label = payload.label
                existing_lvl.sort_order = payload.sort_order
                existing_lvl.revision += 1
                existing_lvl.updated_at = now
                session.flush()
                return {"level": _serialize_level(existing_lvl)}
            except IntegrityError as exc:
                raise ConflictError("Label tingkatan sudah terdaftar.") from exc

    def delete_level(self, payload: ScopedDeletePayload) -> dict[str, Any]:
        with session_scope(self._session_factory) as session:
            lvl = self._repo.get_level(session, payload.institution_id, payload.id)
            if lvl is None:
                raise NotFoundError("Tingkatan tidak ditemukan.")
            session.delete(lvl)
            return {"deleted": True, "id": payload.id}

    def list_exam_types(self, institution_id: str) -> dict[str, Any]:
        with session_scope(self._session_factory) as session:
            self._require_institution(session, institution_id)
            items = self._repo.list_exam_types(session, institution_id)
            return {"items": [_serialize_exam_type(et) for et in items]}

    def save_exam_type(self, payload: ExamTypeSavePayload) -> dict[str, Any]:
        now = _now_iso()
        with session_scope(self._session_factory) as session:
            self._require_institution(session, payload.institution_id)
            try:
                if payload.id is None:
                    et = ExamType(
                        id=_new_id(),
                        institution_id=payload.institution_id,
                        code=payload.code,
                        label=payload.label.strip(),
                        mode_default=payload.mode_default,
                        terminology_json=payload.terminology.model_dump_json(),
                        revision=1,
                        created_at=now,
                        updated_at=now,
                    )
                    session.add(et)
                    session.flush()
                    return {"exam_type": _serialize_exam_type(et)}

                existing_et = self._repo.get_exam_type(
                    session, payload.institution_id, payload.id
                )
                if existing_et is None:
                    raise NotFoundError("Jenis ujian tidak ditemukan.")
                _check_revision(existing_et.revision, payload.expected_revision)
                existing_et.code = payload.code
                existing_et.label = payload.label.strip()
                existing_et.mode_default = payload.mode_default
                existing_et.terminology_json = payload.terminology.model_dump_json()
                existing_et.revision += 1
                existing_et.updated_at = now
                session.flush()
                return {"exam_type": _serialize_exam_type(existing_et)}
            except IntegrityError as exc:
                raise ConflictError("Kode jenis ujian sudah terdaftar.") from exc

    def delete_exam_type(self, payload: ScopedDeletePayload) -> dict[str, Any]:
        with session_scope(self._session_factory) as session:
            et = self._repo.get_exam_type(session, payload.institution_id, payload.id)
            if et is None:
                raise NotFoundError("Jenis ujian tidak ditemukan.")
            session.delete(et)
            return {"deleted": True, "id": payload.id}

    def get_number_policy(self, institution_id: str) -> dict[str, Any]:
        with session_scope(self._session_factory) as session:
            self._require_institution(session, institution_id)
            setting = self._repo.get_setting(session, institution_id, "number_policies")
            if setting is None:
                return {"policy": DEFAULT_NUMBER_POLICIES, "revision": 0}
            return {
                "policy": json.loads(setting.value_json),
                "revision": setting.revision,
            }

    def save_number_policy(self, payload: NumberPolicySavePayload) -> dict[str, Any]:
        now = _now_iso()
        with session_scope(self._session_factory) as session:
            self._require_institution(session, payload.institution_id)
            setting = self._repo.get_setting(
                session, payload.institution_id, "number_policies"
            )
            policy_json = payload.policy.model_dump_json()
            if setting is None:
                setting = Setting(
                    id=_new_id(),
                    institution_id=payload.institution_id,
                    key="number_policies",
                    value_json=policy_json,
                    revision=1,
                    created_at=now,
                    updated_at=now,
                )
                session.add(setting)
                session.flush()
            else:
                _check_revision(setting.revision, payload.expected_revision)
                setting.value_json = policy_json
                setting.revision += 1
                setting.updated_at = now
                session.flush()
            return {
                "policy": NumberPolicyConfig.model_validate_json(
                    setting.value_json
                ).model_dump(),
                "revision": setting.revision,
            }

    def get_settings(self, institution_id: str) -> dict[str, Any]:
        with session_scope(self._session_factory) as session:
            self._require_institution(session, institution_id)
            setting = self._repo.get_setting(session, institution_id, "typed_settings")
            if setting is None:
                return {"settings": DEFAULT_TYPED_SETTINGS, "revision": 0}
            return {
                "settings": json.loads(setting.value_json),
                "revision": setting.revision,
            }

    def update_settings(self, payload: SettingsUpdatePayload) -> dict[str, Any]:
        now = _now_iso()
        with session_scope(self._session_factory) as session:
            self._require_institution(session, payload.institution_id)
            setting = self._repo.get_setting(
                session, payload.institution_id, "typed_settings"
            )
            if setting is None:
                raise NotFoundError("Pengaturan lembaga belum diinisialisasi.")
            _check_revision(setting.revision, payload.expected_revision)
            setting.value_json = payload.settings.model_dump_json()
            setting.revision += 1
            setting.updated_at = now
            session.flush()
            return {
                "settings": TypedSettingsConfig.model_validate_json(
                    setting.value_json
                ).model_dump(),
                "revision": setting.revision,
            }

    def reset_settings(self, payload: SettingsResetPayload) -> dict[str, Any]:
        now = _now_iso()
        with session_scope(self._session_factory) as session:
            self._require_institution(session, payload.institution_id)
            setting = self._repo.get_setting(
                session, payload.institution_id, "typed_settings"
            )
            if setting is None:
                raise NotFoundError("Pengaturan lembaga belum diinisialisasi.")
            _check_revision(setting.revision, payload.expected_revision)
            setting.value_json = json.dumps(DEFAULT_TYPED_SETTINGS)
            setting.revision += 1
            setting.updated_at = now
            session.flush()
            return {
                "settings": DEFAULT_TYPED_SETTINGS,
                "revision": setting.revision,
            }

    def _require_institution(
        self, session: Session, institution_id: str
    ) -> Institution:
        inst = self._repo.get_institution(session, institution_id)
        if inst is None:
            raise NotFoundError("Lembaga tidak ditemukan.")
        return inst
