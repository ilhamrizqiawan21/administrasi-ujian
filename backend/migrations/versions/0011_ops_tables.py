"""OPS tables: room session states, attendance, reports, incidents, makeup links.

Revision ID: 0011_ops_tables
Revises: 0010_exp_tables
Create Date: 2026-11-25
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0011_ops_tables"
down_revision = "0010_exp_tables"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "room_session_states",
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
            unique=True,
        ),
        sa.Column(
            "actual_state", sa.Text(), nullable=False, server_default="scheduled"
        ),
        sa.Column("started_at", sa.Text(), nullable=True),
        sa.Column("finished_at", sa.Text(), nullable=True),
        sa.Column("updated_at", sa.Text(), nullable=False),
    )

    op.create_table(
        "participant_attendance",
        sa.Column("id", sa.Text(), primary_key=True),
        sa.Column(
            "exam_id",
            sa.Text(),
            sa.ForeignKey("exams.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "sitting_id",
            sa.Text(),
            sa.ForeignKey("participant_sittings.id", ondelete="CASCADE"),
            nullable=False,
            unique=True,
        ),
        sa.Column("state", sa.Text(), nullable=False, server_default="unrecorded"),
        sa.Column("recorded_at", sa.Text(), nullable=False),
        sa.Column("note", sa.Text(), nullable=False, server_default=""),
        sa.Column("revision", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("updated_at", sa.Text(), nullable=False),
    )

    op.create_table(
        "staff_attendance",
        sa.Column("id", sa.Text(), primary_key=True),
        sa.Column(
            "exam_id",
            sa.Text(),
            sa.ForeignKey("exams.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "slot_id",
            sa.Text(),
            sa.ForeignKey("invigilation_slots.id", ondelete="CASCADE"),
            nullable=False,
            unique=True,
        ),
        sa.Column(
            "planned_person_id",
            sa.Text(),
            sa.ForeignKey("exam_people.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "actual_person_id",
            sa.Text(),
            sa.ForeignKey("exam_people.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("state", sa.Text(), nullable=False, server_default="unrecorded"),
        sa.Column("recorded_at", sa.Text(), nullable=False),
        sa.Column("approved_by", sa.Text(), nullable=False, server_default=""),
        sa.Column("note", sa.Text(), nullable=False, server_default=""),
        sa.Column("revision", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("updated_at", sa.Text(), nullable=False),
    )

    op.create_table(
        "committee_attendance",
        sa.Column("id", sa.Text(), primary_key=True),
        sa.Column(
            "exam_id",
            sa.Text(),
            sa.ForeignKey("exams.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("att_date", sa.Text(), nullable=False),
        sa.Column("shift", sa.Text(), nullable=False),
        sa.Column(
            "exam_person_id",
            sa.Text(),
            sa.ForeignKey("exam_people.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("state", sa.Text(), nullable=False, server_default="present"),
        sa.Column("note", sa.Text(), nullable=False, server_default=""),
        sa.Column("recorded_at", sa.Text(), nullable=False),
        sa.Column("updated_at", sa.Text(), nullable=False),
        sa.UniqueConstraint(
            "exam_id",
            "att_date",
            "shift",
            "exam_person_id",
            name="uq_com_att_day_shift",
        ),
    )

    op.create_table(
        "session_reports",
        sa.Column("id", sa.Text(), primary_key=True),
        sa.Column(
            "exam_id",
            sa.Text(),
            sa.ForeignKey("exams.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "room_session_id",
            sa.Text(),
            sa.ForeignKey("room_sessions.id", ondelete="CASCADE"),
            nullable=False,
            unique=True,
        ),
        sa.Column("remarks", sa.Text(), nullable=False, server_default=""),
        sa.Column(
            "signer_snapshot_json", sa.Text(), nullable=False, server_default="{}"
        ),
        sa.Column(
            "counts_snapshot_json", sa.Text(), nullable=False, server_default="{}"
        ),
        sa.Column("finalized_at", sa.Text(), nullable=True),
        sa.Column("revision", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("updated_at", sa.Text(), nullable=False),
    )

    op.create_table(
        "incidents",
        sa.Column("id", sa.Text(), primary_key=True),
        sa.Column(
            "exam_id",
            sa.Text(),
            sa.ForeignKey("exams.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "room_session_id",
            sa.Text(),
            sa.ForeignKey("room_sessions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("type_code", sa.Text(), nullable=False),
        sa.Column("severity", sa.Text(), nullable=False, server_default="low"),
        sa.Column(
            "participant_id",
            sa.Text(),
            sa.ForeignKey("exam_participants.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("note", sa.Text(), nullable=False),
        sa.Column("resolution", sa.Text(), nullable=False, server_default=""),
        sa.Column("confidential", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("recorded_at", sa.Text(), nullable=False),
        sa.Column("created_at", sa.Text(), nullable=False),
    )

    op.create_table(
        "makeup_links",
        sa.Column("id", sa.Text(), primary_key=True),
        sa.Column(
            "exam_id",
            sa.Text(),
            sa.ForeignKey("exams.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "original_sitting_id",
            sa.Text(),
            sa.ForeignKey("participant_sittings.id", ondelete="CASCADE"),
            nullable=False,
            unique=True,
        ),
        sa.Column(
            "makeup_sitting_id",
            sa.Text(),
            sa.ForeignKey("participant_sittings.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "target_room_session_id",
            sa.Text(),
            sa.ForeignKey("room_sessions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("reason", sa.Text(), nullable=False, server_default=""),
        sa.Column("created_at", sa.Text(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("makeup_links")
    op.drop_table("incidents")
    op.drop_table("session_reports")
    op.drop_table("committee_attendance")
    op.drop_table("staff_attendance")
    op.drop_table("participant_attendance")
    op.drop_table("room_session_states")
