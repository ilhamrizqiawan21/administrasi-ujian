"""Independent timetable validator for SES-05."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any


@dataclass(frozen=True)
class SessionInfo:
    id: str
    label: str
    local_date: str
    start_local: str
    end_local: str
    starts_at: datetime
    ends_at: datetime
    mode: str

    @property
    def duration_min(self) -> int:
        return int((self.ends_at - self.starts_at).total_seconds() // 60)


@dataclass(frozen=True)
class RoomInfo:
    id: str
    code: str
    mode: str
    capacity_limit: int


@dataclass(frozen=True)
class RequirementInfo:
    id: str
    group_id: str
    group_label: str
    subject_id: str
    subject_code: str
    duration_min: int
    mode: str
    participant_ids: frozenset[str]


@dataclass(frozen=True)
class PaperAssignmentInfo:
    paper_id: str
    room_session_id: str
    session_id: str
    exam_room_id: str
    requirement_id: str
    group_id: str
    locked: bool


def intervals_overlap(
    a_start: datetime, a_end: datetime, b_start: datetime, b_end: datetime
) -> bool:
    """Return True if half-open intervals [a_start, a_end) and [b_start, b_end) hit."""
    return a_start < b_end and b_start < a_end


def mode_compatible(room_mode: str, req_mode: str) -> bool:
    if room_mode == "hybrid":
        return req_mode in ("paper", "cbt", "hybrid")
    return room_mode == req_mode


def validate_plan_schedule(
    *,
    sessions: dict[str, SessionInfo],
    rooms: dict[str, RoomInfo],
    requirements: dict[str, RequirementInfo],
    papers: list[PaperAssignmentInfo],
    holidays: set[str],
    break_windows: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Independently check all hard schedule invariants; return detailed conflicts."""
    conflicts: list[dict[str, Any]] = []

    for ses in sessions.values():
        if ses.local_date in holidays:
            conflicts.append(
                {
                    "code": "SESSION_ON_HOLIDAY",
                    "message": (
                        f"Sesi '{ses.label}' jatuh pada hari libur ({ses.local_date})."
                    ),
                    "conflicting_ids": [ses.id],
                    "resolution_path": (
                        "Pindahkan tanggal sesi atau hapus tanggal dari daftar libur."
                    ),
                }
            )
        for bw in break_windows:
            bw_date = bw.get("local_date")
            if bw_date and bw_date != ses.local_date:
                continue
            bw_start = str(bw["start_local"])
            bw_end = str(bw["end_local"])
            if ses.start_local < bw_end and bw_start < ses.end_local:
                conflicts.append(
                    {
                        "code": "SESSION_BREAK_OVERLAP",
                        "message": (
                            f"Sesi '{ses.label}' bertabrakan dengan jam istirahat "
                            f"({bw_start}–{bw_end})."
                        ),
                        "conflicting_ids": [ses.id],
                        "resolution_path": (
                            "Ubah jam sesi agar tidak memotong jam istirahat."
                        ),
                    }
                )

    papers_by_req: dict[str, list[PaperAssignmentInfo]] = {}
    for p in papers:
        papers_by_req.setdefault(p.requirement_id, []).append(p)

    for req_id, req in requirements.items():
        assigned = papers_by_req.get(req_id, [])
        if len(assigned) == 0:
            conflicts.append(
                {
                    "code": "UNASSIGNED_PAPER",
                    "message": (
                        f"Mapel {req.subject_code} untuk {req.group_label} "
                        "belum dijadwalkan."
                    ),
                    "conflicting_ids": [req_id, req.group_id],
                    "resolution_path": (
                        "Tempatkan mapel ke sesi dan ruang pada kisi jadwal."
                    ),
                }
            )
        elif len(assigned) > 1:
            conflicts.append(
                {
                    "code": "DUPLICATE_PAPER",
                    "message": (
                        f"Mapel {req.subject_code} untuk {req.group_label} "
                        "terjadwal lebih dari sekali."
                    ),
                    "conflicting_ids": [req_id] + [a.paper_id for a in assigned],
                    "resolution_path": "Hapus penempatan ganda pada kisi jadwal.",
                }
            )

    rs_participants: dict[str, set[str]] = {}
    rs_room_id: dict[str, str] = {}
    rs_session_id: dict[str, str] = {}
    rs_reqs: dict[str, list[str]] = {}

    for p in papers:
        paper_ses = sessions.get(p.session_id)
        paper_room = rooms.get(p.exam_room_id)
        paper_req = requirements.get(p.requirement_id)
        if paper_ses is None or paper_room is None or paper_req is None:
            conflicts.append(
                {
                    "code": "BROKEN_REFERENCE",
                    "message": (
                        "Penempatan merujuk sesi, ruang, atau kebutuhan tidak valid."
                    ),
                    "conflicting_ids": [p.paper_id],
                    "resolution_path": "Hapus penempatan rusak.",
                }
            )
            continue

        if paper_ses.duration_min < paper_req.duration_min:
            conflicts.append(
                {
                    "code": "DURATION_TOO_SHORT",
                    "message": (
                        f"Durasi sesi '{paper_ses.label}' "
                        f"({paper_ses.duration_min} mnt) "
                        f"kurang dari {paper_req.subject_code} "
                        f"({paper_req.duration_min} mnt)."
                    ),
                    "conflicting_ids": [paper_ses.id, paper_req.id],
                    "resolution_path": "Perpanjang durasi sesi atau pindah sesi.",
                }
            )

        if not mode_compatible(paper_room.mode, paper_req.mode):
            conflicts.append(
                {
                    "code": "ROOM_MODE_MISMATCH",
                    "message": (
                        f"Mode ruang {paper_room.code} ({paper_room.mode}) "
                        f"tidak cocok dengan "
                        f"{paper_req.subject_code} ({paper_req.mode})."
                    ),
                    "conflicting_ids": [paper_room.id, paper_req.id],
                    "resolution_path": "Pilih ruang dengan mode sesuai atau hybrid.",
                }
            )

        rs_participants.setdefault(p.room_session_id, set()).update(
            paper_req.participant_ids
        )
        rs_room_id[p.room_session_id] = paper_room.id
        rs_session_id[p.room_session_id] = paper_ses.id
        rs_reqs.setdefault(p.room_session_id, []).append(paper_req.id)

    for rs_id, pids in rs_participants.items():
        room = rooms[rs_room_id[rs_id]]
        if len(pids) > room.capacity_limit:
            conflicts.append(
                {
                    "code": "ROOM_CAPACITY_EXCEEDED",
                    "message": (
                        f"Ruang {room.code} terisi {len(pids)} peserta, "
                        f"melebihi kapasitas ({room.capacity_limit})."
                    ),
                    "conflicting_ids": [room.id, rs_id] + rs_reqs[rs_id],
                    "resolution_path": "Pindahkan sebagian kelompok ke ruang lain.",
                }
            )

    rs_ids = sorted(rs_room_id.keys())
    for idx_a in range(len(rs_ids)):
        rs_a = rs_ids[idx_a]
        ses_a = sessions[rs_session_id[rs_a]]
        for idx_b in range(idx_a + 1, len(rs_ids)):
            rs_b = rs_ids[idx_b]
            ses_b = sessions[rs_session_id[rs_b]]
            if not intervals_overlap(
                ses_a.starts_at, ses_a.ends_at, ses_b.starts_at, ses_b.ends_at
            ):
                continue

            if rs_room_id[rs_a] == rs_room_id[rs_b]:
                room = rooms[rs_room_id[rs_a]]
                conflicts.append(
                    {
                        "code": "ROOM_INTERVAL_OVERLAP",
                        "message": (
                            f"Ruang {room.code} dipakai ganda pada sesi bertabrakan "
                            f"('{ses_a.label}' dan '{ses_b.label}')."
                        ),
                        "conflicting_ids": [room.id, ses_a.id, ses_b.id],
                        "resolution_path": "Pindahkan ujian ke ruang atau waktu lain.",
                    }
                )

            shared_participants = rs_participants[rs_a] & rs_participants[rs_b]
            if shared_participants:
                conflicts.append(
                    {
                        "code": "PARTICIPANT_INTERVAL_OVERLAP",
                        "message": (
                            f"{len(shared_participants)} peserta bentrok pada sesi "
                            f"bertabrakan ('{ses_a.label}' dan '{ses_b.label}')."
                        ),
                        "conflicting_ids": sorted(shared_participants)[:10]
                        + [ses_a.id, ses_b.id],
                        "resolution_path": (
                            "Geser jadwal kelompok ke sesi tidak bertabrakan."
                        ),
                    }
                )

    return conflicts
