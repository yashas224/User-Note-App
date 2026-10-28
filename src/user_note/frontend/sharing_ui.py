import streamlit as st

from user_note.frontend import api_client
from user_note.frontend.common import call_api, flash

EXPIRY_OPTIONS = {"1 day": 1, "7 days": 7, "30 days": 30, "Never": None}


def _share_status(share: dict) -> str:
    if share["revoked_at"]:
        return "Revoked"
    return "Active" if share["is_active"] else "Expired"


def render(token: str) -> None:
    st.subheader("Manage Sharing")
    ok, notes = call_api(
        "Could not load notes.", api_client.list_notes, token, limit=100
    )
    if not ok:
        return
    if not notes:
        st.info("Create a note first to share it.")
        return

    by_id = {n["id"]: n for n in notes}
    note_id = st.selectbox("Note", list(by_id), format_func=lambda i: by_id[i]["title"])

    st.warning(
        "Anyone with a sharing link can view this note without signing in, "
        "until the link expires or you revoke it."
    )
    with st.form("create_share"):
        expiry = st.selectbox("Expires after", list(EXPIRY_OPTIONS), index=1)
        if st.form_submit_button("Create sharing link"):
            ok, share = call_api(
                "Could not create the link.",
                api_client.create_share,
                token,
                note_id,
                EXPIRY_OPTIONS[expiry],
            )
            if ok:
                st.session_state["new_share"] = (note_id, share["share_url"])

    new_share = st.session_state.get("new_share")
    if new_share and new_share[0] == note_id:
        st.success("Link created. Copy it now: it won't be shown again.")
        st.code(new_share[1], language=None)

    ok, shares = call_api(
        "Could not load sharing links.", api_client.list_shares, token, note_id
    )
    if not ok:
        return
    st.markdown("**Links for this note**")
    if not shares:
        st.caption("No links yet.")
    for share in shares:
        status = _share_status(share)
        col1, col2, col3 = st.columns([2, 4, 1])
        col1.write(status)
        col2.caption(
            f"created {share['created_at']} · expires {share['expires_at'] or 'never'}"
        )
        if status == "Active" and col3.button("Revoke", key=f"revoke_{share['id']}"):
            ok, _ = call_api(
                "Could not revoke the link.",
                api_client.revoke_share,
                token,
                note_id,
                share["id"],
            )
            if ok:
                flash("Link revoked.")
                st.rerun()
