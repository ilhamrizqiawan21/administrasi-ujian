"""Integration tests for LPJ-01..LPJ-05 via BridgeApi."""

from __future__ import annotations

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


def test_lpj_bridge_end_to_end(tmp_path: Path) -> None:
    runtime = bootstrap_runtime(workspace_root=tmp_path, institution_slug="lpj_bridge")
    api = BridgeApi(runtime=runtime)

    inst_id = _call(
        api,
        "cfg.first_run.setup",
        {
            "name": "SMPN 2 Nusantara",
            "level_preset": "SMP/MTs",
            "academic_year_label": "2026/2027",
        },
    )["data"]["institution"]["id"]
    year_id = _call(api, "cfg.years.list", {"institution_id": inst_id})["data"][
        "items"
    ][0]["id"]
    exam_type_id = _call(api, "cfg.exam_types.list", {"institution_id": inst_id})[
        "data"
    ]["items"][0]["id"]

    exam_id = _call(
        api,
        "evt.exams.create",
        {
            "institution_id": inst_id,
            "year_id": year_id,
            "exam_type_id": exam_type_id,
            "title": "PAS Ganjil LPJ",
            "semester_label": "Ganjil",
            "starts_on": "2026-12-01",
            "ends_on": "2026-12-05",
        },
    )["data"]["exam"]["id"]

    # Add required signatories so finalization policy passes when clean
    _call(
        api,
        "com.signatories.save",
        {
            "institution_id": inst_id,
            "exam_id": exam_id,
            "role_key": "ketua_panitia",
            "role_label": "Ketua Panitia",
            "signer_name": "Budi Santoso, S.Pd.",
            "signer_title": "Ketua Panitia Ujian",
            "required": True,
        },
    )
    _call(
        api,
        "com.signatories.save",
        {
            "institution_id": inst_id,
            "exam_id": exam_id,
            "role_key": "kepala_sekolah",
            "role_label": "Kepala Sekolah",
            "signer_name": "Dr. Sari Wijaya",
            "signer_title": "Kepala Sekolah",
            "required": True,
        },
    )

    cat_id = _call(
        api,
        "fin.categories.save",
        {"institution_id": inst_id, "exam_id": exam_id, "label": "Operasional"},
    )["data"]["id"]

    # Create posted income and one draft expense to test incomplete accounting guard
    inc_id = _call(
        api,
        "fin.ledger.save",
        {
            "institution_id": inst_id,
            "exam_id": exam_id,
            "category_id": cat_id,
            "kind": "income",
            "entry_date": "2026-11-25",
            "reference": "Dana BOS Ujian",
            "amount_idr": 2_000_000,
        },
    )["data"]["id"]
    _call(
        api,
        "fin.ledger.post",
        {"institution_id": inst_id, "exam_id": exam_id, "entry_id": inc_id},
    )

    draft_id = _call(
        api,
        "fin.ledger.save",
        {
            "institution_id": inst_id,
            "exam_id": exam_id,
            "category_id": cat_id,
            "kind": "expense",
            "entry_date": "2026-11-25",
            "reference": "Konsumsi Rapat",
            "amount_idr": 250_000,
        },
    )["data"]["id"]

    # LPJ-01: Initial detail & narrative edit does not overwrite derived totals
    detail = _call(api, "lpj.detail", {"institution_id": inst_id, "exam_id": exam_id})[
        "data"
    ]
    v1_id = detail["active_version"]["id"]
    assert detail["active_version"]["version"] == 1
    assert detail["snapshot"]["derived_totals"]["ledger_income_idr"] == 2_000_000

    edited = _call(
        api,
        "lpj.sections.save",
        {
            "institution_id": inst_id,
            "exam_id": exam_id,
            "lpj_version_id": v1_id,
            "section_key": "intro",
            "narrative": "Narasi pembuka resmi, tidak boleh mengubah angka kas 999.",
        },
    )["data"]
    assert edited["snapshot"]["derived_totals"]["ledger_income_idr"] == 2_000_000

    # LPJ-02: Evaluation item
    eval_res = _call(
        api,
        "lpj.evaluations.save",
        {
            "institution_id": inst_id,
            "exam_id": exam_id,
            "lpj_version_id": v1_id,
            "issue_title": "Keterlambatan distribusi soal ruang 3",
            "resolution": "Kurir cadangan dikerahkan dalam 5 menit",
            "recommendation": "Siapkan cadangan amplop per lantai",
            "pic_name": "Koordinator Naskah",
            "notes": "Selesai tanpa perpanjangan waktu",
        },
    )
    assert eval_res["ok"] is True
    assert len(eval_res["data"]["evaluations"]) == 1

    # LPJ-03: Missing attachment blocks final unless explicitly excluded
    att_res = _call(
        api,
        "lpj.attachments.save",
        {
            "institution_id": inst_id,
            "exam_id": exam_id,
            "lpj_version_id": v1_id,
            "title": "Rekap Arsip Fisik",
            "file_path": "exports/tidak_ada.pdf",
            "included": True,
        },
    )["data"]
    att_id = att_res["attachments"][0]["id"]
    assert "Rekap Arsip Fisik" in att_res["missing_attachments"]

    blocked = _call(
        api,
        "lpj.finalize",
        {"institution_id": inst_id, "exam_id": exam_id, "lpj_version_id": v1_id},
    )
    assert blocked["ok"] is False
    assert blocked["error"]["code"] == "CONFLICT"

    # Resolve blockers: post draft ledger entry + explicitly exclude missing attachment
    _call(
        api,
        "fin.ledger.post",
        {"institution_id": inst_id, "exam_id": exam_id, "entry_id": draft_id},
    )
    _call(
        api,
        "lpj.attachments.save",
        {
            "institution_id": inst_id,
            "exam_id": exam_id,
            "lpj_version_id": v1_id,
            "id": att_id,
            "title": "Rekap Arsip Fisik",
            "file_path": "exports/tidak_ada.pdf",
            "included": False,
            "exclusion_reason": "Disimpan terpisah di lemari arsip",
        },
    )

    # LPJ-04: Finalize succeeds
    finalized = _call(
        api,
        "lpj.finalize",
        {"institution_id": inst_id, "exam_id": exam_id, "lpj_version_id": v1_id},
    )
    assert finalized["ok"] is True
    assert finalized["data"]["active_version"]["state"] == "final"
    assert (
        finalized["data"]["snapshot"]["derived_totals"]["ledger_closing_balance_idr"]
        == 1_750_000
    )

    # LPJ-05: Export PDF and DOCX
    pdf_res = _call(
        api,
        "lpj.export",
        {
            "institution_id": inst_id,
            "exam_id": exam_id,
            "lpj_version_id": v1_id,
            "format": "pdf",
        },
    )
    assert pdf_res["ok"] is True
    pdf_path = runtime.paths.root / pdf_res["data"]["output_path"]
    assert pdf_path.exists()
    assert pdf_path.read_bytes().startswith(b"%PDF-")

    docx_res = _call(
        api,
        "lpj.export",
        {
            "institution_id": inst_id,
            "exam_id": exam_id,
            "lpj_version_id": v1_id,
            "format": "docx",
        },
    )
    assert docx_res["ok"] is True
    docx_path = runtime.paths.root / docx_res["data"]["output_path"]
    assert docx_path.exists()
    assert docx_path.stat().st_size > 1000

    # LPJ-04: Editing a finalized LPJ creates a new draft revision (v2) preserving v1
    v2_res = _call(
        api,
        "lpj.sections.save",
        {
            "institution_id": inst_id,
            "exam_id": exam_id,
            "lpj_version_id": v1_id,
            "section_key": "closing",
            "narrative": "Revisi penutup pada v2.",
        },
    )
    assert v2_res["ok"] is True
    assert v2_res["data"]["active_version"]["version"] == 2
    assert v2_res["data"]["active_version"]["state"] == "draft"
    v1_after = next(v for v in v2_res["data"]["versions"] if v["version"] == 1)
    assert v1_after["state"] == "final"
