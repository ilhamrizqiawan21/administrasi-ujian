"""Transactional service layer for LPJ-01..LPJ-05."""

from __future__ import annotations

import hashlib
import io
import json
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from docx import Document
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)
from sqlalchemy.orm import Session, sessionmaker

from backend.core.db import session_scope
from backend.core.errors import ConflictError, NotFoundError
from backend.core.paths import WorkspacePaths
from backend.modules.cfg.models import Institution
from backend.modules.cfg.repository import CfgRepository
from backend.modules.com.repository import ComRepository
from backend.modules.com.service import validate_signatories_list
from backend.modules.doc.models import DocumentRun
from backend.modules.doc.repository import DocRepository
from backend.modules.doc.service import sanitize_filename
from backend.modules.evt.models import Exam
from backend.modules.evt.repository import EvtRepository
from backend.modules.fin.repository import FinRepository
from backend.modules.lpj.models import LpjAttachment, LpjEvaluation, LpjVersion
from backend.modules.lpj.repository import LpjRepository
from backend.modules.lpj.schemas import (
    LpjAttachmentSavePayload,
    LpjCreateVersionPayload,
    LpjEvaluationSavePayload,
    LpjExportPayload,
    LpjFinalizePayload,
    LpjScopedPayload,
    LpjSectionSavePayload,
)
from backend.modules.ops.repository import OpsRepository

DEFAULT_SECTIONS: list[tuple[str, str]] = [
    ("cover", "Halaman Sampul"),
    ("approval", "Lembar Pengesahan"),
    ("intro", "Kata Pengantar"),
    ("basis", "Dasar Pelaksanaan"),
    ("purpose", "Tujuan Kegiatan"),
    ("program", "Program Kerja"),
    ("committee", "Susunan Kepanitiaan"),
    ("participants", "Rekapitulasi Peserta"),
    ("schedule", "Jadwal Pelaksanaan"),
    ("realization", "Realisasi Pelaksanaan & Presensi"),
    ("incidents", "Kejadian Khusus & Berita Acara"),
    ("finance_reconciliation", "Rekonsiliasi Keuangan & Honor"),
    ("evaluation", "Evaluasi & Rekomendasi"),
    ("closing", "Penutup"),
    ("appendices", "Daftar Lampiran"),
]

SECTION_KEYS = {k for k, _ in DEFAULT_SECTIONS}


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()


def _new_id() -> str:
    return uuid.uuid4().hex


