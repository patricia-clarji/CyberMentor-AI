import uuid
from typing import Any

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session as DatabaseSession

from app.db.session import get_db
from app.identity.dependencies import AuthContext, require_auth, require_csrf
from app.learning.lab_catalog import get_lab, public_catalog, public_lab
from app.learning.lab_service import (
    owned_lab_session,
    replay_payload,
    request_hint,
    run_command,
    save_notes,
    session_payload,
    start_or_resume_lab,
    submit_lab,
)
from app.models.portfolio import PortfolioArtifact
from app.schemas.lab import (
    LabArtifactResponse,
    LabCommandRequest,
    LabCommandResponse,
    LabNotesRequest,
    LabSessionEnvelope,
    LabSubmissionRequest,
)

router = APIRouter(prefix="/labs", tags=["practical-labs"])


@router.get("")
def list_labs(auth: AuthContext = Depends(require_auth)) -> dict[str, Any]:
    del auth
    return {
        "labTypes": sorted({lab["labType"] for lab in public_catalog()}),
        "labs": public_catalog(),
    }


@router.get("/artifacts", response_model=list[LabArtifactResponse])
def list_lab_artifacts(
    auth: AuthContext = Depends(require_auth),
    db: DatabaseSession = Depends(get_db),
) -> list[LabArtifactResponse]:
    artifacts = db.scalars(
        select(PortfolioArtifact)
        .where(
            PortfolioArtifact.organization_id == auth.organization_id,
            PortfolioArtifact.user_id == auth.user.id,
            PortfolioArtifact.source_version.is_not(None),
        )
        .order_by(PortfolioArtifact.created_at.desc())
    ).all()
    return [
        LabArtifactResponse(
            id=artifact.id,
            artifactType=artifact.artifact_type,
            title=artifact.title,
            sourceId=artifact.source_id,
            sourceVersion=artifact.source_version,
            verificationState=artifact.verification_state,
            content=artifact.content,
        )
        for artifact in artifacts
    ]


@router.get("/{lab_id}")
def lab_detail(
    lab_id: str,
    auth: AuthContext = Depends(require_auth),
) -> dict[str, Any]:
    del auth
    return public_lab(get_lab(lab_id), detail=True)


@router.post("/{lab_id}/start", response_model=LabSessionEnvelope, status_code=201)
def start_lab(
    lab_id: str,
    auth: AuthContext = Depends(require_csrf),
    db: DatabaseSession = Depends(get_db),
) -> LabSessionEnvelope:
    session, resumed = start_or_resume_lab(db, auth, lab_id)
    return LabSessionEnvelope(resumed=resumed, session=session_payload(db, session))


@router.get("/sessions/{session_id}", response_model=LabSessionEnvelope)
def get_lab_session(
    session_id: uuid.UUID,
    auth: AuthContext = Depends(require_auth),
    db: DatabaseSession = Depends(get_db),
) -> LabSessionEnvelope:
    session = owned_lab_session(db, auth, session_id)
    return LabSessionEnvelope(resumed=True, session=session_payload(db, session))


@router.post("/sessions/{session_id}/commands", response_model=LabCommandResponse)
def execute_lab_command(
    session_id: uuid.UUID,
    payload: LabCommandRequest,
    auth: AuthContext = Depends(require_csrf),
    db: DatabaseSession = Depends(get_db),
) -> LabCommandResponse:
    session = owned_lab_session(db, auth, session_id, statuses={"active"})
    result = run_command(db, auth, session, payload.command)
    checkpoint = next(
        (
            action["metadata"].get("checkpoint")
            for action in reversed(session_payload(db, session)["actions"])
            if action["type"] == "command"
        ),
        None,
    )
    return LabCommandResponse(
        exitCode=result.exit_code,
        output=result.output,
        cwd=result.cwd,
        checkpoint=checkpoint,
        session=session_payload(db, session),
    )


@router.post("/sessions/{session_id}/hints")
def get_lab_hint(
    session_id: uuid.UUID,
    auth: AuthContext = Depends(require_csrf),
    db: DatabaseSession = Depends(get_db),
) -> dict[str, Any]:
    session = owned_lab_session(db, auth, session_id, statuses={"active"})
    return {"hint": request_hint(db, auth, session), "session": session_payload(db, session)}


@router.patch("/sessions/{session_id}/notes", response_model=LabSessionEnvelope)
def update_lab_notes(
    session_id: uuid.UUID,
    payload: LabNotesRequest,
    auth: AuthContext = Depends(require_csrf),
    db: DatabaseSession = Depends(get_db),
) -> LabSessionEnvelope:
    session = owned_lab_session(db, auth, session_id, statuses={"active"})
    save_notes(db, auth, session, payload.notes, payload.expected_version)
    return LabSessionEnvelope(resumed=True, session=session_payload(db, session))


@router.post("/sessions/{session_id}/submit")
def submit_lab_evidence(
    session_id: uuid.UUID,
    payload: LabSubmissionRequest,
    auth: AuthContext = Depends(require_csrf),
    db: DatabaseSession = Depends(get_db),
) -> dict[str, Any]:
    session = owned_lab_session(db, auth, session_id, statuses={"active", "completed"})
    response = payload.model_dump(exclude={"idempotency_key"})
    result = submit_lab(db, auth, session, response, payload.idempotency_key)
    return {**result, "session": session_payload(db, session)}


@router.get("/sessions/{session_id}/replay")
def get_lab_replay(
    session_id: uuid.UUID,
    auth: AuthContext = Depends(require_auth),
    db: DatabaseSession = Depends(get_db),
) -> dict[str, Any]:
    session = owned_lab_session(db, auth, session_id)
    return replay_payload(db, auth, session)
