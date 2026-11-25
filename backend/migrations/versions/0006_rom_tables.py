"""ROM tables: seats, plan_seat_assignments, participant_sittings.

Revision ID: 0006_rom_tables
Revises: 0005_ses_tables
Create Date: 2026-11-25
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0006_rom_tables"
down_revision = "0005_ses_tables"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "seats",
        sa.Column("id", sa.Text(), primary_key=True),
        sa.Column(
            "plan_id",
            sa.Text(),
            sa.ForeignKey("plans.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "exam_room_id",
            sa.Text(),
            sa.ForeignKey("exam_rooms.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("seat_code", sa.Text(), nullable=False),
        sa.Column("desk_row", sa.Integer(), nullable=False),
        sa.Column("desk_col", sa.Integer(), nullable=False),
        sa.Column("seat_index", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("enabled", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("accessible", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("revision", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("created_at", sa.Text(), nullable=False),
        sa.Column("updated_at", sa.Text(), nullable=False),
        sa.UniqueConstraint(
            "plan_id", "exam_room_id", "seat_code", name="uq_seat_code"
        ),
    )

    op.create_table(
        "plan_seat_assignments",
        sa.Column("id", sa.Text(), primary_key=True),
        sa.Column(
            "plan_id",
            sa.Text(),
            sa.ForeignKey("plans.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "participant_id",
            sa.Text(),
            sa.ForeignKey("exam_participants.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "exam_room_id",
            sa.Text(),
            sa.ForeignKey("exam_rooms.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "seat_id",
            sa.Text(),
            sa.ForeignKey("seats.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("locked", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("revision", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("created_at", sa.Text(), nullable=False),
        sa.Column("updated_at", sa.Text(), nullable=False),
        sa.UniqueConstraint("plan_id", "participant_id", name="uq_plan_seat_part"),
        sa.UniqueConstraint("plan_id", "seat_id", name="uq_plan_seat_occ"),
    )

    op.create_table(
        "participant_sittings",
        sa.Column("id", sa.Text(), primary_key=True),
        sa.Column(
            "plan_id",
            sa.Text(),
            sa.ForeignKey("plans.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "room_session_id",
            sa.Text(),
            sa.ForeignKey("room_sessions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "participant_id",
            sa.Text(),
            sa.ForeignKey("exam_participants.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "requirement_id",
            sa.Text(),
            sa.ForeignKey("exam_requirements.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "seat_id",
            sa.Text(),
            sa.ForeignKey("seats.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("locked", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("revision", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("created_at", sa.Text(), nullable=False),
        sa.Column("updated_at", sa.Text(), nullable=False),
        sa.UniqueConstraint(
            "plan_id", "participant_id", "requirement_id", name="uq_sitting_part_req"
        ),
        sa.UniqueConstraint("room_session_id", "seat_id", name="uq_sitting_rs_seat"),
    )


def downgrade() -> None:
    op.drop_table("participant_sittings")
    op.drop_table("plan_seat_assignments")
    op.drop_table("seats")
