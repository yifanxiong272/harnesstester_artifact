# file: gpt_researcher/retrievers/searx/searx.py:39-78
# asked: {"lines": [47, 49, 51, 53, 56, 57, 58, 59, 60, 62, 63, 66, 67, 68, 69, 70, 73, 75, 76, 77, 78], "branches": [[67, 68], [67, 73]]}
# gained: {"lines": [47, 49, 51, 53, 56, 57, 58, 59, 60, 62, 63, 66, 67, 68, 69, 70, 73, 75, 76, 77, 78], "branches": [[67, 68], [67, 73]]}

import json
import requests
import pytest

from gpt_researcher.retrievers.searx.searx import SearxSearch


def test_search_success(monkeypatch):
    # Arrange: ensure get_searxng_url returns a known base URL before instantiation
    monkeypatch.setattr(SearxSearch, "get_searxng_url", lambda self: "https://searx.example/")

    captured = {}

    class FakeResponse:
        def __init__(self, payload):
            self._payload = payload
            self.status_raised = False

        def raise_for_status(self):
            # simulate OK status
            self.status_raised = True

        def json(self):
            return self._payload

    # Prepare payload with more results than max_results and some missing fields
    payload = {
        "results": [
            {"url": "https://a.example/1", "content": "first"},
            {"url": "https://b.example/2", "content": "second"},
            {"url": "https://c.example/3"},  # missing content -> should default to ''
            {"content": "no-url"}  # missing url -> should default to ''
        ]
    }

    def fake_get(url, params=None, headers=None):
        # capture call arguments for assertions
        captured['url'] = url
        captured['params'] = params
        captured['headers'] = headers
        return FakeResponse(payload)

    monkeypatch.setattr(requests, "get", fake_get)

    # Act
    s = SearxSearch(query="test query")
    results = s.search(max_results=3)  # should limit to first 3 results

    # Assert: requests.get called with expected url and params/headers
    assert captured['url'].endswith("/search")
    assert captured['params'] == {'q': "test query", 'format': 'json'}
    assert captured['headers'] == {'Accept': 'application/json'}

    # Assert: result normalization and slicing
    assert isinstance(results, list)
    assert len(results) == 3
    assert results[0] == {"href": "https://a.example/1", "body": "first"}
    assert results[1] == {"href": "https://b.example/2", "body": "second"}
    # third had no 'content', should default to empty string
    assert results[2] == {"href": "https://c.example/3", "body": ""}


def test_search_request_exception(monkeypatch):
    # Arrange: force get_searxng_url to a known URL
    monkeypatch.setattr(SearxSearch, "get_searxng_url", lambda self: "https://searx.example/")

    def raising_get(url, params=None, headers=None):
        raise requests.exceptions.RequestException("network failure")

    monkeypatch.setattr(requests, "get", raising_get)

    s = SearxSearch(query="q")
    # Act / Assert: should raise a generic Exception with specific message start
    with pytest.raises(Exception) as excinfo:
        s.search()
    assert "Error querying SearxNG" in str(excinfo.value)
    assert "network failure" in str(excinfo.value)


def test_search_json_decode_error(monkeypatch):
    # Arrange: patch base url
    monkeypatch.setattr(SearxSearch, "get_searxng_url", lambda self: "https://searx.example/")

    class FakeBadJSONResponse:
        def raise_for_status(self):
            return None

        def json(self):
            # raise a real JSONDecodeError
            raise json.JSONDecodeError("Expecting value", "doc", 0)

    def fake_get(url, params=None, headers=None):
        return FakeBadJSONResponse()

    monkeypatch.setattr(requests, "get", fake_get)

    s = SearxSearch(query="q")
    with pytest.raises(Exception) as excinfo:
        s.search()
    assert str(excinfo.value) == "Error parsing SearxNG response"
