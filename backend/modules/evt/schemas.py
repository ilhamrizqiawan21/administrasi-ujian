"""Pydantic schemas and validators for EVT-01..EVT-07."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

ExamState = Literal["DRAFT", "PREPARATION", "READY", "RUNNING", "COMPLETED", "ARCHIVED"]
ExamMode = Literal["paper", "cbt", "practice", "hybrid"]
NumberSortOrder = Literal["name", "class_name", "nis"]


class ExamListPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    institution_id: str = Field(min_length=1)


class ExamScopedPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    institution_id: str = Field(min_length=1)
    exam_id: str = Field(min_length=1)


class ExamCreatePayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    institution_id: str = Field(min_length=1)
    year_id: str = Field(min_length=1)
    exam_type_id: str = Field(min_length=1)
    title: str = Field(min_length=2, max_length=160)
    semester_label: str = Field(min_length=1, max_length=40)
    mode: ExamMode = "paper"
    starts_on: str = Field(min_length=8, max_length=20)
    ends_on: str = Field(min_length=8, max_length=20)
    selected_class_ids: list[str] = Field(default_factory=list)
    selected_student_ids: list[str] = Field(default_factory=list)
    selected_room_ids: list[str] = Field(default_factory=list)
    selected_subject_ids: list[str] = Field(default_factory=list)

    @field_validator("title", "semester_label")
    @classmethod
    def _clean_text(cls, value: str) -> str:
        clean = value.strip()
        if not clean:
            raise ValueError("Nilai wajib diisi.")
        return clean

    @model_validator(mode="after")
    def _check_dates(self) -> ExamCreatePayload:
        if self.ends_on < self.starts_on:
            raise ValueError("Tanggal selesai tidak boleh sebelum tanggal mulai.")
        return self


class NumberingGeneratePayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    institution_id: str = Field(min_length=1)
    exam_id: str = Field(min_length=1)
    expected_revision: int = Field(ge=1)
    prefix: str = Field(min_length=1, max_length=16)
    separator: str = Field(default="-", max_length=4)
    padding: int = Field(default=4, ge=2, le=8)
    start_seq: int = Field(default=1, ge=1, le=999999)
    sort_by: NumberSortOrder = "name"
    mark_cards_printed: bool = False


class NumberingOverridePayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    institution_id: str = Field(min_length=1)
    exam_id: str = Field(min_length=1)
    participant_id: str = Field(min_length=1)
    expected_revision: int = Field(ge=1)
    participant_number: str = Field(min_length=1, max_length=32)

    @field_validator("participant_number")
    @classmethod
    def _clean_num(cls, value: str) -> str:
        clean = value.strip()
        if not clean:
            raise ValueError("Nomor peserta tidak boleh kosong.")
        return clean


class ExamGroupSavePayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    institution_id: str = Field(min_length=1)
    exam_id: str = Field(min_length=1)
    id: str | None = None
    label: str = Field(min_length=1, max_length=80)
    participant_ids: list[str] = Field(default_factory=list)


class ExamRequirementSavePayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    institution_id: str = Field(min_length=1)
    exam_id: str = Field(min_length=1)
    group_id: str = Field(min_length=1)
    exam_subject_id: str = Field(min_length=1)
    attempt_no: int = Field(default=1, ge=1, le=5)
    duration_min: int = Field(default=90, ge=15, le=480)
    mode: ExamMode = "paper"


class ExamRequirementDeletePayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    institution_id: str = Field(min_length=1)
    exam_id: str = Field(min_length=1)
    requirement_id: str = Field(min_length=1)


class ExamTransitionPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    institution_id: str = Field(min_length=1)
    exam_id: str = Field(min_length=1)
    expected_revision: int = Field(ge=1)
    target_state: ExamState
    reason: str = Field(default="", max_length=300)
    actor: str = Field(default="operator", min_length=1, max_length=80)


class ExamClonePayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    institution_id: str = Field(min_length=1)
    source_exam_id: str = Field(min_length=1)
    title: str = Field(min_length=2, max_length=160)
    year_id: str | None = None
    semester_label: str | None = None
    starts_on: str = Field(min_length=8, max_length=20)
    ends_on: str = Field(min_length=8, max_length=20)
    copy_rooms: bool = True
    copy_subjects: bool = True
    copy_groups_structure: bool = True

    @model_validator(mode="after")
    def _check_dates(self) -> ExamClonePayload:
        if self.ends_on < self.starts_on:
            raise ValueError("Tanggal selesai tidak boleh sebelum tanggal mulai.")
        return self
