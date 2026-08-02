import uuid
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator

ContentType = Literal[
    "course",
    "module",
    "lesson",
    "assessment",
    "question",
    "question_set",
    "lab",
    "mission",
    "scenario",
    "hint",
    "reference",
    "glossary_entry",
    "skill",
    "learning_objective",
    "project",
    "portfolio_template",
    "completion_rule",
    "certificate_template",
    "rubric",
    "evidence_rule",
    "learning_path",
    "sentinel_knowledge",
]

SectionType = Literal[
    "heading",
    "paragraph",
    "introduction",
    "learning_objectives",
    "definition",
    "concept_explanation",
    "worked_example",
    "investigation_example",
    "alert_walkthrough",
    "log_walkthrough",
    "code_command",
    "code",
    "command",
    "terminal_output",
    "log_sample",
    "table",
    "diagram_placeholder",
    "image",
    "callout",
    "tip",
    "warning",
    "common_mistakes",
    "misconception",
    "guided_practice",
    "reflection",
    "knowledge_checkpoint",
    "references",
    "summary",
    "next_steps",
]

RelationType = Literal[
    "prerequisite",
    "module",
    "lesson",
    "assessment",
    "question",
    "lab",
    "mission",
    "project",
    "skill",
    "reference",
    "parent_skill",
    "elective",
]


class LessonSectionInput(BaseModel):
    section_key: uuid.UUID = Field(default_factory=uuid.uuid4)
    section_type: SectionType
    title: str = Field(default="", max_length=240)
    body: str = Field(default="", max_length=50_000)
    structured_data: dict[str, Any] = Field(default_factory=dict)
    visibility: Literal["visible", "hidden"] = "visible"
    accessibility_label: str | None = Field(default=None, max_length=300)
    sort_order: int = Field(ge=0, le=999)

    @field_validator("body", "title")
    @classmethod
    def reject_unsafe_markup(cls, value: str) -> str:
        lowered = value.casefold()
        blocked = ("<script", "javascript:", "onerror=", "onload=", "<iframe")
        if any(fragment in lowered for fragment in blocked):
            raise ValueError("Unsafe active markup is not allowed.")
        return value.strip()


class LearningObjectiveInput(BaseModel):
    objective_key: uuid.UUID = Field(default_factory=uuid.uuid4)
    title: str = Field(min_length=2, max_length=240)
    description: str = Field(min_length=5, max_length=2_000)
    bloom_level: Literal["remember", "understand", "apply", "analyze", "evaluate", "create"]
    linked_skill_keys: list[str] = Field(default_factory=list, max_length=30)
    assessment_coverage: bool = False
    practical_coverage: bool = False
    review_status: Literal["pending", "reviewed"] = "pending"


class ContentRelationInput(BaseModel):
    target_content_id: uuid.UUID
    target_version_id: uuid.UUID | None = None
    relation_type: RelationType
    required: bool = True
    sort_order: int = Field(default=0, ge=0, le=999)
    configuration: dict[str, Any] = Field(default_factory=dict)


