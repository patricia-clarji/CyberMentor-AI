import re
import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session as DatabaseSession

from app.core.config import Settings
from app.core.errors import AppError
from app.models import (
    AuditEvent,
    EmailVerificationToken,
    MembershipRole,
    Organization,
    OrganizationMembership,
    Role,
    Session,
    User,
    UserProfile,
)
from app.security.passwords import hash_password, password_needs_rehash, verify_password
from app.security.tokens import new_token, token_hash


def normalize_email(email: str) -> str:
    return email.strip().casefold()


def personal_slug(display_name: str, user_id: uuid.UUID) -> str:
    stem = re.sub(r"[^a-z0-9]+", "-", display_name.casefold()).strip("-")[:48]
    return f"{stem or 'learner'}-{str(user_id)[:8]}"


def audit(
    db: DatabaseSession,
    action: str,
    outcome: str,
    user_id: uuid.UUID | None = None,
    organization_id: uuid.UUID | None = None,
    request_id: str | None = None,
    target_type: str | None = None,
    target_id: str | None = None,
    detail: str | None = None,
) -> None:
    db.add(
        AuditEvent(
            actor_user_id=user_id,
            organization_id=organization_id,
            action=action,
            outcome=outcome,
            request_id=request_id,
            target_type=target_type,
            target_id=target_id,
            detail=detail,
            created_at=datetime.now(UTC),
        )
    )


def register_user(
    db: DatabaseSession,
    email: str,
    password: str,
    display_name: str,
    settings: Settings,
    request_id: str | None,
) -> tuple[User, str]:
    normalized = normalize_email(email)
    if db.scalar(select(User.id).where(User.email == normalized)):
        raise AppError(409, "email_registered", "An account already uses this email.")
    learner_role = db.scalar(select(Role).where(Role.key == "learner"))
    if learner_role is None:
        learner_role = Role(key="learner", name="Learner")
        db.add(learner_role)
        db.flush()
    user = User(email=normalized, password_hash=hash_password(password))
    db.add(user)
    db.flush()
    db.add(UserProfile(user_id=user.id, display_name=display_name.strip()))
    organization = Organization(
        name=f"{display_name.strip()}'s workspace",
        slug=personal_slug(display_name, user.id),
        kind="personal",
        owner_user_id=user.id,
    )
    db.add(organization)
    db.flush()
    membership = OrganizationMembership(organization_id=organization.id, user_id=user.id)
    db.add(membership)
    db.flush()
    db.add(MembershipRole(membership_id=membership.id, role_id=learner_role.id))
    raw_token = new_token()
    db.add(
        EmailVerificationToken(
            user_id=user.id,
            token_hash=token_hash(raw_token),
            expires_at=datetime.now(UTC) + timedelta(seconds=settings.verification_ttl_seconds),
        )
    )
    audit(
        db,
        "identity.register",
        "success",
        user.id,
        organization.id,
        request_id,
    )
    db.commit()
    return user, raw_token


def verify_email(db: DatabaseSession, raw_token: str, request_id: str | None) -> User:
    now = datetime.now(UTC)
    record = db.scalar(
        select(EmailVerificationToken).where(
            EmailVerificationToken.token_hash == token_hash(raw_token),
            EmailVerificationToken.used_at.is_(None),
            EmailVerificationToken.expires_at > now,
        )
    )
    if record is None:
        raise AppError(400, "invalid_verification", "Verification link is invalid or expired.")
    user = db.get(User, record.user_id)
    if user is None:
        raise AppError(400, "invalid_verification", "Verification link is invalid or expired.")
    user.email_verified_at = now
    record.used_at = now
    audit(db, "identity.verify_email", "success", user.id, request_id=request_id)
    db.commit()
    return user


def authenticate(db: DatabaseSession, email: str, password: str, request_id: str | None) -> User:
    user = db.scalar(select(User).where(User.email == normalize_email(email)))
    if user is None or not verify_password(user.password_hash, password):
        audit(db, "identity.login", "failure", request_id=request_id)
        db.commit()
        raise AppError(401, "invalid_credentials", "Email or password is incorrect.")
    if user.email_verified_at is None:
        raise AppError(403, "email_not_verified", "Verify your email before signing in.")
    if password_needs_rehash(user.password_hash):
        user.password_hash = hash_password(password)
    return user


def create_session(
    db: DatabaseSession,
    user: User,
    settings: Settings,
    ip_address: str | None,
    user_agent: str | None,
    request_id: str | None,
) -> tuple[Session, str, str]:
    membership = db.scalar(
        select(OrganizationMembership)
        .where(
            OrganizationMembership.user_id == user.id,
            OrganizationMembership.is_active.is_(True),
        )
        .order_by(OrganizationMembership.created_at)
    )
    if membership is None:
        raise AppError(403, "organization_missing", "No active organization is available.")
    raw_session = new_token()
    raw_csrf = new_token()
    now = datetime.now(UTC)
    session = Session(
        user_id=user.id,
        active_organization_id=membership.organization_id,
        token_hash=token_hash(raw_session),
        csrf_hash=token_hash(raw_csrf),
        expires_at=now + timedelta(seconds=settings.session_ttl_seconds),
        last_seen_at=now,
        ip_address=ip_address,
        user_agent=(user_agent or "")[:512] or None,
    )
    db.add(session)
    audit(
        db,
        "identity.login",
        "success",
        user.id,
        membership.organization_id,
        request_id,
    )
    db.commit()
    return session, raw_session, raw_csrf
