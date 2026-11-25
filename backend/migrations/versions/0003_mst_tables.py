"""MST tables: classes, students, enrollments, staff, subjects, and rooms.

Revision ID: 0003_mst_tables
Revises: 0002_cfg_tables
Create Date: 2026-11-25
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0003_mst_tables"
down_revision = "0002_cfg_tables"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "classes",
        sa.Column("id", sa.Text(), primary_key=True),
        sa.Column(
            "institution_id",
            sa.Text(),
            sa.ForeignKey("institutions.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "year_id",
            sa.Text(),
            sa.ForeignKey("academic_years.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "level_id",
            sa.Text(),
            sa.ForeignKey("levels.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("program", sa.Text(), nullable=True),
        sa.Column("revision", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("created_at", sa.Text(), nullable=False),
        sa.Column("updated_at", sa.Text(), nullable=False),
        sa.UniqueConstraint(
            "year_id", "level_id", "name", name="uq_class_year_level_name"
        ),
    )

    op.create_table(
        "students",
        sa.Column("id", sa.Text(), primary_key=True),
        sa.Column(
            "institution_id",
            sa.Text(),
            sa.ForeignKey("institutions.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("nis", sa.Text(), nullable=True),
        sa.Column("nisn", sa.Text(), nullable=True),
        sa.Column("full_name", sa.Text(), nullable=False),
        sa.Column("gender", sa.Text(), nullable=True),
        sa.Column(
            "photo_asset_id",
            sa.Text(),
            sa.ForeignKey("assets.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("accommodation_json", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("active", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("revision", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("created_at", sa.Text(), nullable=False),
        sa.Column("updated_at", sa.Text(), nullable=False),
    )
    op.create_index(
        "uq_student_inst_nis",
        "students",
        ["institution_id", "nis"],
        unique=True,
        sqlite_where=sa.text("nis IS NOT NULL AND nis != ''"),
    )
    op.create_index(
        "ix_students_inst_name", "students", ["institution_id", "full_name"]
    )

    op.create_table(
        "enrollments",
        sa.Column("id", sa.Text(), primary_key=True),
        sa.Column(
            "institution_id",
            sa.Text(),
            sa.ForeignKey("institutions.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "student_id",
            sa.Text(),
            sa.ForeignKey("students.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "class_id",
            sa.Text(),
            sa.ForeignKey("classes.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "year_id",
            sa.Text(),
            sa.ForeignKey("academic_years.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("status", sa.Text(), nullable=False, server_default="active"),
        sa.Column("revision", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("created_at", sa.Text(), nullable=False),
        sa.Column("updated_at", sa.Text(), nullable=False),
        sa.UniqueConstraint("student_id", "year_id", name="uq_enrollment_student_year"),
    )

    op.create_table(
        "staff",
        sa.Column("id", sa.Text(), primary_key=True),
        sa.Column(
            "institution_id",
            sa.Text(),
            sa.ForeignKey("institutions.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("staff_code", sa.Text(), nullable=False),
        sa.Column("nip", sa.Text(), nullable=True),
        sa.Column("full_name", sa.Text(), nullable=False),
        sa.Column("role", sa.Text(), nullable=False, server_default="teacher"),
        sa.Column("active", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("revision", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("created_at", sa.Text(), nullable=False),
        sa.Column("updated_at", sa.Text(), nullable=False),
        sa.UniqueConstraint("institution_id", "staff_code", name="uq_staff_inst_code"),
    )

    op.create_table(
        "subjects",
        sa.Column("id", sa.Text(), primary_key=True),
        sa.Column(
            "institution_id",
            sa.Text(),
            sa.ForeignKey("institutions.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("code", sa.Text(), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("category", sa.Text(), nullable=True),
        sa.Column("revision", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("created_at", sa.Text(), nullable=False),
        sa.Column("updated_at", sa.Text(), nullable=False),
        sa.UniqueConstraint("institution_id", "code", name="uq_subject_inst_code"),
    )

    op.create_table(
        "teaching_assignments",
        sa.Column("id", sa.Text(), primary_key=True),
        sa.Column(
            "institution_id",
            sa.Text(),
            sa.ForeignKey("institutions.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "staff_id",
            sa.Text(),
            sa.ForeignKey("staff.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "class_id",
            sa.Text(),
            sa.ForeignKey("classes.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "subject_id",
            sa.Text(),
            sa.ForeignKey("subjects.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("revision", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("created_at", sa.Text(), nullable=False),
        sa.Column("updated_at", sa.Text(), nullable=False),
        sa.UniqueConstraint(
            "staff_id", "class_id", "subject_id", name="uq_teaching_triple"
        ),
    )

    op.create_table(
        "rooms",
        sa.Column("id", sa.Text(), primary_key=True),
        sa.Column(
            "institution_id",
            sa.Text(),
            sa.ForeignKey("institutions.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("code", sa.Text(), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("mode", sa.Text(), nullable=False, server_default="paper"),
        sa.Column("capacity_limit", sa.Integer(), nullable=False),
        sa.Column("layout_json", sa.Text(), nullable=False),
        sa.Column("revision", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("created_at", sa.Text(), nullable=False),
        sa.Column("updated_at", sa.Text(), nullable=False),
        sa.UniqueConstraint("institution_id", "code", name="uq_room_inst_code"),
    )


def downgrade() -> None:
    op.drop_table("rooms")
    op.drop_table("teaching_assignments")
    op.drop_table("subjects")
    op.drop_table("staff")
    op.drop_table("enrollments")
    op.drop_index("ix_students_inst_name", table_name="students")
    op.drop_index("uq_student_inst_nis", table_name="students")
    op.drop_table("students")
    op.drop_table("classes")
