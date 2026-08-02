import uuid
from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.seed import seed_roles
from app.identity.service import register_user, verify_email
from app.models import OrganizationInvitation, User
from app.models.operations import SharedProfile, SharedProfileAccess
from app.models.portfolio import Portfolio, PortfolioArtifact
from app.security.tokens import token_hash

PASSWORD = "Strong-Password-42!"  # noqa: S105


def register(db: Session, email: str, name: str) -> None:
    _, verification = register_user(db, email, PASSWORD, name, get_settings(), "operations-test")
    verify_email(db, verification, "operations-test")


def login(client: TestClient, email: str) -> str:
    client.cookies.clear()
    response = client.post("/api/v1/auth/login", json={"email": email, "password": PASSWORD})
    assert response.status_code == 200
    csrf = response.cookies.get("cm_csrf")
    assert csrf
    return csrf


def h(csrf: str) -> dict[str, str]:
    return {"X-CSRF-Token": csrf}


def create_org(client: TestClient, csrf: str, slug: str, kind: str) -> str:
    response = client.post(
        "/api/v1/organizations",
        headers=h(csrf),
        json={"name": slug.title(), "slug": slug, "kind": kind},
    )
    assert response.status_code == 201
    organization_id = response.json()["id"]
    assert (
        client.post(
            f"/api/v1/organizations/{organization_id}/activate", headers=h(csrf)
        ).status_code
        == 200
    )
    return organization_id


def invite(client: TestClient, csrf: str, email: str, role: str) -> str:
    response = client.post(
        "/api/v1/organizations/invitations",
        headers=h(csrf),
        json={"email": email, "role": role},
    )
    assert response.status_code == 201
    return response.json()["acceptance_token"]


def accept(client: TestClient, email: str, token: str) -> tuple[str, str]:
    csrf = login(client, email)
    response = client.post(
        "/api/v1/organizations/invitations/accept",
        headers=h(csrf),
        json={"token": token},
    )
    assert response.status_code == 200
    organization_id = response.json()["organization_id"]
    assert (
        client.post(
            f"/api/v1/organizations/{organization_id}/activate", headers=h(csrf)
        ).status_code
        == 200
    )
    return csrf, organization_id


def setup_users(db: Session, *users: tuple[str, str]) -> None:
    seed_roles(db)
    db.commit()
    for email, name in users:
        register(db, email, name)


def test_invitation_lifecycle_role_escalation_and_inactive_membership(
    client: TestClient,
    db: Session,
) -> None:
    setup_users(
        db,
        ("owner@university.example", "Owner"),
        ("instructor@university.example", "Instructor"),
        ("learner@university.example", "Learner"),
    )
    owner_csrf = login(client, "owner@university.example")
    organization_id = create_org(client, owner_csrf, "northbridge-university", "university")
    instructor_token = invite(client, owner_csrf, "instructor@university.example", "instructor")
    learner_token = invite(client, owner_csrf, "learner@university.example", "learner")
    record = db.scalar(
        select(OrganizationInvitation).where(
            OrganizationInvitation.email == "instructor@university.example"
        )
    )
    assert record is not None
    assert record.token_hash == token_hash(instructor_token)
    assert record.token_hash != instructor_token

    learner_csrf = login(client, "learner@university.example")
    tamper = client.post(
        "/api/v1/organizations/invitations/accept",
        headers=h(learner_csrf),
        json={"token": instructor_token},
    )
    assert tamper.status_code == 400
    accept(client, "instructor@university.example", instructor_token)
    learner_csrf, _ = accept(client, "learner@university.example", learner_token)
    assert (
        client.patch(
            "/api/v1/organizations/members/00000000-0000-0000-0000-000000000001",
            headers=h(learner_csrf),
            json={"role": "organization_owner"},
        ).status_code
        == 403
    )
    assert client.get("/api/v1/organizations/audit").status_code == 403

    owner_csrf = login(client, "owner@university.example")
    client.post(f"/api/v1/organizations/{organization_id}/activate", headers=h(owner_csrf))
    members = client.get("/api/v1/organizations/members").json()
    learner = next(item for item in members if item["email"] == "learner@university.example")
    assert (
        client.patch(
            f"/api/v1/organizations/members/{learner['membership_id']}",
            headers=h(owner_csrf),
            json={"active": False},
        ).status_code
        == 200
    )
    learner_csrf = login(client, "learner@university.example")
    assert (
        client.post(
            f"/api/v1/organizations/{organization_id}/activate", headers=h(learner_csrf)
        ).status_code
        == 404
    )


