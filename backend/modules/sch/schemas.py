"""Pydantic schemas for SCH-01..SCH-08."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

RoleCode = Literal["primary", "secondary", "proctor", "backup"]


class InvigilationRules(BaseModel):
    model_config = ConfigDict(extra="forbid")

    hard_avoid_own_class: bool = True
    hard_avoid_own_subject: bool = False
    hard_max_daily: bool = True
    hard_max_total: bool = True
    respect_locks: bool = True
    weight_load_deviation: int = Field(default=10, ge=0, le=100)
    weight_own_class: int = Field(default=20, ge=0, le=100)
    weight_own_subject: int = Field(default=15, ge=0, le=100)
    weight_consecutive: int = Field(default=5, ge=0, le=100)


class InvigilationScopedPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    institution_id: str = Field(min_length=1)
    exam_id: str = Field(min_length=1)
    plan_id: str = Field(min_length=1)


class StaffAvailabilitySavePayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    institution_id: str = Field(min_length=1)
    exam_id: str = Field(min_length=1)
    exam_person_id: str = Field(min_length=1)
    starts_at: str = Field(min_length=10)
    ends_at: str = Field(min_length=10)
    state: Literal["unavailable", "preferred"] = "unavailable"
    reason: str = Field(default="", max_length=200)

    @model_validator(mode="after")
    def _check_interval(self) -> StaffAvailabilitySavePayload:
        s = datetime.fromisoformat(self.starts_at)
        e = datetime.fromisoformat(self.ends_at)
        if e <= s:
            raise ValueError("Waktu selesai ketersediaan harus setelah waktu mulai.")
        return self


class StaffAvailabilityDeletePayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    institution_id: str = Field(min_length=1)
    exam_id: str = Field(min_length=1)
    availability_id: str = Field(min_length=1)


def _default_role_skills() -> list[RoleCode]:
    return ["primary", "secondary"]


class StaffProfileSavePayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    institution_id: str = Field(min_length=1)
    exam_id: str = Field(min_length=1)
    exam_person_id: str = Field(min_length=1)
    max_daily: int | None = Field(default=None, ge=1, le=20)
    max_total: int | None = Field(default=None, ge=1, le=200)
    target_weight_pct: int = Field(default=100, ge=10, le=200)
    role_skills: list[RoleCode] = Field(default_factory=_default_role_skills)


class SlotConfigSavePayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    institution_id: str = Field(min_length=1)
    exam_id: str = Field(min_length=1)
    plan_id: str = Field(min_length=1)
    expected_revision: int = Field(ge=1)
    room_session_id: str = Field(min_length=1)
    primary_count: int = Field(default=1, ge=0, le=5)
    secondary_count: int = Field(default=0, ge=0, le=5)
    proctor_count: int = Field(default=0, ge=0, le=5)


class InvigilationSolvePayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    institution_id: str = Field(min_length=1)
    exam_id: str = Field(min_length=1)
    plan_id: str = Field(min_length=1)
    expected_revision: int = Field(ge=1)
    rules: InvigilationRules = Field(default_factory=InvigilationRules)
    time_limit_sec: int = Field(default=60, ge=1, le=300)
    seed: int = Field(default=42, ge=0)


class InvigilationAssignPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    institution_id: str = Field(min_length=1)
    exam_id: str = Field(min_length=1)
    plan_id: str = Field(min_length=1)
    expected_revision: int = Field(ge=1)
    slot_id: str = Field(min_length=1)
    exam_person_id: str | None = None
    locked: bool = False
    rules: InvigilationRules = Field(default_factory=InvigilationRules)


class ReserveAssignPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    institution_id: str = Field(min_length=1)
    exam_id: str = Field(min_length=1)
    plan_id: str = Field(min_length=1)
    expected_revision: int = Field(ge=1)
    session_id: str = Field(min_length=1)
    exam_person_id: str = Field(min_length=1)


class ReserveDeletePayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    institution_id: str = Field(min_length=1)
    exam_id: str = Field(min_length=1)
    plan_id: str = Field(min_length=1)
    expected_revision: int = Field(ge=1)
    reserve_id: str = Field(min_length=1)
