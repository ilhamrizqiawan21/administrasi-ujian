"""Pydantic schemas and validators for CFG."""

from __future__ import annotations

import re
from typing import Literal
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

ExamMode = Literal["paper", "cbt", "practice", "hybrid"]
PaperSize = Literal["A4", "F4", "Letter"]
ResetScope = Literal["event", "year", "month", "never"]
ExtensionScope = Literal["student", "staff", "room", "exam"]
ExtensionFieldType = Literal["string", "date", "int", "enum"]


def _validate_timezone(tz: str) -> str:
    clean = tz.strip()
    try:
        ZoneInfo(clean)
    except (ZoneInfoNotFoundError, KeyError) as exc:
        raise ValueError(f"Zona waktu '{clean}' tidak valid.") from exc
    return clean


class InstitutionScopedPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    institution_id: str = Field(min_length=1)


class FirstRunPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=2, max_length=160)
    short_name: str | None = Field(default=None, max_length=40)
    npsn: str | None = Field(default=None, max_length=20)
    nsm: str | None = Field(default=None, max_length=20)
    address: str | None = Field(default=None, max_length=300)
    timezone: str = Field(default="Asia/Jakarta", min_length=1, max_length=64)
    level_preset: str = Field(default="SMP/MTs", min_length=1, max_length=40)
    custom_levels: list[str] = Field(default_factory=list)
    academic_year_label: str = Field(min_length=4, max_length=32)

    @field_validator("name", "academic_year_label")
    @classmethod
    def _strip_required(cls, value: str) -> str:
        clean = value.strip()
        if not clean:
            raise ValueError("Nilai tidak boleh kosong.")
        return clean

    @field_validator("npsn", "nsm")
    @classmethod
    def _validate_numeric_text_id(cls, value: str | None) -> str | None:
        if value is None or value.strip() == "":
            return None
        clean = value.strip()
        if not clean.isdigit():
            raise ValueError("NPSN/NSM hanya boleh berisi angka.")
        return clean

    @field_validator("timezone")
    @classmethod
    def _check_timezone(cls, value: str) -> str:
        return _validate_timezone(value)


class InstitutionSavePayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str | None = None
    expected_revision: int | None = Field(default=None, ge=1)
    name: str = Field(min_length=2, max_length=160)
    short_name: str | None = Field(default=None, max_length=40)
    npsn: str | None = Field(default=None, max_length=20)
    nsm: str | None = Field(default=None, max_length=20)
    address: str | None = Field(default=None, max_length=300)
    timezone: str = Field(default="Asia/Jakarta", min_length=1, max_length=64)

    @field_validator("name")
    @classmethod
    def _strip_name(cls, value: str) -> str:
        clean = value.strip()
        if len(clean) < 2:
            raise ValueError("Nama lembaga minimal 2 karakter.")
        return clean

    @field_validator("npsn", "nsm")
    @classmethod
    def _check_id(cls, value: str | None) -> str | None:
        if value is None or value.strip() == "":
            return None
        clean = value.strip()
        if not clean.isdigit():
            raise ValueError("NPSN/NSM harus berupa angka teks.")
        return clean

    @field_validator("timezone")
    @classmethod
    def _check_tz(cls, value: str) -> str:
        return _validate_timezone(value)


class LogoUploadPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    institution_id: str = Field(min_length=1)
    expected_revision: int = Field(ge=1)
    filename: str = Field(min_length=1, max_length=120)
    content_base64: str = Field(min_length=1)


class LevelApplyPresetPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    institution_id: str = Field(min_length=1)
    preset_name: str = Field(min_length=1, max_length=40)


class LevelSavePayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    institution_id: str = Field(min_length=1)
    id: str | None = None
    expected_revision: int | None = Field(default=None, ge=1)
    label: str = Field(min_length=1, max_length=40)
    sort_order: int = Field(ge=1, le=999)

    @field_validator("label")
    @classmethod
    def _clean_label(cls, value: str) -> str:
        clean = value.strip()
        if not clean:
            raise ValueError("Label tingkatan wajib diisi.")
        return clean


class ScopedDeletePayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    institution_id: str = Field(min_length=1)
    id: str = Field(min_length=1)


class AcademicYearSavePayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    institution_id: str = Field(min_length=1)
    id: str | None = None
    expected_revision: int | None = Field(default=None, ge=1)
    label: str = Field(min_length=4, max_length=32)
    starts_on: str | None = None
    ends_on: str | None = None
    is_active: bool = True

    @model_validator(mode="after")
    def _check_dates(self) -> AcademicYearSavePayload:
        if self.starts_on and self.ends_on and self.ends_on < self.starts_on:
            raise ValueError("Tanggal selesai tidak boleh sebelum tanggal mulai.")
        return self


