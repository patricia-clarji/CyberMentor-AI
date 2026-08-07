from datetime import UTC, datetime
from uuid import UUID

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.seed import seed_diagnostic, seed_roles, seed_skills
from app.identity.dependencies import AuthContext
from app.identity.service import create_session, register_user, verify_email
from app.learning.diagnostic import rebuild_roadmap
from app.models.assessment import QuestionVersion
from app.models.learning import LearnerSkillState, Recommendation, Skill, SkillEvidence

PASSWORD = "Strong-Password-42!"  # noqa: S105 - isolated test credential


def prepare(db: Session, email: str = "diagnostic@example.com"):
    seed_roles(db)
    seed_skills(db)
    seed_diagnostic(db)
    db.commit()
    user, token = register_user(
        db, email, PASSWORD, "Diagnostic Learner", get_settings(), "diag-test"
    )
    verify_email(db, token, "diag-test")
    return user


def login(client: TestClient, email: str = "diagnostic@example.com") -> str:
    response = client.post("/api/v1/auth/login", json={"email": email, "password": PASSWORD})
    assert response.status_code == 200
    csrf = response.cookies.get("cm_csrf")
    assert csrf
    return csrf


def test_diagnostic_never_projects_private_answers(client: TestClient, db: Session) -> None:
    prepare(db)
    csrf = login(client)
    start = client.post("/api/v1/diagnostic/start", headers={"X-CSRF-Token": csrf})
    assert start.status_code == 201
    serialized = str(start.json()).casefold()
    assert "private_answer" not in serialized
    assert '"answer"' not in serialized
    assert start.json()["question"]["question_type"] in {
        "single_choice",
        "multiple_choice",
        "ordering",
        "command_interpretation",
        "log_interpretation",
        "scenario_decision",
    }


def test_diagnostic_records_low_confidence_ml_skill_signal(
    client: TestClient, db: Session
) -> None:
    user = prepare(db, "ml-diagnostic@example.com")
    csrf = login(client, "ml-diagnostic@example.com")
    start = client.post(
        "/api/v1/diagnostic/start",
        headers={"X-CSRF-Token": csrf},
        json={
            "self_assessment_text": (
                "I understand networking but need practice with Linux permissions and logs."
            )
        },
    )
    assert start.status_code == 201
    evidence = db.scalars(
        select(SkillEvidence).where(
            SkillEvidence.user_id == user.id,
            SkillEvidence.source_type == "ml_self_assessment",
        )
    ).all()
    assert len(evidence) == 1
    skill = db.get(Skill, evidence[0].skill_id)
    assert skill is not None
    assert skill.stable_key == "linux-processes"
    assert 0.0 < evidence[0].score <= 1.0


def test_complete_diagnostic_generates_low_confidence_evidence_and_roadmap(
    client: TestClient, db: Session
) -> None:
    prepare(db)
    csrf = login(client)
    headers = {"X-CSRF-Token": csrf}
    current = client.post("/api/v1/diagnostic/start", headers=headers).json()
    attempt_id = current["attempt_id"]
    completed = False
    while not completed:
        question_id = current["question"]["id"]
        version = db.get(QuestionVersion, UUID(question_id))
        assert version is not None
        response = client.post(
            f"/api/v1/diagnostic/{attempt_id}/responses/{question_id}",
            headers=headers,
            json={"response": version.private_answer},
        )
        assert response.status_code == 200
        payload = response.json()
        assert "private_answer" not in str(payload)
        assert "initial evidence only" in payload["confidence_notice"]
        completed = payload["completed"]
        if not completed:
            current = {"question": payload["next_question"]}
    dashboard = client.get("/api/v1/learning/dashboard")
    assert dashboard.status_code == 200
    body = dashboard.json()
    assert body["skills"]
    assert all(skill["confidence"] <= 0.35 for skill in body["skills"])
    assert body["recommendations"]
    assert any(item["required"] for item in body["recommendations"])


def test_cross_tenant_diagnostic_attempt_is_hidden(client: TestClient, db: Session) -> None:
    prepare(db, "firstdiag@example.com")
    prepare(db, "seconddiag@example.com")
    first_csrf = login(client, "firstdiag@example.com")
    start = client.post(
        "/api/v1/diagnostic/start",
        headers={"X-CSRF-Token": first_csrf},
    ).json()
    client.cookies.clear()
    second_csrf = login(client, "seconddiag@example.com")
    attempt = client.post(
        f"/api/v1/diagnostic/{start['attempt_id']}/responses/{start['question']['id']}",
        headers={"X-CSRF-Token": second_csrf},
        json={"response": {"choice": 0}},
    )
    assert attempt.status_code == 404


def test_strong_networking_weak_linux_profile_uses_bridge_and_advanced_work(
    db: Session,
) -> None:
    user = prepare(db, "profile@example.com")
    _, _, _ = create_session(db, user, get_settings(), None, "test", "profile-test")
    from app.models import OrganizationMembership

    membership = db.scalar(
        select(OrganizationMembership).where(OrganizationMembership.user_id == user.id)
    )
    assert membership is not None
    skills = {skill.stable_key: skill for skill in db.scalars(select(Skill)).all()}
    now = datetime.now(UTC)
    for key, mastery in {
        "tcp-ip-reasoning": 0.85,
        "linux-processes": 0.2,
        "linux-logs": 0.25,
    }.items():
        db.add(
            LearnerSkillState(
                organization_id=membership.organization_id,
                user_id=user.id,
                skill_id=skills[key].id,
                mastery_estimate=mastery,
                confidence=0.8,
                evidence_strength=0.7,
                independence=0.8,
                reasoning_summary="Test evidence profile.",
                last_evaluated_at=now,
                engine_version="test",
                version=1,
            )
        )
    db.commit()
    from app.models import Session as UserSession

    session = db.scalar(select(UserSession).where(UserSession.user_id == user.id))
    assert session is not None
    rebuild_roadmap(
        db,
        AuthContext(user, session, membership.organization_id),
        weekly_minutes=360,
    )
    db.commit()
    recommendations = db.scalars(
        select(Recommendation)
        .where(Recommendation.user_id == user.id)
        .order_by(Recommendation.created_at)
    ).all()
    ids = {item.activity_id for item in recommendations}
    assert "linux-investigation-refresh" in ids
    assert "linux-through-network-evidence" in ids
    assert "advanced-network-correlation" in ids
    bridge = next(
        item for item in recommendations if item.activity_id == "linux-through-network-evidence"
    )
    assert "network reasoning" in bridge.reason
