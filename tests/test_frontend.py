from pathlib import Path
from unittest.mock import patch

import httpx
import pytest
from streamlit.testing.v1 import AppTest

from user_note.frontend import api_client
from user_note.frontend.common import note_caption
from user_note.frontend.sharing_ui import _share_status

APP = str(Path(__file__).parents[1] / "src/user_note/frontend/app.py")
API = "user_note.frontend.api_client"
NOTE = {
    "id": 1,
    "title": "Plan",
    "body": "Body text",
    "status": "draft",
    "importance": "normal",
    "created_at": "2026-01-01T00:00:00Z",
    "updated_at": "2026-01-01T00:00:00Z",
}


def _app(**state) -> AppTest:
    at = AppTest.from_file(APP, default_timeout=10)
    for key, value in state.items():
        at.session_state[key] = value
    return at


def _logged_in() -> AppTest:
    return _app(token="tok", username="alex")


def _texts(elements) -> list[str]:
    return [e.value for e in elements]


def _button(at, label):
    return next(b for b in at.button if b.label == label)


def test_unauthenticated_user_sees_auth_screen():
    at = _app().run()
    assert not at.exception
    assert [t.label for t in at.tabs] == ["Sign In", "Sign Up"]
    assert not at.sidebar.radio


def test_login_and_logout():
    with (
        patch(f"{API}.login", return_value="tok") as login,
        patch(f"{API}.me", return_value={"username": "alex"}),
        patch(f"{API}.list_notes", return_value=[]),
    ):
        at = _app().run()
        at.tabs[0].text_input[0].input("alex ")
        at.tabs[0].text_input[1].input("pw")
        at.tabs[0].button[0].click().run()

        login.assert_called_once_with("alex", "pw")
        assert at.session_state["token"] == "tok"
        assert "alex" in at.sidebar.markdown[0].value

        at.sidebar.button[0].click().run()
        assert "token" not in at.session_state
        assert [t.label for t in at.tabs] == ["Sign In", "Sign Up"]


def test_login_failure_shows_error():
    with patch(
        f"{API}.login",
        side_effect=api_client.APIError(401, "Invalid username or password"),
    ):
        at = _app().run()
        at.tabs[0].text_input[0].input("alex")
        at.tabs[0].text_input[1].input("bad")
        at.tabs[0].button[0].click().run()
    assert _texts(at.error) == ["Invalid username or password"]
    assert "token" not in at.session_state


def test_api_unreachable_shows_error():
    with patch(f"{API}.login", side_effect=httpx.ConnectError("down")):
        at = _app().run()
        at.tabs[0].button[0].click().run()
    assert _texts(at.error) == ["Could not reach the API."]


def test_sign_up_password_mismatch():
    with patch(f"{API}.register") as register:
        at = _app().run()
        tab = at.tabs[1]
        tab.text_input[0].input("alex")
        tab.text_input[1].input("password-one")
        tab.text_input[2].input("password-two")
        tab.button[0].click().run()
    register.assert_not_called()
    assert _texts(at.error) == ["Passwords do not match."]


def test_sign_up_shows_server_validation_error():
    with patch(
        f"{API}.register",
        side_effect=api_client.APIError(409, "Username already taken"),
    ):
        at = _app().run()
        tab = at.tabs[1]
        tab.text_input[0].input("alex")
        tab.text_input[1].input("pw12345")
        tab.text_input[2].input("pw12345")
        tab.button[0].click().run()
    assert _texts(at.error) == ["Username already taken"]


def test_sign_up_logs_in():
    with (
        patch(f"{API}.register") as register,
        patch(f"{API}.login", return_value="tok"),
        patch(f"{API}.me", return_value={"username": "alex"}),
        patch(f"{API}.list_notes", return_value=[]),
    ):
        at = _app().run()
        tab = at.tabs[1]
        tab.text_input[0].input("alex")
        tab.text_input[1].input("pw12345")
        tab.text_input[2].input("pw12345")
        tab.button[0].click().run()
    register.assert_called_once_with("alex", "pw12345")
    assert at.session_state["token"] == "tok"


def test_dashboard_lists_notes():
    with patch(f"{API}.list_notes", return_value=[NOTE]):
        at = _logged_in().run()
    assert not at.exception
    assert "**Plan**" in _texts(at.markdown)
    assert note_caption(NOTE) in _texts(at.caption)


def test_empty_dashboard():
    with patch(f"{API}.list_notes", return_value=[]):
        at = _logged_in().run()
    assert _texts(at.info) == ["No notes yet."]


def test_filters_passed_to_api():
    with patch(f"{API}.list_notes", return_value=[]) as list_notes:
        at = _logged_in().run()
        at.text_input[0].input("report")
        at.selectbox[0].set_value("completed")
        at.selectbox[2].set_value("Title")
        at.selectbox[3].set_value("asc").run()
    list_notes.assert_called_with(
        "tok",
        search="report",
        status="completed",
        importance=None,
        sort_by="title",
        order="asc",
    )
    assert _texts(at.info) == ["No notes match."]


def test_create_note():
    with (
        patch(f"{API}.list_notes", return_value=[]),
        patch(f"{API}.create_note", return_value=NOTE) as create,
    ):
        at = _logged_in().run()
        at.sidebar.radio[0].set_value("Create Note").run()
        at.text_input[0].input("  Plan ")
        at.text_area[0].input("Body text")
        at.button[0].click().run()
    create.assert_called_once_with("tok", "Plan", "draft", "normal", "Body text")
    assert _texts(at.success) == ["Note created."]


