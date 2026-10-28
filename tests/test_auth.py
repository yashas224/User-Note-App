import pytest
from sqlalchemy import select

from user_note.backend.models import User

PASSWORD = "a-long-example-password"
REGISTER = "/api/v1/auth/register"
LOGIN = "/api/v1/auth/login"
ME = "/api/v1/auth/me"


def test_register_hashes_password(client, session_factory):
    resp = client.post(REGISTER, json={"username": "alex", "password": PASSWORD})
    assert resp.status_code == 201
    assert resp.json()["username"] == "alex"
    assert "password" not in resp.text and "password_hash" not in resp.json()

    with session_factory() as db:
        stored = db.scalar(select(User.password_hash))
    assert stored.startswith("$argon2id$") and PASSWORD not in stored


def test_duplicate_username_case_insensitive(client):
    client.post(REGISTER, json={"username": "alex", "password": PASSWORD})
    resp = client.post(REGISTER, json={"username": "ALEX", "password": PASSWORD})
    assert resp.status_code == 409


def test_short_password_rejected(client):
    resp = client.post(REGISTER, json={"username": "alex", "password": "abcd"})
    assert resp.status_code == 422


def test_login_and_me(client):
    client.post(REGISTER, json={"username": "alex", "password": PASSWORD})
    resp = client.post(LOGIN, json={"username": "Alex", "password": PASSWORD})
    assert resp.status_code == 200
    body = resp.json()
    assert body["token_type"] == "bearer" and body["expires_in"] == 1800

    me = client.get(ME, headers={"Authorization": f"Bearer {body['access_token']}"})
    assert me.status_code == 200 and me.json()["username"] == "alex"


def test_invalid_credentials_are_generic(client):
    client.post(REGISTER, json={"username": "alex", "password": PASSWORD})
    wrong = client.post(LOGIN, json={"username": "alex", "password": "x" * 12})
    unknown = client.post(LOGIN, json={"username": "nobody", "password": PASSWORD})
    assert wrong.status_code == unknown.status_code == 401
    assert wrong.json() == unknown.json()


def test_me_requires_valid_token(client):
    assert client.get(ME).status_code == 401
    bad = client.get(ME, headers={"Authorization": "Bearer garbage"})
    assert bad.status_code == 401


def test_login_rate_limited(client):
    creds = {"username": "nobody", "password": PASSWORD}
    codes = [client.post(LOGIN, json=creds).status_code for _ in range(11)]
    assert codes[-1] == 429


def _token_for(client, username: str = "alex") -> str:
    client.post(REGISTER, json={"username": username, "password": PASSWORD})
    creds = {"username": username, "password": PASSWORD}
    return client.post(LOGIN, json=creds).json()["access_token"]


def test_expired_token_rejected(client, session_factory):
    from datetime import UTC, datetime, timedelta

    import jwt

    from user_note.backend.core.config import settings

    _token_for(client)
    with session_factory() as db:
        user_id = db.scalar(select(User.id))
    expired = jwt.encode(
        {"sub": str(user_id), "exp": datetime.now(UTC) - timedelta(seconds=1)},
        settings.JWT_SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM,
    )
    assert (
        client.get(ME, headers={"Authorization": f"Bearer {expired}"}).status_code
        == 401
    )


def test_disabled_user_cannot_authenticate(client, session_factory):
    token = _token_for(client)
    with session_factory() as db:
        db.scalar(select(User)).is_active = False
        db.commit()
    resp = client.post(LOGIN, json={"username": "alex", "password": PASSWORD})
    assert resp.status_code == 401
    assert resp.json() == {"detail": "Invalid username or password"}
    assert (
        client.get(ME, headers={"Authorization": f"Bearer {token}"}).status_code == 401
    )


def test_token_for_deleted_user_rejected(client, session_factory):
    token = _token_for(client)
    with session_factory() as db:
        db.delete(db.scalar(select(User)))
        db.commit()
    assert (
        client.get(ME, headers={"Authorization": f"Bearer {token}"}).status_code == 401
    )


@pytest.mark.parametrize(
    "payload",
    [
        {"username": "ab", "password": PASSWORD},
        {"username": "bad name!", "password": PASSWORD},
        {"username": "alex", "password": "x" * 129},
        {"username": "alex", "password": PASSWORD, "is_active": False},
    ],
)
def test_invalid_registration_rejected(client, payload):
    assert client.post(REGISTER, json=payload).status_code == 422


def test_register_rate_limited(client):
    codes = [
        client.post(
            REGISTER, json={"username": f"user{i}", "password": PASSWORD}
        ).status_code
        for i in range(11)
    ]
    assert codes[:10] == [201] * 10 and codes[-1] == 429
