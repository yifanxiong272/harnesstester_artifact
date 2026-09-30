# file: gpt_researcher/retrievers/bing/bing.py:39-95
# asked: {"lines": [45, 46, 49, 51, 52, 53, 56, 57, 58, 59, 60, 61, 62, 63, 66, 69, 70, 71, 72, 73, 74, 75, 76, 77, 78, 79, 80, 81, 84, 86, 87, 88, 89, 90, 91, 93, 95], "branches": [[69, 70], [69, 71], [78, 79], [78, 81], [84, 86], [84, 95], [86, 87], [86, 88]]}
# gained: {"lines": [45, 46, 49, 51, 52, 53, 56, 57, 58, 59, 60, 61, 62, 63, 66, 69, 70, 71, 72, 73, 74, 75, 76, 77, 78, 81, 84, 86, 87, 88, 89, 90, 91, 93, 95], "branches": [[69, 70], [69, 71], [78, 81], [84, 86], [84, 95], [86, 87], [86, 88]]}

import json
import types
import pytest

from gpt_researcher.retrievers.bing import bing as bing_module
from gpt_researcher.retrievers.bing.bing import BingSearch


class DummyLogger:
    def __init__(self):
        self.errors = []
        self.warnings = []

    def error(self, msg):
        self.errors.append(msg)

    def warning(self, msg):
        self.warnings.append(msg)


class DummyResponse:
    def __init__(self, text):
        self.text = text


def test_search_returns_normal_results_and_skips_youtube(monkeypatch):
    """
    Test that search:
    - Calls requests.get with expected url, headers and params
    - Parses JSON results
    - Skips youtube.com results
    - Returns normalized results list
    """
    captured = {}

    def fake_get(url, headers=None, params=None):
        # Assert URL and headers/params structure
        assert url == "https://api.bing.microsoft.com/v7.0/search"
        assert headers is not None
        assert headers["Ocp-Apim-Subscription-Key"] == "TESTKEY"
        assert headers["Content-Type"] == "application/json"
        assert params is not None
        # q should be our query and count the provided max_results
        assert params["q"] == "example query"
        assert params["count"] == 3

        # Prepare response with one youtube result (to be skipped) and one normal
        payload = {
            "webPages": {
                "value": [
                    {"name": "A YouTube Video", "url": "https://www.youtube.com/watch?v=abc", "snippet": "yt snippet"},
                    {"name": "Example Page", "url": "https://example.com/page", "snippet": "example snippet"},
                ]
            }
        }
        captured["called"] = True
        return DummyResponse(json.dumps(payload))

    monkeypatch.setattr(bing_module, "requests", types.SimpleNamespace(get=fake_get))
    # Ensure __init__ doesn't try to fetch a real key
    monkeypatch.setattr(BingSearch, "get_api_key", lambda self: "TESTKEY")

    bs = BingSearch("example query")
    bs.logger = DummyLogger()

    results = bs.search(max_results=3)

    assert captured.get("called", False) is True
    # youtube entry should be skipped, so only one result
    assert isinstance(results, list)
    assert len(results) == 1
    res = results[0]
    assert res["title"] == "Example Page"
    assert res["href"] == "https://example.com/page"
    assert res["body"] == "example snippet"
    # no errors or warnings logged
    assert bs.logger.errors == []
    assert bs.logger.warnings == []


def test_search_returns_empty_when_resp_is_none(monkeypatch):
    """
    If requests.get returns None, search should return empty list.
    """
    def fake_get(url, headers=None, params=None):
        return None

    monkeypatch.setattr(bing_module, "requests", types.SimpleNamespace(get=fake_get))
    monkeypatch.setattr(BingSearch, "get_api_key", lambda self: "KEY")

    bs = BingSearch("q")
    bs.logger = DummyLogger()

    result = bs.search()
    assert result == []
    # nothing should have been logged
    assert bs.logger.errors == []
    assert bs.logger.warnings == []


def test_search_handles_invalid_json_and_logs_error(monkeypatch):
    """
    If the response text is invalid JSON, the method should log an error and return [].
    """
    def fake_get(url, headers=None, params=None):
        return DummyResponse("this is not json")

    monkeypatch.setattr(bing_module, "requests", types.SimpleNamespace(get=fake_get))
    monkeypatch.setattr(BingSearch, "get_api_key", lambda self: "ANOTHER")

    bs = BingSearch("query")
    logger = DummyLogger()
    bs.logger = logger

    result = bs.search(max_results=1)
    assert result == []
    # An error should have been logged mentioning parsing Bing search results
    assert any("Error parsing Bing search results" in e for e in logger.errors)
    # No warnings expected
    assert logger.warnings == []
