"""Pydantic schemas for ROM-01..ROM-08."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

MixMode = Literal["mix_grade", "mix_class", "ordered", "custom"]


class AllocationPolicy(BaseModel):
    model_config = ConfigDict(extra="forbid")

    mode: MixMode = "mix_grade"
    hard_mix_grade: bool = False
    hard_mix_class: bool = False
    diagonal_adjacent: bool = False
    balance_rooms: bool = True
    respect_locks: bool = True
    require_accessible: bool = True
    soft_same_grade_weight: int = Field(default=10, ge=0, le=100)
    soft_same_class_weight: int = Field(default=5, ge=0, le=100)


class RoomLayoutUpdatePayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    institution_id: str = Field(min_length=1)
    exam_id: str = Field(min_length=1)
    plan_id: str = Field(min_length=1)
    exam_room_id: str = Field(min_length=1)
    rows: int = Field(ge=1, le=30)
    cols: int = Field(ge=1, le=30)
    seats_per_desk: int = Field(default=1, ge=1, le=2)
    capacity_limit: int = Field(ge=1, le=1000)
    disabled_cells: list[str] = Field(default_factory=list)
    accessible_seats: list[str] = Field(default_factory=list)
    board_position: Literal["top", "bottom"] = "top"

    @model_validator(mode="after")
    def _check_capacity(self) -> RoomLayoutUpdatePayload:
        disabled = set(self.disabled_cells)
        enabled = 0
        for r in range(1, self.rows + 1):
            for c in range(1, self.cols + 1):
                for s in range(1, self.seats_per_desk + 1):
                    if f"R{r}C{c}S{s}" not in disabled and f"R{r}C{c}" not in disabled:
                        enabled += 1
        if self.capacity_limit > enabled:
            raise ValueError(
                f"Kapasitas ({self.capacity_limit}) melebihi kursi aktif ({enabled})."
            )
        return self


class SeatingScopedPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    institution_id: str = Field(min_length=1)
    exam_id: str = Field(min_length=1)
    plan_id: str = Field(min_length=1)


class SeatingSolvePayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    institution_id: str = Field(min_length=1)
    exam_id: str = Field(min_length=1)
    plan_id: str = Field(min_length=1)
    expected_revision: int = Field(ge=1)
    policy: AllocationPolicy = Field(default_factory=AllocationPolicy)
    time_limit_sec: int = Field(default=30, ge=1, le=300)
    seed: int = Field(default=42, ge=0)


class SeatSwapPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    institution_id: str = Field(min_length=1)
    exam_id: str = Field(min_length=1)
    plan_id: str = Field(min_length=1)
    expected_revision: int = Field(ge=1)
    source_seat_id: str = Field(min_length=1)
    target_seat_id: str = Field(min_length=1)
    policy: AllocationPolicy = Field(default_factory=AllocationPolicy)


class SeatLockPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    institution_id: str = Field(min_length=1)
    exam_id: str = Field(min_length=1)
    plan_id: str = Field(min_length=1)
    seat_id: str = Field(min_length=1)
    locked: bool


class SeatingPrintContextPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    institution_id: str = Field(min_length=1)
    exam_id: str = Field(min_length=1)
    plan_id: str = Field(min_length=1)
    exam_room_id: str = Field(min_length=1)
    include_names: bool = True
