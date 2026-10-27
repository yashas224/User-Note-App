import pytest


def test_create_and_list(client, auth_headers):
    headers = auth_headers()
    resp = client.post("/api/v1/notes", json={"title": "Plan"}, headers=headers)
    assert resp.status_code == 201
    note = resp.json()
    assert note["status"] == "draft"
    assert note["importance"] == "normal"
    assert note["body"] == ""
    assert "owner_id" not in note

    notes = client.get("/api/v1/notes", headers=headers).json()
    assert [n["id"] for n in notes] == [note["id"]]


def test_timestamps_are_utc(client, auth_headers):
    headers = auth_headers()
    client.post("/api/v1/notes", json={"title": "Plan"}, headers=headers)
    note = client.get("/api/v1/notes", headers=headers).json()[0]
    assert note["created_at"].endswith("Z")
    assert note["updated_at"].endswith("Z")


def test_notes_require_auth(client):
    assert client.get("/api/v1/notes").status_code == 401
    assert client.post("/api/v1/notes", json={"title": "x"}).status_code == 401


def test_users_only_see_own_notes(client, auth_headers):
    alice, bob = auth_headers("alice"), auth_headers("bob")
    client.post("/api/v1/notes", json={"title": "secret"}, headers=alice)
    assert client.get("/api/v1/notes", headers=bob).json() == []


@pytest.mark.parametrize(
    "payload",
    [
        {"title": "x", "status": "bogus"},
        {"title": "x", "importance": "urgent"},
        {"title": ""},
        {"title": "x" * 201},
        {"title": "x", "owner_id": 99},
    ],
)
def test_invalid_payload_rejected(client, auth_headers, payload):
    resp = client.post("/api/v1/notes", json=payload, headers=auth_headers())
    assert resp.status_code == 422
