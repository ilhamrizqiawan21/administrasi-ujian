"""Independent seating validator and adjacency diagnostics (ROM-03, ROM-05)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class SeatCandidate:
    id: str
    exam_room_id: str
    room_code: str
    seat_code: str
    desk_row: int
    desk_col: int
    seat_index: int
    enabled: bool
    accessible: bool


@dataclass(frozen=True)
class ParticipantCandidate:
    id: str
    code: str
    display_name: str
    participant_number: str | None
    level_label: str
    class_label: str
    needs_accessible: bool


def build_adjacent_seat_pairs(
    seats: list[SeatCandidate], *, diagonal: bool = False
) -> list[tuple[str, str]]:
    """Build undirected adjacent seat pairs within each room."""
    by_room: dict[str, list[SeatCandidate]] = {}
    for s in seats:
        if s.enabled:
            by_room.setdefault(s.exam_room_id, []).append(s)

    pairs: list[tuple[str, str]] = []
    for room_seats in by_room.values():
        for i in range(len(room_seats)):
            sa = room_seats[i]
            for j in range(i + 1, len(room_seats)):
                sb = room_seats[j]
                dr = abs(sa.desk_row - sb.desk_row)
                dc = abs(sa.desk_col - sb.desk_col)
                same_desk = dr == 0 and dc == 0
                ortho = (dr == 1 and dc == 0) or (dr == 0 and dc == 1)
                diag = diagonal and dr == 1 and dc == 1
                if same_desk or ortho or diag:
                    pairs.append((sa.id, sb.id))
    return pairs


def validate_seating_allocation(
    *,
    participants: dict[str, ParticipantCandidate],
    seats: dict[str, SeatCandidate],
    room_caps: dict[str, int],
    assignments: dict[str, str],  # participant_id -> seat_id
    hard_mix_grade: bool = False,
    hard_mix_class: bool = False,
    require_accessible: bool = True,
    diagonal_adjacent: bool = False,
) -> dict[str, Any]:
    """Independently check all seating invariants and soft violations."""
    hard_conflicts: list[dict[str, Any]] = []
    same_grade_adjacent = 0
    same_class_adjacent = 0
    accommodation_conflicts = 0

    seat_to_part: dict[str, str] = {}
    room_occupancy: dict[str, int] = {}

    for pid in participants:
        if pid not in assignments:
            hard_conflicts.append(
                {
                    "code": "UNSEATED_PARTICIPANT",
                    "message": (
                        f"Peserta {participants[pid].display_name} belum dapat kursi."
                    ),
                    "conflicting_ids": [pid],
                }
            )

    for pid, sid in assignments.items():
        part = participants.get(pid)
        seat = seats.get(sid)
        if part is None or seat is None:
            hard_conflicts.append(
                {
                    "code": "INVALID_CANDIDATE",
                    "message": "Penempatan merujuk peserta atau kursi tidak valid.",
                    "conflicting_ids": [pid, sid],
                }
            )
            continue

        if not seat.enabled:
            hard_conflicts.append(
                {
                    "code": "DISABLED_SEAT_USED",
                    "message": (
                        f"Kursi nonaktif {seat.seat_code} tidak boleh ditempati."
                    ),
                    "conflicting_ids": [sid, pid],
                }
            )

        if sid in seat_to_part:
            hard_conflicts.append(
                {
                    "code": "SEAT_DOUBLE_OCCUPANCY",
                    "message": (
                        f"Kursi {seat.seat_code} ditempati lebih dari satu peserta."
                    ),
                    "conflicting_ids": [sid, pid, seat_to_part[sid]],
                }
            )
        seat_to_part[sid] = pid
        room_occupancy[seat.exam_room_id] = room_occupancy.get(seat.exam_room_id, 0) + 1

        if require_accessible and part.needs_accessible and not seat.accessible:
            accommodation_conflicts += 1
            hard_conflicts.append(
                {
                    "code": "ACCESSIBLE_SEAT_REQUIRED",
                    "message": (
                        f"Peserta {part.display_name} membutuhkan kursi aksesibel."
                    ),
                    "conflicting_ids": [pid, sid],
                }
            )

    for room_id, occ in room_occupancy.items():
        cap = room_caps.get(room_id, 0)
        if occ > cap:
            hard_conflicts.append(
                {
                    "code": "ROOM_CAPACITY_EXCEEDED",
                    "message": (
                        f"Okupansi ruang ({occ}) melebihi batas kapasitas ({cap})."
                    ),
                    "conflicting_ids": [room_id],
                }
            )

    adj_pairs = build_adjacent_seat_pairs(
        list(seats.values()), diagonal=diagonal_adjacent
    )
    for sa_id, sb_id in adj_pairs:
        pa_id = seat_to_part.get(sa_id)
        pb_id = seat_to_part.get(sb_id)
        if not pa_id or not pb_id:
            continue
        pa = participants[pa_id]
        pb = participants[pb_id]
        if pa.level_label and pa.level_label == pb.level_label:
            same_grade_adjacent += 1
            if hard_mix_grade:
                hard_conflicts.append(
                    {
                        "code": "SAME_GRADE_ADJACENT",
                        "message": (
                            f"Tingkat sama ({pa.level_label}) bersebelahan di "
                            f"{seats[sa_id].seat_code} dan {seats[sb_id].seat_code}."
                        ),
                        "conflicting_ids": [pa_id, pb_id, sa_id, sb_id],
                    }
                )
        if pa.class_label and pa.class_label == pb.class_label:
            same_class_adjacent += 1
            if hard_mix_class:
                hard_conflicts.append(
                    {
                        "code": "SAME_CLASS_ADJACENT",
                        "message": (
                            f"Rombel sama ({pa.class_label}) bersebelahan di "
                            f"{seats[sa_id].seat_code} dan {seats[sb_id].seat_code}."
                        ),
                        "conflicting_ids": [pa_id, pb_id, sa_id, sb_id],
                    }
                )

    total_cap = sum(
        min(
            room_caps.get(rid, 0),
            sum(1 for s in seats.values() if s.exam_room_id == rid and s.enabled),
        )
        for rid in room_caps
    )
    shortfall = max(0, len(participants) - total_cap)

    return {
        "valid": len(hard_conflicts) == 0,
        "hard_conflicts": hard_conflicts,
        "diagnostics": {
            "capacity_shortfall": shortfall,
            "same_grade_adjacent": same_grade_adjacent,
            "same_class_adjacent": same_class_adjacent,
            "accommodation_conflicts": accommodation_conflicts,
            "total_seated": len(assignments),
            "total_eligible": len(participants),
        },
    }
