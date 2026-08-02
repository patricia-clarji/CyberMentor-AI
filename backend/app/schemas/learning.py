import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class OnboardingRequest(BaseModel):
    experience_level: str = Field(min_length=2, max_length=40)
    career_objective: str = Field(min_length=2, max_length=100)
    weekly_minutes: int = Field(ge=30, le=2400)
    networking_confidence: int = Field(ge=1, le=5)
    linux_confidence: int = Field(ge=1, le=5)
    investigation_confidence: int = Field(ge=1, le=5)
    learning_preferences: list[str] = Field(max_length=8)
    accessibility_needs: str | None = Field(default=None, max_length=2000)


class EnrollmentRequest(BaseModel):
    course_publication_id: str = Field(min_length=3, max_length=160)


class LessonProgressRequest(BaseModel):
    lesson_version: str = Field(min_length=1, max_length=40)
    status: str = Field(pattern="^(started|in_progress|completed)$")
    percent_complete: int = Field(ge=0, le=100)
    last_position: str | None = Field(default=None, max_length=160)
    expected_version: int | None = Field(default=None, ge=1)


class NoteRequest(BaseModel):
    lesson_publication_id: str = Field(min_length=3, max_length=160)
    body: str = Field(min_length=1, max_length=20_000)


class BookmarkRequest(BaseModel):
    resource_type: str = Field(pattern="^(lesson|course|mission|project|lab)$")
    resource_id: str = Field(min_length=3, max_length=160)


class ProgressSnapshotRequest(BaseModel):
    enrolled_courses: list[str] = Field(max_length=100)
    completed_lessons: list[str] = Field(max_length=2000)
    notes: dict[str, str] = Field(max_length=1000)
    lesson_bookmarks: list[str] = Field(max_length=2000)


class ActivitySubmissionRequest(BaseModel):
    response: dict[str, Any]
    idempotency_key: str = Field(min_length=8, max_length=100)
    hints_used: int = Field(default=0, ge=0, le=10)


class AssessmentSubmissionRequest(BaseModel):
    responses: dict[str, dict[str, Any]] = Field(min_length=1, max_length=20)
    idempotency_key: str = Field(min_length=8, max_length=100)
    hints_used: int = Field(default=0, ge=0, le=10)


class LearnerProfileResponse(BaseModel):
    experience_level: str | None
    weekly_minutes: int | None
    networking_confidence: int | None
    linux_confidence: int | None
    investigation_confidence: int | None
    accessibility_needs: str | None
    onboarding_completed_at: datetime | None
    version: int


class EnrollmentResponse(BaseModel):
    id: uuid.UUID
    course_publication_id: str
    status: str
    enrolled_at: datetime
    completed_at: datetime | None


class LessonProgressResponse(BaseModel):
    lesson_publication_id: str
    lesson_version: str
    status: str
    percent_complete: int
    last_position: str | None
    completed_at: datetime | None
    version: int


class NoteResponse(BaseModel):
    id: uuid.UUID
    lesson_publication_id: str
    body: str
    updated_at: datetime


class BookmarkResponse(BaseModel):
    id: uuid.UUID
    resource_type: str
    resource_id: str


class DashboardResponse(BaseModel):
    profile: LearnerProfileResponse | None
    primary_goal: str | None
    preferences: list[str]
    enrollments: list[EnrollmentResponse]
    lesson_progress: list[LessonProgressResponse]
    notes: list[NoteResponse]
    bookmarks: list[BookmarkResponse]
    skills: list[dict[str, Any]]
    recommendations: list[dict[str, Any]]
