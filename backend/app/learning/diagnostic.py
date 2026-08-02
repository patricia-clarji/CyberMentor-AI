import hashlib
import json
from datetime import datetime, timedelta
from typing import Any, cast

from sqlalchemy import select
from sqlalchemy.orm import Session as DatabaseSession

from app.core.errors import AppError
from app.identity.dependencies import AuthContext
from app.learning.soc_profile import ROADMAP_ACTIVITIES, SOC_PROFILE_VERSION
from app.models.assessment import (
    Assessment,
    AssessmentVersion,
    Question,
    QuestionVersion,
)
from app.models.learning import (
    LearnerSkillState,
    Recommendation,
    Skill,
    SkillEvidence,
)
from app.schemas.diagnostic import DiagnosticQuestionResponse


def diagnostic_version(db: DatabaseSession) -> AssessmentVersion:
    version = db.scalar(
        select(AssessmentVersion)
        .join(Assessment, Assessment.id == AssessmentVersion.assessment_id)
        .where(
            Assessment.stable_key == "junior-soc-diagnostic",
            AssessmentVersion.version == SOC_PROFILE_VERSION,
            AssessmentVersion.status == "published",
        )
    )
    if version is None:
        raise AppError(
            503,
            "competition_seed_required",
            "The Junior SOC diagnostic is not seeded. Run the documented seed command.",
        )
    return version


def ordered_questions(
    db: DatabaseSession, version: AssessmentVersion
) -> list[tuple[Question, QuestionVersion]]:
    rows = db.execute(
        select(Question, QuestionVersion)
        .where(
            Question.assessment_id == version.assessment_id,
            QuestionVersion.question_id == Question.id,
            QuestionVersion.version == version.version,
            QuestionVersion.published.is_(True),
        )
        .order_by(Question.stable_key)
    ).all()
    return [(row[0], row[1]) for row in rows]


def public_question(
    question: Question,
    version: QuestionVersion,
    position: int,
    total: int,
) -> DiagnosticQuestionResponse:
    return DiagnosticQuestionResponse(
        id=version.id,
        question_type=question.question_type,
        prompt=version.prompt,
        options=list(version.options or []),
        skill_key=question.skill_key,
        position=position,
        total=total,
    )


def grade(private_answer: dict[str, Any], response: dict[str, Any]) -> bool:
    if "choice" in private_answer:
        return bool(response.get("choice") == private_answer["choice"])
    if "choices" in private_answer:
        submitted = response.get("choices")
        return isinstance(submitted, list) and sorted(set(submitted)) == sorted(
            set(private_answer["choices"])
        )
    if "order" in private_answer:
        return bool(response.get("order") == private_answer["order"])
    accepted = private_answer.get("accepted")
    answer = response.get("answer")
    if accepted and isinstance(answer, str):
        normalized = " ".join(answer.casefold().split())
        return normalized in {
            " ".join(item.casefold().split()) for item in cast(list[str], accepted)
        }
    return False


