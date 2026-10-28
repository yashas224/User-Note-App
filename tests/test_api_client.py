import json

import httpx
import pytest

from user_note.frontend import api_client


@pytest.fixture
def mock_api(monkeypatch):
    """Route api_client calls to a handler; records each request."""
    requests: list[httpx.Request] = []
    responses: dict[tuple[str, str], httpx.Response] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return responses.get(
            (request.method, request.url.path), httpx.Response(200, json={})
        )

    client = httpx.Client(
        base_url="http://api/api/v1", transport=httpx.MockTransport(handler)
    )
    monkeypatch.setattr(api_client, "_client", client)
    return requests, responses


def test_login_returns_token(mock_api):
    requests, responses = mock_api
    responses[("POST", "/api/v1/auth/login")] = httpx.Response(
        200, json={"access_token": "tok"}
    )
    assert api_client.login("alex", "pw") == "tok"
    assert json.loads(requests[0].content) == {"username": "alex", "password": "pw"}


def test_authenticated_calls_send_bearer(mock_api):
    requests, _ = mock_api
    api_client.me("tok")
    api_client.update_note("tok", 3, title="x")
    assert all(r.headers["Authorization"] == "Bearer tok" for r in requests)
    assert requests[1].method == "PATCH" and requests[1].url.path.endswith("/notes/3")


def test_list_notes_drops_none_filters(mock_api):
    requests, responses = mock_api
    responses[("GET", "/api/v1/notes")] = httpx.Response(200, json=[])
    api_client.list_notes("tok", status="draft", importance=None, search=None)
    assert dict(requests[0].url.params) == {"status": "draft"}


@pytest.mark.parametrize(
    "call, method, path",
    [
        (lambda: api_client.register("a", "b"), "POST", "/auth/register"),
        (
            lambda: api_client.create_note("t", "x", "draft", "low", ""),
            "POST",
            "/notes",
        ),
        (lambda: api_client.delete_note("t", 1), "DELETE", "/notes/1"),
        (lambda: api_client.list_trash("t"), "GET", "/notes/trash"),
        (lambda: api_client.restore_note("t", 1), "POST", "/notes/1/restore"),
        (lambda: api_client.create_share("t", 1, None), "POST", "/notes/1/shares"),
        (lambda: api_client.list_shares("t", 1), "GET", "/notes/1/shares"),
        (lambda: api_client.revoke_share("t", 1, 2), "DELETE", "/notes/1/shares/2"),
    ],
)
def test_endpoints(mock_api, call, method, path):
    requests, _ = mock_api
    call()
    assert requests[0].method == method
    assert requests[0].url.path == f"/api/v1{path}"


def test_get_shared_sends_no_auth(mock_api):
    requests, _ = mock_api
    api_client.get_shared("abc")
    assert requests[0].url.path == "/api/v1/shared/abc"
    assert "Authorization" not in requests[0].headers


def test_no_content_returns_none(mock_api):
    _, responses = mock_api
    responses[("DELETE", "/api/v1/notes/1")] = httpx.Response(204)
    assert api_client.delete_note("t", 1) is None


@pytest.mark.parametrize(
    "response, message",
    [
        (
            httpx.Response(409, json={"detail": "Username already taken"}),
            "Username already taken",
        ),
        (
            httpx.Response(
                422, json={"detail": [{"msg": "too short"}, {"msg": "bad"}]}
            ),
            "too short; bad",
        ),
        (httpx.Response(500, text="oops"), "Request failed"),
    ],
)
def test_errors_raise_api_error(mock_api, response, message):
    _, responses = mock_api
    responses[("GET", "/api/v1/auth/me")] = response
    with pytest.raises(api_client.APIError) as exc:
        api_client.me("tok")
    assert exc.value.status_code == response.status_code
    assert str(exc.value) == message
