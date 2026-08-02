import uuid
from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, Request
from sqlalchemy import delete, select
from sqlalchemy.orm import Session as DatabaseSession

from app.core.config import Settings, get_settings
from app.core.errors import AppError
from app.db.session import get_db
from app.identity.dependencies import (
    AuthContext,
    assert_permission,
    permission_keys,
    require_auth,
    require_csrf,
)
from app.identity.service import audit, normalize_email
from app.models import (
    AuditEvent,
    MembershipHistory,
    MembershipRole,
    Organization,
    OrganizationInvitation,
    OrganizationMembership,
    Role,
    User,
    UserProfile,
)
from app.schemas.operations import (
    InvitationCreate,
    InvitationToken,
    MemberUpdate,
    OrganizationCreate,
    OrganizationUpdate,
)
from app.security.tokens import new_token, token_hash
from app.services.email import get_email_provider

router = APIRouter(prefix="/organizations", tags=["organizations"])


def request_id(request: Request) -> str | None:
    return getattr(request.state, "request_id", None)


def current_organization(db: DatabaseSession, auth: AuthContext) -> Organization:
    organization = db.scalar(
        select(Organization).where(
            Organization.id == auth.organization_id,
            Organization.status == "active",
        )
    )
    if organization is None:
        raise AppError(404, "organization_not_found", "Organization was not found.")
    return organization


def organization_role(db: DatabaseSession, key: str) -> Role:
    role = db.scalar(select(Role).where(Role.key == key))
    if role is None:
        raise AppError(503, "roles_not_seeded", "Organization roles are not seeded.")
    return role


@router.post("", status_code=201)
def create_organization(
    payload: OrganizationCreate,
    request: Request,
    auth: AuthContext = Depends(require_csrf),
    db: DatabaseSession = Depends(get_db),
) -> dict[str, object]:
    if db.scalar(select(Organization.id).where(Organization.slug == payload.slug)):
        raise AppError(409, "organization_slug_exists", "That organization slug is unavailable.")
    role = organization_role(db, "organization_owner")
    organization = Organization(
        name=payload.name.strip(),
        slug=payload.slug,
        kind=payload.kind,
        owner_user_id=auth.user.id,
        metadata_json={},
        settings={"detailedLearnerEvidence": False},
        status="active",
        version=1,
    )
    db.add(organization)
    db.flush()
    membership = OrganizationMembership(
        organization_id=organization.id,
        user_id=auth.user.id,
        is_active=True,
    )
    db.add(membership)
    db.flush()
    db.add(MembershipRole(membership_id=membership.id, role_id=role.id))
    db.add(
        MembershipHistory(
            organization_id=organization.id,
            membership_id=membership.id,
            actor_user_id=auth.user.id,
            action="created",
            role_key=role.key,
            created_at=datetime.now(UTC),
        )
    )
    audit(
        db,
        "organization.created",
        "success",
        auth.user.id,
        organization.id,
        request_id(request),
        "organization",
        str(organization.id),
    )
    db.commit()
    return {"id": organization.id, "name": organization.name, "kind": organization.kind}


@router.get("/current")
def get_current_organization(
    auth: AuthContext = Depends(require_auth),
    db: DatabaseSession = Depends(get_db),
) -> dict[str, object]:
    assert_permission(db, auth, "organization.view")
    item = current_organization(db, auth)
    return {
        "id": item.id,
        "name": item.name,
        "slug": item.slug,
        "kind": item.kind,
        "metadata": item.metadata_json,
        "settings": item.settings,
        "status": item.status,
        "version": item.version,
        "permissions": sorted(permission_keys(db, auth)),
    }


@router.patch("/current")
def update_current_organization(
    payload: OrganizationUpdate,
    request: Request,
    auth: AuthContext = Depends(require_csrf),
    db: DatabaseSession = Depends(get_db),
) -> dict[str, object]:
    assert_permission(db, auth, "organization.manage")
    item = current_organization(db, auth)
    if item.version != payload.version:
        raise AppError(409, "organization_changed", "Reload before saving organization changes.")
    if payload.name is not None:
        item.name = payload.name.strip()
    if payload.metadata is not None:
        item.metadata_json = payload.metadata
    if payload.settings is not None:
        item.settings = payload.settings
    item.version += 1
    audit(
        db,
        "organization.settings_changed",
        "success",
        auth.user.id,
        auth.organization_id,
        request_id(request),
        "organization",
        str(item.id),
    )
    db.commit()
    return {"id": item.id, "name": item.name, "version": item.version}