def _atomic_write(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_bytes(data)
    tmp.replace(path)


def _default_sections_dict(exam_name: str) -> dict[str, dict[str, str]]:
    out: dict[str, dict[str, str]] = {}
    for key, title in DEFAULT_SECTIONS:
        default_text = (
            f"Laporan Pertanggungjawaban {exam_name}."
            if key == "cover"
            else f"Bagian {title} untuk kegiatan {exam_name}."
        )
        out[key] = {"title": title, "narrative": default_text}
    return out


class LpjService:
    """Application service for LPJ Builder, Evaluation, Finalization & Export."""

    def __init__(
        self, session_factory: sessionmaker[Session], paths: WorkspacePaths
    ) -> None:
        self._session_factory = session_factory
        self._paths = paths
        self._repo = LpjRepository()
        self._cfg_repo = CfgRepository()
        self._evt_repo = EvtRepository()
        self._com_repo = ComRepository()
        self._ops_repo = OpsRepository()
        self._fin_repo = FinRepository()
        self._doc_repo = DocRepository()

    def _require_exam(
        self, session: Session, institution_id: str, exam_id: str
    ) -> tuple[Institution, Exam]:
        inst = self._cfg_repo.get_institution(session, institution_id)
        if inst is None:
            raise NotFoundError("Lembaga tidak ditemukan.")
        exam = self._evt_repo.get_exam(session, institution_id, exam_id)
        if exam is None:
            raise NotFoundError("Kegiatan ujian tidak ditemukan.")
        return inst, exam

    def _compute_derived_snapshot(
        self, session: Session, inst: Institution, exam: Exam
    ) -> dict[str, Any]:
        parts = self._evt_repo.list_participants(session, exam.id)
        eligible = [p for p in parts if p.eligibility == "eligible"]
        rooms = self._evt_repo.list_rooms(session, exam.id)

        committee_members = self._com_repo.list_members(session, exam.id)
        signatories = self._com_repo.list_signatories(session, exam.id)
        sig_val = validate_signatories_list(signatories)

        part_att = self._ops_repo.list_participant_attendance(session, exam.id)
        staff_att = self._ops_repo.list_staff_attendance(session, exam.id)
        incidents = self._ops_repo.list_incidents(session, exam.id)
        reports = self._ops_repo.list_session_reports(session, exam.id)

        budget_versions = self._fin_repo.list_budget_versions(session, exam.id)
        approved_bv = next(
            (bv for bv in budget_versions if bv.state == "approved"), None
        )
        rab_total_idr = 0
        if approved_bv is not None:
            rab_total_idr = sum(
                ln.amount_idr
                for ln in self._fin_repo.list_budget_lines(session, approved_bv.id)
            )
        any_budget_lines = any(
            len(self._fin_repo.list_budget_lines(session, bv.id)) > 0
            for bv in budget_versions
        )

        ledger_entries = self._fin_repo.list_ledger_entries(session, exam.id)
        posted_entries = [e for e in ledger_entries if e.state == "posted"]
        draft_ledger_count = sum(1 for e in ledger_entries if e.state == "draft")
        total_income_idr = sum(
            e.amount_idr for e in posted_entries if e.kind == "income"
        )
        total_expense_idr = sum(
            e.amount_idr for e in posted_entries if e.kind == "expense"
        )
        closing_balance_idr = total_income_idr - total_expense_idr

        honor_lines = self._fin_repo.list_honor_lines(session, exam.id)
        honor_total_idr = sum(h.amount_idr for h in honor_lines)
        honor_paid_idr = sum(h.amount_idr for h in honor_lines if h.state == "paid")

        doc_runs = self._doc_repo.list_runs(session, exam.id)

        return {
            "source_versions": {
                "institution_id": inst.id,
                "exam_id": exam.id,
                "exam_status": exam.state,
                "approved_budget_version": approved_bv.number if approved_bv else None,
                "document_runs_count": len(doc_runs),
            },
            "derived_totals": {
                "participants_total": len(parts),
                "participants_eligible": len(eligible),
                "rooms_total": len(rooms),
                "committee_members_total": len(committee_members),
                "participant_present": sum(1 for a in part_att if a.state == "present"),
                "participant_absent": sum(1 for a in part_att if a.state == "absent"),
                "staff_present": sum(
                    1 for s in staff_att if s.state in ("present", "replaced")
                ),
                "staff_absent": sum(1 for s in staff_att if s.state == "absent"),
                "incidents_total": len(incidents),
                "session_reports_total": len(reports),
                "rab_approved_idr": rab_total_idr,
                "ledger_income_idr": total_income_idr,
                "ledger_expense_idr": total_expense_idr,
                "ledger_closing_balance_idr": closing_balance_idr,
                "draft_ledger_count": draft_ledger_count,
                "honor_total_idr": honor_total_idr,
                "honor_paid_idr": honor_paid_idr,
            },
            "policy_checks": {
                "signatories_valid": bool(sig_val["valid"]),
                "missing_signatories": sig_val["missing_required"],
                "has_unapproved_budget_only": bool(
                    any_budget_lines and approved_bv is None
                ),
                "draft_ledger_count": draft_ledger_count,
                "closing_balance_idr": closing_balance_idr,
            },
        }

    def _ensure_editable_version(self, session: Session, ver: LpjVersion) -> LpjVersion:
        """Clone finalized version into a new draft revision (LPJ-04)."""
        if ver.state != "final":
            return ver
        now = _now_iso()
        next_num = self._repo.max_version_number(session, ver.exam_id) + 1
        cloned = LpjVersion(
            id=_new_id(),
            institution_id=ver.institution_id,
            exam_id=ver.exam_id,
            version=next_num,
            state="draft",
            title=ver.title,
            sections_json=ver.sections_json,
            snapshot_json=ver.snapshot_json,
            doc_run_id=None,
            finalized_at=None,
            created_at=now,
            updated_at=now,
        )
        session.add(cloned)
        session.flush()
        for ev in self._repo.list_evaluations(session, ver.id):
            session.add(
                LpjEvaluation(
                    id=_new_id(),
                    lpj_version_id=cloned.id,
                    incident_id=ev.incident_id,
                    issue_title=ev.issue_title,
                    resolution=ev.resolution,
                    recommendation=ev.recommendation,
                    pic_name=ev.pic_name,
                    notes=ev.notes,
                    sort_order=ev.sort_order,
                    created_at=now,
                )
            )
        for att in self._repo.list_attachments(session, ver.id):
            session.add(
                LpjAttachment(
                    id=_new_id(),
                    lpj_version_id=cloned.id,
                    doc_run_id=att.doc_run_id,
                    title=att.title,
                    file_path=att.file_path,
                    included=att.included,
                    exclusion_reason=att.exclusion_reason,
                    sort_order=att.sort_order,
                    created_at=now,
                )
            )
        session.flush()
        return cloned

    def _attachment_exists(self, att: LpjAttachment) -> bool:
        if not att.file_path.strip():
            return False
        p = Path(att.file_path)
        if not p.is_absolute():
            p = self._paths.root / att.file_path
        return p.exists() and p.is_file()

    def _build_detail(
        self,
        session: Session,
        inst: Institution,
        exam: Exam,
        active_version_id: str | None = None,
    ) -> dict[str, Any]:
        versions = self._repo.list_versions(session, exam.id)
        if not versions:
            now = _now_iso()
            initial = LpjVersion(
                id=_new_id(),
                institution_id=inst.id,
                exam_id=exam.id,
                version=1,
                state="draft",
                title=f"LPJ {exam.title}",
                sections_json=json.dumps(_default_sections_dict(exam.title)),
                snapshot_json=json.dumps(
                    self._compute_derived_snapshot(session, inst, exam)
                ),
                doc_run_id=None,
                finalized_at=None,
                created_at=now,
                updated_at=now,
            )
            session.add(initial)
            session.flush()
            versions = [initial]

        active = (
            next((v for v in versions if v.id == active_version_id), None)
            or versions[0]
        )
        live_snapshot = self._compute_derived_snapshot(session, inst, exam)
        if active.state == "draft":
            snapshot = live_snapshot
            active.snapshot_json = json.dumps(live_snapshot)
            session.flush()
        else:
            snapshot = json.loads(active.snapshot_json or "{}")

        sections_map = json.loads(active.sections_json or "{}")
        sections = [
            {
                "key": key,
                "title": sections_map.get(key, {}).get("title", title),
                "narrative": sections_map.get(key, {}).get("narrative", ""),
            }
            for key, title in DEFAULT_SECTIONS
        ]

        evals = self._repo.list_evaluations(session, active.id)
        atts = self._repo.list_attachments(session, active.id)
        missing_attachments = [
            a.title for a in atts if a.included == 1 and not self._attachment_exists(a)
        ]

        incidents = self._ops_repo.list_incidents(session, exam.id)
        doc_runs = self._doc_repo.list_runs(session, exam.id)

        return {
            "exam": {
                "id": exam.id,
                "code": exam.semester_label,
                "name": exam.title,
                "status": exam.state,
            },
            "versions": [
                {
                    "id": v.id,
                    "version": v.version,
                    "state": v.state,
                    "title": v.title,
                    "doc_run_id": v.doc_run_id,
                    "finalized_at": v.finalized_at,
                    "updated_at": v.updated_at,
                }
                for v in versions
            ],
            "active_version": {
                "id": active.id,
                "version": active.version,
                "state": active.state,
                "title": active.title,
                "doc_run_id": active.doc_run_id,
                "finalized_at": active.finalized_at,
            },
            "sections": sections,
            "snapshot": snapshot,
            "evaluations": [
                {
                    "id": ev.id,
                    "incident_id": ev.incident_id,
                    "issue_title": ev.issue_title,
                    "resolution": ev.resolution,
                    "recommendation": ev.recommendation,
                    "pic_name": ev.pic_name,
                    "notes": ev.notes,
                    "sort_order": ev.sort_order,
                }
                for ev in evals
            ],
            "attachments": [
                {
                    "id": a.id,
                    "doc_run_id": a.doc_run_id,
                    "title": a.title,
                    "file_path": a.file_path,
                    "included": a.included == 1,
                    "exclusion_reason": a.exclusion_reason,
                    "sort_order": a.sort_order,
                    "file_exists": self._attachment_exists(a),
                }
                for a in atts
            ],
            "missing_attachments": missing_attachments,
            "available_incidents": [
                {
                    "id": inc.id,
                    "type_code": inc.type_code,
                    "severity": inc.severity,
                    "summary": inc.note,
                }
                for inc in incidents
            ],
            "available_doc_runs": [
                {
                    "id": dr.id,
                    "doc_type": dr.doc_type,
                    "format": dr.format,
                    "status": dr.status,
                    "output_path": dr.output_path,
                }
                for dr in doc_runs
            ],
        }

    def get_detail(self, payload: LpjScopedPayload) -> dict[str, Any]:
        with session_scope(self._session_factory) as session:
            inst, exam = self._require_exam(
                session, payload.institution_id, payload.exam_id
            )
            return self._build_detail(session, inst, exam, payload.lpj_version_id)

    def create_version(self, payload: LpjCreateVersionPayload) -> dict[str, Any]:
        with session_scope(self._session_factory) as session:
            inst, exam = self._require_exam(
                session, payload.institution_id, payload.exam_id
            )
            now = _now_iso()
            next_num = self._repo.max_version_number(session, exam.id) + 1
            ver = LpjVersion(
                id=_new_id(),
                institution_id=inst.id,
                exam_id=exam.id,
                version=next_num,
                state="draft",
                title=(payload.title or f"LPJ {exam.title} v{next_num}").strip(),
                sections_json=json.dumps(_default_sections_dict(exam.title)),
                snapshot_json=json.dumps(
                    self._compute_derived_snapshot(session, inst, exam)
                ),
                doc_run_id=None,
                finalized_at=None,
                created_at=now,
                updated_at=now,
            )
            session.add(ver)
            session.flush()
            return self._build_detail(session, inst, exam, ver.id)

    def save_section(self, payload: LpjSectionSavePayload) -> dict[str, Any]:
        with session_scope(self._session_factory) as session:
            inst, exam = self._require_exam(
                session, payload.institution_id, payload.exam_id
            )
            if payload.section_key not in SECTION_KEYS:
                raise NotFoundError("Bagian LPJ tidak dikenal.")
            ver = self._repo.get_version(session, payload.lpj_version_id)
            if ver is None or ver.exam_id != exam.id:
                raise NotFoundError("Versi LPJ tidak ditemukan.")
            target = self._ensure_editable_version(session, ver)
            sections_map = json.loads(target.sections_json or "{}")
            title = dict(DEFAULT_SECTIONS).get(payload.section_key, payload.section_key)
            sections_map[payload.section_key] = {
                "title": title,
                "narrative": payload.narrative,
            }
            target.sections_json = json.dumps(sections_map)
            target.updated_at = _now_iso()
            session.flush()
            return self._build_detail(session, inst, exam, target.id)

    def save_evaluation(self, payload: LpjEvaluationSavePayload) -> dict[str, Any]:
        with session_scope(self._session_factory) as session:
            inst, exam = self._require_exam(
                session, payload.institution_id, payload.exam_id
            )
            ver = self._repo.get_version(session, payload.lpj_version_id)
            if ver is None or ver.exam_id != exam.id:
                raise NotFoundError("Versi LPJ tidak ditemukan.")
            if payload.incident_id:
                incidents = {
                    i.id for i in self._ops_repo.list_incidents(session, exam.id)
                }
                if payload.incident_id not in incidents:
                    raise NotFoundError("Insiden tidak ditemukan pada kegiatan ini.")

            was_final = ver.state == "final"
            target = self._ensure_editable_version(session, ver)
            now = _now_iso()
            ev = (
                self._repo.get_evaluation(session, payload.id)
                if payload.id and not was_final
                else None
            )
            if ev is None:
                ev = LpjEvaluation(
                    id=_new_id(),
                    lpj_version_id=target.id,
                    incident_id=payload.incident_id,
                    issue_title=payload.issue_title.strip(),
                    resolution=payload.resolution.strip(),
                    recommendation=payload.recommendation.strip(),
                    pic_name=payload.pic_name.strip(),
                    notes=payload.notes.strip(),
                    sort_order=payload.sort_order,
                    created_at=now,
                )
                session.add(ev)
            else:
                if ev.lpj_version_id != target.id:
                    raise NotFoundError("Item evaluasi tidak ditemukan.")
                ev.incident_id = payload.incident_id
                ev.issue_title = payload.issue_title.strip()
                ev.resolution = payload.resolution.strip()
                ev.recommendation = payload.recommendation.strip()
                ev.pic_name = payload.pic_name.strip()
                ev.notes = payload.notes.strip()
                ev.sort_order = payload.sort_order
            target.updated_at = now
            session.flush()
            return self._build_detail(session, inst, exam, target.id)

    def save_attachment(self, payload: LpjAttachmentSavePayload) -> dict[str, Any]:
        with session_scope(self._session_factory) as session:
            inst, exam = self._require_exam(
                session, payload.institution_id, payload.exam_id
            )
            ver = self._repo.get_version(session, payload.lpj_version_id)
            if ver is None or ver.exam_id != exam.id:
                raise NotFoundError("Versi LPJ tidak ditemukan.")

            resolved_path = payload.file_path.strip()
            if payload.doc_run_id:
                dr = self._doc_repo.get_run(session, exam.id, payload.doc_run_id)
                if dr is None:
                    raise NotFoundError("Dokumen lampiran tidak ditemukan.")
                if not resolved_path:
                    resolved_path = dr.output_path

            was_final = ver.state == "final"
            target = self._ensure_editable_version(session, ver)
            now = _now_iso()
            att = (
                self._repo.get_attachment(session, payload.id)
                if payload.id and not was_final
                else None
            )
            if att is None:
                att = LpjAttachment(
                    id=_new_id(),
                    lpj_version_id=target.id,
                    doc_run_id=payload.doc_run_id,
                    title=payload.title.strip(),
                    file_path=resolved_path,
                    included=1 if payload.included else 0,
                    exclusion_reason=payload.exclusion_reason.strip(),
                    sort_order=payload.sort_order,
                    created_at=now,
                )
                session.add(att)
            else:
                if att.lpj_version_id != target.id:
                    raise NotFoundError("Lampiran tidak ditemukan.")
                att.doc_run_id = payload.doc_run_id
                att.title = payload.title.strip()
                att.file_path = resolved_path
                att.included = 1 if payload.included else 0
                att.exclusion_reason = payload.exclusion_reason.strip()
                att.sort_order = payload.sort_order
            target.updated_at = now
            session.flush()
            return self._build_detail(session, inst, exam, target.id)

    def finalize(self, payload: LpjFinalizePayload) -> dict[str, Any]:
        with session_scope(self._session_factory) as session:
            inst, exam = self._require_exam(
                session, payload.institution_id, payload.exam_id
            )
            ver = self._repo.get_version(session, payload.lpj_version_id)
            if ver is None or ver.exam_id != exam.id:
                raise NotFoundError("Versi LPJ tidak ditemukan.")
            if ver.state == "final":
                raise ConflictError("Versi LPJ sudah berstatus final.")

            snapshot = self._compute_derived_snapshot(session, inst, exam)
            checks = snapshot["policy_checks"]
            blockers: list[str] = []
            if checks["draft_ledger_count"] > 0:
                cnt = checks["draft_ledger_count"]
                blockers.append(f"Masih ada {cnt} transaksi kas berstatus draft.")
            if checks["closing_balance_idr"] < 0:
                blockers.append("Saldo akhir kas negatif (tidak seimbang).")
            if checks["has_unapproved_budget_only"]:
                blockers.append(
                    "RAB memiliki rincian tetapi belum ada versi yang disetujui."
                )
            if not checks["signatories_valid"]:
                blockers.append(
                    "Penanda tangan wajib belum lengkap: "
                    + ", ".join(checks["missing_signatories"])
                )

            atts = self._repo.list_attachments(session, ver.id)
            missing = [
                a.title
                for a in atts
                if a.included == 1 and not self._attachment_exists(a)
            ]
            if missing:
                blockers.append(
                    "Lampiran tidak ditemukan (perbaiki atau kecualikan eksplisit): "
                    + ", ".join(missing)
                )

            if blockers:
                raise ConflictError("Finalisasi LPJ ditolak: " + " ".join(blockers))

            now = _now_iso()
            ver.snapshot_json = json.dumps(snapshot)
            ver.state = "final"
            ver.finalized_at = now
            ver.updated_at = now
            session.flush()
            return self._build_detail(session, inst, exam, ver.id)

    def _render_lpj_pdf(
        self,
        *,
        inst: Institution,
        exam: Exam,
        ver: LpjVersion,
        sections: list[dict[str, str]],
        snapshot: dict[str, Any],
        evals: list[LpjEvaluation],
        atts: list[LpjAttachment],
        paper_size: str,
    ) -> bytes:
        buf = io.BytesIO()
        pagesize = (215.0 * mm, 330.0 * mm) if paper_size == "F4" else A4
        doc = SimpleDocTemplate(
            buf,
            pagesize=pagesize,
            leftMargin=18 * mm,
            rightMargin=18 * mm,
            topMargin=18 * mm,
            bottomMargin=18 * mm,
        )
        styles = getSampleStyleSheet()
        story: list[Any] = []

        # Page 1: Cover
        story.append(Spacer(1, 30 * mm))
        story.append(Paragraph(f"<b>{ver.title}</b>", styles["Title"]))
        story.append(Spacer(1, 6 * mm))
        story.append(
            Paragraph(
                f"{inst.name} — Kegiatan: {exam.title} ({exam.semester_label})",
                styles["Heading2"],
            )
        )
        story.append(
            Paragraph(
                f"Versi LPJ: v{ver.version} ({ver.state.upper()})",
                styles["Normal"],
            )
        )
        story.append(PageBreak())

        # Page 2: Table of Contents / Daftar Isi & Pengesahan
        story.append(
            Paragraph("<b>Daftar Isi & Ringkasan Bagian</b>", styles["Heading1"])
        )
        toc_rows: list[list[Any]] = [["No", "Bagian", "Status"]]
        for idx, sec in enumerate(sections, start=1):
            toc_rows.append(
                [str(idx), sec["title"], "Terisi" if sec["narrative"].strip() else "-"]
            )
        toc_table = Table(toc_rows, repeatRows=1)
        toc_table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#E2E8F0")),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#94A3B8")),
                    ("PADDING", (0, 0), (-1, -1), 5),
                ]
            )
        )
        story.append(toc_table)
        story.append(PageBreak())

        # Page 3+: Structured Sections + Derived Readonly Totals
        for sec in sections:
            story.append(Paragraph(f"<b>{sec['title']}</b>", styles["Heading2"]))
            story.append(Paragraph(sec["narrative"] or "-", styles["Normal"]))
            story.append(Spacer(1, 4 * mm))

        totals = snapshot.get("derived_totals", {})
        story.append(
            Paragraph("<b>Ringkasan Data Turunan (Read-Only)</b>", styles["Heading2"])
        )
        summary_rows: list[list[Any]] = [
            ["Metrik", "Nilai"],
            ["Peserta Eligible", str(totals.get("participants_eligible", 0))],
            ["Hadir Peserta", str(totals.get("participant_present", 0))],
            ["Hadir Pengawas", str(totals.get("staff_present", 0))],
            ["Insiden Tercatat", str(totals.get("incidents_total", 0))],
            ["RAB Disetujui (IDR)", str(totals.get("rab_approved_idr", 0))],
            ["Pemasukan Kas (IDR)", str(totals.get("ledger_income_idr", 0))],
            ["Pengeluaran Kas (IDR)", str(totals.get("ledger_expense_idr", 0))],
            ["Saldo Akhir Kas (IDR)", str(totals.get("ledger_closing_balance_idr", 0))],
            ["Total Honor (IDR)", str(totals.get("honor_total_idr", 0))],
        ]
        sum_tbl = Table(summary_rows, repeatRows=1)
        sum_tbl.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#E2E8F0")),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#94A3B8")),
                    ("PADDING", (0, 0), (-1, -1), 5),
                ]
            )
        )
        story.append(sum_tbl)
        story.append(PageBreak())

        # Final Page: Evaluation & Appendix Manifest
        story.append(Paragraph("<b>Evaluasi & Rekomendasi</b>", styles["Heading2"]))
        eval_rows: list[list[Any]] = [["Isu", "Solusi", "Rekomendasi", "PIC"]]
        if evals:
            for ev in evals:
                eval_rows.append(
                    [
                        ev.issue_title,
                        ev.resolution or "-",
                        ev.recommendation or "-",
                        ev.pic_name or "-",
                    ]
                )
        else:
            eval_rows.append(["Tidak ada isu tercatat", "-", "-", "-"])
        ev_tbl = Table(eval_rows, repeatRows=1)
        ev_tbl.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#E2E8F0")),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#94A3B8")),
                    ("PADDING", (0, 0), (-1, -1), 5),
                ]
            )
        )
        story.append(ev_tbl)
        story.append(Spacer(1, 6 * mm))

        story.append(
            Paragraph("<b>Daftar Lampiran (Appendix Pack)</b>", styles["Heading2"])
        )
        att_rows: list[list[Any]] = [["No", "Judul Lampiran", "Status", "Catatan"]]
        if atts:
            for idx, a in enumerate(atts, start=1):
                att_rows.append(
                    [
                        str(idx),
                        a.title,
                        "Disertakan" if a.included == 1 else "Dikecualikan",
                        a.exclusion_reason or a.file_path or "-",
                    ]
                )
        else:
            att_rows.append(["1", "Belum ada lampiran terdaftar", "-", "-"])
        att_tbl = Table(att_rows, repeatRows=1)
        att_tbl.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#E2E8F0")),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#94A3B8")),
                    ("PADDING", (0, 0), (-1, -1), 5),
                ]
            )
        )
        story.append(att_tbl)

        doc.build(story)
        return buf.getvalue()

    def _render_lpj_docx(
        self,
        *,
        inst: Institution,
        exam: Exam,
        ver: LpjVersion,
        sections: list[dict[str, str]],
        snapshot: dict[str, Any],
        evals: list[LpjEvaluation],
        atts: list[LpjAttachment],
    ) -> bytes:
        doc = Document()
        doc.add_heading(ver.title, level=0)
        doc.add_paragraph(f"{inst.name} — {exam.title} ({exam.semester_label})")
        doc.add_paragraph(f"Versi: v{ver.version} ({ver.state.upper()})")
        doc.add_page_break()  # type: ignore[no-untyped-call]

        doc.add_heading("Daftar Isi", level=1)
        for idx, sec in enumerate(sections, start=1):
            doc.add_paragraph(f"{idx}. {sec['title']}")
        doc.add_page_break()  # type: ignore[no-untyped-call]

        for sec in sections:
            doc.add_heading(sec["title"], level=2)
            doc.add_paragraph(sec["narrative"] or "-")

        totals = snapshot.get("derived_totals", {})
        doc.add_heading("Ringkasan Data Turunan (Read-Only)", level=2)
        tbl = doc.add_table(rows=1, cols=2)
        tbl.rows[0].cells[0].text = "Metrik"
        tbl.rows[0].cells[1].text = "Nilai"
        for label, key in [
            ("Peserta Eligible", "participants_eligible"),
            ("RAB Disetujui (IDR)", "rab_approved_idr"),
            ("Saldo Akhir Kas (IDR)", "ledger_closing_balance_idr"),
            ("Total Honor (IDR)", "honor_total_idr"),
        ]:
            row = tbl.add_row()
            row.cells[0].text = label
            row.cells[1].text = str(totals.get(key, 0))

        doc.add_heading("Evaluasi & Rekomendasi", level=2)
        for ev in evals:
            doc.add_paragraph(
                f"- {ev.issue_title} | Solusi: {ev.resolution} | PIC: {ev.pic_name}"
            )

        doc.add_heading("Daftar Lampiran", level=2)
        for idx, a in enumerate(atts, start=1):
            status = (
                "Disertakan"
                if a.included == 1
                else f"Dikecualikan ({a.exclusion_reason})"
            )
            doc.add_paragraph(f"{idx}. {a.title} [{status}]")

        out = io.BytesIO()
        doc.save(out)
        return out.getvalue()

    def export(self, payload: LpjExportPayload) -> dict[str, Any]:
        with session_scope(self._session_factory) as session:
            inst, exam = self._require_exam(
                session, payload.institution_id, payload.exam_id
            )
            ver = self._repo.get_version(session, payload.lpj_version_id)
            if ver is None or ver.exam_id != exam.id:
                raise NotFoundError("Versi LPJ tidak ditemukan.")

            detail = self._build_detail(session, inst, exam, ver.id)
            sections = detail["sections"]
            snapshot = detail["snapshot"]
            evals = self._repo.list_evaluations(session, ver.id)
            atts = self._repo.list_attachments(session, ver.id)

            if payload.format == "pdf":
                content = self._render_lpj_pdf(
                    inst=inst,
                    exam=exam,
                    ver=ver,
                    sections=sections,
                    snapshot=snapshot,
                    evals=evals,
                    atts=atts,
                    paper_size=payload.paper_size,
                )
            else:
                content = self._render_lpj_docx(
                    inst=inst,
                    exam=exam,
                    ver=ver,
                    sections=sections,
                    snapshot=snapshot,
                    evals=evals,
                    atts=atts,
                )

            now = _now_iso()
            ext = payload.format
            fname = sanitize_filename(
                f"lpj_{exam.title}_v{ver.version}_{ver.state}.{ext}"
            )
            rel_path = f"exports/{inst.id}/{exam.id}/{fname}"
            abs_path = self._paths.root / rel_path
            _atomic_write(abs_path, content)
            digest = hashlib.sha256(content).hexdigest()

            run = DocumentRun(
                id=_new_id(),
                institution_id=inst.id,
                exam_id=exam.id,
                plan_id=None,
                doc_type="lpj_kegiatan",
                format=payload.format,
                template_id=None,
                context_hash=digest[:16],
                scope_json=json.dumps({"lpj_version": ver.version, "state": ver.state}),
                status="final" if ver.state == "final" else "preview",
                output_path=rel_path,
                output_hash=digest,
                generated_at=now,
                created_at=now,
            )
            session.add(run)
            session.flush()
            ver.doc_run_id = run.id
            ver.updated_at = now
            session.flush()

            return {
                "doc_run_id": run.id,
                "lpj_version_id": ver.id,
                "version": ver.version,
                "state": ver.state,
                "format": payload.format,
                "output_path": rel_path,
                "output_hash": digest,
                "byte_size": len(content),
            }
