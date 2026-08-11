import streamlit as st
import requests

st.set_page_config(page_title="Log Analyzer", layout="wide")

BACKEND_URL = "http://localhost:8000"


def is_valid_input(text: str) -> bool:
    """Return True if text contains non-whitespace content."""
    return bool(text.strip())


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
