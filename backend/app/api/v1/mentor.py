import uuid
from typing import Any, Literal, cast

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session as DatabaseSession

from app.core.config import Settings, get_settings
from app.core.errors import AppError
from app.db.session import get_db
from app.identity.dependencies import AuthContext, require_auth, require_csrf
from app.mentor.adaptation import build_learner_context
from app.mentor.service import answer_question
from app.models.mentor import (
    MentorMessage,
    MentorMessageFeedback,
    MentorThread,
)
from app.schemas.mentor import (
    MentorAnswerResponse,
    MentorFeedbackRequest,
    MentorFeedbackResponse,
    MentorHistoryMessage,
    MentorLearnerModelResponse,
    MentorQuestionRequest,
    MentorThreadHistoryResponse,
    MentorThreadRequest,
    MentorThreadResponse,
)

router = APIRouter(prefix="/mentor", tags=["mentor"])


def owned_thread(
    db: DatabaseSession,
    auth: AuthContext,
    thread_id: uuid.UUID,
) -> MentorThread:
    thread = db.scalar(
        select(MentorThread).where(
            MentorThread.id == thread_id,
            MentorThread.organization_id == auth.organization_id,
            MentorThread.user_id == auth.user.id,
            MentorThread.status == "active",
        )
    )
    if thread is None:
        raise AppError(404, "mentor_thread_not_found", "Mentor thread was not found.")
    return thread


def _thread_response(thread: MentorThread) -> MentorThreadResponse:
    return MentorThreadResponse(
        id=thread.id,
        context_type=thread.context_type,
        context_id=thread.context_id,
        status=thread.status,
    )


@router.get("/threads", response_model=list[MentorThreadResponse])
def list_threads(
    auth: AuthContext = Depends(require_auth),
    db: DatabaseSession = Depends(get_db),
) -> list[MentorThreadResponse]:
    threads = db.scalars(
        select(MentorThread)
        .where(
            MentorThread.organization_id == auth.organization_id,
            MentorThread.user_id == auth.user.id,
            MentorThread.status == "active",
        )
        .order_by(MentorThread.updated_at.desc())
    ).all()
    return [_thread_response(thread) for thread in threads]


@router.post("/threads", response_model=MentorThreadResponse, status_code=201)
def create_thread(
    payload: MentorThreadRequest,
    auth: AuthContext = Depends(require_csrf),
    db: DatabaseSession = Depends(get_db),
) -> MentorThreadResponse:
    existing = db.scalar(
        select(MentorThread)
        .where(
            MentorThread.organization_id == auth.organization_id,
            MentorThread.user_id == auth.user.id,
            MentorThread.context_type == payload.context_type,
            MentorThread.context_id == payload.context_id,
            MentorThread.status == "active",
        )
        .order_by(MentorThread.updated_at.desc())
    )
    if existing is not None:
        return _thread_response(existing)
    thread = MentorThread(
        organization_id=auth.organization_id,
        user_id=auth.user.id,
        context_type=payload.context_type,
        context_id=payload.context_id,
        status="active",
    )
    db.add(thread)
    db.commit()
    return _thread_response(thread)


@router.get(
    "/threads/{thread_id}",
    response_model=MentorThreadHistoryResponse,
)
def get_thread_history(
    thread_id: uuid.UUID,
    auth: AuthContext = Depends(require_auth),
    db: DatabaseSession = Depends(get_db),
) -> MentorThreadHistoryResponse:
    thread = owned_thread(db, auth, thread_id)
    messages = db.scalars(
        select(MentorMessage)
        .where(
            MentorMessage.thread_id == thread.id,
            MentorMessage.organization_id == auth.organization_id,
            MentorMessage.user_id == auth.user.id,
        )
        .order_by(MentorMessage.created_at)
    ).all()
    return MentorThreadHistoryResponse(
        thread=_thread_response(thread),
        messages=[
            MentorHistoryMessage(
                id=message.id,
                role=cast(Literal["user", "assistant"], message.role),
                body=message.body,
                delivery_mode=message.mode,
                mentor_mode=message.mentor_mode,
                provider_generated=message.provider_generated,
                reasoning_summary=message.reasoning_summary,
                related_skills=list(message.related_skills),
                recommended_action=message.recommended_action,
                created_at=message.created_at,
            )
            for message in messages
        ],
    )


