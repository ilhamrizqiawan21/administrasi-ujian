"""Pydantic bridge schemas for ARC-01..ARC-04."""

from __future__ import annotations

from pydantic import BaseModel, Field


class ArcListPayload(BaseModel):
    institution_id: str = Field(min_length=1)
    year_id: str | None = None
    exam_type_id: str | None = None
    state: str | None = None
    search: str | None = None


class ArcExamScopedPayload(BaseModel):
    institution_id: str = Field(min_length=1)
    exam_id: str = Field(min_length=1)


class ArcPackageExportPayload(BaseModel):
    institution_id: str = Field(min_length=1)
    exam_id: str = Field(min_length=1)
    include_personal_info: bool = False
    include_documents: bool = True
    output_filename: str | None = None


class ArcPackageVerifyPayload(BaseModel):
    institution_id: str = Field(min_length=1)
    package_id: str = Field(min_length=1)


class ArcDuplicatePayload(BaseModel):
    institution_id: str = Field(min_length=1)
    source_exam_id: str = Field(min_length=1)
    target_year_id: str = Field(min_length=1)
    title: str = Field(min_length=1, max_length=200)
    semester_label: str = Field(min_length=1, max_length=50)
    starts_on: str = Field(min_length=10, max_length=10)
    ends_on: str = Field(min_length=10, max_length=10)
    mode: str | None = None


class ArcRetentionReviewPayload(BaseModel):
    institution_id: str = Field(min_length=1)
    min_age_days: int = Field(default=365, ge=0, le=36500)


class ArcRetentionPurgePayload(BaseModel):
    institution_id: str = Field(min_length=1)
    exam_id: str = Field(min_length=1)
    authorized_by: str = Field(min_length=1, max_length=120)
    confirm_title: str = Field(min_length=1, max_length=200)
