"""Unit tests for ROM-01..ROM-05 (room layout, candidate/solver, validator)."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from backend.modules.rom.schemas import AllocationPolicy, RoomLayoutUpdatePayload
from backend.modules.rom.solver import solve_seating
from backend.modules.rom.validator import (
    ParticipantCandidate,
    SeatCandidate,
    validate_seating_allocation,
)


def _make_seats(
    rows: int, cols: int, accessible_codes: set[str] | None = None
) -> list[SeatCandidate]:
    acc = accessible_codes or set()
    out: list[SeatCandidate] = []
    for r in range(1, rows + 1):
        for c in range(1, cols + 1):
            code = f"R{r}C{c}S1"
            out.append(
                SeatCandidate(
                    id=f"seat-{code}",
                    exam_room_id="room-1",
                    room_code="R01",
                    seat_code=code,
                    desk_row=r,
                    desk_col=c,
                    seat_index=1,
                    enabled=True,
                    accessible=code in acc,
                )
            )
    return out


def test_room_layout_payload_rejects_capacity_over_enabled_slots() -> None:
    with pytest.raises(ValidationError, match="melebihi kursi aktif"):
        RoomLayoutUpdatePayload(
            institution_id="inst-1",
            exam_id="exam-1",
            plan_id="plan-1",
            exam_room_id="room-1",
            rows=2,
            cols=2,
            seats_per_desk=1,
            capacity_limit=4,
            disabled_cells=["R1C1"],
            accessible_seats=[],
            board_position="top",
        )


def test_solver_reports_capacity_shortfall() -> None:
    seats = _make_seats(1, 2)
    participants = [
        ParticipantCandidate(
            id=f"p-{i}",
            code=f"S{i}",
            display_name=f"Siswa {i}",
            participant_number=f"00{i}",
            level_label="7",
            class_label="7A",
            needs_accessible=False,
        )
        for i in range(1, 4)
    ]
    res = solve_seating(
        participants=participants,
        seats=seats,
        room_caps={"room-1": 2},
        locked_assignments={},
        policy=AllocationPolicy(),
    )
    assert res["status"] == "INFEASIBLE"
    assert res["diagnostics"]["capacity_shortfall"] == 1
    assert "Kapasitas" in res["diagnostics"]["reason"]


def test_solver_reports_impossible_hard_mix_grade() -> None:
    seats = _make_seats(1, 2)
    participants = [
        ParticipantCandidate(
            id="p-1",
            code="S1",
            display_name="Siswa 1",
            participant_number="001",
            level_label="7",
            class_label="7A",
            needs_accessible=False,
        ),
        ParticipantCandidate(
            id="p-2",
            code="S2",
            display_name="Siswa 2",
            participant_number="002",
            level_label="7",
            class_label="7B",
            needs_accessible=False,
        ),
    ]
    res = solve_seating(
        participants=participants,
        seats=seats,
        room_caps={"room-1": 2},
        locked_assignments={},
        policy=AllocationPolicy(hard_mix_grade=True),
    )
    assert res["status"] == "INFEASIBLE"
    assert (
        "tingkat" in res["diagnostics"]["reason"].lower()
        or "aturan keras" in res["diagnostics"]["reason"].lower()
    )


def test_solver_respects_accessible_and_locks_and_passes_validator() -> None:
    seats = _make_seats(2, 2, accessible_codes={"R1C1S1"})
    participants = [
        ParticipantCandidate(
            id="p-1",
            code="S1",
            display_name="Siswa 1",
            participant_number="001",
            level_label="7",
            class_label="7A",
            needs_accessible=True,
        ),
        ParticipantCandidate(
            id="p-2",
            code="S2",
            display_name="Siswa 2",
            participant_number="002",
            level_label="8",
            class_label="8A",
            needs_accessible=False,
        ),
        ParticipantCandidate(
            id="p-3",
            code="S3",
            display_name="Siswa 3",
            participant_number="003",
            level_label="7",
            class_label="7B",
            needs_accessible=False,
        ),
        ParticipantCandidate(
            id="p-4",
            code="S4",
            display_name="Siswa 4",
            participant_number="004",
            level_label="8",
            class_label="8B",
            needs_accessible=False,
        ),
    ]
    res = solve_seating(
        participants=participants,
        seats=seats,
        room_caps={"room-1": 4},
        locked_assignments={"p-2": "seat-R1C2S1"},
        policy=AllocationPolicy(hard_mix_grade=True, require_accessible=True),
    )
    assert res["status"] in ("OPTIMAL", "FEASIBLE")
    assignments = res["assignments"]
    assert assignments["p-1"] == "seat-R1C1S1"
    assert assignments["p-2"] == "seat-R1C2S1"

    validation = validate_seating_allocation(
        participants={p.id: p for p in participants},
        seats={s.id: s for s in seats},
        room_caps={"room-1": 4},
        assignments=assignments,
        hard_mix_grade=True,
        hard_mix_class=False,
        require_accessible=True,
        diagonal_adjacent=False,
    )
    assert validation["valid"] is True
    assert validation["hard_conflicts"] == []
    assert validation["diagnostics"]["same_grade_adjacent"] == 0
