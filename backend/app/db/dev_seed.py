from datetime import UTC, datetime

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.db.seed import seed_roles
from app.db.session import SessionLocal
from app.models import (
    MembershipRole,
    Organization,
    OrganizationMembership,
    Role,
    User,
    UserProfile,
)
from app.security.passwords import hash_password

LOCAL_PASSWORD = "Local-Only-CyberMentor-42!"  # noqa: S105

DEVELOPMENT_ACCOUNTS = (
    (
        "learner@local.cybermentor",
        "Local Learner",
        "cybermentor-university",
        "learner",
        False,
    ),
    (
        "instructor@local.cybermentor",
        "Local Instructor",
        "cybermentor-university",
        "instructor",
        False,
    ),
    (
        "reviewer@local.cybermentor",
        "Local Reviewer",
        "cybermentor-university",
        "reviewer",
        False,
    ),
    (
        "university-admin@local.cybermentor",
        "Local University Administrator",
        "cybermentor-university",
        "organization_owner",
        False,
    ),
    (
        "organization-admin@local.cybermentor",
        "Local Organization Administrator",
        "cybermentor-training",
        "organization_admin",
        False,
    ),
    (
        "company-manager@local.cybermentor",
        "Local Company Manager",
        "cybermentor-company",
        "company_manager",
        False,
    ),
    (
        "recruiter@local.cybermentor",
        "Local Recruiter",
        "cybermentor-recruiter",
        "recruiter",
        False,
    ),
    (
        "platform-admin@local.cybermentor",
        "Administrator",
        "cybermentor-platform",
        "platform_admin",
        True,
    ),
    (
        "content-manager@local.cybermentor",
        "Local Content Manager",
        "cybermentor-platform",
        "content_admin",
        False,
    ),
    (
        "content-author@local.cybermentor",
        "Local Content Author",
        "cybermentor-platform",
        "content_author",
        False,
    ),
    (
        "cms-learner@local.cybermentor",
        "Local CMS Learner",
        "cybermentor-platform",
        "learner",
        False,
    ),
    (
        "cms-reviewer@local.cybermentor",
        "Local CMS Reviewer",
        "cybermentor-platform",
        "technical_reviewer",
        False,
    ),
    (
        "instructional-reviewer@local.cybermentor",
        "Local Instructional Reviewer",
        "cybermentor-platform",
        "instructional_reviewer",
        False,
    ),
    (
        "accessibility-reviewer@local.cybermentor",
        "Local Accessibility Reviewer",
        "cybermentor-platform",
        "accessibility_reviewer",
        False,
    ),
)

ORGANIZATIONS = {
    "cybermentor-university": ("CyberMentor University", "university"),
    "cybermentor-training": ("CyberMentor Training Provider", "training_provider"),
    "cybermentor-company": ("CyberMentor Company", "company"),
    "cybermentor-recruiter": ("CyberMentor Recruiter Network", "recruiter"),
    "cybermentor-platform": ("CyberMentor Platform Operations", "personal"),
}


def require_local_seed(settings: Settings) -> None:
    if settings.environment != "development" or not settings.dev_seed_enabled:
        raise RuntimeError(
            "Development accounts require CYBERMENTOR_ENVIRONMENT=development "
            "and CYBERMENTOR_DEV_SEED_ENABLED=true."
        )


def seed_development_accounts(db: Session, settings: Settings) -> list[dict[str, str]]:
    require_local_seed(settings)
    seed_roles(db)
    db.flush()
    users: dict[str, User] = {}
    for email, display_name, _, _, platform_admin in DEVELOPMENT_ACCOUNTS:
        user = db.scalar(select(User).where(User.email == email))
        if user is None:
            user = User(
                email=email,
                password_hash=hash_password(LOCAL_PASSWORD),
                email_verified_at=datetime.now(UTC),
                is_active=True,
                is_platform_admin=platform_admin,
            )
            db.add(user)
            db.flush()
            db.add(UserProfile(user_id=user.id, display_name=display_name))
        else:
            user.is_active = True
            user.is_platform_admin = platform_admin
            user.password_hash = hash_password(LOCAL_PASSWORD)
            user.email_verified_at = user.email_verified_at or datetime.now(UTC)
            profile = db.scalar(select(UserProfile).where(UserProfile.user_id == user.id))
            if profile is None:
                db.add(UserProfile(user_id=user.id, display_name=display_name))
            else:
                profile.display_name = display_name
        users[email] = user

    organizations: dict[str, Organization] = {}
    for slug, (name, kind) in ORGANIZATIONS.items():
        organization = db.scalar(select(Organization).where(Organization.slug == slug))
        if organization is None:
            organization = Organization(
                name=name,
                slug=slug,
                kind=kind,
                metadata_json={"developmentFixture": "true"},
                settings={"detailedLearnerEvidence": False},
                status="active",
                version=1,
            )
            db.add(organization)
            db.flush()
        organizations[slug] = organization

    result: list[dict[str, str]] = []
    for email, _, slug, role_key, _ in DEVELOPMENT_ACCOUNTS:
        user = users[email]
        organization = organizations[slug]
        role = db.scalar(select(Role).where(Role.key == role_key))
        if role is None:
            raise RuntimeError(f"Required seeded role is missing: {role_key}")
        membership = db.scalar(
            select(OrganizationMembership).where(
                OrganizationMembership.organization_id == organization.id,
                OrganizationMembership.user_id == user.id,
            )
        )
        if membership is None:
            membership = OrganizationMembership(
                organization_id=organization.id,
                user_id=user.id,
                is_active=True,
            )
            db.add(membership)
            db.flush()
        else:
            membership.is_active = True
        db.execute(delete(MembershipRole).where(MembershipRole.membership_id == membership.id))
        db.add(MembershipRole(membership_id=membership.id, role_id=role.id))
        if role_key == "organization_owner":
            organization.owner_user_id = user.id
        result.append(
            {
                "email": email,
                "password": LOCAL_PASSWORD,
                "role": role_key,
                "organization": organization.name,
            }
        )
    db.commit()
    return result


def seed() -> None:
    settings = get_settings()
    with SessionLocal() as db:
        accounts = seed_development_accounts(db, settings)
    print({"event": "development_accounts_seeded", "accounts": accounts})


if __name__ == "__main__":
    seed()
