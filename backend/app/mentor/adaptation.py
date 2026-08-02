import re
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from typing import Any, Literal

from sqlalchemy import func, select
from sqlalchemy.orm import Session as DatabaseSession

from app.identity.dependencies import AuthContext
from app.learning.lab_catalog import get_lab
from app.models.lab import LabAction, LabSession
from app.models.learning import (
    LearnerMisconception,
    LearnerNote,
    LearnerPreference,
    LearnerSkillState,
    LearningActivityAttempt,
    Misconception,
    Recommendation,
    Skill,
)
from app.models.mentor import MentorLearnerMemory, MentorMessage, MentorThread
from app.models.mission import MissionAction, MissionHintUse, MissionSession, MissionStage
from app.models.portfolio import (
    CompletionRecord,
    PortfolioArtifact,
    Project,
    ProjectReview,
    ProjectSubmission,
)

MentorMode = Literal[
    "teaching",
    "explanation",
    "guided_practice",
    "socratic",
    "hint",
    "reflection",
    "investigation",
    "review",
    "assessment_support",
    "safety_redirect",
    "human_review_recommendation",
]

MENTOR_MODES: tuple[MentorMode, ...] = (
    "teaching",
    "explanation",
    "guided_practice",
    "socratic",
    "hint",
    "reflection",
    "investigation",
    "review",
    "assessment_support",
    "safety_redirect",
    "human_review_recommendation",
)

INTERVENTIONS = {
    "ask_question",
    "give_hint",
    "show_analogy",
    "review_prerequisite",
    "recommend_lesson",
    "recommend_lab",
    "recommend_replay",
    "recommend_reassessment",
    "recommend_project",
    "recommend_mission",
    "recommend_break",
    "recommend_instructor_review",
}

MISCONCEPTION_RULES: tuple[tuple[str, str, str, re.Pattern[str]], ...] = (
    (
        "memorization-without-understanding",
        "security-foundations",
        "The learner relies on memorized wording without explaining the evidence relationship.",
        re.compile(r"\b(just memor(?:ize|ise)|memorized answer|same wording every time)\b", re.I),
    ),
    (
        "linux-syntax-confusion",
        "linux-navigation",
        "The learner confuses Linux command arguments, paths, or command purpose.",
        re.compile(
            r"\b(cd a file|grep changes|cat searches|chmod owner|chown permissions)\b", re.I
        ),
    ),
    (
        "network-model-confusion",
        "tcp-ip-reasoning",
        "The learner conflates network layers, addresses, ports, or protocol roles.",
        re.compile(
            r"\b(ip address is a port|dns encrypts|tcp is an ip address|http resolves dns)\b",
            re.I,
        ),
    ),
    (
        "siem-query-misconception",
        "siem-query-reasoning",
        "The learner treats a SIEM query match as proof rather than scoped evidence.",
        re.compile(r"\b(query match (?:proves|confirms)|no results means safe)\b", re.I),
    ),
    (
        "ioc-as-verdict",
        "ioc-analysis",
        "The learner treats an indicator match as a verdict without provenance or context.",
        re.compile(r"\b(ioc|indicator).{0,35}\b(proves|confirms|always malicious)\b", re.I),
    ),
    (
        "incorrect-investigation-order",
        "alert-triage",
        "The learner proposes containment or conclusions before preserving "
        "and correlating evidence.",
        re.compile(
            r"\b(block|delete|isolate|reset).{0,50}"
            r"\b(first|before (?:checking|collecting|preserving))\b",
            re.I,
        ),
    ),
    (
        "confirmation-bias",
        "alert-triage",
        "The learner dismisses alternative explanations after selecting an initial hypothesis.",
        re.compile(
            r"\b(obviously|definitely|must be).{0,45}\b(attacker|compromised|malware)\b", re.I
        ),
    ),
    (
        "missing-evidence",
        "evidence-preservation",
        "The learner reaches a conclusion without identifying corroborating evidence.",
        re.compile(
            r"\b(don't need|no need|without).{0,35}"
            r"\b(more evidence|logs|correlation|verification)\b",
            re.I,
        ),
    ),
    (
        "premature-conclusion",
        "incident-severity",
        "The learner declares an incident or breach beyond the supplied evidence.",
        re.compile(
            r"\b(alert|failed login|single event).{0,40}\b(proves|confirmed breach)\b", re.I
        ),
    ),
)


