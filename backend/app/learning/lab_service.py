import copy
import secrets
import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session as DatabaseSession

from app.core.errors import AppError
from app.identity.dependencies import AuthContext
from app.learning.lab_catalog import get_lab, public_lab
from app.learning.lab_terminal import TerminalResult, execute_terminal
from app.learning.pathway_service import record_attempt
from app.models.lab import LabAction, LabSession, LabSubmission
from app.models.portfolio import CompletionRecord, Portfolio, PortfolioArtifact

EVALUATOR_VERSION = "practical-lab-evaluator-1.0.0"
BAND_RANK = {"needs-revision": 0, "developing": 1, "demonstrated": 2}


def owned_lab_session(
    db: DatabaseSession,
    auth: AuthContext,
    session_id: uuid.UUID,
    *,
    statuses: set[str] | None = None,
) -> LabSession:
    session = db.scalar(
        select(LabSession).where(
            LabSession.id == session_id,
            LabSession.organization_id == auth.organization_id,
            LabSession.user_id == auth.user.id,
        )
    )
    if session is None:
        raise AppError(404, "lab_session_not_found", "The practical lab session was not found.")
    if statuses is not None and session.status not in statuses:
        raise AppError(409, "lab_session_state", "This action is unavailable in the current state.")
    return session


def _elapsed(session: LabSession, now: datetime) -> int:
    started = session.started_at
    if started.tzinfo is None:
        started = started.replace(tzinfo=UTC)
    return max(0, int((now - started).total_seconds()))


def _next_sequence(db: DatabaseSession, session_id: uuid.UUID) -> int:
    value = db.scalar(
        select(func.max(LabAction.sequence)).where(LabAction.session_id == session_id)
    )
    return int(value or 0) + 1


def _add_action(
    db: DatabaseSession,
    auth: AuthContext,
    session: LabSession,
    *,
    action_type: str,
    input_text: str | None,
    output_text: str | None,
    successful: bool,
    mistake: bool = False,
    metadata: dict[str, Any] | None = None,
) -> LabAction:
    now = datetime.now(UTC)
    action = LabAction(
        organization_id=auth.organization_id,
        user_id=auth.user.id,
        session_id=session.id,
        sequence=_next_sequence(db, session.id),
        action_type=action_type,
        input_text=input_text,
        output_text=output_text,
        successful=successful,
        mistake=mistake,
        metadata_json=metadata or {},
        occurred_at=now,
        elapsed_seconds=_elapsed(session, now),
    )
    db.add(action)
    session.last_activity_at = now
    session.version += 1
    return action


def _commands(db: DatabaseSession, session_id: uuid.UUID) -> list[str]:
    actions = db.scalars(
        select(LabAction)
        .where(
            LabAction.session_id == session_id,
            LabAction.action_type == "command",
            LabAction.successful.is_(True),
        )
        .order_by(LabAction.sequence)
    ).all()
    return [
        str(item.metadata_json.get("command"))
        for item in actions
        if item.metadata_json.get("command")
    ]


def _investigation_branch(lab: dict[str, Any], commands: list[str]) -> str:
    validation = lab["validation"]
    required = set(validation.get("requiredCommands", []))
    alternatives = [set(path) for path in validation.get("alternativeCommandPaths", [])]
    observed = set(commands)
    if required.issubset(observed):
        return "primary"
    for index, path in enumerate(alternatives, start=1):
        if path.issubset(observed):
            return f"alternative-{index}"
    return "unresolved"


def _investigation_ready(lab: dict[str, Any], commands: list[str]) -> bool:
    return _investigation_branch(lab, commands) != "unresolved"


def _filesystem_ready(lab: dict[str, Any], files: list[dict[str, Any]]) -> bool:
    for expected in lab["validation"].get("requiredFilesystem", []):
        actual = next((item for item in files if item["path"] == expected["path"]), None)
        if actual is None or any(
            actual.get(key) != value for key, value in expected.items() if key != "path"
        ):
            return False
    return True


