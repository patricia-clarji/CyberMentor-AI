import hashlib
import re
import secrets
import uuid
from datetime import UTC, datetime
from io import BytesIO
from typing import Any, Literal

from fastapi import APIRouter, Depends, Request
from fastapi.responses import Response
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import func, select
from sqlalchemy.orm import Session as DatabaseSession

from app.core.errors import AppError
from app.db.session import get_db
from app.identity.dependencies import AuthContext, assert_permission, require_auth, require_csrf
from app.identity.service import audit
from app.models.career import CareerCertificate, LearnerReflection, ProfessionalProfile
from app.models.identity import Organization
from app.models.learning import Enrollment, LearnerSkillState, Skill, SkillEvidence
from app.models.mission import MissionResult, MissionSession
from app.models.portfolio import (
    CompletionRecord,
    PortfolioArtifact,
    ProjectReview,
    ProjectSubmission,
)

router = APIRouter(prefix="/career", tags=["career development"])
public_router = APIRouter(prefix="/career-public", tags=["public professional portfolio"])

ROLE_MAP: dict[str, dict[str, Any]] = {
    "soc-analyst": {
        "name": "SOC Analyst",
        "required": ["evidence-preservation", "escalation-writing"],
        "recommended": ["dns-evidence", "http-evidence"],
    },
    "security-analyst": {
        "name": "Security Analyst",
        "required": ["evidence-preservation", "escalation-writing"],
        "recommended": ["linux-evidence", "windows-evidence"],
    },
    "blue-team-analyst": {
        "name": "Blue Team Analyst",
        "required": ["evidence-preservation", "escalation-writing"],
        "recommended": ["siem-triage", "authentication-evidence"],
    },
    "incident-responder": {
        "name": "Incident Responder",
        "required": ["evidence-preservation", "escalation-writing"],
        "recommended": ["linux-evidence", "windows-evidence"],
    },
    "threat-hunter": {
        "name": "Threat Hunter",
        "required": ["evidence-preservation", "dns-evidence"],
        "recommended": ["http-evidence", "siem-triage"],
    },
    "junior-penetration-tester": {
        "name": "Junior Penetration Tester",
        "required": ["linux-evidence", "evidence-preservation"],
        "recommended": ["http-evidence", "escalation-writing"],
    },
    "application-security-analyst": {
        "name": "Application Security Analyst",
        "required": ["http-evidence", "evidence-preservation"],
        "recommended": ["escalation-writing"],
    },
    "cloud-security-analyst": {
        "name": "Cloud Security Analyst",
        "required": ["authentication-evidence", "evidence-preservation"],
        "recommended": ["siem-triage"],
    },
    "grc-analyst": {
        "name": "GRC Analyst",
        "required": ["escalation-writing", "evidence-preservation"],
        "recommended": ["authentication-evidence"],
    },
}


class ProfileInput(BaseModel):
    headline: str | None = Field(default=None, max_length=180)
    biography: str | None = Field(default=None, max_length=6000)
    career_goals: str | None = Field(default=None, max_length=3000)
    experience_level: str | None = Field(default=None, max_length=40)
    current_education: str | None = Field(default=None, max_length=220)
    university: str | None = Field(default=None, max_length=220)
    degree: str | None = Field(default=None, max_length=180)
    graduation_year: int | None = Field(default=None, ge=1900, le=2200)
    availability: str | None = Field(default=None, max_length=80)
    preferred_locations: list[str] = Field(default_factory=list, max_length=20)
    remote_preference: str | None = Field(default=None, max_length=40)
    timezone: str | None = Field(default=None, max_length=80)
    domains: list[str] = Field(default_factory=list, max_length=20)
    technical_interests: list[str] = Field(default_factory=list, max_length=30)
    languages: list[str] = Field(default_factory=list, max_length=20)
    links: dict[str, str] = Field(default_factory=dict)
    employment_history: list[dict[str, str]] = Field(default_factory=list, max_length=20)
    privacy: dict[str, Literal["private", "organization_only", "recruiter_only", "public"]] = Field(
        default_factory=dict
    )
    portfolio_visibility: Literal[
        "private", "link_only", "public", "organization_only", "recruiter_only"
    ] = "private"

    @field_validator("links")
    @classmethod
    def safe_links(cls, value: dict[str, str]) -> dict[str, str]:
        allowed = {"github", "linkedin", "website", "resume"}
        if not set(value).issubset(allowed):
            raise ValueError("Only GitHub, LinkedIn, website, and resume links are supported.")
        if any(url and not re.match(r"^https://", url) for url in value.values()):
            raise ValueError("Profile links must use HTTPS.")
        return value


