"""Pydantic schemas for COM-01..COM-06."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class ComScopedPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    institution_id: str = Field(min_length=1)
    exam_id: str = Field(min_length=1)


class CommitteeRoleSavePayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    institution_id: str = Field(min_length=1)
    exam_id: str = Field(min_length=1)
    id: str | None = None
    name: str = Field(min_length=1, max_length=120)
    parent_id: str | None = None
    sort_order: int = Field(default=0, ge=0, le=1000)
    jobdesc: str = Field(default="", max_length=2000)


class CommitteeRoleDeletePayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    institution_id: str = Field(min_length=1)
    exam_id: str = Field(min_length=1)
    role_id: str = Field(min_length=1)


class CommitteeMemberAssignPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    institution_id: str = Field(min_length=1)
    exam_id: str = Field(min_length=1)
    role_id: str = Field(min_length=1)
    exam_person_id: str = Field(min_length=1)
    appointed_on: str = Field(default="", max_length=32)
    note: str = Field(default="", max_length=500)


class CommitteeMemberRemovePayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    institution_id: str = Field(min_length=1)
    exam_id: str = Field(min_length=1)
    member_id: str = Field(min_length=1)


class ProgramMilestone(BaseModel):
    model_config = ConfigDict(extra="forbid")

    label: str = Field(min_length=1, max_length=160)
    target_date: str = Field(default="", max_length=32)


class ProgramSection(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str = Field(min_length=1, max_length=160)
    body: str = Field(default="", max_length=4000)


class ProgramKerjaSavePayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    institution_id: str = Field(min_length=1)
    exam_id: str = Field(min_length=1)
    basis_text: str = Field(default="", max_length=4000)
    objectives: list[str] = Field(default_factory=list)
    milestones: list[ProgramMilestone] = Field(default_factory=list)
    sections: list[ProgramSection] = Field(default_factory=list)


class MeetingSavePayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    institution_id: str = Field(min_length=1)
    exam_id: str = Field(min_length=1)
    id: str | None = None
    title: str = Field(min_length=1, max_length=160)
    meeting_date: str = Field(min_length=10, max_length=32)
    start_time: str = Field(min_length=4, max_length=16)
    end_time: str = Field(min_length=4, max_length=16)
    location: str = Field(default="", max_length=160)
    agenda: str = Field(default="", max_length=2000)
    minutes: str = Field(default="", max_length=8000)
    decisions: list[str] = Field(default_factory=list)


class MeetingDeletePayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    institution_id: str = Field(min_length=1)
    exam_id: str = Field(min_length=1)
    meeting_id: str = Field(min_length=1)


class MeetingAttendanceSavePayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    institution_id: str = Field(min_length=1)
    exam_id: str = Field(min_length=1)
    meeting_id: str = Field(min_length=1)
    exam_person_id: str = Field(min_length=1)
    state: Literal["present", "absent", "excused", "unrecorded"] = "present"
    note: str = Field(default="", max_length=300)


class SignatorySavePayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    institution_id: str = Field(min_length=1)
    exam_id: str = Field(min_length=1)
    role_key: str = Field(min_length=1, max_length=64)
    role_label: str = Field(min_length=1, max_length=120)
    exam_person_id: str | None = None
    signer_name: str = Field(default="", max_length=160)
    signer_title: str = Field(default="", max_length=160)
    signer_nip: str = Field(default="", max_length=64)
    signed_date: str = Field(default="", max_length=32)
    signature_asset_id: str | None = None
    required: bool = True
    sort_order: int = Field(default=0, ge=0, le=100)


class SignatoryDeletePayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    institution_id: str = Field(min_length=1)
    exam_id: str = Field(min_length=1)
    signatory_id: str = Field(min_length=1)
