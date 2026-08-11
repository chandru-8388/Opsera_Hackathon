import json

import requests
import streamlit as st

st.set_page_config(page_title="Log Analyzer", layout="wide")

BACKEND_URL = "http://localhost:8000"


def is_valid_input(text: str) -> bool:
    return bool(text.strip())


def handle_http_error(response) -> None:
    if response.status_code == 422:
        st.error("The backend rejected the input. Please provide a valid, non-empty log snippet.")
        st.stop()
    elif response.status_code == 502:
        try:
            detail = response.json().get("detail", "Backend error.")
        except (json.JSONDecodeError, ValueError):
            detail = "Received an unexpected response from the backend. Please try again."
        st.error(detail)
        st.stop()
    else:
        try:
            detail = response.json().get("detail", f"Unexpected error (HTTP {response.status_code}).")
        except (json.JSONDecodeError, ValueError):
            detail = f"Unexpected error (HTTP {response.status_code}). Please try again."
        st.error(detail)
        st.stop()


def handle_network_error(exc) -> None:
    if isinstance(exc, requests.exceptions.ConnectionError):
        st.error(
            f"Cannot reach the backend at {BACKEND_URL}. "
            "Please ensure the FastAPI server is running."
        )
    elif isinstance(exc, requests.exceptions.Timeout):
        st.error(
            "The request timed out after 30 seconds. "
            "The log may be too large or the AI service may be slow. Please try again."
        )
    else:
        st.error("A network error occurred. Please try again.")
    st.stop()


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
    try:
        response = requests.post(
            f"{BACKEND_URL}/analyze",
            json={"log": log_text},
            timeout=30,
        )
        if response.status_code == 200:
            try:
                result = response.json()
            except (json.JSONDecodeError, ValueError):
                st.error("Received an unexpected response from the backend. Please try again.")
                st.stop()
            else:
                st.session_state["last_result"] = result
                st.session_state["last_log"] = log_text
        else:
            handle_http_error(response)
    except requests.exceptions.RequestException as exc:
        handle_network_error(exc)

if "last_result" in st.session_state:
    render_results(st.session_state["last_result"])
