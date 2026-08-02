import uuid
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field


class MentorThreadRequest(BaseModel):
    context_type: Literal[
        "general",
        "course",
        "lesson",
        "mission",
        "lab",
        "assessment",
        "project",
    ] = "general"
    context_id: str | None = Field(default=None, max_length=160)


class MentorThreadResponse(BaseModel):
    id: uuid.UUID
    context_type: str
    context_id: str | None
    status: str


class MentorQuestionRequest(BaseModel):
    question: str = Field(min_length=1, max_length=4000)


class MentorCitation(BaseModel):
    publication_id: str
    publication_version: str
    chunk_id: str
    title: str
    publisher: str
    url: str
    verification_status: Literal["verified"]


class MentorAnswerResponse(BaseModel):
    thread_id: uuid.UUID
    message_id: uuid.UUID
    answer: str
    mode: Literal["live_grounded", "deterministic_fallback", "policy_refusal"]
    mentor_mode: Literal[
        "teaching",
        "explanation",
        "guided_practice",
        "socratic",
        "hint",
        "reflection",
        "investigation",
        "review",
        "assessment_support",
        "safety_redirect",
        "human_review_recommendation",
    ]
    intervention: str
    provider_generated: bool
    blocked: bool
    citations: list[MentorCitation]
    reasoning_summary: str
    related_skills: list[str]
    recommended_next_action: dict[str, Any] | None
    detected_misconceptions: list[str]
    limitation_notice: str
    prompt_version: str
    retrieval_version: str
    provider: str
    model: str
    latency_ms: int


class MentorHistoryMessage(BaseModel):
    id: uuid.UUID
    role: Literal["user", "assistant"]
    body: str
    delivery_mode: str
    mentor_mode: str
    provider_generated: bool
    reasoning_summary: str | None
    related_skills: list[str]
    recommended_action: dict[str, Any] | None
    created_at: datetime


class MentorThreadHistoryResponse(BaseModel):
    thread: MentorThreadResponse
    messages: list[MentorHistoryMessage]


class MentorFeedbackRequest(BaseModel):
    rating: Literal["helpful", "not_helpful"]
    issue_tags: list[
        Literal[
            "unclear",
            "too_basic",
            "too_advanced",
            "not_grounded",
            "unsafe",
            "answer_leakage",
            "other",
        ]
    ] = Field(default_factory=list, max_length=5)
    comment: str | None = Field(default=None, max_length=1000)


class MentorFeedbackResponse(BaseModel):
    message_id: uuid.UUID
    rating: str
    saved: bool


class MentorLearnerModelResponse(BaseModel):
    weak_skills: list[str]
    strong_skills: list[str]
    misconceptions: list[dict[str, Any]]
    completed_labs: list[str]
    completed_missions: int
    hint_history: list[dict[str, Any]]
    preferred_explanations: list[str]
    learning_pace: str
    confidence_estimate: float
    independence: float
    recent_failures: list[dict[str, Any]]
    recent_improvements: list[dict[str, Any]]
    study_streak: int
    review_schedule: list[dict[str, Any]]
