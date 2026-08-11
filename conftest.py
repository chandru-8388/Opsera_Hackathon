"""
Pytest configuration — sets required environment variables before any test
module imports so app.py's module-level OpenAI client initialization succeeds.
"""
import os

# Set a dummy API key so app.py can be imported without a real OpenAI account.
os.environ.setdefault("OPENAI_API_KEY", "sk-test-dummy-key-for-pytest")

import pytest
from unittest.mock import MagicMock, patch


def _stub_completion():
    """Build a minimal mock OpenAI completion with a valid AnalysisResponse."""
    from app import AnalysisResponse

    message = MagicMock()
    message.refusal = None
    message.parsed = AnalysisResponse(
        root_cause="Stub: NullPointerException in Service.process() at Service.java:42",
        evidence=[
            "Stack trace originates at Service.java line 42",
            "No null guard before method invocation on the injected dependency",
        ],
        remediation_steps=[
            "Add a null check before calling process()",
            "Verify dependency injection configuration in Main.java",
        ],
    )
    choice = MagicMock()
    choice.message = message
    completion = MagicMock()
    completion.choices = [choice]
    return completion


@pytest.fixture(autouse=True)
def _auto_mock_openai_client():
    """Prevent real OpenAI API calls in every test by default.

    Tests in test_analyze.py that need specific completion shapes use
    ``with patch("app.client") as mock_client:`` inside the test body,
    which overrides this fixture for the duration of the ``with`` block.
    """
    with patch("app.client") as mock_client:
        mock_client.beta.chat.completions.parse.return_value = _stub_completion()
        yield mock_client
