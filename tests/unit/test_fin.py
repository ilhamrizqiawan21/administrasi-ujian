"""Unit tests for FIN-01..FIN-08 (exact Decimal rounding & terbilang IDR)."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from backend.modules.fin.schemas import BudgetLineSavePayload
from backend.modules.fin.service import compute_line_amount_idr, terbilang_idr


def test_compute_line_amount_idr_exact_decimal() -> None:
    assert compute_line_amount_idr("2.5", 15000) == 37500
    assert compute_line_amount_idr("1.5", 15) == 23


def test_budget_line_rejects_negative_qty() -> None:
    with pytest.raises(ValidationError, match="negatif"):
        BudgetLineSavePayload(
            institution_id="i1",
            exam_id="e1",
            budget_version_id="v1",
            category_id="c1",
            description="ATK",
            qty_decimal="-2",
            unit="pak",
            unit_rate_idr=10000,
        )


def test_terbilang_idr() -> None:
    assert terbilang_idr(150000) == "seratus lima puluh ribu rupiah"
    assert terbilang_idr(0) == "nol rupiah"
