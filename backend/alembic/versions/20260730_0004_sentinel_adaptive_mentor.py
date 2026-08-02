"""Add adaptive Sentinel memory, misconception evidence, and prompt provenance.

Revision ID: 20260730_0004
Revises: 20260730_0003
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260730_0004"
down_revision: str | None = "20260730_0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "mentor_learner_memories",
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("preferred_explanations", sa.JSON(), nullable=False),
        sa.Column("learning_pace", sa.String(30), nullable=False),
        sa.Column("confidence_estimate", sa.Float(), nullable=False),
        sa.Column("independence_estimate", sa.Float(), nullable=False),
        sa.Column("recent_failures", sa.JSON(), nullable=False),
        sa.Column("recent_improvements", sa.JSON(), nullable=False),
        sa.Column("study_streak_days", sa.Integer(), nullable=False),
        sa.Column("review_schedule", sa.JSON(), nullable=False),
        sa.Column("last_interaction_at", sa.DateTime(timezone=True)),
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
            name="uq_mentor_learner_memory_owner",
        ),
    )
    op.create_index(
        "ix_mentor_learner_memories_organization_id",
        "mentor_learner_memories",
        ["organization_id"],
    )
    op.create_index(
        "ix_mentor_learner_memories_user_id",
        "mentor_learner_memories",
        ["user_id"],
    )
    op.add_column(
        "mentor_messages",
        sa.Column(
            "mentor_mode",
            sa.String(50),
            nullable=False,
            server_default="socratic",
        ),
    )
    op.add_column(
        "mentor_messages",
        sa.Column(
            "retrieval_version",
            sa.String(40),
            nullable=False,
            server_default="unknown",
        ),
    )
    op.add_column(
        "mentor_messages",
        sa.Column(
            "provider",
            sa.String(60),
            nullable=False,
            server_default="deterministic",
        ),
    )
    op.add_column(
        "mentor_messages",
        sa.Column(
            "temperature",
            sa.Float(),
            nullable=False,
            server_default="0",
        ),
    )
    op.add_column(
        "mentor_messages",
        sa.Column(
            "prompt_tokens",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),
    )
    op.add_column(
        "mentor_messages",
        sa.Column(
            "completion_tokens",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),
    )
    op.add_column(
        "mentor_messages",
        sa.Column(
            "latency_ms",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),
    )
    op.add_column("mentor_messages", sa.Column("reasoning_summary", sa.Text()))
    op.add_column(
        "mentor_messages",
        sa.Column(
            "related_skills",
            sa.JSON(),
            nullable=False,
            server_default=sa.text("'[]'"),
        ),
    )
    op.add_column("mentor_messages", sa.Column("recommended_action", sa.JSON()))
    op.create_table(
        "mentor_message_feedback",
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("message_id", sa.Uuid(), nullable=False),
        sa.Column("rating", sa.String(30), nullable=False),
        sa.Column("issue_tags", sa.JSON(), nullable=False),
        sa.Column("comment", sa.Text()),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["message_id"], ["mentor_messages.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("message_id", "user_id", name="uq_mentor_message_feedback_owner"),
    )
    op.create_index(
        "ix_mentor_message_feedback_organization_id",
        "mentor_message_feedback",
        ["organization_id"],
    )
    op.create_index(
        "ix_mentor_message_feedback_user_id",
        "mentor_message_feedback",
        ["user_id"],
    )
    op.create_index(
        "ix_mentor_message_feedback_message_id",
        "mentor_message_feedback",
        ["message_id"],
    )
    op.add_column(
        "ai_usage_events",
        sa.Column(
            "prompt_version",
            sa.String(40),
            nullable=False,
            server_default="unknown",
        ),
    )
    op.add_column(
        "ai_usage_events",
        sa.Column(
            "retrieval_version",
            sa.String(40),
            nullable=False,
            server_default="unknown",
        ),
    )
    op.add_column(
        "ai_usage_events",
        sa.Column(
            "temperature",
            sa.Float(),
            nullable=False,
            server_default="0",
        ),
    )
    op.add_column(
        "learner_misconceptions",
        sa.Column(
            "confidence",
            sa.Float(),
            nullable=False,
            server_default="0.35",
        ),
    )
    op.add_column(
        "learner_misconceptions",
        sa.Column(
            "first_observed_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.add_column(
        "learner_misconceptions",
        sa.Column(
            "supporting_evidence",
            sa.JSON(),
            nullable=False,
            server_default=sa.text("'[]'"),
        ),
    )
    op.add_column(
        "learner_misconceptions",
        sa.Column("resolved_at", sa.DateTime(timezone=True)),
    )


def downgrade() -> None:
    op.drop_column("learner_misconceptions", "resolved_at")
    op.drop_column("learner_misconceptions", "supporting_evidence")
    op.drop_column("learner_misconceptions", "first_observed_at")
    op.drop_column("learner_misconceptions", "confidence")
    op.drop_column("ai_usage_events", "temperature")
    op.drop_column("ai_usage_events", "retrieval_version")
    op.drop_column("ai_usage_events", "prompt_version")
    op.drop_table("mentor_message_feedback")
    op.drop_column("mentor_messages", "recommended_action")
    op.drop_column("mentor_messages", "related_skills")
    op.drop_column("mentor_messages", "reasoning_summary")
    op.drop_column("mentor_messages", "latency_ms")
    op.drop_column("mentor_messages", "completion_tokens")
    op.drop_column("mentor_messages", "prompt_tokens")
    op.drop_column("mentor_messages", "temperature")
    op.drop_column("mentor_messages", "provider")
    op.drop_column("mentor_messages", "retrieval_version")
    op.drop_column("mentor_messages", "mentor_mode")
    op.drop_table("mentor_learner_memories")
