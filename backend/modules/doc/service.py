"""Transactional service layer for DOC-01..DOC-09."""

from __future__ import annotations

import base64
import hashlib
import json
import re
import uuid
import zipfile
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from sqlalchemy.orm import Session, sessionmaker

from backend.core.db import session_scope
from backend.core.errors import ConflictError, NotFoundError, ValidationError
from backend.core.paths import WorkspacePaths
from backend.modules.cfg.models import Institution
from backend.modules.cfg.repository import CfgRepository
from backend.modules.com.repository import ComRepository
from backend.modules.com.service import validate_signatories_list
from backend.modules.doc.models import DocumentNumber, DocumentRun
from backend.modules.doc.renderers import (
    render_docx_bytes,
    render_pdf_bytes,
    render_xlsx_bytes,
)
from backend.modules.doc.repository import DocRepository
from backend.modules.doc.schemas import (
    DocBatchPayload,
    DocGeneratePayload,
    DocReprintPayload,
    DocScopedPayload,
)
from backend.modules.evt.models import Exam
from backend.modules.evt.repository import EvtRepository


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()


def _new_id() -> str:
    return uuid.uuid4().hex


def sanitize_filename(name: str) -> str:
    """Sanitize filename for safe export without path traversal (DOC-05)."""
    clean = re.sub(r"[^A-Za-z0-9._-]+", "_", name.strip())
    return clean.strip("._") or "dokumen"


