"""Add organization portals, cohorts, assignments, reviews, notifications, and sharing.

Revision ID: 20260730_0005
Revises: 20260730_0004
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

from app.models.operations import (
    Assignment,
    AssignmentReview,
    AssignmentSubmission,
    Cohort,
    CohortCurriculum,
    CohortEnrollment,
    CohortStaff,
    EvidenceRequest,
    LearnerAssignment,
    MembershipHistory,
    Notification,
    OrganizationInvitation,
    Programme,
    ReportExport,
    SharedEvidenceItem,
    SharedProfile,
    SharedProfileAccess,
)

revision: str = "20260730_0005"
down_revision: str | None = "20260730_0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

OPERATION_TABLES = [
    OrganizationInvitation.__table__,
    MembershipHistory.__table__,
    Programme.__table__,
    Cohort.__table__,
    CohortStaff.__table__,
    CohortEnrollment.__table__,
    CohortCurriculum.__table__,
    Assignment.__table__,
    LearnerAssignment.__table__,
    AssignmentSubmission.__table__,
    AssignmentReview.__table__,
    Notification.__table__,
    SharedProfile.__table__,
    SharedEvidenceItem.__table__,
    SharedProfileAccess.__table__,
    EvidenceRequest.__table__,
    ReportExport.__table__,
]


def upgrade() -> None:
    with op.batch_alter_table("organizations") as batch:
        batch.add_column(sa.Column("metadata_json", sa.JSON(), nullable=False, server_default="{}"))
        batch.add_column(sa.Column("settings", sa.JSON(), nullable=False, server_default="{}"))
        batch.add_column(
            sa.Column("status", sa.String(30), nullable=False, server_default="active")
        )
        batch.add_column(sa.Column("archived_at", sa.DateTime(timezone=True)))
        batch.add_column(sa.Column("version", sa.Integer(), nullable=False, server_default="1"))
    bind = op.get_bind()
    for table in OPERATION_TABLES:
        table.create(bind, checkfirst=False)


def downgrade() -> None:
    bind = op.get_bind()
    for table in reversed(OPERATION_TABLES):
        table.drop(bind, checkfirst=True)
    with op.batch_alter_table("organizations") as batch:
        batch.drop_column("version")
        batch.drop_column("archived_at")
        batch.drop_column("status")
        batch.drop_column("settings")
        batch.drop_column("metadata_json")
