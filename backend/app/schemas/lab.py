import uuid
from typing import Any

from pydantic import BaseModel, Field


class LabCommandRequest(BaseModel):
    command: str = Field(min_length=1, max_length=1000)


class LabNotesRequest(BaseModel):
    notes: str = Field(max_length=12000)
    expected_version: int = Field(ge=1)


class LabSubmissionRequest(BaseModel):
    indicator: str = Field(min_length=1, max_length=1000)
    classification: str = Field(min_length=1, max_length=1000)
    recommendation: str = Field(min_length=20, max_length=5000)
    report: str = Field(min_length=80, max_length=12000)
    reflection: str = Field(min_length=20, max_length=5000)
    idempotency_key: str = Field(min_length=8, max_length=120)


class LabSessionEnvelope(BaseModel):
    resumed: bool = False
    session: dict[str, Any]


class LabCommandResponse(BaseModel):
    exitCode: int
    output: str
    cwd: str
    checkpoint: str | None = None
    session: dict[str, Any]


class LabArtifactResponse(BaseModel):
    id: uuid.UUID
    artifactType: str
    title: str
    sourceId: str
    sourceVersion: str | None
    verificationState: str
    content: dict[str, Any] | None
