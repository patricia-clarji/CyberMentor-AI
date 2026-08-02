"""Operational CMS foundation.

Revision ID: 20260801_0006
Revises: 20260730_0005
Create Date: 2026-08-01
"""

from collections.abc import Sequence

from alembic import op
from app.models.cms import (
    CmsApiKeyMetadata,
    CmsBackgroundJob,
    CmsContent,
    CmsContentRelation,
    CmsContentTaxonomy,
    CmsContentVersion,
    CmsFeatureFlag,
    CmsLearningObjective,
    CmsLessonSection,
    CmsMaintenanceWindow,
    CmsMediaAsset,
    CmsMediaUsage,
    CmsNotificationTemplate,
    CmsPlatformSetting,
    CmsPublicationEvent,
    CmsReviewAssignment,
    CmsReviewComment,
    CmsSavedSearch,
    CmsTaxonomyTerm,
    CmsTranslation,
    CmsValidationResult,
)

revision: str = "20260801_0006"
down_revision: str | None = "20260730_0005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

TABLES = [
    CmsContent.__table__,
    CmsContentVersion.__table__,
    CmsLessonSection.__table__,
    CmsLearningObjective.__table__,
    CmsContentRelation.__table__,
    CmsReviewAssignment.__table__,
    CmsReviewComment.__table__,
    CmsValidationResult.__table__,
    CmsPublicationEvent.__table__,
    CmsMediaAsset.__table__,
    CmsMediaUsage.__table__,
    CmsTaxonomyTerm.__table__,
    CmsContentTaxonomy.__table__,
    CmsTranslation.__table__,
    CmsFeatureFlag.__table__,
    CmsPlatformSetting.__table__,
    CmsApiKeyMetadata.__table__,
    CmsBackgroundJob.__table__,
    CmsSavedSearch.__table__,
    CmsMaintenanceWindow.__table__,
    CmsNotificationTemplate.__table__,
]


def upgrade() -> None:
    bind = op.get_bind()
    for table in TABLES:
        table.create(bind=bind, checkfirst=True)

    # This historical migration intentionally freezes the schema as it existed
    # at revision 0006. TABLES uses application metadata so a clean install
    # must remove columns introduced by later revisions before Alembic advances.
    with op.batch_alter_table("cms_content_relations") as batch:
        batch.drop_column("configuration")
        batch.drop_column("sort_order")
    with op.batch_alter_table("cms_media_assets") as batch:
        batch.drop_constraint(
            "fk_cms_media_assets_replacement_of_media_id_cms_media_assets",
            type_="foreignkey",
        )
        batch.drop_column("scan_status")
        batch.drop_column("replacement_of_media_id")
        batch.drop_column("version")
        batch.drop_column("description")
        batch.drop_column("title")
    with op.batch_alter_table("cms_background_jobs") as batch:
        batch.drop_index("ix_cms_background_jobs_organization_id")
        batch.drop_constraint(
            "fk_cms_background_jobs_organization_id_organizations", type_="foreignkey"
        )
        batch.drop_column("organization_id")
        batch.drop_column("cancelled_at")
        batch.drop_column("retry_count")
    with op.batch_alter_table("cms_feature_flags") as batch:
        batch.drop_column("starts_at")


def downgrade() -> None:
    bind = op.get_bind()
    for table in reversed(TABLES):
        table.drop(bind=bind, checkfirst=True)
