import csv
import io
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

from fastapi import APIRouter, Depends, Request
from fastapi.responses import Response
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session as DatabaseSession

from app.core.errors import AppError
from app.db.session import get_db
from app.identity.dependencies import AuthContext, assert_permission, require_auth, require_csrf
from app.identity.service import audit
from app.models import OrganizationMembership, User, UserProfile
from app.models.learning import (
    LearnerMisconception,
    LearnerSkillState,
    LearningActivityAttempt,
    Misconception,
    Skill,
)
from app.models.mission import MissionHintUse
from app.models.operations import (
    Assignment,
    AssignmentReview,
    AssignmentSubmission,
    Cohort,
    CohortCurriculum,
    CohortEnrollment,
    CohortStaff,
    EvidenceRequest,
    LearnerAssignment,
    Notification,
    Programme,
    ReportExport,
    SharedEvidenceItem,
    SharedProfile,
    SharedProfileAccess,
)
from app.models.portfolio import CompletionRecord, PortfolioArtifact
from app.schemas.operations import (
    AssignmentCreate,
    AssignmentReviewUpdate,
    AssignmentSubmissionCreate,
    CohortCreate,
    CohortMembers,
    CohortStaffAssign,
    CurriculumAssign,
    EvidenceRequestCreate,
    ProgrammeCreate,
    ShareCreate,
)
from app.security.tokens import new_token, token_hash

router = APIRouter(prefix="/operations", tags=["organization operations"])
public_router = APIRouter(prefix="/verify", tags=["recruiter verification"])


def request_id(request: Request) -> str | None:
    return getattr(request.state, "request_id", None)


def owned(
    db: DatabaseSession,
    model: Any,
    auth: AuthContext,
    object_id: uuid.UUID,
) -> Any:
    item = db.scalar(
        select(model).where(
            model.id == object_id,
            model.organization_id == auth.organization_id,
        )
    )
    if item is None:
        raise AppError(404, "object_not_found", "The requested record was not found.")
    return item


def record_audit(
    db: DatabaseSession,
    request: Request,
    auth: AuthContext,
    action: str,
    target_type: str,
    target_id: uuid.UUID,
) -> None:
    audit(
        db,
        action,
        "success",
        auth.user.id,
        auth.organization_id,
        request_id(request),
        target_type,
        str(target_id),
    )


def notify(
    db: DatabaseSession,
    organization_id: uuid.UUID,
    user_id: uuid.UUID,
    event_type: str,
    title: str,
    message: str,
    deep_link: str | None,
) -> None:
    db.add(
        Notification(
            organization_id=organization_id,
            user_id=user_id,
            event_type=event_type,
            title=title,
            message=message,
            deep_link=deep_link,
        )
    )


@router.get("/dashboard")
def dashboard(
    portal: str = "instructor",
    auth: AuthContext = Depends(require_auth),
    db: DatabaseSession = Depends(get_db),
) -> dict[str, object]:
    permission = "recruiter_evidence.view" if portal == "recruiter" else "organization.view"
    assert_permission(db, auth, permission)
    cohort_count = db.scalar(
        select(func.count(Cohort.id)).where(
            Cohort.organization_id == auth.organization_id,
            Cohort.status == "active",
        )
    )
    learner_count = db.scalar(
        select(func.count(CohortEnrollment.id)).where(
            CohortEnrollment.organization_id == auth.organization_id,
            CohortEnrollment.status == "active",
        )
    )
    pending_reviews = db.scalar(
        select(func.count(AssignmentReview.id)).where(
            AssignmentReview.organization_id == auth.organization_id,
            AssignmentReview.state.in_(["pending", "in_review", "resubmitted"]),
        )
    )
    active_assignments = db.scalar(
        select(func.count(Assignment.id)).where(
            Assignment.organization_id == auth.organization_id,
            Assignment.status == "active",
        )
    )
    completed = db.scalar(
        select(func.count(LearnerAssignment.id)).where(
            LearnerAssignment.organization_id == auth.organization_id,
            LearnerAssignment.status == "completed",
        )
    )
    total = db.scalar(
        select(func.count(LearnerAssignment.id)).where(
            LearnerAssignment.organization_id == auth.organization_id
        )
    )
    attempt_summary = db.execute(
        select(
            func.count(LearningActivityAttempt.id),
            func.count(func.distinct(LearningActivityAttempt.user_id)),
            func.avg(LearningActivityAttempt.score),
            func.sum(LearningActivityAttempt.hints_used),
        ).where(LearningActivityAttempt.organization_id == auth.organization_id)
    ).one()
    mission_hints = db.scalar(
        select(func.count(MissionHintUse.id)).where(
            MissionHintUse.organization_id == auth.organization_id
        )
    )
    misconception_rows = db.execute(
        select(Misconception.stable_key, func.count(LearnerMisconception.id))
        .join(
            LearnerMisconception,
            LearnerMisconception.misconception_id == Misconception.id,
        )
        .where(
            LearnerMisconception.organization_id == auth.organization_id,
            LearnerMisconception.status != "resolved",
        )
        .group_by(Misconception.stable_key)
        .order_by(func.count(LearnerMisconception.id).desc())
        .limit(5)
    ).all()
    skill_gap_rows = db.execute(
        select(Skill.stable_key, func.avg(LearnerSkillState.mastery_estimate))
        .join(LearnerSkillState, LearnerSkillState.skill_id == Skill.id)
        .where(LearnerSkillState.organization_id == auth.organization_id)
        .group_by(Skill.stable_key)
        .order_by(func.avg(LearnerSkillState.mastery_estimate))
        .limit(5)
    ).all()
    attempt_count = int(attempt_summary[0] or 0)
    attempted_learners = int(attempt_summary[1] or 0)
    return {
        "portal": portal,
        "metrics": {
            "active_cohorts": int(cohort_count or 0),
            "active_learners": int(learner_count or 0),
            "pending_reviews": int(pending_reviews or 0),
            "active_assignments": int(active_assignments or 0),
            "assignment_completion_rate": round((completed or 0) / total, 4) if total else None,
        },
        "definitions": {
            "assignment_completion_rate": (
                "Completed learner assignments divided by all learner assignments in the "
                "active organization."
            ),
            "pending_reviews": "Reviews in pending, in-review, or resubmitted state.",
            "average_attempts": "Persisted activity attempts divided by learners with attempts.",
            "hint_dependence": "Recorded activity hints plus mission hint-use events.",
        },
        "analytics": {
            "average_attempts": (
                round(attempt_count / attempted_learners, 2) if attempted_learners else None
            ),
            "average_activity_score": (
                round(float(attempt_summary[2]), 4) if attempt_summary[2] is not None else None
            ),
            "hint_dependence": int(attempt_summary[3] or 0) + int(mission_hints or 0),
            "common_misconceptions": [
                {"key": key, "learners": int(count)} for key, count in misconception_rows
            ],
            "skill_gaps": [
                {"skill": key, "average_mastery": round(float(mastery), 4)}
                for key, mastery in skill_gap_rows
            ],
        },
        "time_range": "all persisted organization events",
        "data_source": "tenant-scoped cohorts, assignments, submissions, and reviews",
        "last_updated": datetime.now(UTC),
        "limitations": (
            "Readiness is not guaranteed. Empty metrics remain null when evidence is insufficient."
        ),
    }


