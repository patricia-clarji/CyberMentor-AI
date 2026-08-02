from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.seed import seed_flagship_project, seed_roles
from app.identity.service import register_user, verify_email
from app.models.identity import (
    MembershipRole,
    OrganizationMembership,
    Role,
)
from app.models.portfolio import RubricCriterion

PASSWORD = "Strong-Password-42!"  # noqa: S105 - isolated test credential


def prepare(db: Session, email: str, name: str):
    seed_roles(db)
    seed_flagship_project(db)
    db.commit()
    user, token = register_user(db, email, PASSWORD, name, get_settings(), "project-test")
    verify_email(db, token, "project-test")
    return user


def sign_in(client: TestClient, email: str) -> str:
    response = client.post("/api/v1/auth/login", json={"email": email, "password": PASSWORD})
    assert response.status_code == 200
    csrf = response.cookies.get("cm_csrf")
    assert csrf
    return csrf


def project_body() -> str:
    return (
        "Problem and scope: The authorized investigation concerns FIN-14 and the "
        "maya.saleh identity during the supplied Harbor Light time window. Business "
        "impact is elevated because the asset supports finance close. Evidence: the "
        "sender path mismatch is a direct observation; the mail-reader to encoded "
        "PowerShell process is a second direct observation; the external sign-in and "
        "MFA denials bound identity risk. The hypothesis is suspected endpoint compromise. "
        "An alternative is an approved administrative script coinciding with a spoofed "
        "message, but process ancestry and timing reduce that likelihood. Uncertainty "
        "remains about payload behavior, persistence, and broader identity scope. Decision: "
        "request authorized isolation of FIN-14 while preserving evidence. Verify isolation "
        "through independent EDR state, then review sessions and revoke only confirmed "
        "exposure. Document source, time, acquisition method, hashes where applicable, "
        "decision owner, residual risk, and monitoring ownership so another analyst can "
        "reproduce the sequence."
    )


def test_project_submission_requires_same_tenant_human_reviewer(
    client: TestClient, db: Session
) -> None:
    learner = prepare(db, "project-learner@example.com", "Project Learner")
    reviewer = prepare(db, "project-reviewer@example.com", "Project Reviewer")
    learner_membership = db.scalar(
        select(OrganizationMembership).where(OrganizationMembership.user_id == learner.id)
    )
    assert learner_membership is not None
    instructor = db.scalar(select(Role).where(Role.key == "instructor"))
    assert instructor is not None
    reviewer_shared_membership = OrganizationMembership(
        organization_id=learner_membership.organization_id,
        user_id=reviewer.id,
        is_active=True,
    )
    db.add(reviewer_shared_membership)
    db.flush()
    db.add(
        MembershipRole(
            membership_id=reviewer_shared_membership.id,
            role_id=instructor.id,
        )
    )
    db.commit()

    learner_csrf = sign_in(client, "project-learner@example.com")
    project = client.get("/api/v1/projects/flagship")
    assert project.status_code == 200
    assert "does not pass automatically" in project.json()["review_notice"]
    submission = client.post(
        "/api/v1/projects/flagship/submissions",
        headers={"X-CSRF-Token": learner_csrf},
        json={
            "body": project_body(),
            "reflection": (
                "The most rewarding part was turning separate evidence into a reproducible "
                "decision. The hardest part was preserving uncertainty while recommending "
                "timely containment. I learned to compare alternatives and will improve by "
                "making verification owners and collection limits even more explicit."
            ),
        },
    )
    assert submission.status_code == 201
    assert submission.json()["status"] == "awaiting_review"
    submission_id = submission.json()["id"]
    criteria = db.scalars(select(RubricCriterion)).all()
    criterion_payload = [
        {
            "key": criterion.stable_key,
            "passed": True,
            "comment": "The submitted report meets this published standard.",
        }
        for criterion in criteria
    ]
    unauthorized = client.post(
        f"/api/v1/projects/submissions/{submission_id}/review",
        headers={"X-CSRF-Token": learner_csrf},
        json={
            "criteria": criterion_payload,
            "feedback": (
                "Learners cannot self-review this project; an authorized reviewer is required."
            ),
        },
    )
    assert unauthorized.status_code == 403

    client.cookies.clear()
    reviewer_csrf = sign_in(client, "project-reviewer@example.com")
    switched = client.post(
        f"/api/v1/organizations/{learner_membership.organization_id}/activate",
        headers={"X-CSRF-Token": reviewer_csrf},
    )
    assert switched.status_code == 200
    review = client.post(
        f"/api/v1/projects/submissions/{submission_id}/review",
        headers={"X-CSRF-Token": reviewer_csrf},
        json={
            "criteria": criterion_payload,
            "feedback": (
                "The report is reproducible, appropriately scoped, and transparent about "
                "uncertainty. Continue strengthening timestamps and evidence provenance."
            ),
        },
    )
    assert review.status_code == 200
    assert review.json()["passed"] is True
    assert review.json()["portfolio_artifact_id"]
    assert review.json()["completion_verification_id"]


def test_project_submission_is_tenant_scoped(client: TestClient, db: Session) -> None:
    prepare(db, "project-first@example.com", "First Project")
    prepare(db, "project-second@example.com", "Second Project")
    first_csrf = sign_in(client, "project-first@example.com")
    submission = client.post(
        "/api/v1/projects/flagship/submissions",
        headers={"X-CSRF-Token": first_csrf},
        json={
            "body": project_body(),
            "reflection": (
                "This reflection explains the learning, the rewarding evidence work, "
                "the challenge of uncertainty, and the next documentation improvement."
            ),
        },
    )
    assert submission.status_code == 201
    client.cookies.clear()
    sign_in(client, "project-second@example.com")
    own = client.get("/api/v1/projects/flagship/submissions")
    assert own.status_code == 200
    assert own.json() == []
