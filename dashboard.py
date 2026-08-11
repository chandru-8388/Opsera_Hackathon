import streamlit as st
import requests

st.set_page_config(page_title="Log Analyzer", layout="wide")

BACKEND_URL = "http://localhost:8000"


def is_valid_input(text: str) -> bool:
    """Return True if text contains non-whitespace content."""
    return bool(text.strip())


def render_results(result: dict) -> None:
    st.subheader("Root Cause")
    st.markdown(result["root_cause"])
    st.subheader("Evidence")
    for item in result["evidence"]:
        st.markdown(f"- {item}")
    st.subheader("Remediation Steps")
    for i, step in enumerate(result["remediation_steps"], 1):
        st.markdown(f"{i}. {step}")


st.title("AI Log Analyzer")

log_text = st.text_area(
    "Paste your failure log",
    height=200,
    placeholder="Paste a stack trace, error log, or failure output...",
)

if st.button("Analyze"):
    if not is_valid_input(log_text):
        st.warning("Please paste a log snippet")
        st.stop()
    if log_text != st.session_state.get("last_log", ""):
        st.session_state.pop("last_result", None)
    response = requests.post(
        f"{BACKEND_URL}/analyze",
        json={"log": log_text},
        timeout=30,
    )
    if response.status_code == 200:
        result = response.json()
        st.session_state["last_result"] = result
        st.session_state["last_log"] = log_text

if "last_result" in st.session_state:
    render_results(st.session_state["last_result"])
