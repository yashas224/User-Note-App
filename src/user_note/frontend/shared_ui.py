import httpx
import streamlit as st

from user_note.frontend import api_client


def render(share_token: str) -> None:
    """Public, read-only view of a shared note. No login, no edit controls."""
    try:
        note = api_client.get_shared(share_token)
    except api_client.APIError:
        st.error("This link is invalid or has expired.")
        return
    except httpx.HTTPError:
        st.error("Could not reach the API.")
        return
    st.caption("Shared note · read-only")
    st.header(note["title"])
    st.caption(
        f"{note['status']} · {note['importance']} · updated {note['updated_at']}"
    )
    st.write(note["body"] or "_(empty)_")
