"""FIN tables: budget_categories, budget_versions, budget_lines, ledger, honor.

Revision ID: 0014_fin_tables
Revises: 0013_doc_tables
Create Date: 2026-11-25
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0014_fin_tables"
down_revision = "0013_doc_tables"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "budget_categories",
        sa.Column("id", sa.Text(), primary_key=True),
        sa.Column(
            "exam_id",
            sa.Text(),
            sa.ForeignKey("exams.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("label", sa.Text(), nullable=False),
        sa.Column(
            "parent_id",
            sa.Text(),
            sa.ForeignKey("budget_categories.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("source_fund", sa.Text(), nullable=False, server_default="BOS"),
        sa.Column("default_unit", sa.Text(), nullable=False, server_default="paket"),
        sa.Column("archived", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("revision", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("created_at", sa.Text(), nullable=False),
        sa.UniqueConstraint("exam_id", "label", name="uq_budget_cat_exam_label"),
    )

    op.create_table(
        "budget_versions",
        sa.Column("id", sa.Text(), primary_key=True),
        sa.Column(
            "exam_id",
            sa.Text(),
            sa.ForeignKey("exams.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("number", sa.Integer(), nullable=False),
        sa.Column("state", sa.Text(), nullable=False, server_default="draft"),
        sa.Column("approved_at", sa.Text(), nullable=True),
        sa.Column("created_at", sa.Text(), nullable=False),
        sa.UniqueConstraint("exam_id", "number", name="uq_budget_ver_exam_num"),
    )

    op.create_table(
        "budget_lines",
        sa.Column("id", sa.Text(), primary_key=True),
        sa.Column(
            "budget_version_id",
            sa.Text(),
            sa.ForeignKey("budget_versions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "category_id",
            sa.Text(),
            sa.ForeignKey("budget_categories.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("qty_decimal", sa.Text(), nullable=False),
        sa.Column("unit", sa.Text(), nullable=False),
        sa.Column("unit_rate_idr", sa.Integer(), nullable=False),
        sa.Column("amount_idr", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.Text(), nullable=False),
    )

    op.create_table(
        "ledger_entries",
        sa.Column("id", sa.Text(), primary_key=True),
        sa.Column(
            "exam_id",
            sa.Text(),
            sa.ForeignKey("exams.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "category_id",
            sa.Text(),
            sa.ForeignKey("budget_categories.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("kind", sa.Text(), nullable=False),
        sa.Column("amount_idr", sa.Integer(), nullable=False),
        sa.Column("entry_date", sa.Text(), nullable=False),
        sa.Column("reference", sa.Text(), nullable=False, server_default=""),
        sa.Column("payee", sa.Text(), nullable=False, server_default=""),
        sa.Column("attachment_asset_id", sa.Text(), nullable=True),
        sa.Column("state", sa.Text(), nullable=False, server_default="draft"),
        sa.Column(
            "reverses_id",
            sa.Text(),
            sa.ForeignKey("ledger_entries.id", ondelete="RESTRICT"),
            nullable=True,
        ),
        sa.Column("source_key", sa.Text(), nullable=True),
        sa.Column("created_at", sa.Text(), nullable=False),
        sa.Column("posted_at", sa.Text(), nullable=True),
    )
    op.create_index(
        "uq_ledger_source_key",
        "ledger_entries",
        ["source_key"],
        unique=True,
        sqlite_where=sa.text("source_key IS NOT NULL"),
    )
    op.create_index(
        "uq_ledger_reverses_id",
        "ledger_entries",
        ["reverses_id"],
        unique=True,
        sqlite_where=sa.text("reverses_id IS NOT NULL"),
    )

    op.create_table(
        "honor_rules",
        sa.Column("id", sa.Text(), primary_key=True),
        sa.Column(
            "exam_id",
            sa.Text(),
            sa.ForeignKey("exams.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("role_code", sa.Text(), nullable=False),
        sa.Column("unit_type", sa.Text(), nullable=False, server_default="session"),
        sa.Column("rate_idr", sa.Integer(), nullable=False),
        sa.Column("effective_date", sa.Text(), nullable=False),
        sa.Column("active", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("created_at", sa.Text(), nullable=False),
    )

    op.create_table(
        "honor_lines",
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
        sa.Column("source_type", sa.Text(), nullable=False),
        sa.Column("source_id", sa.Text(), nullable=False),
        sa.Column("role_code", sa.Text(), nullable=False),
        sa.Column("rate_idr", sa.Integer(), nullable=False),
        sa.Column("qty", sa.Integer(), nullable=False),
        sa.Column("amount_idr", sa.Integer(), nullable=False),
        sa.Column("state", sa.Text(), nullable=False, server_default="draft"),
        sa.Column(
            "ledger_entry_id",
            sa.Text(),
            sa.ForeignKey("ledger_entries.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("created_at", sa.Text(), nullable=False),
        sa.UniqueConstraint(
            "exam_id",
            "source_type",
            "source_id",
            "role_code",
            name="uq_honor_source_role",
        ),
    )


def downgrade() -> None:
    op.drop_table("honor_lines")
    op.drop_table("honor_rules")
    op.drop_table("ledger_entries")
    op.drop_table("budget_lines")
    op.drop_table("budget_versions")
    op.drop_table("budget_categories")
