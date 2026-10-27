import os

os.environ.setdefault("JWT_SECRET_KEY", "test-secret-key-that-is-long-enough-1234")

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from user_note.backend.core.rate_limit import auth_rate_limiter
from user_note.backend.db.base import Base
from user_note.backend.db.session import enable_sqlite_foreign_keys, get_db
from user_note.backend.main import app

PASSWORD = "a-long-example-password"


@pytest.fixture
def session_factory():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    enable_sqlite_foreign_keys(engine)
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine, expire_on_commit=False)


@pytest.fixture
def client(session_factory):
    def override_get_db():
        with session_factory() as db:
            yield db

    auth_rate_limiter.reset()
    app.dependency_overrides[get_db] = override_get_db
    yield TestClient(app)
    app.dependency_overrides.clear()


@pytest.fixture
def auth_headers(client):
    def make(username: str = "alex") -> dict:
        creds = {"username": username, "password": PASSWORD}
        assert client.post("/api/v1/auth/register", json=creds).status_code == 201
        token = client.post("/api/v1/auth/login", json=creds).json()["access_token"]
        return {"Authorization": f"Bearer {token}"}

    return make
