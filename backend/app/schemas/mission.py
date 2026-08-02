import uuid
from typing import Any, Literal

from pydantic import BaseModel, Field


class MissionResourceSummary(BaseModel):
    id: str
    label: str
    classification: str
    opened: bool


class MissionActionChoice(BaseModel):
    id: str
    label: str


class MissionStageResponse(BaseModel):
    id: uuid.UUID
    key: str
    position: int
    total: int
    title: str
    objective: str
    resources: list[MissionResourceSummary]
    actions: list[MissionActionChoice]


class MissionStartResponse(BaseModel):
    session_id: uuid.UUID
    mission_key: str
    title: str
    fictional_organization: str
    business_context: str
    briefing: str
    safety_notice: str
    status: str
    stage: MissionStageResponse


class MissionActionRequest(BaseModel):
    action_type: Literal["open_evidence", "decision"]
    resource_id: str | None = Field(default=None, max_length=160)
    decision_id: str | None = Field(default=None, max_length=160)
    duration_seconds: int | None = Field(default=None, ge=0, le=86400)


class MissionActionResponse(BaseModel):
    outcome: Literal["observed", "correct", "mistake"]
    feedback: str
    status: str
    resource_content: str | None = None
    stage: MissionStageResponse


class MissionHintResponse(BaseModel):
    level: int
    hint: str
    independence_notice: str


class MissionSubmissionRequest(BaseModel):
    classification: Literal[
        "suspected_endpoint_compromise",
        "confirmed_enterprise_breach",
        "false_positive",
        "inconclusive",
    ]
    rationale: str = Field(min_length=120, max_length=4000)
    uncertainty: str = Field(min_length=20, max_length=1500)
    recommendation: Literal[
        "isolate_fin_14_with_approval",
        "no_action",
        "retaliate_against_source",
        "reset_all_accounts",
    ]
    next_steps: list[str] = Field(min_length=2, max_length=6)
    reflection: str = Field(min_length=40, max_length=2000)


class MissionScoresResponse(BaseModel):
    conceptual: float
    practical: float
    decision: float
    independence: float
    reporting: float


class MissionSubmissionResponse(BaseModel):
    passed: bool
    scores: MissionScoresResponse
    strengths: list[str]
    improvements: list[str]
    replay_id: uuid.UUID
    portfolio_artifact_id: uuid.UUID | None
    completion_verification_id: str | None
    scope_notice: str


class ReplayResponse(BaseModel):
    session_id: uuid.UUID
    timeline: list[dict[str, Any]]
    turning_points: list[dict[str, Any]]
    missed_evidence: list[str]
    alternate_approaches: list[str]


class CompletionVerificationResponse(BaseModel):
    verification_id: str
    learner_name: str
    scope_type: str
    scope_id: str
    issued_at: str
    revoked: bool
    criteria_version: str
    evidence_summary: list[dict[str, Any]]
