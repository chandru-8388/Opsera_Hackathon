"""Unit tests for dashboard.py API call and session state caching (WO-014)."""

import sys
from unittest.mock import MagicMock, patch

import pytest

# ── Mock response fixture matching AnalysisResponse schema ─────────────────

MOCK_ANALYSIS_RESPONSE = {
    "root_cause": (
        "NullPointerException in OrderService.validateShipping() at OrderService.java:87 "
        "caused by a null customer reference passed from processOrder()"
    ),
    "evidence": [
        "java.lang.NullPointerException: Cannot invoke \"Customer.getAddress()\" because \"customer\" is null",
        "Stack trace originates at OrderService.java:87 inside validateShipping()",
        "Order 98712 rolled back immediately after the exception at OrderService.java:54",
    ],
    "remediation_steps": [
        "Add a null check for customer before calling getAddress() in validateShipping()",
        "Verify that processOrder() handles missing customer records before invoking validateShipping()",
        "Add a unit test for OrderService.validateShipping() with a null customer argument",
    ],
}

LOG_SAMPLE = "java.lang.NullPointerException at OrderService.java:87\n  at processOrder(OrderService.java:54)"


def _run_dashboard(log_input, initial_session_state=None, status_code=200):
    """
    Re-import dashboard.py simulating a button click with the given log input.

    Uses a fresh sys.modules entry each call to re-execute module-level code.
    Returns (session_state dict, mock_post call tracker).
    """
    sys.modules.pop("dashboard", None)

    session_state = dict(initial_session_state or {})

    st_mock = MagicMock()
    st_mock.session_state = session_state
    st_mock.button.return_value = True
    st_mock.text_area.return_value = log_input

    mock_resp = MagicMock()
    mock_resp.status_code = status_code
    mock_resp.json.return_value = MOCK_ANALYSIS_RESPONSE

    with patch.dict(sys.modules, {"streamlit": st_mock}), \
         patch("requests.post", return_value=mock_resp) as mock_post:
        import dashboard  # noqa: F401

    return session_state, mock_post


# ── API call construction tests ────────────────────────────────────────────

def test_requests_post_called_with_correct_url():
    """POST target must be http://localhost:8000/analyze."""
    _, mock_post = _run_dashboard(LOG_SAMPLE)
    assert mock_post.called
    assert mock_post.call_args.args[0] == "http://localhost:8000/analyze"


def test_requests_post_called_with_correct_json_payload():
    """JSON body must contain the log field with the exact user-submitted text."""
    _, mock_post = _run_dashboard(LOG_SAMPLE)
    assert mock_post.call_args.kwargs["json"] == {"log": LOG_SAMPLE}


def test_requests_post_called_with_30_second_timeout():
    """Timeout must be exactly 30 seconds to handle slow LLM responses."""
    _, mock_post = _run_dashboard(LOG_SAMPLE)
    assert mock_post.call_args.kwargs["timeout"] == 30


# ── Session state storage tests ────────────────────────────────────────────

def test_result_stored_in_session_state_on_200():
    """HTTP 200 response JSON must be stored under 'last_result'."""
    session_state, _ = _run_dashboard(LOG_SAMPLE)
    assert "last_result" in session_state
    assert session_state["last_result"] == MOCK_ANALYSIS_RESPONSE


def test_log_text_stored_in_session_state_on_200():
    """Submitted log text must be stored under 'last_log' for cache invalidation."""
    session_state, _ = _run_dashboard(LOG_SAMPLE)
    assert session_state.get("last_log") == LOG_SAMPLE


def test_result_not_stored_when_status_not_200():
    """Non-200 responses must not update session state."""
    session_state, _ = _run_dashboard(LOG_SAMPLE, status_code=422)
    assert "last_result" not in session_state


# ── Cache invalidation tests ───────────────────────────────────────────────

def test_cache_invalidated_when_log_text_changes():
    """A new log submission replaces the cached result from a prior submission."""
    old_result = {"root_cause": "old", "evidence": [], "remediation_steps": []}
    initial = {"last_result": old_result, "last_log": "previous log text"}

    session_state, mock_post = _run_dashboard(LOG_SAMPLE, initial_session_state=initial)

    # API must have been called (not skipped due to cache)
    assert mock_post.called
    # Result must be the fresh response, not the old cached value
    assert session_state["last_result"] == MOCK_ANALYSIS_RESPONSE
    assert session_state["last_log"] == LOG_SAMPLE


def test_api_called_once_per_submission():
    """Exactly one POST request is made per button click."""
    _, mock_post = _run_dashboard(LOG_SAMPLE)
    assert mock_post.call_count == 1


# ── Mock fixture schema validation ────────────────────────────────────────

def test_mock_response_fixture_has_root_cause_string():
    assert isinstance(MOCK_ANALYSIS_RESPONSE["root_cause"], str)
    assert len(MOCK_ANALYSIS_RESPONSE["root_cause"]) > 0


def test_mock_response_fixture_has_evidence_list():
    assert isinstance(MOCK_ANALYSIS_RESPONSE["evidence"], list)
    assert len(MOCK_ANALYSIS_RESPONSE["evidence"]) > 0
    assert all(isinstance(e, str) for e in MOCK_ANALYSIS_RESPONSE["evidence"])


def test_mock_response_fixture_has_remediation_steps_list():
    assert isinstance(MOCK_ANALYSIS_RESPONSE["remediation_steps"], list)
    assert len(MOCK_ANALYSIS_RESPONSE["remediation_steps"]) > 0
    assert all(isinstance(s, str) for s in MOCK_ANALYSIS_RESPONSE["remediation_steps"])


def test_mock_response_fixture_has_all_required_keys():
    required_keys = {"root_cause", "evidence", "remediation_steps"}
    assert required_keys.issubset(MOCK_ANALYSIS_RESPONSE.keys())