class ReflectionInput(BaseModel):
    source_type: Literal["course", "lesson", "lab", "mission", "project", "assessment"]
    source_id: str = Field(min_length=1, max_length=160)
    learned: str = Field(min_length=10, max_length=5000)
    difficult: str = Field(min_length=3, max_length=5000)
    improvement: str = Field(min_length=3, max_length=5000)
    confidence: int = Field(ge=1, le=5)
    professional_application: str = Field(min_length=10, max_length=5000)


class CertificateRevocationRequest(BaseModel):
    reason: str = Field(min_length=5, max_length=2_000)


def profile_for(
    db: DatabaseSession, auth: AuthContext, create: bool = True
) -> ProfessionalProfile | None:
    profile = db.scalar(
        select(ProfessionalProfile).where(
            ProfessionalProfile.organization_id == auth.organization_id,
            ProfessionalProfile.user_id == auth.user.id,
        )
    )
    if profile is None and create:
        profile = ProfessionalProfile(organization_id=auth.organization_id, user_id=auth.user.id)
        db.add(profile)
        db.flush()
    return profile


def profile_payload(profile: ProfessionalProfile, public: bool = False) -> dict[str, Any]:
    data: dict[str, Any] = {
        column: getattr(profile, column) for column in ProfileInput.model_fields
    }
    data.update(
        {"id": str(profile.id), "public_slug": profile.public_slug, "version": profile.version}
    )
    if public:
        privacy = profile.privacy or {}
        return {
            key: value
            for key, value in data.items()
            if key
            in {
                "headline",
                "domains",
                "technical_interests",
                "languages",
                "portfolio_visibility",
                "public_slug",
            }
            or privacy.get(key) == "public"
        }
    return data


def passport(
    db: DatabaseSession, organization_id: uuid.UUID, user_id: uuid.UUID
) -> list[dict[str, Any]]:
    rows = db.execute(
        select(Skill, LearnerSkillState)
        .join(LearnerSkillState, LearnerSkillState.skill_id == Skill.id)
        .where(
            LearnerSkillState.organization_id == organization_id,
            LearnerSkillState.user_id == user_id,
        )
        .order_by(Skill.name)
    ).all()
    result: list[dict[str, Any]] = []
    for skill, state in rows:
        evidence = list(
            db.scalars(
                select(SkillEvidence)
                .where(
                    SkillEvidence.organization_id == organization_id,
                    SkillEvidence.user_id == user_id,
                    SkillEvidence.skill_id == skill.id,
                )
                .order_by(SkillEvidence.occurred_at)
            ).all()
        )
        sources: dict[str, list[str]] = {
            "labs": [],
            "missions": [],
            "projects": [],
            "assessments": [],
        }
        for item in evidence:
            key = {
                "lab": "labs",
                "mission": "missions",
                "project": "projects",
                "assessment": "assessments",
            }.get(item.source_type)
            if key:
                sources[key].append(item.source_id)
        result.append(
            {
                "skill_id": skill.stable_key,
                "skill_name": skill.name,
                "mastery_level": round(state.mastery_estimate, 3),
                "confidence": round(state.confidence, 3),
                "evidence_count": len(evidence),
                "verification_status": "verified"
                if len(evidence) >= skill.minimum_evidence
                else "developing",
                "first_demonstrated": evidence[0].occurred_at if evidence else None,
                "last_demonstrated": evidence[-1].occurred_at if evidence else None,
                "version": state.engine_version,
                "history": [
                    {
                        "source_type": item.source_type,
                        "source_id": item.source_id,
                        "score": item.score,
                        "occurred_at": item.occurred_at,
                    }
                    for item in evidence
                ],
                **sources,
            }
        )
    return result


