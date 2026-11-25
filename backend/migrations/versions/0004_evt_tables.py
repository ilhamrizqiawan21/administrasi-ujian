"""EVT tables and audit_events.

Revision ID: 0004_evt_tables
Revises: 0003_mst_tables
Create Date: 2026-11-25
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0004_evt_tables"
down_revision = "0003_mst_tables"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "exams",
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
            "exam_type_id",
            sa.Text(),
            sa.ForeignKey("exam_types.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("semester_label", sa.Text(), nullable=False),
        sa.Column("mode", sa.Text(), nullable=False, server_default="paper"),
        sa.Column("starts_on", sa.Text(), nullable=False),
        sa.Column("ends_on", sa.Text(), nullable=False),
        sa.Column("state", sa.Text(), nullable=False, server_default="DRAFT"),
        sa.Column("config_json", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("active_plan_id", sa.Text(), nullable=True),
        sa.Column("revision", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("created_at", sa.Text(), nullable=False),
        sa.Column("updated_at", sa.Text(), nullable=False),
    )

    op.create_table(
        "exam_people",
        sa.Column("id", sa.Text(), primary_key=True),
        sa.Column(
            "exam_id",
            sa.Text(),
            sa.ForeignKey("exams.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("source_id", sa.Text(), nullable=True),
        sa.Column("kind", sa.Text(), nullable=False),
        sa.Column("code", sa.Text(), nullable=False),
        sa.Column("display_name", sa.Text(), nullable=False),
        sa.Column("level_label", sa.Text(), nullable=True),
        sa.Column("class_label", sa.Text(), nullable=True),
        sa.Column("photo_asset_id", sa.Text(), nullable=True),
        sa.Column("snapshot_json", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("revision", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("created_at", sa.Text(), nullable=False),
        sa.Column("updated_at", sa.Text(), nullable=False),
    )
    op.create_index(
        "uq_exam_person_source",
        "exam_people",
        ["exam_id", "kind", "source_id"],
        unique=True,
        sqlite_where=sa.text("source_id IS NOT NULL"),
    )

    op.create_table(
        "exam_participants",
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
        sa.Column("participant_number", sa.Text(), nullable=True),
        sa.Column("eligibility", sa.Text(), nullable=False, server_default="eligible"),
        sa.Column("accommodation_json", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("revision", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("created_at", sa.Text(), nullable=False),
        sa.Column("updated_at", sa.Text(), nullable=False),
        sa.UniqueConstraint("exam_id", "exam_person_id", name="uq_exampart_person"),
    )
    op.create_index(
        "uq_exampart_number",
        "exam_participants",
        ["exam_id", "participant_number"],
        unique=True,
        sqlite_where=sa.text(
            "participant_number IS NOT NULL AND participant_number != ''"
        ),
    )

    op.create_table(
        "exam_rooms",
        sa.Column("id", sa.Text(), primary_key=True),
        sa.Column(
            "exam_id",
            sa.Text(),
            sa.ForeignKey("exams.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("source_room_id", sa.Text(), nullable=True),
        sa.Column("code", sa.Text(), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("layout_json", sa.Text(), nullable=False),
        sa.Column("capacity_limit", sa.Integer(), nullable=False),
        sa.Column("mode", sa.Text(), nullable=False),
        sa.Column("revision", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("created_at", sa.Text(), nullable=False),
        sa.Column("updated_at", sa.Text(), nullable=False),
        sa.UniqueConstraint("exam_id", "code", name="uq_examroom_code"),
    )

    op.create_table(
        "exam_subjects",
        sa.Column("id", sa.Text(), primary_key=True),
        sa.Column(
            "exam_id",
            sa.Text(),
            sa.ForeignKey("exams.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("source_subject_id", sa.Text(), nullable=True),
        sa.Column("code", sa.Text(), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("revision", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("created_at", sa.Text(), nullable=False),
        sa.Column("updated_at", sa.Text(), nullable=False),
        sa.UniqueConstraint("exam_id", "code", name="uq_examsubj_code"),
    )

    op.create_table(
        "exam_groups",
        sa.Column("id", sa.Text(), primary_key=True),
        sa.Column(
            "exam_id",
            sa.Text(),
            sa.ForeignKey("exams.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("label", sa.Text(), nullable=False),
        sa.Column("rule_json", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("revision", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("created_at", sa.Text(), nullable=False),
        sa.Column("updated_at", sa.Text(), nullable=False),
        sa.UniqueConstraint("exam_id", "label", name="uq_examgroup_label"),
    )

    op.create_table(
        "group_members",
        sa.Column("id", sa.Text(), primary_key=True),
        sa.Column(
            "group_id",
            sa.Text(),
            sa.ForeignKey("exam_groups.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "participant_id",
            sa.Text(),
            sa.ForeignKey("exam_participants.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("revision", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("created_at", sa.Text(), nullable=False),
        sa.Column("updated_at", sa.Text(), nullable=False),
        sa.UniqueConstraint("group_id", "participant_id", name="uq_group_member"),
    )

    op.create_table(
        "exam_requirements",
        sa.Column("id", sa.Text(), primary_key=True),
        sa.Column(
            "group_id",
            sa.Text(),
            sa.ForeignKey("exam_groups.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "exam_subject_id",
            sa.Text(),
            sa.ForeignKey("exam_subjects.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("attempt_no", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("duration_min", sa.Integer(), nullable=False, server_default="90"),
        sa.Column("mode", sa.Text(), nullable=False, server_default="paper"),
        sa.Column(
            "eligible_sessions_json", sa.Text(), nullable=False, server_default="[]"
        ),
        sa.Column("revision", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("created_at", sa.Text(), nullable=False),
        sa.Column("updated_at", sa.Text(), nullable=False),
        sa.UniqueConstraint(
            "group_id",
            "exam_subject_id",
            "attempt_no",
            name="uq_examreq_group_subj_attempt",
        ),
    )

    op.create_table(
        "audit_events",
        sa.Column("id", sa.Text(), primary_key=True),
        sa.Column(
            "institution_id",
            sa.Text(),
            sa.ForeignKey("institutions.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("exam_id", sa.Text(), nullable=True),
        sa.Column("actor", sa.Text(), nullable=False, server_default="operator"),
        sa.Column("action", sa.Text(), nullable=False),
        sa.Column("entity_type", sa.Text(), nullable=False),
        sa.Column("entity_id", sa.Text(), nullable=False),
        sa.Column("at", sa.Text(), nullable=False),
        sa.Column(
            "change_summary_json", sa.Text(), nullable=False, server_default="{}"
        ),
        sa.Column("correlation_id", sa.Text(), nullable=False, server_default="-"),
    )


def downgrade() -> None:
    op.drop_table("audit_events")
    op.drop_table("exam_requirements")
    op.drop_table("group_members")
    op.drop_table("exam_groups")
    op.drop_table("exam_subjects")
    op.drop_table("exam_rooms")
    op.drop_index("uq_exampart_number", table_name="exam_participants")
    op.drop_table("exam_participants")
    op.drop_index("uq_exam_person_source", table_name="exam_people")
    op.drop_table("exam_people")
    op.drop_table("exams")
