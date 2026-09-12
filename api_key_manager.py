"""Sidebar widget that lets a visitor use their own Gemini API key while the app is running.

The key lives only in st.session_state (this one browser session) and is passed explicitly with each
Gemini call. It is never written to os.environ, disk or logs: on a shared deployment every visitor
runs in the same Python process, so an environment variable would leak one visitor's key to all others.
"""

import streamlit as st

from nl2sql.config import GEMINI_MODEL, gemini_api_key
from nl2sql.llm import verify_api_key

_SESSION_KEY = "user_gemini_api_key"


def session_api_key() -> str | None:
    return st.session_state.get(_SESSION_KEY)


def active_api_key() -> str | None:
    """The visitor's own key if they entered one, otherwise the app's key (Streamlit secrets / .env)."""
    return session_api_key() or gemini_api_key()


def render_api_key_manager() -> None:
    st.subheader("Gemini API key")

    user_key = session_api_key()
    if user_key:
        st.success(f"Using your key (…{user_key[-4:]}) for this session. Model: {GEMINI_MODEL}")
        if st.button("Remove my key", use_container_width=True):
            del st.session_state[_SESSION_KEY]
            st.rerun()
        return

    app_has_key = bool(gemini_api_key())
    if app_has_key:
        st.success(f"LLM: {GEMINI_MODEL} (app key)")
    else:
        st.warning("No Gemini API key yet - answers are template-based and only vetted queries can be used.")

    with st.expander("Use your own key" if app_has_key else "Add your Gemini API key", expanded=not app_has_key):
        with st.form("api_key_form", clear_on_submit=True):
            key = st.text_input(
                "API key",
                type="password",
                placeholder="Paste your Gemini API key",
                help="Get a free key at https://aistudio.google.com/apikey",
            )
            submitted = st.form_submit_button("Save key", use_container_width=True)
        st.caption("Kept only in this browser session's memory - never saved to disk or shared with other visitors.")

    if submitted:
        key = key.strip()
        if not key:
            st.error("Paste a key first.")
            return
        with st.spinner("Checking the key..."):
            error = verify_api_key(key)
        if error:
            st.error(f"That key didn't work: {error}")
            return
        st.session_state[_SESSION_KEY] = key
        st.rerun()