@router.post("/programmes", status_code=201)
def create_programme(
    payload: ProgrammeCreate,
    request: Request,
    auth: AuthContext = Depends(require_csrf),
    db: DatabaseSession = Depends(get_db),
) -> dict[str, object]:
    assert_permission(db, auth, "cohorts.create")
    item = Programme(
        organization_id=auth.organization_id,
        created_by_user_id=auth.user.id,
        **payload.model_dump(),
    )
    db.add(item)
    try:
        db.flush()
    except IntegrityError as error:
        raise AppError(409, "programme_exists", "Programme key already exists.") from error
    record_audit(db, request, auth, "programme.created", "programme", item.id)
    db.commit()
    return {"id": item.id, "name": item.name, "status": item.status}


@router.get("/programmes")
def list_programmes(
    auth: AuthContext = Depends(require_auth),
    db: DatabaseSession = Depends(get_db),
) -> list[dict[str, object]]:
    assert_permission(db, auth, "cohorts.view")
    items = db.scalars(
        select(Programme)
        .where(Programme.organization_id == auth.organization_id)
        .order_by(Programme.name)
    ).all()
    return [
        {
            "id": item.id,
            "stable_key": item.stable_key,
            "name": item.name,
            "academic_period": item.academic_period,
            "qualification_label": item.qualification_label,
            "required_pathways": item.required_pathways,
            "required_projects": item.required_projects,
            "status": item.status,
            "version": item.version,
        }
        for item in items
    ]


@router.post("/cohorts", status_code=201)
def create_cohort(
    payload: CohortCreate,
    request: Request,
    auth: AuthContext = Depends(require_csrf),
    db: DatabaseSession = Depends(get_db),
) -> dict[str, object]:
    assert_permission(db, auth, "cohorts.create")
    if payload.programme_id:
        owned(db, Programme, auth, payload.programme_id)
    item = Cohort(
        organization_id=auth.organization_id,
        created_by_user_id=auth.user.id,
        **payload.model_dump(),
    )
    db.add(item)
    try:
        db.flush()
    except IntegrityError as error:
        raise AppError(409, "cohort_exists", "Cohort key already exists.") from error
    record_audit(db, request, auth, "cohort.created", "cohort", item.id)
    db.commit()
    return {"id": item.id, "name": item.name, "status": item.status}


@router.get("/cohorts")
def list_cohorts(
    status: str | None = None,
    auth: AuthContext = Depends(require_auth),
    db: DatabaseSession = Depends(get_db),
) -> list[dict[str, object]]:
    assert_permission(db, auth, "cohorts.view")
    query = select(Cohort).where(Cohort.organization_id == auth.organization_id)
    if status:
        query = query.where(Cohort.status == status)
    items = db.scalars(query.order_by(Cohort.start_date.desc(), Cohort.name)).all()
    result: list[dict[str, object]] = []
    for item in items:
        learners = db.scalar(
            select(func.count(CohortEnrollment.id)).where(
                CohortEnrollment.cohort_id == item.id,
                CohortEnrollment.organization_id == auth.organization_id,
                CohortEnrollment.status == "active",
            )
        )
        result.append(
            {
                "id": item.id,
                "stable_key": item.stable_key,
                "name": item.name,
                "description": item.description,
                "cohort_type": item.cohort_type,
                "start_date": item.start_date,
                "end_date": item.end_date,
                "status": item.status,
                "active_learners": int(learners or 0),
                "version": item.version,
            }
        )
    return result


