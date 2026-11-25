"""Transactional service layer for TSK-01..TSK-05."""

from __future__ import annotations

import uuid
from datetime import UTC, date, datetime, timedelta
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
from backend.modules.tsk.models import Task, TaskDependency
from backend.modules.tsk.repository import TskRepository
from backend.modules.tsk.schemas import (
    ApplyPresetPayload,
    TaskDeletePayload,
    TaskDependencyDeletePayload,
    TaskDependencyPayload,
    TaskEvidencePayload,
    TaskSavePayload,
    TskScopedPayload,
)

STANDARD_PRESET_ITEMS: list[tuple[str, str, int, str, str]] = [
    ("preparation", "Rapat koordinasi panitia", -14, "starts_on", "high"),
    ("preparation", "Finalisasi jadwal & denah ruang", -7, "starts_on", "critical"),
    ("preparation", "Cetak kartu peserta & daftar hadir", -3, "starts_on", "high"),
    ("implementation", "Pelaksanaan & monitoring harian", 0, "starts_on", "high"),
    ("closing", "Rekap kehadiran & berita acara", 1, "ends_on", "high"),
    ("closing", "Penyusunan laporan pertanggungjawaban", 5, "ends_on", "medium"),
]


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()


def _new_id() -> str:
    return uuid.uuid4().hex


def has_dependency_cycle(
    deps: list[tuple[str, str]], task_id: str, prerequisite_id: str
) -> bool:
    """Return True if adding (task_id -> prerequisite_id) creates a cycle."""
    if task_id == prerequisite_id:
        return True
    adj: dict[str, list[str]] = {}
    for t_id, p_id in deps:
        adj.setdefault(t_id, []).append(p_id)
    # Walk from prerequisite_id to see if task_id is reachable
    stack = [prerequisite_id]
    visited: set[str] = set()
    while stack:
        curr = stack.pop()
        if curr == task_id:
            return True
        if curr in visited:
            continue
        visited.add(curr)
        stack.extend(adj.get(curr, []))
    return False


