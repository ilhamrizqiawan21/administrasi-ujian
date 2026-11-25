"""Document renderers for PDF (ReportLab), DOCX (sandboxed docxtpl), XLSX."""

from __future__ import annotations

import io
from typing import Any

from docx import Document
from docxtpl import DocxTemplate
from jinja2.sandbox import SandboxedEnvironment
from openpyxl import Workbook
from openpyxl.styles import Font
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    KeepTogether,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)


def _page_size(paper_size: str) -> tuple[float, float]:
    if paper_size == "F4":
        return (215.0 * mm, 330.0 * mm)
    return (float(A4[0]), float(A4[1]))


def render_pdf_bytes(
    *,
    title: str,
    subtitle: str,
    headers: list[str],
    rows: list[list[str]],
    signers: list[dict[str, str]],
    paper_size: str = "A4",
    doc_number: str = "",
) -> bytes:
    """Render structured PDF using ReportLab with repeating headers & KeepTogether."""
    buf = io.BytesIO()
    pagesize = _page_size(paper_size)
    doc = SimpleDocTemplate(
        buf,
        pagesize=pagesize,
        leftMargin=15 * mm,
        rightMargin=15 * mm,
        topMargin=15 * mm,
        bottomMargin=15 * mm,
    )
    styles = getSampleStyleSheet()
    story: list[Any] = [
        Paragraph(f"<b>{title}</b>", styles["Title"]),
        Paragraph(subtitle, styles["Normal"]),
    ]
    if doc_number:
        story.append(Paragraph(f"Nomor: {doc_number}", styles["Normal"]))
    story.append(Spacer(1, 6 * mm))

    table_data: list[list[Any]] = [headers]
    for r in rows:
        table_data.append([Paragraph(str(c), styles["Normal"]) for c in r])

    tbl = Table(table_data, repeatRows=1)
    tbl.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#E2E8F0")),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#94A3B8")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("PADDING", (0, 0), (-1, -1), 5),
            ]
        )
    )
    story.append(tbl)
    story.append(Spacer(1, 8 * mm))

    if signers:
        sig_blocks: list[Any] = []
        for s in signers:
            sig_blocks.append(
                Paragraph(
                    f"<b>{s.get('role_label', '')}</b><br/><br/><br/>"
                    f"<u>{s.get('signer_name', '-')}</u><br/>"
                    f"{s.get('signer_title', '')}",
                    styles["Normal"],
                )
            )
        story.append(KeepTogether(sig_blocks))

    doc.build(story)
    return buf.getvalue()


def render_docx_bytes(
    *,
    title: str,
    subtitle: str,
    headers: list[str],
    rows: list[list[str]],
    signers: list[dict[str, str]],
    template_bytes: bytes | None = None,
    context: dict[str, Any] | None = None,
) -> bytes:
    """Render DOCX using SandboxedEnvironment (docxtpl) or structured python-docx."""
    if template_bytes is not None and context is not None:
        tpl = DocxTemplate(io.BytesIO(template_bytes))
        env = SandboxedEnvironment()
        tpl.render(context, jinja_env=env)
        out = io.BytesIO()
        tpl.save(out)
        return out.getvalue()

    doc = Document()
    doc.add_heading(title, level=1)
    doc.add_paragraph(subtitle)
    table = doc.add_table(rows=1, cols=len(headers))
    for i, h in enumerate(headers):
        table.rows[0].cells[i].text = h
    for r in rows:
        cells = table.add_row().cells
        for i, val in enumerate(r):
            cells[i].text = str(val)
    if signers:
        doc.add_paragraph("")
        for s in signers:
            doc.add_paragraph(
                f"{s.get('role_label', '')}: {s.get('signer_name', '-')} "
                f"({s.get('signer_title', '')})"
            )
    out = io.BytesIO()
    doc.save(out)
    return out.getvalue()


def render_xlsx_bytes(
    *,
    sheet_title: str,
    headers: list[str],
    rows: list[list[str | int]],
) -> bytes:
    """Render typed XLSX preserving leading zeros and numeric types (DOC-08)."""
    wb = Workbook()
    ws = wb.active
    assert ws is not None
    ws.title = sheet_title[:31]
    ws.append(headers)
    for cell in ws[1]:
        cell.font = Font(bold=True)
    ws.print_title_rows = "1:1"

    for r in rows:
        ws.append(r)
        row_idx = ws.max_row
        for col_idx, val in enumerate(r, start=1):
            c = ws.cell(row=row_idx, column=col_idx)
            if isinstance(val, str):
                c.number_format = "@"
            elif isinstance(val, int):
                c.number_format = "#,##0"

    for col_idx, h in enumerate(headers, start=1):
        col_letter = ws.cell(row=1, column=col_idx).column_letter
        max_len = max(
            [len(str(h)), *(len(str(r[col_idx - 1])) for r in rows)], default=10
        )
        ws.column_dimensions[col_letter].width = min(max(max_len + 4, 12), 42)

    out = io.BytesIO()
    wb.save(out)
    return out.getvalue()
