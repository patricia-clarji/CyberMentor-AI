import hashlib
import json
from datetime import UTC, datetime, timedelta
from typing import Any, cast

from sqlalchemy import func, select
from sqlalchemy.orm import Session as DatabaseSession

from app.core.errors import AppError
from app.identity.dependencies import AuthContext
from app.learning.diagnostic import rebuild_roadmap
from app.learning.soc_pathway import MODULES, PATHWAY_ID, PATHWAY_VERSION
from app.models.learning import (
    Enrollment,
    LearnerSkillState,
    LearningActivityAttempt,
    LessonProgress,
    Skill,
    SkillEvidence,
)

EVALUATOR_VERSION = "soc-learning-evaluator-1.0.0"


def grade_response(private_answer: dict[str, Any], response: dict[str, Any]) -> float:
    if "choice" in private_answer:
        return 1.0 if response.get("choice") == private_answer["choice"] else 0.0
    if "choices" in private_answer:
        expected = set(private_answer["choices"])
        submitted_raw = response.get("choices")
        if not isinstance(submitted_raw, list):
            return 0.0
        submitted_choices = set(submitted_raw)
        if not expected and not submitted_choices:
            return 1.0
        correct = len(expected & submitted_choices)
        incorrect = len(submitted_choices - expected)
        return max(0.0, min(1.0, (correct - incorrect) / max(1, len(expected))))
    if "order" in private_answer:
        expected_order = cast(list[Any], private_answer["order"])
        submitted_order = response.get("order")
        if not isinstance(submitted_order, list) or len(submitted_order) != len(expected_order):
            return 0.0
        correct_positions = sum(
            value == expected_order[index] for index, value in enumerate(submitted_order)
        )
        return float(correct_positions) / max(1, len(expected_order))
    if "keywords" in private_answer:
        answer = response.get("answer")
        if not isinstance(answer, str) or len(answer.strip()) < private_answer["minimum_length"]:
            return 0.0
        normalized = " ".join(answer.casefold().split())
        keywords = cast(list[str], private_answer["keywords"])
        minimum_matches = int(private_answer["minimum_matches"])
        matches = sum(keyword.casefold() in normalized for keyword in keywords)
        return min(1.0, float(matches) / max(1, minimum_matches))
    return 0.0


def record_attempt(
    db: DatabaseSession,
    auth: AuthContext,
    *,
    activity_id: str,
    activity_type: str,
    module_id: str,
    response: dict[str, Any],
    score: float,
    feedback: str,
    idempotency_key: str,
    hints_used: int,
    skill_keys: list[str],
) -> LearningActivityAttempt:
    existing = db.scalar(
        select(LearningActivityAttempt).where(
            LearningActivityAttempt.organization_id == auth.organization_id,
            LearningActivityAttempt.user_id == auth.user.id,
            LearningActivityAttempt.idempotency_key == idempotency_key,
        )
    )
    if existing is not None:
        if existing.activity_id != activity_id or existing.response != response:
            raise AppError(
                409,
                "idempotency_conflict",
                "This submission key was already used for a different response.",
            )
        return existing
    now = datetime.now(UTC)
    attempt = LearningActivityAttempt(
        organization_id=auth.organization_id,
        user_id=auth.user.id,
        activity_id=activity_id,
        activity_version=PATHWAY_VERSION,
        activity_type=activity_type,
        module_id=module_id,
        response=response,
        score=score,
        passed=score >= 0.7,
        hints_used=hints_used,
        evaluator=EVALUATOR_VERSION,
        feedback=feedback,
        idempotency_key=idempotency_key,
        submitted_at=now,
    )
    db.add(attempt)
    db.flush()
    for skill_key in sorted(set(skill_keys)):
        record_evidence(
            db,
            auth,
            attempt=attempt,
            skill_key=skill_key,
            score=score,
            now=now,
        )
    rebuild_roadmap(db, auth)
    statuses = module_statuses(db, auth)
    if statuses and all(item["completed"] for item in statuses):
        enrollment = db.scalar(
            select(Enrollment).where(
                Enrollment.organization_id == auth.organization_id,
                Enrollment.user_id == auth.user.id,
                Enrollment.course_publication_id == PATHWAY_ID,
            )
        )
        if enrollment is not None:
            enrollment.status = "completed"
            enrollment.completed_at = now
    db.commit()
    db.refresh(attempt)
    return attempt


