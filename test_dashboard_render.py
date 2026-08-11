"""Unit tests for dashboard.py result rendering (WO-015)."""

import sys
from unittest.mock import MagicMock, call, patch

import pytest

# Mock streamlit before importing dashboard so top-level widget calls are no-ops
_mock_st = MagicMock()
_mock_st.button.return_value = False
_mock_st.session_state = {}
sys.modules["streamlit"] = _mock_st
sys.modules.setdefault("requests", MagicMock())

from dashboard import render_results  # noqa: E402

# ── Test fixture ──────────────────────────────────────────────────────────

SAMPLE_RESULT = {
    "root_cause": (
        "NullPointerException in OrderService.validateShipping() at OrderService.java:87 "
        "caused by a null customer reference passed from processOrder()"
    ),
    "evidence": [
        "java.lang.NullPointerException: Cannot invoke Customer.getAddress() because customer is null",
        "Stack trace originates at OrderService.java:87 inside validateShipping()",
        "Order 98712 rolled back immediately after the exception",
    ],
    "remediation_steps": [
        "Add a null check for customer before calling getAddress() in validateShipping()",
        "Verify that processOrder() handles missing customer records upstream",
        "Add a unit test for OrderService.validateShipping() with a null customer argument",
    ],
}


# ── Section header tests ───────────────────────────────────────────────────

def test_render_results_calls_root_cause_subheader():
    st = _mock_st
    st.reset_mock()
    render_results(SAMPLE_RESULT)
    subheader_calls = [c.args[0] for c in st.subheader.call_args_list]
    assert "Root Cause" in subheader_calls


def test_render_results_calls_evidence_subheader():
    st = _mock_st
    st.reset_mock()
    render_results(SAMPLE_RESULT)
    subheader_calls = [c.args[0] for c in st.subheader.call_args_list]
    assert "Evidence" in subheader_calls


def test_render_results_calls_remediation_subheader():
    st = _mock_st
    st.reset_mock()
    render_results(SAMPLE_RESULT)
    subheader_calls = [c.args[0] for c in st.subheader.call_args_list]
    assert "Remediation Steps" in subheader_calls


def test_render_results_all_three_subheaders_present():
    st = _mock_st
    st.reset_mock()
    render_results(SAMPLE_RESULT)
    subheader_calls = [c.args[0] for c in st.subheader.call_args_list]
    assert subheader_calls == ["Root Cause", "Evidence", "Remediation Steps"]


# ── Root cause rendering tests ─────────────────────────────────────────────

def test_render_results_displays_root_cause_text():
    st = _mock_st
    st.reset_mock()
    render_results(SAMPLE_RESULT)
    markdown_calls = [c.args[0] for c in st.markdown.call_args_list]
    assert SAMPLE_RESULT["root_cause"] in markdown_calls


# ── Evidence rendering tests ───────────────────────────────────────────────

def test_render_results_evidence_items_are_dash_prefixed():
    st = _mock_st
    st.reset_mock()
    render_results(SAMPLE_RESULT)
    markdown_calls = [c.args[0] for c in st.markdown.call_args_list]
    for item in SAMPLE_RESULT["evidence"]:
        assert f"- {item}" in markdown_calls


def test_render_results_three_evidence_items_produce_three_bullets():
    st = _mock_st
    st.reset_mock()
    render_results(SAMPLE_RESULT)
    markdown_calls = [c.args[0] for c in st.markdown.call_args_list]
    bullet_calls = [m for m in markdown_calls if m.startswith("- ")]
    assert len(bullet_calls) == len(SAMPLE_RESULT["evidence"])


def test_render_results_single_evidence_item_still_renders_as_bullet():
    st = _mock_st
    st.reset_mock()
    result = {"root_cause": "cause", "evidence": ["only item"], "remediation_steps": []}
    render_results(result)
    markdown_calls = [c.args[0] for c in st.markdown.call_args_list]
    assert "- only item" in markdown_calls


# ── Remediation steps rendering tests ─────────────────────────────────────

def test_render_results_remediation_steps_are_numbered():
    st = _mock_st
    st.reset_mock()
    render_results(SAMPLE_RESULT)
    markdown_calls = [c.args[0] for c in st.markdown.call_args_list]
    for i, step in enumerate(SAMPLE_RESULT["remediation_steps"], 1):
        assert f"{i}. {step}" in markdown_calls


def test_render_results_numbering_starts_at_one():
    st = _mock_st
    st.reset_mock()
    render_results(SAMPLE_RESULT)
    markdown_calls = [c.args[0] for c in st.markdown.call_args_list]
    first_step = SAMPLE_RESULT["remediation_steps"][0]
    assert f"1. {first_step}" in markdown_calls


def test_render_results_three_remediation_steps_produce_three_numbered_lines():
    st = _mock_st
    st.reset_mock()
    render_results(SAMPLE_RESULT)
    markdown_calls = [c.args[0] for c in st.markdown.call_args_list]
    numbered = [m for m in markdown_calls if m[:2].rstrip(". ").isdigit()]
    assert len(numbered) == len(SAMPLE_RESULT["remediation_steps"])


def test_render_results_single_remediation_step_numbered_as_one():
    st = _mock_st
    st.reset_mock()
    result = {"root_cause": "cause", "evidence": [], "remediation_steps": ["only step"]}
    render_results(result)
    markdown_calls = [c.args[0] for c in st.markdown.call_args_list]
    assert "1. only step" in markdown_calls


# ── Empty list edge cases ──────────────────────────────────────────────────

def test_render_results_empty_evidence_list_does_not_crash():
    st = _mock_st
    st.reset_mock()
    result = {"root_cause": "some cause", "evidence": [], "remediation_steps": []}
    render_results(result)
    subheader_calls = [c.args[0] for c in st.subheader.call_args_list]
    assert "Evidence" in subheader_calls


def test_render_results_empty_remediation_list_does_not_crash():
    st = _mock_st
    st.reset_mock()
    result = {"root_cause": "some cause", "evidence": [], "remediation_steps": []}
    render_results(result)
    subheader_calls = [c.args[0] for c in st.subheader.call_args_list]
    assert "Remediation Steps" in subheader_calls
