import json

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.seed import seed_skills
from app.identity.service import register_user, verify_email
from app.learning.pathway_service import grade_response
from app.learning.soc_pathway import ASSESSMENTS, MODULES, PATHWAY_ID, PATHWAY_VERSION

PASSWORD = "Strong-Password-42!"  # noqa: S105 - isolated test credential


def create_verified(db: Session, email: str, name: str) -> None:
    _, token = register_user(db, email, PASSWORD, name, get_settings(), "soc-pathway-test")
    verify_email(db, token, "soc-pathway-test")


def sign_in(client: TestClient, email: str) -> str:
    response = client.post("/api/v1/auth/login", json={"email": email, "password": PASSWORD})
    assert response.status_code == 200
    csrf = response.cookies.get("cm_csrf")
    assert csrf
    return csrf


def test_soc_pathway_contract_is_ordered_and_complete() -> None:
    assert [module["position"] for module in MODULES] == list(range(1, len(MODULES) + 1))
    assert len({module["id"] for module in MODULES}) == len(MODULES)
    required_areas = {
        "security-foundations",
        "tcp-ip-reasoning",
        "dns",
        "http",
        "linux-navigation",
        "linux-processes",
        "linux-permissions",
        "linux-logs",
        "windows-processes",
        "windows-events",
        "authentication-events",
        "email-analysis",
        "ioc-analysis",
        "siem-query-reasoning",
        "alert-triage",
        "incident-severity",
        "evidence-preservation",
        "escalation-writing",
        "incident-reporting",
    }
    linked = {skill for module in MODULES for skill in module["linked_skills"]}
    assert required_areas <= linked
    for module in MODULES:
        assert module["version"] == PATHWAY_VERSION
        assert module["review_state"] == "internally-checked-pending-external-review"
        assert module["required_lessons"]
        assert module["required_practices"]
        assert module["required_assessment"] in ASSESSMENTS
        assert module["completion_rules"]["assessment_minimum_score"] == 0.7
        for lesson in module["lessons"]:
            assert len(lesson["objectives"]) >= 2
            assert len(lesson["concept"]) > 300
            assert len(lesson["worked_example"]) > 150
            assert lesson["terminology"]
            assert lesson["guided_practice"]
            for source in lesson["references"]:
                assert {
                    "publisher",
                    "title",
                    "url",
                    "retrieved_at",
                    "source_date",
                } <= source.keys()


def test_partial_credit_is_deterministic() -> None:
    private = {"choices": [0, 1]}
    assert grade_response(private, {"choices": [0, 1]}) == 1.0
    assert grade_response(private, {"choices": [0]}) == 0.5
    assert grade_response(private, {"choices": [0, 2]}) == 0.0
    assert grade_response({"order": [1, 2, 0]}, {"order": [1, 0, 2]}) == 1 / 3


