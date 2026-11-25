"""Unit tests for DOC-01..DOC-08 (PDF, DOCX, XLSX renderers & filename)."""

from __future__ import annotations

import io
import zipfile

from openpyxl import load_workbook

from backend.modules.doc.renderers import (
    render_docx_bytes,
    render_pdf_bytes,
    render_xlsx_bytes,
)
from backend.modules.doc.service import sanitize_filename


def test_render_pdf_and_docx_and_xlsx() -> None:
    pdf = render_pdf_bytes(
        title="Daftar Hadir",
        subtitle="SMPN 1 Nusantara",
        headers=["No", "NIS", "Nama"],
        rows=[["1", "00123", "Budi Santoso Panjang Sekali"]],
        signers=[
            {"role_label": "Ketua", "signer_name": "Ahmad", "signer_title": "Kepala"}
        ],
        paper_size="F4",
        doc_number="001/UJN/2026",
    )
    assert pdf.startswith(b"%PDF")

    docx = render_docx_bytes(
        title="Daftar Hadir",
        subtitle="SMPN 1 Nusantara",
        headers=["No", "NIS"],
        rows=[["1", "00123"]],
        signers=[],
    )
    with zipfile.ZipFile(io.BytesIO(docx), "r") as zf:
        assert "word/document.xml" in zf.namelist()

    xlsx = render_xlsx_bytes(
        sheet_title="Rekap",
        headers=["NIS", "Honor"],
        rows=[["00123", 150000]],
    )
    wb = load_workbook(io.BytesIO(xlsx))
    ws = wb.active
    assert ws is not None
    assert ws["A2"].value == "00123"
    assert ws["A2"].number_format == "@"
    assert ws["B2"].value == 150000


def test_sanitize_filename_blocks_traversal() -> None:
    assert sanitize_filename("../../etc/passwd") == "etc_passwd"
