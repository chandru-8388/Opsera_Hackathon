"""
Pytest configuration — sets required environment variables before any test
module imports so app.py's module-level OpenAI client initialization succeeds.
"""
import os

# Set a dummy API key so app.py can be imported without a real OpenAI account.
# Tests that exercise the /analyze endpoint use the stub analyze_log function
# and never make actual API calls — this key is never sent anywhere.
os.environ.setdefault("OPENAI_API_KEY", "sk-test-dummy-key-for-pytest")
