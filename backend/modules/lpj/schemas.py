"""Pydantic schemas for LPJ-01..LPJ-05."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, model_validator


class LpjScopedPayload(BaseModel):
    institution_id: str = Field(min_length=1)
    exam_id: str = Field(min_length=1)
    lpj_version_id: str | None = None


class LpjCreateVersionPayload(BaseModel):
    institution_id: str = Field(min_length=1)
    exam_id: str = Field(min_length=1)
    title: str | None = None


class LpjSectionSavePayload(BaseModel):
    institution_id: str = Field(min_length=1)
    exam_id: str = Field(min_length=1)
    lpj_version_id: str = Field(min_length=1)
    section_key: str = Field(min_length=1)
    narrative: str = ""


class LpjEvaluationSavePayload(BaseModel):
    institution_id: str = Field(min_length=1)
    exam_id: str = Field(min_length=1)
    lpj_version_id: str = Field(min_length=1)
    id: str | None = None
    incident_id: str | None = None
    issue_title: str = Field(min_length=1)
    resolution: str = ""
    recommendation: str = ""
    pic_name: str = ""
    notes: str = ""
    sort_order: int = Field(default=1, ge=1)


class LpjAttachmentSavePayload(BaseModel):
    institution_id: str = Field(min_length=1)
    exam_id: str = Field(min_length=1)
    lpj_version_id: str = Field(min_length=1)
    id: str | None = None
    doc_run_id: str | None = None
    title: str = Field(min_length=1)
    file_path: str = ""
    included: bool = True
    exclusion_reason: str = ""
    sort_order: int = Field(default=1, ge=1)

    @model_validator(mode="after")
    def _validate_exclusion(self) -> LpjAttachmentSavePayload:
        if not self.included and not self.exclusion_reason.strip():
            raise ValueError(
                "Alasan pengecualian wajib diisi jika lampiran dikecualikan."
            )
        return self


class LpjFinalizePayload(BaseModel):
    institution_id: str = Field(min_length=1)
    exam_id: str = Field(min_length=1)
    lpj_version_id: str = Field(min_length=1)


class LpjExportPayload(BaseModel):
    institution_id: str = Field(min_length=1)
    exam_id: str = Field(min_length=1)
    lpj_version_id: str = Field(min_length=1)
    format: Literal["pdf", "docx"] = "pdf"
    paper_size: Literal["A4", "F4"] = "A4"
