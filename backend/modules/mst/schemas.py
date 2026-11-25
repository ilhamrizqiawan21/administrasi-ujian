"""Pydantic schemas and validators for MST-01..MST-08."""

from __future__ import annotations

import re
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

StaffRole = Literal["teacher", "tu", "external_invigilator"]
RoomMode = Literal["paper", "cbt", "practice", "hybrid"]
MasterKind = Literal["students", "staff", "classes", "subjects", "rooms"]
DuplicatePolicy = Literal["skip", "update", "fail"]


def _clean_text_id(value: str | None) -> str | None:
    if value is None:
        return None
    clean = value.strip()
    return clean if clean != "" else None


class MasterListPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    institution_id: str = Field(min_length=1)
    query: str = Field(default="", max_length=100)
    year_id: str | None = None
    active_only: bool = False
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=50, ge=1, le=200)


class ScopedEntityDeletePayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    institution_id: str = Field(min_length=1)
    id: str = Field(min_length=1)


class StudentAccommodation(BaseModel):
    model_config = ConfigDict(extra="forbid")

    accessible_seat: bool = False
    extra_time_min: int = Field(default=0, ge=0, le=180)
    notes: str = Field(default="", max_length=200)


class StudentSavePayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    institution_id: str = Field(min_length=1)
    id: str | None = None
    expected_revision: int | None = Field(default=None, ge=1)
    nis: str | None = Field(default=None, max_length=32)
    nisn: str | None = Field(default=None, max_length=32)
    full_name: str = Field(min_length=2, max_length=160)
    gender: Literal["L", "P", ""] | None = None
    accommodation: StudentAccommodation = Field(default_factory=StudentAccommodation)
    active: bool = True

    @field_validator("nis", "nisn")
    @classmethod
    def _preserve_text_id(cls, value: str | None) -> str | None:
        clean = _clean_text_id(value)
        if clean is not None and not re.fullmatch(r"[A-Za-z0-9._-]+", clean):
            raise ValueError(
                "Nomor identitas hanya boleh berisi huruf, angka, '-', '_'."
            )
        return clean

    @field_validator("full_name")
    @classmethod
    def _clean_name(cls, value: str) -> str:
        clean = value.strip()
        if len(clean) < 2:
            raise ValueError("Nama siswa minimal 2 karakter.")
        return clean


class StaffSavePayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    institution_id: str = Field(min_length=1)
    id: str | None = None
    expected_revision: int | None = Field(default=None, ge=1)
    staff_code: str = Field(min_length=1, max_length=32)
    nip: str | None = Field(default=None, max_length=32)
    full_name: str = Field(min_length=2, max_length=160)
    role: StaffRole = "teacher"
    active: bool = True

    @field_validator("staff_code")
    @classmethod
    def _clean_code(cls, value: str) -> str:
        clean = value.strip().upper()
        if not clean:
            raise ValueError("Kode staf wajib diisi.")
        return clean

    @field_validator("nip")
    @classmethod
    def _clean_nip(cls, value: str | None) -> str | None:
        return _clean_text_id(value)

    @field_validator("full_name")
    @classmethod
    def _clean_name(cls, value: str) -> str:
        clean = value.strip()
        if len(clean) < 2:
            raise ValueError("Nama staf minimal 2 karakter.")
        return clean


class ClassSavePayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    institution_id: str = Field(min_length=1)
    id: str | None = None
    expected_revision: int | None = Field(default=None, ge=1)
    year_id: str = Field(min_length=1)
    level_id: str = Field(min_length=1)
    name: str = Field(min_length=1, max_length=60)
    program: str | None = Field(default=None, max_length=60)

    @field_validator("name")
    @classmethod
    def _clean_name(cls, value: str) -> str:
        clean = value.strip()
        if not clean:
            raise ValueError("Nama rombel wajib diisi.")
        return clean


class EnrollmentSavePayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    institution_id: str = Field(min_length=1)
    student_id: str = Field(min_length=1)
    class_id: str = Field(min_length=1)
    year_id: str = Field(min_length=1)
    status: Literal["active", "inactive", "moved"] = "active"


class SubjectSavePayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    institution_id: str = Field(min_length=1)
    id: str | None = None
    expected_revision: int | None = Field(default=None, ge=1)
    code: str = Field(min_length=1, max_length=24)
    name: str = Field(min_length=2, max_length=120)
    category: str | None = Field(default=None, max_length=60)

    @field_validator("code")
    @classmethod
    def _clean_code(cls, value: str) -> str:
        clean = value.strip().upper()
        if not clean:
            raise ValueError("Kode mata pelajaran wajib diisi.")
        return clean


class TeachingAssignmentSavePayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    institution_id: str = Field(min_length=1)
    staff_id: str = Field(min_length=1)
    class_id: str = Field(min_length=1)
    subject_id: str = Field(min_length=1)


class RoomLayoutConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    rows: int = Field(default=4, ge=1, le=30)
    cols: int = Field(default=5, ge=1, le=30)
    seats_per_desk: int = Field(default=1, ge=1, le=2)
    disabled_cells: list[str] = Field(default_factory=list)
    accessible_seats: list[str] = Field(default_factory=list)
    board_position: Literal["top", "bottom"] = "top"

    @property
    def total_slots(self) -> int:
        return self.rows * self.cols * self.seats_per_desk

    @property
    def enabled_seat_count(self) -> int:
        disabled = set(self.disabled_cells)
        count = 0
        for r in range(1, self.rows + 1):
            for c in range(1, self.cols + 1):
                for s in range(1, self.seats_per_desk + 1):
                    key = f"R{r}C{c}S{s}"
                    cell_key = f"R{r}C{c}"
                    if key not in disabled and cell_key not in disabled:
                        count += 1
        return count


class RoomSavePayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    institution_id: str = Field(min_length=1)
    id: str | None = None
    expected_revision: int | None = Field(default=None, ge=1)
    code: str = Field(min_length=1, max_length=24)
    name: str = Field(min_length=2, max_length=120)
    mode: RoomMode = "paper"
    capacity_limit: int = Field(ge=1, le=1000)
    layout: RoomLayoutConfig = Field(default_factory=RoomLayoutConfig)

    @field_validator("code")
    @classmethod
    def _clean_code(cls, value: str) -> str:
        clean = value.strip().upper()
        if not clean:
            raise ValueError("Kode ruang wajib diisi.")
        return clean

    @model_validator(mode="after")
    def _check_capacity(self) -> RoomSavePayload:
        if self.capacity_limit > self.layout.enabled_seat_count:
            raise ValueError(
                f"Batas kapasitas ({self.capacity_limit}) melebihi jumlah kursi aktif "
                f"({self.layout.enabled_seat_count})."
            )
        return self


class ImportPreviewPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    institution_id: str = Field(min_length=1)
    kind: MasterKind
    filename: str = Field(min_length=1, max_length=160)
    content_base64: str = Field(min_length=1)
    mapping: dict[str, str] = Field(default_factory=dict)


class ImportCommitPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    institution_id: str = Field(min_length=1)
    preview_id: str = Field(min_length=1)
    duplicate_policy: DuplicatePolicy = "skip"
    skip_invalid_rows: bool = False


class ExportMasterPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    institution_id: str = Field(min_length=1)
    kind: MasterKind
    query: str = Field(default="", max_length=100)
    active_only: bool = False


class DataQualityPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    institution_id: str = Field(min_length=1)
    year_id: str | None = None


def build_room_stats(
    room_layout: RoomLayoutConfig, capacity_limit: int
) -> dict[str, Any]:
    enabled = room_layout.enabled_seat_count
    return {
        "enabled_seats": enabled,
        "effective_capacity": min(enabled, capacity_limit),
    }
