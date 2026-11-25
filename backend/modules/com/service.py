"""Transactional service layer for COM-01..COM-06."""

from __future__ import annotations

import json
import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker

from backend.core.db import session_scope
from backend.core.errors import ConflictError, NotFoundError
from backend.modules.cfg.repository import CfgRepository
from backend.modules.com.models import (
    CommitteeMember,
    CommitteeRole,
    ExamSignatory,
    Meeting,
    MeetingAttendance,
    ProgramKerja,
)
from backend.modules.com.repository import ComRepository
from backend.modules.com.schemas import (
    CommitteeMemberAssignPayload,
    CommitteeMemberRemovePayload,
    CommitteeRoleDeletePayload,
    CommitteeRoleSavePayload,
    ComScopedPayload,
    MeetingAttendanceSavePayload,
    MeetingDeletePayload,
    MeetingSavePayload,
    ProgramKerjaSavePayload,
    SignatoryDeletePayload,
    SignatorySavePayload,
)
from backend.modules.evt.models import Exam
from backend.modules.evt.repository import EvtRepository


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()


def _new_id() -> str:
    return uuid.uuid4().hex


def build_org_tree(
    roles: list[CommitteeRole],
    members_by_role: dict[str, list[dict[str, Any]]],
) -> list[dict[str, Any]]:
    """Build acyclic nested organization chart tree (COM-03)."""
    nodes: dict[str, dict[str, Any]] = {}
    for r in roles:
        nodes[r.id] = {
            "id": r.id,
            "name": r.name,
            "parent_id": r.parent_id,
            "sort_order": r.sort_order,
            "jobdesc": r.jobdesc,
            "members": members_by_role.get(r.id, []),
            "children": [],
        }

    roots: list[dict[str, Any]] = []
    for r in roles:
        node = nodes[r.id]
        if r.parent_id and r.parent_id in nodes and r.parent_id != r.id:
            nodes[r.parent_id]["children"].append(node)
        else:
            roots.append(node)
    return roots


def validate_signatories_list(
    signatories: list[ExamSignatory],
) -> dict[str, Any]:
    """Validate required signatories (COM-06): block final docs if missing."""
    missing: list[str] = []
    for s in signatories:
        if s.required and (not s.signer_name.strip() or not s.signer_title.strip()):
            missing.append(s.role_label)
    return {"valid": len(missing) == 0, "missing_required": missing}


