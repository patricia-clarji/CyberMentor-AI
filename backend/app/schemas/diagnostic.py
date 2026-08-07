import uuid
from typing import Any

from pydantic import BaseModel, Field


class DiagnosticQuestionResponse(BaseModel):
    id: uuid.UUID
    question_type: str
    prompt: str
    options: list[str]
    skill_key: str
    position: int
    total: int


class DiagnosticStartResponse(BaseModel):
    attempt_id: uuid.UUID
    profile_version: str
    question: DiagnosticQuestionResponse


class DiagnosticStartRequest(BaseModel):
    self_assessment_text: str | None = Field(default=None, max_length=4000)


class DiagnosticAnswerRequest(BaseModel):
    response: dict[str, Any] = Field(default_factory=dict)


class DiagnosticAnswerResponse(BaseModel):
    correct: bool
    explanation: str
    confidence_notice: str
    completed: bool
    next_question: DiagnosticQuestionResponse | None
    roadmap_updated: bool
