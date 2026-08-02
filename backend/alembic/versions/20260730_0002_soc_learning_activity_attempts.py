"""Persist trusted SOC learning activity attempts.

Revision ID: 20260730_0002
Revises: 20260728_0001
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260730_0002"
down_revision: str | None = "20260728_0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "learning_activity_attempts",
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("activity_id", sa.String(length=160), nullable=False),
        sa.Column("activity_version", sa.String(length=40), nullable=False),
        sa.Column("activity_type", sa.String(length=50), nullable=False),
        sa.Column("module_id", sa.String(length=160), nullable=False),
        sa.Column("response", sa.JSON(), nullable=False),
        sa.Column("score", sa.Float(), nullable=False),
        sa.Column("passed", sa.Boolean(), nullable=False),
        sa.Column("hints_used", sa.Integer(), nullable=False),
        sa.Column("evaluator", sa.String(length=60), nullable=False),
        sa.Column("feedback", sa.Text(), nullable=False),
        sa.Column("idempotency_key", sa.String(length=100), nullable=False),
        sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["organization_id"],
            ["organizations.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "organization_id",
            "user_id",
            "idempotency_key",
            name="uq_learning_activity_attempts_organization_id",
        ),
    )
    op.create_index(
        "ix_learning_activity_attempt_owner",
        "learning_activity_attempts",
        ["organization_id", "user_id", "activity_id"],
    )
    op.create_index(
        op.f("ix_learning_activity_attempts_organization_id"),
        "learning_activity_attempts",
        ["organization_id"],
    )
    op.create_index(
        op.f("ix_learning_activity_attempts_user_id"),
        "learning_activity_attempts",
        ["user_id"],
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_learning_activity_attempts_user_id"),
        table_name="learning_activity_attempts",
    )
    op.drop_index(
        op.f("ix_learning_activity_attempts_organization_id"),
        table_name="learning_activity_attempts",
    )
    op.drop_index(
        "ix_learning_activity_attempt_owner",
        table_name="learning_activity_attempts",
    )
    op.drop_table("learning_activity_attempts")
