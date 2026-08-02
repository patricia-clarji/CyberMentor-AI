"""Add organization scope to CMS background jobs.

Revision ID: 20260802_0010
Revises: 20260802_0009
Create Date: 2026-08-02
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260802_0010"
down_revision: str | None = "20260802_0009"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("cms_background_jobs") as batch:
        batch.add_column(sa.Column("organization_id", sa.Uuid(), nullable=True))
        batch.create_foreign_key(
            "fk_cms_background_jobs_organization_id_organizations",
            "organizations",
            ["organization_id"],
            ["id"],
            ondelete="RESTRICT",
        )
        batch.create_index(
            "ix_cms_background_jobs_organization_id", ["organization_id"], unique=False
        )


def downgrade() -> None:
    with op.batch_alter_table("cms_background_jobs") as batch:
        batch.drop_index("ix_cms_background_jobs_organization_id")
        batch.drop_constraint(
            "fk_cms_background_jobs_organization_id_organizations", type_="foreignkey"
        )
        batch.drop_column("organization_id")
