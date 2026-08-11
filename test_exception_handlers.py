"""Unit tests for OpenAI exception handling in the POST /analyze endpoint (WO-011)."""

from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from openai import APIError, APITimeoutError, AuthenticationError, RateLimitError

from app import app

api_client = TestClient(app)

VALID_LOG = "java.lang.NullPointerException at OrderService.java:87"

# ── Mock exception fixtures ────────────────────────────────────────────────
# openai exceptions require a request object; use None for unit-test purposes.

def _timeout_error():
    return APITimeoutError(request=None)


def _rate_limit_error():
    return RateLimitError(
        message="Rate limit exceeded",
        response=None,
        body=None,
    )


def _auth_error():
    return AuthenticationError(
        message="Incorrect API key",
        response=None,
        body=None,
    )


def _api_error():
    return APIError(
        message="Internal server error",
        request=None,
        body=None,
    )


# ── Helper ─────────────────────────────────────────────────────────────────

def _post_with_exception(exc):
    """POST /analyze with analyze_log raising the given exception."""
    with patch("app.analyze_log", side_effect=exc):
        return api_client.post("/analyze", json={"log": VALID_LOG})


# ── Exception → 502 tests ──────────────────────────────────────────────────

def test_api_timeout_error_returns_502():
    response = _post_with_exception(_timeout_error())
    assert response.status_code == 502


def test_api_timeout_error_message():
    response = _post_with_exception(_timeout_error())
    assert response.json()["detail"] == (
        "OpenAI API timeout: the request exceeded the time limit. Please try again."
    )


def test_rate_limit_error_returns_502():
    response = _post_with_exception(_rate_limit_error())
    assert response.status_code == 502


def test_rate_limit_error_message():
    response = _post_with_exception(_rate_limit_error())
    assert response.json()["detail"] == (
        "Rate limit exceeded. Please wait a moment and try again."
    )


def test_authentication_error_returns_502():
    response = _post_with_exception(_auth_error())
    assert response.status_code == 502


def test_authentication_error_message():
    response = _post_with_exception(_auth_error())
    assert response.json()["detail"] == (
        "Authentication failed. Please verify your OpenAI API key."
    )


def test_api_error_returns_502():
    response = _post_with_exception(_api_error())
    assert response.status_code == 502


def test_api_error_message():
    response = _post_with_exception(_api_error())
    assert response.json()["detail"] == "OpenAI service error. Please try again later."


def test_unexpected_exception_returns_502():
    response = _post_with_exception(RuntimeError("something unexpected"))
    assert response.status_code == 502


def test_unexpected_exception_message():
    response = _post_with_exception(RuntimeError("something unexpected"))
    assert response.json()["detail"] == "An unexpected error occurred. Please try again."


# ── Security: no key/trace leakage ────────────────────────────────────────

@pytest.mark.parametrize("exc", [
    _timeout_error(),
    _rate_limit_error(),
    _auth_error(),
    _api_error(),
    RuntimeError("boom"),
])
def test_error_detail_contains_no_api_key(exc):
    response = _post_with_exception(exc)
    detail = response.json()["detail"]
    assert "sk-" not in detail


@pytest.mark.parametrize("exc", [
    _timeout_error(),
    _rate_limit_error(),
    _auth_error(),
    _api_error(),
    RuntimeError("boom"),
])
def test_error_detail_contains_no_traceback(exc):
    response = _post_with_exception(exc)
    detail = response.json()["detail"]
    assert "Traceback" not in detail
    assert "File \"" not in detail


# ── Ordering: specific exceptions caught before generic APIError ───────────

def test_timeout_not_swallowed_by_api_error():
    """APITimeoutError must produce its specific message, not the generic APIError one."""
    response = _post_with_exception(_timeout_error())
    assert "timeout" in response.json()["detail"].lower()
    assert "service error" not in response.json()["detail"].lower()


def test_rate_limit_not_swallowed_by_api_error():
    response = _post_with_exception(_rate_limit_error())
    assert "rate limit" in response.json()["detail"].lower()
    assert "service error" not in response.json()["detail"].lower()


def test_auth_error_not_swallowed_by_api_error():
    response = _post_with_exception(_auth_error())
    assert "authentication" in response.json()["detail"].lower()
    assert "service error" not in response.json()["detail"].lower()
