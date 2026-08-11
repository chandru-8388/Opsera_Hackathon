"""Unit tests for Pydantic models and FastAPI app configuration (app.py)."""

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app import AnalysisResponse, LogRequest, app

# ── FastAPI app integration tests ──────────────────────────────────────────

client = TestClient(app)


def test_docs_returns_200():
    response = client.get("/docs")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]


def test_openapi_json_has_correct_title():
    response = client.get("/openapi.json")
    assert response.status_code == 200
    data = response.json()
    assert data["info"]["title"] == "Log Analyzer"


def test_openapi_json_has_description():
    response = client.get("/openapi.json")
    assert response.status_code == 200
    data = response.json()
    assert data["info"]["description"]


def test_cors_options_preflight_returns_allow_origin():
    response = client.options(
        "/analyze",
        headers={
            "Origin": "http://localhost:8501",
            "Access-Control-Request-Method": "POST",
        },
    )
    assert "access-control-allow-origin" in response.headers
    assert response.headers["access-control-allow-origin"] == "*"


# ── Fixtures ───────────────────────────────────────────────────────────────

INVALID_INPUTS = [
    "",           # empty string
    "   ",        # spaces only
    "\n",         # newline only
    "\t",         # tab only
    "\n\t   \n",  # mixed whitespace
]

VALID_INPUTS = [
    "java.lang.NullPointerException",
    "ERROR: Connection refused\n  at connect()\n  at main()",
    " valid log with leading/trailing spaces ",
    "a",
]


# ── Invalid input tests ────────────────────────────────────────────────────

def test_empty_string_raises():
    with pytest.raises(ValidationError) as exc_info:
        LogRequest(log="")
    assert "Log snippet must not be empty" in str(exc_info.value)


def test_whitespace_only_raises():
    with pytest.raises(ValidationError):
        LogRequest(log="   ")


def test_newline_only_raises():
    with pytest.raises(ValidationError):
        LogRequest(log="\n")


def test_tab_only_raises():
    with pytest.raises(ValidationError):
        LogRequest(log="\t")


@pytest.mark.parametrize("bad_log", INVALID_INPUTS)
def test_invalid_inputs(bad_log):
    with pytest.raises(ValidationError):
        LogRequest(log=bad_log)


# ── Valid input tests ──────────────────────────────────────────────────────

def test_valid_single_line():
    req = LogRequest(log="java.lang.NullPointerException")
    assert req.log == "java.lang.NullPointerException"


def test_valid_multiline():
    log = "ERROR: Connection refused\n  at connect()\n  at main()"
    req = LogRequest(log=log)
    assert req.log == log


def test_original_value_preserved():
    """Validator must not strip the stored value — only checks emptiness."""
    log = " valid log with leading/trailing spaces "
    req = LogRequest(log=log)
    assert req.log == log


def test_very_long_input():
    log = "ERROR: " + "x" * 10_000
    req = LogRequest(log=log)
    assert len(req.log) > 10_000


@pytest.mark.parametrize("good_log", VALID_INPUTS)
def test_valid_inputs(good_log):
    req = LogRequest(log=good_log)
    assert req.log == good_log


# ══════════════════════════════════════════════════════════════════════════════
# AnalysisResponse tests
# ══════════════════════════════════════════════════════════════════════════════

# ── Reusable fixtures (realistic mock data) ────────────────────────────────

NPE_ANALYSIS = AnalysisResponse(
    root_cause="NullPointerException in Service.process() at Service.java:42 caused by an uninitialized dependency injection",
    evidence=[
        "Stack trace originates at Service.java line 42",
        "No null check before method invocation on the injected dependency",
        "Main.java line 15 calls Service.process() without verifying bean initialization",
    ],
    remediation_steps=[
        "Add a null check before calling process(): if (service == null) throw new IllegalStateException(...)",
        "Verify dependency injection configuration in Main.java",
        "Add an @PostConstruct validation method to Service to fail fast on missing dependencies",
    ],
)