@router.get("/cohorts/{cohort_id}")
def cohort_detail(
    cohort_id: uuid.UUID,
    auth: AuthContext = Depends(require_auth),
    db: DatabaseSession = Depends(get_db),
) -> dict[str, object]:
    assert_permission(db, auth, "cohorts.view")
    cohort = owned(db, Cohort, auth, cohort_id)
    rows = db.execute(
        select(CohortEnrollment, UserProfile)
        .outerjoin(UserProfile, UserProfile.user_id == CohortEnrollment.learner_user_id)
        .where(
            CohortEnrollment.organization_id == auth.organization_id,
            CohortEnrollment.cohort_id == cohort.id,
        )
    ).all()
    return {
        "id": cohort.id,
        "name": cohort.name,
        "status": cohort.status,
        "cohort_type": cohort.cohort_type,
        "learners": [
            {
                "user_id": enrollment.learner_user_id,
                "display_name": profile.display_name if profile else "",
                "status": enrollment.status,
            }
            for enrollment, profile in rows
        ],
        "curriculum": [
            {
                "type": item.content_type,
                "id": item.content_id,
                "version": item.content_version,
                "due_at": item.due_at,
            }
            for item in db.scalars(
                select(CohortCurriculum).where(
                    CohortCurriculum.organization_id == auth.organization_id,
                    CohortCurriculum.cohort_id == cohort.id,
                )
            ).all()
        ],
    }


@router.post("/cohorts/{cohort_id}/archive")
def archive_cohort(
    cohort_id: uuid.UUID,
    request: Request,
    auth: AuthContext = Depends(require_csrf),
    db: DatabaseSession = Depends(get_db),
) -> dict[str, str]:
    assert_permission(db, auth, "cohorts.manage")
    cohort = owned(db, Cohort, auth, cohort_id)
    cohort.status = "archived"
    cohort.version += 1
    record_audit(db, request, auth, "cohort.archived", "cohort", cohort.id)
    db.commit()
    return {"status": cohort.status}


@router.post("/cohorts/{cohort_id}/learners")
def enrol_learners(
    cohort_id: uuid.UUID,
    payload: CohortMembers,
    request: Request,
    auth: AuthContext = Depends(require_csrf),
    db: DatabaseSession = Depends(get_db),
) -> dict[str, int]:
    assert_permission(db, auth, "learners.manage_enrolment")
    cohort = owned(db, Cohort, auth, cohort_id)
    added = 0
    for user_id in dict.fromkeys(payload.user_ids):
        membership = db.scalar(
            select(OrganizationMembership).where(
                OrganizationMembership.organization_id == auth.organization_id,
                OrganizationMembership.user_id == user_id,
                OrganizationMembership.is_active.is_(True),
            )
        )
        if membership is None:
            raise AppError(422, "learner_not_member", "Every learner must be an active member.")
        existing = db.scalar(
            select(CohortEnrollment).where(
                CohortEnrollment.cohort_id == cohort.id,
                CohortEnrollment.learner_user_id == user_id,
            )
        )
        if existing:
            existing.status = "active"
            existing.left_at = None
            continue
        db.add(
            CohortEnrollment(
                organization_id=auth.organization_id,
                cohort_id=cohort.id,
                learner_user_id=user_id,
                enrolled_by_user_id=auth.user.id,
            )
        )
        notify(
            db,
            auth.organization_id,
            user_id,
            "cohort_enrolment",
            f"Enrolled in {cohort.name}",
            "A manager enrolled you in an organization cohort.",
            "/academy",
        )
        added += 1
    record_audit(db, request, auth, "cohort.learners_enrolled", "cohort", cohort.id)
    db.commit()
    return {"added": added}


@router.delete("/cohorts/{cohort_id}/learners/{learner_id}")
def remove_learner(
    cohort_id: uuid.UUID,
    learner_id: uuid.UUID,
    request: Request,
    auth: AuthContext = Depends(require_csrf),
    db: DatabaseSession = Depends(get_db),
) -> dict[str, str]:
    assert_permission(db, auth, "learners.manage_enrolment")
    owned(db, Cohort, auth, cohort_id)
    enrollment = db.scalar(
        select(CohortEnrollment).where(
            CohortEnrollment.organization_id == auth.organization_id,
            CohortEnrollment.cohort_id == cohort_id,
            CohortEnrollment.learner_user_id == learner_id,
        )
    )
    if enrollment is None:
        raise AppError(404, "enrollment_not_found", "Enrollment was not found.")
    enrollment.status = "removed"
    enrollment.left_at = datetime.now(UTC)
    record_audit(db, request, auth, "cohort.learner_removed", "cohort", cohort_id)
    db.commit()
    return {"status": "removed"}


@router.post("/cohorts/{cohort_id}/staff")
def assign_staff(
    cohort_id: uuid.UUID,
    payload: CohortStaffAssign,
    request: Request,
    auth: AuthContext = Depends(require_csrf),
    db: DatabaseSession = Depends(get_db),
) -> dict[str, str]:
    assert_permission(db, auth, "cohorts.assign")
    cohort = owned(db, Cohort, auth, cohort_id)
    membership = db.scalar(
        select(OrganizationMembership).where(
            OrganizationMembership.id == payload.membership_id,
            OrganizationMembership.organization_id == auth.organization_id,
            OrganizationMembership.is_active.is_(True),
        )
    )
    if membership is None:
        raise AppError(404, "membership_not_found", "Membership was not found.")
    existing = db.get(CohortStaff, (cohort.id, membership.id))
    if existing:
        existing.role = payload.role
    else:
        db.add(
            CohortStaff(
                cohort_id=cohort.id,
                membership_id=membership.id,
                role=payload.role,
                assigned_at=datetime.now(UTC),
            )
        )
    record_audit(db, request, auth, "cohort.staff_assigned", "cohort", cohort.id)
    db.commit()
    return {"status": "assigned"}


