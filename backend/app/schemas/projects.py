import uuid

from pydantic import BaseModel, Field


class ProjectMilestoneResponse(BaseModel):
    position: int
    title: str
    requirement: str


class RubricCriterionResponse(BaseModel):
    key: str
    description: str
    weight: float
    pass_standard: str


class ProjectResponse(BaseModel):
    id: uuid.UUID
    stable_key: str
    publication_id: str | None
    title: str
    description: str
    version: str
    milestones: list[ProjectMilestoneResponse]
    rubric_version: str
    rubric: list[RubricCriterionResponse]
    review_notice: str


class ProjectSubmissionRequest(BaseModel):
    body: str = Field(min_length=500, max_length=30_000)
    reflection: str = Field(min_length=120, max_length=5000)


class ProjectSubmissionResponse(BaseModel):
    id: uuid.UUID
    status: str
    submitted_at: str
    version: int
    review_notice: str


class CriterionReview(BaseModel):
    key: str = Field(min_length=2, max_length=120)
    passed: bool
    comment: str = Field(min_length=10, max_length=1500)


class ProjectReviewRequest(BaseModel):
    criteria: list[CriterionReview] = Field(min_length=1, max_length=20)
    feedback: str = Field(min_length=40, max_length=5000)


class ProjectReviewResponse(BaseModel):
    submission_id: uuid.UUID
    passed: bool
    status: str
    portfolio_artifact_id: uuid.UUID | None
    completion_verification_id: str | None
