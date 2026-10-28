import streamlit as st

from user_note.frontend import api_client
from user_note.frontend.common import (
    IMPORTANCES,
    STATUSES,
    call_api,
    flash,
    note_caption,
)

ALL = "All"
SORT_OPTIONS = {
    "Last modified": "updated_at",
    "Created": "created_at",
    "Title": "title",
    "Importance": "importance",
}


def render_create(token: str) -> None:
    st.subheader("Create Note")
    with st.form("create_note", clear_on_submit=True):
        title = st.text_input("Title", max_chars=200)
        col1, col2 = st.columns(2)
        status = col1.selectbox("Status", STATUSES)
        importance = col2.selectbox("Importance", IMPORTANCES, index=1)
        body = st.text_area("Body")
        if st.form_submit_button("Save"):
            if not title.strip():
                st.error("Title is required.")
                return
            ok, _ = call_api(
                "Could not create the note.",
                api_client.create_note,
                token,
                title.strip(),
                status,
                importance,
                body,
            )
            if ok:
                st.success("Note created.")


def _render_filters() -> dict:
    search = st.text_input("Search titles", placeholder="Search…")
    col1, col2, col3, col4 = st.columns(4)
    status = col1.selectbox("Status", [ALL, *STATUSES])
    importance = col2.selectbox("Importance", [ALL, *IMPORTANCES])
    sort_label = col3.selectbox("Sort by", list(SORT_OPTIONS))
    order = col4.selectbox("Order", ["desc", "asc"])
    return {
        "search": search.strip() or None,
        "status": None if status == ALL else status,
        "importance": None if importance == ALL else importance,
        "sort_by": SORT_OPTIONS[sort_label],
        "order": order,
    }


def _render_edit_form(token: str, note: dict) -> None:
    with st.form(f"edit_{note['id']}"):
        title = st.text_input("Title", value=note["title"], max_chars=200)
        col1, col2 = st.columns(2)
        status = col1.selectbox(
            "Status", STATUSES, index=STATUSES.index(note["status"])
        )
        importance = col2.selectbox(
            "Importance", IMPORTANCES, index=IMPORTANCES.index(note["importance"])
        )
        body = st.text_area("Body", value=note["body"])
        save_col, cancel_col = st.columns(2)
        save = save_col.form_submit_button("Save")
        cancel = cancel_col.form_submit_button("Cancel")
    if cancel:
        st.session_state.pop("editing_id", None)
        st.rerun()
    if save:
        if not title.strip():
            st.error("Title is required.")
            return
        ok, _ = call_api(
            "Could not update the note.",
            api_client.update_note,
            token,
            note["id"],
            title=title.strip(),
            status=status,
            importance=importance,
            body=body,
        )
        if ok:
            st.session_state.pop("editing_id", None)
            flash("Note updated.")
            st.rerun()


def render_list(token: str) -> None:
    st.subheader("All Notes")
    filters = _render_filters()
    ok, notes = call_api(
        "Could not load notes.", api_client.list_notes, token, **filters
    )
    if not ok:
        return
    if not notes:
        filtered = any(filters[k] for k in ("search", "status", "importance"))
        st.info("No notes match." if filtered else "No notes yet.")
    for note in notes:
        with st.container(border=True):
            if st.session_state.get("editing_id") == note["id"]:
                _render_edit_form(token, note)
                continue
            st.markdown(f"**{note['title']}**")
            st.caption(note_caption(note))
            if note["body"]:
                st.write(note["body"])
            edit_col, delete_col, _ = st.columns([1, 1, 4])
            if edit_col.button("Edit", key=f"edit_btn_{note['id']}"):
                st.session_state["editing_id"] = note["id"]
                st.rerun()
            if delete_col.button("Delete", key=f"delete_btn_{note['id']}"):
                ok, _ = call_api(
                    "Could not delete the note.",
                    api_client.delete_note,
                    token,
                    note["id"],
                )
                if ok:
                    flash("Note moved to trash.")
                    st.rerun()
