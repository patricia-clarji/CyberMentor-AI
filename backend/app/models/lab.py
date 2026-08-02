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


class LabSession(UUIDPrimaryKey, Timestamped, Base):
    __tablename__ = "lab_sessions"
    __table_args__ = (
        Index("ix_lab_session_owner_status", "organization_id", "user_id", "status"),
        UniqueConstraint(
            "organization_id",
            "user_id",
            "lab_id",
            "active_key",
        ),
    )

    organization_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), index=True
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    lab_id: Mapped[str] = mapped_column(String(160))
    lab_version: Mapped[str] = mapped_column(String(40))
    status: Mapped[str] = mapped_column(String(30), default="active")
    active_key: Mapped[str | None] = mapped_column(String(20), default="active")
    current_stage: Mapped[int] = mapped_column(Integer, default=1)
    cwd: Mapped[str] = mapped_column(String(500))
    filesystem_state: Mapped[list[dict[str, Any]]] = mapped_column(JSON)
    objective_state: Mapped[dict[str, Any]] = mapped_column(JSON)
    score_components: Mapped[dict[str, Any]] = mapped_column(JSON)
    notes: Mapped[str] = mapped_column(Text, default="")
    hints_used: Mapped[int] = mapped_column(Integer, default=0)
    command_count: Mapped[int] = mapped_column(Integer, default=0)
    incorrect_command_count: Mapped[int] = mapped_column(Integer, default=0)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    last_activity_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    final_submission: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    outcome: Mapped[str | None] = mapped_column(String(30))
    version: Mapped[int] = mapped_column(Integer, default=1)


class LabAction(UUIDPrimaryKey, Base):
    __tablename__ = "lab_actions"
    __table_args__ = (
        UniqueConstraint("session_id", "sequence"),
        Index("ix_lab_action_owner_time", "organization_id", "user_id", "occurred_at"),
    )

    organization_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), index=True
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    session_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("lab_sessions.id", ondelete="CASCADE"), index=True
    )
    sequence: Mapped[int] = mapped_column(Integer)
    action_type: Mapped[str] = mapped_column(String(40))
    input_text: Mapped[str | None] = mapped_column(Text)
    output_text: Mapped[str | None] = mapped_column(Text)
    successful: Mapped[bool] = mapped_column(Boolean)
    mistake: Mapped[bool] = mapped_column(Boolean, default=False)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    elapsed_seconds: Mapped[int] = mapped_column(Integer)


class LabSubmission(UUIDPrimaryKey, Timestamped, Base):
    __tablename__ = "lab_submissions"

    organization_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), index=True
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    session_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("lab_sessions.id", ondelete="CASCADE"), index=True
    )
    idempotency_key: Mapped[str] = mapped_column(String(120))
    response: Mapped[dict[str, Any]] = mapped_column(JSON)
    correctness: Mapped[float] = mapped_column(Float)
    efficiency: Mapped[float] = mapped_column(Float)
    evidence_quality: Mapped[float] = mapped_column(Float)
    independence: Mapped[float] = mapped_column(Float)
    decision_quality: Mapped[float] = mapped_column(Float)
    report_quality: Mapped[float] = mapped_column(Float)
    overall_band: Mapped[str] = mapped_column(String(30))
    passed: Mapped[bool] = mapped_column(Boolean)
    feedback: Mapped[list[str]] = mapped_column(JSON)
    evaluator_version: Mapped[str] = mapped_column(String(40))
    submitted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))

    __table_args__ = (
        Index("ix_lab_submission_owner", "organization_id", "user_id", "submitted_at"),
        UniqueConstraint("session_id", "idempotency_key"),
    )