def verified_evidence(db: DatabaseSession, auth: AuthContext) -> dict[str, Any]:
    artifacts = list(
        db.scalars(
            select(PortfolioArtifact).where(
                PortfolioArtifact.organization_id == auth.organization_id,
                PortfolioArtifact.user_id == auth.user.id,
                PortfolioArtifact.verification_state == "verified",
                PortfolioArtifact.revoked_at.is_(None),
            )
        ).all()
    )
    completions = list(
        db.scalars(
            select(CompletionRecord).where(
                CompletionRecord.organization_id == auth.organization_id,
                CompletionRecord.user_id == auth.user.id,
                CompletionRecord.revoked_at.is_(None),
            )
        ).all()
    )
    return {
        "artifacts": [
            {
                "id": str(a.id),
                "title": a.title,
                "type": a.artifact_type,
                "source_id": a.source_id,
                "created_at": a.created_at,
            }
            for a in artifacts
        ],
        "completion_records": [
            {
                "id": str(c.id),
                "verification_id": c.verification_id,
                "scope_type": c.scope_type,
                "scope_id": c.scope_id,
                "version": c.criteria_version,
                "issued_at": c.issued_at,
            }
            for c in completions
        ],
    }


def timeline(db: DatabaseSession, auth: AuthContext) -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = []
    for completion in db.scalars(
        select(CompletionRecord).where(
            CompletionRecord.organization_id == auth.organization_id,
            CompletionRecord.user_id == auth.user.id,
        )
    ):
        events.append(
            {
                "type": "completion_record",
                "title": f"Completed {completion.scope_type}: {completion.scope_id}",
                "occurred_at": completion.issued_at,
                "source_id": str(completion.id),
            }
        )
    for certificate in db.scalars(
        select(CareerCertificate).where(
            CareerCertificate.organization_id == auth.organization_id,
            CareerCertificate.user_id == auth.user.id,
        )
    ):
        events.append(
            {
                "type": "certificate_earned",
                "title": f"Certificate issued: {certificate.course_name}",
                "occurred_at": certificate.issued_at,
                "source_id": str(certificate.id),
            }
        )
    for submission in db.scalars(
        select(ProjectSubmission).where(
            ProjectSubmission.organization_id == auth.organization_id,
            ProjectSubmission.user_id == auth.user.id,
            ProjectSubmission.status == "passed",
        )
    ):
        events.append(
            {
                "type": "project_reviewed",
                "title": "Project evidence verified",
                "occurred_at": submission.updated_at,
                "source_id": str(submission.id),
            }
        )
    for session in db.scalars(
        select(MissionSession).where(
            MissionSession.organization_id == auth.organization_id,
            MissionSession.user_id == auth.user.id,
            MissionSession.status == "completed",
        )
    ):
        events.append(
            {
                "type": "mission_completed",
                "title": "Mission completed",
                "occurred_at": session.completed_at or session.created_at,
                "source_id": str(session.id),
            }
        )
    return sorted(events, key=lambda item: item["occurred_at"], reverse=True)


