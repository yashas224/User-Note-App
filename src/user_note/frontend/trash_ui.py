import streamlit as st

from user_note.frontend import api_client
from user_note.frontend.common import call_api, flash, note_caption


def render(token: str) -> None:
    st.subheader("Trash")
    ok, notes = call_api("Could not load the trash.", api_client.list_trash, token)
    if not ok:
        return
    if not notes:
        st.info("Trash is empty.")
    for note in notes:
        with st.container(border=True):
            st.markdown(f"**{note['title']}**")
            st.caption(note_caption(note))
            if st.button("Restore", key=f"restore_btn_{note['id']}"):
                ok, _ = call_api(
                    "Could not restore the note.",
                    api_client.restore_note,
                    token,
                    note["id"],
                )
                if ok:
                    flash("Note restored.")
                    st.rerun()
