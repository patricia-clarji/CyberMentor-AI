from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.identity.service import register_user, verify_email

PASSWORD = "Strong-Password-42!"  # noqa: S105 - isolated test credential


def create_verified(db: Session, email: str, name: str) -> None:
    _, token = register_user(db, email, PASSWORD, name, get_settings(), "learning-test")
    verify_email(db, token, "learning-test")


def sign_in(client: TestClient, email: str) -> str:
    response = client.post("/api/v1/auth/login", json={"email": email, "password": PASSWORD})
    assert response.status_code == 200
    csrf = response.cookies.get("cm_csrf")
    assert csrf
    return csrf


def test_onboarding_and_learning_state_are_server_owned(client: TestClient, db: Session) -> None:
    create_verified(db, "maya@example.com", "Maya")
    csrf = sign_in(client, "maya@example.com")
    headers = {"X-CSRF-Token": csrf}
    onboarding = client.put(
        "/api/v1/learning/onboarding",
        headers=headers,
        json={
            "experience_level": "beginner",
            "career_objective": "Junior SOC Analyst",
            "weekly_minutes": 360,
            "networking_confidence": 4,
            "linux_confidence": 2,
            "investigation_confidence": 2,
            "learning_preferences": ["worked-examples", "guided-practice"],
            "accessibility_needs": None,
        },
    )
    assert onboarding.status_code == 200
    enrollment = client.post(
        "/api/v1/learning/enrollments",
        headers=headers,
        json={"course_publication_id": "course-4"},
    )
    assert enrollment.status_code == 201
    progress = client.put(
        "/api/v1/learning/lessons/course-4-m1-l1/progress",
        headers=headers,
        json={
            "lesson_version": "1.0.0",
            "status": "completed",
            "percent_complete": 100,
            "last_position": "summary",
        },
    )
    assert progress.status_code == 200
    note = client.post(
        "/api/v1/learning/notes",
        headers=headers,
        json={
            "lesson_publication_id": "course-4-m1-l1",
            "body": "Correlate the alert with authentication and endpoint evidence.",
        },
    )
    assert note.status_code == 201
    bookmark = client.post(
        "/api/v1/learning/bookmarks",
        headers=headers,
        json={"resource_type": "lesson", "resource_id": "course-4-m1-l1"},
    )
    assert bookmark.status_code == 201
    dashboard = client.get("/api/v1/learning/dashboard")
    assert dashboard.status_code == 200
    body = dashboard.json()
    assert body["primary_goal"] == "Junior SOC Analyst"
    assert body["profile"]["linux_confidence"] == 2
    assert body["enrollments"][0]["course_publication_id"] == "course-4"
    assert body["lesson_progress"][0]["status"] == "completed"
    assert body["notes"][0]["body"].startswith("Correlate")
    assert body["bookmarks"][0]["resource_id"] == "course-4-m1-l1"


def test_note_idor_is_denied_as_not_found(client: TestClient, db: Session) -> None:
    create_verified(db, "first@example.com", "First")
    create_verified(db, "second@example.com", "Second")
    first_csrf = sign_in(client, "first@example.com")
    note = client.post(
        "/api/v1/learning/notes",
        headers={"X-CSRF-Token": first_csrf},
        json={
            "lesson_publication_id": "course-4-m1-l1",
            "body": "Private tenant note",
        },
    )
    note_id = note.json()["id"]
    client.cookies.clear()
    second_csrf = sign_in(client, "second@example.com")
    attempt = client.delete(
        f"/api/v1/learning/notes/{note_id}",
        headers={"X-CSRF-Token": second_csrf},
    )
    assert attempt.status_code == 404


def test_progress_optimistic_concurrency_rejects_stale_update(
    client: TestClient, db: Session
) -> None:
    create_verified(db, "concurrency@example.com", "Concurrency")
    csrf = sign_in(client, "concurrency@example.com")
    headers = {"X-CSRF-Token": csrf}
    first = client.put(
        "/api/v1/learning/lessons/course-4-m1-l1/progress",
        headers=headers,
        json={
            "lesson_version": "1.0.0",
            "status": "in_progress",
            "percent_complete": 50,
        },
    )
    assert first.status_code == 200
    second = client.put(
        "/api/v1/learning/lessons/course-4-m1-l1/progress",
        headers=headers,
        json={
            "lesson_version": "1.0.0",
            "status": "in_progress",
            "percent_complete": 70,
            "expected_version": first.json()["version"],
        },
    )
    assert second.status_code == 200
    stale = client.put(
        "/api/v1/learning/lessons/course-4-m1-l1/progress",
        headers=headers,
        json={
            "lesson_version": "1.0.0",
            "status": "completed",
            "percent_complete": 100,
            "expected_version": first.json()["version"],
        },
    )
    assert stale.status_code == 409
    assert stale.json()["error"]["code"] == "version_conflict"
