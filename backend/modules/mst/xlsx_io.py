"""Safe XLSX import/export helpers with leading-zero preservation & anti-injection."""

from __future__ import annotations

import base64
import binascii
import io
import zipfile
from typing import Any

from openpyxl import Workbook, load_workbook
from openpyxl.styles import Alignment, Font

from backend.core.errors import AppError

_MAX_XLSX_BYTES = 10 * 1024 * 1024
_FORMULA_PREFIXES = ("=", "+", "-", "@", "\t", "\r")
_TEXT_ID_COLUMNS = frozenset({"nis", "nisn", "nip", "staff_code", "code"})


def sanitize_excel_text(value: str) -> str:
    """Prevent Excel formula injection on user-controlled text cells."""
    if value and value[0] in _FORMULA_PREFIXES:
        return f"'{value}"
    return value


def parse_xlsx_rows(
    content_base64: str,
) -> tuple[list[str], list[dict[str, Any]], list[str]]:
    """Parse first worksheet of an XLSX file safely without evaluating formulas."""
    try:
        raw_bytes = base64.b64decode(content_base64, validate=True)
    except (binascii.Error, ValueError) as exc:
        raise AppError(
            "FILE_INVALID", "Format base64 berkas XLSX tidak valid."
        ) from exc

    if len(raw_bytes) == 0 or len(raw_bytes) > _MAX_XLSX_BYTES:
        raise AppError(
            "FILE_INVALID",
            "Ukuran berkas XLSX harus lebih dari 0 dan maksimal 10 MB.",
        )

    try:
        wb = load_workbook(io.BytesIO(raw_bytes), read_only=True, data_only=False)
    except (zipfile.BadZipFile, OSError, KeyError, ValueError) as exc:
        raise AppError(
            "FILE_INVALID", "Berkas bukan file XLSX yang valid atau rusak."
        ) from exc

    try:
        ws = wb.active
        if ws is None:
            raise AppError("FILE_INVALID", "Workbook tidak memiliki lembar kerja.")

        raw_rows = list(ws.iter_rows(values_only=False))
        if not raw_rows:
            raise AppError("FILE_INVALID", "Lembar kerja XLSX kosong.")

        headers = [
            str(cell.value).strip() if cell.value is not None else ""
            for cell in raw_rows[0]
        ]
        if not any(headers):
            raise AppError("FILE_INVALID", "Baris header XLSX tidak ditemukan.")

        warnings: list[str] = []
        parsed_rows: list[dict[str, Any]] = []
        numeric_id_warning_emitted = False

        for row_idx, row_cells in enumerate(raw_rows[1:], start=2):
            row_values: dict[str, str] = {}
            formula_cells: list[str] = []
            is_blank_row = True

            for col_idx, header in enumerate(headers):
                if not header:
                    continue
                cell = row_cells[col_idx] if col_idx < len(row_cells) else None
                val = cell.value if cell is not None else None
                if val is None or str(val).strip() == "":
                    row_values[header] = ""
                    continue

                is_blank_row = False
                if isinstance(val, str):
                    stripped = val.strip()
                    if stripped.startswith("="):
                        formula_cells.append(header)
                    row_values[header] = stripped
                elif isinstance(val, (int, float)):
                    if (
                        not numeric_id_warning_emitted
                        and header.lower() in _TEXT_ID_COLUMNS
                    ):
                        numeric_id_warning_emitted = True
                        warnings.append(
                            f"Kolom '{header}' terbaca bertipe angka di Excel; "
                            "angka nol di depan yang hilang di Excel tidak ditebak."
                        )
                    if isinstance(val, float) and val.is_integer():
                        row_values[header] = str(int(val))
                    else:
                        row_values[header] = str(val)
                else:
                    row_values[header] = str(val).strip()

            if is_blank_row:
                continue

            parsed_rows.append(
                {
                    "row_number": row_idx,
                    "values": row_values,
                    "formula_columns": formula_cells,
                }
            )

        return headers, parsed_rows, warnings
    finally:
        wb.close()


def build_xlsx_bytes(
    *,
    sheet_title: str,
    columns: list[tuple[str, str]],
    rows: list[dict[str, Any]],
) -> bytes:
    """Create XLSX bytes with explicit text cell typing for identifier columns."""
    wb = Workbook()
    ws = wb.active
    assert ws is not None
    ws.title = sheet_title[:31]

    bold = Font(bold=True)
    for col_idx, (_key, header_label) in enumerate(columns, start=1):
        cell = ws.cell(row=1, column=col_idx, value=header_label)
        cell.font = bold
        cell.alignment = Alignment(horizontal="center")

    for row_offset, row_data in enumerate(rows, start=2):
        for col_idx, (key, _header_label) in enumerate(columns, start=1):
            raw = row_data.get(key)
            if raw is None:
                val = ""
            elif key in _TEXT_ID_COLUMNS:
                val = str(raw)
            elif isinstance(raw, (int, float)) and not isinstance(raw, bool):
                cell = ws.cell(row=row_offset, column=col_idx, value=raw)
                continue
            else:
                val = sanitize_excel_text(str(raw))

            cell = ws.cell(row=row_offset, column=col_idx)
            cell.value = val
            cell.data_type = "s"
            if key in _TEXT_ID_COLUMNS:
                cell.number_format = "@"

    for col_idx, (key, header_label) in enumerate(columns, start=1):
        max_len = max(
            [len(header_label)] + [len(str(row.get(key) or "")) for row in rows]
        )
        col_letter = ws.cell(row=1, column=col_idx).column_letter
        ws.column_dimensions[col_letter].width = min(max_len + 4, 48)

    ws.print_title_rows = "1:1"
    out = io.BytesIO()
    wb.save(out)
    return out.getvalue()
