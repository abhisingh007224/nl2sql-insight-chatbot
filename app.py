"""Streamlit chatbot UI.

Usage:  uv run streamlit run app.py
"""

import os

import streamlit as st

from api_key_manager import active_api_key, render_api_key_manager
from nl2sql.answerer import compose_response
from nl2sql.config import MIN_SIMILARITY, gemini_api_key
from nl2sql.pipeline import GENERATED_ID, ChatResult, NL2SQLPipeline

st.set_page_config(page_title="Northwind Insight Chatbot", page_icon="📊", layout="wide")

# Streamlit Community Cloud / HF Spaces supply secrets via st.secrets rather than .env.
try:
    if "GEMINI_API_KEY" in st.secrets and not gemini_api_key():
        os.environ["GEMINI_API_KEY"] = st.secrets["GEMINI_API_KEY"]
except Exception:  # no secrets.toml present
    pass


@st.cache_resource(show_spinner="Loading embedding model and query index...")
def get_pipeline() -> NL2SQLPipeline:
    return NL2SQLPipeline()


def render_result(result: ChatResult) -> None:
    if result.answer.source == "guardrail":
        st.error(result.answer.text)
        return
    st.markdown(result.answer.text)
    if result.data is not None and not result.data.empty:
        st.caption("Source data (exact query output)")
        st.dataframe(
            result.data.style.format(precision=2, thousands=","), hide_index=True, use_container_width=True
        )
        if result.data.attrs.get("truncated"):
            st.caption(f"Showing the first {len(result.data):,} rows.")
    if result.answer.unverified_numbers:
        st.warning(
            "These numbers in the answer were not found in the query result: "
            + ", ".join(result.answer.unverified_numbers)
            + ". Trust the table above."
        )
    if result.answer.note:
        st.caption(result.answer.note)
    if result.record is None:
        return
    generated = result.record.query_id == GENERATED_ID
    chosen = result.chosen_match
    if generated:
        label = "How I answered: AI-generated SQL (no vetted query fitted)"
    else:
        label = f"How I answered: vetted query `{result.record.query_id}`"
        if chosen:
            label += f" (similarity {chosen.score:.2f})"
    with st.expander(label):
        if generated:
            st.info(
                "No query in the vetted repository answered this exactly, so Gemini wrote the SQL below from the "
                "database schema. It passed the read-only guardrails (SQL validation, read-only connection, "
                "time limit) before running."
            )
        else:
            st.markdown(f"**Query description:** {result.record.description}")
            if chosen:
                st.markdown(f"**Closest indexed phrasing:** _{chosen.matched_text}_")
        st.code(result.record.sql, language="sql")
        if result.matches:
            st.markdown("**Semantic search candidates**")
            st.dataframe(
                [{"query_id": m.query_id, "similarity": round(m.score, 3)} for m in result.matches],
                hide_index=True,
            )
        st.caption(f"Answer written by: {result.answer.source}")


pipeline = get_pipeline()

if "messages" not in st.session_state:
    st.session_state.messages = []  # list of {"role": ..., "content": str | ChatResult}

with st.sidebar:
    st.header("Northwind Insight Chatbot")
    st.markdown(
        "Ask business questions in plain English. Your question is matched **by meaning** to a vetted SQL query, "
        "the query runs on the Northwind database, and the result is explained in natural language. "
        "If no vetted query fits, Gemini writes a new **read-only** SQL query instead."
    )
    render_api_key_manager()
    st.caption(f"Match threshold: {MIN_SIMILARITY:.2f} cosine similarity")

    st.subheader("Try asking")
    for record in pipeline.repo.values():
        if st.button(record.sample_questions[0], key=f"ex_{record.query_id}", use_container_width=True):
            st.session_state.pending_question = record.sample_questions[0]

    if st.button("Clear conversation", type="primary", use_container_width=True):
        st.session_state.messages = []
        st.rerun()

st.title("📊 Ask Northwind")

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        # Check for str rather than ChatResult: a module hot-reload creates a new ChatResult class.
        if isinstance(message["content"], str):
            st.markdown(message["content"])
        else:
            render_result(message["content"])

question = st.chat_input("e.g. Which customer spent the most?")
question = question or st.session_state.pop("pending_question", None)

if question:
    history = [
        (m["role"], m["content"] if isinstance(m["content"], str) else compose_response(m["content"].answer, None))
        for m in st.session_state.messages
    ]
    st.session_state.messages.append({"role": "user", "content": question})
    with st.chat_message("user"):
        st.markdown(question)

    with st.chat_message("assistant"):
        with st.spinner("Finding the right query and analysing the result..."):
            result = pipeline.ask(question, history, api_key=active_api_key())
        render_result(result)
    st.session_state.messages.append({"role": "assistant", "content": result})
