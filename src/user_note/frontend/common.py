from typing import Any, Callable

import httpx
import streamlit as st

from user_note.frontend import api_client

STATUSES = ["draft", "in_progress", "completed", "archived"]
IMPORTANCES = ["low", "normal", "high", "critical"]


def logout() -> None:
    st.session_state.clear()


def flash(message: str) -> None:
    """Show a toast after the next rerun."""
    st.session_state["flash"] = message


def call_api(fallback: str, fn: Callable, *args, **kwargs) -> tuple[bool, Any]:
    """Run an API call, showing an error on failure. Returns (ok, result).

    A 401 means the session expired, so it logs out and goes back to sign-in.
    """
    try:
        return True, fn(*args, **kwargs)
    except api_client.APIError as e:
        if e.status_code == 401:
            logout()
            st.rerun()
        st.error(fallback)
    except httpx.HTTPError:
        st.error("Could not reach the API.")
    return False, None


def note_caption(note: dict) -> str:
    return f"{note['status']} · {note['importance']} · updated {note['updated_at']}"
