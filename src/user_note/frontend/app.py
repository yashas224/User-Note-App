import httpx
import streamlit as st

from user_note.frontend import api_client, auth_ui

STATUSES = ["draft", "in_progress", "completed", "archived"]
IMPORTANCES = ["low", "normal", "high", "critical"]

st.set_page_config(page_title="Notes", page_icon="📝")
st.title("📝 Notes")


def logout() -> None:
    st.session_state.pop("token", None)
    st.session_state.pop("username", None)


def handle_api_error(e: api_client.APIError, fallback: str) -> None:
    if e.status_code == 401:
        logout()
        st.rerun()
    st.error(fallback)


token = st.session_state.get("token")
if not token:
    auth_ui.render()
    st.stop()

with st.sidebar:
    st.write(f"Signed in as **{st.session_state.get('username', '')}**")
    if st.button("Logout"):
        logout()
        st.rerun()

with st.expander("Create Note", expanded=True):
    with st.form("create_note", clear_on_submit=True):
        title = st.text_input("Title", max_chars=200)
        col1, col2 = st.columns(2)
        status = col1.selectbox("Status", STATUSES)
        importance = col2.selectbox("Importance", IMPORTANCES, index=1)
        body = st.text_area("Body")
        if st.form_submit_button("Save"):
            if not title.strip():
                st.error("Title is required.")
            else:
                try:
                    api_client.create_note(
                        token, title.strip(), status, importance, body
                    )
                    st.success("Note created.")
                except api_client.APIError as e:
                    handle_api_error(e, "Could not create the note.")
                except httpx.HTTPError:
                    st.error("Could not reach the API.")

st.subheader("All Notes")
try:
    notes = api_client.list_notes(token)
except api_client.APIError as e:
    handle_api_error(e, "Could not load notes.")
    st.stop()
except httpx.HTTPError:
    st.error("Could not reach the API.")
    st.stop()

if not notes:
    st.info("No notes yet.")
for note in notes:
    with st.container(border=True):
        st.markdown(f"**{note['title']}**")
        st.caption(
            f"{note['status']} · {note['importance']} · updated {note['updated_at']}"
        )
        if note["body"]:
            st.write(note["body"])
