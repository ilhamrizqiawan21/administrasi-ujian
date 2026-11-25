"""Integration tests for TPL-01..TPL-06 via BridgeApi."""

from __future__ import annotations

import base64
import io
import zipfile
from pathlib import Path
from typing import Any

from backend.bridge.api import BridgeApi
from backend.core.app_shell import bootstrap_runtime


def _call(
    api: BridgeApi, method: str, payload: dict[str, Any] | None = None
) -> dict[str, Any]:
    return api.invoke(
        {"request_id": f"req-{method}", "method": method, "payload": payload or {}}
    )


def test_tpl_bridge_end_to_end(tmp_path: Path) -> None:
    runtime = bootstrap_runtime(workspace_root=tmp_path, institution_slug="tpl_bridge")
    api = BridgeApi(runtime=runtime)

    inst_id = _call(
        api,
        "cfg.first_run.setup",
        {
            "name": "SMPN 1 Nusantara",
            "level_preset": "SMP/MTs",
            "academic_year_label": "2026/2027",
        },
    )["data"]["institution"]["id"]

    # TPL-01: manual letterhead
    lh = _call(
        api,
        "tpl.letterheads.save_manual",
        {
            "institution_id": inst_id,
            "name": "Kop Resmi F4",
            "header_lines": ["PEMERINTAH KABUPATEN", "SMPN 1 NUSANTARA"],
            "paper_size": "F4",
        },
    )
    assert lh["ok"] is True
    assert lh["data"]["version"] == 1

    # TPL-02: image letterhead (reject invalid, accept PNG)
    bad_img = _call(
        api,
        "tpl.letterheads.upload_image",
        {
            "institution_id": inst_id,
            "name": "Kop Gambar",
            "image_b64": base64.b64encode(b"bad-bytes").decode("ascii"),
        },
    )
    assert bad_img["ok"] is False

    ok_img = _call(
        api,
        "tpl.letterheads.upload_image",
        {
            "institution_id": inst_id,
            "name": "Kop Gambar",
            "image_b64": base64.b64encode(b"\x89PNG\r\n\x1a\n0000").decode("ascii"),
        },
    )
    assert ok_img["ok"] is True
    assert ok_img["data"]["version"] == 2

    # TPL-03 & TPL-05: save custom template with F4 layout
    tpl = _call(
        api,
        "tpl.templates.save",
        {
            "institution_id": inst_id,
            "doc_type": "kartu_peserta",
            "name": "Kartu F4 Kustom",
            "engine": "reportlab",
            "layout": {"paper_size": "F4", "columns": 2},
        },
    )
    assert tpl["ok"] is True

    # TPL-04: validate docx placeholders
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("word/document.xml", "<w:document>{{ exam_title }}</w:document>")
    val_doc = _call(
        api,
        "tpl.docx.validate",
        {
            "institution_id": inst_id,
            "docx_b64": base64.b64encode(buf.getvalue()).decode("ascii"),
        },
    )
    assert val_doc["ok"] is True
    assert val_doc["data"]["valid"] is True

    # TPL-06: theme profile contrast check
    bad_th = _call(
        api,
        "tpl.themes.save",
        {
            "institution_id": inst_id,
            "name": "Low Contrast",
            "surface_hex": "#FFFFFF",
            "text_hex": "#CBD5E1",
        },
    )
    assert bad_th["ok"] is False

    ok_th = _call(
        api,
        "tpl.themes.save",
        {
            "institution_id": inst_id,
            "name": "Ocean Ledger",
            "surface_hex": "#FFFFFF",
            "text_hex": "#0F172A",
        },
    )
    assert ok_th["ok"] is True
    assert ok_th["data"]["contrast_ratio"] > 10

    detail = _call(api, "tpl.detail", {"institution_id": inst_id})
    assert detail["data"]["paper_dimensions_mm"]["F4"] == (215.0, 330.0)
