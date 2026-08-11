"""Sanity tests for POST /analyze input validation (WO-018).

These tests verify that the Pydantic field_validator on LogRequest rejects
empty and whitespace-only submissions with HTTP 422. No OpenAI API call is
made — requests are rejected at the validation layer before any business logic.
"""

import re
import time
from pathlib import Path

import pytest
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


# ── Quality validation fixtures (WO-019) ──────────────────────────────────

JAVA_STACK_TRACE_FIXTURE = """\
2024-04-02 09:15:33.412 ERROR [http-nio-8080-exec-3] c.e.p.PaymentService - Payment processing failed for transaction TXN-20240402-8847
java.lang.NullPointerException: Cannot invoke "com.example.model.PaymentMethod.getToken()" because "paymentMethod" is null
    at com.example.payment.PaymentService.chargeCard(PaymentService.java:143)
    at com.example.payment.PaymentService.processPayment(PaymentService.java:89)
    at com.example.api.PaymentController.createCharge(PaymentController.java:56)
    at sun.reflect.NativeMethodAccessorImpl.invoke0(Native Method)
    at sun.reflect.NativeMethodAccessorImpl.invoke(NativeMethodAccessorImpl.java:62)
    at java.lang.reflect.Method.invoke(Method.java:498)
    at org.springframework.web.servlet.FrameworkServlet.processRequest(FrameworkServlet.java:1014)
Caused by: java.lang.IllegalStateException: PaymentMethod not found for userId=44219
    at com.example.repository.PaymentRepository.findActiveByUserId(PaymentRepository.java:67)
    at com.example.payment.PaymentService.loadPaymentMethod(PaymentService.java:201)
    ... 8 more
2024-04-02 09:15:33.413 WARN  [http-nio-8080-exec-3] c.e.p.PaymentService - Transaction TXN-20240402-8847 marked FAILED; no charge issued
2024-04-02 09:15:33.414 ERROR [http-nio-8080-exec-3] c.e.a.PaymentController - Returning HTTP 500 for userId=44219
"""

TIMEOUT_ERROR_FIXTURE = """\
2024-04-02 11:42:01.001 INFO  [worker-7] c.e.d.DatabasePool - Acquiring connection from pool (size=10, active=10, idle=0)
2024-04-02 11:42:01.002 WARN  [worker-7] c.e.d.DatabasePool - All 10 pool connections in use; waiting up to 5000ms
2024-04-02 11:42:06.003 ERROR [worker-7] c.e.d.DatabasePool - Timed out waiting for database connection after 5000ms
    com.zaxxer.hikari.pool.HikariPool$PoolInitializationException: Connection is not available, request timed out after 5000ms
        at com.zaxxer.hikari.pool.HikariPool.getConnection(HikariPool.java:213)
        at com.zaxxer.hikari.HikariDataSource.getConnection(HikariDataSource.java:128)
        at com.example.service.ReportService.generateReport(ReportService.java:78)
        at com.example.scheduler.ReportScheduler.runDailyReport(ReportScheduler.java:45)
2024-04-02 11:42:06.004 ERROR [worker-7] c.e.s.ReportService - Failed to generate daily report: connection pool exhausted
2024-04-02 11:42:06.005 WARN  [worker-7] c.e.s.ReportService - Retry 1/3 in 2000ms
2024-04-02 11:42:08.006 ERROR [worker-7] c.e.s.ReportService - Retry 1 failed: pool still exhausted
2024-04-02 11:42:08.007 ERROR [scheduler] c.e.s.ReportScheduler - Daily report ABORTED after 3 retries; manual intervention required
"""

PERMISSION_ERROR_FIXTURE = """\
2024-04-02 22:05:11.000 INFO  [deploy-agent] pipeline.deploy - Starting deployment to prod-app-01 as user deploy
2024-04-02 22:05:11.201 ERROR [deploy-agent] pipeline.deploy - Failed to write to /var/app/releases/20240402-220511
    java.io.IOException: Permission denied
        at sun.nio.ch.FileChannelImpl.open0(Native Method)
        at sun.nio.ch.FileChannelImpl.open(FileChannelImpl.java:105)
        at com.example.deploy.ReleaseManager.createRelease(ReleaseManager.java:88)
        at com.example.deploy.DeployAgent.deploy(DeployAgent.java:134)
2024-04-02 22:05:11.202 WARN  [deploy-agent] pipeline.deploy - deploy user lacks write permission on /var/app/releases (owner: root, mode: 755)
2024-04-02 22:05:11.203 ERROR [deploy-agent] pipeline.deploy - Deployment FAILED: cannot create release directory
2024-04-02 22:05:11.204 INFO  [deploy-agent] pipeline.audit - Audit: user=deploy action=DEPLOY target=prod-app-01 result=PERMISSION_DENIED
2024-04-02 22:05:11.205 WARN  [ops-monitor] system.monitor - Deployment pipeline failure detected; alerting on-call via PagerDuty
"""