def test_cohort_assignment_revision_review_analytics_and_reports(
    client: TestClient,
    db: Session,
) -> None:
    setup_users(
        db,
        ("owner@training.example", "Owner"),
        ("instructor@training.example", "Instructor"),
        ("learner@training.example", "Learner"),
        ("manager@other-company.example", "Other Manager"),
    )
    owner_csrf = login(client, "owner@training.example")
    organization_id = create_org(client, owner_csrf, "harbor-training", "training_provider")
    instructor_token = invite(client, owner_csrf, "instructor@training.example", "instructor")
    learner_token = invite(client, owner_csrf, "learner@training.example", "learner")
    accept(client, "instructor@training.example", instructor_token)
    accept(client, "learner@training.example", learner_token)

    owner_csrf = login(client, "owner@training.example")
    client.post(f"/api/v1/organizations/{organization_id}/activate", headers=h(owner_csrf))
    members = client.get("/api/v1/organizations/members").json()
    learner_id = next(
        item["user_id"] for item in members if item["email"] == "learner@training.example"
    )
    instructor_membership = next(
        item["membership_id"] for item in members if item["email"] == "instructor@training.example"
    )
    programme = client.post(
        "/api/v1/operations/programmes",
        headers=h(owner_csrf),
        json={
            "stable_key": "soc-fall",
            "name": "SOC Fall Programme",
            "description": "Internal programme",
            "required_pathways": ["junior-soc-analyst"],
        },
    )
    assert programme.status_code == 201
    cohort = client.post(
        "/api/v1/operations/cohorts",
        headers=h(owner_csrf),
        json={
            "stable_key": "soc-fall-a",
            "name": "SOC Fall A",
            "description": "Evidence-based SOC cohort",
            "cohort_type": "bootcamp",
            "start_date": "2026-09-01",
            "programme_id": programme.json()["id"],
        },
    )
    assert cohort.status_code == 201
    cohort_id = cohort.json()["id"]
    assert (
        client.post(
            f"/api/v1/operations/cohorts/{cohort_id}/learners",
            headers=h(owner_csrf),
            json={"user_ids": [learner_id]},
        ).status_code
        == 200
    )
    assert (
        client.post(
            f"/api/v1/operations/cohorts/{cohort_id}/staff",
            headers=h(owner_csrf),
            json={"membership_id": instructor_membership, "role": "instructor"},
        ).status_code
        == 200
    )
    assert (
        client.post(
            f"/api/v1/operations/cohorts/{cohort_id}/curriculum",
            headers=h(owner_csrf),
            json={
                "content_type": "pathway",
                "content_id": "junior-soc-analyst",
                "content_version": "1.0.0",
            },
        ).status_code
        == 201
    )
    assignment = client.post(
        "/api/v1/operations/assignments",
        headers=h(owner_csrf),
        json={
            "cohort_id": cohort_id,
            "title": "SOC escalation report",
            "instructions": "Submit evidence and a defensible escalation.",
            "assignment_type": "project",
            "content_id": "junior-soc-incident-escalation-project",
            "content_version": "1.0.0",
            "grading_method": "rubric",
            "review_required": True,
        },
    )
    assert assignment.status_code == 201
    assignment_id = assignment.json()["id"]
    assert (
        client.post(
            f"/api/v1/operations/assignments/{assignment_id}/publish",
            headers=h(owner_csrf),
        ).status_code
        == 200
    )

    learner_csrf = login(client, "learner@training.example")
    client.post(f"/api/v1/organizations/{organization_id}/activate", headers=h(learner_csrf))
    assert [item["id"] for item in client.get("/api/v1/operations/assignments").json()] == [
        assignment_id
    ]
    first = client.post(
        f"/api/v1/operations/assignments/{assignment_id}/submissions",
        headers=h(learner_csrf),
        json={"body": "Initial evidence-backed response."},
    )
    assert first.status_code == 201
    assert first.json()["revision"] == 1

    instructor_csrf = login(client, "instructor@training.example")
    client.post(f"/api/v1/organizations/{organization_id}/activate", headers=h(instructor_csrf))
    review_id = client.get("/api/v1/operations/reviews").json()[0]["id"]
    assert (
        client.post(
            f"/api/v1/operations/reviews/{review_id}/decision",
            headers=h(instructor_csrf),
            json={
                "decision": "revision_requested",
                "feedback": "Separate observation from inference.",
            },
        ).status_code
        == 200
    )

    learner_csrf = login(client, "learner@training.example")
    client.post(f"/api/v1/organizations/{organization_id}/activate", headers=h(learner_csrf))
    second = client.post(
        f"/api/v1/operations/assignments/{assignment_id}/submissions",
        headers=h(learner_csrf),
        json={"body": "Revised response separating observation and inference."},
    )
    assert second.status_code == 201
    assert second.json()["revision"] == 2

    instructor_csrf = login(client, "instructor@training.example")
    client.post(f"/api/v1/organizations/{organization_id}/activate", headers=h(instructor_csrf))
    queue = client.get("/api/v1/operations/reviews").json()
    resubmitted = next(item for item in queue if item["state"] == "resubmitted")
    assert (
        client.post(
            f"/api/v1/operations/reviews/{resubmitted['id']}/decision",
            headers=h(instructor_csrf),
            json={"decision": "approved", "feedback": "Meets the published criteria."},
        ).status_code
        == 200
    )
    metrics = client.get("/api/v1/operations/dashboard?portal=instructor").json()["metrics"]
    assert metrics["assignment_completion_rate"] == 1.0
    assert client.get("/api/v1/operations/reports/cohort-progress.csv").status_code == 403

    owner_csrf = login(client, "owner@training.example")
    client.post(f"/api/v1/organizations/{organization_id}/activate", headers=h(owner_csrf))
    report = client.get("/api/v1/operations/reports/cohort-progress.csv")
    assert report.status_code == 200
    assert "limitations" in report.text
    assert "SOC escalation report" in report.text
    assert (
        client.post(
            f"/api/v1/operations/cohorts/{cohort_id}/archive", headers=h(owner_csrf)
        ).status_code
        == 200
    )
    assert client.get(f"/api/v1/operations/cohorts/{cohort_id}").status_code == 200
    manager_csrf = login(client, "manager@other-company.example")
    create_org(client, manager_csrf, "other-company", "company")
    assert client.get(f"/api/v1/operations/cohorts/{cohort_id}").status_code == 404


