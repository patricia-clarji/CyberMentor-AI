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


class MentorThread(UUIDPrimaryKey, Timestamped, Base):
    __tablename__ = "mentor_threads"

    organization_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), index=True
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    context_type: Mapped[str] = mapped_column(String(40))
    context_id: Mapped[str | None] = mapped_column(String(160))
    status: Mapped[str] = mapped_column(String(30), default="active")


class MentorLearnerMemory(UUIDPrimaryKey, Timestamped, Base):
    __tablename__ = "mentor_learner_memories"
    __table_args__ = (UniqueConstraint("organization_id", "user_id"),)

    organization_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), index=True
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    preferred_explanations: Mapped[list[str]] = mapped_column(JSON, default=list)
    learning_pace: Mapped[str] = mapped_column(String(30), default="standard")
    confidence_estimate: Mapped[float] = mapped_column(Float, default=0.0)
    independence_estimate: Mapped[float] = mapped_column(Float, default=0.0)
    recent_failures: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list)
    recent_improvements: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list)
    study_streak_days: Mapped[int] = mapped_column(Integer, default=0)
    review_schedule: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list)
    last_interaction_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    version: Mapped[int] = mapped_column(Integer, default=1)


class MentorMessage(UUIDPrimaryKey, Base):
    __tablename__ = "mentor_messages"
    __table_args__ = (Index("ix_mentor_message_thread_time", "thread_id", "created_at"),)

    organization_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="RESTRICT")
    )
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"))
    thread_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("mentor_threads.id", ondelete="CASCADE")
    )
    role: Mapped[str] = mapped_column(String(30))
    mode: Mapped[str] = mapped_column(String(50))
    mentor_mode: Mapped[str] = mapped_column(String(50), default="socratic")
    body: Mapped[str] = mapped_column(Text)
    provider_generated: Mapped[bool] = mapped_column(Boolean, default=False)
    prompt_version: Mapped[str] = mapped_column(String(40))
    retrieval_version: Mapped[str] = mapped_column(String(40), default="unknown")
    provider: Mapped[str] = mapped_column(String(60), default="deterministic")
    model_version: Mapped[str | None] = mapped_column(String(80))
    temperature: Mapped[float] = mapped_column(Float, default=0.0)
    prompt_tokens: Mapped[int] = mapped_column(Integer, default=0)
    completion_tokens: Mapped[int] = mapped_column(Integer, default=0)
    latency_ms: Mapped[int] = mapped_column(Integer, default=0)
    reasoning_summary: Mapped[str | None] = mapped_column(Text)
    related_skills: Mapped[list[str]] = mapped_column(JSON, default=list)
    recommended_action: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class MentorMessageFeedback(UUIDPrimaryKey, Timestamped, Base):
    __tablename__ = "mentor_message_feedback"
    __table_args__ = (UniqueConstraint("message_id", "user_id"),)

    organization_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), index=True
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    message_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("mentor_messages.id", ondelete="CASCADE"), index=True
    )
    rating: Mapped[str] = mapped_column(String(30))
    issue_tags: Mapped[list[str]] = mapped_column(JSON, default=list)
    comment: Mapped[str | None] = mapped_column(Text)


class MentorIntervention(UUIDPrimaryKey, Base):
    __tablename__ = "mentor_interventions"

    organization_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="RESTRICT"), index=True
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), index=True
    )
    thread_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("mentor_threads.id", ondelete="CASCADE")
    )
    trigger_type: Mapped[str] = mapped_column(String(60))
    selected_mode: Mapped[str] = mapped_column(String(50))
    rationale: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class RetrievalQuery(UUIDPrimaryKey, Base):
    __tablename__ = "retrieval_queries"

    organization_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="RESTRICT"), index=True
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), index=True
    )
    thread_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("mentor_threads.id", ondelete="CASCADE")
    )
    query_text: Mapped[str] = mapped_column(Text)
    scope: Mapped[dict[str, Any]] = mapped_column(JSON)
    index_version: Mapped[str] = mapped_column(String(40))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class RetrievalResult(UUIDPrimaryKey, Base):
    __tablename__ = "retrieval_results"

    retrieval_query_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("retrieval_queries.id", ondelete="CASCADE"), index=True
    )
    publication_id: Mapped[str] = mapped_column(String(160))
    publication_version: Mapped[str] = mapped_column(String(40))
    chunk_id: Mapped[str] = mapped_column(String(160))
    lexical_score: Mapped[float] = mapped_column(Float)
    vector_score: Mapped[float | None] = mapped_column(Float)
    hybrid_score: Mapped[float] = mapped_column(Float)
    rank: Mapped[int] = mapped_column(Integer)


class SafetyEvent(UUIDPrimaryKey, Base):
    __tablename__ = "safety_events"

    organization_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="RESTRICT"), index=True
    )
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), index=True
    )
    category: Mapped[str] = mapped_column(String(80))
    action: Mapped[str] = mapped_column(String(40))
    redacted_input_hash: Mapped[str] = mapped_column(String(64))
    policy_version: Mapped[str] = mapped_column(String(40))
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class AIUsageEvent(UUIDPrimaryKey, Base):
    __tablename__ = "ai_usage_events"

    organization_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="RESTRICT"), index=True
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), index=True
    )
    provider: Mapped[str] = mapped_column(String(60))
    model: Mapped[str] = mapped_column(String(100))
    prompt_version: Mapped[str] = mapped_column(String(40), default="unknown")
    retrieval_version: Mapped[str] = mapped_column(String(40), default="unknown")
    temperature: Mapped[float] = mapped_column(Float, default=0.0)
    prompt_tokens: Mapped[int] = mapped_column(Integer)
    completion_tokens: Mapped[int] = mapped_column(Integer)
    estimated_cost: Mapped[float] = mapped_column(Float)
    latency_ms: Mapped[int] = mapped_column(Integer)
    fallback_used: Mapped[bool] = mapped_column(Boolean)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class AIEvaluationCase(UUIDPrimaryKey, Timestamped, Base):
    __tablename__ = "ai_evaluation_cases"

    stable_key: Mapped[str] = mapped_column(String(140), unique=True)
    category: Mapped[str] = mapped_column(String(80))
    input_payload: Mapped[dict[str, Any]] = mapped_column(JSON)
    expected_policy: Mapped[dict[str, Any]] = mapped_column(JSON)
    reviewer_status: Mapped[str] = mapped_column(String(30), default="draft")


class AIEvaluationResult(UUIDPrimaryKey, Base):
    __tablename__ = "ai_evaluation_results"

    case_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("ai_evaluation_cases.id", ondelete="CASCADE")
    )
    provider: Mapped[str] = mapped_column(String(60))
    model: Mapped[str] = mapped_column(String(100))
    prompt_version: Mapped[str] = mapped_column(String(40))
    metrics: Mapped[dict[str, Any]] = mapped_column(JSON)
    passed: Mapped[bool] = mapped_column(Boolean)
    evaluated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
