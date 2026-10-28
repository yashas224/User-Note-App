from datetime import UTC, datetime, timedelta, timezone

import jwt
import pytest
from pydantic import ValidationError
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from user_note.backend.core import rate_limit
from user_note.backend.core.config import Settings, settings
from user_note.backend.core.rate_limit import RateLimiter
from user_note.backend.core.security import (
    create_access_token,
    decode_access_token,
    hash_password,
    verify_password,
)
from user_note.backend.db.types import UTCDateTime

SECRET = "x" * 32


def test_hash_and_verify_password():
    hashed = hash_password("correct horse")
    assert hashed != "correct horse" and hashed.startswith("$argon2id$")
    assert verify_password("correct horse", hashed)
    assert not verify_password("wrong horse", hashed)


def test_token_round_trip():
    token = create_access_token(42)
    assert decode_access_token(token) == 42
    payload = jwt.decode(token, options={"verify_signature": False})
    exp = datetime.fromtimestamp(payload["exp"], UTC)
    assert timedelta(minutes=29) < exp - datetime.now(UTC) <= timedelta(minutes=30)


def _encode(payload: dict, key: str = settings.JWT_SECRET_KEY, alg: str = "HS256"):
    return jwt.encode(payload, key, algorithm=alg)


@pytest.mark.parametrize(
    "token",
    [
        _encode({"sub": "1", "exp": datetime.now(UTC) - timedelta(seconds=1)}),
        _encode(
            {"sub": "1", "exp": datetime.now(UTC) + timedelta(minutes=5)}, "y" * 32
        ),
        _encode({"sub": "1"}),
        _encode({"exp": datetime.now(UTC) + timedelta(minutes=5)}),
        _encode({"sub": "abc", "exp": datetime.now(UTC) + timedelta(minutes=5)}),
        _encode(
            {"sub": "1", "exp": datetime.now(UTC) + timedelta(minutes=5)},
            settings.JWT_SECRET_KEY,
            "HS512",
        ),
        "not-a-jwt",
    ],
    ids=["expired", "wrong-key", "no-exp", "no-sub", "bad-sub", "wrong-alg", "junk"],
)
def test_invalid_tokens_decode_to_none(token):
    assert decode_access_token(token) is None


def test_unsigned_token_rejected():
    token = jwt.encode(
        {"sub": "1", "exp": datetime.now(UTC) + timedelta(minutes=5)},
        None,
        algorithm="none",
    )
    assert decode_access_token(token) is None


def test_settings_validation():
    assert (
        Settings(JWT_SECRET_KEY=SECRET, JWT_ALGORITHM="HS384").JWT_ALGORITHM == "HS384"
    )
    with pytest.raises(ValidationError):
        Settings(JWT_SECRET_KEY="short")
    with pytest.raises(ValidationError):
        Settings(JWT_SECRET_KEY=SECRET, JWT_ALGORITHM="none")


class _Request:
    def __init__(self, host: str):
        self.client = type("Client", (), {"host": host})()


def test_rate_limiter_window(monkeypatch):
    now = [1000.0]
    monkeypatch.setattr(rate_limit.time, "monotonic", lambda: now[0])
    limiter = RateLimiter(max_requests=2, window_seconds=60)

    limiter(_Request("1.1.1.1"))
    limiter(_Request("1.1.1.1"))
    with pytest.raises(Exception) as exc:
        limiter(_Request("1.1.1.1"))
    assert exc.value.status_code == 429
    limiter(_Request("2.2.2.2"))  # separate key

    now[0] += 61
    limiter(_Request("1.1.1.1"))  # window slid

    limiter.reset()
    limiter(_Request("1.1.1.1"))
    limiter(_Request("1.1.1.1"))


def test_utc_datetime_type():
    col = UTCDateTime()
    ist = timezone(timedelta(hours=5, minutes=30))
    stored = col.process_bind_param(datetime(2026, 1, 1, 5, 30, tzinfo=ist), None)
    assert stored == datetime(2026, 1, 1, tzinfo=UTC) and stored.tzinfo == UTC
    assert col.process_bind_param(None, None) is None
    with pytest.raises(ValueError):
        col.process_bind_param(datetime(2026, 1, 1), None)

    loaded = col.process_result_value(datetime(2026, 1, 1), None)
    assert loaded.tzinfo == UTC
    assert col.process_result_value(None, None) is None


def test_sqlite_foreign_keys_enforced(session_factory):
    with session_factory() as db:
        assert db.execute(text("PRAGMA foreign_keys")).scalar() == 1
        with pytest.raises(IntegrityError):
            db.execute(
                text(
                    "INSERT INTO notes (owner_id, title, status, body, importance,"
                    " created_at, updated_at) VALUES (999, 't', 'draft', '',"
                    " 'normal', '2026-01-01', '2026-01-01')"
                )
            )
