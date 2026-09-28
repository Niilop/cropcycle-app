import os
from collections.abc import Iterator

# Set these before importing the app; tests never connect to the developer's database.
os.environ["DATABASE_URL"] = "sqlite://"
os.environ["SECRET_KEY"] = "test-only-secret-key-with-at-least-32-bytes"
os.environ["DEBUG"] = "false"
os.environ["CORS_ORIGINS"] = "http://localhost:3000"

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from backend.core.database import Base, get_db
from backend.core.rate_limit import limiter
from backend.main import create_app
from backend.seed import load_catalog, read_catalog


@pytest.fixture
def session_factory() -> Iterator[sessionmaker[Session]]:
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )

    @event.listens_for(engine, "connect")
    def foreign_keys(connection, record) -> None:
        connection.execute("PRAGMA foreign_keys=ON")

    Base.metadata.create_all(engine)
    yield sessionmaker(bind=engine, autoflush=False)
    engine.dispose()


@pytest.fixture
def db(session_factory: sessionmaker[Session]) -> Iterator[Session]:
    with session_factory() as session:
        yield session


@pytest.fixture
def client(
    session_factory: sessionmaker[Session],
) -> Iterator[TestClient]:
    limiter.reset()
    app = create_app()

    def override_db() -> Iterator[Session]:
        with session_factory() as session:
            yield session

    app.dependency_overrides[get_db] = override_db
    with TestClient(app) as test_client:
        yield test_client
    limiter.reset()


@pytest.fixture
def auth_headers(client: TestClient) -> dict[str, str]:
    response = client.post(
        "/auth/register",
        json={
            "email": "tester@example.com",
            "username": "tester",
            "password": "a-long-test-password",
        },
    )
    assert response.status_code == 201
    response = client.post(
        "/auth/login", data={"username": "tester", "password": "a-long-test-password"}
    )
    assert response.status_code == 200
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


@pytest.fixture
def catalog(db: Session) -> dict[str, int]:
    """Load the real seed catalogue; returns crop IDs by slug."""
    load_catalog(db, read_catalog())
    from backend.models.database import Crop

    return {crop.slug: crop.id for crop in db.query(Crop)}


@pytest.fixture
def other_headers(client: TestClient) -> dict[str, str]:
    client.post(
        "/auth/register",
        json={
            "email": "other@example.com",
            "username": "other",
            "password": "another-long-password",
        },
    )
    response = client.post(
        "/auth/login", data={"username": "other", "password": "another-long-password"}
    )
    return {"Authorization": f"Bearer {response.json()['access_token']}"}
