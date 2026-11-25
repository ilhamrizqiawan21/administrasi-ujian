"""Pydantic schemas for TSK-01..TSK-05."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

TaskPhase = Literal["preparation", "implementation", "closing"]
TaskPriority = Literal["low", "medium", "high", "critical"]
TaskState = Literal["todo", "in_progress", "blocked", "done"]


class TskScopedPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    institution_id: str = Field(min_length=1)
    exam_id: str = Field(min_length=1)


class ApplyPresetPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    institution_id: str = Field(min_length=1)
    exam_id: str = Field(min_length=1)
    preset_key: Literal["standard_exam"] = "standard_exam"


class TaskSavePayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    institution_id: str = Field(min_length=1)
    exam_id: str = Field(min_length=1)
    id: str | None = None
    phase: TaskPhase = "preparation"
    title: str = Field(min_length=1, max_length=200)
    description: str = Field(default="", max_length=2000)
    pic_id: str | None = None
    priority: TaskPriority = "medium"
    due_date: str = Field(pattern=r"^\d{4}-\d{2}-\d{2}$")
    state: TaskState = "todo"
    blocked_reason: str = Field(default="", max_length=500)
    parent_id: str | None = None


class TaskDeletePayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    institution_id: str = Field(min_length=1)
    exam_id: str = Field(min_length=1)
    task_id: str = Field(min_length=1)


class TaskDependencyPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    institution_id: str = Field(min_length=1)
    exam_id: str = Field(min_length=1)
    task_id: str = Field(min_length=1)
    prerequisite_id: str = Field(min_length=1)


class TaskDependencyDeletePayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    institution_id: str = Field(min_length=1)
    exam_id: str = Field(min_length=1)
    dependency_id: str = Field(min_length=1)


class TaskEvidencePayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    institution_id: str = Field(min_length=1)
    exam_id: str = Field(min_length=1)
    task_id: str = Field(min_length=1)
    evidence_asset_id: str = Field(min_length=1, max_length=256)
    evidence_note: str = Field(default="", max_length=1000)
    completed_by: str = Field(min_length=1, max_length=160)
    mark_done: bool = True

    @field_validator("evidence_asset_id")
    @classmethod
    def _validate_asset(cls, value: str) -> str:
        clean = value.strip()
        if ".." in clean or clean.startswith("/") or "\\" in clean:
            raise ValueError("Referensi berkas bukti tidak valid.")
        return clean
