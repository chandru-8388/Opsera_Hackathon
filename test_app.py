"""Sanity tests for POST /analyze input validation (WO-018).

These tests verify that the Pydantic field_validator on LogRequest rejects
empty and whitespace-only submissions with HTTP 422. No OpenAI API call is
made — requests are rejected at the validation layer before any business logic.
"""

from fastapi.testclient import TestClient

from app import app

client = TestClient(app)

# ── Fixtures ───────────────────────────────────────────────────────────────

EMPTY_LOG_FIXTURE = ""
WHITESPACE_LOG_FIXTURE = "   \t\n  "


# ── Empty / whitespace validation tests ───────────────────────────────────

def test_analyze_empty_log_returns_422():
    response = client.post("/analyze", json={"log": EMPTY_LOG_FIXTURE})
    assert response.status_code == 422
    detail = response.json()["detail"]
    assert any("Log snippet must not be empty" in str(e) for e in detail)


def test_analyze_whitespace_log_returns_422():
    response = client.post("/analyze", json={"log": WHITESPACE_LOG_FIXTURE})
    assert response.status_code == 422
    detail = response.json()["detail"]
    assert any("Log snippet must not be empty" in str(e) for e in detail)


# ── Edge cases ─────────────────────────────────────────────────────────────

def test_analyze_newline_only_returns_422():
    response = client.post("/analyze", json={"log": "\n"})
    assert response.status_code == 422


def test_analyze_single_space_returns_422():
    response = client.post("/analyze", json={"log": " "})
    assert response.status_code == 422


def test_analyze_missing_log_field_returns_422():
    response = client.post("/analyze", json={})
    assert response.status_code == 422


def test_analyze_null_log_field_returns_422():
    response = client.post("/analyze", json={"log": None})
    assert response.status_code == 422


def test_422_response_contains_detail_field():
    response = client.post("/analyze", json={"log": EMPTY_LOG_FIXTURE})
    assert response.status_code == 422
    body = response.json()
    assert "detail" in body
    assert isinstance(body["detail"], list)
    assert len(body["detail"]) > 0
