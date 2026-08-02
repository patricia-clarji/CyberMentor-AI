import uuid
from datetime import date, datetime
from typing import Any

from sqlalchemy import (
    JSON,
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, Timestamped, UUIDPrimaryKey


class OrganizationInvitation(UUIDPrimaryKey, Timestamped, Base):
    __tablename__ = "organization_invitations"
    __table_args__ = (
        Index("ix_invitation_org_status", "organization_id", "status"),
        Index("ix_invitation_email_status", "email", "status"),
    )

    organization_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE")
    )
    email: Mapped[str] = mapped_column(String(320))
    role_key: Mapped[str] = mapped_column(String(64))
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    status: Mapped[str] = mapped_column(String(30), default="pending")
    invited_by_user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT")
    )
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    responded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class MembershipHistory(UUIDPrimaryKey, Base):
    __tablename__ = "membership_history"
    __table_args__ = (Index("ix_membership_history_org_time", "organization_id", "created_at"),)

    organization_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE")
    )
    membership_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("organization_memberships.id", ondelete="CASCADE")
    )
    actor_user_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL")
    )
    action: Mapped[str] = mapped_column(String(60))
    role_key: Mapped[str | None] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class Programme(UUIDPrimaryKey, Timestamped, Base):
    __tablename__ = "programmes"
    __table_args__ = (UniqueConstraint("organization_id", "stable_key"),)

    organization_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), index=True
    )
    stable_key: Mapped[str] = mapped_column(String(120))
    name: Mapped[str] = mapped_column(String(180))
    description: Mapped[str] = mapped_column(Text)
    academic_period: Mapped[str | None] = mapped_column(String(100))
    qualification_label: Mapped[str | None] = mapped_column(String(160))
    required_pathways: Mapped[list[str]] = mapped_column(JSON, default=list)
    elective_pathways: Mapped[list[str]] = mapped_column(JSON, default=list)
    required_projects: Mapped[list[str]] = mapped_column(JSON, default=list)
    completion_policy: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    staff_user_ids: Mapped[list[str]] = mapped_column(JSON, default=list)
    status: Mapped[str] = mapped_column(String(30), default="draft")
    created_by_user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT")
    )
    version: Mapped[int] = mapped_column(Integer, default=1)


class Cohort(UUIDPrimaryKey, Timestamped, Base):
    __tablename__ = "cohorts"
    __table_args__ = (
        UniqueConstraint("organization_id", "stable_key"),
        Index("ix_cohort_org_status", "organization_id", "status"),
    )

    organization_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE")
    )
    programme_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("programmes.id", ondelete="SET NULL")
    )
    stable_key: Mapped[str] = mapped_column(String(120))
    name: Mapped[str] = mapped_column(String(180))
    description: Mapped[str] = mapped_column(Text)
    cohort_type: Mapped[str] = mapped_column(String(40))
    start_date: Mapped[date] = mapped_column(Date)
    end_date: Mapped[date | None] = mapped_column(Date)
    status: Mapped[str] = mapped_column(String(30), default="active")
    completion_expectations: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    visibility_rules: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    self_enrolment_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    created_by_user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT")
    )
    version: Mapped[int] = mapped_column(Integer, default=1)


class CohortStaff(Base):
    __tablename__ = "cohort_staff"

    cohort_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("cohorts.id", ondelete="CASCADE"), primary_key=True
    )
    membership_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("organization_memberships.id", ondelete="CASCADE"), primary_key=True
    )
    role: Mapped[str] = mapped_column(String(40))
    assigned_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class CohortEnrollment(UUIDPrimaryKey, Timestamped, Base):
    __tablename__ = "cohort_enrollments"
    __table_args__ = (
        UniqueConstraint("cohort_id", "learner_user_id"),
        Index("ix_enrollment_org_status", "organization_id", "status"),
    )

    organization_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE")
    )
    cohort_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("cohorts.id", ondelete="CASCADE"))
    learner_user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"))
    status: Mapped[str] = mapped_column(String(30), default="active")
    enrolled_by_user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT")
    )
    left_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class CohortCurriculum(UUIDPrimaryKey, Timestamped, Base):
    __tablename__ = "cohort_curriculum"
    __table_args__ = (
        UniqueConstraint("cohort_id", "content_type", "content_id", "content_version"),
    )

    organization_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE")
    )
    cohort_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("cohorts.id", ondelete="CASCADE"))
    content_type: Mapped[str] = mapped_column(String(40))
    content_id: Mapped[str] = mapped_column(String(160))
    content_version: Mapped[str] = mapped_column(String(40))
    due_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    assigned_by_user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT")
    )


