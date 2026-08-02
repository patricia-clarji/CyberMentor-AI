import secrets
import uuid
from datetime import UTC, datetime

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session as DatabaseSession

from app.core.errors import AppError
from app.db.session import get_db
from app.identity.dependencies import AuthContext, assert_permission, require_auth, require_csrf
from app.learning.flagship_project import FLAGSHIP_PROJECT, FLAGSHIP_PROJECT_VERSION
from app.models.portfolio import (
    CompletionRecord,
    Portfolio,
    PortfolioArtifact,
    Project,
    ProjectMilestone,
    ProjectReview,
    ProjectSubmission,
    Rubric,
    RubricCriterion,
)
from app.schemas.projects import (
    ProjectMilestoneResponse,
    ProjectResponse,
    ProjectReviewRequest,
    ProjectReviewResponse,
    ProjectSubmissionRequest,
    ProjectSubmissionResponse,
    RubricCriterionResponse,
)

router = APIRouter(prefix="/projects", tags=["projects"])


def flagship_project(
    db: DatabaseSession,
) -> tuple[Project, Rubric, list[RubricCriterion]]:
    project = db.scalar(
        select(Project).where(
            Project.stable_key == FLAGSHIP_PROJECT["stable_key"],
            Project.version == FLAGSHIP_PROJECT_VERSION,
        )
    )
    if project is None:
        raise AppError(
            503,
            "competition_seed_required",
            "The professional project is not seeded. Run the documented seed command.",
        )
    rubric = db.scalar(
        select(Rubric).where(
            Rubric.project_id == project.id,
            Rubric.version == FLAGSHIP_PROJECT_VERSION,
            Rubric.status == "published",
        )
    )
    if rubric is None:
        raise AppError(503, "project_rubric_missing", "The published rubric is unavailable.")
    criteria = list(
        db.scalars(
            select(RubricCriterion)
            .where(RubricCriterion.rubric_id == rubric.id)
            .order_by(RubricCriterion.stable_key)
        ).all()
    )
    return project, rubric, criteria


@router.get("/flagship", response_model=ProjectResponse)
def get_flagship_project(
    _: AuthContext = Depends(require_auth),
    db: DatabaseSession = Depends(get_db),
) -> ProjectResponse:
    project, rubric, criteria = flagship_project(db)
    milestones = db.scalars(
        select(ProjectMilestone)
        .where(ProjectMilestone.project_id == project.id)
        .order_by(ProjectMilestone.position)
    ).all()
    return ProjectResponse(
        id=project.id,
        stable_key=project.stable_key,
        publication_id=project.publication_id,
        title=project.title,
        description=project.description,
        version=project.version,
        milestones=[
            ProjectMilestoneResponse(
                position=item.position,
                title=item.title,
                requirement=item.requirement,
            )
            for item in milestones
        ],
        rubric_version=rubric.version,
        rubric=[
            RubricCriterionResponse(
                key=item.stable_key,
                description=item.description,
                weight=item.weight,
                pass_standard=item.pass_standard,
            )
            for item in criteria
        ],
        review_notice=(
            "Submission creates durable learner evidence but does not pass automatically. "
            "An authorized human reviewer in the same organization must apply this rubric."
        ),
    )


@router.post(
    "/flagship/submissions",
    response_model=ProjectSubmissionResponse,
    status_code=201,
)
def submit_flagship_project(
    payload: ProjectSubmissionRequest,
    auth: AuthContext = Depends(require_csrf),
    db: DatabaseSession = Depends(get_db),
) -> ProjectSubmissionResponse:
    project, _, _ = flagship_project(db)
    now = datetime.now(UTC)
    submission = ProjectSubmission(
        organization_id=auth.organization_id,
        user_id=auth.user.id,
        project_id=project.id,
        body=payload.body.strip(),
        reflection=payload.reflection.strip(),
        status="awaiting_review",
        submitted_at=now,
        version=1,
    )
    db.add(submission)
    db.commit()
    return ProjectSubmissionResponse(
        id=submission.id,
        status=submission.status,
        submitted_at=submission.submitted_at.isoformat(),
        version=submission.version,
        review_notice=(
            "Saved and awaiting an authorized human review. No completion claim has been issued."
        ),
    )