@router.post("/{organization_id}/activate")
def activate_organization(
    organization_id: uuid.UUID,
    request: Request,
    auth: AuthContext = Depends(require_csrf),
    db: DatabaseSession = Depends(get_db),
) -> dict[str, str]:
    membership = db.scalar(
        select(OrganizationMembership).where(
            OrganizationMembership.organization_id == organization_id,
            OrganizationMembership.user_id == auth.user.id,
            OrganizationMembership.is_active.is_(True),
        )
    )
    if membership is None:
        raise AppError(404, "organization_not_found", "Organization was not found.")
    auth.session.active_organization_id = organization_id
    audit(
        db,
        "organization.activate",
        "success",
        auth.user.id,
        organization_id,
        request_id(request),
        "organization",
        str(organization_id),
    )
    db.commit()
    return {"message": "Active organization changed."}


@router.get("/members")
def members(
    auth: AuthContext = Depends(require_auth),
    db: DatabaseSession = Depends(get_db),
) -> list[dict[str, object]]:
    assert_permission(db, auth, "organization.members.view")
    rows = db.execute(
        select(OrganizationMembership, User, UserProfile)
        .join(User, User.id == OrganizationMembership.user_id)
        .outerjoin(UserProfile, UserProfile.user_id == User.id)
        .where(OrganizationMembership.organization_id == auth.organization_id)
        .order_by(User.email)
    ).all()
    result: list[dict[str, object]] = []
    for membership, user, profile in rows:
        roles = list(
            db.scalars(
                select(Role.key)
                .join(MembershipRole, MembershipRole.role_id == Role.id)
                .where(MembershipRole.membership_id == membership.id)
            ).all()
        )
        result.append(
            {
                "membership_id": membership.id,
                "user_id": user.id,
                "display_name": profile.display_name if profile else "",
                "email": user.email,
                "active": membership.is_active,
                "roles": roles,
                "joined_at": membership.created_at,
            }
        )
    return result


@router.patch("/members/{membership_id}")
def update_member(
    membership_id: uuid.UUID,
    payload: MemberUpdate,
    request: Request,
    auth: AuthContext = Depends(require_csrf),
    db: DatabaseSession = Depends(get_db),
) -> dict[str, object]:
    assert_permission(db, auth, "organization.members.manage")
    membership = db.scalar(
        select(OrganizationMembership).where(
            OrganizationMembership.id == membership_id,
            OrganizationMembership.organization_id == auth.organization_id,
        )
    )
    if membership is None:
        raise AppError(404, "membership_not_found", "Membership was not found.")
    organization = current_organization(db, auth)
    if membership.user_id == organization.owner_user_id and (
        payload.active is False or payload.role not in {None, "organization_owner"}
    ):
        raise AppError(409, "owner_protected", "Transfer ownership before changing the owner.")
    action = "updated"
    if payload.active is not None:
        membership.is_active = payload.active
        action = "reactivated" if payload.active else "deactivated"
    if payload.role is not None:
        role = organization_role(db, payload.role)
        db.execute(delete(MembershipRole).where(MembershipRole.membership_id == membership.id))
        db.add(MembershipRole(membership_id=membership.id, role_id=role.id))
        action = "role_changed"
    db.add(
        MembershipHistory(
            organization_id=auth.organization_id,
            membership_id=membership.id,
            actor_user_id=auth.user.id,
            action=action,
            role_key=payload.role,
            created_at=datetime.now(UTC),
        )
    )
    audit(
        db,
        f"membership.{action}",
        "success",
        auth.user.id,
        auth.organization_id,
        request_id(request),
        "membership",
        str(membership.id),
    )
    db.commit()
    return {"membership_id": membership.id, "active": membership.is_active}


