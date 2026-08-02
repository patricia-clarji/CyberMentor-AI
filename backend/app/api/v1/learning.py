import uuid
from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, Depends, Request
from sqlalchemy import delete, select
from sqlalchemy.orm import Session as DatabaseSession

from app.core.errors import AppError
from app.db.session import get_db
from app.identity.dependencies import AuthContext, require_auth, require_csrf
from app.identity.service import audit
from app.learning.pathway_service import (
    grade_response,
    module_statuses,
    record_attempt,
)
from app.learning.soc_pathway import (
    ASSESSMENTS,
    LESSONS,
    MODULES,
    PATHWAY_ID,
    PATHWAY_VERSION,
    PRACTICES,
    public_pathway,
)
from app.models.learning import (
    Bookmark,
    Enrollment,
    LearnerGoal,
    LearnerNote,
    LearnerPreference,
    LearnerProfile,
    LearnerSkillState,
    LearningActivityAttempt,
    LessonProgress,
    Recommendation,
    Skill,
    SkillEvidence,
)
from app.schemas.learning import (
    ActivitySubmissionRequest,
    AssessmentSubmissionRequest,
    BookmarkRequest,
    BookmarkResponse,
    DashboardResponse,
    EnrollmentRequest,
    EnrollmentResponse,
    LearnerProfileResponse,
    LessonProgressRequest,
    LessonProgressResponse,
    NoteRequest,
    NoteResponse,
    OnboardingRequest,
    ProgressSnapshotRequest,
)

router = APIRouter(prefix="/learning", tags=["learning"])


def owner_filter(model: type[Any], auth: AuthContext) -> tuple[Any, Any]:
    return (
        model.organization_id == auth.organization_id,
        model.user_id == auth.user.id,
    )


def module_for_activity(activity_id: str) -> dict[str, Any] | None:
    return next(
        (
            module
            for module in MODULES
            if module["practice"]["id"] == activity_id or module["assessment"]["id"] == activity_id
        ),
        None,
    )


@router.get("/pathways/junior-soc-analyst")
def get_soc_pathway(
    auth: AuthContext = Depends(require_auth),
    db: DatabaseSession = Depends(get_db),
) -> dict[str, Any]:
    return {
        **public_pathway(),
        "enrolled": db.scalar(
            select(Enrollment.id).where(
                *owner_filter(Enrollment, auth),
                Enrollment.course_publication_id == PATHWAY_ID,
            )
        )
        is not None,
        "module_statuses": module_statuses(db, auth),
    }


@router.get("/pathways/junior-soc-analyst/lessons/{lesson_id}")
def get_soc_lesson(
    lesson_id: str,
    auth: AuthContext = Depends(require_auth),
    db: DatabaseSession = Depends(get_db),
) -> dict[str, Any]:
    item = LESSONS.get(lesson_id)
    if item is None:
        raise AppError(404, "lesson_not_found", "The pathway lesson was not found.")
    progress = db.scalar(
        select(LessonProgress).where(
            *owner_filter(LessonProgress, auth),
            LessonProgress.lesson_publication_id == lesson_id,
        )
    )
    return {
        **item,
        "progress": LessonProgressResponse.model_validate(progress, from_attributes=True)
        if progress
        else None,
    }


@router.post("/pathways/junior-soc-analyst/activities/{activity_id}/submit")
def submit_soc_activity(
    activity_id: str,
    payload: ActivitySubmissionRequest,
    auth: AuthContext = Depends(require_csrf),
    db: DatabaseSession = Depends(get_db),
) -> dict[str, Any]:
    activity = PRACTICES.get(activity_id)
    module = module_for_activity(activity_id)
    if activity is None or module is None:
        raise AppError(404, "activity_not_found", "The pathway practice was not found.")
    score = grade_response(activity["private_answer"], payload.response)
    attempt = record_attempt(
        db,
        auth,
        activity_id=activity_id,
        activity_type="guided_practice",
        module_id=module["id"],
        response=payload.response,
        score=score,
        feedback=activity["feedback"],
        idempotency_key=payload.idempotency_key,
        hints_used=payload.hints_used,
        skill_keys=activity["linked_skills"],
    )
    return {
        "attempt_id": str(attempt.id),
        "score": attempt.score,
        "passed": attempt.passed,
        "feedback": attempt.feedback,
        "module_statuses": module_statuses(db, auth),
    }


