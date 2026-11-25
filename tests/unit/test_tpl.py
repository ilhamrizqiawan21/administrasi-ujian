"""Unit tests for TPL-01..TPL-06 (contrast, image, DOCX macro/tag checks)."""

from __future__ import annotations

import io
import zipfile

import pytest

from backend.core.errors import ConflictError, ValidationError
from backend.modules.tpl.service import (
    contrast_ratio,
    inspect_docx_bytes,
    validate_image_bytes,
)


def _make_docx(doc_xml: str, extra_files: dict[str, bytes] | None = None) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("word/document.xml", doc_xml.encode("utf-8"))
        for k, v in (extra_files or {}).items():
            zf.writestr(k, v)
    return buf.getvalue()


def test_validate_image_bytes_rejects_invalid_header() -> None:
    assert validate_image_bytes(b"\x89PNG\r\n\x1a\nxxxx") == "png"
    with pytest.raises(ValidationError):
        validate_image_bytes(b"NOT_AN_IMAGE")


def test_inspect_docx_rejects_macros_and_external_rels_and_flags_unknown_tags() -> None:
    macro_docx = _make_docx("<w:document/>", {"word/vbaProject.bin": b"VBA"})
    with pytest.raises(ConflictError, match="macro"):
        inspect_docx_bytes(macro_docx)

    ext_docx = _make_docx(
        "<w:document/>",
        {
            "word/_rels/document.xml.rels": (
                b'<Relationships><Relationship TargetMode="External" Target="http://x"/></Relationships>'
            )
        },
    )
    with pytest.raises(ConflictError, match="relasi eksternal"):
        inspect_docx_bytes(ext_docx)

    ok_docx = _make_docx(
        "<w:document>{{ institution_name }} {{ unknown_tag }}</w:document>"
    )
    res = inspect_docx_bytes(ok_docx)
    assert res["valid"] is False
    assert "institution_name" in res["found_tags"]
    assert res["unknown_tags"] == ["unknown_tag"]


def test_contrast_ratio_wcag() -> None:
    assert contrast_ratio("#FFFFFF", "#0F172A") > 15.0
    assert contrast_ratio("#FFFFFF", "#E2E8F0") < 2.0
