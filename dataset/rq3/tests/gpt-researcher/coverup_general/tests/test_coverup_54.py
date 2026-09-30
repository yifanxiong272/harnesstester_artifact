# file: gpt_researcher/retrievers/searx/searx.py:39-78
# asked: {"lines": [47, 49, 51, 53, 56, 57, 58, 59, 60, 62, 63, 66, 67, 68, 69, 70, 73, 75, 76, 77, 78], "branches": [[67, 68], [67, 73]]}
# gained: {"lines": [47, 49, 51, 53, 56, 57, 58, 59, 60, 62, 63, 66, 67, 68, 69, 70, 73, 75, 76, 77, 78], "branches": [[67, 68], [67, 73]]}

import json
import pytest
import requests

from gpt_researcher.retrievers.searx import searx as searx_module
from gpt_researcher.retrievers.searx.searx import SearxSearch


def test_search_success_returns_normalized_results_and_uses_search_url(monkeypatch):
    # Arrange
    base_url = "http://example.org/base/"
    query = "test query"
    max_results = 2

    # Prepare fake results longer than max_results to ensure truncation works
    fake_results = {
        "results": [
            {"url": "http://a", "content": "A"},
            {"url": "http://b", "content": "B"},
            {"url": "http://c", "content": "C"},
        ]
    }

    # Record the call made to requests.get
    recorded = {}

    class FakeResponse:
        def raise_for_status(self):
            # simulate HTTP 200 OK
            return None

        def json(self):
            return fake_results

    def fake_get(url, params=None, headers=None):
        recorded['url'] = url
        recorded['params'] = params
        recorded['headers'] = headers
        return FakeResponse()

    # Monkeypatch the SearxSearch.get_searxng_url to return our base_url
    monkeypatch.setattr(SearxSearch, "get_searxng_url", lambda self: base_url)
    # Monkeypatch the requests.get used in the module under test
    monkeypatch.setattr(searx_module.requests, "get", fake_get)

    # Act
    s = SearxSearch(query=query)
    results = s.search(max_results=max_results)

    # Assert
    # Ensure requests.get was called with urljoin(base_url, "search")
    assert recorded['url'] == "http://example.org/base/search"
    assert recorded['params'] == {'q': query, 'format': 'json'}
    assert recorded['headers'] == {'Accept': 'application/json'}

    # Ensure returned results are normalized and truncated to max_results
    assert isinstance(results, list)
    assert len(results) == max_results
    assert results[0] == {"href": "http://a", "body": "A"}
    assert results[1] == {"href": "http://b", "body": "B"}


def test_search_http_request_exception_is_wrapped(monkeypatch):
    # Arrange
    base_url = "http://example.org/"
    query = "error query"

    def fake_get_raises(url, params=None, headers=None):
        raise requests.exceptions.RequestException("network down")

    monkeypatch.setattr(SearxSearch, "get_searxng_url", lambda self: base_url)
    monkeypatch.setattr(searx_module.requests, "get", fake_get_raises)

    s = SearxSearch(query=query)

    # Act / Assert
    with pytest.raises(Exception) as excinfo:
        s.search()

    assert "Error querying SearxNG" in str(excinfo.value)
    assert "network down" in str(excinfo.value)


def test_search_json_decode_error_is_wrapped(monkeypatch):
    # Arrange
    base_url = "http://example.com/"
    query = "json error"

    class FakeResponse:
        def raise_for_status(self):
            return None

        def json(self):
            # Raise a real JSONDecodeError
            raise json.JSONDecodeError("Expecting value", doc="", pos=0)

    def fake_get(url, params=None, headers=None):
        return FakeResponse()

    monkeypatch.setattr(SearxSearch, "get_searxng_url", lambda self: base_url)
    monkeypatch.setattr(searx_module.requests, "get", fake_get)

    s = SearxSearch(query=query)

    # Act / Assert
    with pytest.raises(Exception) as excinfo:
        s.search()

    assert str(excinfo.value) == "Error parsing SearxNG response"
