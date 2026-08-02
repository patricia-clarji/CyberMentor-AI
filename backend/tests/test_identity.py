from datetime import UTC, datetime

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.identity.service import register_user, verify_email
from app.models import Organization, OrganizationMembership, User


def verified_user(db: Session, email: str = "learner@example.com") -> User:
    user, raw_token = register_user(
        db,
        email,
        "Strong-Password-42!",
        "Test Learner",
        get_settings(),
        "test-request",
    )
    verify_email(db, raw_token, "test-request")
    return user


def login(client: TestClient, email: str = "learner@example.com") -> str:
    response = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "Strong-Password-42!"},
    )
    assert response.status_code == 200
    csrf = response.cookies.get("cm_csrf")
    assert csrf
    return csrf


def test_registration_creates_personal_tenant(db: Session) -> None:
    user, _ = register_user(
        db,
        " MixedCase@Example.com ",
        "Strong-Password-42!",
        "Maya Learner",
        get_settings(),
        "request-1",
    )
    assert user.email == "mixedcase@example.com"
    membership = db.scalar(
        select(OrganizationMembership).where(OrganizationMembership.user_id == user.id)
    )
    assert membership is not None
    organization = db.get(Organization, membership.organization_id)
    assert organization is not None
    assert organization.kind == "personal"
    assert organization.owner_user_id == user.id


def test_unverified_user_cannot_login(client: TestClient, db: Session) -> None:
    register_user(
        db,
        "unverified@example.com",
        "Strong-Password-42!",
        "Unverified Learner",
        get_settings(),
        "request-2",
    )
    response = client.post(
        "/api/v1/auth/login",
        json={
            "email": "unverified@example.com",
            "password": "Strong-Password-42!",
        },
    )
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "email_not_verified"


def test_session_is_cookie_bound_and_csrf_protected(client: TestClient, db: Session) -> None:
    user = verified_user(db)
    csrf = login(client)
    me = client.get("/api/v1/auth/me")
    assert me.status_code == 200
    assert me.json()["id"] == str(user.id)
    rejected = client.post("/api/v1/auth/logout")
    assert rejected.status_code == 403
    accepted = client.post("/api/v1/auth/logout", headers={"X-CSRF-Token": csrf})
    assert accepted.status_code == 200
    assert client.get("/api/v1/auth/me").status_code == 401


def test_session_listing_does_not_expose_tokens(client: TestClient, db: Session) -> None:
    verified_user(db)
    login(client)
    response = client.get("/api/v1/auth/sessions")
    assert response.status_code == 200
    payload = response.json()
    assert len(payload) == 1
    serialized = str(payload).casefold()
    assert "token" not in serialized
    assert payload[0]["current"] is True


def test_generic_password_recovery_response(client: TestClient) -> None:
    response = client.post(
        "/api/v1/auth/forgot-password",
        json={"email": "missing@example.com"},
    )
    assert response.status_code == 200
    assert response.json() == {"message": "If the account exists, a reset message has been sent."}


def test_production_configuration_rejects_development_adapters() -> None:
    from pydantic import ValidationError

    from app.core.config import Settings

    try:
        Settings(environment="production")
    except ValidationError as error:
        text = str(error)
        assert "development-only email" in text
        assert "insecure cookies" in text
        assert "test embeddings" in text
    else:
        raise AssertionError("unsafe production configuration was accepted")


def test_timestamps_are_utc(db: Session) -> None:
    user = verified_user(db, "utc@example.com")
    assert user.email_verified_at is not None
    assert user.email_verified_at <= datetime.now(UTC)
