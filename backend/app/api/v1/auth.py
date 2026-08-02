import uuid
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, Request, Response
from sqlalchemy import select, update
from sqlalchemy.orm import Session as DatabaseSession

from app.core.config import Settings, get_settings
from app.core.errors import AppError
from app.db.session import get_db
from app.identity.dependencies import AuthContext, require_auth, require_csrf
from app.identity.service import (
    audit,
    authenticate,
    create_session,
    register_user,
    verify_email,
)
from app.models import (
    MembershipRole,
    Organization,
    OrganizationMembership,
    PasswordResetToken,
    Role,
    Session,
    User,
    UserProfile,
)
from app.schemas.auth import (
    ChangePasswordRequest,
    ForgotPasswordRequest,
    LoginRequest,
    OrganizationSummary,
    RegisterRequest,
    ResetPasswordRequest,
    SessionSummary,
    TokenRequest,
    UserSummary,
)
from app.security.passwords import hash_password, verify_password
from app.security.tokens import new_token, token_hash
from app.services.email import get_email_provider

router = APIRouter(prefix="/auth", tags=["identity"])


def request_id(request: Request) -> str | None:
    return getattr(request.state, "request_id", None)


def set_auth_cookies(
    response: Response,
    session_token: str,
    csrf_token: str,
    settings: Settings,
) -> None:
    response.set_cookie(
        settings.session_cookie_name,
        session_token,
        httponly=True,
        secure=settings.secure_cookies,
        samesite="lax",
        path="/",
        max_age=settings.session_ttl_seconds,
    )
    response.set_cookie(
        settings.csrf_cookie_name,
        csrf_token,
        httponly=False,
        secure=settings.secure_cookies,
        samesite="lax",
        path="/",
        max_age=settings.session_ttl_seconds,
    )


def clear_auth_cookies(response: Response, settings: Settings) -> None:
    response.delete_cookie(settings.session_cookie_name, path="/")
    response.delete_cookie(settings.csrf_cookie_name, path="/")