def test_create_note_requires_title():
    with (
        patch(f"{API}.list_notes", return_value=[]),
        patch(f"{API}.create_note") as create,
    ):
        at = _logged_in().run()
        at.sidebar.radio[0].set_value("Create Note").run()
        at.button[0].click().run()
    create.assert_not_called()
    assert _texts(at.error) == ["Title is required."]


def test_edit_note_updates_dashboard():
    notes = [NOTE]

    def update(token, note_id, **fields):
        notes[0] = {**NOTE, **fields}
        return notes[0]

    with (
        patch(f"{API}.list_notes", side_effect=lambda *a, **k: list(notes)),
        patch(f"{API}.update_note", side_effect=update) as update_note,
    ):
        at = _logged_in().run()
        _button(at, "Edit").click().run()
        at.text_input[1].input("Renamed")
        _button(at, "Save").click().run()
    update_note.assert_called_once_with(
        "tok", 1, title="Renamed", status="draft", importance="normal", body="Body text"
    )
    assert "**Renamed**" in _texts(at.markdown)
    assert "editing_id" not in at.session_state
    assert _texts(at.toast) == ["Note updated."]


def test_edit_cancel():
    with patch(f"{API}.list_notes", return_value=[NOTE]):
        at = _logged_in().run()
        _button(at, "Edit").click().run()
        _button(at, "Cancel").click().run()
    assert "editing_id" not in at.session_state


def test_delete_note():
    notes = [NOTE]
    with (
        patch(f"{API}.list_notes", side_effect=lambda *a, **k: list(notes)),
        patch(f"{API}.delete_note", side_effect=lambda *a: notes.clear()) as delete,
    ):
        at = _logged_in().run()
        _button(at, "Delete").click().run()
    delete.assert_called_once_with("tok", 1)
    assert _texts(at.info) == ["No notes yet."]


def test_expired_session_returns_to_login():
    with patch(f"{API}.list_notes", side_effect=api_client.APIError(401, "x")):
        at = _logged_in().run()
    assert "token" not in at.session_state
    assert [t.label for t in at.tabs] == ["Sign In", "Sign Up"]


def test_api_error_shows_fallback_message():
    with patch(f"{API}.list_notes", side_effect=api_client.APIError(500, "boom")):
        at = _logged_in().run()
    assert _texts(at.error) == ["Could not load notes."]


def test_trash_and_restore():
    trash = [NOTE]
    with (
        patch(f"{API}.list_notes", return_value=[]),
        patch(f"{API}.list_trash", side_effect=lambda *a: list(trash)),
        patch(f"{API}.restore_note", side_effect=lambda *a: trash.clear()) as restore,
    ):
        at = _logged_in().run()
        at.sidebar.radio[0].set_value("Trash").run()
        _button(at, "Restore").click().run()
    restore.assert_called_once_with("tok", 1)
    assert _texts(at.info) == ["Trash is empty."]


def test_manage_sharing_create_and_revoke():
    share = {
        "id": 5,
        "created_at": "2026-01-01T00:00:00Z",
        "expires_at": None,
        "revoked_at": None,
        "is_active": True,
    }
    url = "http://localhost:8501/?share=abc"
    with (
        patch(f"{API}.list_notes", return_value=[NOTE]),
        patch(f"{API}.list_shares", return_value=[share]),
        patch(f"{API}.create_share", return_value={"share_url": url}) as create,
        patch(f"{API}.revoke_share") as revoke,
    ):
        at = _logged_in().run()
        at.sidebar.radio[0].set_value("Manage Sharing").run()
        assert len(at.warning) == 1
        at.selectbox[1].set_value("Never")
        _button(at, "Create sharing link").click().run()
        create.assert_called_once_with("tok", 1, None)
        assert at.code[0].value == url

        _button(at, "Revoke").click().run()
        revoke.assert_called_once_with("tok", 1, 5)


def test_manage_sharing_without_notes():
    with patch(f"{API}.list_notes", return_value=[]):
        at = _logged_in().run()
        at.sidebar.radio[0].set_value("Manage Sharing").run()
    assert _texts(at.info) == ["Create a note first to share it."]


@pytest.mark.parametrize(
    "share, expected",
    [
        ({"revoked_at": "t", "is_active": False}, "Revoked"),
        ({"revoked_at": None, "is_active": True}, "Active"),
        ({"revoked_at": None, "is_active": False}, "Expired"),
    ],
)
def test_share_status(share, expected):
    assert _share_status(share) == expected


def test_public_share_link_works_without_login():
    shared = {
        k: NOTE[k] for k in ("title", "body", "status", "importance", "updated_at")
    }
    with patch(f"{API}.get_shared", return_value=shared) as get_shared:
        at = _app()
        at.query_params["share"] = "abc"
        at.run()
    get_shared.assert_called_once_with("abc")
    assert at.header[0].value == "Plan"
    assert not at.tabs and not at.button and not at.sidebar.radio


def test_public_share_link_bypasses_login_even_when_signed_in():
    with (
        patch(f"{API}.get_shared", return_value={**NOTE, "body": ""}),
        patch(f"{API}.list_notes") as list_notes,
    ):
        at = _logged_in()
        at.query_params["share"] = "abc"
        at.run()
    list_notes.assert_not_called()
    assert "_(empty)_" in _texts(at.markdown)


def test_invalid_share_link_shows_generic_error():
    with patch(f"{API}.get_shared", side_effect=api_client.APIError(404, "x")):
        at = _app()
        at.query_params["share"] = "bad"
        at.run()
    assert _texts(at.error) == ["This link is invalid or has expired."]
    assert not at.tabs