def test_shares_are_learner_controlled_hashed_expiring_and_tenant_isolated(
    client: TestClient,
    db: Session,
) -> None:
    setup_users(
        db,
        ("owner@company.example", "Owner"),
        ("employee@company.example", "Employee"),
        ("outsider@example.com", "Outsider"),
    )
    owner_csrf = login(client, "owner@company.example")
    organization_id = create_org(client, owner_csrf, "acme-security", "company")
    invite_token = invite(client, owner_csrf, "employee@company.example", "learner")
    employee_csrf, _ = accept(client, "employee@company.example", invite_token)
    employee = db.scalar(select(User).where(User.email == "employee@company.example"))
    assert employee is not None
    portfolio = Portfolio(
        organization_id=uuid.UUID(organization_id),
        user_id=employee.id,
        visibility="private",
    )
    db.add(portfolio)
    db.flush()
    artifact = PortfolioArtifact(
        organization_id=uuid.UUID(organization_id),
        user_id=employee.id,
        portfolio_id=portfolio.id,
        artifact_type="human_reviewed_project",
        source_id="project-1",
        source_version="1.0.0",
        title="Incident escalation",
        verification_state="verified",
        visibility="private",
    )
    db.add(artifact)
    db.commit()
    share = client.post(
        "/api/v1/operations/shares",
        headers=h(employee_csrf),
        json={
            "display_name": "SOC Candidate",
            "include_email": False,
            "expires_in_days": 30,
            "artifact_ids": [str(artifact.id)],
        },
    )
    assert share.status_code == 201
    raw_token = share.json()["share_token"]
    share_id = share.json()["id"]
    stored = db.get(SharedProfile, uuid.UUID(share_id))
    assert stored is not None
    assert stored.token_hash == token_hash(raw_token)
    assert stored.token_hash != raw_token
    public = client.get(f"/api/v1/verify/{raw_token}")
    assert public.status_code == 200
    assert public.json()["email"] is None
    assert public.json()["artifacts"][0]["title"] == "Incident escalation"
    assert "memberships" not in public.text
    assert "Sentinel" not in public.text
    assert db.scalar(select(SharedProfileAccess)) is not None

    outsider_csrf = login(client, "outsider@example.com")
    create_org(client, outsider_csrf, "outsider-company", "company")
    assert client.get(f"/api/v1/operations/shares/{share_id}/preview").status_code == 404

    employee_csrf = login(client, "employee@company.example")
    client.post(f"/api/v1/organizations/{organization_id}/activate", headers=h(employee_csrf))
    assert (
        client.post(
            f"/api/v1/operations/shares/{share_id}/revoke", headers=h(employee_csrf)
        ).status_code
        == 200
    )
    assert client.get(f"/api/v1/verify/{raw_token}").status_code == 404
    stored.revoked_at = None
    stored.status = "active"
    stored.expires_at = datetime.now(UTC) - timedelta(seconds=1)
    db.commit()
    assert client.get(f"/api/v1/verify/{raw_token}").status_code == 404
