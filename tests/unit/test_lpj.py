"""Unit tests for LPJ-01..LPJ-05."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from backend.modules.lpj.schemas import LpjAttachmentSavePayload
from backend.modules.lpj.service import DEFAULT_SECTIONS, _default_sections_dict


def test_attachment_exclusion_requires_reason() -> None:
    with pytest.raises(ValidationError):
        LpjAttachmentSavePayload(
            institution_id="inst1",
            exam_id="ex1",
            lpj_version_id="v1",
            title="Berita Acara",
            included=False,
            exclusion_reason="",
        )

    valid = LpjAttachmentSavePayload(
        institution_id="inst1",
        exam_id="ex1",
        lpj_version_id="v1",
        title="Berita Acara",
        included=False,
        exclusion_reason="Tidak ada insiden",
    )
    assert valid.included is False


def test_default_sections_cover_all_structured_parts() -> None:
    sections = _default_sections_dict("PAS Ganjil")
    assert len(sections) == len(DEFAULT_SECTIONS)
    for key, _ in DEFAULT_SECTIONS:
        assert key in sections
        assert "PAS Ganjil" in sections[key]["narrative"]
