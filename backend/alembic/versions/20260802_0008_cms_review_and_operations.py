"""Extend CMS review history, relationships, media, and jobs.

Revision ID: 20260802_0008
Revises: 20260801_0007
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

from app.models.cms import CmsReviewDecision, CmsReviewRequirement

revision: str = "20260802_0008"
down_revision: str | None = "20260801_0007"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    bind = op.get_bind()
    CmsReviewRequirement.__table__.create(bind, checkfirst=False)
    CmsReviewDecision.__table__.create(bind, checkfirst=False)
    with op.batch_alter_table("cms_content_relations") as batch:
        batch.add_column(sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"))
        batch.add_column(sa.Column("configuration", sa.JSON(), nullable=False, server_default="{}"))
    with op.batch_alter_table("cms_media_assets") as batch:
        batch.add_column(sa.Column("title", sa.String(240), nullable=False, server_default=""))
        batch.add_column(sa.Column("description", sa.Text(), nullable=False, server_default=""))
        batch.add_column(sa.Column("version", sa.Integer(), nullable=False, server_default="1"))
        batch.add_column(sa.Column("replacement_of_media_id", sa.Uuid()))
        batch.add_column(
            sa.Column("scan_status", sa.String(40), nullable=False, server_default="unconfigured")
        )
        batch.create_foreign_key(
            "fk_cms_media_assets_replacement_of_media_id_cms_media_assets",
            "cms_media_assets",
            ["replacement_of_media_id"],
            ["id"],
            ondelete="RESTRICT",
        )
    with op.batch_alter_table("cms_background_jobs") as batch:
        batch.add_column(sa.Column("retry_count", sa.Integer(), nullable=False, server_default="0"))
        batch.add_column(sa.Column("cancelled_at", sa.DateTime(timezone=True)))


def downgrade() -> None:
    with op.batch_alter_table("cms_background_jobs") as batch:
        batch.drop_column("cancelled_at")
        batch.drop_column("retry_count")
    with op.batch_alter_table("cms_media_assets") as batch:
        batch.drop_constraint(
            "fk_cms_media_assets_replacement_of_media_id_cms_media_assets", type_="foreignkey"
        )
        batch.drop_column("scan_status")
        batch.drop_column("replacement_of_media_id")
        batch.drop_column("version")
        batch.drop_column("description")
        batch.drop_column("title")
    with op.batch_alter_table("cms_content_relations") as batch:
        batch.drop_column("configuration")
        batch.drop_column("sort_order")
    bind = op.get_bind()
    CmsReviewDecision.__table__.drop(bind, checkfirst=True)
    CmsReviewRequirement.__table__.drop(bind, checkfirst=True)
