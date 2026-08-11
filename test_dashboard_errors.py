"""Unit tests for dashboard.py error handling paths (WO-016)."""

import json
import sys
from unittest.mock import MagicMock, patch

import requests

LOG_SAMPLE = "ERROR: NullPointerException at Service.java:42"


def _run_dashboard_error(log_input, *, side_effect=None, status_code=None, json_body=None, json_raises=False):
    """Re-import dashboard simulating a button click with an error scenario."""
    sys.modules.pop("dashboard", None)

    session_state = {}
    st_mock = MagicMock()
    st_mock.session_state = session_state
    st_mock.button.return_value = True
    st_mock.text_area.return_value = log_input

    if side_effect is not None:
        post_kwargs = {"side_effect": side_effect}
    else:
        mock_resp = MagicMock()
        mock_resp.status_code = status_code
        if json_raises:
            mock_resp.json.side_effect = json.JSONDecodeError("No JSON object", "", 0)
        else:
            mock_resp.json.return_value = json_body if json_body is not None else {}
        post_kwargs = {"return_value": mock_resp}

    with patch.dict(sys.modules, {"streamlit": st_mock}), patch("requests.post", **post_kwargs):
        import dashboard  # noqa: F401

    return st_mock


# ── ConnectionError ────────────────────────────────────────────────────────

def test_connection_error_calls_st_error():
    st_mock = _run_dashboard_error(LOG_SAMPLE, side_effect=requests.exceptions.ConnectionError())
    assert st_mock.error.called


def test_connection_error_message_contains_backend_url():
    st_mock = _run_dashboard_error(LOG_SAMPLE, side_effect=requests.exceptions.ConnectionError())
    error_msg = st_mock.error.call_args[0][0]
    assert "localhost:8000" in error_msg


def test_connection_error_message_mentions_fastapi_server():
    st_mock = _run_dashboard_error(LOG_SAMPLE, side_effect=requests.exceptions.ConnectionError())
    error_msg = st_mock.error.call_args[0][0]
    assert "FastAPI server" in error_msg


def test_connection_error_calls_st_stop():
    st_mock = _run_dashboard_error(LOG_SAMPLE, side_effect=requests.exceptions.ConnectionError())
    assert st_mock.stop.called


def test_connection_error_does_not_expose_raw_exception():
    st_mock = _run_dashboard_error(
        LOG_SAMPLE, side_effect=requests.exceptions.ConnectionError("Connection refused to 127.0.0.1")
    )
    error_msg = st_mock.error.call_args[0][0]
    assert "Connection refused" not in error_msg
    assert "Traceback" not in error_msg


# ── Timeout ────────────────────────────────────────────────────────────────

def test_timeout_calls_st_error():
    st_mock = _run_dashboard_error(LOG_SAMPLE, side_effect=requests.exceptions.Timeout())
    assert st_mock.error.called


def test_timeout_message_mentions_30_seconds():
    st_mock = _run_dashboard_error(LOG_SAMPLE, side_effect=requests.exceptions.Timeout())
    error_msg = st_mock.error.call_args[0][0]
    assert "30 seconds" in error_msg


def test_timeout_calls_st_stop():
    st_mock = _run_dashboard_error(LOG_SAMPLE, side_effect=requests.exceptions.Timeout())
    assert st_mock.stop.called


def test_timeout_does_not_expose_raw_exception():
    st_mock = _run_dashboard_error(
        LOG_SAMPLE, side_effect=requests.exceptions.Timeout("Read timed out after 30s")
    )
    error_msg = st_mock.error.call_args[0][0]
    assert "Read timed out after 30s" not in error_msg


# ── HTTP 422 ───────────────────────────────────────────────────────────────

def test_http_422_calls_st_error():
    st_mock = _run_dashboard_error(LOG_SAMPLE, status_code=422, json_body={"detail": [{"msg": "value error"}]})
    assert st_mock.error.called


def test_http_422_message_mentions_valid_input():
    st_mock = _run_dashboard_error(LOG_SAMPLE, status_code=422, json_body={"detail": [{"msg": "value error"}]})
    error_msg = st_mock.error.call_args[0][0]
    assert "valid" in error_msg.lower()


def test_http_422_calls_st_stop():
    st_mock = _run_dashboard_error(LOG_SAMPLE, status_code=422, json_body={"detail": [{"msg": "value error"}]})
    assert st_mock.stop.called


# ── HTTP 502 ───────────────────────────────────────────────────────────────

def test_http_502_displays_detail_from_response():
    detail = "OpenAI API timeout: the request exceeded the time limit. Please try again."
    st_mock = _run_dashboard_error(LOG_SAMPLE, status_code=502, json_body={"detail": detail})
    error_msg = st_mock.error.call_args[0][0]
    assert error_msg == detail


def test_http_502_calls_st_stop():
    st_mock = _run_dashboard_error(LOG_SAMPLE, status_code=502, json_body={"detail": "some error"})
    assert st_mock.stop.called


def test_http_502_with_invalid_json_shows_generic_message():
    st_mock = _run_dashboard_error(LOG_SAMPLE, status_code=502, json_raises=True)
    error_msg = st_mock.error.call_args[0][0]
    assert "unexpected" in error_msg.lower() or "try again" in error_msg.lower()


# ── Unexpected status code ─────────────────────────────────────────────────

def test_unexpected_status_code_calls_st_error():
    st_mock = _run_dashboard_error(LOG_SAMPLE, status_code=500, json_body={})
    assert st_mock.error.called


def test_unexpected_status_code_calls_st_stop():
    st_mock = _run_dashboard_error(LOG_SAMPLE, status_code=500, json_body={})
    assert st_mock.stop.called


def test_unexpected_status_code_503_calls_st_error():
    st_mock = _run_dashboard_error(LOG_SAMPLE, status_code=503, json_body={})
    assert st_mock.error.called


# ── HTTP 200 with malformed JSON body ──────────────────────────────────────

def test_200_with_invalid_json_calls_st_error():
    st_mock = _run_dashboard_error(LOG_SAMPLE, status_code=200, json_raises=True)
    assert st_mock.error.called


def test_200_with_invalid_json_shows_generic_message():
    st_mock = _run_dashboard_error(LOG_SAMPLE, status_code=200, json_raises=True)
    error_msg = st_mock.error.call_args[0][0]
    assert "unexpected" in error_msg.lower() or "try again" in error_msg.lower()


def test_200_with_invalid_json_calls_st_stop():
    st_mock = _run_dashboard_error(LOG_SAMPLE, status_code=200, json_raises=True)
    assert st_mock.stop.called
