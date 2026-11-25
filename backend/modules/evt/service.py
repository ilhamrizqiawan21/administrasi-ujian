"""Transactional service layer for EVT-01..EVT-07."""

from __future__ import annotations

import json
import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker

from backend.core.db import session_scope
from backend.core.errors import AppError, ConflictError, NotFoundError, ValidationError
from backend.core.logging import get_correlation_id
from backend.modules.cfg.repository import CfgRepository
from backend.modules.evt.models import (
    AuditEvent,
    Exam,
    ExamGroup,
    ExamParticipant,
    ExamPerson,
    ExamRequirement,
    ExamRoom,
    ExamSubject,
    GroupMember,
)
from backend.modules.evt.repository import EvtRepository
from backend.modules.evt.schemas import (
    ExamClonePayload,
    ExamCreatePayload,
    ExamGroupSavePayload,
    ExamRequirementDeletePayload,
    ExamRequirementSavePayload,
    ExamScopedPayload,
    ExamTransitionPayload,
    NumberingGeneratePayload,
    NumberingOverridePayload,
)
from backend.modules.mst.repository import MstRepository

_STATE_ORDER = {
    "DRAFT": 0,
    "PREPARATION": 1,
    "READY": 2,
    "RUNNING": 3,
    "COMPLETED": 4,
    "ARCHIVED": 5,
}


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()


def _new_id() -> str:
    return uuid.uuid4().hex


def _check_revision(actual: int, expected: int | None) -> None:
    if expected is not None and actual != expected:
        raise AppError(
            "STALE_REVISION",
            "Kegiatan telah diubah. Muat ulang sebelum menyimpan.",
        )


def _assert_not_archived(exam: Exam) -> None:
    if exam.state == "ARCHIVED":
        raise AppError(
            "PERMISSION_DENIED",
            "Kegiatan sudah diarsipkan (read-only). "
            "Duplikasi atau reopen terlebih dahulu.",
        )


def _serialize_exam(exam: Exam) -> dict[str, Any]:
    return {
        "id": exam.id,
        "institution_id": exam.institution_id,
        "year_id": exam.year_id,
        "exam_type_id": exam.exam_type_id,
        "title": exam.title,
        "semester_label": exam.semester_label,
        "mode": exam.mode,
        "starts_on": exam.starts_on,
        "ends_on": exam.ends_on,
        "state": exam.state,
        "config": json.loads(exam.config_json),
        "active_plan_id": exam.active_plan_id,
        "revision": exam.revision,
    }


