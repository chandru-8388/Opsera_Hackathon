"""Unit tests for LogRequest Pydantic model (app.py)."""

import pytest
from pydantic import ValidationError

from app import LogRequest


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
