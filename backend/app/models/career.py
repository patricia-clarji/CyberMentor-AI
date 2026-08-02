import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import (
    JSON,
    Boolean,
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


class ProfessionalProfile(UUIDPrimaryKey, Timestamped, Base):
    __tablename__ = "professional_profiles"
    __table_args__ = (UniqueConstraint("organization_id", "user_id"),)

    organization_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), index=True
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    headline: Mapped[str | None] = mapped_column(String(180))
    biography: Mapped[str | None] = mapped_column(Text)
    career_goals: Mapped[str | None] = mapped_column(Text)
    experience_level: Mapped[str | None] = mapped_column(String(40))
    current_education: Mapped[str | None] = mapped_column(String(220))
    university: Mapped[str | None] = mapped_column(String(220))
    degree: Mapped[str | None] = mapped_column(String(180))
    graduation_year: Mapped[int | None] = mapped_column(Integer)
    availability: Mapped[str | None] = mapped_column(String(80))
    preferred_locations: Mapped[list[str]] = mapped_column(JSON, default=list)
    remote_preference: Mapped[str | None] = mapped_column(String(40))
    timezone: Mapped[str | None] = mapped_column(String(80))
    domains: Mapped[list[str]] = mapped_column(JSON, default=list)
    technical_interests: Mapped[list[str]] = mapped_column(JSON, default=list)
    languages: Mapped[list[str]] = mapped_column(JSON, default=list)
    links: Mapped[dict[str, str]] = mapped_column(JSON, default=dict)
    employment_history: Mapped[list[dict[str, str]]] = mapped_column(JSON, default=list)
    privacy: Mapped[dict[str, str]] = mapped_column(JSON, default=dict)
    portfolio_visibility: Mapped[str] = mapped_column(String(30), default="private")
    public_slug: Mapped[str | None] = mapped_column(String(100), unique=True)
    version: Mapped[int] = mapped_column(Integer, default=1)


class LearnerReflection(UUIDPrimaryKey, Timestamped, Base):
    __tablename__ = "learner_reflections"
    __table_args__ = (
        Index(
            "ix_reflection_owner_source", "organization_id", "user_id", "source_type", "source_id"
        ),
    )

    organization_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE")
    )
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    source_type: Mapped[str] = mapped_column(String(50))
    source_id: Mapped[str] = mapped_column(String(160))
    learned: Mapped[str] = mapped_column(Text)
    difficult: Mapped[str] = mapped_column(Text)
    improvement: Mapped[str] = mapped_column(Text)
    confidence: Mapped[int] = mapped_column(Integer)
    professional_application: Mapped[str] = mapped_column(Text)
    revision: Mapped[int] = mapped_column(Integer, default=1)


class CareerTimelineEvent(UUIDPrimaryKey, Base):
    __tablename__ = "career_timeline_events"
    __table_args__ = (
        Index("ix_career_timeline_owner_when", "organization_id", "user_id", "occurred_at"),
        UniqueConstraint("organization_id", "user_id", "event_key"),
    )

    organization_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="RESTRICT")
    )
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"))
    event_key: Mapped[str] = mapped_column(String(180))
    event_type: Mapped[str] = mapped_column(String(60))
    title: Mapped[str] = mapped_column(String(240))
    source_type: Mapped[str] = mapped_column(String(60))
    source_id: Mapped[str] = mapped_column(String(160))
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    summary: Mapped[str | None] = mapped_column(Text)


class CareerCertificate(UUIDPrimaryKey, Timestamped, Base):
    __tablename__ = "career_certificates"
    __table_args__ = (
        UniqueConstraint("certificate_id"),
        UniqueConstraint("organization_id", "completion_record_id"),
    )

    organization_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="RESTRICT"), index=True
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), index=True
    )
    completion_record_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("completion_records.id", ondelete="RESTRICT")
    )
    certificate_id: Mapped[str] = mapped_column(String(80), index=True)
    verification_code: Mapped[str] = mapped_column(String(80), unique=True, index=True)
    course_name: Mapped[str] = mapped_column(String(240))
    course_version: Mapped[str] = mapped_column(String(80))
    organization_name: Mapped[str] = mapped_column(String(240))
    issued_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(String(30), default="valid")
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    revocation_reason: Mapped[str | None] = mapped_column(Text)
    signature_hash: Mapped[str] = mapped_column(String(64))
    facts: Mapped[dict[str, Any]] = mapped_column(JSON)


class CareerRoleDefinition(UUIDPrimaryKey, Timestamped, Base):
    __tablename__ = "career_role_definitions"
    __table_args__ = (UniqueConstraint("organization_id", "key"),)

    organization_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), nullable=True
    )
    key: Mapped[str] = mapped_column(String(100))
    name: Mapped[str] = mapped_column(String(160))
    required_skills: Mapped[list[str]] = mapped_column(JSON)
    recommended_skills: Mapped[list[str]] = mapped_column(JSON, default=list)
    required_evidence: Mapped[list[str]] = mapped_column(JSON, default=list)
    recommended_projects: Mapped[list[str]] = mapped_column(JSON, default=list)
    version: Mapped[str] = mapped_column(String(40), default="1.0")


class CareerAchievement(UUIDPrimaryKey, Base):
    __tablename__ = "career_achievements"
    __table_args__ = (UniqueConstraint("organization_id", "user_id", "key"),)

    organization_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="RESTRICT")
    )
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"))
    key: Mapped[str] = mapped_column(String(100))
    title: Mapped[str] = mapped_column(String(180))
    source_type: Mapped[str] = mapped_column(String(60))
    source_id: Mapped[str] = mapped_column(String(160))
    earned_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class CareerRecruiterAccess(UUIDPrimaryKey, Timestamped, Base):
    __tablename__ = "career_recruiter_access"
    __table_args__ = (UniqueConstraint("organization_id", "learner_user_id", "recruiter_user_id"),)

    organization_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE")
    )
    learner_user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    recruiter_user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    active: Mapped[bool] = mapped_column(Boolean, default=True)
