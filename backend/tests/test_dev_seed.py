from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.db.dev_seed import DEVELOPMENT_ACCOUNTS, LOCAL_PASSWORD, seed_development_accounts
from app.models import OrganizationMembership, User
from app.security.passwords import verify_password


def test_development_accounts_are_guarded_idempotent_and_verified(db: Session) -> None:
    disabled = Settings(
        environment="development",
        database_url="sqlite+pysqlite:///:memory:",
        email_backend="console",
        dev_seed_enabled=False,
    )
    try:
        seed_development_accounts(db, disabled)
    except RuntimeError as error:
        assert "DEV_SEED_ENABLED=true" in str(error)
    else:
        raise AssertionError("Disabled development account seed unexpectedly ran.")

    enabled = Settings(
        environment="development",
        database_url="sqlite+pysqlite:///:memory:",
        email_backend="console",
        dev_seed_enabled=True,
    )
    first = seed_development_accounts(db, enabled)
    second = seed_development_accounts(db, enabled)
    assert first == second
    assert len(first) == len(DEVELOPMENT_ACCOUNTS)
    assert db.scalar(select(func.count(User.id))) == len(DEVELOPMENT_ACCOUNTS)
    assert db.scalar(select(func.count(OrganizationMembership.id))) == len(DEVELOPMENT_ACCOUNTS)
    learner = db.scalar(select(User).where(User.email == "learner@local.cybermentor"))
    assert learner is not None
    assert learner.email_verified_at is not None
    assert verify_password(learner.password_hash, LOCAL_PASSWORD)


def test_production_rejects_development_account_flag() -> None:
    try:
        Settings(
            environment="production",
            database_url="postgresql+psycopg://example",
            email_backend="provider",
            production_email_provider="example",
            secure_cookies=True,
            embedding_provider="provider",
            object_storage_backend="provider",
            dev_seed_enabled=True,
        )
    except ValueError as error:
        assert "development seed accounts" in str(error)
    else:
        raise AssertionError("Production accepted development seed accounts.")
