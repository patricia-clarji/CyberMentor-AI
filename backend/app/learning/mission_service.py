import hashlib
import json
import secrets
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any, cast

from sqlalchemy import func, select
from sqlalchemy.orm import Session as DatabaseSession

from app.core.errors import AppError
from app.identity.dependencies import AuthContext
from app.learning.flagship_mission import (
    EVALUATOR_VERSION,
    FLAGSHIP_MISSION,
    FLAGSHIP_MISSION_VERSION,
)
from app.models.learning import LearnerSkillState, Skill, SkillEvidence
from app.models.mission import (
    InvestigationReplay,
    Mission,
    MissionAction,
    MissionEvidence,
    MissionHintUse,
    MissionResult,
    MissionSession,
    MissionStage,
    MissionVersion,
)
from app.models.portfolio import CompletionRecord, Portfolio, PortfolioArtifact
from app.schemas.mission import (
    MissionActionChoice,
    MissionResourceSummary,
    MissionStageResponse,
    MissionSubmissionRequest,
)


def published_mission(db: DatabaseSession) -> tuple[Mission, MissionVersion]:
    pair = db.execute(
        select(Mission, MissionVersion).where(
            Mission.stable_key == FLAGSHIP_MISSION["stable_key"],
            MissionVersion.mission_id == Mission.id,
            MissionVersion.version == FLAGSHIP_MISSION_VERSION,
            MissionVersion.status == "published",
        )
    ).one_or_none()
    if pair is None:
        raise AppError(
            503,
            "competition_seed_required",
            "The flagship mission is not seeded. Run the documented seed command.",
        )
    return pair[0], pair[1]


def ordered_stages(db: DatabaseSession, version_id: uuid.UUID) -> list[MissionStage]:
    return list(
        db.scalars(
            select(MissionStage)
            .where(MissionStage.mission_version_id == version_id)
            .order_by(MissionStage.position)
        ).all()
    )


def stage_definition(stage: MissionStage) -> dict[str, Any]:
    definition = next(
        (item for item in FLAGSHIP_MISSION["stages"] if item["key"] == stage.stable_key),
        None,
    )
    if definition is None:
        raise AppError(500, "mission_definition_invalid", "Mission stage definition is missing.")
    return cast(dict[str, Any], definition)


def evaluate_mission_action(
    definition: dict[str, Any],
    action_type: str,
    resource_id: str | None,
    decision_id: str | None,
) -> tuple[str, str, str | None, bool]:
    """Pure mission-engine evaluation shared by learner and protected draft playtests."""
    if action_type == "open_evidence":
        resource = next(
            (item for item in definition.get("resources", []) if item.get("id") == resource_id),
            None,
        )
        if resource is None:
            raise AppError(422, "invalid_mission_resource", "Select an available resource.")
        return (
            "observed",
            "Evidence opened and added to the investigation workspace.",
            str(resource.get("content") or ""),
            False,
        )
    valid_ids = {str(item.get("id")) for item in definition.get("actions", [])}
    if decision_id not in valid_ids:
        raise AppError(422, "invalid_mission_decision", "Select an available decision.")
    accepted = {str(definition.get("required_action"))} | {
        str(item) for item in definition.get("alternative_valid_actions", [])
    }
    correct = decision_id in accepted
    return (
        "correct" if correct else "mistake",
        (
            "Decision recorded. The evidence supports moving forward."
            if correct
            else (
                "That decision is unsupported or unsafe. Recheck the supplied evidence "
                "and choose a proportionate defensive action."
            )
        ),
        None,
        correct,
    )


def owned_session(
    db: DatabaseSession,
    auth: AuthContext,
    session_id: uuid.UUID,
    *,
    allowed_statuses: set[str] | None = None,
) -> MissionSession:
    mission_session = db.scalar(
        select(MissionSession).where(
            MissionSession.id == session_id,
            MissionSession.organization_id == auth.organization_id,
            MissionSession.user_id == auth.user.id,
        )
    )
    if mission_session is None:
        raise AppError(404, "mission_session_not_found", "Mission session was not found.")
    if allowed_statuses is not None and mission_session.status not in allowed_statuses:
        raise AppError(409, "mission_session_closed", "This mission session is not active.")
    return mission_session


