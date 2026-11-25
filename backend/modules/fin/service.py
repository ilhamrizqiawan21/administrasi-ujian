"""Transactional service layer for FIN-01..FIN-08."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from decimal import ROUND_HALF_UP, Decimal
from typing import Any

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker

from backend.core.db import session_scope
from backend.core.errors import ConflictError, NotFoundError
from backend.modules.cfg.repository import CfgRepository
from backend.modules.evt.models import Exam
from backend.modules.evt.repository import EvtRepository
from backend.modules.fin.models import (
    BudgetCategory,
    BudgetLine,
    BudgetVersion,
    HonorLine,
    HonorRule,
    LedgerEntry,
)
from backend.modules.fin.repository import FinRepository
from backend.modules.fin.schemas import (
    BudgetCategoryArchivePayload,
    BudgetCategorySavePayload,
    BudgetLineSavePayload,
    BudgetVersionActionPayload,
    FinScopedPayload,
    HonorPayPayload,
    HonorRuleSavePayload,
    LedgerActionPayload,
    LedgerSavePayload,
)
from backend.modules.ops.repository import OpsRepository
from backend.modules.sch.repository import SchRepository

_ONES = [
    "",
    "satu",
    "dua",
    "tiga",
    "empat",
    "lima",
    "enam",
    "tujuh",
    "delapan",
    "sembilan",
    "sepuluh",
    "sebelas",
]


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()


def _new_id() -> str:
    return uuid.uuid4().hex


def compute_line_amount_idr(qty_decimal: str, unit_rate_idr: int) -> int:
    """Exact Decimal multiplication rounded HALF_UP to integer IDR (FIN-02)."""
    val = (Decimal(qty_decimal) * Decimal(unit_rate_idr)).quantize(
        Decimal("1"), rounding=ROUND_HALF_UP
    )
    return int(val)


def terbilang_idr(amount: int) -> str:
    """Convert non-negative integer IDR to Indonesian words (FIN-07)."""
    if amount == 0:
        return "nol rupiah"

    def _spell(n: int) -> str:
        if n < 12:
            return _ONES[n]
        if n < 20:
            return f"{_ONES[n - 10]} belas"
        if n < 100:
            rem = n % 10
            return f"{_ONES[n // 10]} puluh" + (f" {_spell(rem)}" if rem else "")
        if n < 200:
            rem = n - 100
            return "seratus" + (f" {_spell(rem)}" if rem else "")
        if n < 1000:
            rem = n % 100
            return f"{_ONES[n // 100]} ratus" + (f" {_spell(rem)}" if rem else "")
        if n < 2000:
            rem = n - 1000
            return "seribu" + (f" {_spell(rem)}" if rem else "")
        if n < 1_000_000:
            rem = n % 1000
            return f"{_spell(n // 1000)} ribu" + (f" {_spell(rem)}" if rem else "")
        if n < 1_000_000_000:
            rem = n % 1_000_000
            return f"{_spell(n // 1_000_000)} juta" + (f" {_spell(rem)}" if rem else "")
        rem = n % 1_000_000_000
        return f"{_spell(n // 1_000_000_000)} miliar" + (
            f" {_spell(rem)}" if rem else ""
        )

    return f"{_spell(amount).strip()} rupiah"


class FinService:
    """Application service for Budget, Finance & Honorarium (FIN-01..FIN-08)."""

    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._session_factory = session_factory
        self._repo = FinRepository()
        self._cfg_repo = CfgRepository()
        self._evt_repo = EvtRepository()
        self._ops_repo = OpsRepository()
        self._sch_repo = SchRepository()

    def _require_exam(
        self, session: Session, institution_id: str, exam_id: str
    ) -> Exam:
        if self._cfg_repo.get_institution(session, institution_id) is None:
            raise NotFoundError("Lembaga tidak ditemukan.")
        exam = self._evt_repo.get_exam(session, institution_id, exam_id)
        if exam is None:
            raise NotFoundError("Kegiatan ujian tidak ditemukan.")
        return exam

    def _would_create_cat_cycle(
        self, cats: list[BudgetCategory], cat_id: str, parent_id: str | None
    ) -> bool:
        if parent_id is None:
            return False
        if parent_id == cat_id:
            return True
        parent_map = {c.id: c.parent_id for c in cats}
        curr: str | None = parent_id
        visited = {cat_id}
        while curr is not None:
            if curr in visited:
                return True
            visited.add(curr)
            curr = parent_map.get(curr)
        return False

    def get_detail(self, payload: FinScopedPayload) -> dict[str, Any]:
        with session_scope(self._session_factory) as session:
            exam = self._require_exam(session, payload.institution_id, payload.exam_id)
            cats = self._repo.list_categories(session, exam.id)
            cat_map = {c.id: c for c in cats}
            versions = self._repo.list_budget_versions(session, exam.id)
            approved_ver = next((v for v in versions if v.state == "approved"), None)

            versions_out = []
            approved_by_cat: dict[str, int] = {}
            for v in versions:
                lines = self._repo.list_budget_lines(session, v.id)
                total = sum(ln.amount_idr for ln in lines)
                if approved_ver and v.id == approved_ver.id:
                    for ln in lines:
                        approved_by_cat[ln.category_id] = (
                            approved_by_cat.get(ln.category_id, 0) + ln.amount_idr
                        )
                versions_out.append(
                    {
                        "id": v.id,
                        "number": v.number,
                        "state": v.state,
                        "approved_at": v.approved_at,
                        "total_idr": total,
                        "lines": [
                            {
                                "id": ln.id,
                                "category_id": ln.category_id,
                                "category_label": (
                                    cat_map[ln.category_id].label
                                    if ln.category_id in cat_map
                                    else ""
                                ),
                                "description": ln.description,
                                "qty_decimal": ln.qty_decimal,
                                "unit": ln.unit,
                                "unit_rate_idr": ln.unit_rate_idr,
                                "amount_idr": ln.amount_idr,
                            }
                            for ln in lines
                        ],
                    }
                )

            entries = self._repo.list_ledger_entries(session, exam.id)
            entry_map = {e.id: e for e in entries}
            running = 0
            actual_expense_by_cat: dict[str, int] = {}
            cashbook_out = []
            for e in entries:
                signed = 0
                if e.state == "posted":
                    if e.kind == "income":
                        signed = e.amount_idr
                    elif e.kind == "expense":
                        signed = -e.amount_idr
                        actual_expense_by_cat[e.category_id] = (
                            actual_expense_by_cat.get(e.category_id, 0) + e.amount_idr
                        )
                    elif e.kind == "reversal" and e.reverses_id in entry_map:
                        orig = entry_map[e.reverses_id]
                        if orig.kind == "expense":
                            signed = e.amount_idr
                            actual_expense_by_cat[e.category_id] = (
                                actual_expense_by_cat.get(e.category_id, 0)
                                - e.amount_idr
                            )
                        else:
                            signed = -e.amount_idr
                    running += signed

                cashbook_out.append(
                    {
                        "id": e.id,
                        "category_id": e.category_id,
                        "category_label": (
                            cat_map[e.category_id].label
                            if e.category_id in cat_map
                            else ""
                        ),
                        "kind": e.kind,
                        "amount_idr": e.amount_idr,
                        "entry_date": e.entry_date,
                        "reference": e.reference,
                        "payee": e.payee,
                        "state": e.state,
                        "reverses_id": e.reverses_id,
                        "running_balance_idr": running if e.state == "posted" else None,
                    }
                )

            variance = []
            for c in cats:
                rab_amt = approved_by_cat.get(c.id, 0)
                act_amt = actual_expense_by_cat.get(c.id, 0)
                variance.append(
                    {
                        "category_id": c.id,
                        "category_label": c.label,
                        "approved_rab_idr": rab_amt,
                        "actual_expense_idr": act_amt,
                        "remaining_idr": rab_amt - act_amt,
                        "over_budget": act_amt > rab_amt if rab_amt > 0 else False,
                    }
                )

            people = {
                p.id: p
                for p in self._evt_repo.list_people(session, exam.id, kind="staff")
            }
            rules = self._repo.list_honor_rules(session, exam.id)
            h_lines = self._repo.list_honor_lines(session, exam.id)

            return {
                "categories": [
                    {
                        "id": c.id,
                        "label": c.label,
                        "parent_id": c.parent_id,
                        "source_fund": c.source_fund,
                        "default_unit": c.default_unit,
                        "archived": bool(c.archived),
                    }
                    for c in cats
                ],
                "budget_versions": versions_out,
                "cashbook": cashbook_out,
                "closing_balance_idr": running,
                "variance": variance,
                "honor_rules": [
                    {
                        "id": r.id,
                        "role_code": r.role_code,
                        "unit_type": r.unit_type,
                        "rate_idr": r.rate_idr,
                        "effective_date": r.effective_date,
                        "active": bool(r.active),
                    }
                    for r in rules
                ],
                "honor_lines": [
                    {
                        "id": h.id,
                        "exam_person_id": h.exam_person_id,
                        "person_name": (
                            people[h.exam_person_id].display_name
                            if h.exam_person_id in people
                            else ""
                        ),
                        "source_type": h.source_type,
                        "role_code": h.role_code,
                        "rate_idr": h.rate_idr,
                        "qty": h.qty,
                        "amount_idr": h.amount_idr,
                        "amount_words": terbilang_idr(h.amount_idr),
                        "state": h.state,
                    }
                    for h in h_lines
                ],
            }

    def save_category(self, payload: BudgetCategorySavePayload) -> dict[str, Any]:
        now = _now_iso()
        with session_scope(self._session_factory) as session:
            exam = self._require_exam(session, payload.institution_id, payload.exam_id)
            cats = self._repo.list_categories(session, exam.id)
            if payload.id is None:
                cat = BudgetCategory(
                    id=_new_id(),
                    exam_id=exam.id,
                    label=payload.label.strip(),
                    parent_id=payload.parent_id,
                    source_fund=payload.source_fund,
                    default_unit=payload.default_unit,
                    archived=0,
                    revision=1,
                    created_at=now,
                )
                session.add(cat)
                try:
                    session.flush()
                except IntegrityError as exc:
                    raise ConflictError("Kategori anggaran sudah ada.") from exc
                return {"id": cat.id}

            existing = self._repo.get_category(session, exam.id, payload.id)
            if existing is None:
                raise NotFoundError("Kategori anggaran tidak ditemukan.")
            if self._would_create_cat_cycle(cats, existing.id, payload.parent_id):
                raise ConflictError("Hierarki kategori membentuk siklus.")
            existing.label = payload.label.strip()
            existing.parent_id = payload.parent_id
            existing.source_fund = payload.source_fund
            existing.default_unit = payload.default_unit
            existing.revision += 1
            session.flush()
            return {"id": existing.id}

    def archive_category(self, payload: BudgetCategoryArchivePayload) -> dict[str, Any]:
        with session_scope(self._session_factory) as session:
            exam = self._require_exam(session, payload.institution_id, payload.exam_id)
            cat = self._repo.get_category(session, exam.id, payload.category_id)
            if cat is None:
                raise NotFoundError("Kategori tidak ditemukan.")
            cat.archived = 1
            cat.revision += 1
            session.flush()
            return {"archived": True}

    def create_budget_version(
        self, payload: BudgetVersionActionPayload
    ) -> dict[str, Any]:
        now = _now_iso()
        with session_scope(self._session_factory) as session:
            exam = self._require_exam(session, payload.institution_id, payload.exam_id)
            existing = self._repo.list_budget_versions(session, exam.id)
            next_num = max((v.number for v in existing), default=0) + 1
            bv = BudgetVersion(
                id=_new_id(),
                exam_id=exam.id,
                number=next_num,
                state="draft",
                approved_at=None,
                created_at=now,
            )
            session.add(bv)
            session.flush()
            return {"id": bv.id, "number": bv.number}

    def save_budget_line(self, payload: BudgetLineSavePayload) -> dict[str, Any]:
        now = _now_iso()
        with session_scope(self._session_factory) as session:
            exam = self._require_exam(session, payload.institution_id, payload.exam_id)
            bv = self._repo.get_budget_version(
                session, exam.id, payload.budget_version_id
            )
            if bv is None:
                raise NotFoundError("Versi RAB tidak ditemukan.")
            if bv.state != "draft":
                raise ConflictError("RAB yang sudah disetujui tidak dapat diubah.")
            amt = compute_line_amount_idr(payload.qty_decimal, payload.unit_rate_idr)
            ln = BudgetLine(
                id=_new_id(),
                budget_version_id=bv.id,
                category_id=payload.category_id,
                description=payload.description.strip(),
                qty_decimal=payload.qty_decimal,
                unit=payload.unit.strip(),
                unit_rate_idr=payload.unit_rate_idr,
                amount_idr=amt,
                created_at=now,
            )
            session.add(ln)
            session.flush()
            return {"id": ln.id, "amount_idr": amt}

    def approve_budget_version(
        self, payload: BudgetVersionActionPayload
    ) -> dict[str, Any]:
        now = _now_iso()
        with session_scope(self._session_factory) as session:
            exam = self._require_exam(session, payload.institution_id, payload.exam_id)
            if not payload.budget_version_id:
                raise NotFoundError("ID versi RAB wajib diisi.")
            bv = self._repo.get_budget_version(
                session, exam.id, payload.budget_version_id
            )
            if bv is None:
                raise NotFoundError("Versi RAB tidak ditemukan.")
            for old in self._repo.list_budget_versions(session, exam.id):
                if old.state == "approved" and old.id != bv.id:
                    old.state = "superseded"
            bv.state = "approved"
            bv.approved_at = now
            session.flush()
            return {"state": bv.state}

    def save_ledger_entry(self, payload: LedgerSavePayload) -> dict[str, Any]:
        now = _now_iso()
        with session_scope(self._session_factory) as session:
            exam = self._require_exam(session, payload.institution_id, payload.exam_id)
            le = LedgerEntry(
                id=_new_id(),
                exam_id=exam.id,
                category_id=payload.category_id,
                kind=payload.kind,
                amount_idr=payload.amount_idr,
                entry_date=payload.entry_date,
                reference=payload.reference,
                payee=payload.payee,
                attachment_asset_id=None,
                state="draft",
                reverses_id=None,
                source_key=None,
                created_at=now,
                posted_at=None,
            )
            session.add(le)
            session.flush()
            return {"id": le.id}

    def post_ledger_entry(self, payload: LedgerActionPayload) -> dict[str, Any]:
        now = _now_iso()
        with session_scope(self._session_factory) as session:
            exam = self._require_exam(session, payload.institution_id, payload.exam_id)
            le = self._repo.get_ledger_entry(session, exam.id, payload.entry_id)
            if le is None:
                raise NotFoundError("Entri kas tidak ditemukan.")
            if le.state == "posted":
                raise ConflictError("Entri kas sudah diposting.")
            le.state = "posted"
            le.posted_at = now
            session.flush()
            return {"state": le.state}

    def reverse_ledger_entry(self, payload: LedgerActionPayload) -> dict[str, Any]:
        now = _now_iso()
        with session_scope(self._session_factory) as session:
            exam = self._require_exam(session, payload.institution_id, payload.exam_id)
            orig = self._repo.get_ledger_entry(session, exam.id, payload.entry_id)
            if orig is None or orig.state != "posted":
                raise ConflictError(
                    "Hanya entri kas berstatus posted yang dapat dibalik."
                )
            if orig.kind == "reversal":
                raise ConflictError("Entri pembalik tidak dapat dibalik ulang.")
            rev = LedgerEntry(
                id=_new_id(),
                exam_id=exam.id,
                category_id=orig.category_id,
                kind="reversal",
                amount_idr=orig.amount_idr,
                entry_date=orig.entry_date,
                reference=f"REV-{orig.reference or orig.id[:6]}",
                payee=orig.payee,
                attachment_asset_id=None,
                state="posted",
                reverses_id=orig.id,
                source_key=None,
                created_at=now,
                posted_at=now,
            )
            session.add(rev)
            try:
                session.flush()
            except IntegrityError as exc:
                raise ConflictError("Entri ini sudah pernah dibalik.") from exc
            return {"reversal_id": rev.id}

    def save_honor_rule(self, payload: HonorRuleSavePayload) -> dict[str, Any]:
        now = _now_iso()
        with session_scope(self._session_factory) as session:
            exam = self._require_exam(session, payload.institution_id, payload.exam_id)
            for old in self._repo.list_honor_rules(session, exam.id):
                if old.role_code == payload.role_code and old.active:
                    old.active = 0
            hr = HonorRule(
                id=_new_id(),
                exam_id=exam.id,
                role_code=payload.role_code.strip(),
                unit_type=payload.unit_type,
                rate_idr=payload.rate_idr,
                effective_date=payload.effective_date,
                active=1,
                created_at=now,
            )
            session.add(hr)
            session.flush()
            return {"id": hr.id}

    def generate_honor_lines(self, payload: FinScopedPayload) -> dict[str, Any]:
        now = _now_iso()
        with session_scope(self._session_factory) as session:
            exam = self._require_exam(session, payload.institution_id, payload.exam_id)
            active_rules = {
                r.role_code: r
                for r in self._repo.list_honor_rules(session, exam.id)
                if r.active
            }
            existing_keys = {
                (h.source_type, h.source_id, h.role_code)
                for h in self._repo.list_honor_lines(session, exam.id)
            }

            slots_by_id: dict[str, str] = {}
            for p in self._evt_repo.list_exams(session, exam.institution_id):
                if p.id == exam.id:
                    break
            from backend.modules.ses.repository import SesRepository

            for pl in SesRepository().list_plans(session, exam.id):
                for sl in self._sch_repo.list_slots(session, pl.id):
                    slots_by_id[sl.id] = sl.role_code

            created = 0
            # Staff attendance actual duty (FIN-06)
            for sa in self._ops_repo.list_staff_attendance(session, exam.id):
                if (
                    sa.state not in ("present", "substituted")
                    or not sa.actual_person_id
                ):
                    continue
                role = slots_by_id.get(sa.slot_id, "primary")
                rule = active_rules.get(role)
                if rule is None:
                    continue
                key = ("invigilation", sa.id, role)
                if key in existing_keys:
                    continue
                existing_keys.add(key)
                session.add(
                    HonorLine(
                        id=_new_id(),
                        exam_id=exam.id,
                        exam_person_id=sa.actual_person_id,
                        source_type="invigilation",
                        source_id=sa.id,
                        role_code=role,
                        rate_idr=rule.rate_idr,
                        qty=1,
                        amount_idr=rule.rate_idr,
                        state="draft",
                        ledger_entry_id=None,
                        created_at=now,
                    )
                )
                created += 1

            # Committee attendance
            for ca in self._ops_repo.list_committee_attendance(session, exam.id):
                if ca.state != "present":
                    continue
                rule = active_rules.get("committee")
                if rule is None:
                    continue
                key = ("committee", ca.id, "committee")
                if key in existing_keys:
                    continue
                existing_keys.add(key)
                session.add(
                    HonorLine(
                        id=_new_id(),
                        exam_id=exam.id,
                        exam_person_id=ca.exam_person_id,
                        source_type="committee",
                        source_id=ca.id,
                        role_code="committee",
                        rate_idr=rule.rate_idr,
                        qty=1,
                        amount_idr=rule.rate_idr,
                        state="draft",
                        ledger_entry_id=None,
                        created_at=now,
                    )
                )
                created += 1

            session.flush()
            return {"created_count": created}

    def pay_honor_line(self, payload: HonorPayPayload) -> dict[str, Any]:
        now = _now_iso()
        with session_scope(self._session_factory) as session:
            exam = self._require_exam(session, payload.institution_id, payload.exam_id)
            hl = self._repo.get_honor_line(session, exam.id, payload.honor_line_id)
            if hl is None:
                raise NotFoundError("Baris honorarium tidak ditemukan.")
            if hl.state == "paid":
                raise ConflictError("Honorarium ini sudah dibayarkan.")

            le = LedgerEntry(
                id=_new_id(),
                exam_id=exam.id,
                category_id=payload.category_id,
                kind="expense",
                amount_idr=max(1, hl.amount_idr),
                entry_date=payload.entry_date,
                reference=f"HON-{hl.id[:8]}",
                payee=hl.exam_person_id,
                attachment_asset_id=None,
                state="posted",
                reverses_id=None,
                source_key=f"honor:{hl.id}",
                created_at=now,
                posted_at=now,
            )
            session.add(le)
            try:
                session.flush()
            except IntegrityError as exc:
                raise ConflictError("Pembayaran honorarium ganda dicegah.") from exc

            hl.state = "paid"
            hl.ledger_entry_id = le.id
            session.flush()
            return {
                "ledger_entry_id": le.id,
                "amount_words": terbilang_idr(hl.amount_idr),
            }
