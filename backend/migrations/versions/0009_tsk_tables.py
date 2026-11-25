"""TSK tables: tasks and task_dependencies.

Revision ID: 0009_tsk_tables
Revises: 0008_com_tables
Create Date: 2026-11-25
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0009_tsk_tables"
down_revision = "0008_com_tables"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "tasks",
        sa.Column("id", sa.Text(), primary_key=True),
        sa.Column(
            "exam_id",
            sa.Text(),
            sa.ForeignKey("exams.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("phase", sa.Text(), nullable=False, server_default="preparation"),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("description", sa.Text(), nullable=False, server_default=""),
        sa.Column(
            "pic_id",
            sa.Text(),
            sa.ForeignKey("exam_people.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("priority", sa.Text(), nullable=False, server_default="medium"),
        sa.Column("due_date", sa.Text(), nullable=False),
        sa.Column("state", sa.Text(), nullable=False, server_default="todo"),
        sa.Column("blocked_reason", sa.Text(), nullable=False, server_default=""),
        sa.Column(
            "parent_id",
            sa.Text(),
            sa.ForeignKey("tasks.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("evidence_asset_id", sa.Text(), nullable=True),
        sa.Column("evidence_note", sa.Text(), nullable=False, server_default=""),
        sa.Column("completed_at", sa.Text(), nullable=True),
        sa.Column("completed_by", sa.Text(), nullable=True),
        sa.Column("revision", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("created_at", sa.Text(), nullable=False),
        sa.Column("updated_at", sa.Text(), nullable=False),
    )
    op.create_index("ix_tasks_exam", "tasks", ["exam_id"])

    op.create_table(
        "task_dependencies",
        sa.Column("id", sa.Text(), primary_key=True),
        sa.Column(
            "exam_id",
            sa.Text(),
            sa.ForeignKey("exams.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "task_id",
            sa.Text(),
            sa.ForeignKey("tasks.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "prerequisite_id",
            sa.Text(),
            sa.ForeignKey("tasks.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("created_at", sa.Text(), nullable=False),
        sa.UniqueConstraint("task_id", "prerequisite_id", name="uq_task_dep_pair"),
    )


def downgrade() -> None:
    op.drop_table("task_dependencies")
    op.drop_table("tasks")
