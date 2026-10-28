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


def _create(client, headers, **fields) -> dict:
    payload = {"title": "Plan", **fields}
    return client.post("/api/v1/notes", json=payload, headers=headers).json()


def test_partial_update(client, auth_headers):
    headers = auth_headers()
    note = _create(client, headers, body="keep me")
    resp = client.patch(
        f"/api/v1/notes/{note['id']}",
        json={"title": "New", "status": "completed"},
        headers=headers,
    )
    assert resp.status_code == 200
    updated = resp.json()
    assert updated["title"] == "New"
    assert updated["status"] == "completed"
    assert updated["body"] == "keep me"
    assert updated["importance"] == "normal"
    assert updated["updated_at"] > note["updated_at"]
    assert client.get(f"/api/v1/notes/{note['id']}", headers=headers).json() == updated


@pytest.mark.parametrize(
    "payload",
    [
        {"status": "bogus"},
        {"importance": "urgent"},
        {"title": None},
        {"title": ""},
        {"owner_id": 99},
    ],
)
def test_invalid_update_rejected(client, auth_headers, payload):
    headers = auth_headers()
    note = _create(client, headers)
    resp = client.patch(f"/api/v1/notes/{note['id']}", json=payload, headers=headers)
    assert resp.status_code == 422


def test_soft_delete(client, auth_headers):
    headers = auth_headers()
    note = _create(client, headers)
    url = f"/api/v1/notes/{note['id']}"
    resp = client.delete(url, headers=headers)
    assert resp.status_code == 204
    assert resp.content == b""
    assert client.get("/api/v1/notes", headers=headers).json() == []
    assert client.get(url, headers=headers).status_code == 404
    assert client.patch(url, json={"title": "x"}, headers=headers).status_code == 404
    assert client.delete(url, headers=headers).status_code == 404


def test_cannot_access_other_users_note(client, auth_headers):
    alice, bob = auth_headers("alice"), auth_headers("bob")
    note = _create(client, alice)
    url = f"/api/v1/notes/{note['id']}"
    assert client.get(url, headers=bob).status_code == 404
    assert client.patch(url, json={"title": "x"}, headers=bob).status_code == 404
    assert client.delete(url, headers=bob).status_code == 404
    assert client.get(url, headers=alice).json() == note


def test_update_delete_require_auth(client, auth_headers):
    note = _create(client, auth_headers())
    url = f"/api/v1/notes/{note['id']}"
    assert client.patch(url, json={"title": "x"}).status_code == 401
    assert client.delete(url).status_code == 401


def test_trash_and_restore(client, auth_headers):
    headers = auth_headers()
    note = _create(client, headers)
    assert client.get("/api/v1/notes/trash", headers=headers).json() == []
    client.delete(f"/api/v1/notes/{note['id']}", headers=headers)

    trash = client.get("/api/v1/notes/trash", headers=headers).json()
    assert [n["id"] for n in trash] == [note["id"]]

    resp = client.post(f"/api/v1/notes/{note['id']}/restore", headers=headers)
    assert resp.status_code == 200
    assert client.get("/api/v1/notes/trash", headers=headers).json() == []
    assert [n["id"] for n in client.get("/api/v1/notes", headers=headers).json()] == [
        note["id"]
    ]
    # Restoring an active note is not a valid target.
    resp = client.post(f"/api/v1/notes/{note['id']}/restore", headers=headers)
    assert resp.status_code == 404


def test_cannot_see_or_restore_other_users_trash(client, auth_headers):
    alice, bob = auth_headers("alice"), auth_headers("bob")
    note = _create(client, alice)
    client.delete(f"/api/v1/notes/{note['id']}", headers=alice)
    assert client.get("/api/v1/notes/trash", headers=bob).json() == []
    resp = client.post(f"/api/v1/notes/{note['id']}/restore", headers=bob)
    assert resp.status_code == 404


def _titles(client, headers, **params) -> list[str]:
    resp = client.get("/api/v1/notes", headers=headers, params=params)
    assert resp.status_code == 200
    return [n["title"] for n in resp.json()]


def test_filters_search_and_sort(client, auth_headers):
    headers = auth_headers()
    for title, status, importance in [
        ("Beta report", "draft", "critical"),
        ("Alpha plan", "completed", "low"),
        ("Gamma report", "draft", "normal"),
    ]:
        client.post(
            "/api/v1/notes",
            json={"title": title, "status": status, "importance": importance},
            headers=headers,
        )

    assert _titles(client, headers, status="draft", sort_by="title", order="asc") == [
        "Beta report",
        "Gamma report",
    ]
    assert _titles(client, headers, importance="low") == ["Alpha plan"]
    assert _titles(client, headers, search="REPORT", sort_by="title", order="asc") == [
        "Beta report",
        "Gamma report",
    ]
    assert _titles(client, headers, search="%") == []
    # Importance sorts by severity, not alphabetically.
    assert _titles(client, headers, sort_by="importance", order="desc") == [
        "Beta report",
        "Gamma report",
        "Alpha plan",
    ]
    assert _titles(
        client, headers, sort_by="title", order="asc", limit=1, offset=1
    ) == ["Beta report"]


@pytest.mark.parametrize(
    "params",
    [{"status": "bogus"}, {"sort_by": "owner_id"}, {"limit": 0}, {"offset": -1}],
)
def test_invalid_list_params_rejected(client, auth_headers, params):
    resp = client.get("/api/v1/notes", headers=auth_headers(), params=params)
    assert resp.status_code == 422
