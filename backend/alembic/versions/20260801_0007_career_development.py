"""Add verified professional development records.

Revision ID: 20260801_0007
Revises: 20260801_0006
"""

from collections.abc import Sequence

from alembic import op

from app.models.career import (
    CareerAchievement,
    CareerCertificate,
    CareerRecruiterAccess,
    CareerRoleDefinition,
    CareerTimelineEvent,
    LearnerReflection,
    ProfessionalProfile,
)

revision: str = "20260801_0007"
down_revision: str | None = "20260801_0006"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

TABLES = [
    ProfessionalProfile.__table__,
    LearnerReflection.__table__,
    CareerTimelineEvent.__table__,
    CareerCertificate.__table__,
    CareerRoleDefinition.__table__,
    CareerAchievement.__table__,
    CareerRecruiterAccess.__table__,
]


def upgrade() -> None:
    bind = op.get_bind()
    for table in TABLES:
        table.create(bind, checkfirst=False)


def downgrade() -> None:
    bind = op.get_bind()
    for table in reversed(TABLES):
        table.drop(bind, checkfirst=True)
