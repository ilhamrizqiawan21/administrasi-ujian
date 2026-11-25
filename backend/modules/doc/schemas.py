"""Pydantic schemas for DOC-01..DOC-09."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

DocFormat = Literal["pdf", "docx", "xlsx"]
PaperSize = Literal["A4", "F4"]


class DocScopedPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    institution_id: str = Field(min_length=1)
    exam_id: str = Field(min_length=1)


class DocGeneratePayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    institution_id: str = Field(min_length=1)
    exam_id: str = Field(min_length=1)
    doc_type: str = Field(min_length=1, max_length=64)
    format: DocFormat = "pdf"
    plan_id: str | None = None
    template_id: str | None = None
    paper_size: PaperSize = "A4"
    series: str = Field(default="UJN", min_length=1, max_length=32)
    is_final: bool = False
    scope: dict[str, Any] = Field(default_factory=dict)


class DocBatchPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    institution_id: str = Field(min_length=1)
    exam_id: str = Field(min_length=1)
    doc_type: str = Field(default="kartu_peserta", min_length=1, max_length=64)
    format: Literal["pdf", "docx"] = "pdf"
    plan_id: str | None = None
    paper_size: PaperSize = "A4"
    combine_pdf: bool = True
    item_labels: list[str] = Field(default_factory=list)


class DocReprintPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    institution_id: str = Field(min_length=1)
    exam_id: str = Field(min_length=1)
    run_id: str = Field(min_length=1)
