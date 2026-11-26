"""Integration tests for ARC-01..ARC-04 via BridgeApi."""

from __future__ import annotations

import zipfile
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from backend.bridge.api import BridgeApi
from backend.core.app_shell import bootstrap_runtime
from backend.core.db import session_scope
from backend.modules.doc.models import DocumentRun
from backend.modules.evt.models import Exam, ExamSubject


def _call(
    api: BridgeApi, method: str, payload: dict[str, Any] | None = None
) -> dict[str, Any]:
    return api.invoke(
        {"request_id": f"req-{method}", "method": method, "payload": payload or {}}
    )


def test_arc_bridge_end_to_end(tmp_path: Path) -> None:
    runtime = bootstrap_runtime(workspace_root=tmp_path, institution_slug="arc_bridge")
    api = BridgeApi(runtime=runtime)

    inst_id = _call(
        api,
        "cfg.first_run.setup",
        {
            "name": "SMAN 1 Harapan",
            "level_preset": "SMA/MA",
            "academic_year_label": "2024/2025",
        },
    )["data"]["institution"]["id"]
    year_2024 = _call(api, "cfg.years.list", {"institution_id": inst_id})["data"][
        "items"
    ][0]["id"]
    year_2026 = _call(
        api,
        "cfg.years.save",
        {
            "institution_id": inst_id,
            "label": "2026/2027",
            "starts_on": "2026-07-01",
            "ends_on": "2027-06-30",
        },
    )["data"]["year"]["id"]
    exam_type_id = _call(api, "cfg.exam_types.list", {"institution_id": inst_id})[
        "data"
    ]["items"][0]["id"]

    exam_id = _call(
        api,
        "evt.exams.create",
        {
            "institution_id": inst_id,
            "year_id": year_2024,
            "exam_type_id": exam_type_id,
            "title": "PAS Ganjil 2024",
            "semester_label": "Ganjil",
            "starts_on": "2024-12-01",
            "ends_on": "2024-12-06",
        },
    )["data"]["exam"]["id"]

    # Add structural policies & sample document
    _call(
        api,
        "mst.students.save",
        {
            "institution_id": inst_id,
            "nis": "00123",
            "full_name": "Budi Santoso",
            "active": True,
        },
    )
    _call(
        api,
        "evt.people.generate",
        {"institution_id": inst_id, "exam_id": exam_id, "kind": "student"},
    )
    _call(
        api,
        "evt.subjects.save",
        {
            "institution_id": inst_id,
            "exam_id": exam_id,
            "code": "MAT",
            "name": "Matematika",
        },
    )
    _call(
        api,
        "com.roles.save",
        {
            "institution_id": inst_id,
            "exam_id": exam_id,
            "name": "Ketua Panitia",
            "sort_order": 1,
            "jobdesc": "Koordinasi umum",
        },
    )
    _call(
        api,
        "fin.categories.save",
        {"institution_id": inst_id, "exam_id": exam_id, "label": "Konsumsi"},
    )

    sample_pdf = runtime.paths.exports_dir / "kartu_peserta.pdf"
    sample_pdf.parent.mkdir(parents=True, exist_ok=True)
    sample_pdf.write_bytes(b"%PDF-1.4\n%sample\n")
    with session_scope(runtime.session_factory) as session:
        session.add(
            ExamSubject(
                id="subj-mat-1",
                exam_id=exam_id,
                source_subject_id=None,
                code="MAT",
                name="Matematika",
                revision=1,
                created_at=datetime.now(UTC).isoformat(),
                updated_at=datetime.now(UTC).isoformat(),
            )
        )
        session.add(
            DocumentRun(
                id="doc-run-1",
                institution_id=inst_id,
                exam_id=exam_id,
                plan_id=None,
                doc_type="cards",
                format="pdf",
                template_id=None,
                context_hash="abc123",
                scope_json="{}",
                status="final",
                output_path="exports/kartu_peserta.pdf",
                output_hash="deadbeef",
                generated_at=datetime.now(UTC).isoformat(),
                created_at=datetime.now(UTC).isoformat(),
            )
        )
        exam_row = session.get(Exam, exam_id)
        assert exam_row is not None
        exam_row.state = "COMPLETED"

    # ARC-01: archive and verify read-only lock through bridge
    arc_res = _call(
        api, "arc.events.archive", {"institution_id": inst_id, "exam_id": exam_id}
    )
    assert arc_res["ok"] is True
    assert arc_res["data"]["state"] == "ARCHIVED"

    edit_blocked = _call(
        api,
        "evt.exams.update",
        {
            "institution_id": inst_id,
            "exam_id": exam_id,
            "title": "Ubah Judul",
            "semester_label": "Ganjil",
            "starts_on": "2024-12-01",
            "ends_on": "2024-12-06",
            "mode": "paper",
            "revision": 2,
        },
    )
    assert edit_blocked["ok"] is False

    listed = _call(
        api,
        "arc.events.list",
        {"institution_id": inst_id, "year_id": year_2024, "state": "ARCHIVED"},
    )
    assert listed["ok"] is True
    assert len(listed["data"]["items"]) == 1

    detail = _call(
        api, "arc.events.detail", {"institution_id": inst_id, "exam_id": exam_id}
    )
    assert detail["ok"] is True
    assert detail["data"]["exam"]["is_archived"] is True
    assert detail["data"]["counts"]["documents"] == 1

    # ARC-02: export ZIP without & with personal info, then verify hashes
    pkg_no_pii = _call(
        api,
        "arc.package.export",
        {
            "institution_id": inst_id,
            "exam_id": exam_id,
            "include_personal_info": False,
            "include_documents": True,
        },
    )
    assert pkg_no_pii["ok"] is True
    zip_path_1 = runtime.paths.root / pkg_no_pii["data"]["file_path"]
    with zipfile.ZipFile(zip_path_1, "r") as zf:
        names = set(zf.namelist())
        assert "manifest.json" in names
        assert "metadata/event.json" in names
        assert "documents/kartu_peserta.pdf" in names
        assert "metadata/participants.json" not in names

    verify_1 = _call(
        api,
        "arc.package.verify",
        {"institution_id": inst_id, "package_id": pkg_no_pii["data"]["id"]},
    )
    assert verify_1["ok"] is True
    assert verify_1["data"]["valid"] is True

    pkg_with_pii = _call(
        api,
        "arc.package.export",
        {
            "institution_id": inst_id,
            "exam_id": exam_id,
            "include_personal_info": True,
            "include_documents": True,
            "output_filename": "arsip_lengkap.zip",
        },
    )
    assert pkg_with_pii["ok"] is True
    zip_path_2 = runtime.paths.root / pkg_with_pii["data"]["file_path"]
    with zipfile.ZipFile(zip_path_2, "r") as zf:
        assert "metadata/participants.json" in zf.namelist()

    # ARC-03: duplicate policies into new DRAFT event
    dup_res = _call(
        api,
        "arc.events.duplicate",
        {
            "institution_id": inst_id,
            "source_exam_id": exam_id,
            "target_year_id": year_2026,
            "title": "PAS Ganjil 2026",
            "semester_label": "Ganjil",
            "starts_on": "2026-12-01",
            "ends_on": "2026-12-06",
        },
    )
    assert dup_res["ok"] is True, dup_res
    new_exam_id = dup_res["data"]["id"]
    assert dup_res["data"]["state"] == "DRAFT"
    assert dup_res["data"]["cloned"]["subjects"] == 1
    assert dup_res["data"]["cloned"]["roles"] == 1
    assert dup_res["data"]["cloned"]["budget_categories"] == 1

    new_detail = _call(
        api, "arc.events.detail", {"institution_id": inst_id, "exam_id": new_exam_id}
    )
    assert new_detail["data"]["counts"]["people"] == 0
    assert new_detail["data"]["counts"]["documents"] == 0

    # ARC-04: retention review, impact preview, authorized purge with backup
    rev = _call(
        api,
        "arc.retention.review",
        {"institution_id": inst_id, "min_age_days": 300},
    )
    assert rev["ok"] is True
    old_row = next(e for e in rev["data"]["events"] if e["id"] == exam_id)
    assert old_row["eligible_for_purge"] is True

    prev = _call(
        api, "arc.retention.preview", {"institution_id": inst_id, "exam_id": exam_id}
    )
    assert prev["ok"] is True
    assert prev["data"]["can_purge"] is True
    assert prev["data"]["impact_counts"]["documents"] == 1

    bad_purge = _call(
        api,
        "arc.retention.purge",
        {
            "institution_id": inst_id,
            "exam_id": exam_id,
            "authorized_by": "Kepala Sekolah",
            "confirm_title": "SALAH",
        },
    )
    assert bad_purge["ok"] is False

    purge = _call(
        api,
        "arc.retention.purge",
        {
            "institution_id": inst_id,
            "exam_id": exam_id,
            "authorized_by": "Kepala Sekolah",
            "confirm_title": "PAS Ganjil 2024",
        },
    )
    assert purge["ok"] is True
    bak_file = runtime.paths.root / purge["data"]["backup"]["file_path"]
    assert bak_file.exists()

    rev_after = _call(
        api,
        "arc.retention.review",
        {"institution_id": inst_id, "min_age_days": 300},
    )
    assert all(e["id"] != exam_id for e in rev_after["data"]["events"])
    assert rev_after["data"]["last_good_backup"] is not None
