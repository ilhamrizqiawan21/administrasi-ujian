"""Pydantic schemas for TPL-01..TPL-06."""

from __future__ import annotations

import re
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

PaperSize = Literal["A4", "F4"]
DocEngine = Literal["reportlab", "docx"]

PAPER_DIMENSIONS_MM: dict[PaperSize, tuple[float, float]] = {
    "A4": (210.0, 297.0),
    "F4": (215.0, 330.0),
}

ALLOWLISTED_PLACEHOLDERS: set[str] = {
    "institution_name",
    "institution_address",
    "exam_title",
    "academic_year",
    "semester",
    "room_code",
    "room_name",
    "session_label",
    "session_date",
    "participant_number",
    "participant_name",
    "class_label",
    "signer_name",
    "signer_title",
    "signer_nip",
    "document_number",
}


class TplScopedPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    institution_id: str = Field(min_length=1)


class LetterheadManualPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    institution_id: str = Field(min_length=1)
    name: str = Field(min_length=1, max_length=120)
    header_lines: list[str] = Field(min_length=1)
    alignment: Literal["left", "center"] = "center"
    line_style: Literal["single", "double", "none"] = "double"
    paper_size: PaperSize = "A4"
    logo_left_b64: str | None = None
    logo_right_b64: str | None = None


class LetterheadImagePayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    institution_id: str = Field(min_length=1)
    name: str = Field(min_length=1, max_length=120)
    image_b64: str = Field(min_length=8)
    paper_size: PaperSize = "A4"


class LayoutSettings(BaseModel):
    model_config = ConfigDict(extra="forbid")

    paper_size: PaperSize = "A4"
    margin_top_mm: int = Field(default=15, ge=5, le=50)
    margin_bottom_mm: int = Field(default=15, ge=5, le=50)
    margin_left_mm: int = Field(default=15, ge=5, le=50)
    margin_right_mm: int = Field(default=15, ge=5, le=50)
    font_family: Literal["Helvetica", "Times-Roman"] = "Helvetica"
    font_size_pt: int = Field(default=10, ge=8, le=14)
    columns: int = Field(default=1, ge=1, le=3)
    show_signature: bool = True
    body_clause: str = Field(default="", max_length=2000)


class TemplateSavePayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    institution_id: str = Field(min_length=1)
    doc_type: str = Field(min_length=1, max_length=64)
    name: str = Field(min_length=1, max_length=120)
    engine: DocEngine = "reportlab"
    layout: LayoutSettings = Field(default_factory=LayoutSettings)
    mapping: dict[str, str] = Field(default_factory=dict)
    activate: bool = True


class TemplateDocxValidatePayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    institution_id: str = Field(min_length=1)
    docx_b64: str = Field(min_length=8)


class ThemeProfileSavePayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    institution_id: str = Field(min_length=1)
    name: str = Field(min_length=1, max_length=80)
    app_title: str = Field(default="Ujian Cerdas", min_length=2, max_length=80)
    palette_preset: Literal["ocean_ledger", "forest_slate", "warm_paper"] = (
        "ocean_ledger"
    )
    density: Literal["comfortable", "compact"] = "comfortable"
    surface_hex: str = Field(default="#FFFFFF")
    text_hex: str = Field(default="#0F172A")
    accent_hex: str = Field(default="#0F766E")

    @field_validator("surface_hex", "text_hex", "accent_hex")
    @classmethod
    def _check_hex(cls, value: str) -> str:
        clean = value.strip().upper()
        if not re.fullmatch(r"#[0-9A-F]{6}", clean):
            raise ValueError("Warna harus berformat hex #RRGGBB.")
        return clean