@router.post("/register", status_code=201)
def register(
    payload: RegisterRequest,
    request: Request,
    db: DatabaseSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> dict[str, str]:
    user, verification_token = register_user(
        db,
        str(payload.email),
        payload.password,
        payload.display_name,
        settings,
        request_id(request),
    )
    verify_url = f"{settings.frontend_origin}/verify-email?token={verification_token}"
    get_email_provider(settings).send(
        user.email,
        "Verify your CyberMentor account",
        f"Verify your account using this one-time link:\n\n{verify_url}\n",
    )
    return {"message": "Registration accepted. Check your email to verify the account."}


@router.post("/verify-email")
def verify(
    payload: TokenRequest,
    request: Request,
    db: DatabaseSession = Depends(get_db),
) -> dict[str, str]:
    verify_email(db, payload.token, request_id(request))
    return {"message": "Email verified. You can now sign in."}


@router.post("/login")
def login(
    payload: LoginRequest,
    request: Request,
    response: Response,
    db: DatabaseSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> dict[str, str]:
    user = authenticate(db, str(payload.email), payload.password, request_id(request))
    _, session_token, csrf_token = create_session(
        db,
        user,
        settings,
        request.client.host if request.client else None,
        request.headers.get("user-agent"),
        request_id(request),
    )
    set_auth_cookies(response, session_token, csrf_token, settings)
    return {"message": "Signed in."}


@router.post("/logout")
def logout(
    request: Request,
    response: Response,
    auth: AuthContext = Depends(require_csrf),
    db: DatabaseSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> dict[str, str]:
    auth.session.revoked_at = datetime.now(UTC)
    audit(
        db,
        "identity.logout",
        "success",
        auth.user.id,
        auth.organization_id,
        request_id(request),
        "session",
        str(auth.session.id),
    )
    db.commit()
    clear_auth_cookies(response, settings)
    return {"message": "Signed out."}


def user_summary(db: DatabaseSession, auth: AuthContext) -> UserSummary:
    profile = db.scalar(select(UserProfile).where(UserProfile.user_id == auth.user.id))
    rows = db.execute(
        select(OrganizationMembership, Organization)
        .join(
            Organization,
            Organization.id == OrganizationMembership.organization_id,
        )
        .where(
            OrganizationMembership.user_id == auth.user.id,
            OrganizationMembership.is_active.is_(True),
        )
    ).all()
    organizations: list[OrganizationSummary] = []
    for membership, organization in rows:
        roles = db.scalars(
            select(Role.key)
            .join(MembershipRole, MembershipRole.role_id == Role.id)
            .where(MembershipRole.membership_id == membership.id)
        ).all()
        organizations.append(
            OrganizationSummary(
                id=organization.id,
                name=organization.name,
                slug=organization.slug,
                kind=organization.kind,
                roles=list(roles),
            )
        )
    return UserSummary(
        id=auth.user.id,
        email=auth.user.email,
        display_name=profile.display_name if profile else "",
        email_verified=auth.user.email_verified_at is not None,
        active_organization_id=auth.organization_id,
        organizations=organizations,
    )


@router.get("/me", response_model=UserSummary)
def me(
    auth: AuthContext = Depends(require_auth),
    db: DatabaseSession = Depends(get_db),
) -> UserSummary:
    return user_summary(db, auth)


@router.get("/sessions", response_model=list[SessionSummary])
def sessions(
    auth: AuthContext = Depends(require_auth),
    db: DatabaseSession = Depends(get_db),
) -> list[SessionSummary]:
    records = db.scalars(
        select(Session)
        .where(Session.user_id == auth.user.id, Session.revoked_at.is_(None))
        .order_by(Session.created_at.desc())
    ).all()
    return [
        SessionSummary(
            id=record.id,
            created_at=record.created_at,
            last_seen_at=record.last_seen_at,
            expires_at=record.expires_at,
            current=record.id == auth.session.id,
            user_agent=record.user_agent,
        )
        for record in records
    ]


@router.delete("/sessions/{session_id}")
def revoke_session(
    session_id: uuid.UUID,
    request: Request,
    response: Response,
    auth: AuthContext = Depends(require_csrf),
    db: DatabaseSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> dict[str, str]:
    target = db.scalar(
        select(Session).where(
            Session.id == session_id,
            Session.user_id == auth.user.id,
            Session.revoked_at.is_(None),
        )
    )
    if target is None:
        raise AppError(404, "session_not_found", "Session was not found.")
    target.revoked_at = datetime.now(UTC)
    audit(
        db,
        "identity.revoke_session",
        "success",
        auth.user.id,
        auth.organization_id,
        request_id(request),
        "session",
        str(target.id),
    )
    db.commit()
    if target.id == auth.session.id:
        clear_auth_cookies(response, settings)
    return {"message": "Session revoked."}


@router.post("/forgot-password")
def forgot_password(
    payload: ForgotPasswordRequest,
    request: Request,
    db: DatabaseSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> dict[str, str]:
    from datetime import timedelta

    email = str(payload.email).strip().casefold()
    user = db.scalar(select(User).where(User.email == email, User.is_active.is_(True)))
    if user is not None:
        raw_token = new_token()
        db.add(
            PasswordResetToken(
                user_id=user.id,
                token_hash=token_hash(raw_token),
                expires_at=datetime.now(UTC) + timedelta(seconds=settings.reset_ttl_seconds),
            )
        )
        audit(
            db,
            "identity.password_reset_requested",
            "success",
            user.id,
            request_id=request_id(request),
        )
        db.commit()
        reset_url = f"{settings.frontend_origin}/reset-password?token={raw_token}"
        get_email_provider(settings).send(
            user.email,
            "Reset your CyberMentor password",
            f"Use this one-time reset link:\n\n{reset_url}\n",
        )
    return {"message": "If the account exists, a reset message has been sent."}


@router.post("/reset-password")
def reset_password(
    payload: ResetPasswordRequest,
    request: Request,
    db: DatabaseSession = Depends(get_db),
) -> dict[str, str]:
    now = datetime.now(UTC)
    record = db.scalar(
        select(PasswordResetToken).where(
            PasswordResetToken.token_hash == token_hash(payload.token),
            PasswordResetToken.used_at.is_(None),
            PasswordResetToken.expires_at > now,
        )
    )
    if record is None:
        raise AppError(400, "invalid_reset", "Reset link is invalid or expired.")
    user = db.get(User, record.user_id)
    if user is None:
        raise AppError(400, "invalid_reset", "Reset link is invalid or expired.")
    user.password_hash = hash_password(payload.password)
    record.used_at = now
    db.execute(
        update(Session)
        .where(Session.user_id == user.id, Session.revoked_at.is_(None))
        .values(revoked_at=now)
    )
    audit(db, "identity.password_reset", "success", user.id, request_id=request_id(request))
    db.commit()
    return {"message": "Password reset. Sign in again on every device."}


@router.post("/change-password")
def change_password(
    payload: ChangePasswordRequest,
    request: Request,
    response: Response,
    auth: AuthContext = Depends(require_csrf),
    db: DatabaseSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> dict[str, str]:
    if not verify_password(auth.user.password_hash, payload.current_password):
        raise AppError(400, "invalid_current_password", "Current password is incorrect.")
    auth.user.password_hash = hash_password(payload.new_password)
    now = datetime.now(UTC)
    db.execute(
        update(Session)
        .where(Session.user_id == auth.user.id, Session.revoked_at.is_(None))
        .values(revoked_at=now)
    )
    audit(
        db,
        "identity.password_changed",
        "success",
        auth.user.id,
        auth.organization_id,
        request_id(request),
    )
    db.commit()
    clear_auth_cookies(response, settings)
    return {"message": "Password changed. Sign in again on every device."}