@router.get("/pathways/junior-soc-analyst/assessments/{assessment_id}")
def get_soc_assessment(
    assessment_id: str,
    auth: AuthContext = Depends(require_auth),
    db: DatabaseSession = Depends(get_db),
) -> dict[str, Any]:
    assessment = ASSESSMENTS.get(assessment_id)
    if assessment is None:
        raise AppError(404, "assessment_not_found", "The module assessment was not found.")
    attempts = db.scalars(
        select(LearningActivityAttempt)
        .where(
            *owner_filter(LearningActivityAttempt, auth),
            LearningActivityAttempt.activity_id == assessment_id,
        )
        .order_by(LearningActivityAttempt.submitted_at.desc())
    ).all()
    return {
        "id": assessment["id"],
        "version": assessment["version"],
        "title": assessment["title"],
        "retake_policy": assessment["retake_policy"],
        "questions": [
            {key: value for key, value in question.items() if key != "private_answer"}
            for question in assessment["questions"]
        ],
        "attempts": [
            {
                "id": str(attempt.id),
                "score": attempt.score,
                "passed": attempt.passed,
                "submitted_at": attempt.submitted_at,
            }
            for attempt in attempts
        ],
    }


@router.post("/pathways/junior-soc-analyst/assessments/{assessment_id}/submit")
def submit_soc_assessment(
    assessment_id: str,
    payload: AssessmentSubmissionRequest,
    auth: AuthContext = Depends(require_csrf),
    db: DatabaseSession = Depends(get_db),
) -> dict[str, Any]:
    assessment = ASSESSMENTS.get(assessment_id)
    module = module_for_activity(assessment_id)
    if assessment is None or module is None:
        raise AppError(404, "assessment_not_found", "The module assessment was not found.")
    question_ids = {question["id"] for question in assessment["questions"]}
    if set(payload.responses) != question_ids:
        raise AppError(
            422,
            "incomplete_assessment",
            "Submit exactly one response for every assessment question.",
        )
    results = [
        (
            question,
            grade_response(
                question["private_answer"],
                payload.responses[question["id"]],
            ),
        )
        for question in assessment["questions"]
    ]
    total_weight = sum(question["weight"] for question, _ in results)
    score = sum(question["weight"] * item_score for question, item_score in results) / (
        total_weight or 1
    )
    feedback = " ".join(f"{question['id']}: {question['explanation']}" for question, _ in results)
    attempt = record_attempt(
        db,
        auth,
        activity_id=assessment_id,
        activity_type="module_assessment",
        module_id=module["id"],
        response=payload.responses,
        score=score,
        feedback=feedback,
        idempotency_key=payload.idempotency_key,
        hints_used=payload.hints_used,
        skill_keys=[question["skill"] for question, _ in results],
    )
    return {
        "attempt_id": str(attempt.id),
        "score": attempt.score,
        "passed": attempt.passed,
        "feedback": attempt.feedback,
        "question_results": [
            {"question_id": question["id"], "score": item_score} for question, item_score in results
        ],
        "module_statuses": module_statuses(db, auth),
    }


@router.get("/skills/evidence")
def get_skill_evidence(
    auth: AuthContext = Depends(require_auth),
    db: DatabaseSession = Depends(get_db),
) -> dict[str, Any]:
    rows = db.execute(
        select(SkillEvidence, Skill)
        .join(Skill, Skill.id == SkillEvidence.skill_id)
        .where(*owner_filter(SkillEvidence, auth))
        .order_by(SkillEvidence.occurred_at.desc())
    ).all()
    states = db.execute(
        select(LearnerSkillState, Skill)
        .join(Skill, Skill.id == LearnerSkillState.skill_id)
        .where(*owner_filter(LearnerSkillState, auth))
        .order_by(Skill.name)
    ).all()
    evidence_counts: dict[uuid.UUID, int] = {}
    for evidence, _ in rows:
        evidence_counts[evidence.skill_id] = evidence_counts.get(evidence.skill_id, 0) + 1
    return {
        "profile_version": PATHWAY_VERSION,
        "skills": [
            {
                "skill_id": skill.stable_key,
                "skill_name": skill.name,
                "current_estimate": state.mastery_estimate,
                "confidence": state.confidence,
                "independence": state.independence,
                "supporting_evidence_count": evidence_counts.get(skill.id, 0),
                "weak_area": state.mastery_estimate < 0.6,
                "recent_evidence": next(
                    (
                        evidence.source_id
                        for evidence, row_skill in rows
                        if row_skill.id == skill.id
                    ),
                    None,
                ),
                "next_review": state.next_review_at,
                "why_changed": state.reasoning_summary,
            }
            for state, skill in states
        ],
        "evidence": [
            {
                "id": str(evidence.id),
                "skill_id": skill.stable_key,
                "skill_name": skill.name,
                "source_activity": evidence.source_id,
                "source_version": evidence.source_version,
                "evidence_type": evidence.source_type,
                "result": evidence.score,
                "independence": evidence.independence,
                "hint_usage": evidence.hints_used,
                "timestamp": evidence.occurred_at,
                "evaluator": "trusted-server",
                "confidence": "observed",
                "valid": True,
            }
            for evidence, skill in rows
        ],
    }


