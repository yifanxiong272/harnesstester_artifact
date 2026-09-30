# file: gpt_researcher/retrievers/serpapi/serpapi.py:36-82
# asked: {"lines": [42, 43, 45, 47, 48, 50, 52, 53, 54, 56, 57, 58, 59, 60, 61, 62, 63, 64, 65, 67, 68, 69, 70, 71, 72, 73, 74, 76, 77, 78, 79, 80, 82], "branches": [[48, 50], [48, 52], [60, 61], [60, 82], [62, 63], [62, 82], [65, 67], [65, 82], [67, 68], [67, 69], [69, 70], [69, 71]]}
# gained: {"lines": [42, 43, 45, 47, 48, 50, 52, 53, 54, 56, 57, 58, 59, 60, 61, 62, 63, 64, 65, 67, 68, 69, 70, 71, 72, 73, 74, 76, 77, 78, 79, 80, 82], "branches": [[48, 50], [48, 52], [60, 61], [62, 63], [65, 67], [67, 68], [67, 69], [69, 70], [69, 71]]}

import pytest

from gpt_researcher.retrievers.serpapi import serpapi as serpapi_mod


class FakeResponse:
    def __init__(self, status_code, json_data):
        self.status_code = status_code
        self._json = json_data

    def json(self):
        return self._json


def test_search_with_domains_skips_youtube_and_respects_max_results(monkeypatch, capsys):
    # Arrange: patch get_api_key to avoid real env dependency
    monkeypatch.setattr(serpapi_mod.SerpApiSearch, "get_api_key", lambda self: "DUMMY_KEY")

    # Prepare search results: include a youtube link that should be skipped and more items than max_results
    organic_results = [
        {"title": "First result", "link": "https://example.com/page1", "snippet": "Snippet 1"},
        {"title": "YouTube video", "link": "https://www.youtube.com/watch?v=abc", "snippet": "YT Snippet"},
        {"title": "Second result", "link": "https://example.com/page2", "snippet": "Snippet 2"},
        {"title": "Third result", "link": "https://example.com/page3", "snippet": "Snippet 3"},
        {"title": "Fourth result", "link": "https://example.com/page4", "snippet": "Snippet 4"},
    ]
    fake_json = {"organic_results": organic_results}

    captured = {}

    def fake_get(url, timeout=0):
        # record call
        captured["url"] = url
        captured["timeout"] = timeout
        return FakeResponse(200, fake_json)

    # Patch requests.get used inside the module
    monkeypatch.setattr(serpapi_mod.requests, "get", fake_get)

    # Create instance with query_domains to exercise that branch
    s = serpapi_mod.SerpApiSearch("test query", query_domains=["example.com", "another.com"])

    # Act: request max_results=2 to ensure limit is enforced and youtube is skipped
    results = s.search(max_results=2)

    # Capture printed output and assert the initial print occurred
    captured_output = capsys.readouterr().out
    assert "SerpApiSearch: Searching with query test query" in captured_output

    # Assert requests.get was called and timeout forwarded
    assert "url" in captured
    assert captured["timeout"] == 10

    # The encoded URL should contain the site: domain parts (percent-encoded)
    assert "site%3Aexample.com" in captured["url"]
    assert "OR+site%3Aanother.com" in captured["url"]

    # Assert result length equals max_results and no youtube link present
    assert isinstance(results, list)
    assert len(results) == 2
    for item in results:
        assert "youtube.com" not in item["href"]
        assert set(item.keys()) == {"title", "href", "body"}

    # Ensure ordering matches the non-youtube entries from organic_results
    assert results[0]["title"] == "First result"
    assert results[1]["title"] == "Second result"


def test_search_handles_request_exception_and_returns_empty(monkeypatch, capsys):
    # Arrange: patch get_api_key to avoid real env dependency
    monkeypatch.setattr(serpapi_mod.SerpApiSearch, "get_api_key", lambda self: "DUMMY_KEY")

    def raising_get(url, timeout=0):
        raise RuntimeError("boom")

    monkeypatch.setattr(serpapi_mod.requests, "get", raising_get)

    s = serpapi_mod.SerpApiSearch("another query")
    # Act
    results = s.search(max_results=5)

    # Assert returned empty list on exception
    assert results == []

    # Assert the error message was printed
    out = capsys.readouterr().out
    assert "Error: boom. Failed fetching sources. Resulting in empty response." in out
