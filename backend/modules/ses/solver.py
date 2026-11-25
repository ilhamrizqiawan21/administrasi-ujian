"""OR-Tools CP-SAT optional timetable auto-generator (SES-07)."""

from __future__ import annotations

from typing import Any

from ortools.sat.python import cp_model

from backend.modules.ses.validator import (
    PaperAssignmentInfo,
    RequirementInfo,
    RoomInfo,
    SessionInfo,
    intervals_overlap,
    mode_compatible,
)


def solve_timetable(
    *,
    sessions: dict[str, SessionInfo],
    rooms: dict[str, RoomInfo],
    requirements: dict[str, RequirementInfo],
    locked_papers: list[PaperAssignmentInfo],
    holidays: set[str],
    break_windows: list[dict[str, Any]],
    time_limit_sec: int = 30,
    seed: int = 42,
) -> dict[str, Any]:
    """Generate feasible timetable draft respecting locks and hard constraints."""
    valid_session_ids: set[str] = set()
    for ses in sessions.values():
        if ses.local_date in holidays:
            continue
        overlaps_break = any(
            (not bw.get("local_date") or bw["local_date"] == ses.local_date)
            and ses.start_local < str(bw["end_local"])
            and str(bw["start_local"]) < ses.end_local
            for bw in break_windows
        )
        if not overlaps_break:
            valid_session_ids.add(ses.id)

    model = cp_model.CpModel()
    locked_by_req = {lp.requirement_id: lp for lp in locked_papers}

    x: dict[tuple[str, str, str], cp_model.IntVar] = {}
    for req_id, req in requirements.items():
        if req_id in locked_by_req:
            lp = locked_by_req[req_id]
            var = model.new_bool_var(f"x_{req_id}_{lp.session_id}_{lp.exam_room_id}")
            model.add(var == 1)
            x[(req_id, lp.session_id, lp.exam_room_id)] = var
            continue

        candidates: list[cp_model.IntVar] = []
        for ses_id in sorted(valid_session_ids):
            ses = sessions[ses_id]
            if ses.duration_min < req.duration_min:
                continue
            for room_id, room in sorted(rooms.items()):
                if not mode_compatible(room.mode, req.mode):
                    continue
                if len(req.participant_ids) > room.capacity_limit:
                    continue
                var = model.new_bool_var(f"x_{req_id}_{ses_id}_{room_id}")
                x[(req_id, ses_id, room_id)] = var
                candidates.append(var)

        if not candidates:
            return {
                "status": "INFEASIBLE",
                "assignments": [],
                "diagnostics": [
                    f"Tidak ada pasangan sesi-ruang yang memenuhi syarat untuk "
                    f"{req.subject_code} ({req.group_label})."
                ],
            }
        model.add(sum(candidates) == 1)

    # Room capacity per (session, room) and no double-booking on overlapping intervals
    session_list = sorted(sessions.values(), key=lambda s: s.starts_at)
    for room_id, room in rooms.items():
        for ses in session_list:
            vars_in_cell = [
                (req_id, var)
                for (req_id, sid, rid), var in x.items()
                if sid == ses.id and rid == room_id
            ]
            if vars_in_cell:
                model.add(
                    sum(
                        len(requirements[req_id].participant_ids) * var
                        for req_id, var in vars_in_cell
                    )
                    <= room.capacity_limit
                )

        for i in range(len(session_list)):
            for j in range(i + 1, len(session_list)):
                sa, sb = session_list[i], session_list[j]
                if not intervals_overlap(
                    sa.starts_at, sa.ends_at, sb.starts_at, sb.ends_at
                ):
                    continue
                vars_a = [
                    var
                    for (_req, sid, rid), var in x.items()
                    if sid == sa.id and rid == room_id
                ]
                vars_b = [
                    var
                    for (_req, sid, rid), var in x.items()
                    if sid == sb.id and rid == room_id
                ]
                if vars_a and vars_b:
                    # Distinct overlapping sessions cannot share the same room
                    used_a = model.new_bool_var(f"rm_{room_id}_{sa.id}_used")
                    used_b = model.new_bool_var(f"rm_{room_id}_{sb.id}_used")
                    model.add_max_equality(used_a, vars_a)
                    model.add_max_equality(used_b, vars_b)
                    model.add(used_a + used_b <= 1)

    # Participant non-overlap across all sessions with overlapping intervals
    all_pids: set[str] = set()
    for req in requirements.values():
        all_pids.update(req.participant_ids)

    for pid in sorted(all_pids):
        for i, sa in enumerate(session_list):
            overlapping_ids = {sa.id}
            for sb in session_list[i + 1 :]:
                if intervals_overlap(
                    sa.starts_at, sa.ends_at, sb.starts_at, sb.ends_at
                ):
                    overlapping_ids.add(sb.id)
            if len(overlapping_ids) == 1:
                vars_for_p = [
                    var
                    for (req_id, sid, _rid), var in x.items()
                    if sid == sa.id and pid in requirements[req_id].participant_ids
                ]
                if len(vars_for_p) > 1:
                    model.add(sum(vars_for_p) <= 1)
            else:
                vars_for_p = [
                    var
                    for (req_id, sid, _rid), var in x.items()
                    if sid in overlapping_ids
                    and pid in requirements[req_id].participant_ids
                ]
                if len(vars_for_p) > 1:
                    model.add(sum(vars_for_p) <= 1)

    solver = cp_model.CpSolver()
    solver.parameters.num_workers = 1
    solver.parameters.random_seed = seed
    solver.parameters.max_time_in_seconds = float(time_limit_sec)
    status = solver.solve(model)
    status_name = solver.status_name(status)

    if status_name not in ("OPTIMAL", "FEASIBLE"):
        return {
            "status": status_name,
            "assignments": [],
            "diagnostics": [
                f"Solver berhenti dengan status {status_name}; "
                "periksa kapasitas atau jumlah sesi."
            ],
        }

    assignments = [
        {"requirement_id": req_id, "session_id": sid, "exam_room_id": rid}
        for (req_id, sid, rid), var in x.items()
        if solver.value(var) == 1
    ]
    return {
        "status": status_name,
        "assignments": assignments,
        "diagnostics": [],
    }
