import json
import uuid
from datetime import UTC, datetime

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session as DatabaseSession

from app.core.errors import AppError
from app.db.session import get_db
from app.identity.dependencies import AuthContext, require_auth, require_csrf
from app.learning.mission_service import (
    build_submission_result,
    evaluate_mission_action,
    next_sequence,
    ordered_stages,
    owned_session,
    public_stage,
    published_mission,
    stage_definition,
)
from app.models.identity import User, UserProfile
from app.models.mission import (
    InvestigationReplay,
    MissionAction,
    MissionEvidence,
    MissionHintUse,
    MissionSession,
    MissionStage,
    MissionSubmission,
)
from app.models.portfolio import CompletionRecord
from app.schemas.mission import (
    CompletionVerificationResponse,
    MissionActionRequest,
    MissionActionResponse,
    MissionHintResponse,
    MissionScoresResponse,
    MissionStartResponse,
    MissionSubmissionRequest,
    MissionSubmissionResponse,
    ReplayResponse,
)

router = APIRouter(prefix="/missions", tags=["missions"])


@router.post("/flagship/start", response_model=MissionStartResponse, status_code=201)
def start_flagship_mission(
    auth: AuthContext = Depends(require_csrf),
    db: DatabaseSession = Depends(get_db),
) -> MissionStartResponse:
    mission, version = published_mission(db)
    stages = ordered_stages(db, version.id)
    if not stages:
        raise AppError(503, "mission_empty", "The flagship mission has no published stages.")
    now = datetime.now(UTC)
    mission_session = MissionSession(
        organization_id=auth.organization_id,
        user_id=auth.user.id,
        mission_version_id=version.id,
        current_stage_id=stages[0].id,
        status="active",
        started_at=now,
        version=1,
    )
    db.add(mission_session)
    db.flush()
    response = MissionStartResponse(
        session_id=mission_session.id,
        mission_key=mission.stable_key,
        title=mission.title,
        fictional_organization=version.fictional_organization,
        business_context=version.business_context,
        briefing=version.briefing,
        safety_notice=(
            "Authorized defensive training only. All people, organizations, systems, "
            "addresses, and telemetry in this mission are synthetic."
        ),
        status=mission_session.status,
        stage=public_stage(db, auth, mission_session, stages[0]),
    )
    db.commit()
    return response


@router.post(
    "/sessions/{session_id}/actions",
    response_model=MissionActionResponse,
)
def record_action(
    session_id: uuid.UUID,
    payload: MissionActionRequest,
    auth: AuthContext = Depends(require_csrf),
    db: DatabaseSession = Depends(get_db),
) -> MissionActionResponse:
    mission_session = owned_session(db, auth, session_id, allowed_statuses={"active"})
    stage = db.get(MissionStage, mission_session.current_stage_id)
    if stage is None:
        raise AppError(409, "mission_stage_missing", "The current mission stage is unavailable.")
    definition = stage_definition(stage)
    now = datetime.now(UTC)
    resource_id = (
        payload.resource_id if payload.action_type == "open_evidence" else payload.decision_id
    )
    outcome, feedback, resource_content, advances = evaluate_mission_action(
        definition,
        payload.action_type,
        payload.resource_id,
        payload.decision_id,
    )
    if payload.action_type == "open_evidence":
        resource = next(
            (item for item in definition["resources"] if item["id"] == payload.resource_id),
            None,
        )
        assert resource is not None
        existing = db.scalar(
            select(MissionEvidence).where(
                MissionEvidence.mission_session_id == mission_session.id,
                MissionEvidence.evidence_key == resource["id"],
            )
        )
        if existing is None:
            db.add(
                MissionEvidence(
                    organization_id=auth.organization_id,
                    user_id=auth.user.id,
                    mission_session_id=mission_session.id,
                    evidence_key=resource["id"],
                    classification=resource["classification"],
                    opened_at=now,
                )
            )
    else:
        if advances:
            stages = ordered_stages(db, mission_session.mission_version_id)
            next_stage = next(
                (candidate for candidate in stages if candidate.position == stage.position + 1),
                None,
            )
            if next_stage is None:
                mission_session.status = "ready_to_submit"
            else:
                mission_session.current_stage_id = next_stage.id
            mission_session.version += 1
    db.add(
        MissionAction(
            organization_id=auth.organization_id,
            user_id=auth.user.id,
            mission_session_id=mission_session.id,
            stage_id=stage.id,
            sequence=next_sequence(db, mission_session.id),
            action_type=payload.action_type,
            resource_id=resource_id,
            learner_input=payload.decision_id,
            outcome=outcome,
            duration_seconds=payload.duration_seconds,
            occurred_at=now,
        )
    )
    db.flush()
    response_stage = db.get(MissionStage, mission_session.current_stage_id) or stage
    response = MissionActionResponse(
        outcome=outcome,
        feedback=feedback,
        status=mission_session.status,
        resource_content=resource_content,
        stage=public_stage(db, auth, mission_session, response_stage),
    )
    db.commit()
    return response