@router.get("/members/{membership_id}/history")
def membership_history(
    membership_id: uuid.UUID,
    auth: AuthContext = Depends(require_auth),
    db: DatabaseSession = Depends(get_db),
) -> list[dict[str, object]]:
    assert_permission(db, auth, "organization.members.view")
    records = db.scalars(
        select(MembershipHistory)
        .where(
            MembershipHistory.organization_id == auth.organization_id,
            MembershipHistory.membership_id == membership_id,
        )
        .order_by(MembershipHistory.created_at.desc())
    ).all()
    return [
        {
            "action": item.action,
            "role": item.role_key,
            "actor_user_id": item.actor_user_id,
            "created_at": item.created_at,
        }
        for item in records
    ]


@router.post("/invitations", status_code=201)
def invite_member(
    payload: InvitationCreate,
    request: Request,
    auth: AuthContext = Depends(require_csrf),
    db: DatabaseSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> dict[str, object]:
    assert_permission(db, auth, "organization.members.invite")
    organization_role(db, payload.role)
    email = normalize_email(str(payload.email))
    now = datetime.now(UTC)
    existing = db.scalar(
        select(OrganizationInvitation).where(
            OrganizationInvitation.organization_id == auth.organization_id,
            OrganizationInvitation.email == email,
            OrganizationInvitation.status == "pending",
            OrganizationInvitation.expires_at > now,
        )
    )
    if existing:
        raise AppError(409, "invitation_exists", "An active invitation already exists.")
    raw_token = new_token()
    invitation = OrganizationInvitation(
        organization_id=auth.organization_id,
        email=email,
        role_key=payload.role,
        token_hash=token_hash(raw_token),
        status="pending",
        invited_by_user_id=auth.user.id,
        expires_at=now + timedelta(days=payload.expires_in_days),
    )
    db.add(invitation)
    db.flush()
    audit(
        db,
        "member.invited",
        "success",
        auth.user.id,
        auth.organization_id,
        request_id(request),
        "invitation",
        str(invitation.id),
    )
    db.commit()
    get_email_provider(settings).send(
        email,
        "CyberMentor organization invitation",
        f"Accept the invitation with this one-time token:\n\n{raw_token}\n",
    )
    return {
        "id": invitation.id,
        "status": invitation.status,
        "expires_at": invitation.expires_at,
        "acceptance_token": raw_token if settings.environment != "production" else None,
    }


@router.get("/invitations")
def invitations(
    auth: AuthContext = Depends(require_auth),
    db: DatabaseSession = Depends(get_db),
) -> list[dict[str, object]]:
    assert_permission(db, auth, "organization.members.view")
    records = db.scalars(
        select(OrganizationInvitation)
        .where(OrganizationInvitation.organization_id == auth.organization_id)
        .order_by(OrganizationInvitation.created_at.desc())
    ).all()
    return [
        {
            "id": item.id,
            "email": item.email,
            "role": item.role_key,
            "status": item.status,
            "expires_at": item.expires_at,
        }
        for item in records
    ]


@router.post("/invitations/{invitation_id}/cancel")
def cancel_invitation(
    invitation_id: uuid.UUID,
    request: Request,
    auth: AuthContext = Depends(require_csrf),
    db: DatabaseSession = Depends(get_db),
) -> dict[str, str]:
    assert_permission(db, auth, "organization.members.invite")
    invitation = db.scalar(
        select(OrganizationInvitation).where(
            OrganizationInvitation.id == invitation_id,
            OrganizationInvitation.organization_id == auth.organization_id,
            OrganizationInvitation.status == "pending",
        )
    )
    if invitation is None:
        raise AppError(404, "invitation_not_found", "Invitation was not found.")
    invitation.status = "cancelled"
    invitation.responded_at = datetime.now(UTC)
    audit(
        db,
        "member.invitation_cancelled",
        "success",
        auth.user.id,
        auth.organization_id,
        request_id(request),
        "invitation",
        str(invitation.id),
    )
    db.commit()
    return {"status": "cancelled"}


@router.post("/invitations/{invitation_id}/resend")
def resend_invitation(
    invitation_id: uuid.UUID,
    payload: InvitationCreate,
    request: Request,
    auth: AuthContext = Depends(require_csrf),
    db: DatabaseSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> dict[str, object]:
    assert_permission(db, auth, "organization.members.invite")
    old = db.scalar(
        select(OrganizationInvitation).where(
            OrganizationInvitation.id == invitation_id,
            OrganizationInvitation.organization_id == auth.organization_id,
            OrganizationInvitation.status == "pending",
        )
    )
    if old is None or old.email != normalize_email(str(payload.email)):
        raise AppError(404, "invitation_not_found", "Invitation was not found.")
    old.status = "cancelled"
    db.flush()
    return invite_member(payload, request, auth, db, settings)


def respond_to_invitation(
    payload: InvitationToken,
    accepted: bool,
    request: Request,
    auth: AuthContext,
    db: DatabaseSession,
) -> dict[str, object]:
    now = datetime.now(UTC)
    invitation = db.scalar(
        select(OrganizationInvitation).where(
            OrganizationInvitation.token_hash == token_hash(payload.token),
            OrganizationInvitation.status == "pending",
            OrganizationInvitation.expires_at > now,
        )
    )
    if invitation is None or invitation.email != auth.user.email:
        raise AppError(400, "invalid_invitation", "Invitation is invalid or expired.")
    invitation.status = "accepted" if accepted else "rejected"
    invitation.responded_at = now
    if accepted:
        role = organization_role(db, invitation.role_key)
        membership = db.scalar(
            select(OrganizationMembership).where(
                OrganizationMembership.organization_id == invitation.organization_id,
                OrganizationMembership.user_id == auth.user.id,
            )
        )
        if membership is None:
            membership = OrganizationMembership(
                organization_id=invitation.organization_id,
                user_id=auth.user.id,
                is_active=True,
            )
            db.add(membership)
            db.flush()
        else:
            membership.is_active = True
        db.execute(delete(MembershipRole).where(MembershipRole.membership_id == membership.id))
        db.add(MembershipRole(membership_id=membership.id, role_id=role.id))
        db.add(
            MembershipHistory(
                organization_id=invitation.organization_id,
                membership_id=membership.id,
                actor_user_id=auth.user.id,
                action="invitation_accepted",
                role_key=role.key,
                created_at=now,
            )
        )
    audit(
        db,
        f"member.invitation_{invitation.status}",
        "success",
        auth.user.id,
        invitation.organization_id,
        request_id(request),
        "invitation",
        str(invitation.id),
    )
    db.commit()
    return {"status": invitation.status, "organization_id": invitation.organization_id}


@router.post("/invitations/accept")
def accept_invitation(
    payload: InvitationToken,
    request: Request,
    auth: AuthContext = Depends(require_csrf),
    db: DatabaseSession = Depends(get_db),
) -> dict[str, object]:
    return respond_to_invitation(payload, True, request, auth, db)


@router.post("/invitations/reject")
def reject_invitation(
    payload: InvitationToken,
    request: Request,
    auth: AuthContext = Depends(require_csrf),
    db: DatabaseSession = Depends(get_db),
) -> dict[str, object]:
    return respond_to_invitation(payload, False, request, auth, db)


@router.get("/audit")
def audit_events(
    auth: AuthContext = Depends(require_auth),
    db: DatabaseSession = Depends(get_db),
    limit: int = 100,
) -> list[dict[str, object]]:
    assert_permission(db, auth, "audit_logs.view")
    records = db.scalars(
        select(AuditEvent)
        .where(AuditEvent.organization_id == auth.organization_id)
        .order_by(AuditEvent.created_at.desc())
        .limit(min(max(limit, 1), 500))
    ).all()
    return [
        {
            "id": item.id,
            "actor_user_id": item.actor_user_id,
            "action": item.action,
            "target_type": item.target_type,
            "target_id": item.target_id,
            "timestamp": item.created_at,
            "request_id": item.request_id,
            "result": item.outcome,
        }
        for item in records
    ]