@router.post("/cohorts/{cohort_id}/curriculum", status_code=201)
def assign_curriculum(
    cohort_id: uuid.UUID,
    payload: CurriculumAssign,
    request: Request,
    auth: AuthContext = Depends(require_csrf),
    db: DatabaseSession = Depends(get_db),
) -> dict[str, object]:
    assert_permission(db, auth, "cohorts.assign")
    cohort = owned(db, Cohort, auth, cohort_id)
    item = CohortCurriculum(
        organization_id=auth.organization_id,
        cohort_id=cohort.id,
        assigned_by_user_id=auth.user.id,
        **payload.model_dump(),
    )
    db.add(item)
    try:
        db.flush()
    except IntegrityError as error:
        raise AppError(
            409, "curriculum_already_assigned", "Content version is already assigned."
        ) from error
    record_audit(db, request, auth, "cohort.curriculum_assigned", "cohort", cohort.id)
    db.commit()
    return {"id": item.id, "content_version": item.content_version}


@router.post("/assignments", status_code=201)
def create_assignment(
    payload: AssignmentCreate,
    request: Request,
    auth: AuthContext = Depends(require_csrf),
    db: DatabaseSession = Depends(get_db),
) -> dict[str, object]:
    assert_permission(db, auth, "assignments.create")
    if payload.cohort_id:
        owned(db, Cohort, auth, payload.cohort_id)
    data = payload.model_dump(exclude={"learner_user_ids"})
    item = Assignment(
        organization_id=auth.organization_id,
        created_by_user_id=auth.user.id,
        **data,
    )
    db.add(item)
    db.flush()
    learner_ids = set(payload.learner_user_ids)
    if payload.cohort_id:
        learner_ids.update(
            db.scalars(
                select(CohortEnrollment.learner_user_id).where(
                    CohortEnrollment.organization_id == auth.organization_id,
                    CohortEnrollment.cohort_id == payload.cohort_id,
                    CohortEnrollment.status == "active",
                )
            ).all()
        )
    for learner_id in learner_ids:
        if not db.scalar(
            select(OrganizationMembership.id).where(
                OrganizationMembership.organization_id == auth.organization_id,
                OrganizationMembership.user_id == learner_id,
                OrganizationMembership.is_active.is_(True),
            )
        ):
            raise AppError(422, "learner_not_member", "Assigned learners must be active members.")
        db.add(
            LearnerAssignment(
                organization_id=auth.organization_id,
                assignment_id=item.id,
                learner_user_id=learner_id,
            )
        )
    record_audit(db, request, auth, "assignment.created", "assignment", item.id)
    db.commit()
    return {"id": item.id, "status": item.status, "content_version": item.content_version}


@router.get("/assignments")
def list_assignments(
    auth: AuthContext = Depends(require_auth),
    db: DatabaseSession = Depends(get_db),
) -> list[dict[str, object]]:
    permissions_error = False
    try:
        assert_permission(db, auth, "assignments.view")
    except AppError:
        permissions_error = True
    if permissions_error:
        items = db.scalars(
            select(Assignment)
            .join(LearnerAssignment, LearnerAssignment.assignment_id == Assignment.id)
            .where(
                Assignment.organization_id == auth.organization_id,
                LearnerAssignment.organization_id == auth.organization_id,
                LearnerAssignment.learner_user_id == auth.user.id,
                Assignment.status.in_(["active", "closed"]),
            )
        ).all()
    else:
        items = db.scalars(
            select(Assignment)
            .where(Assignment.organization_id == auth.organization_id)
            .order_by(Assignment.due_at, Assignment.created_at.desc())
        ).all()
    now = datetime.now(UTC)
    return [
        {
            "id": item.id,
            "title": item.title,
            "assignment_type": item.assignment_type,
            "content_id": item.content_id,
            "content_version": item.content_version,
            "release_at": item.release_at,
            "due_at": item.due_at,
            "overdue": bool(item.due_at and item.due_at < now and item.status == "active"),
            "review_required": item.review_required,
            "status": item.status,
        }
        for item in items
    ]


@router.post("/assignments/{assignment_id}/publish")
def publish_assignment(
    assignment_id: uuid.UUID,
    request: Request,
    auth: AuthContext = Depends(require_csrf),
    db: DatabaseSession = Depends(get_db),
) -> dict[str, str]:
    assert_permission(db, auth, "assignments.manage")
    item = owned(db, Assignment, auth, assignment_id)
    if item.status not in {"draft", "scheduled"}:
        raise AppError(409, "assignment_not_publishable", "Assignment cannot be published.")
    item.status = (
        "scheduled" if item.release_at and item.release_at > datetime.now(UTC) else "active"
    )
    for learner_id in db.scalars(
        select(LearnerAssignment.learner_user_id).where(
            LearnerAssignment.organization_id == auth.organization_id,
            LearnerAssignment.assignment_id == item.id,
        )
    ).all():
        notify(
            db,
            auth.organization_id,
            learner_id,
            "assignment_published",
            item.title,
            "New assigned work is available.",
            "/organization/assignments",
        )
    record_audit(db, request, auth, "assignment.published", "assignment", item.id)
    db.commit()
    return {"status": item.status}