def _objective_state(
    lab: dict[str, Any],
    commands: list[str],
    *,
    submission_ready: bool = False,
) -> dict[str, Any]:
    investigation = _investigation_ready(lab, commands)
    required = [item for item in lab["objectives"] if item.get("required")]
    state: dict[str, Any] = {}
    for index, objective in enumerate(lab["objectives"]):
        completed = False
        if objective.get("bonus"):
            completed = "ps" in commands or "ss" in commands or "netstat" in commands
        elif index == 0:
            completed = investigation
        elif submission_ready:
            completed = True
        state[objective["id"]] = {
            "title": objective["title"],
            "required": bool(objective.get("required")),
            "bonus": bool(objective.get("bonus")),
            "stage": objective["stage"],
            "completed": completed,
        }
    completed_required = sum(state[item["id"]]["completed"] for item in required)
    return {
        "objectives": state,
        "requiredCompleted": completed_required,
        "requiredTotal": len(required),
        "activeBranch": _investigation_branch(lab, commands),
    }


def session_payload(
    db: DatabaseSession,
    session: LabSession,
    *,
    include_actions: bool = True,
) -> dict[str, Any]:
    lab = get_lab(session.lab_id)
    payload: dict[str, Any] = {
        "sessionId": str(session.id),
        "lab": public_lab(lab, detail=True),
        "status": session.status,
        "currentStage": session.current_stage,
        "cwd": session.cwd,
        "objectiveState": session.objective_state,
        "scoreComponents": session.score_components,
        "notes": session.notes,
        "hintsUsed": session.hints_used,
        "commandCount": session.command_count,
        "incorrectCommandCount": session.incorrect_command_count,
        "outcome": session.outcome,
        "version": session.version,
        "startedAt": session.started_at.isoformat(),
        "lastActivityAt": session.last_activity_at.isoformat(),
        "completedAt": session.completed_at.isoformat() if session.completed_at else None,
    }
    if include_actions:
        actions = db.scalars(
            select(LabAction).where(LabAction.session_id == session.id).order_by(LabAction.sequence)
        ).all()
        payload["actions"] = [
            {
                "sequence": action.sequence,
                "type": action.action_type,
                "input": action.input_text,
                "output": action.output_text,
                "successful": action.successful,
                "mistake": action.mistake,
                "metadata": action.metadata_json,
                "elapsedSeconds": action.elapsed_seconds,
            }
            for action in actions
        ]
    return payload


def start_or_resume_lab(
    db: DatabaseSession,
    auth: AuthContext,
    lab_id: str,
) -> tuple[LabSession, bool]:
    lab = get_lab(lab_id)
    existing = db.scalar(
        select(LabSession).where(
            LabSession.organization_id == auth.organization_id,
            LabSession.user_id == auth.user.id,
            LabSession.lab_id == lab_id,
            LabSession.active_key == "active",
        )
    )
    if existing is not None:
        return existing, True
    now = datetime.now(UTC)
    environment = lab["virtualEnvironment"]
    session = LabSession(
        organization_id=auth.organization_id,
        user_id=auth.user.id,
        lab_id=lab_id,
        lab_version=lab["version"],
        status="active",
        active_key="active",
        current_stage=1,
        cwd=environment["cwd"],
        filesystem_state=copy.deepcopy(environment["files"]),
        objective_state=_objective_state(lab, []),
        score_components={},
        notes="",
        hints_used=0,
        command_count=0,
        incorrect_command_count=0,
        started_at=now,
        last_activity_at=now,
        version=1,
    )
    db.add(session)
    db.flush()
    _add_action(
        db,
        auth,
        session,
        action_type="session_started",
        input_text=None,
        output_text="Synthetic practical lab initialized.",
        successful=True,
        metadata={"labVersion": lab["version"]},
    )
    db.commit()
    db.refresh(session)
    return session, False