TIMEOUT_ANALYSIS = AnalysisResponse(
    root_cause="Database connection timeout after 30s caused by connection pool exhaustion under high load",
    evidence=[
        "Timeout error after exactly 30000ms matches the configured pool timeout",
        "All 10 pool connections are in ACTIVE state in the thread dump",
        "High request rate (500 req/s) observed in logs 10 minutes before the error",
    ],
    remediation_steps=[
        "Increase connection pool size from 10 to 25 in application.properties",
        "Add connection pool metrics to Grafana to detect exhaustion proactively",
        "Review slow queries and add missing indexes to reduce connection hold time",
    ],
)


# ── Valid instantiation ────────────────────────────────────────────────────

def test_analysis_response_valid():
    resp = AnalysisResponse(
        root_cause="Root cause text",
        evidence=["evidence item 1", "evidence item 2"],
        remediation_steps=["step 1", "step 2"],
    )
    assert resp.root_cause == "Root cause text"
    assert resp.evidence == ["evidence item 1", "evidence item 2"]
    assert resp.remediation_steps == ["step 1", "step 2"]


def test_analysis_response_empty_lists_accepted():
    """Empty lists are schema-valid even if semantically weak."""
    resp = AnalysisResponse(root_cause="something", evidence=[], remediation_steps=[])
    assert resp.evidence == []
    assert resp.remediation_steps == []


def test_analysis_response_empty_root_cause_accepted():
    """Empty string is schema-valid (OpenAI may produce this; app layer handles it)."""
    resp = AnalysisResponse(root_cause="", evidence=[], remediation_steps=[])
    assert resp.root_cause == ""


def test_analysis_response_npe_fixture():
    assert "NullPointerException" in NPE_ANALYSIS.root_cause
    assert len(NPE_ANALYSIS.evidence) == 3
    assert len(NPE_ANALYSIS.remediation_steps) == 3


def test_analysis_response_timeout_fixture():
    assert "timeout" in TIMEOUT_ANALYSIS.root_cause.lower()
    assert len(TIMEOUT_ANALYSIS.evidence) == 3
    assert len(TIMEOUT_ANALYSIS.remediation_steps) == 3


# ── Missing fields ─────────────────────────────────────────────────────────

def test_missing_root_cause_raises():
    with pytest.raises(ValidationError):
        AnalysisResponse(evidence=["e1"], remediation_steps=["s1"])


def test_missing_evidence_raises():
    with pytest.raises(ValidationError):
        AnalysisResponse(root_cause="cause", remediation_steps=["s1"])


def test_missing_remediation_steps_raises():
    with pytest.raises(ValidationError):
        AnalysisResponse(root_cause="cause", evidence=["e1"])


# ── Wrong types ────────────────────────────────────────────────────────────

def test_evidence_as_string_raises():
    """evidence must be list[str], not a plain str."""
    with pytest.raises(ValidationError):
        AnalysisResponse(
            root_cause="cause",
            evidence="this should be a list",
            remediation_steps=["s1"],
        )


def test_remediation_steps_as_string_raises():
    with pytest.raises(ValidationError):
        AnalysisResponse(
            root_cause="cause",
            evidence=["e1"],
            remediation_steps="this should be a list",
        )


# ── JSON Schema compatibility ──────────────────────────────────────────────

def test_json_schema_has_required_properties():
    schema = AnalysisResponse.model_json_schema()
    props = schema.get("properties", {})
    assert "root_cause" in props
    assert "evidence" in props
    assert "remediation_steps" in props


def test_json_schema_all_fields_required():
    schema = AnalysisResponse.model_json_schema()
    required = schema.get("required", [])
    assert "root_cause" in required
    assert "evidence" in required
    assert "remediation_steps" in required


def test_json_schema_evidence_is_array():
    schema = AnalysisResponse.model_json_schema()
    assert schema["properties"]["evidence"]["type"] == "array"


def test_json_schema_remediation_steps_is_array():
    schema = AnalysisResponse.model_json_schema()
    assert schema["properties"]["remediation_steps"]["type"] == "array"
