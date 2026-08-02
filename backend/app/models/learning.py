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


class LearnerProfile(UUIDPrimaryKey, Timestamped, Base):
    __tablename__ = "learner_profiles"

    organization_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), index=True
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), unique=True
    )
    experience_level: Mapped[str | None] = mapped_column(String(40))
    weekly_minutes: Mapped[int | None] = mapped_column(Integer)
    networking_confidence: Mapped[int | None] = mapped_column(Integer)
    linux_confidence: Mapped[int | None] = mapped_column(Integer)
    investigation_confidence: Mapped[int | None] = mapped_column(Integer)
    accessibility_needs: Mapped[str | None] = mapped_column(Text)
    onboarding_completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    version: Mapped[int] = mapped_column(Integer, default=1)


class LearnerGoal(UUIDPrimaryKey, Timestamped, Base):
    __tablename__ = "learner_goals"
    __table_args__ = (UniqueConstraint("organization_id", "user_id", "goal_key"),)

    organization_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), index=True
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    goal_key: Mapped[str] = mapped_column(String(80))
    target_role: Mapped[str] = mapped_column(String(100))
    is_primary: Mapped[bool] = mapped_column(Boolean, default=False)


class LearnerPreference(UUIDPrimaryKey, Timestamped, Base):
    __tablename__ = "learner_preferences"
    __table_args__ = (UniqueConstraint("organization_id", "user_id", "preference_key"),)

    organization_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), index=True
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    preference_key: Mapped[str] = mapped_column(String(80))
    preference_value: Mapped[str] = mapped_column(String(500))


class Enrollment(UUIDPrimaryKey, Timestamped, Base):
    __tablename__ = "enrollments"
    __table_args__ = (UniqueConstraint("organization_id", "user_id", "course_publication_id"),)

    organization_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), index=True
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    course_publication_id: Mapped[str] = mapped_column(String(160))
    status: Mapped[str] = mapped_column(String(32), default="active")
    enrolled_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class LessonProgress(UUIDPrimaryKey, Timestamped, Base):
    __tablename__ = "lesson_progress"
    __table_args__ = (UniqueConstraint("organization_id", "user_id", "lesson_publication_id"),)

    organization_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), index=True
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    lesson_publication_id: Mapped[str] = mapped_column(String(160))
    lesson_version: Mapped[str] = mapped_column(String(40))
    status: Mapped[str] = mapped_column(String(32), default="started")
    percent_complete: Mapped[int] = mapped_column(Integer, default=0)
    last_position: Mapped[str | None] = mapped_column(String(160))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    version: Mapped[int] = mapped_column(Integer, default=1)


class LearningActivityAttempt(UUIDPrimaryKey, Timestamped, Base):
    __tablename__ = "learning_activity_attempts"
    __table_args__ = (
        Index(
            "ix_learning_activity_attempt_owner",
            "organization_id",
            "user_id",
            "activity_id",
        ),
        UniqueConstraint("organization_id", "user_id", "idempotency_key"),
    )

    organization_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), index=True
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    activity_id: Mapped[str] = mapped_column(String(160))
    activity_version: Mapped[str] = mapped_column(String(40))
    activity_type: Mapped[str] = mapped_column(String(50))
    module_id: Mapped[str] = mapped_column(String(160))
    response: Mapped[dict[str, Any]] = mapped_column(JSON)
    score: Mapped[float] = mapped_column(Float)
    passed: Mapped[bool] = mapped_column(Boolean)
    hints_used: Mapped[int] = mapped_column(Integer, default=0)
    evaluator: Mapped[str] = mapped_column(String(60))
    feedback: Mapped[str] = mapped_column(Text)
    idempotency_key: Mapped[str] = mapped_column(String(100))
    submitted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class LearnerNote(UUIDPrimaryKey, Timestamped, Base):
    __tablename__ = "learner_notes"
    __table_args__ = (
        Index("ix_notes_owner_lesson", "organization_id", "user_id", "lesson_publication_id"),
    )

    organization_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE")
    )
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    lesson_publication_id: Mapped[str] = mapped_column(String(160))
    body: Mapped[str] = mapped_column(Text)


class Bookmark(UUIDPrimaryKey, Timestamped, Base):
    __tablename__ = "bookmarks"
    __table_args__ = (
        UniqueConstraint("organization_id", "user_id", "resource_type", "resource_id"),
    )

    organization_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), index=True
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    resource_type: Mapped[str] = mapped_column(String(40))
    resource_id: Mapped[str] = mapped_column(String(160))


class LearningSession(UUIDPrimaryKey, Timestamped, Base):
    __tablename__ = "learning_sessions"
    __table_args__ = (
        Index("ix_learning_session_owner_start", "organization_id", "user_id", "started_at"),
    )

    organization_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE")
    )
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    activity_type: Mapped[str] = mapped_column(String(40))
    activity_id: Mapped[str] = mapped_column(String(160))
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class Skill(UUIDPrimaryKey, Timestamped, Base):
    __tablename__ = "skills"

    stable_key: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(160))
    description: Mapped[str] = mapped_column(Text)
    evidence_types: Mapped[list[str]] = mapped_column(JSON)
    minimum_evidence: Mapped[int] = mapped_column(Integer, default=3)
    recency_days: Mapped[int] = mapped_column(Integer, default=180)
    readiness_relevance: Mapped[float] = mapped_column(Float, default=0.0)
    profile_version: Mapped[str] = mapped_column(String(40))


