import json
from unittest.mock import patch

from gpt_researcher.retrievers.bing import bing as bing_module

# Create small helpers used by the tests
class FakeLogger:
    def __init__(self):
        self.errors = []
        self.warnings = []

    def error(self, msg):
        # store as string for deterministic assertions
        self.errors.append(str(msg))

    def warning(self, msg):
        self.warnings.append(str(msg))


class RespObj:
    def __init__(self, text):
        self.text = text


class DummySelf:
    def __init__(self):
        # attributes expected by BingSearch.search
        self.query = "test query"
        self.api_key = "fake_key"
        self.logger = FakeLogger()


def test_search_resp_none_round_038():
    """When requests.get returns None, search should return an empty list."""
    dummy = DummySelf()

    # Patch the requests.get used in the bing module to return None
    with patch.object(bing_module.requests, "get", return_value=None):
        res = bing_module.BingSearch.search(dummy, max_results=3)

    assert res == [], "Expected empty list when requests.get returns None"


def test_search_invalid_json_round_038():
    """When the response contains invalid JSON, search logs an error and returns []."""
    dummy = DummySelf()

    # Provide invalid JSON text so json.loads will raise
    bad_response = RespObj(text="not a json")

    with patch.object(bing_module.requests, "get", return_value=bad_response):
        res = bing_module.BingSearch.search(dummy, max_results=2)

    assert res == [], "Expected empty list for invalid JSON response"
    # The logger.error should have been called with a message mentioning parsing
    assert any("Error parsing Bing search results" in e or "parsing Bing search results" in e for e in dummy.logger.errors), (
        f"Expected error log mentioning parsing, got: {dummy.logger.errors}"
    )


def test_search_normal_results_and_skip_youtube_round_038():
    """Valid search results: youtube links are skipped, other results normalized and returned."""
    dummy = DummySelf()

    # Build a response with two results: one youtube (should be skipped), one normal
    payload = {
        "webPages": {
            "value": [
                {"name": "A YouTube Video", "url": "https://www.youtube.com/watch?v=abcd", "snippet": "yt snippet"},
                {"name": "Example Page", "url": "https://example.com/page", "snippet": "example snippet"}
            ]
        }
    }

    good_response = RespObj(text=json.dumps(payload))

    with patch.object(bing_module.requests, "get", return_value=good_response):
        res = bing_module.BingSearch.search(dummy, max_results=5)

    # Expect only the non-youtube result, normalized
    assert isinstance(res, list), "Result should be a list"
    assert len(res) == 1, f"Expected 1 non-youtube result, got {len(res)}: {res}"
    first = res[0]
    assert first["title"] == "Example Page"
    assert first["href"] == "https://example.com/page"
    assert first["body"] == "example snippet"

    # No error logs expected for normal flow
    assert dummy.logger.errors == [], f"Did not expect errors in normal flow, got: {dummy.logger.errors}"
    # No warnings for this payload
    assert dummy.logger.warnings == [], f"Did not expect warnings in normal flow, got: {dummy.logger.warnings}"
