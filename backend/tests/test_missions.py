from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.seed import seed_flagship_mission, seed_roles, seed_skills
from app.identity.service import register_user, verify_email
from app.learning.flagship_mission import FLAGSHIP_MISSION

PASSWORD = "Strong-Password-42!"  # noqa: S105 - isolated test credential


def prepare(db: Session, email: str) -> None:
    seed_roles(db)
    seed_skills(db)
    seed_flagship_mission(db)
    db.commit()
    _, token = register_user(db, email, PASSWORD, "Mission Learner", get_settings(), "mission-test")
    verify_email(db, token, "mission-test")


def sign_in(client: TestClient, email: str) -> str:
    response = client.post("/api/v1/auth/login", json={"email": email, "password": PASSWORD})
    assert response.status_code == 200
    csrf = response.cookies.get("cm_csrf")
    assert csrf
    return csrf


def test_flagship_mission_records_actions_replay_and_verifiable_completion(
    client: TestClient, db: Session
) -> None:
    prepare(db, "mission@example.com")
    csrf = sign_in(client, "mission@example.com")
    headers = {"X-CSRF-Token": csrf}
    start = client.post("/api/v1/missions/flagship/start", headers=headers)
    assert start.status_code == 201
    current = start.json()
    serialized = str(current).casefold()
    assert "required_action" not in serialized
    assert "hints" not in serialized
    assert "content" not in serialized
    assert "synthetic" in current["safety_notice"].casefold()
    session_id = current["session_id"]

    for definition in FLAGSHIP_MISSION["stages"]:
        assert current["stage"]["key"] == definition["key"]
        resource_id = definition["resources"][0]["id"]
        opened = client.post(
            f"/api/v1/missions/sessions/{session_id}/actions",
            headers=headers,
            json={"action_type": "open_evidence", "resource_id": resource_id},
        )
        assert opened.status_code == 200
        assert opened.json()["outcome"] == "observed"
        assert opened.json()["resource_content"]
        decision = client.post(
            f"/api/v1/missions/sessions/{session_id}/actions",
            headers=headers,
            json={
                "action_type": "decision",
                "decision_id": definition["required_action"],
            },
        )
        assert decision.status_code == 200
        current = decision.json()
    assert current["status"] == "ready_to_submit"

    submission = client.post(
        f"/api/v1/missions/sessions/{session_id}/submit",
        headers=headers,
        json={
            "classification": "suspected_endpoint_compromise",
            "rationale": (
                "The sender-path mismatch, mail-reader to encoded PowerShell process, "
                "external authentication sequence, and critical finance asset form a "
                "corroborated chain. They support suspected endpoint compromise, while "
                "the supplied evidence does not establish organization-wide impact."
            ),
            "uncertainty": (
                "Payload behavior and the full authentication scope remain unconfirmed."
            ),
            "recommendation": "isolate_fin_14_with_approval",
            "next_steps": [
                "Preserve volatile and endpoint evidence under the incident procedure.",
                "Review the affected identity sessions and revoke only confirmed exposure.",
            ],
            "reflection": (
                "The most challenging part was preserving uncertainty while still "
                "recommending timely and proportionate containment."
            ),
        },
    )
    assert submission.status_code == 200
    result = submission.json()
    assert result["passed"] is True
    assert result["portfolio_artifact_id"]
    assert result["completion_verification_id"]
    assert "not an industry certification" in result["scope_notice"]

    replay = client.get(f"/api/v1/missions/sessions/{session_id}/replay")
    assert replay.status_code == 200
    assert len(replay.json()["timeline"]) == 8
    assert replay.json()["missed_evidence"] == []
    verification = client.get(f"/api/v1/missions/verify/{result['completion_verification_id']}")
    assert verification.status_code == 200
    assert verification.json()["scope_type"] == "workplace_mission"
    assert verification.json()["revoked"] is False


def test_mission_mistakes_and_hints_are_observed(client: TestClient, db: Session) -> None:
    prepare(db, "mistake@example.com")
    csrf = sign_in(client, "mistake@example.com")
    headers = {"X-CSRF-Token": csrf}
    current = client.post("/api/v1/missions/flagship/start", headers=headers).json()
    session_id = current["session_id"]
    hint = client.post(f"/api/v1/missions/sessions/{session_id}/hint", headers=headers)
    assert hint.status_code == 200
    assert hint.json()["level"] == 1
    mistake = client.post(
        f"/api/v1/missions/sessions/{session_id}/actions",
        headers=headers,
        json={"action_type": "decision", "decision_id": "declare_breach"},
    )
    assert mistake.status_code == 200
    assert mistake.json()["outcome"] == "mistake"
    assert mistake.json()["stage"]["key"] == "email-intake"


def test_cross_tenant_mission_session_is_hidden(client: TestClient, db: Session) -> None:
    prepare(db, "mission-first@example.com")
    prepare(db, "mission-second@example.com")
    first_csrf = sign_in(client, "mission-first@example.com")
    session_id = client.post(
        "/api/v1/missions/flagship/start",
        headers={"X-CSRF-Token": first_csrf},
    ).json()["session_id"]
    client.cookies.clear()
    second_csrf = sign_in(client, "mission-second@example.com")
    attempt = client.post(
        f"/api/v1/missions/sessions/{session_id}/actions",
        headers={"X-CSRF-Token": second_csrf},
        json={"action_type": "decision", "decision_id": "flag_sender_mismatch"},
    )
    assert attempt.status_code == 404