def run_command(
    db: DatabaseSession,
    auth: AuthContext,
    session: LabSession,
    command_text: str,
) -> TerminalResult:
    lab = get_lab(session.lab_id)
    environment = lab["virtualEnvironment"]
    files = copy.deepcopy(session.filesystem_state)
    result = execute_terminal(
        command_text,
        cwd=session.cwd,
        files=files,
        processes=environment.get("processes", []),
        connections=environment.get("connections", []),
        allowed_tools=set(lab["availableTools"]),
    )
    session.command_count += 1
    if result.exit_code != 0:
        session.incorrect_command_count += 1
    session.cwd = result.cwd
    session.filesystem_state = files
    checkpoint = next(
        (
            item["feedback"]
            for item in lab.get("checkpoints", [])
            if item["afterCommand"] == result.command and result.exit_code == 0
        ),
        None,
    )
    _add_action(
        db,
        auth,
        session,
        action_type="command",
        input_text=command_text,
        output_text=result.output,
        successful=result.exit_code == 0,
        mistake=result.exit_code != 0,
        metadata={
            "command": result.command,
            "exitCode": result.exit_code,
            "checkpoint": checkpoint,
        },
    )
    commands = _commands(db, session.id)
    if result.exit_code == 0 and result.command:
        commands.append(result.command)
    session.objective_state = _objective_state(lab, commands)
    stages = [
        value["stage"]
        for value in session.objective_state["objectives"].values()
        if value["completed"]
    ]
    session.current_stage = min(
        max((max(stages) + 1) if stages else 1, 1),
        max(item["stage"] for item in lab["objectives"]),
    )
    db.commit()
    return result


def request_hint(
    db: DatabaseSession,
    auth: AuthContext,
    session: LabSession,
) -> dict[str, Any]:
    lab = get_lab(session.lab_id)
    level = min(5, session.hints_used + 1)
    hint = lab["hints"][level - 1]
    session.hints_used += 1
    _add_action(
        db,
        auth,
        session,
        action_type="hint",
        input_text=f"level {level}",
        output_text=hint["text"],
        successful=True,
        metadata={"level": level, "kind": hint["kind"]},
    )
    db.commit()
    return {
        **hint,
        "independenceNotice": (
            "This progressive hint is recorded as independence evidence "
            "and does not block completion."
        ),
    }


def save_notes(
    db: DatabaseSession,
    auth: AuthContext,
    session: LabSession,
    notes: str,
    expected_version: int,
) -> LabSession:
    if session.version != expected_version:
        raise AppError(
            409,
            "stale_lab_session",
            "The lab changed in another request. Refresh before saving these notes.",
        )
    session.notes = notes
    _add_action(
        db,
        auth,
        session,
        action_type="notes_saved",
        input_text=None,
        output_text=None,
        successful=True,
        metadata={"length": len(notes)},
    )
    db.commit()
    db.refresh(session)
    return session


def _field_score(specification: dict[str, Any], value: str) -> float:
    normalized = " ".join(value.casefold().split())
    accepted = specification.get("accepted")
    if accepted:
        return 1.0 if any(item.casefold() in normalized for item in accepted) else 0.0
    if len(value.strip()) < int(specification.get("minimumLength", 0)):
        return 0.0
    keywords = specification.get("keywords", [])
    required = int(specification.get("minimumMatches", len(keywords) or 1))
    matches = sum(keyword.casefold() in normalized for keyword in keywords)
    return min(1.0, matches / max(1, required))


def _component_label(value: float) -> str:
    if value >= 0.85:
        return "demonstrated"
    if value >= 0.6:
        return "developing"
    return "needs-revision"


def _create_artifact(
    db: DatabaseSession,
    auth: AuthContext,
    session: LabSession,
    lab: dict[str, Any],
    response: dict[str, str],
    components: dict[str, float],
) -> tuple[PortfolioArtifact | None, CompletionRecord | None]:
    if not lab["portfolioEligibility"]:
        return None, None
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
        artifact_type=lab["generatedEvidence"]["artifactType"],
        source_id=str(session.id),
        source_version=lab["version"],
        title=lab["generatedEvidence"]["title"],
        verification_state="verified",
        visibility="private",
        content={
            "labId": lab["id"],
            "labTitle": lab["title"],
            "synthetic": True,
            "report": response["report"],
            "indicator": response["indicator"],
            "classification": response["classification"],
            "recommendation": response["recommendation"],
            "reflection": response["reflection"],
            "skills": lab["linkedSkills"],
            "assessment": {key: _component_label(value) for key, value in components.items()},
        },
    )
    db.add(artifact)
    completion = CompletionRecord(
        organization_id=auth.organization_id,
        user_id=auth.user.id,
        verification_id=secrets.token_urlsafe(18),
        criteria_version=EVALUATOR_VERSION,
        scope_type="practical_lab",
        scope_id=lab["id"],
        skill_summary=[{"skill": key, "result": "demonstrated"} for key in lab["linkedSkills"]],
        evidence_summary=[
            {
                "type": "synthetic_practical_lab",
                "sessionId": str(session.id),
                "labVersion": lab["version"],
                "overallBand": session.outcome,
            }
        ],
        issued_at=datetime.now(UTC),
    )
    db.add(completion)
    return artifact, completion


