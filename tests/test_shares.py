from datetime import UTC, datetime, timedelta
from urllib.parse import parse_qs, urlparse

from sqlalchemy import select

from user_note.backend.models import NoteShare


def _note(client, headers) -> dict:
    payload = {"title": "Shared", "body": "Hello", "importance": "high"}
    return client.post("/api/v1/notes", json=payload, headers=headers).json()


def _share(client, headers, note_id: int, **body) -> dict:
    resp = client.post(f"/api/v1/notes/{note_id}/shares", json=body, headers=headers)
    assert resp.status_code == 201
    return resp.json()


def _token(share: dict) -> str:
    return parse_qs(urlparse(share["share_url"]).query)["share"][0]


def _public(client, share: dict):
    return client.get(f"/api/v1/shared/{_token(share)}")


def test_valid_link_without_login_returns_only_public_fields(client, auth_headers):
    headers = auth_headers()
    note = _note(client, headers)
    share = _share(client, headers, note["id"])
    assert share["share_url"].startswith("http://localhost:8501/?share=")

    resp = _public(client, share)
    assert resp.status_code == 200
    assert set(resp.json()) == {"title", "body", "status", "importance", "updated_at"}
    assert resp.json()["title"] == "Shared"


def test_raw_token_not_stored(client, auth_headers, session_factory):
    headers = auth_headers()
    share = _share(client, headers, _note(client, headers)["id"])
    with session_factory() as db:
        row = db.scalar(select(NoteShare))
    assert len(row.token_hash) == 64
    assert row.token_hash != _token(share)


def test_list_shares_hides_token(client, auth_headers):
    headers = auth_headers()
    note = _note(client, headers)
    _share(client, headers, note["id"], expires_in_days=None)
    shares = client.get(f"/api/v1/notes/{note['id']}/shares", headers=headers).json()
    assert len(shares) == 1
    assert shares[0]["is_active"] is True
    assert shares[0]["expires_at"] is None
    assert "share_url" not in shares[0] and "token_hash" not in shares[0]


def test_revoked_link_fails(client, auth_headers):
    headers = auth_headers()
    note = _note(client, headers)
    share = _share(client, headers, note["id"])
    resp = client.delete(
        f"/api/v1/notes/{note['id']}/shares/{share['id']}", headers=headers
    )
    assert resp.status_code == 204
    assert _public(client, share).status_code == 404


def test_expired_link_fails(client, auth_headers, session_factory):
    headers = auth_headers()
    share = _share(client, headers, _note(client, headers)["id"])
    with session_factory() as db:
        row = db.get(NoteShare, share["id"])
        row.expires_at = datetime.now(UTC) - timedelta(seconds=1)
        db.commit()
    assert _public(client, share).status_code == 404


def test_deleted_note_link_fails(client, auth_headers):
    headers = auth_headers()
    note = _note(client, headers)
    share = _share(client, headers, note["id"])
    client.delete(f"/api/v1/notes/{note['id']}", headers=headers)
    assert _public(client, share).status_code == 404


def test_invalid_links_share_one_generic_error(client):
    resp = client.get("/api/v1/shared/not-a-real-token")
    assert resp.status_code == 404
    assert resp.json() == {"detail": "Link is invalid or has expired"}


def test_shared_note_cannot_be_modified_anonymously(client, auth_headers):
    headers = auth_headers()
    share = _share(client, headers, _note(client, headers)["id"])
    url = f"/api/v1/shared/{_token(share)}"
    assert client.patch(url, json={"title": "x"}).status_code == 405
    assert client.delete(url).status_code == 405


def test_other_user_cannot_manage_shares(client, auth_headers):
    alice, bob = auth_headers("alice"), auth_headers("bob")
    note = _note(client, alice)
    share = _share(client, alice, note["id"])
    base = f"/api/v1/notes/{note['id']}/shares"
    assert client.post(base, json={}, headers=bob).status_code == 404
    assert client.get(base, headers=bob).status_code == 404
    assert client.delete(f"{base}/{share['id']}", headers=bob).status_code == 404
    assert _public(client, share).status_code == 200


def test_invalid_expiry_rejected(client, auth_headers):
    headers = auth_headers()
    note = _note(client, headers)
    resp = client.post(
        f"/api/v1/notes/{note['id']}/shares",
        json={"expires_in_days": 0},
        headers=headers,
    )
    assert resp.status_code == 422
