"""CFG tables: institutions, assets, academic_years, levels, exam_types, settings.

Revision ID: 0002_cfg_tables
Revises: 0001_core_bootstrap
Create Date: 2026-11-25
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0002_cfg_tables"
down_revision = "0001_core_bootstrap"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "institutions",
        sa.Column("id", sa.Text(), primary_key=True),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("short_name", sa.Text(), nullable=True),
        sa.Column("npsn", sa.Text(), nullable=True),
        sa.Column("nsm", sa.Text(), nullable=True),
        sa.Column("address", sa.Text(), nullable=True),
        sa.Column("timezone", sa.Text(), nullable=False, server_default="Asia/Jakarta"),
        sa.Column("logo_asset_id", sa.Text(), nullable=True),
        sa.Column("revision", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("created_at", sa.Text(), nullable=False),
        sa.Column("updated_at", sa.Text(), nullable=False),
        sa.Column("archived_at", sa.Text(), nullable=True),
    )

    op.create_table(
        "assets",
        sa.Column("id", sa.Text(), primary_key=True),
        sa.Column(
            "institution_id",
            sa.Text(),
            sa.ForeignKey("institutions.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("relative_path", sa.Text(), nullable=False),
        sa.Column("sha256", sa.Text(), nullable=False),
        sa.Column("mime", sa.Text(), nullable=False),
        sa.Column("byte_size", sa.Integer(), nullable=False),
        sa.Column("purpose", sa.Text(), nullable=False),
        sa.Column("revision", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("created_at", sa.Text(), nullable=False),
        sa.Column("updated_at", sa.Text(), nullable=False),
    )
    op.create_index("ix_assets_institution", "assets", ["institution_id"])

    op.create_table(
        "academic_years",
        sa.Column("id", sa.Text(), primary_key=True),
        sa.Column(
            "institution_id",
            sa.Text(),
            sa.ForeignKey("institutions.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("label", sa.Text(), nullable=False),
        sa.Column("starts_on", sa.Text(), nullable=True),
        sa.Column("ends_on", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("revision", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("created_at", sa.Text(), nullable=False),
        sa.Column("updated_at", sa.Text(), nullable=False),
        sa.UniqueConstraint("institution_id", "label", name="uq_year_inst_label"),
    )

    op.create_table(
        "levels",
        sa.Column("id", sa.Text(), primary_key=True),
        sa.Column(
            "institution_id",
            sa.Text(),
            sa.ForeignKey("institutions.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("label", sa.Text(), nullable=False),
        sa.Column("sort_order", sa.Integer(), nullable=False),
        sa.Column("revision", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("created_at", sa.Text(), nullable=False),
        sa.Column("updated_at", sa.Text(), nullable=False),
        sa.UniqueConstraint("institution_id", "label", name="uq_level_inst_label"),
    )

    op.create_table(
        "exam_types",
        sa.Column("id", sa.Text(), primary_key=True),
        sa.Column(
            "institution_id",
            sa.Text(),
            sa.ForeignKey("institutions.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("code", sa.Text(), nullable=False),
        sa.Column("label", sa.Text(), nullable=False),
        sa.Column("mode_default", sa.Text(), nullable=False, server_default="paper"),
        sa.Column("terminology_json", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("revision", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("created_at", sa.Text(), nullable=False),
        sa.Column("updated_at", sa.Text(), nullable=False),
        sa.UniqueConstraint("institution_id", "code", name="uq_examtype_inst_code"),
    )

    op.create_table(
        "settings",
        sa.Column("id", sa.Text(), primary_key=True),
        sa.Column(
            "institution_id",
            sa.Text(),
            sa.ForeignKey("institutions.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("key", sa.Text(), nullable=False),
        sa.Column("value_json", sa.Text(), nullable=False),
        sa.Column("revision", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("created_at", sa.Text(), nullable=False),
        sa.Column("updated_at", sa.Text(), nullable=False),
        sa.UniqueConstraint("institution_id", "key", name="uq_setting_inst_key"),
    )


def downgrade() -> None:
    op.drop_table("settings")
    op.drop_table("exam_types")
    op.drop_table("levels")
    op.drop_table("academic_years")
    op.drop_index("ix_assets_institution", table_name="assets")
    op.drop_table("assets")
    op.drop_table("institutions")
