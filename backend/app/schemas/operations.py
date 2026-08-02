import uuid
from datetime import date, datetime
from typing import Any, Literal

from pydantic import BaseModel, EmailStr, Field, model_validator

OrganizationKind = Literal["university", "training_provider", "company", "recruiter", "personal"]
CohortType = Literal[
    "academic_course",
    "bootcamp",
    "employee_training",
    "certification_preparation",
    "private_group",
]
AssignmentType = Literal[
    "pathway",
    "module",
    "lesson",
    "assessment",
    "lab",
    "mission",
    "project",
    "reflection",
    "portfolio_submission",
]


class OrganizationCreate(BaseModel):
    name: str = Field(min_length=2, max_length=160)
    slug: str = Field(pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$", max_length=120)
    kind: OrganizationKind


class OrganizationUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=160)
    metadata: dict[str, str] | None = None
    settings: dict[str, Any] | None = None
    version: int = Field(ge=1)


class InvitationCreate(BaseModel):
    email: EmailStr
    role: Literal[
        "organization_admin",
        "instructor",
        "reviewer",
        "cohort_manager",
        "company_manager",
        "recruiter",
        "learner",
    ]
    expires_in_days: int = Field(default=7, ge=1, le=30)


class InvitationToken(BaseModel):
    token: str = Field(min_length=32, max_length=256)


class MemberUpdate(BaseModel):
    role: str | None = Field(default=None, max_length=64)
    active: bool | None = None


class ProgrammeCreate(BaseModel):
    stable_key: str = Field(pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$", max_length=120)
    name: str = Field(min_length=2, max_length=180)
    description: str = Field(min_length=1, max_length=5000)
    academic_period: str | None = Field(default=None, max_length=100)
    qualification_label: str | None = Field(default=None, max_length=160)
    required_pathways: list[str] = []
    elective_pathways: list[str] = []
    required_projects: list[str] = []
    completion_policy: dict[str, Any] = {}


class CohortCreate(BaseModel):
    stable_key: str = Field(pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$", max_length=120)
    name: str = Field(min_length=2, max_length=180)
    description: str = Field(default="", max_length=5000)
    cohort_type: CohortType
    start_date: date
    end_date: date | None = None
    programme_id: uuid.UUID | None = None
    completion_expectations: dict[str, Any] = {}
    visibility_rules: dict[str, Any] = {}
    self_enrolment_enabled: bool = False

    @model_validator(mode="after")
    def valid_dates(self) -> "CohortCreate":
        if self.end_date and self.end_date < self.start_date:
            raise ValueError("end_date cannot precede start_date")
        return self


class CohortMembers(BaseModel):
    user_ids: list[uuid.UUID] = Field(min_length=1, max_length=500)


class CohortStaffAssign(BaseModel):
    membership_id: uuid.UUID
    role: Literal["instructor", "cohort_manager", "company_manager"]


class CurriculumAssign(BaseModel):
    content_type: Literal["pathway", "module", "lab", "mission", "project"]
    content_id: str = Field(min_length=1, max_length=160)
    content_version: str = Field(min_length=1, max_length=40)
    due_at: datetime | None = None


class AssignmentCreate(BaseModel):
    cohort_id: uuid.UUID | None = None
    learner_user_ids: list[uuid.UUID] = []
    title: str = Field(min_length=2, max_length=220)
    instructions: str = Field(min_length=1, max_length=10000)
    assignment_type: AssignmentType
    content_id: str = Field(min_length=1, max_length=160)
    content_version: str = Field(min_length=1, max_length=40)
    release_at: datetime | None = None
    due_at: datetime | None = None
    late_policy: str | None = Field(default=None, max_length=2000)
    completion_criteria: dict[str, Any] = {}
    grading_method: Literal["completion", "automatic", "human_review", "rubric"] = "completion"
    review_required: bool = False
    visibility: Literal["assigned", "cohort", "private"] = "assigned"


class AssignmentSubmissionCreate(BaseModel):
    body: str = Field(min_length=1, max_length=30000)
    evidence_items: list[dict[str, Any]] = []


class AssignmentReviewUpdate(BaseModel):
    decision: Literal["revision_requested", "approved", "rejected"]
    feedback: str = Field(min_length=2, max_length=10000)
    rubric_scores: list[dict[str, Any]] = []


class ShareCreate(BaseModel):
    display_name: str = Field(min_length=2, max_length=120)
    include_email: bool = False
    expires_in_days: int = Field(default=30, ge=1, le=180)
    artifact_ids: list[uuid.UUID] = []
    completion_ids: list[uuid.UUID] = []


class EvidenceRequestCreate(BaseModel):
    message: str = Field(min_length=5, max_length=2000)