class EvtService:
    """Application service for Exam Workspace (EVT-01..EVT-07)."""

    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._session_factory = session_factory
        self._repo = EvtRepository()
        self._cfg_repo = CfgRepository()
        self._mst_repo = MstRepository()

    def list_exams(self, institution_id: str) -> dict[str, Any]:
        with session_scope(self._session_factory) as session:
            if self._cfg_repo.get_institution(session, institution_id) is None:
                raise NotFoundError("Lembaga tidak ditemukan.")
            exams = self._repo.list_exams(session, institution_id)
            return {"items": [_serialize_exam(e) for e in exams]}

    def create_exam(self, payload: ExamCreatePayload) -> dict[str, Any]:
        now = _now_iso()
        with session_scope(self._session_factory) as session:
            if self._cfg_repo.get_institution(session, payload.institution_id) is None:
                raise NotFoundError("Lembaga tidak ditemukan.")
            if (
                self._cfg_repo.get_year(
                    session, payload.institution_id, payload.year_id
                )
                is None
            ):
                raise NotFoundError("Tahun ajaran tidak ditemukan.")
            if (
                self._cfg_repo.get_exam_type(
                    session, payload.institution_id, payload.exam_type_id
                )
                is None
            ):
                raise NotFoundError("Jenis ujian tidak ditemukan.")

            all_classes = {
                c.id: c
                for c in self._mst_repo.list_classes(
                    session, payload.institution_id, year_id=payload.year_id
                )
            }
            all_levels = {
                lv.id: lv.label
                for lv in self._cfg_repo.list_levels(session, payload.institution_id)
            }
            all_students = {
                s.id: s
                for s in self._mst_repo.list_all_students(
                    session, payload.institution_id
                )
            }
            enrollments_by_student = {
                e.student_id: e
                for e in self._mst_repo.list_enrollments(
                    session, payload.institution_id, year_id=payload.year_id
                )
                if e.status == "active"
            }

            selected_class_set = set(payload.selected_class_ids)
            for cid in selected_class_set:
                if cid not in all_classes:
                    raise ValidationError(
                        f"Kelas '{cid}' tidak valid untuk tahun ajaran ini."
                    )

            selected_student_set = set(payload.selected_student_ids)
            for sid in selected_student_set:
                if sid not in all_students or not all_students[sid].active:
                    raise ValidationError(
                        f"Siswa '{sid}' tidak ditemukan atau nonaktif."
                    )

            if selected_class_set:
                for stu_id, enr in enrollments_by_student.items():
                    if (
                        enr.class_id in selected_class_set
                        and all_students[stu_id].active
                    ):
                        selected_student_set.add(stu_id)

            if not selected_student_set and (
                payload.selected_class_ids or payload.selected_student_ids
            ):
                raise ValidationError("Tidak ada siswa aktif pada pilihan kelas/siswa.")

            if not selected_student_set:
                selected_student_set = {s.id for s in all_students.values() if s.active}

            all_rooms = {
                r.id: r
                for r in self._mst_repo.list_rooms(session, payload.institution_id)
            }
            selected_rooms = (
                [
                    all_rooms[rid]
                    for rid in payload.selected_room_ids
                    if rid in all_rooms
                ]
                if payload.selected_room_ids
                else list(all_rooms.values())
            )
            if payload.selected_room_ids and len(set(payload.selected_room_ids)) != len(
                selected_rooms
            ):
                raise ValidationError("Terdapat ruang yang tidak valid pada pilihan.")

            all_subjects = {
                sb.id: sb
                for sb in self._mst_repo.list_subjects(session, payload.institution_id)
            }
            selected_subjects = (
                [
                    all_subjects[sbid]
                    for sbid in payload.selected_subject_ids
                    if sbid in all_subjects
                ]
                if payload.selected_subject_ids
                else list(all_subjects.values())
            )
            if payload.selected_subject_ids and len(
                set(payload.selected_subject_ids)
            ) != len(selected_subjects):
                raise ValidationError("Terdapat mapel yang tidak valid pada pilihan.")

            all_staff = [
                st
                for st in self._mst_repo.list_all_staff(session, payload.institution_id)
                if st.active
            ]
            teaching_rels = [
                {
                    "staff_id": ta.staff_id,
                    "class_id": ta.class_id,
                    "subject_id": ta.subject_id,
                }
                for ta in self._mst_repo.list_teaching_assignments(
                    session, payload.institution_id
                )
            ]
            settings_row = self._cfg_repo.get_setting(
                session, payload.institution_id, "typed_settings"
            )
            frozen_settings = (
                json.loads(settings_row.value_json) if settings_row else {}
            )

            exam = Exam(
                id=_new_id(),
                institution_id=payload.institution_id,
                year_id=payload.year_id,
                exam_type_id=payload.exam_type_id,
                title=payload.title,
                semester_label=payload.semester_label,
                mode=payload.mode,
                starts_on=payload.starts_on,
                ends_on=payload.ends_on,
                state="DRAFT",
                config_json=json.dumps(
                    {
                        "settings_snapshot": frozen_settings,
                        "teaching_snapshot": teaching_rels,
                        "numbering_revision": 0,
                        "cards_printed": False,
                        "cards_stale": False,
                        "documents_stale": False,
                    }
                ),
                revision=1,
                created_at=now,
                updated_at=now,
            )
            session.add(exam)
            session.flush()

            participants_by_class: dict[str, list[str]] = {}
            for stu_id in sorted(selected_student_set):
                stu = all_students[stu_id]
                student_enr = enrollments_by_student.get(stu_id)
                cls_obj = (
                    all_classes.get(student_enr.class_id)
                    if student_enr is not None
                    else None
                )
                lvl_label = all_levels.get(cls_obj.level_id) if cls_obj else None
                cls_label = cls_obj.name if cls_obj else None

                person = ExamPerson(
                    id=_new_id(),
                    exam_id=exam.id,
                    source_id=stu.id,
                    kind="student",
                    code=stu.nis or stu.id[:8],
                    display_name=stu.full_name,
                    level_label=lvl_label,
                    class_label=cls_label,
                    photo_asset_id=stu.photo_asset_id,
                    snapshot_json=json.dumps({"nis": stu.nis, "nisn": stu.nisn}),
                    revision=1,
                    created_at=now,
                    updated_at=now,
                )
                session.add(person)
                session.flush()

                part = ExamParticipant(
                    id=_new_id(),
                    exam_id=exam.id,
                    exam_person_id=person.id,
                    participant_number=None,
                    eligibility="eligible",
                    accommodation_json=stu.accommodation_json,
                    revision=1,
                    created_at=now,
                    updated_at=now,
                )
                session.add(part)
                session.flush()
                group_key = cls_label or "Umum"
                participants_by_class.setdefault(group_key, []).append(part.id)

            for st in all_staff:
                session.add(
                    ExamPerson(
                        id=_new_id(),
                        exam_id=exam.id,
                        source_id=st.id,
                        kind="staff",
                        code=st.staff_code,
                        display_name=st.full_name,
                        snapshot_json=json.dumps({"nip": st.nip, "role": st.role}),
                        revision=1,
                        created_at=now,
                        updated_at=now,
                    )
                )

            for rm in selected_rooms:
                session.add(
                    ExamRoom(
                        id=_new_id(),
                        exam_id=exam.id,
                        source_room_id=rm.id,
                        code=rm.code,
                        name=rm.name,
                        layout_json=rm.layout_json,
                        capacity_limit=rm.capacity_limit,
                        mode=rm.mode,
                        revision=1,
                        created_at=now,
                        updated_at=now,
                    )
                )

            created_subjects: list[ExamSubject] = []
            for sb in selected_subjects:
                es = ExamSubject(
                    id=_new_id(),
                    exam_id=exam.id,
                    source_subject_id=sb.id,
                    code=sb.code,
                    name=sb.name,
                    revision=1,
                    created_at=now,
                    updated_at=now,
                )
                session.add(es)
                created_subjects.append(es)
            session.flush()

            for grp_label, part_ids in sorted(participants_by_class.items()):
                grp = ExamGroup(
                    id=_new_id(),
                    exam_id=exam.id,
                    label=grp_label,
                    rule_json=json.dumps({"kind": "class"}),
                    revision=1,
                    created_at=now,
                    updated_at=now,
                )
                session.add(grp)
                session.flush()
                for pid in part_ids:
                    session.add(
                        GroupMember(
                            id=_new_id(),
                            group_id=grp.id,
                            participant_id=pid,
                            revision=1,
                            created_at=now,
                            updated_at=now,
                        )
                    )
                for es in created_subjects:
                    session.add(
                        ExamRequirement(
                            id=_new_id(),
                            group_id=grp.id,
                            exam_subject_id=es.id,
                            attempt_no=1,
                            duration_min=90,
                            mode=payload.mode,
                            eligible_sessions_json="[]",
                            revision=1,
                            created_at=now,
                            updated_at=now,
                        )
                    )

            session.flush()
            return {"exam": _serialize_exam(exam)}

    def list_participants(self, payload: ExamScopedPayload) -> dict[str, Any]:
        with session_scope(self._session_factory) as session:
            exam = self._require_exam(session, payload.institution_id, payload.exam_id)
            people = {
                p.id: p
                for p in self._repo.list_people(session, exam.id, kind="student")
            }
            parts = self._repo.list_participants(session, exam.id)
            items = []
            for pt in parts:
                person = people.get(pt.exam_person_id)
                if person is None:
                    continue
                items.append(
                    {
                        "id": pt.id,
                        "exam_person_id": pt.exam_person_id,
                        "code": person.code,
                        "display_name": person.display_name,
                        "level_label": person.level_label,
                        "class_label": person.class_label,
                        "participant_number": pt.participant_number,
                        "eligibility": pt.eligibility,
                        "revision": pt.revision,
                    }
                )
            items.sort(key=lambda x: str(x["display_name"]))
            return {"items": items}

    def generate_participant_numbers(
        self, payload: NumberingGeneratePayload
    ) -> dict[str, Any]:
        now = _now_iso()
        with session_scope(self._session_factory) as session:
            exam = self._require_exam(session, payload.institution_id, payload.exam_id)
            _assert_not_archived(exam)
            _check_revision(exam.revision, payload.expected_revision)

            people = {
                p.id: p
                for p in self._repo.list_people(session, exam.id, kind="student")
            }
            parts = self._repo.list_participants(session, exam.id)

            def _sort_key(pt: ExamParticipant) -> tuple[str, str]:
                p = people[pt.exam_person_id]
                if payload.sort_by == "class_name":
                    return (p.class_label or "", p.display_name)
                if payload.sort_by == "nis":
                    return (p.code, p.display_name)
                return (p.display_name, p.code)

            ordered = sorted(parts, key=_sort_key)
            for idx, pt in enumerate(ordered):
                seq_str = str(payload.start_seq + idx).zfill(payload.padding)
                pt.participant_number = f"{payload.prefix}{payload.separator}{seq_str}"
                pt.revision += 1
                pt.updated_at = now

            cfg = json.loads(exam.config_json)
            cfg["numbering_revision"] = int(cfg.get("numbering_revision", 0)) + 1
            if cfg.get("cards_printed"):
                cfg["cards_stale"] = True
            if payload.mark_cards_printed:
                cfg["cards_printed"] = True
                cfg["cards_stale"] = False
            exam.config_json = json.dumps(cfg)
            exam.revision += 1
            exam.updated_at = now
            session.flush()
            return {"exam": _serialize_exam(exam), "assigned_count": len(ordered)}

    def override_participant_number(
        self, payload: NumberingOverridePayload
    ) -> dict[str, Any]:
        now = _now_iso()
        with session_scope(self._session_factory) as session:
            exam = self._require_exam(session, payload.institution_id, payload.exam_id)
            _assert_not_archived(exam)
            _check_revision(exam.revision, payload.expected_revision)

            pt = self._repo.get_participant(session, exam.id, payload.participant_id)
            if pt is None:
                raise NotFoundError("Peserta kegiatan tidak ditemukan.")

            try:
                pt.participant_number = payload.participant_number
                pt.revision += 1
                pt.updated_at = now
                session.flush()
            except IntegrityError as exc:
                raise ConflictError(
                    f"Nomor peserta '{payload.participant_number}' sudah digunakan."
                ) from exc

            cfg = json.loads(exam.config_json)
            cfg["numbering_revision"] = int(cfg.get("numbering_revision", 0)) + 1
            if cfg.get("cards_printed"):
                cfg["cards_stale"] = True
            exam.config_json = json.dumps(cfg)
            exam.revision += 1
            exam.updated_at = now
            session.flush()
            return {
                "exam": _serialize_exam(exam),
                "participant_number": pt.participant_number,
                "cards_stale": bool(cfg.get("cards_stale")),
            }

    def list_groups(self, payload: ExamScopedPayload) -> dict[str, Any]:
        with session_scope(self._session_factory) as session:
            exam = self._require_exam(session, payload.institution_id, payload.exam_id)
            groups = self._repo.list_groups(session, exam.id)
            subjects = {s.id: s for s in self._repo.list_subjects(session, exam.id)}
            items = []
            for grp in groups:
                members = self._repo.list_group_members(session, grp.id)
                reqs = self._repo.list_requirements(session, grp.id)
                items.append(
                    {
                        "id": grp.id,
                        "label": grp.label,
                        "member_count": len(members),
                        "participant_ids": [m.participant_id for m in members],
                        "requirements": [
                            {
                                "id": r.id,
                                "exam_subject_id": r.exam_subject_id,
                                "subject_code": subjects[r.exam_subject_id].code
                                if r.exam_subject_id in subjects
                                else "",
                                "subject_name": subjects[r.exam_subject_id].name
                                if r.exam_subject_id in subjects
                                else "",
                                "attempt_no": r.attempt_no,
                                "duration_min": r.duration_min,
                                "mode": r.mode,
                            }
                            for r in reqs
                        ],
                    }
                )
            return {
                "groups": items,
                "subjects": [
                    {"id": s.id, "code": s.code, "name": s.name}
                    for s in subjects.values()
                ],
            }

    def save_group(self, payload: ExamGroupSavePayload) -> dict[str, Any]:
        now = _now_iso()
        with session_scope(self._session_factory) as session:
            exam = self._require_exam(session, payload.institution_id, payload.exam_id)
            _assert_not_archived(exam)

            valid_pids = {p.id for p in self._repo.list_participants(session, exam.id)}
            for pid in payload.participant_ids:
                if pid not in valid_pids:
                    raise ValidationError(
                        f"Peserta '{pid}' tidak termasuk kegiatan ini."
                    )

            try:
                if payload.id is None:
                    grp = ExamGroup(
                        id=_new_id(),
                        exam_id=exam.id,
                        label=payload.label.strip(),
                        rule_json=json.dumps({"kind": "custom"}),
                        revision=1,
                        created_at=now,
                        updated_at=now,
                    )
                    session.add(grp)
                    session.flush()
                else:
                    existing_grp = self._repo.get_group(session, exam.id, payload.id)
                    if existing_grp is None:
                        raise NotFoundError("Kelompok ujian tidak ditemukan.")
                    existing_grp.label = payload.label.strip()
                    existing_grp.revision += 1
                    existing_grp.updated_at = now
                    grp = existing_grp
                    for old_m in self._repo.list_group_members(session, grp.id):
                        session.delete(old_m)
                    session.flush()

                for pid in dict.fromkeys(payload.participant_ids):
                    session.add(
                        GroupMember(
                            id=_new_id(),
                            group_id=grp.id,
                            participant_id=pid,
                            revision=1,
                            created_at=now,
                            updated_at=now,
                        )
                    )
                session.flush()
                return {"id": grp.id, "label": grp.label}
            except IntegrityError as exc:
                raise ConflictError("Nama kelompok ujian sudah digunakan.") from exc

    def save_requirement(self, payload: ExamRequirementSavePayload) -> dict[str, Any]:
        now = _now_iso()
        with session_scope(self._session_factory) as session:
            exam = self._require_exam(session, payload.institution_id, payload.exam_id)
            _assert_not_archived(exam)
            if self._repo.get_group(session, exam.id, payload.group_id) is None:
                raise NotFoundError("Kelompok ujian tidak ditemukan.")
            if (
                self._repo.get_subject(session, exam.id, payload.exam_subject_id)
                is None
            ):
                raise NotFoundError("Mata pelajaran kegiatan tidak ditemukan.")

            try:
                req = ExamRequirement(
                    id=_new_id(),
                    group_id=payload.group_id,
                    exam_subject_id=payload.exam_subject_id,
                    attempt_no=payload.attempt_no,
                    duration_min=payload.duration_min,
                    mode=payload.mode,
                    eligible_sessions_json="[]",
                    revision=1,
                    created_at=now,
                    updated_at=now,
                )
                session.add(req)
                session.flush()
                return {"id": req.id}
            except IntegrityError as exc:
                raise ConflictError(
                    "Kebutuhan mapel dan attempt tersebut sudah ada pada kelompok ini."
                ) from exc

    def delete_requirement(
        self, payload: ExamRequirementDeletePayload
    ) -> dict[str, Any]:
        with session_scope(self._session_factory) as session:
            exam = self._require_exam(session, payload.institution_id, payload.exam_id)
            _assert_not_archived(exam)
            req = self._repo.get_requirement(session, payload.requirement_id)
            if (
                req is None
                or self._repo.get_group(session, exam.id, req.group_id) is None
            ):
                raise NotFoundError("Kebutuhan ujian tidak ditemukan.")
            session.delete(req)
            return {"deleted": True}

    def transition_state(self, payload: ExamTransitionPayload) -> dict[str, Any]:
        now = _now_iso()
        with session_scope(self._session_factory) as session:
            exam = self._require_exam(session, payload.institution_id, payload.exam_id)
            _check_revision(exam.revision, payload.expected_revision)
            current = exam.state
            target = payload.target_state

            if current == target:
                return {"exam": _serialize_exam(exam)}

            is_backward = _STATE_ORDER[target] < _STATE_ORDER[current]
            if current == "ARCHIVED" and target != "PREPARATION":
                raise AppError(
                    "PERMISSION_DENIED",
                    "Kegiatan diarsipkan hanya bisa dibuka kembali ke status "
                    "PREPARATION.",
                )

            if is_backward:
                if not payload.reason.strip():
                    raise ValidationError(
                        "Alasan wajib diisi untuk mundur status atau reopen kegiatan.",
                        field_errors={"reason": "Wajib diisi"},
                    )
                cfg = json.loads(exam.config_json)
                cfg["documents_stale"] = True
                exam.config_json = json.dumps(cfg)

            if target == "READY":
                blockers = self._compute_readiness_blockers(session, exam)
                if blockers:
                    raise ConflictError(f"Tidak dapat mengubah ke READY: {blockers[0]}")

            exam.state = target
            exam.revision += 1
            exam.updated_at = now

            session.add(
                AuditEvent(
                    id=_new_id(),
                    institution_id=exam.institution_id,
                    exam_id=exam.id,
                    actor=payload.actor,
                    action="exam.state_transition",
                    entity_type="exam",
                    entity_id=exam.id,
                    at=now,
                    change_summary_json=json.dumps(
                        {
                            "from": current,
                            "to": target,
                            "reason": payload.reason.strip(),
                        }
                    ),
                    correlation_id=get_correlation_id(),
                )
            )
            session.flush()
            return {"exam": _serialize_exam(exam)}

    def clone_event(self, payload: ExamClonePayload) -> dict[str, Any]:
        now = _now_iso()
        with session_scope(self._session_factory) as session:
            source = self._require_exam(
                session, payload.institution_id, payload.source_exam_id
            )
            year_id = payload.year_id or source.year_id
            if (
                self._cfg_repo.get_year(session, payload.institution_id, year_id)
                is None
            ):
                raise NotFoundError("Tahun ajaran tujuan tidak ditemukan.")

            src_cfg = json.loads(source.config_json)
            new_exam = Exam(
                id=_new_id(),
                institution_id=source.institution_id,
                year_id=year_id,
                exam_type_id=source.exam_type_id,
                title=payload.title.strip(),
                semester_label=(
                    payload.semester_label.strip()
                    if payload.semester_label
                    else source.semester_label
                ),
                mode=source.mode,
                starts_on=payload.starts_on,
                ends_on=payload.ends_on,
                state="DRAFT",
                config_json=json.dumps(
                    {
                        "settings_snapshot": src_cfg.get("settings_snapshot", {}),
                        "teaching_snapshot": src_cfg.get("teaching_snapshot", []),
                        "numbering_revision": 0,
                        "cards_printed": False,
                        "cards_stale": False,
                        "documents_stale": False,
                        "cloned_from_exam_id": source.id,
                    }
                ),
                revision=1,
                created_at=now,
                updated_at=now,
            )
            session.add(new_exam)
            session.flush()

            if payload.copy_rooms:
                for rm in self._repo.list_rooms(session, source.id):
                    session.add(
                        ExamRoom(
                            id=_new_id(),
                            exam_id=new_exam.id,
                            source_room_id=rm.source_room_id,
                            code=rm.code,
                            name=rm.name,
                            layout_json=rm.layout_json,
                            capacity_limit=rm.capacity_limit,
                            mode=rm.mode,
                            revision=1,
                            created_at=now,
                            updated_at=now,
                        )
                    )

            subject_map: dict[str, str] = {}
            if payload.copy_subjects:
                for sb in self._repo.list_subjects(session, source.id):
                    new_sb_id = _new_id()
                    subject_map[sb.id] = new_sb_id
                    session.add(
                        ExamSubject(
                            id=new_sb_id,
                            exam_id=new_exam.id,
                            source_subject_id=sb.source_subject_id,
                            code=sb.code,
                            name=sb.name,
                            revision=1,
                            created_at=now,
                            updated_at=now,
                        )
                    )

            if payload.copy_groups_structure:
                for grp in self._repo.list_groups(session, source.id):
                    new_grp = ExamGroup(
                        id=_new_id(),
                        exam_id=new_exam.id,
                        label=grp.label,
                        rule_json=grp.rule_json,
                        revision=1,
                        created_at=now,
                        updated_at=now,
                    )
                    session.add(new_grp)
                    session.flush()
                    if payload.copy_subjects:
                        for req in self._repo.list_requirements(session, grp.id):
                            mapped_subj = subject_map.get(req.exam_subject_id)
                            if mapped_subj:
                                session.add(
                                    ExamRequirement(
                                        id=_new_id(),
                                        group_id=new_grp.id,
                                        exam_subject_id=mapped_subj,
                                        attempt_no=req.attempt_no,
                                        duration_min=req.duration_min,
                                        mode=req.mode,
                                        eligible_sessions_json="[]",
                                        revision=1,
                                        created_at=now,
                                        updated_at=now,
                                    )
                                )

            session.flush()
            return {"exam": _serialize_exam(new_exam)}

    def get_dashboard(self, payload: ExamScopedPayload) -> dict[str, Any]:
        with session_scope(self._session_factory) as session:
            exam = self._require_exam(session, payload.institution_id, payload.exam_id)
            parts = self._repo.list_participants(session, exam.id)
            rooms = self._repo.list_rooms(session, exam.id)
            staff = self._repo.list_people(session, exam.id, kind="staff")
            groups = self._repo.list_groups(session, exam.id)

            numbered_count = sum(1 for p in parts if p.participant_number)
            total_capacity = sum(r.capacity_limit for r in rooms)
            req_count = sum(
                len(self._repo.list_requirements(session, g.id)) for g in groups
            )
            blockers = self._compute_readiness_blockers(session, exam)
            cfg = json.loads(exam.config_json)

            checklist = [
                {
                    "id": "participants",
                    "label": "Peserta kegiatan",
                    "done": len(parts) > 0,
                    "detail": f"{len(parts)} peserta · {numbered_count} bernomor",
                    "route": "/events",
                },
                {
                    "id": "rooms",
                    "label": "Ruang & kapasitas",
                    "done": len(rooms) > 0 and total_capacity >= len(parts),
                    "detail": f"{len(rooms)} ruang · kapasitas {total_capacity}",
                    "route": "/master",
                },
                {
                    "id": "numbering",
                    "label": "Penomoran peserta",
                    "done": len(parts) > 0 and numbered_count == len(parts),
                    "detail": f"{numbered_count} / {len(parts)} terisi",
                    "route": "/events",
                },
                {
                    "id": "requirements",
                    "label": "Kelompok & kebutuhan mapel",
                    "done": req_count > 0,
                    "detail": f"{len(groups)} kelompok · {req_count} kebutuhan",
                    "route": "/events",
                },
            ]
            if cfg.get("cards_stale"):
                checklist.append(
                    {
                        "id": "cards_stale",
                        "label": "Kartu peserta perlu cetak ulang",
                        "done": False,
                        "detail": "Nomor peserta berubah setelah cetak.",
                        "route": "/events",
                    }
                )

            return {
                "exam": _serialize_exam(exam),
                "counts": {
                    "participants": len(parts),
                    "numbered_participants": numbered_count,
                    "rooms": len(rooms),
                    "total_capacity": total_capacity,
                    "staff": len(staff),
                    "groups": len(groups),
                    "requirements": req_count,
                },
                "checklist": checklist,
                "blockers": blockers,
            }

    def _compute_readiness_blockers(self, session: Session, exam: Exam) -> list[str]:
        blockers: list[str] = []
        parts = self._repo.list_participants(session, exam.id)
        rooms = self._repo.list_rooms(session, exam.id)
        groups = self._repo.list_groups(session, exam.id)

        if not parts:
            blockers.append("Belum ada peserta pada kegiatan ini.")
        if not rooms:
            blockers.append("Belum ada ruang ujian pada kegiatan ini.")
        if parts and rooms:
            cap = sum(r.capacity_limit for r in rooms)
            if cap < len(parts):
                blockers.append(
                    f"Kapasitas ruang ({cap}) kurang dari jumlah peserta "
                    f"({len(parts)})."
                )
        missing_nums = [p for p in parts if not p.participant_number]
        if parts and missing_nums:
            blockers.append(
                f"{len(missing_nums)} peserta belum memiliki nomor peserta."
            )
        if not groups or not any(
            self._repo.list_requirements(session, g.id) for g in groups
        ):
            blockers.append("Belum ada kebutuhan mata pelajaran pada kelompok ujian.")
        return blockers

    def _require_exam(
        self, session: Session, institution_id: str, exam_id: str
    ) -> Exam:
        exam = self._repo.get_exam(session, institution_id, exam_id)
        if exam is None:
            raise NotFoundError("Kegiatan ujian tidak ditemukan.")
        return exam
