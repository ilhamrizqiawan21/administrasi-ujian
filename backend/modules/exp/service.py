"""Transactional service layer for EXP-01..EXP-06."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any
from zoneinfo import ZoneInfo

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker

from backend.core.db import session_scope
from backend.core.errors import ConflictError, NotFoundError
from backend.modules.cfg.models import Institution
from backend.modules.cfg.repository import CfgRepository
from backend.modules.evt.models import AuditEvent, Exam
from backend.modules.evt.repository import EvtRepository
from backend.modules.exp.models import (
    Handover,
    PrintQuantity,
    SubmissionItem,
    SubmissionVersion,
)
from backend.modules.exp.repository import ExpRepository
from backend.modules.exp.schemas import (
    ExpScopedPayload,
    HandoverRecordPayload,
    MatrixGeneratePayload,
    PrintComputePayload,
    PrintOverridePayload,
    SubmissionItemSavePayload,
    SubmissionReceivePayload,
    SubmissionReviewPayload,
)
from backend.modules.rom.repository import RomRepository
from backend.modules.ses.repository import SesRepository

ALLOWED_REVIEW_TRANSITIONS: dict[str, set[str]] = {
    "received": {"revision", "valid"},
    "revision": {"received", "valid"},
    "valid": {"ready", "revision"},
    "ready": {"revision"},
}


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()


def _new_id() -> str:
    return uuid.uuid4().hex


def validate_review_transition(current_state: str, new_state: str) -> bool:
    """Return True if review state transition is allowed (EXP-03)."""
    return new_state in ALLOWED_REVIEW_TRANSITIONS.get(current_state, set())


class ExpService:
    """Application service for Ekspedisi & Bahan (EXP-01..EXP-06)."""

    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._session_factory = session_factory
        self._repo = ExpRepository()
        self._evt_repo = EvtRepository()
        self._cfg_repo = CfgRepository()
        self._ses_repo = SesRepository()
        self._rom_repo = RomRepository()

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

    def get_detail(self, payload: ExpScopedPayload) -> dict[str, Any]:
        with session_scope(self._session_factory) as session:
            inst, exam = self._require_exam(
                session, payload.institution_id, payload.exam_id
            )
            tz = ZoneInfo(inst.timezone or "Asia/Jakarta")
            today_local = datetime.now(tz).date().isoformat()

            staff = self._evt_repo.list_people(session, exam.id, kind="staff")
            staff_map = {p.id: p for p in staff}

            items = self._repo.list_items(session, exam.id)
            items_out = []
            counts = {
                "total": len(items),
                "missing": 0,
                "received": 0,
                "revision": 0,
                "valid": 0,
                "ready": 0,
                "late": 0,
            }
            for it in items:
                counts[it.state] = counts.get(it.state, 0) + 1
                is_late = bool(
                    it.due_date
                    and it.due_date < today_local
                    and it.state in ("missing", "revision")
                )
                if is_late:
                    counts["late"] += 1
                versions = self._repo.list_versions(session, it.id)
                owner = staff_map.get(it.owner_id) if it.owner_id else None
                items_out.append(
                    {
                        "id": it.id,
                        "subject_label": it.subject_label,
                        "class_label": it.class_label,
                        "type_code": it.type_code,
                        "owner_id": it.owner_id,
                        "owner_name": owner.display_name if owner else None,
                        "due_date": it.due_date,
                        "is_late": is_late,
                        "state": it.state,
                        "current_version": it.current_version,
                        "versions": [
                            {
                                "id": v.id,
                                "version": v.version,
                                "asset_id": v.asset_id,
                                "received_at": v.received_at,
                                "state": v.state,
                                "note": v.note,
                            }
                            for v in versions
                        ],
                    }
                )

            pqs = self._repo.list_print_quantities(session, exam.id)
            pq_out = [
                {
                    "id": pq.id,
                    "plan_id": pq.plan_id,
                    "room_session_id": pq.room_session_id,
                    "requirement_id": pq.requirement_id,
                    "roster_count": pq.roster_count,
                    "reserve_count": pq.reserve_count,
                    "override_qty": pq.override_qty,
                    "exclude_cbt": bool(pq.exclude_cbt),
                    "effective_qty": (
                        pq.override_qty
                        if pq.override_qty is not None
                        else (pq.roster_count + pq.reserve_count)
                    ),
                }
                for pq in pqs
            ]

            handovers = self._repo.list_handovers(session, exam.id)
            ho_out = [
                {
                    "id": h.id,
                    "room_session_id": h.room_session_id,
                    "kind": h.kind,
                    "material_type": h.material_type,
                    "expected_qty": h.expected_qty,
                    "actual_qty": h.actual_qty,
                    "discrepancy": h.discrepancy,
                    "mismatch": h.discrepancy != 0,
                    "from_person_name": h.from_person_name,
                    "to_person_name": h.to_person_name,
                    "handed_at": h.handed_at,
                    "note": h.note,
                }
                for h in handovers
            ]

            return {
                "today_local": today_local,
                "staff": [
                    {"id": p.id, "code": p.code, "display_name": p.display_name}
                    for p in staff
                ],
                "items": items_out,
                "counts": counts,
                "print_quantities": pq_out,
                "handovers": ho_out,
            }

    def generate_matrix(self, payload: MatrixGeneratePayload) -> dict[str, Any]:
        now = _now_iso()
        with session_scope(self._session_factory) as session:
            _, exam = self._require_exam(
                session, payload.institution_id, payload.exam_id
            )
            groups = self._evt_repo.list_groups(session, exam.id)
            subjs = {
                es.id: es.name for es in self._evt_repo.list_subjects(session, exam.id)
            }
            existing_keys = {
                (it.subject_label, it.class_label, it.type_code)
                for it in self._repo.list_items(session, exam.id)
            }

            created = 0
            for grp in groups:
                for req in self._evt_repo.list_requirements(session, grp.id):
                    subj_label = subjs.get(req.exam_subject_id, req.exam_subject_id)
                    for tc in payload.item_types:
                        clean_tc = tc.strip()
                        if not clean_tc:
                            continue
                        key = (subj_label, grp.label, clean_tc)
                        if key in existing_keys:
                            continue
                        existing_keys.add(key)
                        session.add(
                            SubmissionItem(
                                id=_new_id(),
                                exam_id=exam.id,
                                requirement_id=req.id,
                                subject_label=subj_label,
                                class_label=grp.label,
                                type_code=clean_tc,
                                owner_id=None,
                                due_date=payload.due_date or exam.starts_on,
                                state="missing",
                                current_version=0,
                                revision=1,
                                created_at=now,
                                updated_at=now,
                            )
                        )
                        created += 1
            session.flush()
            return {"created_count": created}

    def save_item(self, payload: SubmissionItemSavePayload) -> dict[str, Any]:
        now = _now_iso()
        with session_scope(self._session_factory) as session:
            _, exam = self._require_exam(
                session, payload.institution_id, payload.exam_id
            )
            it = SubmissionItem(
                id=_new_id(),
                exam_id=exam.id,
                requirement_id=None,
                subject_label=payload.subject_label.strip(),
                class_label=payload.class_label.strip(),
                type_code=payload.type_code.strip(),
                owner_id=payload.owner_id,
                due_date=payload.due_date,
                state="missing",
                current_version=0,
                revision=1,
                created_at=now,
                updated_at=now,
            )
            session.add(it)
            try:
                session.flush()
            except IntegrityError as exc:
                raise ConflictError(
                    "Item ekspedisi untuk mapel/kelompok/jenis tersebut sudah ada."
                ) from exc
            return {"id": it.id}

    def receive_submission(self, payload: SubmissionReceivePayload) -> dict[str, Any]:
        now = _now_iso()
        with session_scope(self._session_factory) as session:
            _, exam = self._require_exam(
                session, payload.institution_id, payload.exam_id
            )
            it = self._repo.get_item(session, exam.id, payload.item_id)
            if it is None:
                raise NotFoundError("Item ekspedisi tidak ditemukan.")

            next_ver = it.current_version + 1
            session.add(
                SubmissionVersion(
                    id=_new_id(),
                    item_id=it.id,
                    version=next_ver,
                    asset_id=payload.asset_id,
                    received_at=payload.received_at,
                    reviewer_id=None,
                    state="received",
                    note=payload.note,
                    created_at=now,
                )
            )
            # Replacement invalidates prior validation/ready state (EXP-02)
            it.current_version = next_ver
            it.state = "received"
            it.revision += 1
            it.updated_at = now
            session.flush()
            return {"version": next_ver, "state": it.state}

    def review_submission(self, payload: SubmissionReviewPayload) -> dict[str, Any]:
        now = _now_iso()
        with session_scope(self._session_factory) as session:
            _, exam = self._require_exam(
                session, payload.institution_id, payload.exam_id
            )
            it = self._repo.get_item(session, exam.id, payload.item_id)
            if it is None:
                raise NotFoundError("Item ekspedisi tidak ditemukan.")
            if not validate_review_transition(it.state, payload.new_state):
                raise ConflictError(
                    f"Transisi status dari '{it.state}' ke '{payload.new_state}' "
                    "tidak diizinkan."
                )

            next_ver = it.current_version + 1
            versions = self._repo.list_versions(session, it.id)
            latest_asset = versions[0].asset_id if versions else ""
            session.add(
                SubmissionVersion(
                    id=_new_id(),
                    item_id=it.id,
                    version=next_ver,
                    asset_id=latest_asset,
                    received_at=now,
                    reviewer_id=payload.reviewer_id,
                    state=payload.new_state,
                    note=payload.note,
                    created_at=now,
                )
            )
            it.current_version = next_ver
            it.state = payload.new_state
            it.revision += 1
            it.updated_at = now
            session.flush()
            return {"version": next_ver, "state": it.state}

    def compute_print_quantities(self, payload: PrintComputePayload) -> dict[str, Any]:
        now = _now_iso()
        with session_scope(self._session_factory) as session:
            _, exam = self._require_exam(
                session, payload.institution_id, payload.exam_id
            )
            plan = self._ses_repo.get_plan(session, exam.id, payload.plan_id)
            if plan is None:
                raise NotFoundError("Rencana jadwal tidak ditemukan.")

            for old in self._repo.list_print_quantities(session, exam.id):
                session.delete(old)
            session.flush()

            groups = self._evt_repo.list_groups(session, exam.id)
            reqs_mode: dict[str, str] = {}
            for grp in groups:
                for req in self._evt_repo.list_requirements(session, grp.id):
                    reqs_mode[req.id] = req.mode

            group_counts = {
                grp.id: len(self._evt_repo.list_group_members(session, grp.id))
                for grp in groups
            }
            sittings = self._rom_repo.list_sittings(session, plan.id)
            sitting_counts: dict[tuple[str, str], int] = {}
            for st in sittings:
                key = (st.room_session_id, st.requirement_id)
                sitting_counts[key] = sitting_counts.get(key, 0) + 1

            computed = 0
            for rp in self._ses_repo.list_room_papers_for_plan(session, plan.id):
                mode = reqs_mode.get(rp.requirement_id, "paper")
                if payload.exclude_cbt and mode == "cbt":
                    roster_cnt = 0
                    reserve_cnt = 0
                else:
                    roster_cnt = sitting_counts.get(
                        (rp.room_session_id, rp.requirement_id),
                        group_counts.get(rp.group_id, 0),
                    )
                    reserve_cnt = payload.reserve_per_room

                session.add(
                    PrintQuantity(
                        id=_new_id(),
                        exam_id=exam.id,
                        plan_id=plan.id,
                        room_session_id=rp.room_session_id,
                        requirement_id=rp.requirement_id,
                        roster_count=roster_cnt,
                        reserve_count=reserve_cnt,
                        override_qty=None,
                        exclude_cbt=1 if payload.exclude_cbt else 0,
                        revision=1,
                        created_at=now,
                        updated_at=now,
                    )
                )
                computed += 1
            session.flush()
            return {"computed_count": computed}

    def override_print_quantity(self, payload: PrintOverridePayload) -> dict[str, Any]:
        now = _now_iso()
        with session_scope(self._session_factory) as session:
            _, exam = self._require_exam(
                session, payload.institution_id, payload.exam_id
            )
            pq = self._repo.get_print_quantity(session, exam.id, payload.print_qty_id)
            if pq is None:
                raise NotFoundError("Baris jumlah cetak tidak ditemukan.")
            pq.override_qty = payload.override_qty
            pq.revision += 1
            pq.updated_at = now
            session.add(
                AuditEvent(
                    id=_new_id(),
                    institution_id=exam.institution_id,
                    exam_id=exam.id,
                    actor="operator",
                    action="exp.print.override",
                    entity_type="print_quantity",
                    entity_id=pq.id,
                    at=now,
                    change_summary_json=(
                        f'{{"override_qty":{payload.override_qty},"reason":"{payload.reason}"}}'
                    ),
                    correlation_id=_new_id(),
                )
            )
            session.flush()
            return {"override_qty": pq.override_qty}

    def record_handover(self, payload: HandoverRecordPayload) -> dict[str, Any]:
        now = _now_iso()
        with session_scope(self._session_factory) as session:
            _, exam = self._require_exam(
                session, payload.institution_id, payload.exam_id
            )
            discrepancy = payload.actual_qty - payload.expected_qty
            ho = Handover(
                id=_new_id(),
                exam_id=exam.id,
                room_session_id=payload.room_session_id,
                kind=payload.kind,
                material_type=payload.material_type.strip(),
                expected_qty=payload.expected_qty,
                actual_qty=payload.actual_qty,
                discrepancy=discrepancy,
                from_person_name=payload.from_person_name.strip(),
                to_person_name=payload.to_person_name.strip(),
                handed_at=payload.handed_at,
                note=payload.note,
                created_at=now,
            )
            session.add(ho)
            session.flush()
            return {
                "id": ho.id,
                "discrepancy": discrepancy,
                "mismatch": discrepancy != 0,
            }
