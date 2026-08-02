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


class Assessment(UUIDPrimaryKey, Timestamped, Base):
    __tablename__ = "assessments"

    stable_key: Mapped[str] = mapped_column(String(120), unique=True)
    title: Mapped[str] = mapped_column(String(200))
    purpose: Mapped[str] = mapped_column(String(40))
    publication_id: Mapped[str | None] = mapped_column(String(160))


class AssessmentVersion(UUIDPrimaryKey, Timestamped, Base):
    __tablename__ = "assessment_versions"
    __table_args__ = (UniqueConstraint("assessment_id", "version"),)

    assessment_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("assessments.id", ondelete="CASCADE")
    )
    version: Mapped[str] = mapped_column(String(40))
    status: Mapped[str] = mapped_column(String(30), default="draft")
    instructions: Mapped[str] = mapped_column(Text)
    time_limit_seconds: Mapped[int | None] = mapped_column(Integer)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class Question(UUIDPrimaryKey, Timestamped, Base):
    __tablename__ = "questions"

    stable_key: Mapped[str] = mapped_column(String(140), unique=True)
    assessment_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("assessments.id", ondelete="CASCADE")
    )
    skill_key: Mapped[str] = mapped_column(String(100), index=True)
    question_type: Mapped[str] = mapped_column(String(50))


class QuestionVersion(UUIDPrimaryKey, Timestamped, Base):
    __tablename__ = "question_versions"
    __table_args__ = (UniqueConstraint("question_id", "version"),)

    question_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("questions.id", ondelete="CASCADE"))
    version: Mapped[str] = mapped_column(String(40))
    prompt: Mapped[str] = mapped_column(Text)
    options: Mapped[list[str] | None] = mapped_column(JSON)
    private_answer: Mapped[dict[str, Any]] = mapped_column(JSON)
    explanation: Mapped[str] = mapped_column(Text)
    difficulty: Mapped[str] = mapped_column(String(30))
    published: Mapped[bool] = mapped_column(Boolean, default=False)


class AssessmentAttempt(UUIDPrimaryKey, Timestamped, Base):
    __tablename__ = "assessment_attempts"
    __table_args__ = (
        Index("ix_assessment_attempt_owner", "organization_id", "user_id", "created_at"),
    )

    organization_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE")
    )
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    assessment_version_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("assessment_versions.id", ondelete="RESTRICT")
    )
    status: Mapped[str] = mapped_column(String(30), default="started")
    score: Mapped[float | None] = mapped_column(Float)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class QuestionResponse(UUIDPrimaryKey, Timestamped, Base):
    __tablename__ = "question_responses"
    __table_args__ = (UniqueConstraint("attempt_id", "question_version_id"),)

    organization_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), index=True
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    attempt_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("assessment_attempts.id", ondelete="CASCADE")
    )
    question_version_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("question_versions.id", ondelete="RESTRICT")
    )
    response: Mapped[dict[str, Any]] = mapped_column(JSON)
    correct: Mapped[bool | None] = mapped_column(Boolean)
    score: Mapped[float | None] = mapped_column(Float)
    attempts: Mapped[int] = mapped_column(Integer, default=1)
    hints_used: Mapped[int] = mapped_column(Integer, default=0)
    evaluator_version: Mapped[str] = mapped_column(String(40))
