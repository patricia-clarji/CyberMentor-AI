from datetime import UTC, datetime

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models import Organization, User
from app.models.portfolio import CompletionRecord
from tests.test_cms import h, login, setup_cms_users


def completion_for(db: Session, organization: Organization, user: User) -> CompletionRecord:
    record = CompletionRecord(
        organization_id=organization.id,
        user_id=user.id,
        verification_id="career-test-completion",
        criteria_version="2026.1",
        scope_type="course",
        scope_id="junior-soc-pathway",
        skill_summary=[{"skill": "evidence-preservation", "result": "verified"}],
        evidence_summary=[{"type": "mission", "id": "harbor-light"}],
        issued_at=datetime.now(UTC),
        revoked_at=None,
        revocation_reason=None,
    )
    db.add(record)
    db.commit()
    return record


def test_certificate_requires_trusted_completion_and_is_publicly_verifiable(
    client: TestClient, db: Session
) -> None:
    setup_cms_users(db)
    csrf = login(client, "learner@example.com")
    assert (
        client.post(
            "/api/v1/career/certificates/from-completion/00000000-0000-0000-0000-000000000001",
            headers=h(csrf),
        ).status_code
        == 404
    )

    organization = db.query(Organization).one()
    learner = db.query(User).filter(User.email == "learner@example.com").one()
    record = completion_for(db, organization, learner)
    response = client.post(
        f"/api/v1/career/certificates/from-completion/{record.id}", headers=h(csrf)
    )
    assert response.status_code == 201
    certificate = response.json()
    assert certificate["status"] == "valid"
    assert certificate["facts"]["completionCriteria"] == "2026.1"
    verified = client.get(f"/api/v1/career-public/certificates/{certificate['verification_code']}")
    assert verified.status_code == 200
    assert "verification_code" not in verified.json()


def test_profile_privacy_passport_transcript_and_resume_are_evidence_bound(
    client: TestClient, db: Session
) -> None:
    setup_cms_users(db)
    csrf = login(client, "learner@example.com")
    profile = client.put(
        "/api/v1/career/profile",
        headers=h(csrf),
        json={
            "headline": "Junior SOC analyst",
            "biography": "Evidence-first learner.",
            "domains": ["defensive operations"],
            "technical_interests": [],
            "languages": ["English"],
            "links": {"github": "https://github.com/example"},
            "privacy": {"headline": "public"},
            "portfolio_visibility": "public",
        },
    )
    assert profile.status_code == 200
    slug = profile.json()["public_slug"]
    public = client.get(f"/api/v1/career-public/portfolios/{slug}")
    assert public.status_code == 200
    assert public.json()["profile"]["headline"] == "Junior SOC analyst"
    assert "biography" not in public.json()["profile"]
    assert client.get("/api/v1/career/passport").json()["skills"] == []
    assert client.get("/api/v1/career/resume").json()["verified_skills"] == []
    pdf = client.get("/api/v1/career/transcript.pdf")
    assert pdf.status_code == 200
    assert pdf.headers["content-type"].startswith("application/pdf")
    assert pdf.content.startswith(b"%PDF")


def test_role_mapping_reflections_and_tenant_report_permission(
    client: TestClient, db: Session
) -> None:
    setup_cms_users(db)
    csrf = login(client, "learner@example.com")
    roles = client.get("/api/v1/career/roles")
    assert {item["name"] for item in roles.json()} >= {"SOC Analyst", "GRC Analyst"}
    reflection = client.post(
        "/api/v1/career/reflections",
        headers=h(csrf),
        json={
            "source_type": "mission",
            "source_id": "harbor-light",
            "learned": "I learned to distinguish evidence from conclusions.",
            "difficult": "Prioritizing evidence.",
            "improvement": "I will use a structured timeline.",
            "confidence": 4,
            "professional_application": "I can apply this approach in an incident triage workflow.",
        },
    )
    assert reflection.status_code == 201
    assert client.get("/api/v1/career/reflections").json()[0]["revision"] == 1
    assert client.get("/api/v1/career/organization-report").status_code == 403
    login(client, "organization-admin@example.com")
    assert client.get("/api/v1/career/organization-report").status_code == 200
