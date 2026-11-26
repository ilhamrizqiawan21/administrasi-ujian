"""Pydantic bridge schemas for BAK-01..BAK-04."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class BakScopedPayload(BaseModel):
    institution_id: str = Field(min_length=1)


class BakCreatePayload(BaseModel):
    institution_id: str = Field(min_length=1)
    kind: Literal["manual", "scheduled_startup", "scheduled_close"] = "manual"
    output_filename: str | None = None


class BakVerifyPayload(BaseModel):
    institution_id: str = Field(min_length=1)
    backup_id: str | None = None
    file_path: str | None = None


class BakScheduleSavePayload(BaseModel):
    institution_id: str = Field(min_length=1)
    auto_on_startup: bool = True
    auto_on_close: bool = True
    retention_count: int = Field(default=7, ge=1, le=365)


class BakScheduleRunPayload(BaseModel):
    institution_id: str = Field(min_length=1)
    trigger: Literal["startup", "close"] = "startup"
    simulate_failure: bool = False


class BakRestorePayload(BaseModel):
    institution_id: str = Field(min_length=1)
    file_path: str = Field(min_length=1)


class BakRecoveryPayload(BaseModel):
    institution_id: str = Field(min_length=1)
    clean_temp_files: bool = True
    mark_interrupted_jobs: bool = True