def pdf(title: str, lines: list[str]) -> bytes:
    safe = [re.sub(r"[^ -~]", "?", line)[:110] for line in [title, *lines]]
    stream = (
        "BT /F1 16 Tf 50 780 Td (" + safe[0].replace("(", "[").replace(")", "]") + ") Tj /F1 10 Tf"
    )
    for line in safe[1:]:
        stream += " 0 -18 Td (" + line.replace("(", "[").replace(")", "]") + ") Tj"
    stream += " ET"
    objects = [
        "<< /Type /Catalog /Pages 2 0 R >>",
        "<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        "<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
        "/Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>",
        "<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
        f"<< /Length {len(stream.encode())} >>\nstream\n{stream}\nendstream",
    ]
    output = BytesIO()
    output.write(b"%PDF-1.4\n")
    offsets = [0]
    for index, obj in enumerate(objects, 1):
        offsets.append(output.tell())
        output.write(f"{index} 0 obj\n{obj}\nendobj\n".encode())
    start = output.tell()
    output.write(f"xref\n0 {len(objects) + 1}\n0000000000 65535 f \n".encode())
    [output.write(f"{offset:010d} 00000 n \n".encode()) for offset in offsets[1:]]
    output.write(
        f"trailer << /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{start}\n%%EOF".encode()
    )
    return output.getvalue()


@router.get("/profile")
def get_profile(
    auth: AuthContext = Depends(require_auth), db: DatabaseSession = Depends(get_db)
) -> dict[str, Any]:
    profile = profile_for(db, auth)
    assert profile is not None
    return profile_payload(profile)


@router.put("/profile")
def update_profile(
    payload: ProfileInput,
    request: Request,
    auth: AuthContext = Depends(require_csrf),
    db: DatabaseSession = Depends(get_db),
) -> dict[str, Any]:
    profile = profile_for(db, auth)
    assert profile is not None
    for key, value in payload.model_dump().items():
        setattr(profile, key, value)
    if profile.portfolio_visibility in {"public", "link_only"} and not profile.public_slug:
        profile.public_slug = f"{auth.user.id.hex[:10]}-{secrets.token_hex(3)}"
    profile.version += 1
    audit(
        db,
        "career.profile_updated",
        "success",
        auth.user.id,
        auth.organization_id,
        getattr(request.state, "request_id", None),
        "professional_profile",
        str(profile.id),
    )
    db.commit()
    return profile_payload(profile)


@router.get("/passport")
def get_passport(
    auth: AuthContext = Depends(require_auth), db: DatabaseSession = Depends(get_db)
) -> dict[str, Any]:
    return {
        "skills": passport(db, auth.organization_id, auth.user.id),
        "notice": (
            "Skill Passport entries are derived only from persisted verified learning evidence."
        ),
    }


@router.get("/portfolio")
def get_portfolio(
    auth: AuthContext = Depends(require_auth), db: DatabaseSession = Depends(get_db)
) -> dict[str, Any]:
    profile = profile_for(db, auth)
    assert profile is not None
    return {
        "profile": profile_payload(profile),
        "skill_passport": passport(db, auth.organization_id, auth.user.id),
        "evidence": verified_evidence(db, auth),
        "timeline": timeline(db, auth),
    }


@router.get("/reflections")
def list_reflections(
    auth: AuthContext = Depends(require_auth), db: DatabaseSession = Depends(get_db)
) -> list[dict[str, Any]]:
    return [
        {
            "id": str(x.id),
            "source_type": x.source_type,
            "source_id": x.source_id,
            "learned": x.learned,
            "difficult": x.difficult,
            "improvement": x.improvement,
            "confidence": x.confidence,
            "professional_application": x.professional_application,
            "revision": x.revision,
            "created_at": x.created_at,
        }
        for x in db.scalars(
            select(LearnerReflection)
            .where(
                LearnerReflection.organization_id == auth.organization_id,
                LearnerReflection.user_id == auth.user.id,
            )
            .order_by(LearnerReflection.created_at.desc())
        )
    ]


@router.post("/reflections", status_code=201)
def create_reflection(
    payload: ReflectionInput,
    auth: AuthContext = Depends(require_csrf),
    db: DatabaseSession = Depends(get_db),
) -> dict[str, Any]:
    prior = (
        db.scalar(
            select(func.max(LearnerReflection.revision)).where(
                LearnerReflection.organization_id == auth.organization_id,
                LearnerReflection.user_id == auth.user.id,
                LearnerReflection.source_type == payload.source_type,
                LearnerReflection.source_id == payload.source_id,
            )
        )
        or 0
    )
    item = LearnerReflection(
        organization_id=auth.organization_id,
        user_id=auth.user.id,
        revision=prior + 1,
        **payload.model_dump(),
    )
    db.add(item)
    db.commit()
    return {"id": str(item.id), "revision": item.revision}