def public_stage(
    db: DatabaseSession,
    auth: AuthContext,
    mission_session: MissionSession,
    stage: MissionStage,
) -> MissionStageResponse:
    definition = stage_definition(stage)
    opened = set(
        db.scalars(
            select(MissionEvidence.evidence_key).where(
                MissionEvidence.mission_session_id == mission_session.id,
                MissionEvidence.organization_id == auth.organization_id,
                MissionEvidence.user_id == auth.user.id,
            )
        ).all()
    )
    total = len(FLAGSHIP_MISSION["stages"])
    return MissionStageResponse(
        id=stage.id,
        key=stage.stable_key,
        position=stage.position,
        total=total,
        title=stage.title,
        objective=stage.objective,
        resources=[
            MissionResourceSummary(
                id=resource["id"],
                label=resource["label"],
                classification=resource["classification"],
                opened=resource["id"] in opened,
            )
            for resource in definition["resources"]
        ],
        actions=[
            MissionActionChoice(id=action["id"], label=action["label"])
            for action in definition["actions"]
        ],
    )


def next_sequence(db: DatabaseSession, session_id: uuid.UUID) -> int:
    return (
        db.scalar(
            select(func.max(MissionAction.sequence)).where(
                MissionAction.mission_session_id == session_id
            )
        )
        or 0
    ) + 1


def record_practical_evidence(
    db: DatabaseSession,
    auth: AuthContext,
    mission_session: MissionSession,
    correct_stage_keys: set[str],
    hints_used: int,
    now: datetime,
) -> None:
    skill_by_key = {item.stable_key: item for item in db.scalars(select(Skill)).all()}
    for definition in FLAGSHIP_MISSION["stages"]:
        skill = skill_by_key.get(definition["skill"])
        if skill is None:
            raise AppError(500, "skill_missing", "Mission skill mapping is unavailable.")
        correct = definition["key"] in correct_stage_keys
        independence = max(0.2, 1 - (hints_used * 0.08))
        digest = hashlib.sha256(
            json.dumps(
                {
                    "organization": str(auth.organization_id),
                    "user": str(auth.user.id),
                    "session": str(mission_session.id),
                    "stage": definition["key"],
                    "correct": correct,
                },
                sort_keys=True,
            ).encode()
        ).hexdigest()
        db.add(
            SkillEvidence(
                organization_id=auth.organization_id,
                user_id=auth.user.id,
                skill_id=skill.id,
                source_type="workplace_mission",
                source_id=f"{mission_session.id}:{definition['key']}",
                source_version=FLAGSHIP_MISSION_VERSION,
                score=1.0 if correct else 0.0,
                independence=independence,
                hints_used=hints_used,
                attempts=1,
                occurred_at=now,
                provenance_hash=digest,
            )
        )
        state = db.scalar(
            select(LearnerSkillState).where(
                LearnerSkillState.organization_id == auth.organization_id,
                LearnerSkillState.user_id == auth.user.id,
                LearnerSkillState.skill_id == skill.id,
            )
        )
        observed = 0.82 if correct else 0.18
        if state is None:
            state = LearnerSkillState(
                organization_id=auth.organization_id,
                user_id=auth.user.id,
                skill_id=skill.id,
                mastery_estimate=observed,
                confidence=0.42,
                evidence_strength=0.55,
                independence=independence,
                reasoning_summary="Observed in a verified synthetic workplace mission.",
                last_evaluated_at=now,
                next_review_at=now + timedelta(days=30),
                engine_version="mastery-1.0.0",
                version=1,
            )
            db.add(state)
        else:
            state.mastery_estimate = (state.mastery_estimate * 0.55) + (observed * 0.45)
            state.confidence = min(0.78, state.confidence + 0.28)
            state.evidence_strength = min(0.85, state.evidence_strength + 0.35)
            state.independence = (state.independence + independence) / 2
            state.reasoning_summary = "Diagnostic estimate updated by practical mission evidence."
            state.last_evaluated_at = now
            state.next_review_at = now + timedelta(days=30)
            state.version += 1


