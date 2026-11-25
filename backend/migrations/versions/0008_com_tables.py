"""COM tables: committee_roles, committee_members, program_kerja, meetings, signatories.

Revision ID: 0008_com_tables
Revises: 0007_sch_tables
Create Date: 2026-11-25
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0008_com_tables"
down_revision = "0007_sch_tables"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "committee_roles",
        sa.Column("id", sa.Text(), primary_key=True),
        sa.Column(
            "exam_id",
            sa.Text(),
            sa.ForeignKey("exams.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column(
            "parent_id",
            sa.Text(),
            sa.ForeignKey("committee_roles.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("jobdesc", sa.Text(), nullable=False, server_default=""),
        sa.Column("revision", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("created_at", sa.Text(), nullable=False),
        sa.Column("updated_at", sa.Text(), nullable=False),
    )
    op.create_index("ix_committee_roles_exam", "committee_roles", ["exam_id"])

    op.create_table(
        "committee_members",
        sa.Column("id", sa.Text(), primary_key=True),
        sa.Column(
            "exam_id",
            sa.Text(),
            sa.ForeignKey("exams.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "role_id",
            sa.Text(),
            sa.ForeignKey("committee_roles.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "exam_person_id",
            sa.Text(),
            sa.ForeignKey("exam_people.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("appointed_on", sa.Text(), nullable=False, server_default=""),
        sa.Column("note", sa.Text(), nullable=False, server_default=""),
        sa.Column("revision", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("created_at", sa.Text(), nullable=False),
        sa.Column("updated_at", sa.Text(), nullable=False),
        sa.UniqueConstraint("role_id", "exam_person_id", name="uq_com_role_person"),
    )

    op.create_table(
        "program_kerja",
        sa.Column("id", sa.Text(), primary_key=True),
        sa.Column(
            "exam_id",
            sa.Text(),
            sa.ForeignKey("exams.id", ondelete="CASCADE"),
            nullable=False,
            unique=True,
        ),
        sa.Column("basis_text", sa.Text(), nullable=False, server_default=""),
        sa.Column("objectives_json", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("milestones_json", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("sections_json", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("revision", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("created_at", sa.Text(), nullable=False),
        sa.Column("updated_at", sa.Text(), nullable=False),
    )

    op.create_table(
        "meetings",
        sa.Column("id", sa.Text(), primary_key=True),
        sa.Column(
            "exam_id",
            sa.Text(),
            sa.ForeignKey("exams.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("meeting_date", sa.Text(), nullable=False),
        sa.Column("start_time", sa.Text(), nullable=False),
        sa.Column("end_time", sa.Text(), nullable=False),
        sa.Column("location", sa.Text(), nullable=False, server_default=""),
        sa.Column("agenda", sa.Text(), nullable=False, server_default=""),
        sa.Column("minutes", sa.Text(), nullable=False, server_default=""),
        sa.Column("decisions_json", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("revision", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("created_at", sa.Text(), nullable=False),
        sa.Column("updated_at", sa.Text(), nullable=False),
    )
    op.create_index("ix_meetings_exam", "meetings", ["exam_id"])

    op.create_table(
        "meeting_attendance",
        sa.Column("id", sa.Text(), primary_key=True),
        sa.Column(
            "meeting_id",
            sa.Text(),
            sa.ForeignKey("meetings.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "exam_person_id",
            sa.Text(),
            sa.ForeignKey("exam_people.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("state", sa.Text(), nullable=False, server_default="unrecorded"),
        sa.Column("note", sa.Text(), nullable=False, server_default=""),
        sa.Column("revision", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("created_at", sa.Text(), nullable=False),
        sa.Column("updated_at", sa.Text(), nullable=False),
        sa.UniqueConstraint(
            "meeting_id", "exam_person_id", name="uq_meeting_attendance_person"
        ),
    )

    op.create_table(
        "exam_signatories",
        sa.Column("id", sa.Text(), primary_key=True),
        sa.Column(
            "exam_id",
            sa.Text(),
            sa.ForeignKey("exams.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("role_key", sa.Text(), nullable=False),
        sa.Column("role_label", sa.Text(), nullable=False),
        sa.Column(
            "exam_person_id",
            sa.Text(),
            sa.ForeignKey("exam_people.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("signer_name", sa.Text(), nullable=False, server_default=""),
        sa.Column("signer_title", sa.Text(), nullable=False, server_default=""),
        sa.Column("signer_nip", sa.Text(), nullable=False, server_default=""),
        sa.Column("signed_date", sa.Text(), nullable=False, server_default=""),
        sa.Column("signature_asset_id", sa.Text(), nullable=True),
        sa.Column("required", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("revision", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("created_at", sa.Text(), nullable=False),
        sa.Column("updated_at", sa.Text(), nullable=False),
        sa.UniqueConstraint("exam_id", "role_key", name="uq_exam_signatory_key"),
    )


def downgrade() -> None:
    op.drop_table("exam_signatories")
    op.drop_table("meeting_attendance")
    op.drop_table("meetings")
    op.drop_table("program_kerja")
    op.drop_table("committee_members")
    op.drop_table("committee_roles")