@router.post("/assignments/{assignment_id}/submissions", status_code=201)
def submit_assignment(
    assignment_id: uuid.UUID,
    payload: AssignmentSubmissionCreate,
    request: Request,
    auth: AuthContext = Depends(require_csrf),
    db: DatabaseSession = Depends(get_db),
) -> dict[str, object]:
    assignment = owned(db, Assignment, auth, assignment_id)
    link = db.scalar(
        select(LearnerAssignment).where(
            LearnerAssignment.organization_id == auth.organization_id,
            LearnerAssignment.assignment_id == assignment.id,
            LearnerAssignment.learner_user_id == auth.user.id,
        )
    )
    if link is None or assignment.status not in {"active", "closed"}:
        raise AppError(404, "assignment_not_found", "Assignment was not found.")
    previous = db.scalar(
        select(AssignmentSubmission)
        .where(
            AssignmentSubmission.organization_id == auth.organization_id,
            AssignmentSubmission.assignment_id == assignment.id,
            AssignmentSubmission.learner_user_id == auth.user.id,
        )
        .order_by(AssignmentSubmission.revision.desc())
    )
    if previous and previous.status != "revision_requested":
        raise AppError(409, "submission_exists", "A current submission already exists.")
    revision = previous.revision + 1 if previous else 1
    now = datetime.now(UTC)
    submission = AssignmentSubmission(
        organization_id=auth.organization_id,
        assignment_id=assignment.id,
        learner_user_id=auth.user.id,
        parent_submission_id=previous.id if previous else None,
        body=payload.body.strip(),
        evidence_items=payload.evidence_items,
        revision=revision,
        status="pending" if assignment.review_required else "approved",
        submitted_at=now,
    )
    db.add(submission)
    db.flush()
    if assignment.review_required:
        db.add(
            AssignmentReview(
                organization_id=auth.organization_id,
                submission_id=submission.id,
                learner_user_id=auth.user.id,
                content_version=assignment.content_version,
                state="resubmitted" if previous else "pending",
                assigned_at=now,
                revision_count=revision - 1,
                history=[
                    {"state": "resubmitted" if previous else "pending", "at": now.isoformat()}
                ],
            )
        )
    else:
        link.status = "completed"
        link.completed_at = now
    record_audit(db, request, auth, "assignment.submitted", "submission", submission.id)
    db.commit()
    return {"id": submission.id, "revision": revision, "status": submission.status}


@router.get("/reviews")
def review_queue(
    auth: AuthContext = Depends(require_auth),
    db: DatabaseSession = Depends(get_db),
) -> list[dict[str, object]]:
    assert_permission(db, auth, "reviews.view")
    records = db.execute(
        select(AssignmentReview, AssignmentSubmission, Assignment)
        .join(AssignmentSubmission, AssignmentSubmission.id == AssignmentReview.submission_id)
        .join(Assignment, Assignment.id == AssignmentSubmission.assignment_id)
        .where(AssignmentReview.organization_id == auth.organization_id)
        .order_by(AssignmentReview.created_at.desc())
    ).all()
    return [
        {
            "id": review.id,
            "submission_id": submission.id,
            "assignment_id": assignment.id,
            "assignment_title": assignment.title,
            "learner_user_id": review.learner_user_id,
            "state": review.state,
            "revision_count": review.revision_count,
            "content_version": review.content_version,
            "feedback": review.feedback,
        }
        for review, submission, assignment in records
    ]


@router.post("/reviews/{review_id}/decision")
def review_decision(
    review_id: uuid.UUID,
    payload: AssignmentReviewUpdate,
    request: Request,
    auth: AuthContext = Depends(require_csrf),
    db: DatabaseSession = Depends(get_db),
) -> dict[str, object]:
    assert_permission(db, auth, "reviews.perform")
    review = owned(db, AssignmentReview, auth, review_id)
    if review.state not in {"pending", "in_review", "resubmitted"}:
        raise AppError(409, "review_complete", "This review already has a final decision.")
    now = datetime.now(UTC)
    review.reviewer_user_id = auth.user.id
    review.started_at = review.started_at or now
    review.completed_at = now
    review.decision = payload.decision
    review.state = payload.decision
    review.feedback = payload.feedback.strip()
    review.rubric_scores = payload.rubric_scores
    review.history = [
        *review.history,
        {
            "state": payload.decision,
            "at": now.isoformat(),
            "reviewerUserId": str(auth.user.id),
        },
    ]
    submission = owned(db, AssignmentSubmission, auth, review.submission_id)
    submission.status = payload.decision
    assignment_link = db.scalar(
        select(LearnerAssignment).where(
            LearnerAssignment.organization_id == auth.organization_id,
            LearnerAssignment.assignment_id == submission.assignment_id,
            LearnerAssignment.learner_user_id == submission.learner_user_id,
        )
    )
    if payload.decision == "approved" and assignment_link:
        assignment_link.status = "completed"
        assignment_link.completed_at = now
    notify(
        db,
        auth.organization_id,
        submission.learner_user_id,
        f"review_{payload.decision}",
        f"Review {payload.decision.replace('_', ' ')}",
        "A human reviewer recorded a decision and feedback.",
        "/organization/assignments",
    )
    record_audit(db, request, auth, "submission.reviewed", "review", review.id)
    db.commit()
    return {
        "id": review.id,
        "state": review.state,
        "reviewer_user_id": review.reviewer_user_id,
        "completed_at": review.completed_at,
    }


