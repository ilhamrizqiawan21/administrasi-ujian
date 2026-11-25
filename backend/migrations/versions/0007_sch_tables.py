"""SCH tables: staff availability, profiles, invigilation slots, assignments, reserves.

Revision ID: 0007_sch_tables
Revises: 0006_rom_tables
Create Date: 2026-11-25
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0007_sch_tables"
down_revision = "0006_rom_tables"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "staff_availability",
        sa.Column("id", sa.Text(), primary_key=True),
        sa.Column(
            "exam_id",
            sa.Text(),
            sa.ForeignKey("exams.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "exam_person_id",
            sa.Text(),
            sa.ForeignKey("exam_people.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("starts_at", sa.Text(), nullable=False),
        sa.Column("ends_at", sa.Text(), nullable=False),
        sa.Column("state", sa.Text(), nullable=False, server_default="unavailable"),
        sa.Column("reason", sa.Text(), nullable=False, server_default=""),
        sa.Column("revision", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("created_at", sa.Text(), nullable=False),
        sa.Column("updated_at", sa.Text(), nullable=False),
    )
    op.create_index(
        "ix_staff_avail_exam_person",
        "staff_availability",
        ["exam_id", "exam_person_id"],
    )

    op.create_table(
        "staff_profiles",
        sa.Column("id", sa.Text(), primary_key=True),
        sa.Column(
            "exam_id",
            sa.Text(),
            sa.ForeignKey("exams.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "exam_person_id",
            sa.Text(),
            sa.ForeignKey("exam_people.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("max_daily", sa.Integer(), nullable=True),
        sa.Column("max_total", sa.Integer(), nullable=True),
        sa.Column(
            "target_weight_pct", sa.Integer(), nullable=False, server_default="100"
        ),
        sa.Column(
            "role_skills_json",
            sa.Text(),
            nullable=False,
            server_default='["primary","secondary"]',
        ),
        sa.Column("revision", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("created_at", sa.Text(), nullable=False),
        sa.Column("updated_at", sa.Text(), nullable=False),
        sa.UniqueConstraint(
            "exam_id", "exam_person_id", name="uq_staff_profile_exam_person"
        ),
    )

    op.create_table(
        "invigilation_slots",
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
        sa.Column("role_code", sa.Text(), nullable=False),
        sa.Column("slot_index", sa.Integer(), nullable=False),
        sa.Column("revision", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("created_at", sa.Text(), nullable=False),
        sa.Column("updated_at", sa.Text(), nullable=False),
        sa.UniqueConstraint(
            "room_session_id", "role_code", "slot_index", name="uq_inv_slot_rs_role_idx"
        ),
    )
    op.create_index("ix_inv_slots_plan", "invigilation_slots", ["plan_id"])

    op.create_table(
        "invigilations",
        sa.Column("id", sa.Text(), primary_key=True),
        sa.Column(
            "plan_id",
            sa.Text(),
            sa.ForeignKey("plans.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "slot_id",
            sa.Text(),
            sa.ForeignKey("invigilation_slots.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "exam_person_id",
            sa.Text(),
            sa.ForeignKey("exam_people.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("locked", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("revision", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("created_at", sa.Text(), nullable=False),
        sa.Column("updated_at", sa.Text(), nullable=False),
        sa.UniqueConstraint("plan_id", "slot_id", name="uq_inv_plan_slot"),
    )
    op.create_index("ix_invigilations_plan", "invigilations", ["plan_id"])

    op.create_table(
        "invigilation_reserves",
        sa.Column("id", sa.Text(), primary_key=True),
        sa.Column(
            "plan_id",
            sa.Text(),
            sa.ForeignKey("plans.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "session_id",
            sa.Text(),
            sa.ForeignKey("sessions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "exam_person_id",
            sa.Text(),
            sa.ForeignKey("exam_people.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("locked", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("revision", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("created_at", sa.Text(), nullable=False),
        sa.Column("updated_at", sa.Text(), nullable=False),
        sa.UniqueConstraint(
            "plan_id", "session_id", "exam_person_id", name="uq_inv_res_plan_sess_pers"
        ),
    )

    op.create_table(
        "solver_runs",
        sa.Column("id", sa.Text(), primary_key=True),
        sa.Column(
            "exam_id",
            sa.Text(),
            sa.ForeignKey("exams.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "plan_id",
            sa.Text(),
            sa.ForeignKey("plans.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("kind", sa.Text(), nullable=False),
        sa.Column("input_hash", sa.Text(), nullable=False),
        sa.Column("seed", sa.Integer(), nullable=False),
        sa.Column("solver_version", sa.Text(), nullable=False),
        sa.Column("weights_json", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("status", sa.Text(), nullable=False),
        sa.Column("score", sa.Integer(), nullable=True),
        sa.Column("diagnostics_json", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("created_at", sa.Text(), nullable=False),
    )
    op.create_index("ix_solver_runs_plan", "solver_runs", ["plan_id"])


def downgrade() -> None:
    op.drop_table("solver_runs")
    op.drop_table("invigilation_reserves")
    op.drop_table("invigilations")
    op.drop_table("invigilation_slots")
    op.drop_table("staff_profiles")
    op.drop_table("staff_availability")