class ComService:
    """Application service for Committee & Meetings (COM-01..COM-06)."""

    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._session_factory = session_factory
        self._repo = ComRepository()
        self._evt_repo = EvtRepository()
        self._cfg_repo = CfgRepository()

    def _require_exam(
        self, session: Session, institution_id: str, exam_id: str
    ) -> Exam:
        if self._cfg_repo.get_institution(session, institution_id) is None:
            raise NotFoundError("Lembaga tidak ditemukan.")
        exam = self._evt_repo.get_exam(session, institution_id, exam_id)
        if exam is None:
            raise NotFoundError("Kegiatan ujian tidak ditemukan.")
        return exam

    def _would_create_cycle(
        self,
        roles: list[CommitteeRole],
        role_id: str,
        new_parent_id: str | None,
    ) -> bool:
        if new_parent_id is None:
            return False
        if new_parent_id == role_id:
            return True
        parent_map = {r.id: r.parent_id for r in roles}
        curr: str | None = new_parent_id
        visited: set[str] = {role_id}
        while curr is not None:
            if curr in visited:
                return True
            visited.add(curr)
            curr = parent_map.get(curr)
        return False

    def get_detail(self, payload: ComScopedPayload) -> dict[str, Any]:
        with session_scope(self._session_factory) as session:
            exam = self._require_exam(session, payload.institution_id, payload.exam_id)
            people = self._evt_repo.list_people(session, exam.id, kind="staff")
            people_map = {p.id: p for p in people}

            roles = self._repo.list_roles(session, exam.id)
            members = self._repo.list_members(session, exam.id)
            members_by_role: dict[str, list[dict[str, Any]]] = {}
            members_out: list[dict[str, Any]] = []
            for m in members:
                person = people_map.get(m.exam_person_id)
                item = {
                    "id": m.id,
                    "role_id": m.role_id,
                    "exam_person_id": m.exam_person_id,
                    "person_name": person.display_name if person else "",
                    "person_code": person.code if person else "",
                    "appointed_on": m.appointed_on,
                    "note": m.note,
                }
                members_by_role.setdefault(m.role_id, []).append(item)
                members_out.append(item)

            org_tree = build_org_tree(roles, members_by_role)

            pk = self._repo.get_program_kerja(session, exam.id)
            program_out = {
                "basis_text": pk.basis_text if pk else "",
                "objectives": json.loads(pk.objectives_json) if pk else [],
                "milestones": json.loads(pk.milestones_json) if pk else [],
                "sections": json.loads(pk.sections_json) if pk else [],
                "revision": pk.revision if pk else 0,
            }

            meetings = self._repo.list_meetings(session, exam.id)
            meetings_out = []
            for mt in meetings:
                att_rows = self._repo.list_meeting_attendance(session, mt.id)
                att_out = [
                    {
                        "id": a.id,
                        "exam_person_id": a.exam_person_id,
                        "person_name": (
                            people_map[a.exam_person_id].display_name
                            if a.exam_person_id in people_map
                            else ""
                        ),
                        "state": a.state,
                        "note": a.note,
                    }
                    for a in att_rows
                ]
                meetings_out.append(
                    {
                        "id": mt.id,
                        "title": mt.title,
                        "meeting_date": mt.meeting_date,
                        "start_time": mt.start_time,
                        "end_time": mt.end_time,
                        "location": mt.location,
                        "agenda": mt.agenda,
                        "minutes": mt.minutes,
                        "decisions": json.loads(mt.decisions_json),
                        "attendance": att_out,
                    }
                )

            signatories = self._repo.list_signatories(session, exam.id)
            sig_validation = validate_signatories_list(signatories)
            sig_out = [
                {
                    "id": s.id,
                    "role_key": s.role_key,
                    "role_label": s.role_label,
                    "exam_person_id": s.exam_person_id,
                    "signer_name": s.signer_name,
                    "signer_title": s.signer_title,
                    "signer_nip": s.signer_nip,
                    "signed_date": s.signed_date,
                    "signature_asset_id": s.signature_asset_id,
                    "required": bool(s.required),
                    "sort_order": s.sort_order,
                }
                for s in signatories
            ]

            return {
                "staff": [
                    {"id": p.id, "code": p.code, "display_name": p.display_name}
                    for p in people
                ],
                "roles": [
                    {
                        "id": r.id,
                        "name": r.name,
                        "parent_id": r.parent_id,
                        "sort_order": r.sort_order,
                        "jobdesc": r.jobdesc,
                    }
                    for r in roles
                ],
                "members": members_out,
                "org_tree": org_tree,
                "program_kerja": program_out,
                "meetings": meetings_out,
                "signatories": sig_out,
                "signatory_validation": sig_validation,
            }

    def save_role(self, payload: CommitteeRoleSavePayload) -> dict[str, Any]:
        now = _now_iso()
        with session_scope(self._session_factory) as session:
            exam = self._require_exam(session, payload.institution_id, payload.exam_id)
            roles = self._repo.list_roles(session, exam.id)
            if payload.parent_id is not None and not any(
                r.id == payload.parent_id for r in roles
            ):
                raise NotFoundError("Peran induk tidak ditemukan.")

            if payload.id is None:
                role = CommitteeRole(
                    id=_new_id(),
                    exam_id=exam.id,
                    name=payload.name.strip(),
                    parent_id=payload.parent_id,
                    sort_order=payload.sort_order,
                    jobdesc=payload.jobdesc,
                    revision=1,
                    created_at=now,
                    updated_at=now,
                )
                session.add(role)
                session.flush()
                return {"id": role.id}

            existing = self._repo.get_role(session, exam.id, payload.id)
            if existing is None:
                raise NotFoundError("Peran panitia tidak ditemukan.")
            if self._would_create_cycle(roles, existing.id, payload.parent_id):
                raise ConflictError("Relasi induk peran membentuk siklus (cycle).")

            existing.name = payload.name.strip()
            existing.parent_id = payload.parent_id
            existing.sort_order = payload.sort_order
            existing.jobdesc = payload.jobdesc
            existing.revision += 1
            existing.updated_at = now
            session.flush()
            return {"id": existing.id}

    def delete_role(self, payload: CommitteeRoleDeletePayload) -> dict[str, Any]:
        with session_scope(self._session_factory) as session:
            exam = self._require_exam(session, payload.institution_id, payload.exam_id)
            role = self._repo.get_role(session, exam.id, payload.role_id)
            if role is None:
                raise NotFoundError("Peran panitia tidak ditemukan.")
            session.delete(role)
            session.flush()
            return {"deleted": True}

    def assign_member(self, payload: CommitteeMemberAssignPayload) -> dict[str, Any]:
        now = _now_iso()
        with session_scope(self._session_factory) as session:
            exam = self._require_exam(session, payload.institution_id, payload.exam_id)
            if self._repo.get_role(session, exam.id, payload.role_id) is None:
                raise NotFoundError("Peran panitia tidak ditemukan.")
            member = CommitteeMember(
                id=_new_id(),
                exam_id=exam.id,
                role_id=payload.role_id,
                exam_person_id=payload.exam_person_id,
                appointed_on=payload.appointed_on,
                note=payload.note,
                revision=1,
                created_at=now,
                updated_at=now,
            )
            session.add(member)
            try:
                session.flush()
            except IntegrityError as exc:
                raise ConflictError(
                    "Personel sudah terdaftar pada peran panitia ini."
                ) from exc
            return {"id": member.id}

    def remove_member(self, payload: CommitteeMemberRemovePayload) -> dict[str, Any]:
        with session_scope(self._session_factory) as session:
            exam = self._require_exam(session, payload.institution_id, payload.exam_id)
            member = self._repo.get_member(session, exam.id, payload.member_id)
            if member is None:
                raise NotFoundError("Anggota panitia tidak ditemukan.")
            session.delete(member)
            session.flush()
            return {"deleted": True}

    def save_program_kerja(self, payload: ProgramKerjaSavePayload) -> dict[str, Any]:
        now = _now_iso()
        with session_scope(self._session_factory) as session:
            exam = self._require_exam(session, payload.institution_id, payload.exam_id)
            pk = self._repo.get_program_kerja(session, exam.id)
            obj_json = json.dumps(payload.objectives)
            ms_json = json.dumps([m.model_dump() for m in payload.milestones])
            sec_json = json.dumps([s.model_dump() for s in payload.sections])
            if pk is None:
                pk = ProgramKerja(
                    id=_new_id(),
                    exam_id=exam.id,
                    basis_text=payload.basis_text,
                    objectives_json=obj_json,
                    milestones_json=ms_json,
                    sections_json=sec_json,
                    revision=1,
                    created_at=now,
                    updated_at=now,
                )
                session.add(pk)
            else:
                pk.basis_text = payload.basis_text
                pk.objectives_json = obj_json
                pk.milestones_json = ms_json
                pk.sections_json = sec_json
                pk.revision += 1
                pk.updated_at = now
            session.flush()
            return {"id": pk.id, "revision": pk.revision}

    def save_meeting(self, payload: MeetingSavePayload) -> dict[str, Any]:
        now = _now_iso()
        with session_scope(self._session_factory) as session:
            exam = self._require_exam(session, payload.institution_id, payload.exam_id)
            dec_json = json.dumps(payload.decisions)
            if payload.id is None:
                mt = Meeting(
                    id=_new_id(),
                    exam_id=exam.id,
                    title=payload.title.strip(),
                    meeting_date=payload.meeting_date,
                    start_time=payload.start_time,
                    end_time=payload.end_time,
                    location=payload.location,
                    agenda=payload.agenda,
                    minutes=payload.minutes,
                    decisions_json=dec_json,
                    revision=1,
                    created_at=now,
                    updated_at=now,
                )
                session.add(mt)
                session.flush()
                return {"id": mt.id}

            existing = self._repo.get_meeting(session, exam.id, payload.id)
            if existing is None:
                raise NotFoundError("Catatan rapat tidak ditemukan.")
            existing.title = payload.title.strip()
            existing.meeting_date = payload.meeting_date
            existing.start_time = payload.start_time
            existing.end_time = payload.end_time
            existing.location = payload.location
            existing.agenda = payload.agenda
            existing.minutes = payload.minutes
            existing.decisions_json = dec_json
            existing.revision += 1
            existing.updated_at = now
            session.flush()
            return {"id": existing.id}

    def delete_meeting(self, payload: MeetingDeletePayload) -> dict[str, Any]:
        with session_scope(self._session_factory) as session:
            exam = self._require_exam(session, payload.institution_id, payload.exam_id)
            mt = self._repo.get_meeting(session, exam.id, payload.meeting_id)
            if mt is None:
                raise NotFoundError("Catatan rapat tidak ditemukan.")
            session.delete(mt)
            session.flush()
            return {"deleted": True}

    def save_meeting_attendance(
        self, payload: MeetingAttendanceSavePayload
    ) -> dict[str, Any]:
        now = _now_iso()
        with session_scope(self._session_factory) as session:
            exam = self._require_exam(session, payload.institution_id, payload.exam_id)
            mt = self._repo.get_meeting(session, exam.id, payload.meeting_id)
            if mt is None:
                raise NotFoundError("Rapat tidak ditemukan.")
            existing = self._repo.get_meeting_attendance_person(
                session, mt.id, payload.exam_person_id
            )
            if existing is None:
                att = MeetingAttendance(
                    id=_new_id(),
                    meeting_id=mt.id,
                    exam_person_id=payload.exam_person_id,
                    state=payload.state,
                    note=payload.note,
                    revision=1,
                    created_at=now,
                    updated_at=now,
                )
                session.add(att)
                session.flush()
                return {"id": att.id}
            existing.state = payload.state
            existing.note = payload.note
            existing.revision += 1
            existing.updated_at = now
            session.flush()
            return {"id": existing.id}

    def save_signatory(self, payload: SignatorySavePayload) -> dict[str, Any]:
        now = _now_iso()
        with session_scope(self._session_factory) as session:
            exam = self._require_exam(session, payload.institution_id, payload.exam_id)
            existing = self._repo.get_signatory_by_key(
                session, exam.id, payload.role_key
            )
            if existing is None:
                sig = ExamSignatory(
                    id=_new_id(),
                    exam_id=exam.id,
                    role_key=payload.role_key.strip(),
                    role_label=payload.role_label.strip(),
                    exam_person_id=payload.exam_person_id,
                    signer_name=payload.signer_name.strip(),
                    signer_title=payload.signer_title.strip(),
                    signer_nip=payload.signer_nip.strip(),
                    signed_date=payload.signed_date,
                    signature_asset_id=payload.signature_asset_id,
                    required=1 if payload.required else 0,
                    sort_order=payload.sort_order,
                    revision=1,
                    created_at=now,
                    updated_at=now,
                )
                session.add(sig)
                session.flush()
                return {"id": sig.id}

            existing.role_label = payload.role_label.strip()
            existing.exam_person_id = payload.exam_person_id
            existing.signer_name = payload.signer_name.strip()
            existing.signer_title = payload.signer_title.strip()
            existing.signer_nip = payload.signer_nip.strip()
            existing.signed_date = payload.signed_date
            existing.signature_asset_id = payload.signature_asset_id
            existing.required = 1 if payload.required else 0
            existing.sort_order = payload.sort_order
            existing.revision += 1
            existing.updated_at = now
            session.flush()
            return {"id": existing.id}

    def delete_signatory(self, payload: SignatoryDeletePayload) -> dict[str, Any]:
        with session_scope(self._session_factory) as session:
            exam = self._require_exam(session, payload.institution_id, payload.exam_id)
            sig = self._repo.get_signatory(session, exam.id, payload.signatory_id)
            if sig is None:
                raise NotFoundError("Penanda tangan tidak ditemukan.")
            session.delete(sig)
            session.flush()
            return {"deleted": True}
