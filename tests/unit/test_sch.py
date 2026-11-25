"""Unit tests for SCH-01..SCH-08 (overlap, rules, solver, workload, reserve)."""

from __future__ import annotations

from datetime import UTC, datetime

from backend.modules.sch.schemas import InvigilationRules
from backend.modules.sch.solver import solve_invigilation
from backend.modules.sch.validator import (
    ReserveCandidate,
    SlotCandidate,
    StaffCandidate,
    validate_invigilation_schedule,
)


def _dt(h: int, m: int = 0) -> datetime:
    return datetime(2026, 12, 1, h, m, tzinfo=UTC)


def test_validator_detects_interval_overlap_across_distinct_sessions() -> None:
    staff = {
        "t1": StaffCandidate(
            id="t1",
            code="G1",
            display_name="Guru Satu",
            role_skills={"primary"},
            max_daily=None,
            max_total=None,
            target_weight_pct=100,
            unavailable_intervals=[],
            taught_classes=set(),
            taught_subjects=set(),
        )
    }
    slots = {
        "s1": SlotCandidate(
            id="s1",
            room_session_id="rs1",
            session_id="ses-1",
            session_label="Sesi Pagi A",
            local_date="2026-12-01",
            starts_at=_dt(7, 30),
            ends_at=_dt(9, 0),
            room_code="R01",
            role_code="primary",
            slot_index=1,
            class_labels=set(),
            subject_codes=set(),
        ),
        "s2": SlotCandidate(
            id="s2",
            room_session_id="rs2",
            session_id="ses-2",
            session_label="Sesi Pagi B",
            local_date="2026-12-01",
            starts_at=_dt(8, 30),
            ends_at=_dt(10, 0),
            room_code="R02",
            role_code="primary",
            slot_index=1,
            class_labels=set(),
            subject_codes=set(),
        ),
    }
    res = validate_invigilation_schedule(
        staff=staff,
        slots=slots,
        assignments={"s1": "t1", "s2": "t1"},
        reserves=[],
        hard_avoid_own_class=True,
        hard_avoid_own_subject=False,
        hard_max_daily=True,
        hard_max_total=True,
    )
    assert res["valid"] is False
    assert any(c["code"] == "STAFF_INTERVAL_OVERLAP" for c in res["hard_conflicts"])


def test_solver_respects_availability_own_class_part_time_and_locks() -> None:
    staff = [
        StaffCandidate(
            id="t1",
            code="G1",
            display_name="Guru Full",
            role_skills={"primary", "secondary"},
            max_daily=2,
            max_total=4,
            target_weight_pct=100,
            unavailable_intervals=[],
            taught_classes={"7A"},
            taught_subjects=set(),
        ),
        StaffCandidate(
            id="t2",
            code="G2",
            display_name="Guru Part",
            role_skills={"primary"},
            max_daily=2,
            max_total=4,
            target_weight_pct=50,
            unavailable_intervals=[(_dt(7, 0), _dt(9, 0))],
            taught_classes=set(),
            taught_subjects=set(),
        ),
    ]
    slots = [
        SlotCandidate(
            id="s1",
            room_session_id="rs1",
            session_id="ses-1",
            session_label="Sesi 1",
            local_date="2026-12-01",
            starts_at=_dt(7, 30),
            ends_at=_dt(9, 0),
            room_code="R01",
            role_code="primary",
            slot_index=1,
            class_labels={"8A"},
            subject_codes={"MAT"},
        ),
        SlotCandidate(
            id="s2",
            room_session_id="rs2",
            session_id="ses-2",
            session_label="Sesi 2",
            local_date="2026-12-01",
            starts_at=_dt(9, 30),
            ends_at=_dt(11, 0),
            room_code="R01",
            role_code="primary",
            slot_index=1,
            class_labels={"7A"},
            subject_codes={"IPA"},
        ),
    ]
    res = solve_invigilation(
        staff=staff,
        slots=slots,
        locked_assignments={},
        rules=InvigilationRules(hard_avoid_own_class=True),
    )
    assert res["status"] in ("OPTIMAL", "FEASIBLE")
    assert res["assignments"]["s1"] == "t1"
    assert res["assignments"]["s2"] == "t2"

    # Reserve on Sesi 2 for t1 is valid and not counted as active duty
    staff_map = {p.id: p for p in staff}
    slot_map = {s.id: s for s in slots}
    val_ok = validate_invigilation_schedule(
        staff=staff_map,
        slots=slot_map,
        assignments=res["assignments"],
        reserves=[
            ReserveCandidate(
                id="r1",
                session_id="ses-2",
                session_label="Sesi 2",
                starts_at=_dt(9, 30),
                ends_at=_dt(11, 0),
                exam_person_id="t1",
            )
        ],
        hard_avoid_own_class=True,
        hard_avoid_own_subject=False,
        hard_max_daily=True,
        hard_max_total=True,
    )
    assert val_ok["valid"] is True
    w_t1 = [w for w in val_ok["workload"] if w["exam_person_id"] == "t1"][0]
    assert w_t1["active_count"] == 1
    assert w_t1["reserve_count"] == 1