@router.put("/onboarding")
def complete_onboarding(
    payload: OnboardingRequest,
    request: Request,
    auth: AuthContext = Depends(require_csrf),
    db: DatabaseSession = Depends(get_db),
) -> dict[str, str]:
    profile = db.scalar(select(LearnerProfile).where(*owner_filter(LearnerProfile, auth)))
    now = datetime.now(UTC)
    if profile is None:
        profile = LearnerProfile(
            organization_id=auth.organization_id,
            user_id=auth.user.id,
            version=1,
        )
        db.add(profile)
    profile.experience_level = payload.experience_level
    profile.weekly_minutes = payload.weekly_minutes
    profile.networking_confidence = payload.networking_confidence
    profile.linux_confidence = payload.linux_confidence
    profile.investigation_confidence = payload.investigation_confidence
    profile.accessibility_needs = payload.accessibility_needs
    profile.onboarding_completed_at = now
    profile.version = (profile.version or 0) + 1
    db.execute(
        delete(LearnerGoal).where(
            *owner_filter(LearnerGoal, auth),
            LearnerGoal.is_primary.is_(True),
        )
    )
    db.add(
        LearnerGoal(
            organization_id=auth.organization_id,
            user_id=auth.user.id,
            goal_key="primary-career-objective",
            target_role=payload.career_objective,
            is_primary=True,
        )
    )
    db.execute(delete(LearnerPreference).where(*owner_filter(LearnerPreference, auth)))
    for preference in sorted(set(payload.learning_preferences)):
        db.add(
            LearnerPreference(
                organization_id=auth.organization_id,
                user_id=auth.user.id,
                preference_key=f"learning-mode:{preference[:60]}",
                preference_value=preference[:500],
            )
        )
    audit(
        db,
        "learning.onboarding_completed",
        "success",
        auth.user.id,
        auth.organization_id,
        getattr(request.state, "request_id", None),
    )
    db.commit()
    return {"message": "Onboarding saved."}