@router.get("/learners/{learner_id}")
def learner_detail(
    learner_id: uuid.UUID,
    auth: AuthContext = Depends(require_auth),
    db: DatabaseSession = Depends(get_db),
) -> dict[str, object]:
    assert_permission(db, auth, "learners.view_detailed_progress")
    membership = db.scalar(
        select(OrganizationMembership).where(
            OrganizationMembership.organization_id == auth.organization_id,
            OrganizationMembership.user_id == learner_id,
            OrganizationMembership.is_active.is_(True),
        )
    )
    if membership is None:
        raise AppError(404, "learner_not_found", "Learner was not found.")
    profile = db.scalar(select(UserProfile).where(UserProfile.user_id == learner_id))
    snapshots = db.scalars(
        select(LearnerSkillState).where(
            LearnerSkillState.organization_id == auth.organization_id,
            LearnerSkillState.user_id == learner_id,
        )
    ).all()
    completions = db.scalars(
        select(CompletionRecord).where(
            CompletionRecord.organization_id == auth.organization_id,
            CompletionRecord.user_id == learner_id,
        )
    ).all()
    return {
        "user_id": learner_id,
        "display_name": profile.display_name if profile else "",
        "skills": [
            {
                "skill_id": item.skill_id,
                "mastery": item.mastery_estimate,
                "confidence": item.confidence,
            }
            for item in snapshots
        ],
        "completion_records": [
            {
                "scope_type": item.scope_type,
                "scope_id": item.scope_id,
                "issued_at": item.issued_at,
                "revoked": item.revoked_at is not None,
            }
            for item in completions
        ],
        "privacy_notice": (
            "Private notes, Sentinel conversations, and activity outside this organization "
            "are excluded."
        ),
    }


@router.get("/notifications")
def notifications(
    auth: AuthContext = Depends(require_auth),
    db: DatabaseSession = Depends(get_db),
) -> dict[str, object]:
    records = db.scalars(
        select(Notification)
        .where(
            Notification.organization_id == auth.organization_id,
            Notification.user_id == auth.user.id,
        )
        .order_by(Notification.created_at.desc())
        .limit(100)
    ).all()
    return {
        "unread_count": sum(item.read_at is None for item in records),
        "items": [
            {
                "id": item.id,
                "event_type": item.event_type,
                "title": item.title,
                "message": item.message,
                "deep_link": item.deep_link,
                "read_at": item.read_at,
                "created_at": item.created_at,
            }
            for item in records
        ],
    }


@router.post("/notifications/{notification_id}/read")
def mark_notification_read(
    notification_id: uuid.UUID,
    auth: AuthContext = Depends(require_csrf),
    db: DatabaseSession = Depends(get_db),
) -> dict[str, str]:
    item = db.scalar(
        select(Notification).where(
            Notification.id == notification_id,
            Notification.organization_id == auth.organization_id,
            Notification.user_id == auth.user.id,
        )
    )
    if item is None:
        raise AppError(404, "notification_not_found", "Notification was not found.")
    item.read_at = datetime.now(UTC)
    db.commit()
    return {"status": "read"}


@router.post("/notifications/read-all")
def mark_all_notifications_read(
    auth: AuthContext = Depends(require_csrf),
    db: DatabaseSession = Depends(get_db),
) -> dict[str, int]:
    records = db.scalars(
        select(Notification).where(
            Notification.organization_id == auth.organization_id,
            Notification.user_id == auth.user.id,
            Notification.read_at.is_(None),
        )
    ).all()
    now = datetime.now(UTC)
    for item in records:
        item.read_at = now
    db.commit()
    return {"updated": len(records)}


@router.post("/shares", status_code=201)
def create_share(
    payload: ShareCreate,
    request: Request,
    auth: AuthContext = Depends(require_csrf),
    db: DatabaseSession = Depends(get_db),
) -> dict[str, object]:
    artifacts = db.scalars(
        select(PortfolioArtifact).where(
            PortfolioArtifact.id.in_(payload.artifact_ids or [uuid.uuid4()]),
            PortfolioArtifact.organization_id == auth.organization_id,
            PortfolioArtifact.user_id == auth.user.id,
            PortfolioArtifact.revoked_at.is_(None),
        )
    ).all()
    completions = db.scalars(
        select(CompletionRecord).where(
            CompletionRecord.id.in_(payload.completion_ids or [uuid.uuid4()]),
            CompletionRecord.organization_id == auth.organization_id,
            CompletionRecord.user_id == auth.user.id,
            CompletionRecord.revoked_at.is_(None),
        )
    ).all()
    if len(artifacts) != len(set(payload.artifact_ids)) or len(completions) != len(
        set(payload.completion_ids)
    ):
        raise AppError(422, "invalid_shared_evidence", "Only your current evidence can be shared.")
    raw_token = new_token()
    share = SharedProfile(
        organization_id=auth.organization_id,
        learner_user_id=auth.user.id,
        display_name=payload.display_name.strip(),
        include_email=payload.include_email,
        token_hash=token_hash(raw_token),
        expires_at=datetime.now(UTC) + timedelta(days=payload.expires_in_days),
    )
    db.add(share)
    db.flush()
    for artifact in artifacts:
        db.add(
            SharedEvidenceItem(
                organization_id=auth.organization_id,
                shared_profile_id=share.id,
                evidence_type="artifact",
                evidence_id=artifact.id,
            )
        )
    for completion in completions:
        db.add(
            SharedEvidenceItem(
                organization_id=auth.organization_id,
                shared_profile_id=share.id,
                evidence_type="completion",
                evidence_id=completion.id,
            )
        )
    record_audit(db, request, auth, "shared_profile.created", "shared_profile", share.id)
    db.commit()
    return {
        "id": share.id,
        "share_token": raw_token,
        "expires_at": share.expires_at,
        "evidence_count": len(artifacts) + len(completions),
    }


