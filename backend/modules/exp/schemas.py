"""Pydantic schemas for EXP-01..EXP-06."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

ReviewState = Literal["received", "revision", "valid", "ready"]


class ExpScopedPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    institution_id: str = Field(min_length=1)
    exam_id: str = Field(min_length=1)


class MatrixGeneratePayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    institution_id: str = Field(min_length=1)
    exam_id: str = Field(min_length=1)
    item_types: list[str] = Field(
        default_factory=lambda: ["kisi_kisi", "naskah", "kunci", "kartu_soal", "nilai"]
    )
    due_date: str = Field(default="", max_length=32)


class SubmissionItemSavePayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    institution_id: str = Field(min_length=1)
    exam_id: str = Field(min_length=1)
    subject_label: str = Field(min_length=1, max_length=120)
    class_label: str = Field(min_length=1, max_length=120)
    type_code: str = Field(min_length=1, max_length=64)
    owner_id: str | None = None
    due_date: str = Field(default="", max_length=32)


class SubmissionReceivePayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    institution_id: str = Field(min_length=1)
    exam_id: str = Field(min_length=1)
    item_id: str = Field(min_length=1)
    asset_id: str = Field(min_length=1, max_length=256)
    received_at: str = Field(min_length=10, max_length=40)
    note: str = Field(default="", max_length=1000)

    @field_validator("asset_id")
    @classmethod
    def _validate_asset(cls, value: str) -> str:
        clean = value.strip()
        if ".." in clean or clean.startswith("/") or "\\" in clean:
            raise ValueError("Referensi berkas tidak valid.")
        return clean


class SubmissionReviewPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    institution_id: str = Field(min_length=1)
    exam_id: str = Field(min_length=1)
    item_id: str = Field(min_length=1)
    new_state: ReviewState
    reviewer_id: str | None = None
    note: str = Field(default="", max_length=1000)


class PrintComputePayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    institution_id: str = Field(min_length=1)
    exam_id: str = Field(min_length=1)
    plan_id: str = Field(min_length=1)
    reserve_per_room: int = Field(default=2, ge=0, le=50)
    exclude_cbt: bool = True


class PrintOverridePayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    institution_id: str = Field(min_length=1)
    exam_id: str = Field(min_length=1)
    print_qty_id: str = Field(min_length=1)
    override_qty: int = Field(ge=0, le=5000)
    reason: str = Field(min_length=2, max_length=300)


class HandoverRecordPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    institution_id: str = Field(min_length=1)
    exam_id: str = Field(min_length=1)
    room_session_id: str | None = None
    kind: Literal["out", "in"] = "out"
    material_type: str = Field(min_length=1, max_length=120)
    expected_qty: int = Field(ge=0, le=10000)
    actual_qty: int = Field(ge=0, le=10000)
    from_person_name: str = Field(min_length=1, max_length=160)
    to_person_name: str = Field(min_length=1, max_length=160)
    handed_at: str = Field(min_length=10, max_length=40)
    note: str = Field(default="", max_length=500)