@router.get("/roles")
def roles() -> list[dict[str, Any]]:
    return [
        {
            "key": key,
            "name": value["name"],
            "required_skills": value["required"],
            "recommended_skills": value["recommended"],
            "required_evidence": ["verified skill evidence", "verified completion record"],
            "recommended_projects": ["human-reviewed project"],
        }
        for key, value in ROLE_MAP.items()
    ]


@router.get("/readiness")
def readiness(
    auth: AuthContext = Depends(require_auth), db: DatabaseSession = Depends(get_db)
) -> dict[str, Any]:
    skills = passport(db, auth.organization_id, auth.user.id)
    evidence = verified_evidence(db, auth)
    verified = [x for x in skills if x["verification_status"] == "verified"]
    average = sum(x["mastery_level"] for x in skills) / len(skills) if skills else 0
    roles_result = []
    for key, role in ROLE_MAP.items():
        present = {x["skill_id"] for x in verified}
        required = set(role["required"])
        missing = sorted(required - present)
        score = round(
            100
            * (len(required) - len(missing))
            / len(required)
            * min(1, len(evidence["completion_records"]) / 2),
            1,
        )
        roles_result.append(
            {
                "key": key,
                "name": role["name"],
                "readiness_score": score,
                "missing_skills": missing,
                "why": (
                    "Based on verified skill evidence and durable completion records; "
                    "it is not a hiring prediction."
                ),
            }
        )
    return {
        "strengths": [x["skill_name"] for x in verified],
        "weaknesses": [x["skill_name"] for x in skills if x["mastery_level"] < 0.6],
        "recommended_learning": [
            "Complete a verified lab or mission for every missing role skill."
        ],
        "portfolio_completeness": {
            "profile": bool(profile_for(db, auth, False)),
            "verified_evidence_items": len(evidence["artifacts"])
            + len(evidence["completion_records"]),
        },
        "technical_skill_average": round(average, 3),
        "role_matches": sorted(roles_result, key=lambda x: x["readiness_score"], reverse=True),
    }


@router.post("/certificates/from-completion/{completion_id}", status_code=201)
def issue_certificate(
    completion_id: uuid.UUID,
    auth: AuthContext = Depends(require_csrf),
    db: DatabaseSession = Depends(get_db),
) -> dict[str, Any]:
    completion = db.scalar(
        select(CompletionRecord).where(
            CompletionRecord.id == completion_id,
            CompletionRecord.organization_id == auth.organization_id,
            CompletionRecord.user_id == auth.user.id,
            CompletionRecord.revoked_at.is_(None),
        )
    )
    if completion is None:
        raise AppError(
            404,
            "eligible_completion_not_found",
            "A current verified completion record is required before a certificate can be issued.",
        )
    existing = db.scalar(
        select(CareerCertificate).where(CareerCertificate.completion_record_id == completion.id)
    )
    if existing:
        return certificate_payload(existing)
    organization = db.get(Organization, auth.organization_id)
    now = datetime.now(UTC)
    certificate_id = f"CM-{now.year}-{secrets.token_hex(5).upper()}"
    code = secrets.token_urlsafe(16)
    facts = {
        "completionCriteria": completion.criteria_version,
        "skills": completion.skill_summary,
        "evidence": completion.evidence_summary,
        "completionDate": completion.issued_at.isoformat(),
    }
    signature = hashlib.sha256(
        f"{certificate_id}|{code}|{completion.verification_id}|{facts}".encode()
    ).hexdigest()
    item = CareerCertificate(
        organization_id=auth.organization_id,
        user_id=auth.user.id,
        completion_record_id=completion.id,
        certificate_id=certificate_id,
        verification_code=code,
        course_name=completion.scope_id,
        course_version=completion.criteria_version,
        organization_name=organization.name if organization else "CyberMentor",
        issued_at=now,
        signature_hash=signature,
        facts=facts,
    )
    db.add(item)
    db.commit()
    return certificate_payload(item)


