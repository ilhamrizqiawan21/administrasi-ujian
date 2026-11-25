"""DOC tables: document_runs and document_numbers.

Revision ID: 0013_doc_tables
Revises: 0012_tpl_tables
Create Date: 2026-11-25
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0013_doc_tables"
down_revision = "0012_tpl_tables"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "document_runs",
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
        sa.Column("plan_id", sa.Text(), nullable=True),
        sa.Column("doc_type", sa.Text(), nullable=False),
        sa.Column("format", sa.Text(), nullable=False),
        sa.Column("template_id", sa.Text(), nullable=True),
        sa.Column("context_hash", sa.Text(), nullable=False),
        sa.Column("scope_json", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("status", sa.Text(), nullable=False, server_default="preview"),
        sa.Column("output_path", sa.Text(), nullable=False),
        sa.Column("output_hash", sa.Text(), nullable=False),
        sa.Column("generated_at", sa.Text(), nullable=False),
        sa.Column("created_at", sa.Text(), nullable=False),
    )
    op.create_index("ix_doc_runs_exam", "document_runs", ["exam_id"])

    op.create_table(
        "document_numbers",
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
        sa.Column("series", sa.Text(), nullable=False),
        sa.Column("sequence", sa.Integer(), nullable=False),
        sa.Column("number_text", sa.Text(), nullable=False),
        sa.Column(
            "doc_run_id",
            sa.Text(),
            sa.ForeignKey("document_runs.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("status", sa.Text(), nullable=False, server_default="active"),
        sa.Column("created_at", sa.Text(), nullable=False),
        sa.UniqueConstraint(
            "institution_id", "series", "sequence", name="uq_doc_num_seq"
        ),
        sa.UniqueConstraint("institution_id", "number_text", name="uq_doc_num_text"),
    )


def downgrade() -> None:
    op.drop_table("document_numbers")
    op.drop_table("document_runs")