# ── Hero snippet for live demo (WO-020) ───────────────────────────────────
#
# Selected: JAVA_STACK_TRACE_FIXTURE (payment service NullPointerException)
#
# Rationale: The payment NPE produces the most specific and impressive analysis
# of the three fixtures. It contains a clear causal chain (NPE at chargeCard →
# Caused By IllegalStateException at PaymentRepository.findActiveByUserId),
# a unique transaction ID (TXN-20240402-8847) and user ID (userId=44219) that
# the LLM cites verbatim as evidence, and a business-critical domain (payments)
# that resonates with any demo audience. At 15 lines it is quick to paste and
# the multi-level stack trace gives GPT-4o-mini rich context to produce
# actionable, non-generic remediation steps.

HERO_LOG_SNIPPET = """\
2024-04-02 09:15:33.412 ERROR [http-nio-8080-exec-3] c.e.p.PaymentService - Payment processing failed for transaction TXN-20240402-8847
java.lang.NullPointerException: Cannot invoke "com.example.model.PaymentMethod.getToken()" because "paymentMethod" is null
    at com.example.payment.PaymentService.chargeCard(PaymentService.java:143)
    at com.example.payment.PaymentService.processPayment(PaymentService.java:89)
    at com.example.api.PaymentController.createCharge(PaymentController.java:56)
    at sun.reflect.NativeMethodAccessorImpl.invoke0(Native Method)
    at sun.reflect.NativeMethodAccessorImpl.invoke(NativeMethodAccessorImpl.java:62)
    at java.lang.reflect.Method.invoke(Method.java:498)
    at org.springframework.web.servlet.FrameworkServlet.processRequest(FrameworkServlet.java:1014)
Caused by: java.lang.IllegalStateException: PaymentMethod not found for userId=44219
    at com.example.repository.PaymentRepository.findActiveByUserId(PaymentRepository.java:67)
    at com.example.payment.PaymentService.loadPaymentMethod(PaymentService.java:201)
    ... 8 more
2024-04-02 09:15:33.413 WARN  [http-nio-8080-exec-3] c.e.p.PaymentService - Transaction TXN-20240402-8847 marked FAILED; no charge issued
2024-04-02 09:15:33.414 ERROR [http-nio-8080-exec-3] c.e.a.PaymentController - Returning HTTP 500 for userId=44219
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


# ── LLM output quality across three log types (WO-019) ────────────────────

@pytest.mark.parametrize("log_fixture,label", [
    (JAVA_STACK_TRACE_FIXTURE, "java_npe"),
    (TIMEOUT_ERROR_FIXTURE, "timeout"),
    (PERMISSION_ERROR_FIXTURE, "permission_denied"),
])
def test_analyze_quality_across_log_types(log_fixture, label):
    response = client.post("/analyze", json={"log": log_fixture})
    assert response.status_code == 200
    data = response.json()
    result = AnalysisResponse(**data)
    print(f"\n[{label}] root_cause: {result.root_cause}")
    assert len(result.root_cause) >= 20, f"[{label}] root_cause too short: {result.root_cause!r}"
    assert len(result.evidence) >= 2, f"[{label}] expected >= 2 evidence items, got {len(result.evidence)}"
    assert len(result.remediation_steps) >= 2, f"[{label}] expected >= 2 remediation steps, got {len(result.remediation_steps)}"


# ── Hero snippet consistency test (WO-020) ────────────────────────────────

def test_hero_snippet_quality():
    for run in range(1, 4):
        response = client.post("/analyze", json={"log": HERO_LOG_SNIPPET})
        assert response.status_code == 200, f"[run {run}] expected 200, got {response.status_code}"
        data = response.json()
        result = AnalysisResponse(**data)
        print(f"\n[run {run}] root_cause: {result.root_cause}")
        print(f"[run {run}] evidence[0]: {result.evidence[0]}")
        assert len(result.root_cause) >= 30, (
            f"[run {run}] root_cause too short ({len(result.root_cause)} chars): {result.root_cause!r}"
        )
        assert len(result.evidence) >= 2, (
            f"[run {run}] expected >= 2 evidence items, got {len(result.evidence)}"
        )
        assert len(result.remediation_steps) >= 2, (
            f"[run {run}] expected >= 2 remediation steps, got {len(result.remediation_steps)}"
        )


# ── End-to-end round-trip latency test (WO-021) ───────────────────────────

def test_analyze_round_trip_under_15_seconds():
    start = time.time()
    response = client.post("/analyze", json={"log": HERO_LOG_SNIPPET})
    elapsed = time.time() - start
    print(f"\nRound-trip latency: {elapsed:.2f}s")
    assert response.status_code == 200, f"Expected HTTP 200, got {response.status_code}"
    data = response.json()
    result = AnalysisResponse(**data)
    assert len(result.root_cause) > 0, "root_cause must not be empty"
    assert len(result.evidence) >= 1, "evidence list must not be empty"
    assert len(result.remediation_steps) >= 1, "remediation_steps list must not be empty"
    assert elapsed < 15.0, (
        f"Round-trip took {elapsed:.2f}s, exceeding the 15s latency budget"
    )


# ── Manual E2E verification checklist ─────────────────────────────────────
#
# Run this checklist once before each live demo with both services running
# and a real OPENAI_API_KEY set.
#
#  1. Terminal 1 — start FastAPI backend:
#       uvicorn app:app --reload
#     Confirm: "Application startup complete" and no KeyError for OPENAI_API_KEY
#
#  2. Terminal 2 — start Streamlit frontend:
#       streamlit run dashboard.py
#     Confirm: browser opens to http://localhost:8501
#
#  3. In the browser, verify the page title "AI Log Analyzer" and text area
#     placeholder text are visible.
#
#  4. Paste the HERO_LOG_SNIPPET (payment service NPE above) into the text area.
#
#  5. Click the "Analyze" button and start a stopwatch.
#
#  6. Verify a "Root Cause" subheader appears with a specific, non-generic
#     description that references PaymentService or PaymentMethod.
#
#  7. Verify an "Evidence" subheader appears with a bulleted list of at least
#     2 items that cite actual log content (class names, line numbers, or the
#     transaction ID TXN-20240402-8847).
#
#  8. Verify a "Remediation Steps" subheader appears with a numbered list of
#     at least 2 actionable steps (not generic advice).
#
#  9. Stop the stopwatch when results are fully rendered.
#     Target: total time from click to rendered results < 15 seconds.
#
# 10. Repeat steps 4–9 twice more to confirm consistency across 3 runs.
#     All 3 runs must complete under 15 seconds with non-empty, specific output.


# ── Security posture tests (WO-022) ───────────────────────────────────────

# Source files in the production 3-file constraint.
_SOURCE_FILES = [Path("app.py"), Path("dashboard.py"), Path("requirements.txt")]

# Matches a quoted OpenAI API key (real keys are 51+ chars; 20 is a safe lower bound
# that avoids false positives on short package names or documentation snippets).
_API_KEY_PATTERN = re.compile(r"""['"]sk-[a-zA-Z0-9_-]{20,}['"]""")