@dataclass(frozen=True)
class AdaptationDecision:
    mode: MentorMode
    intervention: str
    rationale: str
    related_skills: list[str]
    recommended_action: dict[str, Any] | None
    difficulty_risk: str


def _owner(model: type[Any], auth: AuthContext) -> tuple[Any, Any]:
    return (
        model.organization_id == auth.organization_id,
        model.user_id == auth.user.id,
    )


def _study_streak(days: list[date], today: date) -> int:
    unique = set(days)
    cursor = today
    if cursor not in unique and cursor - timedelta(days=1) in unique:
        cursor -= timedelta(days=1)
    streak = 0
    while cursor in unique:
        streak += 1
        cursor -= timedelta(days=1)
    return streak


def _skill_snapshot(db: DatabaseSession, auth: AuthContext) -> list[dict[str, Any]]:
    rows = db.execute(
        select(
            Skill.stable_key,
            Skill.name,
            LearnerSkillState.mastery_estimate,
            LearnerSkillState.confidence,
            LearnerSkillState.independence,
            LearnerSkillState.next_review_at,
        )
        .join(LearnerSkillState, LearnerSkillState.skill_id == Skill.id)
        .where(*_owner(LearnerSkillState, auth))
        .order_by(LearnerSkillState.mastery_estimate)
    ).all()
    return [
        {
            "key": key,
            "name": name,
            "mastery": mastery,
            "confidence": confidence,
            "independence": independence,
            "nextReviewAt": next_review.isoformat() if next_review else None,
        }
        for key, name, mastery, confidence, independence, next_review in rows
    ]


def _current_context(
    db: DatabaseSession,
    auth: AuthContext,
    thread: MentorThread,
) -> dict[str, Any]:
    if thread.context_type == "lab" and thread.context_id:
        lab_session = db.scalar(
            select(LabSession)
            .where(
                *_owner(LabSession, auth),
                LabSession.lab_id == thread.context_id,
            )
            .order_by(LabSession.created_at.desc())
        )
        lab = get_lab(thread.context_id)
        if lab_session is None:
            return {
                "type": "lab",
                "id": lab["id"],
                "title": lab["title"],
                "scenario": lab["scenario"],
                "objectives": lab["objectives"],
                "status": "not_started",
            }
        actions = db.scalars(
            select(LabAction)
            .where(
                LabAction.organization_id == auth.organization_id,
                LabAction.user_id == auth.user.id,
                LabAction.session_id == lab_session.id,
            )
            .order_by(LabAction.sequence.desc())
            .limit(8)
        ).all()
        return {
            "type": "lab",
            "id": lab["id"],
            "title": lab["title"],
            "scenario": lab["scenario"],
            "objectives": lab["objectives"],
            "status": lab_session.status,
            "stage": lab_session.current_stage,
            "objectiveState": lab_session.objective_state,
            "hintsUsed": lab_session.hints_used,
            "notes": lab_session.notes[-1200:],
            "recentActions": [
                {
                    "type": action.action_type,
                    "input": action.input_text,
                    "successful": action.successful,
                    "mistake": action.mistake,
                }
                for action in reversed(actions)
            ],
        }
    if thread.context_type == "mission":
        mission_session = db.scalar(
            select(MissionSession)
            .where(*_owner(MissionSession, auth))
            .order_by(MissionSession.created_at.desc())
        )
        if mission_session is None:
            return {"type": "mission", "id": thread.context_id, "status": "not_started"}
        stage = db.get(MissionStage, mission_session.current_stage_id)
        mistakes = db.scalar(
            select(func.count(MissionAction.id)).where(
                MissionAction.organization_id == auth.organization_id,
                MissionAction.user_id == auth.user.id,
                MissionAction.mission_session_id == mission_session.id,
                MissionAction.outcome == "mistake",
            )
        )
        hints = db.scalar(
            select(func.count(MissionHintUse.id)).where(
                MissionHintUse.organization_id == auth.organization_id,
                MissionHintUse.user_id == auth.user.id,
                MissionHintUse.mission_session_id == mission_session.id,
            )
        )
        return {
            "type": "mission",
            "id": thread.context_id,
            "status": mission_session.status,
            "stage": stage.title if stage else None,
            "stageObjective": stage.objective if stage else None,
            "mistakes": int(mistakes or 0),
            "hintsUsed": int(hints or 0),
        }
    if thread.context_type == "lesson" and thread.context_id:
        notes = db.scalars(
            select(LearnerNote)
            .where(
                *_owner(LearnerNote, auth),
                LearnerNote.lesson_publication_id == thread.context_id,
            )
            .order_by(LearnerNote.updated_at.desc())
            .limit(3)
        ).all()
        return {
            "type": "lesson",
            "id": thread.context_id,
            "learnerNotes": [note.body[-800:] for note in notes],
        }
    if thread.context_type == "project":
        submission = db.scalar(
            select(ProjectSubmission)
            .where(*_owner(ProjectSubmission, auth))
            .order_by(ProjectSubmission.submitted_at.desc())
        )
        if submission is None:
            return {
                "type": "project",
                "id": thread.context_id,
                "status": "not_submitted",
            }
        project = db.get(Project, submission.project_id)
        review = db.scalar(
            select(ProjectReview)
            .where(
                ProjectReview.organization_id == auth.organization_id,
                ProjectReview.submission_id == submission.id,
            )
            .order_by(ProjectReview.reviewed_at.desc())
        )
        criterion_results = list(review.criterion_results) if review else []
        return {
            "type": "project",
            "id": thread.context_id,
            "title": project.title if project else None,
            "status": submission.status,
            "strengths": [
                item.get("key") for item in criterion_results if item.get("passed") is True
            ],
            "improvementAreas": [
                item.get("key") for item in criterion_results if item.get("passed") is False
            ],
            "humanReviewed": review is not None,
        }
    return {"type": thread.context_type, "id": thread.context_id}