def submit_lab(
    db: DatabaseSession,
    auth: AuthContext,
    session: LabSession,
    response: dict[str, str],
    idempotency_key: str,
) -> dict[str, Any]:
    existing = db.scalar(
        select(LabSubmission).where(
            LabSubmission.session_id == session.id,
            LabSubmission.idempotency_key == idempotency_key,
        )
    )
    if existing is not None:
        if existing.response != response:
            raise AppError(
                409,
                "idempotency_conflict",
                "This submission key was already used for different lab evidence.",
            )
        return _submission_payload(db, existing)
    if session.status == "completed":
        raise AppError(
            409,
            "lab_already_completed",
            "This lab session is complete. Start a new session for another attempt.",
        )
    lab = get_lab(session.lab_id)
    commands = _commands(db, session.id)
    specifications = lab["validation"]["submissionFields"]
    field_scores = {
        key: _field_score(specification, response.get(key, ""))
        for key, specification in specifications.items()
    }
    correctness = sum(field_scores.values()) / max(1, len(field_scores))
    evidence_quality = (field_scores.get("indicator", 0) + field_scores.get("report", 0)) / 2
    decision_quality = (
        field_scores.get("classification", 0) + field_scores.get("recommendation", 0)
    ) / 2
    report_quality = field_scores.get("report", 0)
    ideal = max(3, len(lab["validation"].get("requiredCommands", [])) + 2)
    efficiency = max(
        0.2,
        1.0
        - (max(0, session.command_count - ideal) * 0.06)
        - (session.incorrect_command_count * 0.1),
    )
    independence = max(0.2, 1.0 - (session.hints_used * 0.16))
    components = {
        "correctness": correctness,
        "efficiency": efficiency,
        "evidenceQuality": evidence_quality,
        "independence": independence,
        "decisionQuality": decision_quality,
        "reportQuality": report_quality,
    }
    investigation_ready = _investigation_ready(lab, commands)
    filesystem_ready = _filesystem_ready(lab, session.filesystem_state)
    if (
        correctness >= 0.9
        and evidence_quality >= 0.8
        and decision_quality >= 0.75
        and report_quality >= 0.75
        and investigation_ready
        and filesystem_ready
    ):
        band = "demonstrated"
    elif correctness >= 0.65 and report_quality >= 0.5 and investigation_ready and filesystem_ready:
        band = "developing"
    else:
        band = "needs-revision"
    minimum_band = lab["completionCriteria"]["minimumOverallBand"]
    passed = BAND_RANK[band] >= BAND_RANK[minimum_band]
    feedback = []
    if not investigation_ready:
        feedback.append("Use a valid investigation path before submitting.")
    if not filesystem_ready:
        feedback.append("The required virtual file ownership or mode is not yet correct.")
    for key, score in field_scores.items():
        if score < 0.65:
            feedback.append(f"Strengthen the {key.replace('_', ' ')} evidence.")
    if not feedback:
        feedback.append("The submitted evidence supports the recorded outcome.")
    now = datetime.now(UTC)
    submission = LabSubmission(
        organization_id=auth.organization_id,
        user_id=auth.user.id,
        session_id=session.id,
        idempotency_key=idempotency_key,
        response=response,
        correctness=correctness,
        efficiency=efficiency,
        evidence_quality=evidence_quality,
        independence=independence,
        decision_quality=decision_quality,
        report_quality=report_quality,
        overall_band=band,
        passed=passed,
        feedback=feedback,
        evaluator_version=EVALUATOR_VERSION,
        submitted_at=now,
    )
    db.add(submission)
    session.score_components = {
        key: {"band": _component_label(value)} for key, value in components.items()
    }
    session.final_submission = response
    session.outcome = band if passed else "partial-success"
    session.objective_state = _objective_state(lab, commands, submission_ready=passed)
    if passed:
        session.status = "completed"
        session.active_key = None
        session.completed_at = now
    _add_action(
        db,
        auth,
        session,
        action_type="submission",
        input_text=None,
        output_text="\n".join(feedback),
        successful=passed,
        mistake=not passed,
        metadata={"overallBand": band, "passed": passed},
    )
    db.flush()
    artifact = None
    completion = None
    if passed:
        artifact, completion = _create_artifact(db, auth, session, lab, response, components)
        record_attempt(
            db,
            auth,
            activity_id=lab["id"],
            activity_type="practical_lab",
            module_id="trusted-practical-labs",
            response=response,
            score=(
                correctness * 0.3
                + evidence_quality * 0.2
                + decision_quality * 0.2
                + report_quality * 0.15
                + independence * 0.1
                + efficiency * 0.05
            ),
            feedback=" ".join(feedback),
            idempotency_key=f"lab:{session.id}:{idempotency_key}",
            hints_used=session.hints_used,
            skill_keys=lab["linkedSkills"],
        )
    else:
        db.commit()
    db.refresh(submission)
    return {
        **_submission_payload(db, submission),
        "portfolioArtifactId": str(artifact.id) if artifact else None,
        "completionVerificationId": completion.verification_id if completion else None,
    }