def test_no_hardcoded_api_key():
    for path in _SOURCE_FILES:
        content = path.read_text()
        matches = _API_KEY_PATTERN.findall(content)
        assert not matches, (
            f"{path} contains a hardcoded API key pattern: {matches}"
        )


def test_dashboard_no_api_key_reference():
    content = Path("dashboard.py").read_text()
    assert "OPENAI_API_KEY" not in content, (
        "dashboard.py must not reference OPENAI_API_KEY — key access belongs in the backend only"
    )
    assert "os.environ" not in content, (
        "dashboard.py must not access os.environ — key access belongs in the backend only"
    )
    assert "os.getenv" not in content, (
        "dashboard.py must not call os.getenv — key access belongs in the backend only"
    )


def test_empty_log_error_contains_no_secrets():
    response = client.post("/analyze", json={"log": ""})
    assert response.status_code == 422
    body_text = response.text
    assert "Traceback" not in body_text, (
        "Error response must not contain a Python traceback"
    )
    assert 'File "' not in body_text, (
        "Error response must not contain file path references from a traceback"
    )
    assert "sk-" not in body_text, (
        "Error response must not contain any API key pattern"
    )
    assert "OPENAI_API_KEY" not in body_text, (
        "Error response must not reference the API key environment variable name"
    )


def test_error_response_format():
    response = client.post("/analyze", json={"log": ""})
    assert response.status_code == 422
    body = response.json()
    assert "detail" in body, "422 response must contain a 'detail' field"
    detail_str = str(body["detail"])
    assert any(word in detail_str.lower() for word in ("empty", "log", "snippet")), (
        f"Error message must be human-readable; got: {detail_str!r}"
    )