def build_learner_context(
    db: DatabaseSession,
    auth: AuthContext,
    thread: MentorThread,
) -> dict[str, Any]:
    skills = _skill_snapshot(db, auth)
    attempts = db.scalars(
        select(LearningActivityAttempt)
        .where(*_owner(LearningActivityAttempt, auth))
        .order_by(LearningActivityAttempt.submitted_at.desc())
        .limit(10)
    ).all()
    misconceptions = db.execute(
        select(
            Misconception.stable_key,
            Misconception.description,
            LearnerMisconception.confidence,
            LearnerMisconception.evidence_count,
            LearnerMisconception.status,
        )
        .join(
            LearnerMisconception,
            LearnerMisconception.misconception_id == Misconception.id,
        )
        .where(
            *_owner(LearnerMisconception, auth),
            LearnerMisconception.status != "resolved",
        )
        .order_by(LearnerMisconception.confidence.desc())
    ).all()
    preferences = db.scalars(
        select(LearnerPreference).where(*_owner(LearnerPreference, auth))
    ).all()
    recommendations = db.scalars(
        select(Recommendation)
        .where(*_owner(Recommendation, auth), Recommendation.status == "active")
        .order_by(Recommendation.created_at.desc())
        .limit(6)
    ).all()
    completed_labs = db.scalars(
        select(LabSession.lab_id).where(
            *_owner(LabSession, auth),
            LabSession.status == "completed",
        )
    ).all()
    completed_missions = db.scalar(
        select(func.count(MissionSession.id)).where(
            *_owner(MissionSession, auth),
            MissionSession.status.in_(("passed", "completed")),
        )
    )
    artifact_count = db.scalar(
        select(func.count(PortfolioArtifact.id)).where(*_owner(PortfolioArtifact, auth))
    )
    completion_count = db.scalar(
        select(func.count(CompletionRecord.id)).where(*_owner(CompletionRecord, auth))
    )
    message_days = [
        item.date()
        for item in db.scalars(
            select(MentorMessage.created_at).where(*_owner(MentorMessage, auth))
        ).all()
    ]
    conversation_turns = db.scalar(
        select(func.count(MentorMessage.id)).where(*_owner(MentorMessage, auth))
    )
    attempt_days = [attempt.submitted_at.date() for attempt in attempts]
    failures = [
        {
            "activityId": attempt.activity_id,
            "activityType": attempt.activity_type,
            "hintsUsed": attempt.hints_used,
        }
        for attempt in attempts
        if not attempt.passed
    ][:5]
    improvements = [
        {
            "activityId": attempt.activity_id,
            "activityType": attempt.activity_type,
            "independent": attempt.hints_used == 0,
        }
        for attempt in attempts
        if attempt.passed
    ][:5]
    now = datetime.now(UTC)
    memory = db.scalar(select(MentorLearnerMemory).where(*_owner(MentorLearnerMemory, auth)))
    mastery_values = [item["mastery"] for item in skills]
    independence_values = [item["independence"] for item in skills]
    review_schedule = [
        {"skill": item["key"], "nextReviewAt": item["nextReviewAt"]}
        for item in skills
        if item["nextReviewAt"]
    ]
    if memory is None:
        memory = MentorLearnerMemory(
            organization_id=auth.organization_id,
            user_id=auth.user.id,
            preferred_explanations=[],
            learning_pace="standard",
            confidence_estimate=sum(mastery_values) / max(1, len(mastery_values)),
            independence_estimate=sum(independence_values) / max(1, len(independence_values)),
            recent_failures=failures,
            recent_improvements=improvements,
            study_streak_days=_study_streak(message_days + attempt_days, now.date()),
            review_schedule=review_schedule,
            last_interaction_at=now,
            version=1,
        )
        db.add(memory)
    else:
        memory.confidence_estimate = sum(mastery_values) / max(1, len(mastery_values))
        memory.independence_estimate = sum(independence_values) / max(1, len(independence_values))
        memory.recent_failures = failures
        memory.recent_improvements = improvements
        memory.study_streak_days = _study_streak(message_days + attempt_days, now.date())
        memory.review_schedule = review_schedule
        memory.last_interaction_at = now
        memory.version += 1
    preference_map = {item.preference_key: item.preference_value for item in preferences}
    preferred = list(memory.preferred_explanations)
    if (
        preference_map.get("explanation_style")
        and preference_map["explanation_style"] not in preferred
    ):
        preferred.append(preference_map["explanation_style"])
        memory.preferred_explanations = preferred[-5:]
    return {
        "skills": skills,
        "weakSkills": [item["key"] for item in skills if item["mastery"] < 0.45][:5],
        "strongSkills": [item["key"] for item in reversed(skills) if item["mastery"] >= 0.7][:5],
        "misconceptions": [
            {
                "key": key,
                "description": description,
                "confidence": confidence,
                "evidenceCount": evidence_count,
                "status": status,
            }
            for key, description, confidence, evidence_count, status in misconceptions
        ],
        "completedLabs": sorted(set(completed_labs)),
        "completedMissions": int(completed_missions or 0),
        "portfolioArtifacts": int(artifact_count or 0),
        "completionRecords": int(completion_count or 0),
        "hintHistory": [
            {"activityId": item.activity_id, "hintsUsed": item.hints_used}
            for item in attempts
            if item.hints_used
        ][:6],
        "preferredExplanations": preferred,
        "learningPace": memory.learning_pace,
        "confidenceEstimate": memory.confidence_estimate,
        "independence": memory.independence_estimate,
        "recentFailures": failures,
        "recentImprovements": improvements,
        "studyStreak": memory.study_streak_days,
        "conversationTurns": int(conversation_turns or 0),
        "reviewSchedule": review_schedule,
        "recommendations": [
            {
                "activityType": item.activity_type,
                "activityId": item.activity_id,
                "reason": item.reason,
            }
            for item in recommendations
        ],
        "currentContext": _current_context(db, auth, thread),
    }


