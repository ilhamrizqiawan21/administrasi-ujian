"""EXP tables: submission_items, submission_versions, print_quantities, handovers.

Revision ID: 0010_exp_tables
Revises: 0009_tsk_tables
Create Date: 2026-11-25
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0010_exp_tables"
down_revision = "0009_tsk_tables"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "submission_items",
        sa.Column("id", sa.Text(), primary_key=True),
        sa.Column(
            "exam_id",
            sa.Text(),
            sa.ForeignKey("exams.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "requirement_id",
            sa.Text(),
            sa.ForeignKey("exam_requirements.id", ondelete="CASCADE"),
            nullable=True,
        ),
        sa.Column("subject_label", sa.Text(), nullable=False),
        sa.Column("class_label", sa.Text(), nullable=False),
        sa.Column("type_code", sa.Text(), nullable=False),
        sa.Column(
            "owner_id",
            sa.Text(),
            sa.ForeignKey("exam_people.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("due_date", sa.Text(), nullable=False, server_default=""),
        sa.Column("state", sa.Text(), nullable=False, server_default="missing"),
        sa.Column("current_version", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("revision", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("created_at", sa.Text(), nullable=False),
        sa.Column("updated_at", sa.Text(), nullable=False),
        sa.UniqueConstraint(
            "exam_id",
            "subject_label",
            "class_label",
            "type_code",
            name="uq_sub_item_key",
        ),
    )
    op.create_index("ix_sub_items_exam", "submission_items", ["exam_id"])

    op.create_table(
        "submission_versions",
        sa.Column("id", sa.Text(), primary_key=True),
        sa.Column(
            "item_id",
            sa.Text(),
            sa.ForeignKey("submission_items.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("asset_id", sa.Text(), nullable=False, server_default=""),
        sa.Column("received_at", sa.Text(), nullable=False),
        sa.Column(
            "reviewer_id",
            sa.Text(),
            sa.ForeignKey("exam_people.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("state", sa.Text(), nullable=False),
        sa.Column("note", sa.Text(), nullable=False, server_default=""),
        sa.Column("created_at", sa.Text(), nullable=False),
        sa.UniqueConstraint("item_id", "version", name="uq_sub_ver_item_ver"),
    )

    op.create_table(
        "print_quantities",
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
        sa.Column("roster_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("reserve_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("override_qty", sa.Integer(), nullable=True),
        sa.Column("exclude_cbt", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("revision", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("created_at", sa.Text(), nullable=False),
        sa.Column("updated_at", sa.Text(), nullable=False),
        sa.UniqueConstraint(
            "room_session_id", "requirement_id", name="uq_print_qty_rs_req"
        ),
    )

    op.create_table(
        "handovers",
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
            sa.ForeignKey("room_sessions.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("kind", sa.Text(), nullable=False),
        sa.Column("material_type", sa.Text(), nullable=False),
        sa.Column("expected_qty", sa.Integer(), nullable=False),
        sa.Column("actual_qty", sa.Integer(), nullable=False),
        sa.Column("discrepancy", sa.Integer(), nullable=False),
        sa.Column("from_person_name", sa.Text(), nullable=False),
        sa.Column("to_person_name", sa.Text(), nullable=False),
        sa.Column("handed_at", sa.Text(), nullable=False),
        sa.Column("note", sa.Text(), nullable=False, server_default=""),
        sa.Column("created_at", sa.Text(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("handovers")
    op.drop_table("print_quantities")
    op.drop_table("submission_versions")
    op.drop_table("submission_items")