@router.post(
    "/sessions/{session_id}/hint",
    response_model=MissionHintResponse,
)
def request_hint(
    session_id: uuid.UUID,
    auth: AuthContext = Depends(require_csrf),
    db: DatabaseSession = Depends(get_db),
) -> MissionHintResponse:
    mission_session = owned_session(db, auth, session_id, allowed_statuses={"active"})
    stage = db.get(MissionStage, mission_session.current_stage_id)
    if stage is None:
        raise AppError(409, "mission_stage_missing", "The current mission stage is unavailable.")
    prior = list(
        db.scalars(
            select(MissionHintUse).where(
                MissionHintUse.mission_session_id == mission_session.id,
                MissionHintUse.stage_id == stage.id,
            )
        ).all()
    )
    level = min(5, len(prior) + 1)
    hint = stage_definition(stage)["hints"][level - 1]
    db.add(
        MissionHintUse(
            organization_id=auth.organization_id,
            user_id=auth.user.id,
            mission_session_id=mission_session.id,
            stage_id=stage.id,
            level=level,
            hint_type="progressive",
            used_at=datetime.now(UTC),
        )
    )
    db.commit()
    return MissionHintResponse(
        level=level,
        hint=hint,
        independence_notice=(
            "Hints are recorded as part of independence evidence; they do not prevent completion."
        ),
    )


@router.post(
    "/sessions/{session_id}/submit",
    response_model=MissionSubmissionResponse,
)
def submit_mission(
    session_id: uuid.UUID,
    payload: MissionSubmissionRequest,
    auth: AuthContext = Depends(require_csrf),
    db: DatabaseSession = Depends(get_db),
) -> MissionSubmissionResponse:
    mission_session = owned_session(db, auth, session_id, allowed_statuses={"ready_to_submit"})
    now = datetime.now(UTC)
    db.add(
        MissionSubmission(
            organization_id=auth.organization_id,
            user_id=auth.user.id,
            mission_session_id=mission_session.id,
            report_body=json.dumps(payload.model_dump(), sort_keys=True),
            learner_authored=True,
            submitted_at=now,
            version=1,
        )
    )
    result, replay, artifact, completion = build_submission_result(
        db, auth, mission_session, payload
    )
    db.flush()
    strengths = []
    improvements = []
    if result.practical_score == 1:
        strengths.append("All required investigation decisions were completed.")
    else:
        improvements.append("Revisit missed or unsupported investigation decisions.")
    if result.conceptual_score >= 0.85:
        strengths.append("The report was grounded in the available evidence.")
    else:
        improvements.append("Open and correlate every relevant evidence source.")
    if result.decision_score == 1:
        strengths.append("The classification and response preserve scope and authority.")
    else:
        improvements.append("Use a scoped classification and authorized defensive response.")
    if result.reporting_score < 0.75:
        improvements.append("Make the rationale, uncertainty, next steps, and reflection explicit.")
    response = MissionSubmissionResponse(
        passed=result.passed,
        scores=MissionScoresResponse(
            conceptual=result.conceptual_score,
            practical=result.practical_score,
            decision=result.decision_score,
            independence=result.independence_score,
            reporting=result.reporting_score,
        ),
        strengths=strengths,
        improvements=improvements,
        replay_id=replay.id,
        portfolio_artifact_id=artifact.id if artifact else None,
        completion_verification_id=completion.verification_id if completion else None,
        scope_notice=(
            "This verifies completion of one synthetic workplace mission. "
            "It is not an industry certification or a claim of job readiness."
        ),
    )
    db.commit()
    return response


@router.get("/sessions/{session_id}/replay", response_model=ReplayResponse)
def get_replay(
    session_id: uuid.UUID,
    auth: AuthContext = Depends(require_auth),
    db: DatabaseSession = Depends(get_db),
) -> ReplayResponse:
    owned_session(db, auth, session_id)
    replay = db.scalar(
        select(InvestigationReplay).where(
            InvestigationReplay.mission_session_id == session_id,
            InvestigationReplay.organization_id == auth.organization_id,
            InvestigationReplay.user_id == auth.user.id,
        )
    )
    if replay is None:
        raise AppError(404, "replay_not_found", "Replay is available after mission submission.")
    return ReplayResponse(
        session_id=session_id,
        timeline=list(replay.timeline),
        turning_points=list(replay.turning_points),
        missed_evidence=list(replay.missed_evidence),
        alternate_approaches=list(replay.alternate_approaches),
    )


@router.get(
    "/verify/{verification_id}",
    response_model=CompletionVerificationResponse,
)
def verify_completion(
    verification_id: str,
    db: DatabaseSession = Depends(get_db),
) -> CompletionVerificationResponse:
    record = db.scalar(
        select(CompletionRecord).where(CompletionRecord.verification_id == verification_id)
    )
    if record is None:
        raise AppError(404, "completion_not_found", "Completion record was not found.")
    identity = db.execute(
        select(User, UserProfile).where(
            User.id == record.user_id,
            UserProfile.user_id == User.id,
        )
    ).one_or_none()
    if identity is None:
        raise AppError(404, "completion_not_found", "Completion record was not found.")
    _, profile = identity
    return CompletionVerificationResponse(
        verification_id=record.verification_id,
        learner_name=profile.display_name,
        scope_type=record.scope_type,
        scope_id=record.scope_id,
        issued_at=record.issued_at.isoformat(),
        revoked=record.revoked_at is not None,
        criteria_version=record.criteria_version,
        evidence_summary=list(record.evidence_summary),
    )