class ContentCreateRequest(BaseModel):
    content_type: ContentType
    title: str = Field(min_length=2, max_length=240)
    public_slug: str = Field(pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$", max_length=160)
    description: str = Field(default="", max_length=5_000)
    language: str = Field(default="en", pattern=r"^[a-z]{2,3}(?:-[A-Z]{2})?$")
    fallback_language: str | None = Field(default=None, max_length=16)
    visibility: Literal["private", "organization", "public"] = "private"
    version: str = Field(default="1.0.0", pattern=r"^\d+\.\d+\.\d+$")
    change_summary: str = Field(default="Initial draft", min_length=3, max_length=2_000)
    metadata: dict[str, Any] = Field(default_factory=dict)
    sections: list[LessonSectionInput] = Field(default_factory=list, max_length=200)
    objectives: list[LearningObjectiveInput] = Field(default_factory=list, max_length=100)
    relationships: list[ContentRelationInput] = Field(default_factory=list, max_length=500)


class ContentUpdateRequest(BaseModel):
    expected_lock_version: int = Field(ge=1)
    title: str = Field(min_length=2, max_length=240)
    public_slug: str = Field(pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$", max_length=160)
    description: str = Field(default="", max_length=5_000)
    visibility: Literal["private", "organization", "public"] = "private"
    change_summary: str = Field(min_length=3, max_length=2_000)
    metadata: dict[str, Any] = Field(default_factory=dict)
    sections: list[LessonSectionInput] = Field(default_factory=list, max_length=200)
    objectives: list[LearningObjectiveInput] = Field(default_factory=list, max_length=100)
    relationships: list[ContentRelationInput] = Field(default_factory=list, max_length=500)


class DraftFromVersionRequest(BaseModel):
    version: str = Field(pattern=r"^\d+\.\d+\.\d+$")
    change_summary: str = Field(min_length=3, max_length=2_000)


class ReviewerAssignmentRequest(BaseModel):
    reviewer_email: str = Field(min_length=3, max_length=320)
    reviewer_type: Literal[
        "content_reviewer",
        "technical_reviewer",
        "instructional_reviewer",
        "cybersecurity_subject_matter_expert",
        "curriculum_reviewer",
        "language_reviewer",
        "accessibility_reviewer",
        "content_administrator",
        "platform_administrator",
    ]
    due_at: datetime | None = None


class ReviewDecisionRequest(BaseModel):
    decision: Literal["approve", "request_changes", "reject"]
    notes: str = Field(min_length=3, max_length=5_000)
    checklist: list[dict[str, Any]] = Field(default_factory=list, max_length=30)


class ReviewCommentRequest(BaseModel):
    body: str = Field(min_length=2, max_length=10_000)
    parent_comment_id: uuid.UUID | None = None
    location_type: Literal["version", "section", "objective", "metadata"] = "version"
    location_key: str | None = Field(default=None, max_length=160)
    severity: Literal["suggestion", "warning", "blocking"] = "suggestion"
    suggested_change: str | None = Field(default=None, max_length=10_000)


class CommentStatusRequest(BaseModel):
    resolved: bool


class CommentEditRequest(BaseModel):
    body: str = Field(min_length=2, max_length=10_000)
    suggested_change: str | None = Field(default=None, max_length=10_000)


class ScheduleRequest(BaseModel):
    publish_at: datetime
    timezone: str = Field(min_length=1, max_length=64)


class PublishRequest(BaseModel):
    reason: str = Field(default="Approved publication", min_length=3, max_length=2_000)


class RollbackRequest(BaseModel):
    target_revision: int = Field(ge=1)
    reason: str = Field(min_length=5, max_length=2_000)


class SkillMergeRequest(BaseModel):
    target_skill_id: uuid.UUID
    reason: str = Field(min_length=5, max_length=2_000)


class FeatureFlagRequest(BaseModel):
    name: str = Field(pattern=r"^[a-z][a-z0-9_.-]+$", max_length=100)
    description: str = Field(min_length=3, max_length=2_000)
    environment: Literal["development", "test", "production"]
    default_state: bool = False
    current_state: bool = False
    starts_at: datetime | None = None
    expires_at: datetime | None = None


class FeatureFlagUpdateRequest(BaseModel):
    current_state: bool
    description: str = Field(min_length=3, max_length=2_000)
    starts_at: datetime | None = None
    expires_at: datetime | None = None


class JobActionRequest(BaseModel):
    reason: str = Field(min_length=3, max_length=1_000)


class ReviewRequirementRequest(BaseModel):
    content_type: ContentType
    reviewer_type: Literal[
        "technical_reviewer",
        "instructional_reviewer",
        "accessibility_reviewer",
        "content_administrator",
    ]
    required: bool = True
    active: bool = True


class CmsLabPreviewCommandRequest(BaseModel):
    command: str = Field(min_length=1, max_length=500)
    cwd: str = Field(default="/home/analyst", max_length=500)


class CmsMissionPreviewActionRequest(BaseModel):
    stage_id: str = Field(min_length=1, max_length=160)
    action_type: Literal["open_evidence", "decision"]
    resource_id: str | None = Field(default=None, max_length=500)
    decision_id: str | None = Field(default=None, max_length=500)


class ManagedAssessmentSubmissionRequest(BaseModel):
    answers: dict[str, Any] = Field(default_factory=dict)
    idempotency_key: str = Field(min_length=8, max_length=100)
