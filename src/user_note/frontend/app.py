from pathlib import Path

import streamlit as st

from user_note.frontend import (
    auth_ui,
    notes_ui,
    shared_ui,
    sharing_ui,
    trash_ui,
)
from user_note.frontend.common import logout

HERO_IMAGE = Path(__file__).parent / "assets" / "hero.svg"

st.set_page_config(page_title="Notes", page_icon="📝")

# Public share links are handled before the login gate.
if share_token := st.query_params.get("share"):
    shared_ui.render(share_token)
    st.stop()

st.title("📝 Notes")

token = st.session_state.get("token")
if not token:
    st.image(HERO_IMAGE, width="stretch")
    auth_ui.render()
    st.stop()

PAGES = {
    "All Notes": notes_ui.render_list,
    "Create Note": notes_ui.render_create,
    "Trash": trash_ui.render,
    "Manage Sharing": sharing_ui.render,
}

with st.sidebar:
    st.write(f"Signed in as **{st.session_state.get('username', '')}**")
    page = st.radio("Navigate", list(PAGES), label_visibility="collapsed")
    if st.button("Logout"):
        logout()
        st.rerun()

if message := st.session_state.pop("flash", None):
    st.toast(message)

PAGES[page](token)
