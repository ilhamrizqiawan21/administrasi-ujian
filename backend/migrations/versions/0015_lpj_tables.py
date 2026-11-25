"""LPJ tables: lpj_versions, lpj_evaluations, lpj_attachments.

Revision ID: 0015_lpj_tables
Revises: 0014_fin_tables
Create Date: 2026-11-25
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0015_lpj_tables"
down_revision = "0014_fin_tables"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "lpj_versions",
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
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("state", sa.Text(), nullable=False, server_default="draft"),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("sections_json", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("snapshot_json", sa.Text(), nullable=False, server_default="{}"),
        sa.Column(
            "doc_run_id",
            sa.Text(),
            sa.ForeignKey("document_runs.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("finalized_at", sa.Text(), nullable=True),
        sa.Column("created_at", sa.Text(), nullable=False),
        sa.Column("updated_at", sa.Text(), nullable=False),
        sa.UniqueConstraint("exam_id", "version", name="uq_lpj_ver_exam_num"),
    )

    op.create_table(
        "lpj_evaluations",
        sa.Column("id", sa.Text(), primary_key=True),
        sa.Column(
            "lpj_version_id",
            sa.Text(),
            sa.ForeignKey("lpj_versions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "incident_id",
            sa.Text(),
            sa.ForeignKey("incidents.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("issue_title", sa.Text(), nullable=False),
        sa.Column("resolution", sa.Text(), nullable=False, server_default=""),
        sa.Column("recommendation", sa.Text(), nullable=False, server_default=""),
        sa.Column("pic_name", sa.Text(), nullable=False, server_default=""),
        sa.Column("notes", sa.Text(), nullable=False, server_default=""),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("created_at", sa.Text(), nullable=False),
    )

    op.create_table(
        "lpj_attachments",
        sa.Column("id", sa.Text(), primary_key=True),
        sa.Column(
            "lpj_version_id",
            sa.Text(),
            sa.ForeignKey("lpj_versions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "doc_run_id",
            sa.Text(),
            sa.ForeignKey("document_runs.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("file_path", sa.Text(), nullable=False, server_default=""),
        sa.Column("included", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("exclusion_reason", sa.Text(), nullable=False, server_default=""),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("created_at", sa.Text(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("lpj_attachments")
    op.drop_table("lpj_evaluations")
    op.drop_table("lpj_versions")
