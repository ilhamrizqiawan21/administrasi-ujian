"""Pydantic schemas for FIN-01..FIN-08."""

from __future__ import annotations

from decimal import Decimal, InvalidOperation
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class FinScopedPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    institution_id: str = Field(min_length=1)
    exam_id: str = Field(min_length=1)


class BudgetCategorySavePayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    institution_id: str = Field(min_length=1)
    exam_id: str = Field(min_length=1)
    id: str | None = None
    label: str = Field(min_length=1, max_length=120)
    parent_id: str | None = None
    source_fund: str = Field(default="BOS", min_length=1, max_length=64)
    default_unit: str = Field(default="paket", min_length=1, max_length=32)


class BudgetCategoryArchivePayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    institution_id: str = Field(min_length=1)
    exam_id: str = Field(min_length=1)
    category_id: str = Field(min_length=1)


class BudgetVersionActionPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    institution_id: str = Field(min_length=1)
    exam_id: str = Field(min_length=1)
    budget_version_id: str | None = None


class BudgetLineSavePayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    institution_id: str = Field(min_length=1)
    exam_id: str = Field(min_length=1)
    budget_version_id: str = Field(min_length=1)
    category_id: str = Field(min_length=1)
    description: str = Field(min_length=1, max_length=240)
    qty_decimal: str = Field(min_length=1, max_length=32)
    unit: str = Field(min_length=1, max_length=32)
    unit_rate_idr: int = Field(ge=0)

    @field_validator("qty_decimal")
    @classmethod
    def _validate_qty(cls, value: str) -> str:
        try:
            d = Decimal(value.strip())
        except InvalidOperation as exc:
            raise ValueError("Kuantitas harus berupa angka desimal valid.") from exc
        if d < 0:
            raise ValueError("Kuantitas tidak boleh bernilai negatif.")
        return str(d)


class LedgerSavePayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    institution_id: str = Field(min_length=1)
    exam_id: str = Field(min_length=1)
    category_id: str = Field(min_length=1)
    kind: Literal["income", "expense"] = "expense"
    amount_idr: int = Field(gt=0)
    entry_date: str = Field(pattern=r"^\d{4}-\d{2}-\d{2}$")
    reference: str = Field(default="", max_length=120)
    payee: str = Field(default="", max_length=160)


class LedgerActionPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    institution_id: str = Field(min_length=1)
    exam_id: str = Field(min_length=1)
    entry_id: str = Field(min_length=1)


class HonorRuleSavePayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    institution_id: str = Field(min_length=1)
    exam_id: str = Field(min_length=1)
    role_code: str = Field(min_length=1, max_length=64)
    unit_type: Literal["session", "day", "fixed"] = "session"
    rate_idr: int = Field(ge=0)
    effective_date: str = Field(pattern=r"^\d{4}-\d{2}-\d{2}$")


class HonorPayPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    institution_id: str = Field(min_length=1)
    exam_id: str = Field(min_length=1)
    honor_line_id: str = Field(min_length=1)
    category_id: str = Field(min_length=1)
    entry_date: str = Field(pattern=r"^\d{4}-\d{2}-\d{2}$")