def _submission_payload(db: DatabaseSession, submission: LabSubmission) -> dict[str, Any]:
    artifact = db.scalar(
        select(PortfolioArtifact).where(
            PortfolioArtifact.source_id == str(submission.session_id),
            PortfolioArtifact.organization_id == submission.organization_id,
            PortfolioArtifact.user_id == submission.user_id,
        )
    )
    session = db.get(LabSession, submission.session_id)
    completion = db.scalar(
        select(CompletionRecord)
        .where(
            CompletionRecord.organization_id == submission.organization_id,
            CompletionRecord.user_id == submission.user_id,
            CompletionRecord.scope_type == "practical_lab",
            CompletionRecord.scope_id == (session.lab_id if session else ""),
        )
        .order_by(CompletionRecord.issued_at.desc())
    )
    return {
        "submissionId": str(submission.id),
        "passed": submission.passed,
        "overallBand": submission.overall_band,
        "components": {
            "correctness": _component_label(submission.correctness),
            "efficiency": _component_label(submission.efficiency),
            "evidenceQuality": _component_label(submission.evidence_quality),
            "independence": _component_label(submission.independence),
            "decisionQuality": _component_label(submission.decision_quality),
            "reportQuality": _component_label(submission.report_quality),
        },
        "feedback": submission.feedback,
        "portfolioArtifactId": str(artifact.id) if artifact else None,
        "completionVerificationId": completion.verification_id if completion else None,
        "canRetry": not submission.passed,
    }


def replay_payload(
    db: DatabaseSession,
    auth: AuthContext,
    session: LabSession,
) -> dict[str, Any]:
    actions = db.scalars(
        select(LabAction)
        .where(
            LabAction.session_id == session.id,
            LabAction.organization_id == auth.organization_id,
            LabAction.user_id == auth.user.id,
        )
        .order_by(LabAction.sequence)
    ).all()
    lab = get_lab(session.lab_id)
    prior_mistake = False
    timeline = []
    corrections = []
    for action in actions:
        if action.mistake:
            prior_mistake = True
        if prior_mistake and action.successful and action.action_type in {"command", "submission"}:
            corrections.append(
                {"sequence": action.sequence, "action": action.input_text or action.action_type}
            )
            prior_mistake = False
        timeline.append(
            {
                "sequence": action.sequence,
                "type": action.action_type,
                "input": action.input_text,
                "output": action.output_text,
                "successful": action.successful,
                "mistake": action.mistake,
                "elapsedSeconds": action.elapsed_seconds,
                "metadata": action.metadata_json,
            }
        )
    return {
        "sessionId": str(session.id),
        "status": session.status,
        "timeline": timeline,
        "mistakes": [item for item in timeline if item["mistake"]],
        "corrections": corrections,
        "hints": [item for item in timeline if item["type"] == "hint"],
        "timeSpentSeconds": max((action.elapsed_seconds for action in actions), default=0),
        "alternativeValidPaths": lab["validation"].get("alternativeCommandPaths", []),
        "expertSolution": lab["expertSolution"] if session.status == "completed" else None,
    }
