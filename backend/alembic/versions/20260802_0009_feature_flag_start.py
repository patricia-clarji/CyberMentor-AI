"""Add effective-start scheduling to CMS feature flags.

Revision ID: 20260802_0009
Revises: 20260802_0008
Create Date: 2026-08-02
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260802_0009"
down_revision: str | None = "20260802_0008"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("cms_feature_flags") as batch:
        batch.add_column(sa.Column("starts_at", sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("cms_feature_flags") as batch:
        batch.drop_column("starts_at")