@router.post(
    "/threads/{thread_id}/messages",
    response_model=MentorAnswerResponse,
)
def ask_mentor(
    thread_id: uuid.UUID,
    payload: MentorQuestionRequest,
    auth: AuthContext = Depends(require_csrf),
    db: DatabaseSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> MentorAnswerResponse:
    thread = owned_thread(db, auth, thread_id)
    return MentorAnswerResponse.model_validate(
        answer_question(
            db,
            auth,
            thread,
            payload.question,
            settings,
        )
    )


@router.post(
    "/threads/{thread_id}/messages/{message_id}/feedback",
    response_model=MentorFeedbackResponse,
)
def save_message_feedback(
    thread_id: uuid.UUID,
    message_id: uuid.UUID,
    payload: MentorFeedbackRequest,
    auth: AuthContext = Depends(require_csrf),
    db: DatabaseSession = Depends(get_db),
) -> MentorFeedbackResponse:
    thread = owned_thread(db, auth, thread_id)
    message = db.scalar(
        select(MentorMessage).where(
            MentorMessage.id == message_id,
            MentorMessage.thread_id == thread.id,
            MentorMessage.organization_id == auth.organization_id,
            MentorMessage.user_id == auth.user.id,
            MentorMessage.role == "assistant",
        )
    )
    if message is None:
        raise AppError(404, "mentor_message_not_found", "Mentor message was not found.")
    feedback = db.scalar(
        select(MentorMessageFeedback).where(
            MentorMessageFeedback.message_id == message.id,
            MentorMessageFeedback.organization_id == auth.organization_id,
            MentorMessageFeedback.user_id == auth.user.id,
        )
    )
    if feedback is None:
        feedback = MentorMessageFeedback(
            organization_id=auth.organization_id,
            user_id=auth.user.id,
            message_id=message.id,
            rating=payload.rating,
            issue_tags=list(payload.issue_tags),
            comment=payload.comment,
        )
        db.add(feedback)
    else:
        feedback.rating = payload.rating
        feedback.issue_tags = list(payload.issue_tags)
        feedback.comment = payload.comment
    db.commit()
    return MentorFeedbackResponse(
        message_id=message.id,
        rating=feedback.rating,
        saved=True,
    )


@router.get("/learner-model", response_model=MentorLearnerModelResponse)
def get_learner_model(
    auth: AuthContext = Depends(require_auth),
    db: DatabaseSession = Depends(get_db),
) -> MentorLearnerModelResponse:
    thread = db.scalar(
        select(MentorThread)
        .where(
            MentorThread.organization_id == auth.organization_id,
            MentorThread.user_id == auth.user.id,
            MentorThread.status == "active",
        )
        .order_by(MentorThread.updated_at.desc())
    )
    if thread is None:
        thread = MentorThread(
            organization_id=auth.organization_id,
            user_id=auth.user.id,
            context_type="general",
            context_id=None,
            status="active",
        )
        db.add(thread)
        db.flush()
    context = build_learner_context(db, auth, thread)
    db.commit()
    payload: dict[str, Any] = {
        "weak_skills": context["weakSkills"],
        "strong_skills": context["strongSkills"],
        "misconceptions": context["misconceptions"],
        "completed_labs": context["completedLabs"],
        "completed_missions": context["completedMissions"],
        "hint_history": context["hintHistory"],
        "preferred_explanations": context["preferredExplanations"],
        "learning_pace": context["learningPace"],
        "confidence_estimate": context["confidenceEstimate"],
        "independence": context["independence"],
        "recent_failures": context["recentFailures"],
        "recent_improvements": context["recentImprovements"],
        "study_streak": context["studyStreak"],
        "review_schedule": context["reviewSchedule"],
    }
    return MentorLearnerModelResponse.model_validate(payload)