def _atomic_write(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_bytes(data)
    tmp.replace(path)


class DocService:
    """Application service for Document Engine (DOC-01..DOC-09)."""

    def __init__(
        self, session_factory: sessionmaker[Session], paths: WorkspacePaths
    ) -> None:
        self._session_factory = session_factory
        self._paths = paths
        self._repo = DocRepository()
        self._cfg_repo = CfgRepository()
        self._evt_repo = EvtRepository()
        self._com_repo = ComRepository()

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

    def _build_context(
        self,
        session: Session,
        inst: Institution,
        exam: Exam,
        doc_type: str,
        *,
        is_final: bool,
    ) -> tuple[str, str, list[str], list[list[str]], list[dict[str, str]], str]:
        people = {p.id: p for p in self._evt_repo.list_people(session, exam.id)}
        parts = self._evt_repo.list_participants(session, exam.id)
        signatories = self._com_repo.list_signatories(session, exam.id)
        if is_final:
            sig_val = validate_signatories_list(signatories)
            if not sig_val["valid"]:
                raise ConflictError(
                    "Penanda tangan wajib belum lengkap: "
                    + ", ".join(sig_val["missing_required"])
                )

        headers: list[str] = ["No", "Kode/Nomor", "Nama", "Keterangan"]
        rows: list[list[str]] = []
        if doc_type in ("kartu_peserta", "daftar_hadir"):
            eligible = [pt for pt in parts if pt.eligibility == "eligible"]
            if is_final and doc_type == "kartu_peserta":
                missing_num = [
                    pt.id
                    for pt in eligible
                    if not (pt.participant_number or "").strip()
                ]
                if missing_num:
                    raise ConflictError(
                        f"Masih ada {len(missing_num)} peserta belum memiliki nomor."
                    )
            headers = ["No", "No. Peserta", "Nama Peserta", "Kelas"]
            for idx, pt in enumerate(eligible, start=1):
                person = people.get(pt.exam_person_id)
                rows.append(
                    [
                        str(idx),
                        pt.participant_number or "-",
                        person.display_name if person else "-",
                        person.class_label or "-" if person else "-",
                    ]
                )
        else:
            rooms = self._evt_repo.list_rooms(session, exam.id)
            headers = ["No", "Kode Ruang", "Nama Ruang", "Kapasitas"]
            for idx, rm in enumerate(rooms, start=1):
                rows.append([str(idx), rm.code, rm.name, str(rm.capacity_limit)])

        signers_out = [
            {
                "role_label": s.role_label,
                "signer_name": s.signer_name,
                "signer_title": s.signer_title,
                "signer_nip": s.signer_nip,
            }
            for s in signatories
        ]
        title = f"{doc_type.replace('_', ' ').title()} - {exam.title}"
        subtitle = f"{inst.name} | {exam.semester_label} | {exam.starts_on}"
        ctx_hash = hashlib.sha256(
            json.dumps(
                {
                    "doc_type": doc_type,
                    "title": title,
                    "subtitle": subtitle,
                    "rows": rows,
                    "signers": signers_out,
                },
                sort_keys=True,
            ).encode("utf-8")
        ).hexdigest()
        return title, subtitle, headers, rows, signers_out, ctx_hash

    def get_detail(self, payload: DocScopedPayload) -> dict[str, Any]:
        with session_scope(self._session_factory) as session:
            inst, exam = self._require_exam(
                session, payload.institution_id, payload.exam_id
            )
            runs = self._repo.list_runs(session, exam.id)
            current_hashes: dict[str, str] = {}
            runs_out = []
            nums_by_run: dict[str, str] = {}
            for run in runs:
                if run.doc_type not in current_hashes:
                    _, _, _, _, _, ch = self._build_context(
                        session, inst, exam, run.doc_type, is_final=False
                    )
                    current_hashes[run.doc_type] = ch
                is_stale = run.context_hash != current_hashes[run.doc_type]
                runs_out.append(
                    {
                        "id": run.id,
                        "doc_type": run.doc_type,
                        "format": run.format,
                        "status": run.status,
                        "document_number": nums_by_run.get(run.id),
                        "output_path": run.output_path,
                        "output_hash": run.output_hash,
                        "is_stale": is_stale,
                        "generated_at": run.generated_at,
                    }
                )
            return {"runs": runs_out}

    def generate_document(self, payload: DocGeneratePayload) -> dict[str, Any]:
        now = _now_iso()
        with session_scope(self._session_factory) as session:
            inst, exam = self._require_exam(
                session, payload.institution_id, payload.exam_id
            )
            title, subtitle, headers, rows, signers, ctx_hash = self._build_context(
                session, inst, exam, payload.doc_type, is_final=payload.is_final
            )

            doc_number_text = ""
            num_row: DocumentNumber | None = None
            if payload.is_final:
                existing_nums = self._repo.list_numbers(
                    session, inst.id, payload.series
                )
                next_seq = max((n.sequence for n in existing_nums), default=0) + 1
                doc_number_text = (
                    f"{next_seq:03d}/{payload.series}/{exam.starts_on[:4]}"
                )
                num_row = DocumentNumber(
                    id=_new_id(),
                    institution_id=inst.id,
                    exam_id=exam.id,
                    series=payload.series,
                    sequence=next_seq,
                    number_text=doc_number_text,
                    doc_run_id=None,
                    status="active",
                    created_at=now,
                )
                session.add(num_row)
                session.flush()

            try:
                if payload.format == "pdf":
                    out_bytes = render_pdf_bytes(
                        title=title,
                        subtitle=subtitle,
                        headers=headers,
                        rows=rows,
                        signers=signers,
                        paper_size=payload.paper_size,
                        doc_number=doc_number_text,
                    )
                elif payload.format == "docx":
                    out_bytes = render_docx_bytes(
                        title=title,
                        subtitle=subtitle,
                        headers=headers,
                        rows=rows,
                        signers=signers,
                    )
                else:
                    typed_rows: list[list[str | int]] = [
                        [str(c) for c in r] for r in rows
                    ]
                    out_bytes = render_xlsx_bytes(
                        sheet_title=payload.doc_type,
                        headers=headers,
                        rows=typed_rows,
                    )
            except Exception as exc:
                if num_row is not None:
                    num_row.status = "voided"
                raise ValidationError(f"Gagal merender dokumen: {exc}") from exc

            out_hash = hashlib.sha256(out_bytes).hexdigest()
            run_id = _new_id()
            fname = sanitize_filename(
                f"{payload.doc_type}_{run_id[:8]}.{payload.format}"
            )
            out_path = self._paths.exports_dir / fname
            _atomic_write(out_path, out_bytes)

            run = DocumentRun(
                id=run_id,
                institution_id=inst.id,
                exam_id=exam.id,
                plan_id=payload.plan_id,
                doc_type=payload.doc_type,
                format=payload.format,
                template_id=payload.template_id,
                context_hash=ctx_hash,
                scope_json=json.dumps(payload.scope),
                status="final" if payload.is_final else "preview",
                output_path=str(out_path),
                output_hash=out_hash,
                generated_at=now,
                created_at=now,
            )
            session.add(run)
            session.flush()
            if num_row is not None:
                num_row.doc_run_id = run.id
                session.flush()

            return {
                "run_id": run.id,
                "status": run.status,
                "document_number": doc_number_text or None,
                "output_path": str(out_path),
                "output_hash": out_hash,
                "bytes_b64": base64.b64encode(out_bytes).decode("ascii"),
            }

    def generate_batch(self, payload: DocBatchPayload) -> dict[str, Any]:
        now = _now_iso()
        with session_scope(self._session_factory) as session:
            inst, exam = self._require_exam(
                session, payload.institution_id, payload.exam_id
            )
            title, subtitle, headers, rows, signers, ctx_hash = self._build_context(
                session, inst, exam, payload.doc_type, is_final=False
            )
            labels = payload.item_labels or [
                f"Item-{i}" for i in range(1, len(rows) + 1)
            ]
            if not labels:
                labels = ["Batch-1"]

            run_id = _new_id()
            if payload.format == "pdf" and payload.combine_pdf:
                batch_rows = [
                    [str(i + 1), lbl, title, exam.title] for i, lbl in enumerate(labels)
                ]
                out_bytes = render_pdf_bytes(
                    title=title,
                    subtitle=subtitle,
                    headers=["No", "Label", "Dokumen", "Kegiatan"],
                    rows=batch_rows,
                    signers=signers,
                    paper_size=payload.paper_size,
                )
                ext = "pdf"
            else:
                import io

                buf = io.BytesIO()
                used_names: set[str] = set()
                with zipfile.ZipFile(buf, "w", compression=zipfile.ZIP_DEFLATED) as zf:
                    for idx, lbl in enumerate(labels, start=1):
                        base = sanitize_filename(f"{idx:03d}_{lbl}")
                        name = f"{base}.{payload.format}"
                        while name in used_names:
                            name = f"{base}_{idx}.{payload.format}"
                        used_names.add(name)
                        if payload.format == "pdf":
                            item_bytes = render_pdf_bytes(
                                title=f"{title} - {lbl}",
                                subtitle=subtitle,
                                headers=headers,
                                rows=rows[:5],
                                signers=signers,
                                paper_size=payload.paper_size,
                            )
                        else:
                            item_bytes = render_docx_bytes(
                                title=f"{title} - {lbl}",
                                subtitle=subtitle,
                                headers=headers,
                                rows=rows[:5],
                                signers=signers,
                            )
                        zf.writestr(name, item_bytes)
                out_bytes = buf.getvalue()
                ext = "zip"

            out_hash = hashlib.sha256(out_bytes).hexdigest()
            out_path = self._paths.exports_dir / sanitize_filename(
                f"batch_{payload.doc_type}_{run_id[:8]}.{ext}"
            )
            _atomic_write(out_path, out_bytes)

            run = DocumentRun(
                id=run_id,
                institution_id=inst.id,
                exam_id=exam.id,
                plan_id=payload.plan_id,
                doc_type=payload.doc_type,
                format=ext,
                template_id=None,
                context_hash=ctx_hash,
                scope_json=json.dumps({"count": len(labels)}),
                status="final",
                output_path=str(out_path),
                output_hash=out_hash,
                generated_at=now,
                created_at=now,
            )
            session.add(run)
            session.flush()
            return {
                "run_id": run.id,
                "item_count": len(labels),
                "output_path": str(out_path),
                "output_hash": out_hash,
            }

    def reprint_document(self, payload: DocReprintPayload) -> dict[str, Any]:
        with session_scope(self._session_factory) as session:
            _, exam = self._require_exam(
                session, payload.institution_id, payload.exam_id
            )
            run = self._repo.get_run(session, exam.id, payload.run_id)
            if run is None:
                raise NotFoundError("Riwayat dokumen tidak ditemukan.")
            p = Path(run.output_path)
            if not p.exists():
                raise NotFoundError("Berkas arsip dokumen tidak ditemukan di disk.")
            raw = p.read_bytes()
            actual_hash = hashlib.sha256(raw).hexdigest()
            if actual_hash != run.output_hash:
                raise ConflictError("Hash berkas arsip tidak cocok.")
            return {
                "run_id": run.id,
                "output_hash": actual_hash,
                "bytes_b64": base64.b64encode(raw).decode("ascii"),
            }
