"""Pydantic schemas and interval helpers for SES-01..SES-07."""

from __future__ import annotations

import re
from datetime import UTC, datetime
from typing import Literal
from zoneinfo import ZoneInfo

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

ExamMode = Literal["paper", "cbt", "practice", "hybrid"]
_TIME_RE = re.compile(r"^([01]\d|2[0-3]):[0-5]\d$")
_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


class BreakWindow(BaseModel):
    model_config = ConfigDict(extra="forbid")

    label: str = Field(default="Istirahat", min_length=1, max_length=60)
    local_date: str | None = None
    start_local: str
    end_local: str

    @field_validator("start_local", "end_local")
    @classmethod
    def _check_time(cls, value: str) -> str:
        clean = value.strip()
        if not _TIME_RE.fullmatch(clean):
            raise ValueError("Format jam harus HH:MM (24 jam).")
        return clean

    @model_validator(mode="after")
    def _check_window(self) -> BreakWindow:
        if self.end_local <= self.start_local:
            raise ValueError("Jam selesai istirahat harus setelah jam mulai.")
        return self


class CalendarRules(BaseModel):
    model_config = ConfigDict(extra="forbid")

    holidays: list[str] = Field(default_factory=list)
    break_windows: list[BreakWindow] = Field(default_factory=list)
    allow_overnight: bool = False


class PlanListPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    institution_id: str = Field(min_length=1)
    exam_id: str = Field(min_length=1)


class PlanCreatePayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    institution_id: str = Field(min_length=1)
    exam_id: str = Field(min_length=1)
    clone_from_plan_id: str | None = None


class PlanScopedPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    institution_id: str = Field(min_length=1)
    exam_id: str = Field(min_length=1)
    plan_id: str = Field(min_length=1)


class CalendarUpdatePayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    institution_id: str = Field(min_length=1)
    exam_id: str = Field(min_length=1)
    plan_id: str = Field(min_length=1)
    expected_revision: int = Field(ge=1)
    calendar: CalendarRules


class SessionSavePayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    institution_id: str = Field(min_length=1)
    exam_id: str = Field(min_length=1)
    plan_id: str = Field(min_length=1)
    id: str | None = None
    label: str = Field(min_length=1, max_length=60)
    local_date: str
    start_local: str
    end_local: str
    sort_order: int = Field(default=1, ge=1, le=999)
    mode: ExamMode = "paper"

    @field_validator("local_date")
    @classmethod
    def _check_date(cls, value: str) -> str:
        clean = value.strip()
        if not _DATE_RE.fullmatch(clean):
            raise ValueError("Format tanggal harus YYYY-MM-DD.")
        return clean

    @field_validator("start_local", "end_local")
    @classmethod
    def _check_time(cls, value: str) -> str:
        clean = value.strip()
        if not _TIME_RE.fullmatch(clean):
            raise ValueError("Format jam harus HH:MM.")
        return clean


class SessionDeletePayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    institution_id: str = Field(min_length=1)
    exam_id: str = Field(min_length=1)
    plan_id: str = Field(min_length=1)
    session_id: str = Field(min_length=1)


class PaperAssignPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    institution_id: str = Field(min_length=1)
    exam_id: str = Field(min_length=1)
    plan_id: str = Field(min_length=1)
    expected_revision: int = Field(ge=1)
    requirement_id: str = Field(min_length=1)
    session_id: str = Field(min_length=1)
    exam_room_id: str = Field(min_length=1)


class PaperLockPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    institution_id: str = Field(min_length=1)
    exam_id: str = Field(min_length=1)
    plan_id: str = Field(min_length=1)
    paper_id: str = Field(min_length=1)
    locked: bool


class PlanPublishPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    institution_id: str = Field(min_length=1)
    exam_id: str = Field(min_length=1)
    plan_id: str = Field(min_length=1)
    expected_revision: int = Field(ge=1)


class AutoSchedulePayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    institution_id: str = Field(min_length=1)
    exam_id: str = Field(min_length=1)
    plan_id: str = Field(min_length=1)
    expected_revision: int = Field(ge=1)
    time_limit_sec: int = Field(default=30, ge=1, le=300)
    seed: int = Field(default=42, ge=0)


def local_to_utc_interval(
    local_date: str,
    start_local: str,
    end_local: str,
    timezone_name: str,
    *,
    allow_overnight: bool = False,
) -> tuple[datetime, datetime]:
    """Convert local date/time strings to UTC datetime interval [start, end)."""
    tz = ZoneInfo(timezone_name)
    start_dt = datetime.strptime(
        f"{local_date} {start_local}", "%Y-%m-%d %H:%M"
    ).replace(tzinfo=tz)
    end_dt = datetime.strptime(f"{local_date} {end_local}", "%Y-%m-%d %H:%M").replace(
        tzinfo=tz
    )
    if end_dt <= start_dt:
        if not allow_overnight:
            raise ValueError(
                "Jam selesai sesi harus setelah jam mulai (overnight ditolak)."
            )
        from datetime import timedelta

        end_dt = end_dt + timedelta(days=1)
    return start_dt.astimezone(UTC), end_dt.astimezone(UTC)