def certificate_payload(item: CareerCertificate) -> dict[str, Any]:
    return {
        "id": str(item.id),
        "certificate_id": item.certificate_id,
        "verification_code": item.verification_code,
        "course": item.course_name,
        "course_version": item.course_version,
        "organization": item.organization_name,
        "issued_at": item.issued_at,
        "status": item.status,
        "expires_at": item.expires_at,
        "qr_verification_url": f"/api/v1/career-public/certificates/{item.verification_code}",
        "signature": item.signature_hash,
        "facts": item.facts,
    }


@router.get("/certificates")
def certificates(
    auth: AuthContext = Depends(require_auth), db: DatabaseSession = Depends(get_db)
) -> list[dict[str, Any]]:
    return [
        certificate_payload(x)
        for x in db.scalars(
            select(CareerCertificate)
            .where(
                CareerCertificate.organization_id == auth.organization_id,
                CareerCertificate.user_id == auth.user.id,
            )
            .order_by(CareerCertificate.issued_at.desc())
        )
    ]


@router.post("/certificates/{certificate_id}/revoke")
def revoke_certificate(
    certificate_id: uuid.UUID,
    payload: CertificateRevocationRequest,
    request: Request,
    auth: AuthContext = Depends(require_csrf),
    db: DatabaseSession = Depends(get_db),
) -> dict[str, Any]:
    assert_permission(db, auth, "reports.export")
    certificate = db.scalar(
        select(CareerCertificate).where(
            CareerCertificate.id == certificate_id,
            CareerCertificate.organization_id == auth.organization_id,
        )
    )
    if certificate is None:
        raise AppError(404, "certificate_not_found", "Certificate was not found.")
    if certificate.status != "valid":
        raise AppError(409, "certificate_not_active", "Only a valid certificate can be revoked.")
    certificate.status = "revoked"
    certificate.revoked_at = datetime.now(UTC)
    certificate.revocation_reason = payload.reason.strip()
    audit(
        db,
        "career.certificate_revoked",
        "success",
        auth.user.id,
        auth.organization_id,
        getattr(request.state, "request_id", None),
        "career_certificate",
        str(certificate.id),
        certificate.revocation_reason,
    )
    db.commit()
    return certificate_payload(certificate)


@router.get("/transcript")
def transcript(
    auth: AuthContext = Depends(require_auth), db: DatabaseSession = Depends(get_db)
) -> dict[str, Any]:
    enrollments = list(
        db.scalars(
            select(Enrollment).where(
                Enrollment.organization_id == auth.organization_id,
                Enrollment.user_id == auth.user.id,
            )
        ).all()
    )
    evidence = verified_evidence(db, auth)
    skills = passport(db, auth.organization_id, auth.user.id)
    return {
        "generated_at": datetime.now(UTC),
        "status": "verified activity transcript",
        "courses": [
            {
                "course": x.course_publication_id,
                "status": x.status,
                "enrolled_at": x.enrolled_at,
                "completed_at": x.completed_at,
            }
            for x in enrollments
        ],
        "skills": skills,
        "evidence": evidence,
        "certificates": [
            certificate_payload(x)
            for x in db.scalars(
                select(CareerCertificate).where(
                    CareerCertificate.organization_id == auth.organization_id,
                    CareerCertificate.user_id == auth.user.id,
                )
            )
        ],
        "limitations": (
            "Hours are not claimed because no trusted duration total is available for every course."
        ),
    }


