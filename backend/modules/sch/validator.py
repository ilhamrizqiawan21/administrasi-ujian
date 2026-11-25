"""Independent validator for SCH-01..SCH-08 (interval overlap, rules, workload)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any


@dataclass(frozen=True)
class StaffCandidate:
    id: str
    code: str
    display_name: str
    role_skills: set[str]
    max_daily: int | None
    max_total: int | None
    target_weight_pct: int
    unavailable_intervals: list[tuple[datetime, datetime]]
    taught_classes: set[str]
    taught_subjects: set[str]


@dataclass(frozen=True)
class SlotCandidate:
    id: str
    room_session_id: str
    session_id: str
    session_label: str
    local_date: str
    starts_at: datetime
    ends_at: datetime
    room_code: str
    role_code: str
    slot_index: int
    class_labels: set[str]
    subject_codes: set[str]


@dataclass(frozen=True)
class ReserveCandidate:
    id: str
    session_id: str
    session_label: str
    starts_at: datetime
    ends_at: datetime
    exam_person_id: str


def intervals_overlap(
    a_start: datetime, a_end: datetime, b_start: datetime, b_end: datetime
) -> bool:
    return a_start < b_end and b_start < a_end


def validate_invigilation_schedule(
    *,
    staff: dict[str, StaffCandidate],
    slots: dict[str, SlotCandidate],
    assignments: dict[str, str],  # slot_id -> exam_person_id
    reserves: list[ReserveCandidate],
    hard_avoid_own_class: bool,
    hard_avoid_own_subject: bool,
    hard_max_daily: bool,
    hard_max_total: bool,
) -> dict[str, Any]:
    """Independently validate active invigilation, reserves, and workload."""
    hard_conflicts: list[dict[str, Any]] = []
    soft_violations: list[dict[str, Any]] = []

    staff_slots: dict[str, list[SlotCandidate]] = {pid: [] for pid in staff}
    own_class_count = 0
    own_subject_count = 0

    for slot_id, slot in slots.items():
        pid = assignments.get(slot_id)
        if pid is None:
            hard_conflicts.append(
                {
                    "code": "UNASSIGNED_SLOT",
                    "message": (
                        f"Slot {slot.room_code} {slot.session_label} "
                        f"({slot.role_code} #{slot.slot_index}) belum terisi."
                    ),
                    "conflicting_ids": [slot_id],
                }
            )
            continue

        person = staff.get(pid)
        if person is None:
            hard_conflicts.append(
                {
                    "code": "INVALID_STAFF",
                    "message": "Pengawas tidak valid.",
                    "conflicting_ids": [slot_id, pid],
                }
            )
            continue

        if slot.role_code not in person.role_skills:
            hard_conflicts.append(
                {
                    "code": "ROLE_INCOMPATIBLE",
                    "message": (
                        f"{person.display_name} tidak memiliki peran {slot.role_code}."
                    ),
                    "conflicting_ids": [slot_id, pid],
                }
            )

        for u_start, u_end in person.unavailable_intervals:
            if intervals_overlap(slot.starts_at, slot.ends_at, u_start, u_end):
                hard_conflicts.append(
                    {
                        "code": "STAFF_UNAVAILABLE",
                        "message": (
                            f"{person.display_name} tidak tersedia pada "
                            f"{slot.session_label}."
                        ),
                        "conflicting_ids": [slot_id, pid],
                    }
                )
                break

        if person.taught_classes & slot.class_labels:
            own_class_count += 1
            msg = (
                f"{person.display_name} mengawasi rombel ajarannya di "
                f"{slot.room_code} ({slot.session_label})."
            )
            if hard_avoid_own_class:
                hard_conflicts.append(
                    {
                        "code": "OWN_CLASS_CONFLICT",
                        "message": msg,
                        "conflicting_ids": [slot_id, pid],
                    }
                )
            else:
                soft_violations.append({"code": "OWN_CLASS_SOFT", "message": msg})

        if person.taught_subjects & slot.subject_codes:
            own_subject_count += 1
            msg = (
                f"{person.display_name} mengawasi mapel ajarannya di "
                f"{slot.room_code} ({slot.session_label})."
            )
            if hard_avoid_own_subject:
                hard_conflicts.append(
                    {
                        "code": "OWN_SUBJECT_CONFLICT",
                        "message": msg,
                        "conflicting_ids": [slot_id, pid],
                    }
                )
            else:
                soft_violations.append({"code": "OWN_SUBJECT_SOFT", "message": msg})

        staff_slots[pid].append(slot)

    # Interval overlap across distinct session IDs for active invigilations
    for pid, assigned_list in staff_slots.items():
        person = staff[pid]
        sorted_list = sorted(assigned_list, key=lambda s: s.starts_at)
        for i in range(len(sorted_list)):
            for j in range(i + 1, len(sorted_list)):
                sa = sorted_list[i]
                sb = sorted_list[j]
                if intervals_overlap(
                    sa.starts_at, sa.ends_at, sb.starts_at, sb.ends_at
                ):
                    hard_conflicts.append(
                        {
                            "code": "STAFF_INTERVAL_OVERLAP",
                            "message": (
                                f"{person.display_name} bentrok waktu antara "
                                f"{sa.session_label} dan {sb.session_label}."
                            ),
                            "conflicting_ids": [sa.id, sb.id, pid],
                        }
                    )

        # Daily and total caps (active duty only)
        daily_counts: dict[str, int] = {}
        for s in sorted_list:
            daily_counts[s.local_date] = daily_counts.get(s.local_date, 0) + 1

        if person.max_daily is not None:
            for dt, cnt in daily_counts.items():
                if cnt > person.max_daily:
                    msg = (
                        f"{person.display_name} melebihi batas harian "
                        f"({cnt} > {person.max_daily}) pada {dt}."
                    )
                    if hard_max_daily:
                        hard_conflicts.append(
                            {
                                "code": "MAX_DAILY_EXCEEDED",
                                "message": msg,
                                "conflicting_ids": [pid],
                            }
                        )
                    else:
                        soft_violations.append(
                            {"code": "MAX_DAILY_SOFT", "message": msg}
                        )

        if person.max_total is not None and len(sorted_list) > person.max_total:
            msg = (
                f"{person.display_name} melebihi batas total "
                f"({len(sorted_list)} > {person.max_total})."
            )
            if hard_max_total:
                hard_conflicts.append(
                    {
                        "code": "MAX_TOTAL_EXCEEDED",
                        "message": msg,
                        "conflicting_ids": [pid],
                    }
                )
            else:
                soft_violations.append({"code": "MAX_TOTAL_SOFT", "message": msg})

    # Reserve validation (SCH-08): check availability & overlap
    reserve_counts: dict[str, int] = {pid: 0 for pid in staff}
    reserves_by_staff: dict[str, list[ReserveCandidate]] = {pid: [] for pid in staff}
    for r in reserves:
        person_opt = staff.get(r.exam_person_id)
        if person_opt is None:
            continue
        reserve_counts[r.exam_person_id] = reserve_counts.get(r.exam_person_id, 0) + 1
        for u_start, u_end in person_opt.unavailable_intervals:
            if intervals_overlap(r.starts_at, r.ends_at, u_start, u_end):
                hard_conflicts.append(
                    {
                        "code": "RESERVE_UNAVAILABLE",
                        "message": (
                            f"Cadangan {person_opt.display_name} tidak tersedia "
                            f"pada {r.session_label}."
                        ),
                        "conflicting_ids": [r.id, r.exam_person_id],
                    }
                )
                break
        for active_slot in staff_slots.get(r.exam_person_id, []):
            if intervals_overlap(
                r.starts_at, r.ends_at, active_slot.starts_at, active_slot.ends_at
            ):
                hard_conflicts.append(
                    {
                        "code": "RESERVE_ACTIVE_OVERLAP",
                        "message": (
                            f"Cadangan {person_opt.display_name} bentrok dengan "
                            f"tugas aktif di {active_slot.room_code}."
                        ),
                        "conflicting_ids": [r.id, active_slot.id, r.exam_person_id],
                    }
                )
                break
        for prev_r in reserves_by_staff.get(r.exam_person_id, []):
            if intervals_overlap(
                r.starts_at, r.ends_at, prev_r.starts_at, prev_r.ends_at
            ):
                hard_conflicts.append(
                    {
                        "code": "RESERVE_OVERLAP",
                        "message": (
                            f"Cadangan {person_opt.display_name} ganda pada "
                            f"interval {r.session_label}."
                        ),
                        "conflicting_ids": [r.id, prev_r.id, r.exam_person_id],
                    }
                )
                break
        reserves_by_staff.setdefault(r.exam_person_id, []).append(r)

    # Workload summary (SCH-05): counts match active assignment list; reserve separate
    total_weight = sum(p.target_weight_pct for p in staff.values()) or 1
    total_slots = len(slots)
    workload: list[dict[str, Any]] = []
    active_counts_list: list[int] = []
    for pid, person in staff.items():
        active_cnt = len(staff_slots.get(pid, []))
        active_counts_list.append(active_cnt)
        daily: dict[str, int] = {}
        for s in staff_slots.get(pid, []):
            daily[s.local_date] = daily.get(s.local_date, 0) + 1
        expected = round(total_slots * person.target_weight_pct / total_weight, 2)
        workload.append(
            {
                "exam_person_id": pid,
                "code": person.code,
                "display_name": person.display_name,
                "active_count": active_cnt,
                "reserve_count": reserve_counts.get(pid, 0),
                "target_weight_pct": person.target_weight_pct,
                "expected_load": expected,
                "deviation": round(active_cnt - expected, 2),
                "daily_counts": daily,
            }
        )

    return {
        "valid": len(hard_conflicts) == 0,
        "hard_conflicts": hard_conflicts,
        "soft_violations": soft_violations,
        "workload": workload,
        "summary": {
            "total_slots": total_slots,
            "assigned_slots": len(assignments),
            "min_load": min(active_counts_list) if active_counts_list else 0,
            "max_load": max(active_counts_list) if active_counts_list else 0,
            "own_class_count": own_class_count,
            "own_subject_count": own_subject_count,
        },
    }
