"""Unit tests for EXP-01..EXP-06 (transitions, negative handover validation)."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from backend.modules.exp.schemas import HandoverRecordPayload
from backend.modules.exp.service import validate_review_transition


def test_review_transition_rules() -> None:
    assert validate_review_transition("missing", "ready") is False
    assert validate_review_transition("received", "ready") is False
    assert validate_review_transition("received", "valid") is True
    assert validate_review_transition("valid", "ready") is True
    assert validate_review_transition("ready", "revision") is True


def test_handover_rejects_negative_quantities() -> None:
    with pytest.raises(ValidationError):
        HandoverRecordPayload(
            institution_id="inst-1",
            exam_id="ex-1",
            material_type="Naskah MAT",
            expected_qty=-1,
            actual_qty=10,
            from_person_name="Panitia",
            to_person_name="Pengawas",
            handed_at="2026-12-01T07:00:00+00:00",
        )