def build_submission_result(
    db: DatabaseSession,
    auth: AuthContext,
    mission_session: MissionSession,
    payload: MissionSubmissionRequest,
) -> tuple[MissionResult, InvestigationReplay, PortfolioArtifact | None, CompletionRecord | None]:
    now = datetime.now(UTC)
    actions = list(
        db.scalars(
            select(MissionAction)
            .where(
                MissionAction.mission_session_id == mission_session.id,
                MissionAction.organization_id == auth.organization_id,
                MissionAction.user_id == auth.user.id,
            )
            .order_by(MissionAction.sequence)
        ).all()
    )
    evidences = list(
        db.scalars(
            select(MissionEvidence).where(
                MissionEvidence.mission_session_id == mission_session.id,
                MissionEvidence.organization_id == auth.organization_id,
                MissionEvidence.user_id == auth.user.id,
            )
        ).all()
    )
    hints = list(
        db.scalars(
            select(MissionHintUse).where(
                MissionHintUse.mission_session_id == mission_session.id,
                MissionHintUse.organization_id == auth.organization_id,
                MissionHintUse.user_id == auth.user.id,
            )
        ).all()
    )
    correct_stage_keys: set[str] = set()
    for action in actions:
        if action.outcome != "correct":
            continue
        action_stage = db.get(MissionStage, action.stage_id)
        if action_stage is not None:
            correct_stage_keys.add(str(stage_definition(action_stage)["key"]))
    stage_count = len(FLAGSHIP_MISSION["stages"])
    practical = len(correct_stage_keys) / stage_count
    conceptual = min(1.0, (len(evidences) / stage_count) * 0.55 + practical * 0.45)
    decision = (
        1.0
        if payload.classification == "suspected_endpoint_compromise"
        and payload.recommendation == "isolate_fin_14_with_approval"
        else 0.35
    )
    independence = max(0.2, 1 - (len(hints) * 0.08))
    reporting_checks = [
        len(payload.rationale.strip()) >= 160,
        len(payload.uncertainty.strip()) >= 40,
        len(payload.next_steps) >= 2,
        len(payload.reflection.strip()) >= 60,
    ]
    reporting = sum(reporting_checks) / len(reporting_checks)
    passed = practical == 1.0 and conceptual >= 0.85 and decision == 1.0 and reporting >= 0.75
    result = MissionResult(
        organization_id=auth.organization_id,
        user_id=auth.user.id,
        mission_session_id=mission_session.id,
        passed=passed,
        conceptual_score=conceptual,
        practical_score=practical,
        decision_score=decision,
        independence_score=independence,
        reporting_score=reporting,
        evaluator_version=EVALUATOR_VERSION,
        evaluated_at=now,
    )
    db.add(result)
    all_evidence = {
        resource["id"] for stage in FLAGSHIP_MISSION["stages"] for resource in stage["resources"]
    }
    opened_evidence = {item.evidence_key for item in evidences}
    timeline = [
        {
            "sequence": action.sequence,
            "stage": str(action.stage_id),
            "actionType": action.action_type,
            "resourceId": action.resource_id,
            "outcome": action.outcome,
            "occurredAt": action.occurred_at.isoformat(),
        }
        for action in actions
    ]
    replay = InvestigationReplay(
        organization_id=auth.organization_id,
        user_id=auth.user.id,
        mission_session_id=mission_session.id,
        timeline=timeline,
        turning_points=[
            {
                "sequence": action.sequence,
                "observation": (
                    "This decision advanced the evidence-based investigation."
                    if action.outcome == "correct"
                    else "This decision was recorded as an unsupported or unsafe turn."
                ),
            }
            for action in actions
            if action.action_type == "decision"
        ],
        missed_evidence=sorted(all_evidence - opened_evidence),
        alternate_approaches=[
            "Preserve the raw evidence before drawing a conclusion.",
            "Correlate independent telemetry and state remaining uncertainty.",
            "Request scoped, authorized containment rather than retaliatory action.",
        ],
        generated_at=now,
        generator_version="deterministic-replay-1.0.0",
    )
    db.add(replay)
    record_practical_evidence(db, auth, mission_session, correct_stage_keys, len(hints), now)
    artifact = None
    completion = None
    if passed:
        portfolio = db.scalar(
            select(Portfolio).where(
                Portfolio.organization_id == auth.organization_id,
                Portfolio.user_id == auth.user.id,
            )
        )
        if portfolio is None:
            portfolio = Portfolio(
                organization_id=auth.organization_id,
                user_id=auth.user.id,
                visibility="private",
            )
            db.add(portfolio)
            db.flush()
        artifact = PortfolioArtifact(
            organization_id=auth.organization_id,
            user_id=auth.user.id,
            portfolio_id=portfolio.id,
            artifact_type="verified_workplace_mission",
            source_id=str(mission_session.id),
            title=FLAGSHIP_MISSION["title"],
            verification_state="verified",
            visibility="private",
        )
        db.add(artifact)
        completion = CompletionRecord(
            organization_id=auth.organization_id,
            user_id=auth.user.id,
            verification_id=secrets.token_urlsafe(18),
            criteria_version=EVALUATOR_VERSION,
            scope_type="workplace_mission",
            scope_id=FLAGSHIP_MISSION["stable_key"],
            skill_summary=[
                {"skill": definition["skill"], "result": "demonstrated"}
                for definition in FLAGSHIP_MISSION["stages"]
            ],
            evidence_summary=[
                {
                    "type": "synthetic_workplace_mission",
                    "missionVersion": FLAGSHIP_MISSION_VERSION,
                    "passed": True,
                }
            ],
            issued_at=now,
        )
        db.add(completion)
    mission_session.status = "passed" if passed else "not_passed"
    mission_session.completed_at = now
    mission_session.version += 1
    return result, replay, artifact, completion