def record_evidence(
    db: DatabaseSession,
    auth: AuthContext,
    *,
    attempt: LearningActivityAttempt,
    skill_key: str,
    score: float,
    now: datetime,
) -> None:
    skill = db.scalar(select(Skill).where(Skill.stable_key == skill_key))
    if skill is None:
        raise AppError(500, "skill_mapping_missing", "A pathway skill mapping is unavailable.")
    evidence_count = (
        db.scalar(
            select(func.count(SkillEvidence.id)).where(
                SkillEvidence.organization_id == auth.organization_id,
                SkillEvidence.user_id == auth.user.id,
                SkillEvidence.skill_id == skill.id,
            )
        )
        or 0
    )
    independence = max(0.2, 1.0 - (attempt.hints_used * 0.2))
    digest = hashlib.sha256(
        json.dumps(
            {
                "organization": str(auth.organization_id),
                "user": str(auth.user.id),
                "attempt": str(attempt.id),
                "skill": skill_key,
            },
            sort_keys=True,
        ).encode()
    ).hexdigest()
    db.add(
        SkillEvidence(
            organization_id=auth.organization_id,
            user_id=auth.user.id,
            skill_id=skill.id,
            source_type=attempt.activity_type,
            source_id=attempt.activity_id,
            source_version=attempt.activity_version,
            score=score,
            independence=independence,
            hints_used=attempt.hints_used,
            attempts=int(evidence_count) + 1,
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
    observed = score * independence
    if state is None:
        state = LearnerSkillState(
            organization_id=auth.organization_id,
            user_id=auth.user.id,
            skill_id=skill.id,
            mastery_estimate=observed * 0.35,
            confidence=0.18,
            evidence_strength=0.2,
            independence=independence,
            reasoning_summary=(
                "One learning activity is recorded; more varied evidence is required "
                "before mastery can be inferred."
            ),
            last_evaluated_at=now,
            next_review_at=now + timedelta(days=14 if score < 0.7 else 30),
            engine_version="mastery-1.1.0",
            version=1,
        )
        db.add(state)
        return
    weight = min(0.35, 0.16 + (int(evidence_count) * 0.03))
    state.mastery_estimate = (state.mastery_estimate * (1 - weight)) + (observed * weight)
    state.confidence = min(0.85, state.confidence + 0.1)
    state.evidence_strength = min(0.9, state.evidence_strength + 0.12)
    state.independence = (state.independence * 0.7) + (independence * 0.3)
    state.reasoning_summary = (
        f"Updated from {int(evidence_count) + 1} recorded evidence items; "
        f"the latest {attempt.activity_type.replace('_', ' ')} scored {score:.0%} "
        f"with {attempt.hints_used} hint(s)."
    )
    state.last_evaluated_at = now
    state.next_review_at = now + timedelta(days=14 if score < 0.7 else 30)
    state.engine_version = "mastery-1.1.0"
    state.version += 1


def module_statuses(db: DatabaseSession, auth: AuthContext) -> list[dict[str, Any]]:
    completed_lessons = set(
        db.scalars(
            select(LessonProgress.lesson_publication_id).where(
                LessonProgress.organization_id == auth.organization_id,
                LessonProgress.user_id == auth.user.id,
                LessonProgress.status == "completed",
            )
        ).all()
    )
    attempts = db.scalars(
        select(LearningActivityAttempt).where(
            LearningActivityAttempt.organization_id == auth.organization_id,
            LearningActivityAttempt.user_id == auth.user.id,
        )
    ).all()
    passed_ids = {attempt.activity_id for attempt in attempts if attempt.passed}
    statuses: list[dict[str, Any]] = []
    previous_complete = True
    for module in MODULES:
        lesson_done = all(item in completed_lessons for item in module["required_lessons"])
        practice_done = all(item in passed_ids for item in module["required_practices"])
        assessment_done = module["required_assessment"] in passed_ids
        complete = lesson_done and practice_done and assessment_done
        statuses.append(
            {
                "module_id": module["id"],
                "unlocked": previous_complete,
                "completed": complete,
                "required_lessons_completed": lesson_done,
                "required_practices_completed": practice_done,
                "assessment_passed": assessment_done,
            }
        )
        previous_complete = previous_complete and complete
    return statuses
