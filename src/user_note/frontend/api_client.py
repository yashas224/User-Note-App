import os

import httpx
from dotenv import load_dotenv

load_dotenv()
API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000/api/v1")

_client = httpx.Client(base_url=API_BASE_URL, timeout=10)


class APIError(Exception):
    def __init__(self, status_code: int, message: str):
        super().__init__(message)
        self.status_code = status_code


def _check(resp: httpx.Response) -> dict | list | None:
    if resp.is_error:
        try:
            detail = resp.json().get("detail", "Request failed")
        except ValueError:
            detail = "Request failed"
        if isinstance(detail, list):  # Pydantic validation errors
            detail = "; ".join(e.get("msg", "") for e in detail)
        raise APIError(resp.status_code, detail)
    if resp.status_code == 204:
        return None
    return resp.json()


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def register(username: str, password: str) -> dict:
    return _check(
        _client.post(
            "/auth/register", json={"username": username, "password": password}
        )
    )


def login(username: str, password: str) -> str:
    data = _check(
        _client.post("/auth/login", json={"username": username, "password": password})
    )
    return data["access_token"]


def me(token: str) -> dict:
    return _check(_client.get("/auth/me", headers=_auth(token)))


def list_notes(token: str, **filters) -> list[dict]:
    params = {k: v for k, v in filters.items() if v is not None}
    return _check(_client.get("/notes", headers=_auth(token), params=params))


def create_note(
    token: str, title: str, status: str, importance: str, body: str
) -> dict:
    return _check(
        _client.post(
            "/notes",
            headers=_auth(token),
            json={
                "title": title,
                "status": status,
                "importance": importance,
                "body": body,
            },
        )
    )


def update_note(token: str, note_id: int, **fields) -> dict:
    return _check(_client.patch(f"/notes/{note_id}", headers=_auth(token), json=fields))


def delete_note(token: str, note_id: int) -> None:
    _check(_client.delete(f"/notes/{note_id}", headers=_auth(token)))


def list_trash(token: str) -> list[dict]:
    return _check(_client.get("/notes/trash", headers=_auth(token)))


def restore_note(token: str, note_id: int) -> dict:
    return _check(_client.post(f"/notes/{note_id}/restore", headers=_auth(token)))


def create_share(token: str, note_id: int, expires_in_days: int | None) -> dict:
    return _check(
        _client.post(
            f"/notes/{note_id}/shares",
            headers=_auth(token),
            json={"expires_in_days": expires_in_days},
        )
    )


def list_shares(token: str, note_id: int) -> list[dict]:
    return _check(_client.get(f"/notes/{note_id}/shares", headers=_auth(token)))


def revoke_share(token: str, note_id: int, share_id: int) -> None:
    _check(_client.delete(f"/notes/{note_id}/shares/{share_id}", headers=_auth(token)))


def get_shared(share_token: str) -> dict:
    """Public endpoint: deliberately sends no auth header."""
    return _check(_client.get(f"/shared/{share_token}"))