@router.post("/enrollments", response_model=EnrollmentResponse, status_code=201)
def enroll(
    payload: EnrollmentRequest,
    auth: AuthContext = Depends(require_csrf),
    db: DatabaseSession = Depends(get_db),
) -> Enrollment:
    existing = db.scalar(
        select(Enrollment).where(
            *owner_filter(Enrollment, auth),
            Enrollment.course_publication_id == payload.course_publication_id,
        )
    )
    if existing:
        return existing
    record = Enrollment(
        organization_id=auth.organization_id,
        user_id=auth.user.id,
        course_publication_id=payload.course_publication_id,
        status="active",
        enrolled_at=datetime.now(UTC),
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


@router.put("/lessons/{lesson_id}/progress", response_model=LessonProgressResponse)
def update_lesson_progress(
    lesson_id: str,
    payload: LessonProgressRequest,
    auth: AuthContext = Depends(require_csrf),
    db: DatabaseSession = Depends(get_db),
) -> LessonProgress:
    record = db.scalar(
        select(LessonProgress).where(
            *owner_filter(LessonProgress, auth),
            LessonProgress.lesson_publication_id == lesson_id,
        )
    )
    if record is None:
        record = LessonProgress(
            organization_id=auth.organization_id,
            user_id=auth.user.id,
            lesson_publication_id=lesson_id,
            lesson_version=payload.lesson_version,
            version=0,
        )
        db.add(record)
    elif payload.expected_version is not None and record.version != payload.expected_version:
        raise AppError(
            409,
            "version_conflict",
            "Progress changed in another session. Refresh before retrying.",
        )
    record.lesson_version = payload.lesson_version
    record.status = payload.status
    record.percent_complete = payload.percent_complete
    record.last_position = payload.last_position
    record.completed_at = datetime.now(UTC) if payload.status == "completed" else None
    record.version += 1
    db.commit()
    db.refresh(record)
    return record


@router.post("/notes", response_model=NoteResponse, status_code=201)
def save_note(
    payload: NoteRequest,
    auth: AuthContext = Depends(require_csrf),
    db: DatabaseSession = Depends(get_db),
) -> LearnerNote:
    record = db.scalar(
        select(LearnerNote)
        .where(
            *owner_filter(LearnerNote, auth),
            LearnerNote.lesson_publication_id == payload.lesson_publication_id,
        )
        .order_by(LearnerNote.updated_at.desc())
    )
    if record is None:
        record = LearnerNote(
            organization_id=auth.organization_id,
            user_id=auth.user.id,
            lesson_publication_id=payload.lesson_publication_id,
            body=payload.body,
        )
        db.add(record)
    else:
        record.body = payload.body
    db.commit()
    db.refresh(record)
    return record


@router.delete("/notes/{note_id}", status_code=204)
def delete_note(
    note_id: uuid.UUID,
    auth: AuthContext = Depends(require_csrf),
    db: DatabaseSession = Depends(get_db),
) -> None:
    record = db.scalar(
        select(LearnerNote).where(LearnerNote.id == note_id, *owner_filter(LearnerNote, auth))
    )
    if record is None:
        raise AppError(404, "note_not_found", "Note was not found.")
    db.delete(record)
    db.commit()


@router.post("/bookmarks", response_model=BookmarkResponse, status_code=201)
def add_bookmark(
    payload: BookmarkRequest,
    auth: AuthContext = Depends(require_csrf),
    db: DatabaseSession = Depends(get_db),
) -> Bookmark:
    existing = db.scalar(
        select(Bookmark).where(
            *owner_filter(Bookmark, auth),
            Bookmark.resource_type == payload.resource_type,
            Bookmark.resource_id == payload.resource_id,
        )
    )
    if existing:
        return existing
    record = Bookmark(
        organization_id=auth.organization_id,
        user_id=auth.user.id,
        resource_type=payload.resource_type,
        resource_id=payload.resource_id,
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


@router.put("/progress-snapshot")
def synchronize_progress_snapshot(
    payload: ProgressSnapshotRequest,
    auth: AuthContext = Depends(require_csrf),
    db: DatabaseSession = Depends(get_db),
) -> dict[str, int]:
    now = datetime.now(UTC)
    enrolled_ids = set(payload.enrolled_courses)
    enrollment_records = db.scalars(select(Enrollment).where(*owner_filter(Enrollment, auth))).all()
    enrollment_by_course = {item.course_publication_id: item for item in enrollment_records}
    for course_id in enrolled_ids - set(enrollment_by_course):
        db.add(
            Enrollment(
                organization_id=auth.organization_id,
                user_id=auth.user.id,
                course_publication_id=course_id,
                status="active",
                enrolled_at=now,
            )
        )
    completed_ids = set(payload.completed_lessons)
    progress_records = db.scalars(
        select(LessonProgress).where(*owner_filter(LessonProgress, auth))
    ).all()
    progress_by_lesson = {item.lesson_publication_id: item for item in progress_records}
    for lesson_id in completed_ids:
        progress_record = progress_by_lesson.get(lesson_id)
        if progress_record is None:
            progress_record = LessonProgress(
                organization_id=auth.organization_id,
                user_id=auth.user.id,
                lesson_publication_id=lesson_id,
                lesson_version="publication-current",
                version=0,
            )
            db.add(progress_record)
        progress_record.status = "completed"
        progress_record.percent_complete = 100
        progress_record.completed_at = progress_record.completed_at or now
        progress_record.version = (progress_record.version or 0) + 1
    note_records = db.scalars(select(LearnerNote).where(*owner_filter(LearnerNote, auth))).all()
    note_by_lesson = {item.lesson_publication_id: item for item in note_records}
    for lesson_id, body in payload.notes.items():
        clean = body.strip()
        if len(clean) > 20_000:
            raise AppError(422, "note_too_long", "A note exceeds 20,000 characters.")
        note_record = note_by_lesson.get(lesson_id)
        if not clean:
            if note_record:
                db.delete(note_record)
            continue
        if note_record is None:
            note_record = LearnerNote(
                organization_id=auth.organization_id,
                user_id=auth.user.id,
                lesson_publication_id=lesson_id,
                body=clean,
            )
            db.add(note_record)
        else:
            note_record.body = clean
    desired_bookmarks = set(payload.lesson_bookmarks)
    bookmark_records = db.scalars(
        select(Bookmark).where(*owner_filter(Bookmark, auth), Bookmark.resource_type == "lesson")
    ).all()
    bookmark_by_resource = {item.resource_id: item for item in bookmark_records}
    for resource_id in desired_bookmarks - set(bookmark_by_resource):
        db.add(
            Bookmark(
                organization_id=auth.organization_id,
                user_id=auth.user.id,
                resource_type="lesson",
                resource_id=resource_id,
            )
        )
    for resource_id in set(bookmark_by_resource) - desired_bookmarks:
        db.delete(bookmark_by_resource[resource_id])
    db.commit()
    return {
        "enrollments": len(enrolled_ids),
        "completedLessons": len(completed_ids),
        "notes": len([value for value in payload.notes.values() if value.strip()]),
        "bookmarks": len(desired_bookmarks),
    }


@router.delete("/bookmarks/{resource_type}/{resource_id}", status_code=204)
def remove_bookmark(
    resource_type: str,
    resource_id: str,
    auth: AuthContext = Depends(require_csrf),
    db: DatabaseSession = Depends(get_db),
) -> None:
    record = db.scalar(
        select(Bookmark).where(
            *owner_filter(Bookmark, auth),
            Bookmark.resource_type == resource_type,
            Bookmark.resource_id == resource_id,
        )
    )
    if record is None:
        raise AppError(404, "bookmark_not_found", "Bookmark was not found.")
    db.delete(record)
    db.commit()


@router.get("/dashboard", response_model=DashboardResponse)
def dashboard(
    auth: AuthContext = Depends(require_auth),
    db: DatabaseSession = Depends(get_db),
) -> DashboardResponse:
    profile = db.scalar(select(LearnerProfile).where(*owner_filter(LearnerProfile, auth)))
    goal = db.scalar(
        select(LearnerGoal).where(
            *owner_filter(LearnerGoal, auth), LearnerGoal.is_primary.is_(True)
        )
    )
    preferences = db.scalars(
        select(LearnerPreference.preference_value).where(*owner_filter(LearnerPreference, auth))
    ).all()
    enrollments = db.scalars(select(Enrollment).where(*owner_filter(Enrollment, auth))).all()
    progress = db.scalars(select(LessonProgress).where(*owner_filter(LessonProgress, auth))).all()
    notes = db.scalars(select(LearnerNote).where(*owner_filter(LearnerNote, auth))).all()
    bookmarks = db.scalars(select(Bookmark).where(*owner_filter(Bookmark, auth))).all()
    skills = db.execute(
        select(LearnerSkillState, Skill)
        .join(Skill, Skill.id == LearnerSkillState.skill_id)
        .where(*owner_filter(LearnerSkillState, auth))
    ).all()
    recommendations = db.scalars(
        select(Recommendation).where(
            *owner_filter(Recommendation, auth), Recommendation.status == "active"
        )
    ).all()
    return DashboardResponse(
        profile=LearnerProfileResponse.model_validate(profile, from_attributes=True)
        if profile
        else None,
        primary_goal=goal.target_role if goal else None,
        preferences=list(preferences),
        enrollments=[
            EnrollmentResponse.model_validate(item, from_attributes=True) for item in enrollments
        ],
        lesson_progress=[
            LessonProgressResponse.model_validate(item, from_attributes=True) for item in progress
        ],
        notes=[NoteResponse.model_validate(item, from_attributes=True) for item in notes],
        bookmarks=[
            BookmarkResponse.model_validate(item, from_attributes=True) for item in bookmarks
        ],
        skills=[
            {
                "skillId": skill.stable_key,
                "name": skill.name,
                "mastery": state.mastery_estimate,
                "confidence": state.confidence,
                "independence": state.independence,
                "reasoning": state.reasoning_summary,
                "nextReviewAt": state.next_review_at,
            }
            for state, skill in skills
        ],
        recommendations=[
            {
                "id": str(item.id),
                "activityType": item.activity_type,
                "activityId": item.activity_id,
                "reason": item.reason,
                "interventionType": item.intervention_type,
                "required": item.required,
            }
            for item in recommendations
        ],
    )