def detect_misconceptions(
    db: DatabaseSession,
    auth: AuthContext,
    question: str,
) -> list[str]:
    detected: list[str] = []
    now = datetime.now(UTC)
    for stable_key, skill_key, description, pattern in MISCONCEPTION_RULES:
        if not pattern.search(question):
            continue
        skill = db.scalar(select(Skill).where(Skill.stable_key == skill_key))
        if skill is None:
            continue
        definition = db.scalar(select(Misconception).where(Misconception.stable_key == stable_key))
        if definition is None:
            definition = Misconception(
                stable_key=stable_key,
                skill_id=skill.id,
                description=description,
            )
            db.add(definition)
            db.flush()
        record = db.scalar(
            select(LearnerMisconception).where(
                *_owner(LearnerMisconception, auth),
                LearnerMisconception.misconception_id == definition.id,
            )
        )
        evidence = {
            "source": "mentor_conversation",
            "summary": " ".join(question.strip().split())[:240],
            "observedAt": now.isoformat(),
        }
        if record is None:
            record = LearnerMisconception(
                organization_id=auth.organization_id,
                user_id=auth.user.id,
                misconception_id=definition.id,
                evidence_count=1,
                confidence=0.4,
                status="suspected",
                first_observed_at=now,
                last_observed_at=now,
                supporting_evidence=[evidence],
            )
            db.add(record)
        else:
            record.evidence_count += 1
            record.confidence = min(0.95, record.confidence + 0.15)
            record.status = "observed" if record.confidence >= 0.65 else "suspected"
            record.last_observed_at = now
            record.supporting_evidence = [*record.supporting_evidence[-4:], evidence]
            record.resolved_at = None
        detected.append(stable_key)
    return detected


