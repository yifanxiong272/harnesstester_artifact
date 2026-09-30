# file: gpt_researcher/retrievers/serper/serper.py:57-130
# asked: {"lines": [63, 64, 67, 69, 70, 71, 75, 78, 79, 80, 83, 85, 86, 88, 89, 90, 94, 95, 97, 98, 100, 101, 103, 105, 108, 109, 110, 111, 112, 113, 114, 115, 117, 118, 122, 123, 124, 125, 126, 128, 130], "branches": [[78, 79], [78, 83], [79, 80], [79, 83], [83, 85], [83, 88], [94, 95], [94, 97], [97, 98], [97, 100], [100, 101], [100, 103], [108, 109], [108, 110], [114, 115], [114, 117], [122, 123], [122, 130]]}
# gained: {"lines": [63, 64, 67, 69, 70, 71, 75, 78, 79, 80, 83, 85, 86, 88, 89, 90, 94, 95, 97, 98, 100, 101, 103, 105, 108, 109, 110, 111, 112, 113, 114, 115, 117, 118, 122, 123, 124, 125, 126, 128, 130], "branches": [[78, 79], [79, 80], [79, 83], [83, 85], [83, 88], [94, 95], [94, 97], [97, 98], [97, 100], [100, 101], [100, 103], [108, 109], [108, 110], [114, 115], [114, 117], [122, 123], [122, 130]]}

import json
import types
import pytest

from gpt_researcher.retrievers.serper import serper as serper_module
from gpt_researcher.retrievers.serper.serper import SerperSearch


class DummyResponse:
    def __init__(self, text):
        self.text = text


def _patch_api_key(monkeypatch, key="DUMMY_KEY"):
    # Ensure SerperSearch.get_api_key returns a deterministic key and does not access environment.
    monkeypatch.setattr(SerperSearch, "get_api_key", lambda self: key)


def test_search_returns_normalized_results_and_params(monkeypatch):
    _patch_api_key(monkeypatch, key="TESTKEY123")

    captured = {}

    def fake_request(method, url, timeout, headers, data):
        # capture the incoming parameters for assertions
        captured['method'] = method
        captured['url'] = url
        captured['timeout'] = timeout
        captured['headers'] = headers
        captured['data'] = data

        # Return a valid JSON body with an organic list
        body = {
            "organic": [
                {"title": "Result Title", "link": "https://example.com/page", "snippet": "A short snippet"}
            ]
        }
        return DummyResponse(json.dumps(body))

    # Patch the requests.request used inside the module
    monkeypatch.setattr(serper_module.requests, "request", fake_request)

    # Create SerperSearch with domains and exclude sites to exercise query building
    ss = SerperSearch(
        query="my query",
        query_domains=["example.com", "foo.com"],
        country="us",
        language="en",
        time_range="qdr:m",
        exclude_sites=["bad.com"]
    )

    results = ss.search(max_results=5)

    # Verify normalized results
    assert isinstance(results, list)
    assert len(results) == 1
    assert results[0]["title"] == "Result Title"
    assert results[0]["href"] == "https://example.com/page"
    assert results[0]["body"] == "A short snippet"

    # Verify request call details
    assert captured["method"] == "POST"
    assert captured["url"] == "https://google.serper.dev/search"
    assert captured["timeout"] == 10

    # Headers should include the API key and content type
    assert captured["headers"]["X-API-KEY"] == "TESTKEY123"
    assert "Content-Type" in captured["headers"]

    # Data must be JSON and include q, num, gl, hl, tbs
    sent = json.loads(captured["data"])
    # Query should include original query, excluded site, and domain query
    assert "my query" in sent["q"]
    assert "-site:bad.com" in sent["q"]
    # Domain query string should be present with OR joined
    assert "site:example.com OR site:foo.com" in sent["q"] or "site:example.com OR site:foo.com" in sent["q"]
    assert sent["num"] == 5
    assert sent["gl"] == "us"
    assert sent["hl"] == "en"
    assert sent["tbs"] == "qdr:m"


def test_search_returns_none_when_response_is_none(monkeypatch):
    _patch_api_key(monkeypatch, key="KEY2")

    def fake_request_none(method, url, timeout, headers, data):
        return None

    monkeypatch.setattr(serper_module.requests, "request", fake_request_none)

    ss = SerperSearch(query="q", exclude_sites=["x.com"])
    res = ss.search()
    assert res is None


def test_search_returns_none_on_invalid_json(monkeypatch):
    _patch_api_key(monkeypatch, key="KEY3")

    def fake_request_invalid_json(method, url, timeout, headers, data):
        # Response.text that's not valid JSON
        return DummyResponse("this is not json")

    monkeypatch.setattr(serper_module.requests, "request", fake_request_invalid_json)

    ss = SerperSearch(query="q2", exclude_sites=["x.com"])
    res = ss.search()
    assert res is None


def test_search_returns_none_when_json_null(monkeypatch):
    _patch_api_key(monkeypatch, key="KEY4")

    def fake_request_null_json(method, url, timeout, headers, data):
        # JSON 'null' deserializes to None
        return DummyResponse("null")

    monkeypatch.setattr(serper_module.requests, "request", fake_request_null_json)

    ss = SerperSearch(query="q3", exclude_sites=["x.com"])
    res = ss.search()
    assert res is None
