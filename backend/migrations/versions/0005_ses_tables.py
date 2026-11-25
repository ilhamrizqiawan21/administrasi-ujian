"""SES tables: plans, sessions, room_sessions, room_papers.

Revision ID: 0005_ses_tables
Revises: 0004_evt_tables
Create Date: 2026-11-25
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0005_ses_tables"
down_revision = "0004_evt_tables"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "plans",
        sa.Column("id", sa.Text(), primary_key=True),
        sa.Column(
            "exam_id",
            sa.Text(),
            sa.ForeignKey("exams.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("state", sa.Text(), nullable=False, server_default="draft"),
        sa.Column("parent_id", sa.Text(), nullable=True),
        sa.Column("input_hash", sa.Text(), nullable=False),
        sa.Column("rules_json", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("published_at", sa.Text(), nullable=True),
        sa.Column("revision", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("created_at", sa.Text(), nullable=False),
        sa.Column("updated_at", sa.Text(), nullable=False),
        sa.UniqueConstraint("exam_id", "version", name="uq_plan_exam_ver"),
    )

    op.create_table(
        "sessions",
        sa.Column("id", sa.Text(), primary_key=True),
        sa.Column(
            "plan_id",
            sa.Text(),
            sa.ForeignKey("plans.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("label", sa.Text(), nullable=False),
        sa.Column("local_date", sa.Text(), nullable=False),
        sa.Column("starts_at", sa.Text(), nullable=False),
        sa.Column("ends_at", sa.Text(), nullable=False),
        sa.Column("start_local", sa.Text(), nullable=False),
        sa.Column("end_local", sa.Text(), nullable=False),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("mode", sa.Text(), nullable=False, server_default="paper"),
        sa.Column("revision", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("created_at", sa.Text(), nullable=False),
        sa.Column("updated_at", sa.Text(), nullable=False),
    )

    op.create_table(
        "room_sessions",
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
            "exam_room_id",
            sa.Text(),
            sa.ForeignKey("exam_rooms.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "required_staff_count", sa.Integer(), nullable=False, server_default="1"
        ),
        sa.Column("revision", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("created_at", sa.Text(), nullable=False),
        sa.Column("updated_at", sa.Text(), nullable=False),
        sa.UniqueConstraint(
            "plan_id", "session_id", "exam_room_id", name="uq_room_session"
        ),
    )

    op.create_table(
        "room_papers",
        sa.Column("id", sa.Text(), primary_key=True),
        sa.Column(
            "room_session_id",
            sa.Text(),
            sa.ForeignKey("room_sessions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "requirement_id",
            sa.Text(),
            sa.ForeignKey("exam_requirements.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "group_id",
            sa.Text(),
            sa.ForeignKey("exam_groups.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("locked", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("revision", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("created_at", sa.Text(), nullable=False),
        sa.Column("updated_at", sa.Text(), nullable=False),
        sa.UniqueConstraint(
            "room_session_id", "requirement_id", name="uq_room_paper_req"
        ),
    )


def downgrade() -> None:
    op.drop_table("room_papers")
    op.drop_table("room_sessions")
    op.drop_table("sessions")
    op.drop_table("plans")