@router.get("/shareable-evidence")
def shareable_evidence(
    auth: AuthContext = Depends(require_auth),
    db: DatabaseSession = Depends(get_db),
) -> dict[str, object]:
    artifacts = db.scalars(
        select(PortfolioArtifact)
        .where(
            PortfolioArtifact.organization_id == auth.organization_id,
            PortfolioArtifact.user_id == auth.user.id,
            PortfolioArtifact.revoked_at.is_(None),
        )
        .order_by(PortfolioArtifact.created_at.desc())
    ).all()
    completions = db.scalars(
        select(CompletionRecord)
        .where(
            CompletionRecord.organization_id == auth.organization_id,
            CompletionRecord.user_id == auth.user.id,
            CompletionRecord.revoked_at.is_(None),
        )
        .order_by(CompletionRecord.issued_at.desc())
    ).all()
    return {
        "artifacts": [
            {
                "id": item.id,
                "title": item.title,
                "type": item.artifact_type,
                "verification_state": item.verification_state,
                "source_version": item.source_version,
            }
            for item in artifacts
        ],
        "completion_records": [
            {
                "id": item.id,
                "scope_type": item.scope_type,
                "scope_id": item.scope_id,
                "criteria_version": item.criteria_version,
                "issued_at": item.issued_at,
            }
            for item in completions
        ],
    }


@router.get("/shares")
def list_shares(
    auth: AuthContext = Depends(require_auth),
    db: DatabaseSession = Depends(get_db),
) -> list[dict[str, object]]:
    records = db.scalars(
        select(SharedProfile)
        .where(
            SharedProfile.organization_id == auth.organization_id,
            SharedProfile.learner_user_id == auth.user.id,
        )
        .order_by(SharedProfile.created_at.desc())
    ).all()
    return [
        {
            "id": item.id,
            "display_name": item.display_name,
            "expires_at": item.expires_at,
            "revoked_at": item.revoked_at,
            "status": item.status,
        }
        for item in records
    ]


@router.post("/shares/{share_id}/revoke")
def revoke_share(
    share_id: uuid.UUID,
    request: Request,
    auth: AuthContext = Depends(require_csrf),
    db: DatabaseSession = Depends(get_db),
) -> dict[str, str]:
    share = db.scalar(
        select(SharedProfile).where(
            SharedProfile.id == share_id,
            SharedProfile.organization_id == auth.organization_id,
            SharedProfile.learner_user_id == auth.user.id,
        )
    )
    if share is None:
        raise AppError(404, "share_not_found", "Shared profile was not found.")
    share.revoked_at = datetime.now(UTC)
    share.status = "revoked"
    record_audit(db, request, auth, "shared_profile.revoked", "shared_profile", share.id)
    db.commit()
    return {"status": "revoked"}


def shared_profile_payload(
    db: DatabaseSession,
    share: SharedProfile,
    email: str | None,
) -> dict[str, object]:
    evidence = db.scalars(
        select(SharedEvidenceItem).where(
            SharedEvidenceItem.organization_id == share.organization_id,
            SharedEvidenceItem.shared_profile_id == share.id,
        )
    ).all()
    artifacts: list[dict[str, object]] = []
    completions: list[dict[str, object]] = []
    demonstrated_skills = 0
    human_reviewed_items = 0
    completion_dates: list[datetime] = []
    for item in evidence:
        if item.evidence_type == "artifact":
            artifact = db.scalar(
                select(PortfolioArtifact).where(
                    PortfolioArtifact.id == item.evidence_id,
                    PortfolioArtifact.organization_id == share.organization_id,
                    PortfolioArtifact.user_id == share.learner_user_id,
                    PortfolioArtifact.revoked_at.is_(None),
                )
            )
            if artifact:
                artifacts.append(
                    {
                        "id": artifact.id,
                        "title": artifact.title,
                        "type": artifact.artifact_type,
                        "verification_state": artifact.verification_state,
                        "source_version": artifact.source_version,
                    }
                )
                if artifact.verification_state == "verified":
                    human_reviewed_items += 1
        elif item.evidence_type == "completion":
            completion = db.scalar(
                select(CompletionRecord).where(
                    CompletionRecord.id == item.evidence_id,
                    CompletionRecord.organization_id == share.organization_id,
                    CompletionRecord.user_id == share.learner_user_id,
                    CompletionRecord.revoked_at.is_(None),
                )
            )
            if completion:
                completions.append(
                    {
                        "id": completion.id,
                        "verification_id": completion.verification_id,
                        "scope_type": completion.scope_type,
                        "scope_id": completion.scope_id,
                        "criteria_version": completion.criteria_version,
                        "issued_at": completion.issued_at,
                        "skills": completion.skill_summary,
                    }
                )
                demonstrated_skills += len(completion.skill_summary)
                completion_dates.append(completion.issued_at)
    return {
        "display_name": share.display_name,
        "email": email if share.include_email else None,
        "expires_at": share.expires_at,
        "artifacts": artifacts,
        "completion_records": completions,
        "dimensions": {
            "demonstrated_skills": demonstrated_skills,
            "evidence_depth": len(artifacts) + len(completions),
            "human_reviewed_items": human_reviewed_items,
            "recency": max(completion_dates, default=None),
        },
        "limitations": (
            "This is learner-selected evidence, not a hire score or employment guarantee."
        ),
    }


