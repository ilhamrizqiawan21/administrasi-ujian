"""Unit tests for OPS-01..OPS-08 (derived attendance counts)."""

from __future__ import annotations

from backend.modules.ops.service import derive_attendance_counts


def test_derive_attendance_counts_keeps_unrecorded_distinct_from_absent() -> None:
    counts = derive_attendance_counts(
        ["present", "present", "absent", "sick", "unrecorded"]
    )
    assert counts["total"] == 5
    assert counts["present"] == 2
    assert counts["absent"] == 1
    assert counts["sick"] == 1
    assert counts["unrecorded"] == 1
