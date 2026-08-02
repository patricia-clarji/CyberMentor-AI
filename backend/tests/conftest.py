import os
from collections.abc import Generator

os.environ["CYBERMENTOR_ENVIRONMENT"] = "test"
os.environ["CYBERMENTOR_DATABASE_URL"] = "sqlite+pysqlite:///:memory:"
os.environ["CYBERMENTOR_EMAIL_BACKEND"] = "console"

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.db.session import get_db
from app.main import app

test_engine = create_engine(
    "sqlite+pysqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestSession = sessionmaker(bind=test_engine, expire_on_commit=False)


@pytest.fixture(autouse=True)
def clean_database() -> Generator[None, None, None]:
    Base.metadata.drop_all(test_engine)
    Base.metadata.create_all(test_engine)
    yield


@pytest.fixture
def db() -> Generator[Session, None, None]:
    with TestSession() as session:
        yield session


@pytest.fixture
def client() -> Generator[TestClient, None, None]:
    def override_db() -> Generator[Session, None, None]:
        with TestSession() as session:
            yield session

    app.dependency_overrides[get_db] = override_db
    with TestClient(app, base_url="http://testserver") as test_client:
        yield test_client
    app.dependency_overrides.clear()