@router.get("/transcript.pdf")
def transcript_pdf(
    auth: AuthContext = Depends(require_auth), db: DatabaseSession = Depends(get_db)
) -> Response:
    data = transcript(auth, db)
    lines = [f"{x['course']} — {x['status']}" for x in data["courses"]] + [
        f"Verified skill: {x['skill_name']} ({x['evidence_count']} evidence records)"
        for x in data["skills"]
    ]
    return Response(
        pdf("CyberMentor verified activity transcript", lines),
        media_type="application/pdf",
        headers={"Content-Disposition": "attachment; filename=cybermentor-transcript.pdf"},
    )


@router.get("/resume")
def resume(
    auth: AuthContext = Depends(require_auth), db: DatabaseSession = Depends(get_db)
) -> dict[str, Any]:
    profile = profile_for(db, auth)
    assert profile is not None
    evidence = verified_evidence(db, auth)
    return {
        "headline": profile.headline,
        "professional_summary": profile.biography,
        "verified_skills": [
            {
                "name": x["skill_name"],
                "mastery": x["mastery_level"],
                "evidence_count": x["evidence_count"],
            }
            for x in passport(db, auth.organization_id, auth.user.id)
            if x["evidence_count"]
        ],
        "verified_projects": [
            x for x in evidence["artifacts"] if x["type"] == "human_reviewed_project"
        ],
        "verified_completions": evidence["completion_records"],
        "certificates": [
            certificate_payload(x)
            for x in db.scalars(
                select(CareerCertificate).where(
                    CareerCertificate.organization_id == auth.organization_id,
                    CareerCertificate.user_id == auth.user.id,
                )
            )
        ],
        "notice": (
            "This resume contains only profile details supplied by the learner and verified "
            "CyberMentor evidence. It does not infer employment experience."
        ),
    }


@router.get("/organization-report")
def organization_report(
    auth: AuthContext = Depends(require_auth), db: DatabaseSession = Depends(get_db)
) -> dict[str, Any]:
    assert_permission(db, auth, "reports.view")
    records = db.execute(
        select(CompletionRecord.user_id, func.count(CompletionRecord.id))
        .where(
            CompletionRecord.organization_id == auth.organization_id,
            CompletionRecord.revoked_at.is_(None),
        )
        .group_by(CompletionRecord.user_id)
    ).all()
    return {
        "organization_id": str(auth.organization_id),
        "learners_with_verified_completions": len(records),
        "completion_records": sum(int(x[1]) for x in records),
        "mission_completions": int(
            db.scalar(
                select(func.count(MissionResult.id)).where(
                    MissionResult.organization_id == auth.organization_id,
                    MissionResult.passed.is_(True),
                )
            )
            or 0
        ),
        "project_reviews": int(
            db.scalar(
                select(func.count(ProjectReview.id)).where(
                    ProjectReview.organization_id == auth.organization_id,
                    ProjectReview.passed.is_(True),
                )
            )
            or 0
        ),
        "notice": (
            "Only tenant-scoped verified activity is included; private learner analytics "
            "are excluded."
        ),
    }


@public_router.get("/certificates/{code}")
def verify_certificate(code: str, db: DatabaseSession = Depends(get_db)) -> dict[str, Any]:
    item = db.scalar(select(CareerCertificate).where(CareerCertificate.verification_code == code))
    if item is None:
        raise AppError(404, "certificate_not_found", "Certificate verification code was not found.")
    return {
        key: value
        for key, value in certificate_payload(item).items()
        if key not in {"verification_code", "signature"}
    }


@public_router.get("/portfolios/{slug}")
def public_portfolio(slug: str, db: DatabaseSession = Depends(get_db)) -> dict[str, Any]:
    profile = db.scalar(
        select(ProfessionalProfile).where(
            ProfessionalProfile.public_slug == slug,
            ProfessionalProfile.portfolio_visibility == "public",
        )
    )
    if profile is None:
        raise AppError(404, "portfolio_not_found", "This public portfolio is unavailable.")
    return {
        "profile": profile_payload(profile, public=True),
        "skill_passport": passport(db, profile.organization_id, profile.user_id),
    }
