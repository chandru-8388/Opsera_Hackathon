"""Sanity tests for POST /analyze input validation (WO-018).

These tests verify that the Pydantic field_validator on LogRequest rejects
empty and whitespace-only submissions with HTTP 422. No OpenAI API call is
made — requests are rejected at the validation layer before any business logic.
"""

from fastapi.testclient import TestClient
from pydantic import ValidationError

from app import AnalysisResponse, app

client = TestClient(app)

# ── Fixtures ───────────────────────────────────────────────────────────────

EMPTY_LOG_FIXTURE = ""
WHITESPACE_LOG_FIXTURE = "   \t\n  "

VALID_LOG_FIXTURE = """\
2024-03-15 14:23:07.891 ERROR [main] c.e.s.OrderService - Failed to process order 98712
java.lang.NullPointerException: Cannot invoke "com.example.model.Customer.getAddress()" because "customer" is null
    at com.example.service.OrderService.validateShipping(OrderService.java:87)
    at com.example.service.OrderService.processOrder(OrderService.java:54)
    at com.example.controller.OrderController.submitOrder(OrderController.java:32)
    at sun.reflect.NativeMethodAccessorImpl.invoke0(Native Method)
    at sun.reflect.NativeMethodAccessorImpl.invoke(NativeMethodAccessorImpl.java:62)
    at sun.reflect.DelegatingMethodAccessorImpl.invoke(DelegatingMethodAccessorImpl.java:43)
    at java.lang.reflect.Method.invoke(Method.java:498)
Caused by: java.lang.IllegalStateException: Customer repository returned null for order 98712
    at com.example.repository.CustomerRepository.findById(CustomerRepository.java:34)
    at com.example.service.OrderService.loadCustomer(OrderService.java:112)
    ... 5 more
2024-03-15 14:23:07.892 WARN  [main] c.e.s.OrderService - Order 98712 rolled back due to unhandled exception
2024-03-15 14:23:07.893 INFO  [main] c.e.c.OrderController - Returning HTTP 500 to client for order 98712
"""


# ── Happy path: valid log returns 200 with schema-conformant response ─────

def test_analyze_valid_log_returns_200_with_schema():
    response = client.post("/analyze", json={"log": VALID_LOG_FIXTURE})
    assert response.status_code == 200
    data = response.json()
    result = AnalysisResponse(**data)
    assert isinstance(result.root_cause, str) and len(result.root_cause) > 0
    assert isinstance(result.evidence, list) and len(result.evidence) >= 1
    assert isinstance(result.remediation_steps, list) and len(result.remediation_steps) >= 1


def test_analyze_valid_log_response_has_required_keys():
    response = client.post("/analyze", json={"log": VALID_LOG_FIXTURE})
    assert response.status_code == 200
    data = response.json()
    assert "root_cause" in data
    assert "evidence" in data
    assert "remediation_steps" in data


def test_analyze_valid_log_evidence_items_are_strings():
    response = client.post("/analyze", json={"log": VALID_LOG_FIXTURE})
    data = response.json()
    result = AnalysisResponse(**data)
    assert all(isinstance(e, str) for e in result.evidence)


def test_analyze_valid_log_remediation_steps_are_strings():
    response = client.post("/analyze", json={"log": VALID_LOG_FIXTURE})
    data = response.json()
    result = AnalysisResponse(**data)
    assert all(isinstance(s, str) for s in result.remediation_steps)


def test_analyze_valid_log_pydantic_validates_without_error():
    response = client.post("/analyze", json={"log": VALID_LOG_FIXTURE})
    data = response.json()
    try:
        AnalysisResponse(**data)
    except ValidationError as exc:
        raise AssertionError(f"Response failed AnalysisResponse validation: {exc}") from exc


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
