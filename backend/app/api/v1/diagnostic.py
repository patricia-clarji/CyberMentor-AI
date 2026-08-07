import hashlib
import uuid
from datetime import UTC, datetime

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session as DatabaseSession

from app.core.errors import AppError
from app.db.session import get_db
from app.identity.dependencies import AuthContext, require_csrf
from app.learning.diagnostic import (
    diagnostic_version,
    grade,
    ordered_questions,
    public_question,
    rebuild_roadmap,
    record_skill_evidence,
)
from app.learning.skill_classifier import predict
from app.learning.soc_profile import SOC_PROFILE_VERSION
from app.models.assessment import AssessmentAttempt, QuestionResponse
from app.models.learning import DiagnosticAttempt, LearnerProfile, Skill, SkillEvidence
from app.schemas.diagnostic import (
    DiagnosticAnswerRequest,
    DiagnosticAnswerResponse,
    DiagnosticStartRequest,
    DiagnosticStartResponse,
)

router = APIRouter(prefix="/diagnostic", tags=["diagnostic"])


@router.post("/start", response_model=DiagnosticStartResponse, status_code=201)
def start_diagnostic(
    payload: DiagnosticStartRequest | None = None,
    auth: AuthContext = Depends(require_csrf),
    db: DatabaseSession = Depends(get_db),
) -> DiagnosticStartResponse:
    version = diagnostic_version(db)
    questions = ordered_questions(db, version)
    if not questions:
        raise AppError(503, "diagnostic_empty", "The diagnostic has no published questions.")
    now = datetime.now(UTC)
    attempt = AssessmentAttempt(
        organization_id=auth.organization_id,
        user_id=auth.user.id,
        assessment_version_id=version.id,
        status="started",
        started_at=now,
    )
    db.add(attempt)
    db.flush()
    db.add(
        DiagnosticAttempt(
            organization_id=auth.organization_id,
            user_id=auth.user.id,
            assessment_version_id=version.id,
            assessment_attempt_id=attempt.id,
            status="started",
        )
    )
    if payload and payload.self_assessment_text:
        signal = predict(payload.self_assessment_text)
        if signal:
            skill_key, confidence = signal
            skill = db.scalar(select(Skill).where(Skill.stable_key == skill_key))
            if skill:
                digest = hashlib.sha256(
                    payload.self_assessment_text.strip().encode("utf-8")
                ).hexdigest()
                db.add(
                    SkillEvidence(
                        organization_id=auth.organization_id,
                        user_id=auth.user.id,
                        skill_id=skill.id,
                        source_type="ml_self_assessment",
                        source_id=str(attempt.id),
                        source_version="skill-classifier-1.0.0",
                        score=confidence,
                        independence=0.0,
                        hints_used=0,
                        attempts=1,
                        occurred_at=now,
                        provenance_hash=digest,
                    )
                )
    db.commit()
    question, question_version = questions[0]
    return DiagnosticStartResponse(
        attempt_id=attempt.id,
        profile_version=SOC_PROFILE_VERSION,
        question=public_question(question, question_version, 1, len(questions)),
    )


@router.post(
    "/{attempt_id}/responses/{question_version_id}",
    response_model=DiagnosticAnswerResponse,
)
def answer_diagnostic(
    attempt_id: uuid.UUID,
    question_version_id: uuid.UUID,
    payload: DiagnosticAnswerRequest,
    auth: AuthContext = Depends(require_csrf),
    db: DatabaseSession = Depends(get_db),
) -> DiagnosticAnswerResponse:
    attempt = db.scalar(
        select(AssessmentAttempt).where(
            AssessmentAttempt.id == attempt_id,
            AssessmentAttempt.organization_id == auth.organization_id,
            AssessmentAttempt.user_id == auth.user.id,
        )
    )
    if attempt is None:
        raise AppError(404, "diagnostic_not_found", "Diagnostic attempt was not found.")
    if attempt.status != "started":
        raise AppError(409, "diagnostic_closed", "Diagnostic attempt is already closed.")
    version = diagnostic_version(db)
    questions = ordered_questions(db, version)
    answered_ids = set(
        db.scalars(
            select(QuestionResponse.question_version_id).where(
                QuestionResponse.attempt_id == attempt.id
            )
        ).all()
    )
    next_pair = next(
        (pair for pair in questions if pair[1].id not in answered_ids),
        None,
    )
    if next_pair is None or next_pair[1].id != question_version_id:
        raise AppError(
            409,
            "diagnostic_sequence",
            "Submit the current diagnostic question before continuing.",
        )
    question, question_version = next_pair
    correct = grade(question_version.private_answer, payload.response)
    now = datetime.now(UTC)
    db.add(
        QuestionResponse(
            organization_id=auth.organization_id,
            user_id=auth.user.id,
            attempt_id=attempt.id,
            question_version_id=question_version.id,
            response=payload.response,
            correct=correct,
            score=1.0 if correct else 0.0,
            attempts=1,
            hints_used=0,
            evaluator_version="diagnostic-grader-1.0.0",
        )
    )
    record_skill_evidence(
        db,
        auth,
        question,
        question_version,
        payload.response,
        correct,
        now,
    )
    db.flush()
    answered_count = (
        db.scalar(
            select(func.count(QuestionResponse.id)).where(QuestionResponse.attempt_id == attempt.id)
        )
        or 0
    )
    completed = answered_count >= len(questions)
    next_question = None
    roadmap_updated = False
    if completed:
        attempt.status = "completed"
        attempt.submitted_at = now
        scores = db.scalars(
            select(QuestionResponse.score).where(QuestionResponse.attempt_id == attempt.id)
        ).all()
        attempt.score = sum(score or 0 for score in scores) / len(questions)
        diagnostic = db.scalar(
            select(DiagnosticAttempt).where(DiagnosticAttempt.assessment_attempt_id == attempt.id)
        )
        if diagnostic:
            diagnostic.status = "completed"
            diagnostic.completed_at = now
        profile = db.scalar(
            select(LearnerProfile).where(
                LearnerProfile.organization_id == auth.organization_id,
                LearnerProfile.user_id == auth.user.id,
            )
        )
        weekly_minutes = profile.weekly_minutes if profile and profile.weekly_minutes else 360
        rebuild_roadmap(db, auth, weekly_minutes)
        roadmap_updated = True
    else:
        next_index = int(answered_count)
        next_question = public_question(
            questions[next_index][0],
            questions[next_index][1],
            next_index + 1,
            len(questions),
        )
    db.commit()
    return DiagnosticAnswerResponse(
        correct=correct,
        explanation=question_version.explanation,
        confidence_notice=(
            "This result is initial evidence only. Practical confirmation is required."
        ),
        completed=completed,
        next_question=next_question,
        roadmap_updated=roadmap_updated,
    )
