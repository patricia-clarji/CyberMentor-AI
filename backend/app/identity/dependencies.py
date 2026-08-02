import secrets
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime

from fastapi import Cookie, Depends, Header, Request
from sqlalchemy import select
from sqlalchemy.orm import Session as DatabaseSession

from app.core.config import Settings, get_settings
from app.core.errors import AppError
from app.db.session import get_db
from app.models import (
    MembershipRole,
    OrganizationMembership,
    Permission,
    RolePermission,
    Session,
    User,
)
from app.security.tokens import token_hash


@dataclass(frozen=True)
class AuthContext:
    user: User
    session: Session
    organization_id: uuid.UUID


def as_utc(value: datetime) -> datetime:
    return value.replace(tzinfo=UTC) if value.tzinfo is None else value


def require_auth(
    request: Request,
    session_token: str | None = Cookie(default=None, alias="cm_session"),
    db: DatabaseSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> AuthContext:
    if not session_token:
        raise AppError(401, "authentication_required", "Sign in to continue.")
    session = db.scalar(select(Session).where(Session.token_hash == token_hash(session_token)))
    now = datetime.now(UTC)
    if session is None or session.revoked_at is not None or as_utc(session.expires_at) <= now:
        raise AppError(401, "session_expired", "Your session has expired.")
    user = db.get(User, session.user_id)
    if user is None or not user.is_active:
        raise AppError(401, "account_unavailable", "This account is unavailable.")
    membership = db.scalar(
        select(OrganizationMembership).where(
            OrganizationMembership.organization_id == session.active_organization_id,
            OrganizationMembership.user_id == user.id,
            OrganizationMembership.is_active.is_(True),
        )
    )
    if membership is None:
        raise AppError(403, "organization_access_denied", "Organization access denied.")
    session.last_seen_at = now
    db.commit()
    auth = AuthContext(user, session, session.active_organization_id)
    request.state.auth = auth
    return auth


def require_csrf(
    auth: AuthContext = Depends(require_auth),
    csrf_cookie: str | None = Cookie(default=None, alias="cm_csrf"),
    csrf_header: str | None = Header(default=None, alias="X-CSRF-Token"),
) -> AuthContext:
    if (
        not csrf_cookie
        or not csrf_header
        or not secrets.compare_digest(csrf_cookie, csrf_header)
        or not secrets.compare_digest(token_hash(csrf_header), auth.session.csrf_hash)
    ):
        raise AppError(403, "csrf_failed", "Request validation failed.")
    return auth


def permission_keys(db: DatabaseSession, auth: AuthContext) -> set[str]:
    if auth.user.is_platform_admin:
        return {"*"}
    return set(
        db.scalars(
            select(Permission.key)
            .join(RolePermission, RolePermission.permission_id == Permission.id)
            .join(MembershipRole, MembershipRole.role_id == RolePermission.role_id)
            .join(
                OrganizationMembership,
                OrganizationMembership.id == MembershipRole.membership_id,
            )
            .where(
                OrganizationMembership.organization_id == auth.organization_id,
                OrganizationMembership.user_id == auth.user.id,
                OrganizationMembership.is_active.is_(True),
            )
        ).all()
    )


def assert_permission(
    db: DatabaseSession,
    auth: AuthContext,
    permission: str,
) -> None:
    keys = permission_keys(db, auth)
    if "*" not in keys and permission not in keys:
        raise AppError(
            403,
            "permission_denied",
            f"The {permission} permission is required.",
        )