@router.get("/shares/{share_id}/preview")
def preview_share(
    share_id: uuid.UUID,
    auth: AuthContext = Depends(require_auth),
    db: DatabaseSession = Depends(get_db),
) -> dict[str, object]:
    share = db.scalar(
        select(SharedProfile).where(
            SharedProfile.id == share_id,
            SharedProfile.organization_id == auth.organization_id,
            SharedProfile.learner_user_id == auth.user.id,
        )
    )
    if share is None:
        raise AppError(404, "share_not_found", "Shared profile was not found.")
    return shared_profile_payload(db, share, auth.user.email)


@public_router.get("/{share_token}")
def verify_share(
    share_token: str,
    request: Request,
    db: DatabaseSession = Depends(get_db),
) -> dict[str, object]:
    now = datetime.now(UTC)
    share = db.scalar(
        select(SharedProfile).where(
            SharedProfile.token_hash == token_hash(share_token),
            SharedProfile.status == "active",
            SharedProfile.revoked_at.is_(None),
            SharedProfile.expires_at > now,
        )
    )
    if share is None:
        raise AppError(404, "share_unavailable", "Shared profile is invalid, expired, or revoked.")
    user = db.get(User, share.learner_user_id)
    db.add(
        SharedProfileAccess(
            shared_profile_id=share.id,
            recruiter_user_id=None,
            action="viewed",
            accessed_at=now,
            request_id=request_id(request),
        )
    )
    audit(
        db,
        "shared_profile.accessed",
        "success",
        None,
        share.organization_id,
        request_id(request),
        "shared_profile",
        str(share.id),
    )
    db.commit()
    return shared_profile_payload(db, share, user.email if user else None)


@router.post("/shares/{share_id}/evidence-requests", status_code=201)
def request_evidence(
    share_id: uuid.UUID,
    payload: EvidenceRequestCreate,
    auth: AuthContext = Depends(require_csrf),
    db: DatabaseSession = Depends(get_db),
) -> dict[str, object]:
    assert_permission(db, auth, "recruiter_evidence.request")
    share = db.scalar(
        select(SharedProfile).where(
            SharedProfile.id == share_id,
            SharedProfile.status == "active",
            SharedProfile.revoked_at.is_(None),
            SharedProfile.expires_at > datetime.now(UTC),
        )
    )
    if share is None:
        raise AppError(404, "share_unavailable", "Shared profile is unavailable.")
    item = EvidenceRequest(
        organization_id=auth.organization_id,
        shared_profile_id=share.id,
        requested_by_user_id=auth.user.id,
        message=payload.message.strip(),
    )
    db.add(item)
    notify(
        db,
        share.organization_id,
        share.learner_user_id,
        "recruiter_evidence_request",
        "Additional evidence requested",
        "A recruiter requested additional learner-controlled evidence.",
        "/portfolio/sharing",
    )
    db.commit()
    return {"id": item.id, "status": item.status}


@router.get("/reports/{report_type}.csv")
def export_report(
    report_type: str,
    request: Request,
    auth: AuthContext = Depends(require_auth),
    db: DatabaseSession = Depends(get_db),
) -> Response:
    assert_permission(db, auth, "reports.export")
    if report_type not in {
        "cohort-progress",
        "assignment-completion",
        "employee-training",
        "project-review",
        "audit",
    }:
        raise AppError(404, "report_not_found", "Report type was not found.")
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(
        [
            "CyberMentor report",
            report_type,
            "generated_at",
            datetime.now(UTC).isoformat(),
            "organization_id",
            str(auth.organization_id),
        ]
    )
    writer.writerow(["definition", "Persisted tenant-scoped platform events only"])
    writer.writerow(["limitations", "Mastery and readiness are estimates, not guarantees"])
    writer.writerow(["assignment_id", "title", "status", "assigned", "completed", "due_at"])
    assignments = db.scalars(
        select(Assignment).where(Assignment.organization_id == auth.organization_id)
    ).all()
    for item in assignments:
        assigned = db.scalar(
            select(func.count(LearnerAssignment.id)).where(
                LearnerAssignment.organization_id == auth.organization_id,
                LearnerAssignment.assignment_id == item.id,
            )
        )
        completed = db.scalar(
            select(func.count(LearnerAssignment.id)).where(
                LearnerAssignment.organization_id == auth.organization_id,
                LearnerAssignment.assignment_id == item.id,
                LearnerAssignment.status == "completed",
            )
        )
        writer.writerow(
            [item.id, item.title, item.status, assigned or 0, completed or 0, item.due_at]
        )
    export = ReportExport(
        organization_id=auth.organization_id,
        generated_by_user_id=auth.user.id,
        report_type=report_type,
        filters={},
        row_count=len(assignments),
        generated_at=datetime.now(UTC),
    )
    db.add(export)
    db.flush()
    record_audit(db, request, auth, "report.exported", "report_export", export.id)
    db.commit()
    return Response(
        content=output.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{report_type}.csv"'},
    )
