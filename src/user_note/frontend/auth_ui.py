import httpx
import streamlit as st

from user_note.frontend import api_client


def _sign_in(username: str, password: str) -> None:
    try:
        token = api_client.login(username, password)
        st.session_state["token"] = token
        st.session_state["username"] = api_client.me(token)["username"]
        st.rerun()
    except api_client.APIError as e:
        st.error(str(e))
    except httpx.HTTPError:
        st.error("Could not reach the API.")


def render() -> None:
    sign_in_tab, sign_up_tab = st.tabs(["Sign In", "Sign Up"])

    with sign_in_tab:
        with st.form("sign_in"):
            username = st.text_input("Username")
            password = st.text_input("Password", type="password")
            if st.form_submit_button("Sign In"):
                _sign_in(username.strip(), password)

    with sign_up_tab:
        with st.form("sign_up"):
            username = st.text_input("Username", max_chars=50)
            password = st.text_input("Password", type="password")
            confirm = st.text_input("Confirm Password", type="password")
            if st.form_submit_button("Create Account"):
                if password != confirm:
                    st.error("Passwords do not match.")
                else:
                    try:
                        api_client.register(username.strip(), password)
                    except api_client.APIError as e:
                        st.error(str(e))
                    except httpx.HTTPError:
                        st.error("Could not reach the API.")
                    else:
                        _sign_in(username.strip(), password)
