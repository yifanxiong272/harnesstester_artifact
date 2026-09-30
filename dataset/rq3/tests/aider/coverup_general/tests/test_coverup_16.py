# file: aider/models.py:919-968
# asked: {"lines": [922, 924, 925, 926, 928, 930, 931, 933, 936, 937, 939, 940, 941, 943, 944, 945, 946, 947, 950, 951, 952, 953, 954, 955, 956, 957, 958, 959, 960, 963, 964, 965, 966, 968], "branches": [[924, 0], [924, 928], [936, 937], [936, 939], [940, 941], [940, 943], [952, 953], [952, 963], [965, 966], [965, 968]]}
# gained: {"lines": [922, 924, 928, 930, 931, 933, 936, 937, 939, 940, 941, 943, 944, 945, 946, 947, 950, 951, 952, 953, 954, 955, 956, 957, 958, 959, 960, 963, 964, 965, 966, 968], "branches": [[924, 928], [936, 937], [936, 939], [940, 941], [940, 943], [952, 953], [952, 963], [965, 966], [965, 968]]}

import json
import os
import types
import pytest

from aider import models
from aider.models import Model


def _call_method(extra_headers):
    # call the method as an unbound function to avoid Model initialization requirements
    return Model.github_copilot_token_to_open_ai_key(None, extra_headers)


def test_missing_github_token_raises_keyerror(monkeypatch):
    # Ensure OPENAI_API_KEY is not present so the function enters the token exchange path
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    # Ensure GITHUB_COPILOT_TOKEN is absent
    monkeypatch.delenv("GITHUB_COPILOT_TOKEN", raising=False)

    extra_headers = {"Editor-Version": "1.0", "Copilot-Integration-Id": "integration-id"}

    with pytest.raises(KeyError) as excinfo:
        _call_method(extra_headers)
    assert "GITHUB_COPILOT_TOKEN environment variable not found" in str(excinfo.value)


def test_empty_github_token_raises_keyerror(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    # Set GITHUB_COPILOT_TOKEN to whitespace
    monkeypatch.setenv("GITHUB_COPILOT_TOKEN", "   ")

    extra_headers = {"Editor-Version": "1.0", "Copilot-Integration-Id": "integration-id"}

    with pytest.raises(KeyError) as excinfo:
        _call_method(extra_headers)
    assert "GITHUB_COPILOT_TOKEN environment variable is empty" in str(excinfo.value)


def test_requests_non_200_raises_githubcopilottokenerror_and_hides_token(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    # Set a token long enough to trigger the preview with ellipses
    monkeypatch.setenv("GITHUB_COPILOT_TOKEN", "tok12345abcdef")

    extra_headers = {"Editor-Version": "1.0", "Copilot-Integration-Id": "integration-id"}

    class MockResponse:
        def __init__(self):
            self.status_code = 400
            self.text = "bad request"

        def json(self):
            return {"irrelevant": True}

    # Patch requests.get globally so the inline import inside the function will use this
    def mock_get(url, headers):
        # check that headers were passed as expected
        assert headers["Editor-Version"] == extra_headers["Editor-Version"]
        assert headers["Copilot-Integration-Id"] == extra_headers["Copilot-Integration-Id"]
        # Authorization should contain full token in the actual request
        assert headers["Authorization"].endswith("tok12345abcdef")
        return MockResponse()

    monkeypatch.setattr("requests.get", mock_get)

    with pytest.raises(Exception) as excinfo:
        _call_method(extra_headers)

    e = excinfo.value
    # The exception class is defined inside the function; verify by name
    assert e.__class__.__name__ == "GitHubCopilotTokenError"
    msg = str(e)
    assert "Status: 400" in msg
    assert "URL: https://api.github.com/copilot_internal/v2/token" in msg
    # Ensure the token preview (first 5 chars + '...') is present in the error message
    assert "tok12..." in msg
    # Ensure full token was not included
    assert "tok12345abcdef" not in msg


def test_response_missing_token_field_raises_error(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.setenv("GITHUB_COPILOT_TOKEN", "abcdef")

    extra_headers = {"Editor-Version": "1.0", "Copilot-Integration-Id": "integration-id"}

    class MockResponse:
        status_code = 200
        text = "{}"

        def json(self):
            return {}  # missing 'token' field

    def mock_get(url, headers):
        return MockResponse()

    monkeypatch.setattr("requests.get", mock_get)

    with pytest.raises(Exception) as excinfo:
        _call_method(extra_headers)

    e = excinfo.value
    assert e.__class__.__name__ == "GitHubCopilotTokenError"
    assert str(e) == "Response missing 'token' field"


def test_success_sets_openai_api_key(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.setenv("GITHUB_COPILOT_TOKEN", "validtoken")

    extra_headers = {"Editor-Version": "1.0", "Copilot-Integration-Id": "integration-id"}

    token_value = "OPENAI-KEY-123"

    class MockResponse:
        status_code = 200
        text = json.dumps({"token": token_value})

        def json(self):
            return {"token": token_value}

    def mock_get(url, headers):
        return MockResponse()

    monkeypatch.setattr("requests.get", mock_get)

    # Ensure env doesn't already have OPENAI_API_KEY
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    # Call the method and ensure it completes without raising
    _call_method(extra_headers)
    # Confirm OPENAI_API_KEY is set correctly
    assert os.environ.get("OPENAI_API_KEY") == token_value
    # Clean up explicitly (monkeypatch will also restore, but be explicit)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
