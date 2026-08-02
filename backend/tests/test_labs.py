from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.seed import seed_roles, seed_skills
from app.identity.service import register_user, verify_email
from app.models.lab import LabSession, LabSubmission
from app.models.portfolio import CompletionRecord, PortfolioArtifact

PASSWORD = "Strong-Password-42!"  # noqa: S105 - isolated test credential


def prepare(db: Session, email: str) -> None:
    seed_roles(db)
    seed_skills(db)
    db.commit()
    _, token = register_user(db, email, PASSWORD, "Lab Learner", get_settings(), "lab-test")
    verify_email(db, token, "lab-test")


def sign_in(client: TestClient, email: str) -> dict[str, str]:
    response = client.post("/api/v1/auth/login", json={"email": email, "password": PASSWORD})
    assert response.status_code == 200
    csrf = response.cookies.get("cm_csrf")
    assert csrf
    return {"X-CSRF-Token": csrf}


def strong_submission(key: str = "lab-submit-0001") -> dict[str, str]:
    return {
        "indicator": "203.0.113.42",
        "classification": "SSH password spraying",
        "recommendation": (
            "Correlate the source with identity telemetry, monitor continued attempts, "
            "and request an authorized block if the activity continues."
        ),
        "report": (
            "The synthetic auth log records three failed SSH password attempts from "
            "203.0.113.42, including an invalid admin user and Salma. This supports "
            "suspicious password spraying, but it does not establish compromise. "
            "Uncertainty remains about other targets. The next step is identity and "
            "firewall correlation followed by a monitored, authorized block."
        ),
        "reflection": (
            "Identity and firewall records would improve confidence and help bound scope."
        ),
        "idempotency_key": key,
    }


def test_full_lab_flow_grades_server_side_updates_portfolio_and_replay(
    client: TestClient, db: Session
) -> None:
    prepare(db, "labs@example.com")
    headers = sign_in(client, "labs@example.com")
    catalog = client.get("/api/v1/labs")
    assert catalog.status_code == 200
    assert len(catalog.json()["labTypes"]) == 7
    assert "virtualEnvironment" not in str(catalog.json())
    start = client.post(
        "/api/v1/labs/soc-lab-linux-auth-triage/start",
        headers=headers,
    )
    assert start.status_code == 201
    current = start.json()["session"]
    session_id = current["sessionId"]
    wrong = client.post(
        f"/api/v1/labs/sessions/{session_id}/commands",
        headers=headers,
        json={"command": "whoami"},
    )
    assert wrong.status_code == 200
    assert wrong.json()["exitCode"] == 127
    location = client.post(
        f"/api/v1/labs/sessions/{session_id}/commands",
        headers=headers,
        json={"command": "pwd"},
    )
    assert location.json()["exitCode"] == 0
    correct = client.post(
        f"/api/v1/labs/sessions/{session_id}/commands",
        headers=headers,
        json={"command": "grep 'Failed password' /var/log/auth.log"},
    )
    assert correct.status_code == 200
    assert "203.0.113.42" in correct.json()["output"]
    hint = client.post(f"/api/v1/labs/sessions/{session_id}/hints", headers=headers)
    assert hint.status_code == 200
    assert hint.json()["hint"]["level"] == 1
    version = hint.json()["session"]["version"]
    notes = client.patch(
        f"/api/v1/labs/sessions/{session_id}/notes",
        headers=headers,
        json={"notes": "Repeated source; conclusion remains bounded.", "expected_version": version},
    )
    assert notes.status_code == 200
    submission = client.post(
        f"/api/v1/labs/sessions/{session_id}/submit",
        headers=headers,
        json=strong_submission(),
    )
    assert submission.status_code == 200
    result = submission.json()
    assert result["passed"] is True
    assert result["overallBand"] == "demonstrated"
    assert set(result["components"]) == {
        "correctness",
        "efficiency",
        "evidenceQuality",
        "independence",
        "decisionQuality",
        "reportQuality",
    }
    assert result["portfolioArtifactId"]
    assert result["completionVerificationId"]
    assert db.query(PortfolioArtifact).count() == 1
    assert db.query(CompletionRecord).filter_by(scope_type="practical_lab").count() == 1
    replay = client.get(f"/api/v1/labs/sessions/{session_id}/replay")
    assert replay.status_code == 200
    replay_body = replay.json()
    assert replay_body["mistakes"]
    assert replay_body["corrections"]
    assert replay_body["hints"]
    assert replay_body["expertSolution"]
    assert client.get("/api/v1/labs/artifacts").json()[0]["content"]["synthetic"] is True


def test_partial_success_can_recover_and_submission_is_idempotent(
    client: TestClient, db: Session
) -> None:
    prepare(db, "retry@example.com")
    headers = sign_in(client, "retry@example.com")
    session_id = client.post(
        "/api/v1/labs/soc-lab-linux-auth-triage/start", headers=headers
    ).json()["session"]["sessionId"]
    poor = strong_submission("lab-submit-poor")
    poor["indicator"] = "unknown"
    poor["report"] = (
        "This report is deliberately incomplete and needs more direct evidence before "
        "the analyst can reach a supported decision or recommend the next action."
    )
    first = client.post(
        f"/api/v1/labs/sessions/{session_id}/submit",
        headers=headers,
        json=poor,
    )
    assert first.status_code == 200
    assert first.json()["passed"] is False
    assert first.json()["canRetry"] is True
    client.post(
        f"/api/v1/labs/sessions/{session_id}/commands",
        headers=headers,
        json={"command": "cat /var/log/auth.log"},
    )
    recovered = client.post(
        f"/api/v1/labs/sessions/{session_id}/submit",
        headers=headers,
        json=strong_submission("lab-submit-recovered"),
    )
    assert recovered.json()["passed"] is True
    repeated = client.post(
        f"/api/v1/labs/sessions/{session_id}/submit",
        headers=headers,
        json=strong_submission("lab-submit-recovered"),
    )
    assert repeated.status_code == 200
    assert repeated.json()["submissionId"] == recovered.json()["submissionId"]
    assert db.query(LabSubmission).count() == 2


def test_session_resumes_after_new_login_and_cross_tenant_access_is_hidden(
    client: TestClient, db: Session
) -> None:
    prepare(db, "owner@example.com")
    prepare(db, "other@example.com")
    owner_headers = sign_in(client, "owner@example.com")
    started = client.post(
        "/api/v1/labs/soc-lab-web-log-independent/start",
        headers=owner_headers,
    ).json()
    session_id = started["session"]["sessionId"]
    client.cookies.clear()
    owner_headers = sign_in(client, "owner@example.com")
    resumed = client.post(
        "/api/v1/labs/soc-lab-web-log-independent/start",
        headers=owner_headers,
    )
    assert resumed.json()["resumed"] is True
    assert resumed.json()["session"]["sessionId"] == session_id
    assert db.query(LabSession).count() == 1
    client.cookies.clear()
    other_headers = sign_in(client, "other@example.com")
    hidden = client.post(
        f"/api/v1/labs/sessions/{session_id}/commands",
        headers=other_headers,
        json={"command": "pwd"},
    )
    assert hidden.status_code == 404