@router.get("/flagship/submissions", response_model=list[ProjectSubmissionResponse])
def list_own_submissions(
    auth: AuthContext = Depends(require_auth),
    db: DatabaseSession = Depends(get_db),
) -> list[ProjectSubmissionResponse]:
    project, _, _ = flagship_project(db)
    records = db.scalars(
        select(ProjectSubmission)
        .where(
            ProjectSubmission.organization_id == auth.organization_id,
            ProjectSubmission.user_id == auth.user.id,
            ProjectSubmission.project_id == project.id,
        )
        .order_by(ProjectSubmission.submitted_at.desc())
    ).all()
    return [
        ProjectSubmissionResponse(
            id=item.id,
            status=item.status,
            submitted_at=item.submitted_at.isoformat(),
            version=item.version,
            review_notice=(
                "A human review is required before this project becomes verified evidence."
            ),
        )
        for item in records
    ]


@router.post(
    "/submissions/{submission_id}/review",
    response_model=ProjectReviewResponse,
)
def review_submission(
    submission_id: uuid.UUID,
    payload: ProjectReviewRequest,
    auth: AuthContext = Depends(require_csrf),
    db: DatabaseSession = Depends(get_db),
) -> ProjectReviewResponse:
    assert_permission(db, auth, "reviews.perform")
    submission = db.scalar(
        select(ProjectSubmission).where(
            ProjectSubmission.id == submission_id,
            ProjectSubmission.organization_id == auth.organization_id,
        )
    )
    if submission is None:
        raise AppError(404, "project_submission_not_found", "Submission was not found.")
    if submission.status != "awaiting_review":
        raise AppError(409, "project_already_reviewed", "Submission is already reviewed.")
    project, rubric, criteria = flagship_project(db)
    if submission.project_id != project.id:
        raise AppError(404, "project_submission_not_found", "Submission was not found.")
    expected = {item.stable_key for item in criteria}
    supplied = {item.key for item in payload.criteria}
    if supplied != expected or len(supplied) != len(payload.criteria):
        raise AppError(
            422,
            "rubric_incomplete",
            "Review every published criterion exactly once.",
        )
    passed = all(item.passed for item in payload.criteria)
    now = datetime.now(UTC)
    db.add(
        ProjectReview(
            organization_id=auth.organization_id,
            submission_id=submission.id,
            reviewer_user_id=auth.user.id,
            rubric_id=rubric.id,
            passed=passed,
            criterion_results=[item.model_dump() for item in payload.criteria],
            feedback=payload.feedback.strip(),
            reviewed_at=now,
        )
    )
    submission.status = "passed" if passed else "revision_required"
    submission.version += 1
    artifact = None
    completion = None
    if passed:
        portfolio = db.scalar(
            select(Portfolio).where(
                Portfolio.organization_id == auth.organization_id,
                Portfolio.user_id == submission.user_id,
            )
        )
        if portfolio is None:
            portfolio = Portfolio(
                organization_id=auth.organization_id,
                user_id=submission.user_id,
                visibility="private",
            )
            db.add(portfolio)
            db.flush()
        artifact = PortfolioArtifact(
            organization_id=auth.organization_id,
            user_id=submission.user_id,
            portfolio_id=portfolio.id,
            artifact_type="human_reviewed_project",
            source_id=str(submission.id),
            title=project.title,
            verification_state="verified",
            visibility="private",
        )
        db.add(artifact)
        completion = CompletionRecord(
            organization_id=auth.organization_id,
            user_id=submission.user_id,
            verification_id=secrets.token_urlsafe(18),
            criteria_version=rubric.version,
            scope_type="professional_project",
            scope_id=project.stable_key,
            skill_summary=[
                {"skill": criterion.stable_key, "result": "reviewer_passed"}
                for criterion in criteria
            ],
            evidence_summary=[
                {
                    "type": "human_reviewed_project",
                    "submissionId": str(submission.id),
                    "reviewerUserId": str(auth.user.id),
                }
            ],
            issued_at=now,
        )
        db.add(completion)
    db.commit()
    return ProjectReviewResponse(
        submission_id=submission.id,
        passed=passed,
        status=submission.status,
        portfolio_artifact_id=artifact.id if artifact else None,
        completion_verification_id=completion.verification_id if completion else None,
    )
