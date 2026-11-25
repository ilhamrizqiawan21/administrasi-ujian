"""OR-Tools CP-SAT invigilation scheduling solver (SCH-03..SCH-05)."""

from __future__ import annotations

from typing import Any

from ortools.sat.python import cp_model

from backend.modules.sch.schemas import InvigilationRules
from backend.modules.sch.validator import (
    SlotCandidate,
    StaffCandidate,
    intervals_overlap,
)


def solve_invigilation(
    *,
    staff: list[StaffCandidate],
    slots: list[SlotCandidate],
    locked_assignments: dict[str, str],  # slot_id -> exam_person_id
    rules: InvigilationRules,
    time_limit_sec: int = 60,
    seed: int = 42,
) -> dict[str, Any]:
    """Solve invigilation assignment using CP-SAT without relaxing hard rules."""
    if not slots:
        return {
            "status": "OPTIMAL",
            "assignments": {},
            "objective": 0,
            "diagnostics": {"reason": ""},
        }
    if not staff:
        return {
            "status": "INFEASIBLE",
            "assignments": {},
            "objective": None,
            "diagnostics": {
                "reason": "Tidak ada staf pengawas yang tersedia pada kegiatan ini."
            },
        }

    # Preflight: check each slot has at least one eligible candidate
    eligible_map: dict[str, list[int]] = {}
    for s in slots:
        cands: list[int] = []
        for t_idx, person in enumerate(staff):
            if s.role_code not in person.role_skills:
                continue
            if any(
                intervals_overlap(s.starts_at, s.ends_at, u_s, u_e)
                for u_s, u_e in person.unavailable_intervals
            ):
                continue
            if rules.hard_avoid_own_class and (person.taught_classes & s.class_labels):
                continue
            if rules.hard_avoid_own_subject and (
                person.taught_subjects & s.subject_codes
            ):
                continue
            cands.append(t_idx)
        if not cands:
            return {
                "status": "INFEASIBLE",
                "assignments": {},
                "objective": None,
                "diagnostics": {
                    "reason": (
                        f"Slot {s.room_code} {s.session_label} ({s.role_code}) "
                        "tidak memiliki kandidat pengawas yang memenuhi syarat."
                    )
                },
            }
        eligible_map[s.id] = cands

    model = cp_model.CpModel()
    x: dict[tuple[int, int], cp_model.IntVar] = {}
    for s_idx, s in enumerate(slots):
        for t_idx in eligible_map[s.id]:
            x[(t_idx, s_idx)] = model.new_bool_var(f"x_{t_idx}_{s_idx}")

    # 1. Each slot assigned exactly once
    for s_idx, s in enumerate(slots):
        model.add(sum(x[(t_idx, s_idx)] for t_idx in eligible_map[s.id]) == 1)

    # 2. Respect fixed locks
    staff_idx_by_id = {p.id: idx for idx, p in enumerate(staff)}
    if rules.respect_locks:
        for s_idx, s in enumerate(slots):
            locked_pid = locked_assignments.get(s.id)
            if locked_pid is None:
                continue
            locked_t_idx = staff_idx_by_id.get(locked_pid)
            if locked_t_idx is None or (locked_t_idx, s_idx) not in x:
                return {
                    "status": "INFEASIBLE",
                    "assignments": {},
                    "objective": None,
                    "diagnostics": {
                        "reason": (
                            f"Kunci slot {s.room_code} {s.session_label} "
                            "melanggar aturan keras atau ketersediaan."
                        )
                    },
                }
            model.add(x[(locked_t_idx, s_idx)] == 1)

    # 3. Non-overlapping intervals per staff (across all session IDs)
    for t_idx in range(len(staff)):
        for i in range(len(slots)):
            if (t_idx, i) not in x:
                continue
            for j in range(i + 1, len(slots)):
                if (t_idx, j) not in x:
                    continue
                if intervals_overlap(
                    slots[i].starts_at,
                    slots[i].ends_at,
                    slots[j].starts_at,
                    slots[j].ends_at,
                ):
                    model.add(x[(t_idx, i)] + x[(t_idx, j)] <= 1)

    # 4. Daily & total limits (hard if configured)
    dates = sorted({s.local_date for s in slots})
    for t_idx, person in enumerate(staff):
        if rules.hard_max_total and person.max_total is not None:
            vars_all = [
                x[(t_idx, s_idx)] for s_idx in range(len(slots)) if (t_idx, s_idx) in x
            ]
            if vars_all:
                model.add(sum(vars_all) <= person.max_total)

        if rules.hard_max_daily and person.max_daily is not None:
            for dt in dates:
                vars_day = [
                    x[(t_idx, s_idx)]
                    for s_idx, s in enumerate(slots)
                    if s.local_date == dt and (t_idx, s_idx) in x
                ]
                if vars_day:
                    model.add(sum(vars_day) <= person.max_daily)

    # 5. Soft objective: weighted load deviation + soft own class/subject
    penalties: list[cp_model.LinearExpr] = []
    total_weight = sum(p.target_weight_pct for p in staff) or 1
    total_slots = len(slots)
    scale = 100

    for t_idx, person in enumerate(staff):
        vars_all = [
            x[(t_idx, s_idx)] for s_idx in range(len(slots)) if (t_idx, s_idx) in x
        ]
        load_var = model.new_int_var(0, total_slots, f"load_{t_idx}")
        model.add(load_var == sum(vars_all))
        target_scaled = round(
            total_slots * person.target_weight_pct * scale / total_weight
        )
        dev_var = model.new_int_var(0, total_slots * scale, f"dev_{t_idx}")
        model.add_abs_equality(dev_var, load_var * scale - target_scaled)
        if rules.weight_load_deviation > 0:
            penalties.append(dev_var * rules.weight_load_deviation)

        for s_idx, s in enumerate(slots):
            if (t_idx, s_idx) not in x:
                continue
            if not rules.hard_avoid_own_class and (
                person.taught_classes & s.class_labels
            ):
                penalties.append(x[(t_idx, s_idx)] * (rules.weight_own_class * scale))
            if not rules.hard_avoid_own_subject and (
                person.taught_subjects & s.subject_codes
            ):
                penalties.append(x[(t_idx, s_idx)] * (rules.weight_own_subject * scale))

    if penalties:
        model.minimize(sum(penalties))

    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = float(time_limit_sec)
    solver.parameters.random_seed = seed
    solver.parameters.num_search_workers = 1

    status_code = solver.solve(model)
    status_name = solver.status_name(status_code)
    if status_code not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        return {
            "status": status_name,
            "assignments": {},
            "objective": None,
            "diagnostics": {
                "reason": (
                    f"Solver berhenti dengan status {status_name}; aturan keras "
                    "atau kapasitas pengawas tidak mencukupi."
                )
            },
        }

    assignments: dict[str, str] = {}
    for s_idx, s in enumerate(slots):
        for t_idx in eligible_map[s.id]:
            if solver.value(x[(t_idx, s_idx)]) == 1:
                assignments[s.id] = staff[t_idx].id
                break

    return {
        "status": status_name,
        "assignments": assignments,
        "objective": int(solver.objective_value) if penalties else 0,
        "diagnostics": {"reason": ""},
    }
