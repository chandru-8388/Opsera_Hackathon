"""Unit tests for dashboard.py input validation helper."""

import sys
from unittest.mock import MagicMock

import pytest

# Mock streamlit and requests before importing dashboard so top-level widget
# calls are no-ops and st.button() returns False (skips the button block).
_mock_st = MagicMock()
_mock_st.button.return_value = False
sys.modules["streamlit"] = _mock_st
sys.modules.setdefault("requests", MagicMock())

from dashboard import is_valid_input  # noqa: E402 — must follow sys.modules patch


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
    " log with leading/trailing spaces ",
    "a",
    "x" * 10_000,  # very large input
]


# ── Invalid input tests ────────────────────────────────────────────────────

def test_empty_string_is_invalid():
    assert is_valid_input("") is False


def test_spaces_only_is_invalid():
    assert is_valid_input("   ") is False


def test_newline_only_is_invalid():
    assert is_valid_input("\n") is False


def test_tab_only_is_invalid():
    assert is_valid_input("\t") is False


@pytest.mark.parametrize("bad_input", INVALID_INPUTS)
def test_invalid_inputs(bad_input):
    assert is_valid_input(bad_input) is False


# ── Valid input tests ──────────────────────────────────────────────────────

def test_normal_log_is_valid():
    assert is_valid_input("java.lang.NullPointerException") is True


def test_multiline_log_is_valid():
    assert is_valid_input("ERROR: Connection refused\n  at connect()") is True


def test_leading_trailing_whitespace_with_content_is_valid():
    """strip() is used only for empty check — content with surrounding whitespace passes."""
    assert is_valid_input(" valid content ") is True


def test_very_large_input_is_valid():
    assert is_valid_input("x" * 10_000) is True


@pytest.mark.parametrize("good_input", VALID_INPUTS)
def test_valid_inputs(good_input):
    assert is_valid_input(good_input) is True