class SkillDependency(Base):
    __tablename__ = "skill_dependencies"

    skill_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("skills.id", ondelete="CASCADE"), primary_key=True
    )
    prerequisite_skill_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("skills.id", ondelete="CASCADE"), primary_key=True
    )
    minimum_mastery: Mapped[float] = mapped_column(Float, default=0.6)


class LearnerSkillState(UUIDPrimaryKey, Timestamped, Base):
    __tablename__ = "learner_skill_states"
    __table_args__ = (UniqueConstraint("organization_id", "user_id", "skill_id"),)

    organization_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), index=True
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    skill_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("skills.id", ondelete="CASCADE"))
    mastery_estimate: Mapped[float] = mapped_column(Float, default=0.0)
    confidence: Mapped[float] = mapped_column(Float, default=0.0)
    evidence_strength: Mapped[float] = mapped_column(Float, default=0.0)
    independence: Mapped[float] = mapped_column(Float, default=0.0)
    reasoning_summary: Mapped[str] = mapped_column(Text, default="No evidence yet.")
    last_evaluated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    next_review_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    engine_version: Mapped[str] = mapped_column(String(40))
    version: Mapped[int] = mapped_column(Integer, default=1)


class SkillEvidence(UUIDPrimaryKey, Base):
    __tablename__ = "skill_evidence"
    __table_args__ = (
        Index("ix_skill_evidence_owner_time", "organization_id", "user_id", "occurred_at"),
    )

    organization_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="RESTRICT")
    )
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"))
    skill_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("skills.id", ondelete="RESTRICT"))
    source_type: Mapped[str] = mapped_column(String(40))
    source_id: Mapped[str] = mapped_column(String(160))
    source_version: Mapped[str] = mapped_column(String(40))
    score: Mapped[float] = mapped_column(Float)
    independence: Mapped[float] = mapped_column(Float)
    hints_used: Mapped[int] = mapped_column(Integer, default=0)
    attempts: Mapped[int] = mapped_column(Integer, default=1)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    provenance_hash: Mapped[str] = mapped_column(String(64), unique=True)


class Misconception(UUIDPrimaryKey, Timestamped, Base):
    __tablename__ = "misconceptions"

    stable_key: Mapped[str] = mapped_column(String(120), unique=True)
    skill_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("skills.id", ondelete="CASCADE"))
    description: Mapped[str] = mapped_column(Text)


class LearnerMisconception(UUIDPrimaryKey, Timestamped, Base):
    __tablename__ = "learner_misconceptions"
    __table_args__ = (UniqueConstraint("organization_id", "user_id", "misconception_id"),)

    organization_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE")
    )
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    misconception_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("misconceptions.id", ondelete="CASCADE")
    )
    evidence_count: Mapped[int] = mapped_column(Integer, default=1)
    confidence: Mapped[float] = mapped_column(Float, default=0.35)
    status: Mapped[str] = mapped_column(String(30), default="suspected")
    first_observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    last_observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    supporting_evidence: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class Recommendation(UUIDPrimaryKey, Timestamped, Base):
    __tablename__ = "recommendations"
    __table_args__ = (
        Index("ix_recommendation_owner_status", "organization_id", "user_id", "status"),
    )

    organization_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE")
    )
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    activity_type: Mapped[str] = mapped_column(String(40))
    activity_id: Mapped[str] = mapped_column(String(160))
    reason: Mapped[str] = mapped_column(Text)
    intervention_type: Mapped[str] = mapped_column(String(60))
    required: Mapped[bool] = mapped_column(Boolean, default=False)
    status: Mapped[str] = mapped_column(String(30), default="active")
    engine_version: Mapped[str] = mapped_column(String(40))


class RecommendationDecision(UUIDPrimaryKey, Base):
    __tablename__ = "recommendation_decisions"

    organization_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="RESTRICT"), index=True
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), index=True
    )
    recommendation_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("recommendations.id", ondelete="RESTRICT")
    )
    decision: Mapped[str] = mapped_column(String(40))
    reason: Mapped[str | None] = mapped_column(Text)
    decided_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class DiagnosticAttempt(UUIDPrimaryKey, Timestamped, Base):
    __tablename__ = "diagnostic_attempts"
    __table_args__ = (
        Index("ix_diagnostic_owner_started", "organization_id", "user_id", "created_at"),
    )

    organization_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE")
    )
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    assessment_version_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("assessment_versions.id", ondelete="RESTRICT")
    )
    assessment_attempt_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("assessment_attempts.id", ondelete="CASCADE"), unique=True
    )
    status: Mapped[str] = mapped_column(String(30), default="started")
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