def record_skill_evidence(
    db: DatabaseSession,
    auth: AuthContext,
    question: Question,
    question_version: QuestionVersion,
    response: dict[str, Any],
    correct: bool,
    now: datetime,
) -> None:
    skill = db.scalar(select(Skill).where(Skill.stable_key == question.skill_key))
    if skill is None:
        raise AppError(500, "skill_missing", "Diagnostic skill mapping is unavailable.")
    digest = hashlib.sha256(
        json.dumps(
            {
                "organization": str(auth.organization_id),
                "user": str(auth.user.id),
                "question": str(question_version.id),
                "response": response,
                "occurredAt": now.isoformat(),
            },
            sort_keys=True,
        ).encode()
    ).hexdigest()
    db.add(
        SkillEvidence(
            organization_id=auth.organization_id,
            user_id=auth.user.id,
            skill_id=skill.id,
            source_type="diagnostic",
            source_id=str(question.id),
            source_version=question_version.version,
            score=1.0 if correct else 0.0,
            independence=1.0,
            hints_used=0,
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
    observed = 0.45 if correct else 0.1
    if state is None:
        state = LearnerSkillState(
            organization_id=auth.organization_id,
            user_id=auth.user.id,
            skill_id=skill.id,
            mastery_estimate=observed,
            confidence=0.12,
            evidence_strength=0.15,
            independence=1.0,
            reasoning_summary=(
                "Initial diagnostic evidence only; practical confirmation is required."
            ),
            last_evaluated_at=now,
            next_review_at=now + timedelta(days=14),
            engine_version="mastery-1.0.0",
            version=1,
        )
        db.add(state)
    else:
        state.mastery_estimate = (state.mastery_estimate * 0.75) + (observed * 0.25)
        state.confidence = min(0.35, state.confidence + 0.08)
        state.evidence_strength = min(0.4, state.evidence_strength + 0.1)
        state.last_evaluated_at = now
        state.next_review_at = now + timedelta(days=14)
        state.version += 1


def rebuild_roadmap(db: DatabaseSession, auth: AuthContext, weekly_minutes: int = 360) -> None:
    state_rows = db.execute(
        select(Skill.stable_key, LearnerSkillState.mastery_estimate)
        .join(LearnerSkillState, LearnerSkillState.skill_id == Skill.id)
        .where(
            LearnerSkillState.organization_id == auth.organization_id,
            LearnerSkillState.user_id == auth.user.id,
        )
    ).all()
    states: dict[str, float] = {row[0]: row[1] for row in state_rows}
    evidence_rows = db.execute(
        select(
            Skill.stable_key,
            SkillEvidence.score,
            SkillEvidence.independence,
            SkillEvidence.hints_used,
        )
        .join(SkillEvidence, SkillEvidence.skill_id == Skill.id)
        .where(
            SkillEvidence.organization_id == auth.organization_id,
            SkillEvidence.user_id == auth.user.id,
        )
        .order_by(SkillEvidence.occurred_at.desc())
    ).all()
    evidence_by_skill: dict[str, list[tuple[float, float, int]]] = {}
    for skill_key, score, independence, hints_used in evidence_rows:
        evidence_by_skill.setdefault(skill_key, []).append((score, independence, hints_used))
    existing = db.scalars(
        select(Recommendation).where(
            Recommendation.organization_id == auth.organization_id,
            Recommendation.user_id == auth.user.id,
            Recommendation.status == "active",
        )
    ).all()
    for item in existing:
        item.status = "superseded"
    strong_network = states.get("tcp-ip-reasoning", 0) >= 0.4
    weak_linux = (
        min(
            states.get("linux-processes", 0),
            states.get("linux-logs", 0),
        )
        < 0.4
    )
    ranked: list[tuple[int, dict[str, Any], str, str]] = []
    for activity in ROADMAP_ACTIVITIES:
        activity_skills = cast(list[str], activity["skills"])
        values = [states.get(skill, 0) for skill in activity_skills]
        gap = 1 - (sum(values) / max(1, len(values)))
        priority = round(gap * 100)
        reason = (
            f"Recommended because current evidence is limited across {', '.join(activity_skills)}."
        )
        intervention = "prerequisite_review"
        recent = [
            item
            for skill_key in activity_skills
            for item in evidence_by_skill.get(skill_key, [])[:3]
        ]
        repeated_failures = sum(score < 0.7 for score, _, _ in recent) >= 2
        independently_improving = bool(recent) and all(
            score >= 0.7 and independence >= 0.8 and hints == 0
            for score, independence, hints in recent[:2]
        )
        if repeated_failures:
            priority += 35
            reason = (
                "Repeated unsuccessful evidence indicates targeted remediation and "
                "earlier guidance are needed before reassessment."
            )
            intervention = "targeted_remediation"
        elif independently_improving:
            priority = max(20, priority - 20)
            reason = (
                "Recent independent evidence is improving, so guidance is reduced "
                "and the next check uses greater challenge."
            )
            intervention = "independent_reassessment"
        if activity["id"] == "linux-through-network-evidence" and strong_network and weak_linux:
            priority = 130
            reason = (
                "Uses your demonstrated network reasoning to explain developing "
                "Linux investigation skills."
            )
            intervention = "worked_micro_example"
        elif activity["id"] == "linux-investigation-refresh" and weak_linux:
            priority = 125
            reason = (
                "Linux process and log evidence needs guided practice before the "
                "flagship investigation."
            )
            intervention = "guided_learning_mode"
        elif activity["id"] == "advanced-network-correlation" and strong_network:
            priority = 80
            reason = "Retains advanced network reasoning without repeating elementary networking."
            intervention = "independent_reassessment"
        if cast(int, activity["minutes"]) <= weekly_minutes:
            ranked.append((priority, activity, reason, intervention))
    for _, activity, reason, intervention in sorted(
        ranked, key=lambda item: (-item[0], item[1]["id"])
    )[:6]:
        db.add(
            Recommendation(
                organization_id=auth.organization_id,
                user_id=auth.user.id,
                activity_type=activity["type"],
                activity_id=activity["id"],
                reason=reason,
                intervention_type=intervention,
                required=activity["id"]
                in {
                    "soc-foundations-course",
                    "flagship-phishing-endpoint-mission",
                },
                status="active",
                engine_version="roadmap-1.0.0",
            )
        )