class TskService:
    """Application service for Tasks & Timeline (TSK-01..TSK-05)."""

    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._session_factory = session_factory
        self._repo = TskRepository()
        self._evt_repo = EvtRepository()
        self._cfg_repo = CfgRepository()

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

    def _require_mutable(self, exam: Exam) -> None:
        if exam.state == "ARCHIVED":
            raise ConflictError("Kegiatan yang diarsipkan bersifat baca-saja.")

    def _record_audit(
        self,
        session: Session,
        exam: Exam,
        action: str,
        entity_id: str,
        summary_json: str,
        now: str,
    ) -> None:
        session.add(
            AuditEvent(
                id=_new_id(),
                institution_id=exam.institution_id,
                exam_id=exam.id,
                actor="operator",
                action=action,
                entity_type="task",
                entity_id=entity_id,
                at=now,
                change_summary_json=summary_json,
                correlation_id=_new_id(),
            )
        )

    def get_detail(self, payload: TskScopedPayload) -> dict[str, Any]:
        with session_scope(self._session_factory) as session:
            inst, exam = self._require_exam(
                session, payload.institution_id, payload.exam_id
            )
            tz = ZoneInfo(inst.timezone or "Asia/Jakarta")
            today_local = datetime.now(tz).date().isoformat()

            staff = self._evt_repo.list_people(session, exam.id, kind="staff")
            staff_map = {p.id: p for p in staff}
            tasks = self._repo.list_tasks(session, exam.id)
            deps = self._repo.list_dependencies(session, exam.id)

            deps_by_task: dict[str, list[dict[str, str]]] = {}
            for d in deps:
                deps_by_task.setdefault(d.task_id, []).append(
                    {"id": d.id, "prerequisite_id": d.prerequisite_id}
                )

            overdue_count = 0
            tasks_out = []
            for t in tasks:
                is_overdue = t.state != "done" and t.due_date < today_local
                if is_overdue:
                    overdue_count += 1
                pic = staff_map.get(t.pic_id) if t.pic_id else None
                tasks_out.append(
                    {
                        "id": t.id,
                        "phase": t.phase,
                        "title": t.title,
                        "description": t.description,
                        "pic_id": t.pic_id,
                        "pic_name": pic.display_name if pic else None,
                        "missing_pic": t.pic_id is None,
                        "priority": t.priority,
                        "due_date": t.due_date,
                        "is_overdue": is_overdue,
                        "state": t.state,
                        "blocked_reason": t.blocked_reason,
                        "parent_id": t.parent_id,
                        "evidence_asset_id": t.evidence_asset_id,
                        "evidence_note": t.evidence_note,
                        "completed_at": t.completed_at,
                        "completed_by": t.completed_by,
                        "dependencies": deps_by_task.get(t.id, []),
                    }
                )

            return {
                "is_archived": exam.state == "ARCHIVED",
                "today_local": today_local,
                "overdue_count": overdue_count,
                "staff": [
                    {"id": p.id, "code": p.code, "display_name": p.display_name}
                    for p in staff
                ],
                "tasks": tasks_out,
            }

    def apply_preset(self, payload: ApplyPresetPayload) -> dict[str, Any]:
        now = _now_iso()
        with session_scope(self._session_factory) as session:
            _, exam = self._require_exam(
                session, payload.institution_id, payload.exam_id
            )
            self._require_mutable(exam)

            start_dt = date.fromisoformat(exam.starts_on)
            end_dt = date.fromisoformat(exam.ends_on)
            created_ids: list[str] = []
            for phase, title, offset, anchor, priority in STANDARD_PRESET_ITEMS:
                base = start_dt if anchor == "starts_on" else end_dt
                due = (base + timedelta(days=offset)).isoformat()
                t = Task(
                    id=_new_id(),
                    exam_id=exam.id,
                    phase=phase,
                    title=title,
                    description="",
                    pic_id=None,
                    priority=priority,
                    due_date=due,
                    state="todo",
                    blocked_reason="",
                    parent_id=None,
                    evidence_asset_id=None,
                    evidence_note="",
                    completed_at=None,
                    completed_by=None,
                    revision=1,
                    created_at=now,
                    updated_at=now,
                )
                session.add(t)
                created_ids.append(t.id)
            session.flush()
            return {"created_count": len(created_ids)}

    def _validate_done_policy(
        self, session: Session, exam_id: str, task_id: str
    ) -> None:
        all_tasks = {t.id: t for t in self._repo.list_tasks(session, exam_id)}
        deps = self._repo.list_dependencies(session, exam_id)
        for d in deps:
            if d.task_id == task_id:
                prereq = all_tasks.get(d.prerequisite_id)
                if prereq and prereq.state != "done":
                    raise ConflictError(
                        f"Tugas prasyarat '{prereq.title}' belum selesai."
                    )
        for child in all_tasks.values():
            if child.parent_id == task_id and child.state != "done":
                raise ConflictError(f"Subtugas '{child.title}' belum selesai.")

    def save_task(self, payload: TaskSavePayload) -> dict[str, Any]:
        now = _now_iso()
        with session_scope(self._session_factory) as session:
            _, exam = self._require_exam(
                session, payload.institution_id, payload.exam_id
            )
            self._require_mutable(exam)

            if payload.id is None:
                if payload.state == "done":
                    # New task has no prerequisites or children yet
                    pass
                t = Task(
                    id=_new_id(),
                    exam_id=exam.id,
                    phase=payload.phase,
                    title=payload.title.strip(),
                    description=payload.description,
                    pic_id=payload.pic_id or None,
                    priority=payload.priority,
                    due_date=payload.due_date,
                    state=payload.state,
                    blocked_reason=payload.blocked_reason,
                    parent_id=payload.parent_id or None,
                    evidence_asset_id=None,
                    evidence_note="",
                    completed_at=now if payload.state == "done" else None,
                    completed_by="operator" if payload.state == "done" else None,
                    revision=1,
                    created_at=now,
                    updated_at=now,
                )
                session.add(t)
                session.flush()
                return {"id": t.id}

            existing = self._repo.get_task(session, exam.id, payload.id)
            if existing is None:
                raise NotFoundError("Tugas tidak ditemukan.")
            if payload.parent_id == existing.id:
                raise ConflictError("Tugas tidak dapat menjadi induk dirinya sendiri.")
            if payload.state == "done":
                self._validate_done_policy(session, exam.id, existing.id)

            prev_state = existing.state
            existing.phase = payload.phase
            existing.title = payload.title.strip()
            existing.description = payload.description
            existing.pic_id = payload.pic_id or None
            existing.priority = payload.priority
            existing.due_date = payload.due_date
            existing.state = payload.state
            existing.blocked_reason = payload.blocked_reason
            existing.parent_id = payload.parent_id or None
            if payload.state == "done" and prev_state != "done":
                existing.completed_at = now
                existing.completed_by = "operator"
            existing.revision += 1
            existing.updated_at = now
            if prev_state != payload.state:
                self._record_audit(
                    session,
                    exam,
                    "tsk.task.state_change",
                    existing.id,
                    f'{{"from":"{prev_state}","to":"{payload.state}"}}',
                    now,
                )
            session.flush()
            return {"id": existing.id}

    def delete_task(self, payload: TaskDeletePayload) -> dict[str, Any]:
        with session_scope(self._session_factory) as session:
            _, exam = self._require_exam(
                session, payload.institution_id, payload.exam_id
            )
            self._require_mutable(exam)
            t = self._repo.get_task(session, exam.id, payload.task_id)
            if t is None:
                raise NotFoundError("Tugas tidak ditemukan.")
            session.delete(t)
            session.flush()
            return {"deleted": True}

    def add_dependency(self, payload: TaskDependencyPayload) -> dict[str, Any]:
        now = _now_iso()
        with session_scope(self._session_factory) as session:
            _, exam = self._require_exam(
                session, payload.institution_id, payload.exam_id
            )
            self._require_mutable(exam)
            if (
                self._repo.get_task(session, exam.id, payload.task_id) is None
                or self._repo.get_task(session, exam.id, payload.prerequisite_id)
                is None
            ):
                raise NotFoundError("Tugas atau prasyarat tidak ditemukan.")

            existing_pairs = [
                (d.task_id, d.prerequisite_id)
                for d in self._repo.list_dependencies(session, exam.id)
            ]
            if has_dependency_cycle(
                existing_pairs, payload.task_id, payload.prerequisite_id
            ):
                raise ConflictError("Dependensi membentuk siklus (cycle).")

            dep = TaskDependency(
                id=_new_id(),
                exam_id=exam.id,
                task_id=payload.task_id,
                prerequisite_id=payload.prerequisite_id,
                created_at=now,
            )
            session.add(dep)
            try:
                session.flush()
            except IntegrityError as exc:
                raise ConflictError("Dependensi sudah terdaftar.") from exc
            return {"id": dep.id}

    def remove_dependency(self, payload: TaskDependencyDeletePayload) -> dict[str, Any]:
        with session_scope(self._session_factory) as session:
            _, exam = self._require_exam(
                session, payload.institution_id, payload.exam_id
            )
            self._require_mutable(exam)
            dep = self._repo.get_dependency(session, exam.id, payload.dependency_id)
            if dep is None:
                raise NotFoundError("Dependensi tidak ditemukan.")
            session.delete(dep)
            session.flush()
            return {"deleted": True}

    def attach_evidence(self, payload: TaskEvidencePayload) -> dict[str, Any]:
        now = _now_iso()
        with session_scope(self._session_factory) as session:
            _, exam = self._require_exam(
                session, payload.institution_id, payload.exam_id
            )
            self._require_mutable(exam)
            t = self._repo.get_task(session, exam.id, payload.task_id)
            if t is None:
                raise NotFoundError("Tugas tidak ditemukan.")

            if payload.mark_done:
                self._validate_done_policy(session, exam.id, t.id)

            prev_state = t.state
            t.evidence_asset_id = payload.evidence_asset_id
            t.evidence_note = payload.evidence_note
            if payload.mark_done:
                t.state = "done"
                t.completed_at = now
                t.completed_by = payload.completed_by
            t.revision += 1
            t.updated_at = now
            self._record_audit(
                session,
                exam,
                "tsk.evidence.attach",
                t.id,
                f'{{"from":"{prev_state}","to":"{t.state}"}}',
                now,
            )
            session.flush()
            return {"id": t.id, "state": t.state}
