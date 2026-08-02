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


class Mission(UUIDPrimaryKey, Timestamped, Base):
    __tablename__ = "missions"

    stable_key: Mapped[str] = mapped_column(String(120), unique=True)
    title: Mapped[str] = mapped_column(String(220))
    description: Mapped[str] = mapped_column(Text)
    safety_classification: Mapped[str] = mapped_column(String(60))


class MissionVersion(UUIDPrimaryKey, Timestamped, Base):
    __tablename__ = "mission_versions"
    __table_args__ = (UniqueConstraint("mission_id", "version"),)

    mission_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("missions.id", ondelete="CASCADE"))
    version: Mapped[str] = mapped_column(String(40))
    fictional_organization: Mapped[str] = mapped_column(String(200))
    business_context: Mapped[str] = mapped_column(Text)
    briefing: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(30), default="draft")
    evidence_manifest: Mapped[list[dict[str, Any]]] = mapped_column(JSON)
    evaluator_version: Mapped[str] = mapped_column(String(40))


class MissionStage(UUIDPrimaryKey, Timestamped, Base):
    __tablename__ = "mission_stages"
    __table_args__ = (UniqueConstraint("mission_version_id", "position"),)

    mission_version_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("mission_versions.id", ondelete="CASCADE")
    )
    position: Mapped[int] = mapped_column(Integer)
    stable_key: Mapped[str] = mapped_column(String(100))
    title: Mapped[str] = mapped_column(String(180))
    objective: Mapped[str] = mapped_column(Text)


class MissionObjective(UUIDPrimaryKey, Timestamped, Base):
    __tablename__ = "mission_objectives"

    mission_stage_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("mission_stages.id", ondelete="CASCADE")
    )
    stable_key: Mapped[str] = mapped_column(String(120))
    description: Mapped[str] = mapped_column(Text)
    required: Mapped[bool] = mapped_column(Boolean, default=True)
    skill_key: Mapped[str] = mapped_column(String(100))


class MissionSession(UUIDPrimaryKey, Timestamped, Base):
    __tablename__ = "mission_sessions"
    __table_args__ = (
        Index("ix_mission_session_owner", "organization_id", "user_id", "created_at"),
    )

    organization_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE")
    )
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    mission_version_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("mission_versions.id", ondelete="RESTRICT")
    )
    current_stage_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("mission_stages.id", ondelete="RESTRICT")
    )
    status: Mapped[str] = mapped_column(String(30), default="active")
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    version: Mapped[int] = mapped_column(Integer, default=1)


class MissionAction(UUIDPrimaryKey, Base):
    __tablename__ = "mission_actions"
    __table_args__ = (Index("ix_mission_action_timeline", "mission_session_id", "sequence"),)

    organization_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="RESTRICT")
    )
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"))
    mission_session_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("mission_sessions.id", ondelete="RESTRICT")
    )
    stage_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("mission_stages.id", ondelete="RESTRICT")
    )
    sequence: Mapped[int] = mapped_column(Integer)
    action_type: Mapped[str] = mapped_column(String(60))
    resource_id: Mapped[str | None] = mapped_column(String(160))
    learner_input: Mapped[str | None] = mapped_column(Text)
    outcome: Mapped[str] = mapped_column(String(40))
    duration_seconds: Mapped[int | None] = mapped_column(Integer)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class MissionHintUse(UUIDPrimaryKey, Base):
    __tablename__ = "mission_hint_uses"

    organization_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="RESTRICT"), index=True
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), index=True
    )
    mission_session_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("mission_sessions.id", ondelete="RESTRICT")
    )
    stage_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("mission_stages.id", ondelete="RESTRICT")
    )
    level: Mapped[int] = mapped_column(Integer)
    hint_type: Mapped[str] = mapped_column(String(50))
    used_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class MissionEvidence(UUIDPrimaryKey, Base):
    __tablename__ = "mission_evidence"
    __table_args__ = (UniqueConstraint("mission_session_id", "evidence_key"),)

    organization_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="RESTRICT"), index=True
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), index=True
    )
    mission_session_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("mission_sessions.id", ondelete="RESTRICT")
    )
    evidence_key: Mapped[str] = mapped_column(String(120))
    classification: Mapped[str] = mapped_column(String(40))
    opened_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class MissionSubmission(UUIDPrimaryKey, Timestamped, Base):
    __tablename__ = "mission_submissions"

    organization_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="RESTRICT"), index=True
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), index=True
    )
    mission_session_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("mission_sessions.id", ondelete="RESTRICT")
    )
    report_body: Mapped[str] = mapped_column(Text)
    learner_authored: Mapped[bool] = mapped_column(Boolean, default=True)
    submitted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    version: Mapped[int] = mapped_column(Integer, default=1)


class MissionResult(UUIDPrimaryKey, Base):
    __tablename__ = "mission_results"

    organization_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="RESTRICT"), index=True
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), index=True
    )
    mission_session_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("mission_sessions.id", ondelete="RESTRICT"), unique=True
    )
    passed: Mapped[bool] = mapped_column(Boolean)
    conceptual_score: Mapped[float] = mapped_column(Float)
    practical_score: Mapped[float] = mapped_column(Float)
    decision_score: Mapped[float] = mapped_column(Float)
    independence_score: Mapped[float] = mapped_column(Float)
    reporting_score: Mapped[float] = mapped_column(Float)
    evaluator_version: Mapped[str] = mapped_column(String(40))
    evaluated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class InvestigationReplay(UUIDPrimaryKey, Base):
    __tablename__ = "investigation_replays"

    organization_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="RESTRICT"), index=True
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), index=True
    )
    mission_session_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("mission_sessions.id", ondelete="RESTRICT"), unique=True
    )
    timeline: Mapped[list[dict[str, Any]]] = mapped_column(JSON)
    turning_points: Mapped[list[dict[str, Any]]] = mapped_column(JSON)
    missed_evidence: Mapped[list[str]] = mapped_column(JSON)
    alternate_approaches: Mapped[list[str]] = mapped_column(JSON)
    generated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    generator_version: Mapped[str] = mapped_column(String(40))
