"""Pydantic schemas for OPS-01..OPS-08."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

RoomSessionActualState = Literal["scheduled", "in_progress", "finished"]
StudentAttState = Literal["unrecorded", "present", "sick", "excused", "absent", "late"]
StaffAttState = Literal["unrecorded", "present", "absent", "substituted"]


class OpsScopedPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    institution_id: str = Field(min_length=1)
    exam_id: str = Field(min_length=1)
    plan_id: str = Field(min_length=1)
    include_confidential: bool = False


class RoomSessionStatePayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    institution_id: str = Field(min_length=1)
    exam_id: str = Field(min_length=1)
    plan_id: str = Field(min_length=1)
    room_session_id: str = Field(min_length=1)
    actual_state: RoomSessionActualState


class StudentAttendancePayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    institution_id: str = Field(min_length=1)
    exam_id: str = Field(min_length=1)
    sitting_ids: list[str] = Field(min_length=1)
    state: StudentAttState
    note: str = Field(default="", max_length=300)


class StaffAttendancePayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    institution_id: str = Field(min_length=1)
    exam_id: str = Field(min_length=1)
    plan_id: str = Field(min_length=1)
    slot_id: str = Field(min_length=1)
    state: StaffAttState
    actual_person_id: str | None = None
    approved_by: str = Field(default="", max_length=120)
    note: str = Field(default="", max_length=300)


class CommitteeAttendancePayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    institution_id: str = Field(min_length=1)
    exam_id: str = Field(min_length=1)
    att_date: str = Field(pattern=r"^\d{4}-\d{2}-\d{2}$")
    shift: str = Field(min_length=1, max_length=60)
    exam_person_id: str = Field(min_length=1)
    state: str = Field(min_length=1, max_length=40)
    note: str = Field(default="", max_length=300)


class SessionReportPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    institution_id: str = Field(min_length=1)
    exam_id: str = Field(min_length=1)
    plan_id: str = Field(min_length=1)
    room_session_id: str = Field(min_length=1)
    remarks: str = Field(default="", max_length=2000)
    signer_name: str = Field(default="", max_length=160)


class IncidentRecordPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    institution_id: str = Field(min_length=1)
    exam_id: str = Field(min_length=1)
    room_session_id: str = Field(min_length=1)
    type_code: Literal["late", "violation", "technical", "other"] = "other"
    severity: Literal["low", "medium", "high"] = "low"
    participant_id: str | None = None
    note: str = Field(min_length=2, max_length=1000)
    resolution: str = Field(default="", max_length=1000)
    confidential: bool = False


class MakeupCreatePayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    institution_id: str = Field(min_length=1)
    exam_id: str = Field(min_length=1)
    plan_id: str = Field(min_length=1)
    original_sitting_id: str = Field(min_length=1)
    target_room_session_id: str = Field(min_length=1)
    reason: str = Field(default="", max_length=300)


class ClosingCompletePayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    institution_id: str = Field(min_length=1)
    exam_id: str = Field(min_length=1)
    plan_id: str = Field(min_length=1)
    require_all_attendance: bool = True
    require_all_reports_final: bool = True
