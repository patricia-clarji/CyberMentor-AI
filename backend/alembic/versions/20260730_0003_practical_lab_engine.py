"""Add durable practical lab sessions, actions, submissions, and artifact content.

Revision ID: 20260730_0003
Revises: 20260730_0002
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260730_0003"
down_revision: str | None = "20260730_0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("portfolio_artifacts", sa.Column("source_version", sa.String(40)))
    op.add_column("portfolio_artifacts", sa.Column("content", sa.JSON()))
    op.create_table(
        "lab_sessions",
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("lab_id", sa.String(160), nullable=False),
        sa.Column("lab_version", sa.String(40), nullable=False),
        sa.Column("status", sa.String(30), nullable=False),
        sa.Column("active_key", sa.String(20)),
        sa.Column("current_stage", sa.Integer(), nullable=False),
        sa.Column("cwd", sa.String(500), nullable=False),
        sa.Column("filesystem_state", sa.JSON(), nullable=False),
        sa.Column("objective_state", sa.JSON(), nullable=False),
        sa.Column("score_components", sa.JSON(), nullable=False),
        sa.Column("notes", sa.Text(), nullable=False),
        sa.Column("hints_used", sa.Integer(), nullable=False),
        sa.Column("command_count", sa.Integer(), nullable=False),
        sa.Column("incorrect_command_count", sa.Integer(), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_activity_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True)),
        sa.Column("final_submission", sa.JSON()),
        sa.Column("outcome", sa.String(30)),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "organization_id",
            "user_id",
            "lab_id",
            "active_key",
            name="uq_lab_session_active",
        ),
    )
    op.create_index(
        "ix_lab_session_owner_status",
        "lab_sessions",
        ["organization_id", "user_id", "status"],
    )
    op.create_index("ix_lab_sessions_organization_id", "lab_sessions", ["organization_id"])
    op.create_index("ix_lab_sessions_user_id", "lab_sessions", ["user_id"])
    op.create_table(
        "lab_actions",
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("session_id", sa.Uuid(), nullable=False),
        sa.Column("sequence", sa.Integer(), nullable=False),
        sa.Column("action_type", sa.String(40), nullable=False),
        sa.Column("input_text", sa.Text()),
        sa.Column("output_text", sa.Text()),
        sa.Column("successful", sa.Boolean(), nullable=False),
        sa.Column("mistake", sa.Boolean(), nullable=False),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("elapsed_seconds", sa.Integer(), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["session_id"], ["lab_sessions.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("session_id", "sequence", name="uq_lab_action_sequence"),
    )
    op.create_index(
        "ix_lab_action_owner_time",
        "lab_actions",
        ["organization_id", "user_id", "occurred_at"],
    )
    op.create_index("ix_lab_actions_organization_id", "lab_actions", ["organization_id"])
    op.create_index("ix_lab_actions_session_id", "lab_actions", ["session_id"])
    op.create_index("ix_lab_actions_user_id", "lab_actions", ["user_id"])
    op.create_table(
        "lab_submissions",
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("session_id", sa.Uuid(), nullable=False),
        sa.Column("idempotency_key", sa.String(120), nullable=False),
        sa.Column("response", sa.JSON(), nullable=False),
        sa.Column("correctness", sa.Float(), nullable=False),
        sa.Column("efficiency", sa.Float(), nullable=False),
        sa.Column("evidence_quality", sa.Float(), nullable=False),
        sa.Column("independence", sa.Float(), nullable=False),
        sa.Column("decision_quality", sa.Float(), nullable=False),
        sa.Column("report_quality", sa.Float(), nullable=False),
        sa.Column("overall_band", sa.String(30), nullable=False),
        sa.Column("passed", sa.Boolean(), nullable=False),
        sa.Column("feedback", sa.JSON(), nullable=False),
        sa.Column("evaluator_version", sa.String(40), nullable=False),
        sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["session_id"], ["lab_sessions.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "session_id",
            "idempotency_key",
            name="uq_lab_submission_idempotency",
        ),
    )
    op.create_index(
        "ix_lab_submission_owner",
        "lab_submissions",
        ["organization_id", "user_id", "submitted_at"],
    )
    op.create_index("ix_lab_submissions_organization_id", "lab_submissions", ["organization_id"])
    op.create_index("ix_lab_submissions_session_id", "lab_submissions", ["session_id"])
    op.create_index("ix_lab_submissions_user_id", "lab_submissions", ["user_id"])


def downgrade() -> None:
    op.drop_table("lab_submissions")
    op.drop_table("lab_actions")
    op.drop_table("lab_sessions")
    op.drop_column("portfolio_artifacts", "content")
    op.drop_column("portfolio_artifacts", "source_version")