def test_pathway_payload_excludes_private_answers_and_flow_persists(
    client: TestClient, db: Session
) -> None:
    seed_skills(db)
    db.commit()
    create_verified(db, "pathway@example.com", "Pathway Learner")
    csrf = sign_in(client, "pathway@example.com")
    headers = {"X-CSRF-Token": csrf}
    pathway = client.get("/api/v1/learning/pathways/junior-soc-analyst")
    assert pathway.status_code == 200
    assert pathway.json()["id"] == PATHWAY_ID
    assert "private_answer" not in json.dumps(pathway.json())
    assert pathway.json()["module_statuses"][0]["unlocked"] is True
    assert pathway.json()["module_statuses"][1]["unlocked"] is False

    enrollment = client.post(
        "/api/v1/learning/enrollments",
        headers=headers,
        json={"course_publication_id": PATHWAY_ID},
    )
    assert enrollment.status_code == 201
    lesson = client.get("/api/v1/learning/pathways/junior-soc-analyst/lessons/soc-01-l1")
    assert lesson.status_code == 200
    assert lesson.json()["progress"] is None
    progress = client.put(
        "/api/v1/learning/lessons/soc-01-l1/progress",
        headers=headers,
        json={
            "lesson_version": PATHWAY_VERSION,
            "status": "completed",
            "percent_complete": 100,
            "last_position": "reflection",
        },
    )
    assert progress.status_code == 200
    note = client.post(
        "/api/v1/learning/notes",
        headers=headers,
        json={
            "lesson_publication_id": "soc-01-l1",
            "body": "Separate the supported authentication observations from the hypothesis.",
        },
    )
    assert note.status_code == 201
    bookmark = client.post(
        "/api/v1/learning/bookmarks",
        headers=headers,
        json={"resource_type": "lesson", "resource_id": "soc-01-l1"},
    )
    assert bookmark.status_code == 201

    practice_payload = {
        "response": {"choice": 1},
        "idempotency_key": "practice-attempt-0001",
        "hints_used": 0,
    }
    practice = client.post(
        "/api/v1/learning/pathways/junior-soc-analyst/activities/soc-01-practice/submit",
        headers=headers,
        json=practice_payload,
    )
    assert practice.status_code == 200
    assert practice.json()["passed"] is True
    duplicate = client.post(
        "/api/v1/learning/pathways/junior-soc-analyst/activities/soc-01-practice/submit",
        headers=headers,
        json=practice_payload,
    )
    assert duplicate.status_code == 200
    assert duplicate.json()["attempt_id"] == practice.json()["attempt_id"]

    assessment = client.get(
        "/api/v1/learning/pathways/junior-soc-analyst/assessments/soc-01-foundations-assessment"
    )
    assert assessment.status_code == 200
    assert "private_answer" not in json.dumps(assessment.json())
    submission = client.post(
        "/api/v1/learning/pathways/junior-soc-analyst/assessments/"
        "soc-01-foundations-assessment/submit",
        headers=headers,
        json={
            "responses": {
                "soc-01-foundations-q1": {"choice": 1},
                "soc-01-foundations-q2": {"choice": 0},
            },
            "idempotency_key": "assessment-attempt-0001",
            "hints_used": 0,
        },
    )
    assert submission.status_code == 200
    assert submission.json()["score"] == 1.0
    assert submission.json()["module_statuses"][0]["completed"] is True
    assert submission.json()["module_statuses"][1]["unlocked"] is True

    dashboard = client.get("/api/v1/learning/dashboard")
    assert dashboard.status_code == 200
    assert dashboard.json()["enrollments"][0]["course_publication_id"] == PATHWAY_ID
    assert dashboard.json()["lesson_progress"][0]["status"] == "completed"
    assert dashboard.json()["notes"][0]["body"].startswith("Separate")
    evidence = client.get("/api/v1/learning/skills/evidence")
    assert evidence.status_code == 200
    assert len(evidence.json()["evidence"]) >= 2
    alert_state = next(
        item for item in dashboard.json()["skills"] if item["skillId"] == "alert-triage"
    )
    assert alert_state["mastery"] < 0.8
    assert alert_state["confidence"] < 0.5


def test_activity_attempts_are_tenant_isolated(client: TestClient, db: Session) -> None:
    seed_skills(db)
    db.commit()
    create_verified(db, "owner@example.com", "Owner")
    create_verified(db, "other@example.com", "Other")
    owner_csrf = sign_in(client, "owner@example.com")
    owner_attempt = client.post(
        "/api/v1/learning/pathways/junior-soc-analyst/activities/soc-01-practice/submit",
        headers={"X-CSRF-Token": owner_csrf},
        json={
            "response": {"choice": 1},
            "idempotency_key": "shared-looking-key-0001",
            "hints_used": 0,
        },
    )
    assert owner_attempt.status_code == 200
    client.cookies.clear()
    other_csrf = sign_in(client, "other@example.com")
    other_attempt = client.post(
        "/api/v1/learning/pathways/junior-soc-analyst/activities/soc-01-practice/submit",
        headers={"X-CSRF-Token": other_csrf},
        json={
            "response": {"choice": 0},
            "idempotency_key": "shared-looking-key-0001",
            "hints_used": 1,
        },
    )
    assert other_attempt.status_code == 200
    assert other_attempt.json()["attempt_id"] != owner_attempt.json()["attempt_id"]
    other_evidence = client.get("/api/v1/learning/skills/evidence")
    assert len(other_evidence.json()["evidence"]) == 1
    assert other_evidence.json()["evidence"][0]["result"] == 0.0