class ExamTypeTerminology(BaseModel):
    model_config = ConfigDict(extra="forbid")

    participant_term: str = Field(default="Peserta", min_length=1, max_length=40)
    room_term: str = Field(default="Ruang Ujian", min_length=1, max_length=40)
    invigilator_term: str = Field(default="Pengawas", min_length=1, max_length=40)


class ExamTypeSavePayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    institution_id: str = Field(min_length=1)
    id: str | None = None
    expected_revision: int | None = Field(default=None, ge=1)
    code: str = Field(min_length=2, max_length=24)
    label: str = Field(min_length=2, max_length=80)
    mode_default: ExamMode = "paper"
    terminology: ExamTypeTerminology = Field(default_factory=ExamTypeTerminology)

    @field_validator("code")
    @classmethod
    def _normalize_code(cls, value: str) -> str:
        clean = value.strip().upper()
        if not re.fullmatch(r"[A-Z0-9_-]{2,24}", clean):
            raise ValueError("Kode jenis ujian hanya boleh huruf, angka, '-' atau '_'.")
        return clean


class ParticipantNumberPolicy(BaseModel):
    model_config = ConfigDict(extra="forbid")

    prefix: str = Field(min_length=1, max_length=16)
    separator: str = Field(default="-", max_length=4)
    padding: int = Field(ge=2, le=8)
    start_seq: int = Field(ge=1, le=999999)
    reset_scope: ResetScope = "event"

    @field_validator("prefix")
    @classmethod
    def _clean_prefix(cls, value: str) -> str:
        clean = value.strip()
        if not clean:
            raise ValueError("Prefix nomor peserta tidak boleh kosong.")
        return clean


class DocumentNumberPolicy(BaseModel):
    model_config = ConfigDict(extra="forbid")

    pattern: str = Field(min_length=5, max_length=80)
    padding: int = Field(ge=2, le=6)
    reset_scope: ResetScope = "year"

    @field_validator("pattern")
    @classmethod
    def _must_contain_seq(cls, value: str) -> str:
        if "{seq}" not in value:
            raise ValueError("Pola nomor surat wajib mengandung '{seq}'.")
        return value.strip()


class NumberPolicyConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    participant: ParticipantNumberPolicy
    document: DocumentNumberPolicy


class NumberPolicySavePayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    institution_id: str = Field(min_length=1)
    expected_revision: int | None = Field(default=None, ge=1)
    policy: NumberPolicyConfig


class NumberPolicyPreviewPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    policy: NumberPolicyConfig
    series: str = ""
    exam_code: str = ""
    year: str = ""
    count: int = Field(default=3, ge=1, le=10)


class ExtensionFieldDef(BaseModel):
    model_config = ConfigDict(extra="forbid")

    key: str = Field(min_length=2, max_length=40)
    label: str = Field(min_length=1, max_length=60)
    scope: ExtensionScope
    field_type: ExtensionFieldType
    required: bool = False
    enum_options: list[str] = Field(default_factory=list)

    @field_validator("key")
    @classmethod
    def _check_key(cls, value: str) -> str:
        clean = value.strip()
        if not re.fullmatch(r"[a-z][a-z0-9_]{1,39}", clean):
            raise ValueError(
                "Key kolom ekstra harus huruf kecil/angka/underscore diawali huruf."
            )
        return clean

    @model_validator(mode="after")
    def _check_enum(self) -> ExtensionFieldDef:
        if self.field_type == "enum" and len(self.enum_options) < 1:
            raise ValueError("Kolom bertipe enum wajib memiliki minimal 1 opsi.")
        return self


class TypedSettingsConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    default_paper_size: PaperSize = "A4"
    solver_time_limit_sec: int = Field(default=60, ge=5, le=300)
    allow_part_time_weights: bool = True
    extension_fields: list[ExtensionFieldDef] = Field(default_factory=list)

    @model_validator(mode="after")
    def _unique_extension_keys(self) -> TypedSettingsConfig:
        seen: set[tuple[str, str]] = set()
        for field_def in self.extension_fields:
            pair = (field_def.scope, field_def.key)
            if pair in seen:
                raise ValueError(
                    f"Key kolom ekstra '{field_def.key}' duplikat pada scope "
                    f"'{field_def.scope}'."
                )
            seen.add(pair)
        return self


class SettingsUpdatePayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    institution_id: str = Field(min_length=1)
    expected_revision: int = Field(ge=1)
    settings: TypedSettingsConfig


class SettingsResetPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    institution_id: str = Field(min_length=1)
    expected_revision: int = Field(ge=1)
