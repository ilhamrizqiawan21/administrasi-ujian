"""Create archive_packages and retention_backups tables for ARC-01..ARC-04.

Revision ID: 0016_arc_tables
Revises: 0015_lpj_tables
Create Date: 2026-11-26
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0016_arc_tables"
down_revision = "0015_lpj_tables"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "archive_packages",
        sa.Column("id", sa.Text(), primary_key=True),
        sa.Column(
            "institution_id",
            sa.Text(),
            sa.ForeignKey("institutions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "exam_id",
            sa.Text(),
            sa.ForeignKey("exams.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("file_path", sa.Text(), nullable=False),
        sa.Column("sha256", sa.Text(), nullable=False),
        sa.Column("file_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "include_personal_info",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),
        sa.Column("manifest_json", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("created_at", sa.Text(), nullable=False),
    )
    op.create_index("ix_arc_pkg_exam", "archive_packages", ["exam_id"])

    op.create_table(
        "retention_backups",
        sa.Column("id", sa.Text(), primary_key=True),
        sa.Column(
            "institution_id",
            sa.Text(),
            sa.ForeignKey("institutions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("exam_id", sa.Text(), nullable=True),
        sa.Column("exam_title", sa.Text(), nullable=False, server_default=""),
        sa.Column("file_path", sa.Text(), nullable=False),
        sa.Column("sha256", sa.Text(), nullable=False),
        sa.Column("byte_size", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("authorized_by", sa.Text(), nullable=False, server_default=""),
        sa.Column("created_at", sa.Text(), nullable=False),
    )
    op.create_index("ix_ret_bak_inst", "retention_backups", ["institution_id"])


def downgrade() -> None:
    op.drop_index("ix_ret_bak_inst", table_name="retention_backups")
    op.drop_table("retention_backups")
    op.drop_index("ix_arc_pkg_exam", table_name="archive_packages")
    op.drop_table("archive_packages")