def _related_skills(question: str, context: dict[str, Any]) -> list[str]:
    normalized = question.casefold()
    related = [
        item["key"]
        for item in context["skills"]
        if item["key"].replace("-", " ") in normalized
        or any(part in normalized for part in item["key"].split("-") if len(part) > 4)
    ]
    current = context["currentContext"]
    if current.get("type") == "lab" and current.get("id"):
        related.extend(get_lab(current["id"])["linkedSkills"])
    return list(dict.fromkeys(related))[:6]


def select_adaptation(
    question: str,
    context: dict[str, Any],
    detected: list[str],
    *,
    context_type: str,
) -> AdaptationDecision:
    normalized = question.casefold()
    related = _related_skills(question, context)
    recurring = any(
        item["confidence"] >= 0.75 or item["evidenceCount"] >= 3
        for item in context["misconceptions"]
    )
    failures = len(context["recentFailures"])
    hints = sum(item["hintsUsed"] for item in context["hintHistory"])
    risk = "high" if recurring or failures >= 3 else "medium" if failures or hints >= 2 else "low"
    if recurring:
        return AdaptationDecision(
            "human_review_recommendation",
            "recommend_instructor_review",
            "A recurring misconception has multiple supporting observations.",
            related,
            {
                "type": "instructor_review",
                "id": "scoped-mentor-review",
                "reason": "Repeated evidence indicates that accountable human feedback may help.",
            },
            risk,
        )
    if "hint" in normalized or "stuck" in normalized:
        return AdaptationDecision(
            "hint",
            "give_hint",
            "The learner explicitly requested bounded assistance.",
            related,
            None,
            risk,
        )
    if context_type in {"assessment"}:
        return AdaptationDecision(
            "assessment_support",
            "review_prerequisite",
            "Assessment context requires concept support without answer disclosure.",
            related,
            {
                "type": "lesson",
                "id": related[0] if related else "soc-foundations-course",
                "reason": "Review the underlying concept before continuing the assessment.",
            },
            risk,
        )
    if detected:
        return AdaptationDecision(
            "socratic",
            "ask_question",
            "The learner statement matches a misconception pattern that should be tested.",
            related,
            None,
            risk,
        )
    if context_type == "project":
        current = context["currentContext"]
        improvements = [item for item in current.get("improvementAreas", []) if item]
        action = (
            {
                "type": "lesson",
                "id": improvements[0],
                "reason": (
                    "The human-reviewed project identified this criterion as an improvement area."
                ),
            }
            if improvements
            else None
        )
        return AdaptationDecision(
            "review",
            "recommend_lesson" if action else "ask_question",
            (
                "Use only recorded human-review results when summarizing "
                "project strengths and improvement areas."
            ),
            related,
            action,
            risk,
        )
    if context_type in {"lab", "mission"}:
        current = context["currentContext"]
        mistakes = sum(
            bool(item.get("mistake")) for item in current.get("recentActions", [])
        ) + int(current.get("mistakes", 0))
        if mistakes >= 2:
            return AdaptationDecision(
                "guided_practice",
                "recommend_replay",
                "Repeated investigation mistakes indicate that replay "
                "is more useful than a solution.",
                related,
                {
                    "type": "replay",
                    "id": str(current.get("id") or context_type),
                    "reason": (
                        "Review the decision sequence and correct the earliest unsupported step."
                    ),
                },
                "high",
            )
        return AdaptationDecision(
            "investigation",
            "ask_question",
            "Active practical work benefits from evidence-focused questioning.",
            related,
            None,
            risk,
        )
    if any(word in normalized for word in ("reflect", "what did i learn", "improve")):
        return AdaptationDecision(
            "reflection",
            "ask_question",
            "The learner is reviewing their own reasoning and progress.",
            related,
            None,
            risk,
        )
    if any(word in normalized for word in ("explain", "why", "difference", "analogy")):
        strong = context["strongSkills"]
        return AdaptationDecision(
            "explanation",
            "show_analogy" if strong else "review_prerequisite",
            (
                f"Use demonstrated {strong[0]} knowledge as an analogy."
                if strong
                else "The concept should be explained from its prerequisite."
            ),
            related,
            None,
            risk,
        )
    if failures >= 3 and not (failures >= 5 and context["conversationTurns"] >= 8):
        weak = context["weakSkills"]
        return AdaptationDecision(
            "guided_practice",
            "recommend_lesson",
            "Recent failures indicate a smaller guided step before reassessment.",
            related or weak[:2],
            {
                "type": "lesson",
                "id": weak[0] if weak else "soc-foundations-course",
                "reason": "Recent unsuccessful attempts indicate a prerequisite gap.",
            },
            risk,
        )
    if failures >= 5 and context["conversationTurns"] >= 8:
        return AdaptationDecision(
            "reflection",
            "recommend_break",
            "A dense sequence of unsuccessful attempts suggests a short pause before review.",
            related,
            {
                "type": "break",
                "id": "short-study-break",
                "reason": "Pause briefly, then return to one bounded evidence question.",
            },
            risk,
        )
    if len(context["completedLabs"]) >= 2 and context["completedMissions"] == 0:
        return AdaptationDecision(
            "review",
            "recommend_mission",
            "Completed lab evidence supports moving to an integrated mission.",
            related,
            {
                "type": "mission",
                "id": "harbor-light-phishing-investigation",
                "reason": "Multiple completed labs support an integrated investigation challenge.",
            },
            risk,
        )
    if len(context["strongSkills"]) >= 4 and context["portfolioArtifacts"] == 0:
        return AdaptationDecision(
            "review",
            "recommend_project",
            "Several strong skills are recorded but no portfolio artifact exists.",
            related,
            {
                "type": "project",
                "id": "junior-soc-incident-escalation-project",
                "reason": "Apply demonstrated skills in a human-reviewed portfolio project.",
            },
            risk,
        )
    if context["weakSkills"] and not context["completedLabs"]:
        weak = context["weakSkills"][0]
        lab_id = (
            "soc-lab-linux-auth-triage"
            if weak.startswith("linux")
            else "soc-lab-web-log-independent"
        )
        return AdaptationDecision(
            "guided_practice",
            "recommend_lab",
            "A weak skill has no completed practical-lab evidence.",
            related or [weak],
            {
                "type": "lab",
                "id": lab_id,
                "reason": f"Build practical evidence for {weak.replace('-', ' ')}.",
            },
            risk,
        )
    if len(context["recentImprovements"]) >= 2 and context["independence"] >= 0.7:
        return AdaptationDecision(
            "review",
            "recommend_reassessment",
            "Recent independent improvement supports a more demanding check.",
            related,
            {
                "type": "reassessment",
                "id": related[0] if related else "junior-soc-diagnostic",
                "reason": "Independent evidence has improved across recent attempts.",
            },
            risk,
        )
    return AdaptationDecision(
        "teaching",
        "ask_question",
        "No urgent remediation trigger was observed; teach and check reasoning.",
        related,
        None,
        risk,
    )


def record_roadmap_recommendation(
    db: DatabaseSession,
    auth: AuthContext,
    decision: AdaptationDecision,
) -> None:
    action = decision.recommended_action
    if action is None or decision.intervention not in {
        "recommend_lesson",
        "recommend_lab",
        "recommend_replay",
        "recommend_reassessment",
        "recommend_project",
        "recommend_mission",
        "recommend_instructor_review",
    }:
        return
    existing = db.scalar(
        select(Recommendation).where(
            *_owner(Recommendation, auth),
            Recommendation.activity_type == action["type"],
            Recommendation.activity_id == action["id"],
            Recommendation.status == "active",
        )
    )
    if existing is None:
        db.add(
            Recommendation(
                organization_id=auth.organization_id,
                user_id=auth.user.id,
                activity_type=action["type"],
                activity_id=action["id"],
                reason=action["reason"],
                intervention_type=decision.intervention,
                required=decision.intervention == "recommend_instructor_review",
                status="active",
                engine_version="sentinel-adaptation-1.0.0",
            )
        )
