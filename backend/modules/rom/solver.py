"""OR-Tools CP-SAT seating allocation solver (ROM-02..ROM-05)."""

from __future__ import annotations

from typing import Any

from ortools.sat.python import cp_model

from backend.modules.rom.schemas import AllocationPolicy
from backend.modules.rom.validator import (
    ParticipantCandidate,
    SeatCandidate,
    build_adjacent_seat_pairs,
)


def solve_seating(
    *,
    participants: list[ParticipantCandidate],
    seats: list[SeatCandidate],
    room_caps: dict[str, int],
    locked_assignments: dict[str, str],  # participant_id -> seat_id
    policy: AllocationPolicy,
    time_limit_sec: int = 30,
    seed: int = 42,
) -> dict[str, Any]:
    """Allocate eligible participants to enabled seats using CP-SAT."""
    enabled_seats = [s for s in seats if s.enabled]
    total_effective_cap = sum(
        min(
            room_caps.get(rid, 0),
            sum(1 for s in enabled_seats if s.exam_room_id == rid),
        )
        for rid in room_caps
    )

    if len(participants) > total_effective_cap:
        return {
            "status": "INFEASIBLE",
            "assignments": {},
            "diagnostics": {
                "capacity_shortfall": len(participants) - total_effective_cap,
                "reason": (
                    f"Kapasitas kursi aktif ({total_effective_cap}) kurang dari "
                    f"jumlah peserta ({len(participants)})."
                ),
            },
        }

    distinct_grades = {p.level_label for p in participants if p.level_label}
    if policy.hard_mix_grade and len(distinct_grades) <= 1 and len(participants) > 1:
        adj = build_adjacent_seat_pairs(
            enabled_seats, diagonal=policy.diagonal_adjacent
        )
        if adj and len(participants) > len(enabled_seats) // 2 + 1:
            return {
                "status": "INFEASIBLE",
                "assignments": {},
                "diagnostics": {
                    "capacity_shortfall": 0,
                    "reason": (
                        "Pemisahan tingkat keras tidak mungkin karena seluruh peserta "
                        "berasal dari tingkat yang sama."
                    ),
                },
            }

    if policy.mode == "ordered":
        ordered_parts = sorted(
            participants,
            key=lambda p: (p.participant_number or "", p.display_name),
        )
        ordered_seats = sorted(
            enabled_seats,
            key=lambda s: (s.room_code, s.desk_row, s.desk_col, s.seat_index),
        )
        assignments: dict[str, str] = {}
        used_seats: set[str] = set()
        if policy.respect_locks:
            for pid, sid in locked_assignments.items():
                assignments[pid] = sid
                used_seats.add(sid)
        room_used: dict[str, int] = {}
        seat_map = {s.id: s for s in ordered_seats}
        for sid in used_seats:
            if sid in seat_map:
                rid = seat_map[sid].exam_room_id
                room_used[rid] = room_used.get(rid, 0) + 1

        avail_seats = [s for s in ordered_seats if s.id not in used_seats]
        seat_idx = 0
        for p in ordered_parts:
            if p.id in assignments:
                continue
            while seat_idx < len(avail_seats):
                cand = avail_seats[seat_idx]
                seat_idx += 1
                if room_used.get(cand.exam_room_id, 0) >= room_caps.get(
                    cand.exam_room_id, 0
                ):
                    continue
                if (
                    policy.require_accessible
                    and p.needs_accessible
                    and not cand.accessible
                ):
                    continue
                assignments[p.id] = cand.id
                room_used[cand.exam_room_id] = room_used.get(cand.exam_room_id, 0) + 1
                break
        return {
            "status": "FEASIBLE",
            "assignments": assignments,
            "diagnostics": {"capacity_shortfall": 0},
        }

    model = cp_model.CpModel()
    x: dict[tuple[str, str], cp_model.IntVar] = {}

    for p in participants:
        p_vars: list[cp_model.IntVar] = []
        locked_sid = locked_assignments.get(p.id) if policy.respect_locks else None
        for s in enabled_seats:
            if locked_sid is not None and s.id != locked_sid:
                continue
            if policy.require_accessible and p.needs_accessible and not s.accessible:
                continue
            var = model.new_bool_var(f"x_{p.id}_{s.id}")
            x[(p.id, s.id)] = var
            p_vars.append(var)
        if not p_vars:
            return {
                "status": "INFEASIBLE",
                "assignments": {},
                "diagnostics": {
                    "capacity_shortfall": 0,
                    "reason": (
                        f"Tidak ada kursi layak untuk {p.display_name} "
                        "(periksa kebutuhan kursi aksesibel atau kunci)."
                    ),
                },
            }
        model.add(sum(p_vars) == 1)

    for s in enabled_seats:
        s_vars = [x[(p.id, s.id)] for p in participants if (p.id, s.id) in x]
        if s_vars:
            model.add(sum(s_vars) <= 1)

    for rid, cap in room_caps.items():
        r_vars = [
            x[(p.id, s.id)]
            for p in participants
            for s in enabled_seats
            if s.exam_room_id == rid and (p.id, s.id) in x
        ]
        if r_vars:
            model.add(sum(r_vars) <= cap)

    adj_pairs = build_adjacent_seat_pairs(
        enabled_seats, diagonal=policy.diagonal_adjacent
    )
    penalties: list[cp_model.LinearExpr] = []
    part_by_id = {p.id: p for p in participants}

    # Build seat occupancy by grade/class indicators for compact adjacency constraints
    for sa_id, sb_id in adj_pairs:
        for i in range(len(participants)):
            pa = participants[i]
            if (pa.id, sa_id) not in x:
                continue
            for j in range(len(participants)):
                if i == j:
                    continue
                pb = participants[j]
                if (pb.id, sb_id) not in x:
                    continue
                same_grade = bool(pa.level_label and pa.level_label == pb.level_label)
                same_class = bool(pa.class_label and pa.class_label == pb.class_label)
                if (policy.hard_mix_grade and same_grade) or (
                    policy.hard_mix_class and same_class
                ):
                    model.add(x[(pa.id, sa_id)] + x[(pb.id, sb_id)] <= 1)
                else:
                    weight = 0
                    if same_grade:
                        weight += policy.soft_same_grade_weight
                    if same_class:
                        weight += policy.soft_same_class_weight
                    if weight > 0:
                        both = model.new_bool_var(
                            f"adj_{pa.id}_{pb.id}_{sa_id}_{sb_id}"
                        )
                        model.add_bool_and(
                            [x[(pa.id, sa_id)], x[(pb.id, sb_id)]]
                        ).only_enforce_if(both)
                        model.add_bool_or(
                            [x[(pa.id, sa_id)].Not(), x[(pb.id, sb_id)].Not()]
                        ).only_enforce_if(both.Not())
                        penalties.append(weight * both)

    if penalties:
        model.minimize(sum(penalties))

    solver = cp_model.CpSolver()
    solver.parameters.num_workers = 1
    solver.parameters.random_seed = seed
    solver.parameters.max_time_in_seconds = float(time_limit_sec)
    status = solver.solve(model)
    status_name = solver.status_name(status)

    if status_name not in ("OPTIMAL", "FEASIBLE"):
        return {
            "status": status_name,
            "assignments": {},
            "diagnostics": {
                "capacity_shortfall": 0,
                "reason": (
                    f"Solver berhenti dengan status {status_name}; aturan keras "
                    "terlalu ketat untuk kombinasi peserta dan kursi saat ini."
                ),
            },
        }

    result_map: dict[str, str] = {}
    for (pid, sid), var in x.items():
        if solver.value(var) == 1:
            result_map[pid] = sid
    _ = part_by_id
    return {
        "status": status_name,
        "assignments": result_map,
        "diagnostics": {"capacity_shortfall": 0},
    }
