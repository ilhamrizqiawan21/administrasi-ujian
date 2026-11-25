"""TPL tables: letterheads, templates, theme_profiles.

Revision ID: 0012_tpl_tables
Revises: 0011_ops_tables
Create Date: 2026-11-25
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0012_tpl_tables"
down_revision = "0011_ops_tables"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "letterheads",
        sa.Column("id", sa.Text(), primary_key=True),
        sa.Column(
            "institution_id",
            sa.Text(),
            sa.ForeignKey("institutions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("mode", sa.Text(), nullable=False, server_default="manual"),
        sa.Column("config_json", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("asset_id", sa.Text(), nullable=True),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("active", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("created_at", sa.Text(), nullable=False),
    )
    op.create_index("ix_letterheads_inst", "letterheads", ["institution_id"])

    op.create_table(
        "templates",
        sa.Column("id", sa.Text(), primary_key=True),
        sa.Column(
            "institution_id",
            sa.Text(),
            sa.ForeignKey("institutions.id", ondelete="CASCADE"),
            nullable=True,
        ),
        sa.Column("doc_type", sa.Text(), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("engine", sa.Text(), nullable=False, server_default="reportlab"),
        sa.Column("asset_id", sa.Text(), nullable=True),
        sa.Column("layout_json", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("mapping_json", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("active", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("created_at", sa.Text(), nullable=False),
    )
    op.create_index(
        "ix_templates_inst_type", "templates", ["institution_id", "doc_type"]
    )

    op.create_table(
        "theme_profiles",
        sa.Column("id", sa.Text(), primary_key=True),
        sa.Column(
            "institution_id",
            sa.Text(),
            sa.ForeignKey("institutions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("tokens_json", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("active", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("created_at", sa.Text(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("theme_profiles")
    op.drop_table("templates")
    op.drop_table("letterheads")