class Assignment(UUIDPrimaryKey, Timestamped, Base):
    __tablename__ = "assignments"
    __table_args__ = (Index("ix_assignment_org_status_due", "organization_id", "status", "due_at"),)

    organization_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE")
    )
    cohort_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("cohorts.id", ondelete="SET NULL")
    )
    title: Mapped[str] = mapped_column(String(220))
    instructions: Mapped[str] = mapped_column(Text)
    assignment_type: Mapped[str] = mapped_column(String(40))
    content_id: Mapped[str] = mapped_column(String(160))
    content_version: Mapped[str] = mapped_column(String(40))
    release_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    due_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    late_policy: Mapped[str | None] = mapped_column(Text)
    completion_criteria: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    grading_method: Mapped[str] = mapped_column(String(40), default="completion")
    review_required: Mapped[bool] = mapped_column(Boolean, default=False)
    visibility: Mapped[str] = mapped_column(String(30), default="assigned")
    status: Mapped[str] = mapped_column(String(30), default="draft")
    created_by_user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT")
    )
    version: Mapped[int] = mapped_column(Integer, default=1)


class LearnerAssignment(UUIDPrimaryKey, Timestamped, Base):
    __tablename__ = "learner_assignments"
    __table_args__ = (UniqueConstraint("assignment_id", "learner_user_id"),)

    organization_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), index=True
    )
    assignment_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("assignments.id", ondelete="CASCADE")
    )
    learner_user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"))
    status: Mapped[str] = mapped_column(String(30), default="assigned")
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class AssignmentSubmission(UUIDPrimaryKey, Timestamped, Base):
    __tablename__ = "assignment_submissions"
    __table_args__ = (
        UniqueConstraint("assignment_id", "learner_user_id", "revision"),
        Index("ix_assignment_submission_org_status", "organization_id", "status"),
    )

    organization_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE")
    )
    assignment_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("assignments.id", ondelete="RESTRICT")
    )
    learner_user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"))
    parent_submission_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("assignment_submissions.id", ondelete="RESTRICT")
    )
    body: Mapped[str] = mapped_column(Text)
    evidence_items: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list)
    revision: Mapped[int] = mapped_column(Integer, default=1)
    status: Mapped[str] = mapped_column(String(30), default="pending")
    submitted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class AssignmentReview(UUIDPrimaryKey, Timestamped, Base):
    __tablename__ = "assignment_reviews"
    __table_args__ = (Index("ix_assignment_review_org_state", "organization_id", "state"),)

    organization_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="RESTRICT")
    )
    submission_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("assignment_submissions.id", ondelete="RESTRICT")
    )
    learner_user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"))
    reviewer_user_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT")
    )
    content_version: Mapped[str] = mapped_column(String(40))
    state: Mapped[str] = mapped_column(String(30), default="pending")
    assigned_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    rubric: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list)
    rubric_scores: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list)
    feedback: Mapped[str | None] = mapped_column(Text)
    decision: Mapped[str | None] = mapped_column(String(30))
    revision_count: Mapped[int] = mapped_column(Integer, default=0)
    history: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list)
    ai_suggestions: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list)


class Notification(UUIDPrimaryKey, Timestamped, Base):
    __tablename__ = "notifications"
    __table_args__ = (Index("ix_notification_user_read", "user_id", "read_at"),)

    organization_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE")
    )
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    event_type: Mapped[str] = mapped_column(String(60))
    title: Mapped[str] = mapped_column(String(180))
    message: Mapped[str] = mapped_column(Text)
    deep_link: Mapped[str | None] = mapped_column(String(300))
    read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class SharedProfile(UUIDPrimaryKey, Timestamped, Base):
    __tablename__ = "shared_profiles"
    __table_args__ = (Index("ix_shared_profile_owner", "organization_id", "learner_user_id"),)

    organization_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE")
    )
    learner_user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    display_name: Mapped[str] = mapped_column(String(120))
    include_email: Mapped[bool] = mapped_column(Boolean, default=False)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(String(30), default="active")


class SharedEvidenceItem(UUIDPrimaryKey, Timestamped, Base):
    __tablename__ = "shared_evidence_items"
    __table_args__ = (UniqueConstraint("shared_profile_id", "evidence_type", "evidence_id"),)

    organization_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE")
    )
    shared_profile_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("shared_profiles.id", ondelete="CASCADE")
    )
    evidence_type: Mapped[str] = mapped_column(String(40))
    evidence_id: Mapped[uuid.UUID] = mapped_column()


class SharedProfileAccess(UUIDPrimaryKey, Base):
    __tablename__ = "shared_profile_access"
    __table_args__ = (Index("ix_share_access_profile_time", "shared_profile_id", "accessed_at"),)

    shared_profile_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("shared_profiles.id", ondelete="CASCADE")
    )
    recruiter_user_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL")
    )
    action: Mapped[str] = mapped_column(String(40))
    accessed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    request_id: Mapped[str | None] = mapped_column(String(80))


class EvidenceRequest(UUIDPrimaryKey, Timestamped, Base):
    __tablename__ = "evidence_requests"

    organization_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE")
    )
    shared_profile_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("shared_profiles.id", ondelete="CASCADE")
    )
    requested_by_user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT")
    )
    message: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(30), default="pending")


class ReportExport(UUIDPrimaryKey, Base):
    __tablename__ = "report_exports"
    __table_args__ = (Index("ix_report_export_org_time", "organization_id", "generated_at"),)

    organization_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE")
    )
    generated_by_user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT")
    )
    report_type: Mapped[str] = mapped_column(String(60))
    filters: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    row_count: Mapped[int] = mapped_column(Integer)
    generated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
