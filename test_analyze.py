"""Unit and integration tests for the real analyze_log function (WO-010)."""

import os
from unittest.mock import MagicMock, patch

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from app import AnalysisResponse, analyze_log, app

api_client = TestClient(app)

# ── Mock OpenAI response fixture ───────────────────────────────────────────

MOCK_PARSED = AnalysisResponse(
    root_cause=(
        "NullPointerException in OrderService.validateShipping() at OrderService.java:87 "
        "caused by a null customer reference passed from processOrder()"
    ),
    evidence=[
        "java.lang.NullPointerException: Cannot invoke \"Customer.getAddress()\" because \"customer\" is null",
        "Stack trace originates at OrderService.java:87 inside validateShipping()",
        "Order 98712 rolled back immediately after the exception at OrderService.java:54",
    ],
    remediation_steps=[
        "Add a null check for customer before calling getAddress() in validateShipping()",
        "Verify that processOrder() handles missing customer records before invoking validateShipping()",
        "Add a unit test for OrderService.validateShipping() with a null customer argument",
    ],
)


def _make_completion(parsed=None, refusal=None):
    """Return a mock OpenAI completion matching the beta.parse() response shape."""
    message = MagicMock()
    message.parsed = parsed if parsed is not None else MOCK_PARSED
    message.refusal = refusal
    choice = MagicMock()
    choice.message = message
    completion = MagicMock()
    completion.choices = [choice]
    return completion


# ── Unit tests: mocked OpenAI client ──────────────────────────────────────
#
# These tests import analyze_log directly (a reference to the original function
# object). The autouse _auto_mock_openai_client fixture in conftest.py patches
# app.client at the module level. Each test overrides that with an inner
# ``with patch("app.client")`` to control the exact completion shape.

def test_analyze_log_successful_parse_returns_analysis_response():
    with patch("app.client") as mock_client:
        mock_client.beta.chat.completions.parse.return_value = _make_completion()
        result = analyze_log("java.lang.NullPointerException at OrderService.java:87")
    assert isinstance(result, AnalysisResponse)
    assert result.root_cause == MOCK_PARSED.root_cause
    assert result.evidence == MOCK_PARSED.evidence
    assert result.remediation_steps == MOCK_PARSED.remediation_steps


def test_analyze_log_calls_gpt4o_mini():
    with patch("app.client") as mock_client:
        mock_client.beta.chat.completions.parse.return_value = _make_completion()
        analyze_log("some log text")
    assert mock_client.beta.chat.completions.parse.call_args.kwargs["model"] == "gpt-4o-mini"


def test_analyze_log_sends_system_prompt_as_first_message():
    from app import SYSTEM_PROMPT
    with patch("app.client") as mock_client:
        mock_client.beta.chat.completions.parse.return_value = _make_completion()
        analyze_log("ERROR: connection refused")
    messages = mock_client.beta.chat.completions.parse.call_args.kwargs["messages"]
    assert messages[0]["role"] == "system"
    assert messages[0]["content"] == SYSTEM_PROMPT


def test_analyze_log_sends_log_text_as_user_message():
    log_text = "FATAL: disk I/O error on /dev/sda1"
    with patch("app.client") as mock_client:
        mock_client.beta.chat.completions.parse.return_value = _make_completion()
        analyze_log(log_text)
    messages = mock_client.beta.chat.completions.parse.call_args.kwargs["messages"]
    assert messages[1]["role"] == "user"
    assert messages[1]["content"] == log_text


def test_analyze_log_uses_analysis_response_as_response_format():
    with patch("app.client") as mock_client:
        mock_client.beta.chat.completions.parse.return_value = _make_completion()
        analyze_log("some log")
    assert mock_client.beta.chat.completions.parse.call_args.kwargs["response_format"] is AnalysisResponse


def test_analyze_log_refusal_raises_http_502():
    with patch("app.client") as mock_client:
        mock_client.beta.chat.completions.parse.return_value = _make_completion(
            parsed=None, refusal="I cannot analyze this content."
        )
        with pytest.raises(HTTPException) as exc_info:
            analyze_log("some log")
    assert exc_info.value.status_code == 502
    assert "refused" in exc_info.value.detail.lower()


def test_analyze_log_none_parsed_raises_http_502():
    with patch("app.client") as mock_client:
        # refusal is None but parsed is also None — defensive path
        mock_client.beta.chat.completions.parse.return_value = _make_completion(
            parsed=None, refusal=None
        )
        with pytest.raises(HTTPException) as exc_info:
            analyze_log("some log")
    assert exc_info.value.status_code == 502


def test_analyze_log_single_call_per_request():
    with patch("app.client") as mock_client:
        mock_client.beta.chat.completions.parse.return_value = _make_completion()
        analyze_log("some log")
    assert mock_client.beta.chat.completions.parse.call_count == 1


# ── HTTP endpoint tests (mocked client) ───────────────────────────────────

def test_analyze_endpoint_200_with_mocked_client():
    with patch("app.client") as mock_client:
        mock_client.beta.chat.completions.parse.return_value = _make_completion()
        response = api_client.post(
            "/analyze", json={"log": "java.lang.NullPointerException at Main.java:42"}
        )
    assert response.status_code == 200
    data = response.json()
    assert "root_cause" in data
    assert "evidence" in data
    assert "remediation_steps" in data


def test_analyze_endpoint_502_on_refusal():
    with patch("app.client") as mock_client:
        mock_client.beta.chat.completions.parse.return_value = _make_completion(
            parsed=None, refusal="Content policy violation."
        )
        response = api_client.post("/analyze", json={"log": "some log"})
    assert response.status_code == 502
    assert "detail" in response.json()


# ── Live integration test (opt-in only) ───────────────────────────────────

@pytest.mark.skipif(
    not os.environ.get("RUN_INTEGRATION_TESTS"),
    reason="Set RUN_INTEGRATION_TESTS=1 with a real OPENAI_API_KEY to run",
)
def test_analyze_log_live_end_to_end():
    """Real API call — verifies the full pipeline with GPT-4o-mini."""
    from test_fixtures import HERO_SNIPPET
    result = analyze_log(HERO_SNIPPET)
    assert isinstance(result, AnalysisResponse)
    assert isinstance(result.root_cause, str) and len(result.root_cause) > 10
    assert isinstance(result.evidence, list) and len(result.evidence) >= 1
    assert isinstance(result.remediation_steps, list) and len(result.remediation_steps) >= 1
