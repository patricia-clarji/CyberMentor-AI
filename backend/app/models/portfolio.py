import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, Timestamped, UUIDPrimaryKey


class Project(UUIDPrimaryKey, Timestamped, Base):
    __tablename__ = "projects"

    stable_key: Mapped[str] = mapped_column(String(120), unique=True)
    publication_id: Mapped[str | None] = mapped_column(String(160))
    title: Mapped[str] = mapped_column(String(220))
    description: Mapped[str] = mapped_column(Text)
    version: Mapped[str] = mapped_column(String(40))


class ProjectMilestone(UUIDPrimaryKey, Timestamped, Base):
    __tablename__ = "project_milestones"
    __table_args__ = (UniqueConstraint("project_id", "position"),)

    project_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"))
    position: Mapped[int] = mapped_column(Integer)
    title: Mapped[str] = mapped_column(String(180))
    requirement: Mapped[str] = mapped_column(Text)


class Rubric(UUIDPrimaryKey, Timestamped, Base):
    __tablename__ = "rubrics"

    project_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"))
    version: Mapped[str] = mapped_column(String(40))
    status: Mapped[str] = mapped_column(String(30), default="draft")
    __table_args__ = (UniqueConstraint("project_id", "version"),)


class RubricCriterion(UUIDPrimaryKey, Timestamped, Base):
    __tablename__ = "rubric_criteria"

    rubric_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("rubrics.id", ondelete="CASCADE"))
    stable_key: Mapped[str] = mapped_column(String(120))
    description: Mapped[str] = mapped_column(Text)
    weight: Mapped[float] = mapped_column(Float)
    pass_standard: Mapped[str] = mapped_column(Text)


class ProjectSubmission(UUIDPrimaryKey, Timestamped, Base):
    __tablename__ = "project_submissions"
    __table_args__ = (
        Index("ix_project_submission_owner", "organization_id", "user_id", "created_at"),
    )

    organization_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE")
    )
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    project_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("projects.id", ondelete="RESTRICT"))
    body: Mapped[str] = mapped_column(Text)
    reflection: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(30), default="submitted")
    submitted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    version: Mapped[int] = mapped_column(Integer, default=1)


class ProjectReview(UUIDPrimaryKey, Timestamped, Base):
    __tablename__ = "project_reviews"

    organization_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="RESTRICT"), index=True
    )
    submission_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("project_submissions.id", ondelete="RESTRICT")
    )
    reviewer_user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"))
    rubric_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("rubrics.id", ondelete="RESTRICT"))
    passed: Mapped[bool] = mapped_column(Boolean)
    criterion_results: Mapped[list[dict[str, Any]]] = mapped_column(JSON)
    feedback: Mapped[str] = mapped_column(Text)
    reviewed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class Portfolio(UUIDPrimaryKey, Timestamped, Base):
    __tablename__ = "portfolios"
    __table_args__ = (UniqueConstraint("organization_id", "user_id"),)

    organization_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE")
    )
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    visibility: Mapped[str] = mapped_column(String(30), default="private")


class PortfolioArtifact(UUIDPrimaryKey, Timestamped, Base):
    __tablename__ = "portfolio_artifacts"

    organization_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), index=True
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    portfolio_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("portfolios.id", ondelete="CASCADE"))
    artifact_type: Mapped[str] = mapped_column(String(40))
    source_id: Mapped[str] = mapped_column(String(160))
    source_version: Mapped[str | None] = mapped_column(String(40))
    title: Mapped[str] = mapped_column(String(220))
    verification_state: Mapped[str] = mapped_column(String(30))
    visibility: Mapped[str] = mapped_column(String(30), default="private")
    content: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class CompletionRecord(UUIDPrimaryKey, Timestamped, Base):
    __tablename__ = "completion_records"

    organization_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="RESTRICT"), index=True
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), index=True
    )
    verification_id: Mapped[str] = mapped_column(String(80), unique=True, index=True)
    criteria_version: Mapped[str] = mapped_column(String(40))
    scope_type: Mapped[str] = mapped_column(String(40))
    scope_id: Mapped[str] = mapped_column(String(160))
    skill_summary: Mapped[list[dict[str, Any]]] = mapped_column(JSON)
    evidence_summary: Mapped[list[dict[str, Any]]] = mapped_column(JSON)
    issued_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    revocation_reason: Mapped[str | None] = mapped_column(Text)
