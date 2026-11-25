"""Integration tests for DOC-01..DOC-09 via BridgeApi."""

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


def test_doc_bridge_end_to_end(tmp_path: Path) -> None:
    runtime = bootstrap_runtime(workspace_root=tmp_path, institution_slug="doc_bridge")
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
    year_id = _call(api, "cfg.years.list", {"institution_id": inst_id})["data"][
        "items"
    ][0]["id"]
    et_id = _call(api, "cfg.exam_types.list", {"institution_id": inst_id})["data"][
        "items"
    ][0]["id"]
    lvl_id = _call(api, "cfg.levels.list", {"institution_id": inst_id})["data"][
        "items"
    ][0]["id"]
    cls_id = _call(
        api,
        "mst.classes.save",
        {
            "institution_id": inst_id,
            "year_id": year_id,
            "level_id": lvl_id,
            "name": "7A",
        },
    )["data"]["class_item"]["id"]
    st_id = _call(
        api,
        "mst.students.save",
        {"institution_id": inst_id, "nis": "0001", "full_name": "Siswa 1"},
    )["data"]["student"]["id"]
    _call(
        api,
        "mst.enrollments.save",
        {
            "institution_id": inst_id,
            "year_id": year_id,
            "student_id": st_id,
            "class_id": cls_id,
        },
    )

    exam_id = _call(
        api,
        "evt.exams.create",
        {
            "institution_id": inst_id,
            "year_id": year_id,
            "exam_type_id": et_id,
            "title": "PAS Ganjil",
            "semester_label": "Ganjil",
            "starts_on": "2026-12-01",
            "ends_on": "2026-12-05",
        },
    )["data"]["exam"]["id"]

    # DOC-06: preview does not consume document number
    prev = _call(
        api,
        "doc.generate",
        {
            "institution_id": inst_id,
            "exam_id": exam_id,
            "doc_type": "daftar_hadir",
            "format": "pdf",
            "is_final": False,
        },
    )
    assert prev["ok"] is True
    assert prev["data"]["document_number"] is None

    # DOC-01: missing required participant_number blocks final kartu_peserta
    bad_final = _call(
        api,
        "doc.generate",
        {
            "institution_id": inst_id,
            "exam_id": exam_id,
            "doc_type": "kartu_peserta",
            "format": "pdf",
            "is_final": True,
        },
    )
    assert bad_final["ok"] is False
    assert bad_final["error"]["code"] == "CONFLICT"

    # Generate final daftar_hadir -> consumes number 001/UJN/2026
    fin = _call(
        api,
        "doc.generate",
        {
            "institution_id": inst_id,
            "exam_id": exam_id,
            "doc_type": "daftar_hadir",
            "format": "pdf",
            "is_final": True,
        },
    )
    assert fin["ok"] is True
    assert fin["data"]["document_number"] == "001/UJN/2026"

    # DOC-07: reprint returns byte-identical hash
    rep = _call(
        api,
        "doc.reprint",
        {
            "institution_id": inst_id,
            "exam_id": exam_id,
            "run_id": fin["data"]["run_id"],
        },
    )
    assert rep["ok"] is True
    assert rep["data"]["output_hash"] == fin["data"]["output_hash"]

    # DOC-05: batch 200 cards
    batch = _call(
        api,
        "doc.batch",
        {
            "institution_id": inst_id,
            "exam_id": exam_id,
            "doc_type": "kartu_peserta",
            "format": "pdf",
            "combine_pdf": True,
            "item_labels": [f"K-{i:03d}" for i in range(1, 201)],
        },
    )
    assert batch["ok"] is True
    assert batch["data"]["item_count"] == 200
