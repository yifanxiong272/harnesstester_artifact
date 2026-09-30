import os
import urllib.parse
import importlib
import pytest

# Import the module and class under test
serpapi_module = importlib.import_module("gpt_researcher.retrievers.serpapi.serpapi")
from gpt_researcher.retrievers.serpapi.serpapi import SerpApiSearch


class FakeResponse:
    def __init__(self, status_code, json_data):
        self.status_code = status_code
        self._json = json_data

    def json(self):
        return self._json


def _install_fake_get(monkeypatch, get_func):
    """Patch the requests.get used in the serpapi module with a provided callable."""
    fake_requests = type("R", (), {"get": staticmethod(get_func)})
    monkeypatch.setattr(serpapi_module, "requests", fake_requests)


def test_search_no_results_round_028(monkeypatch):
    # Ensure deterministic API key resolution
    monkeypatch.setenv("SERPAPI_API_KEY", "testkey_no_results")

    captured = {}

    def fake_get(url, timeout=10):
        captured["url"] = url
        return FakeResponse(200, {})

    _install_fake_get(monkeypatch, fake_get)

    s = SerpApiSearch("myquery")
    result = s.search(max_results=5)

    # No organic results -> empty list
    assert result == []

    # Check encoded URL contains expected q and api_key params
    assert "q=myquery" in captured["url"]
    assert "api_key=testkey_no_results" in captured["url"]


def test_search_with_domains_and_skip_youtube_and_max_results_round_028(monkeypatch):
    # Test branch where query_domains are provided, youtube results are skipped,
    # and max_results limits processed items.
    monkeypatch.setenv("SERPAPI_API_KEY", "testkey_domains")

    captured = {}

    results = [
        {"title": "video", "link": "https://youtube.com/watch?v=1", "snippet": "yt snippet"},
        {"title": "page1", "link": "https://example.com/page1", "snippet": "snippet1"},
        {"title": "page2", "link": "https://another.com/page2", "snippet": "snippet2"},
    ]

    def fake_get(url, timeout=10):
        captured["url"] = url
        return FakeResponse(200, {"organic_results": results})

    _install_fake_get(monkeypatch, fake_get)

    s = SerpApiSearch("searchterm", query_domains=["example.com", "another.com"]) 
    # ask for only 1 result to force the max_results break logic
    out = s.search(max_results=1)

    # The youtube result should be skipped, so the first returned should be page1 only
    assert out == [{"title": "page1", "href": "https://example.com/page1", "body": "snippet1"}]

    # Verify that the q parameter includes the site:... OR site:... addition (decoded)
    parsed = urllib.parse.urlparse(captured["url"])
    qs = urllib.parse.parse_qs(parsed.query)
    # parse_qs yields decoded values; the constructed search query should contain both sites joined by ' OR '
    assert "site:example.com OR site:another.com" in qs.get("q", [""])[0]
    # Ensure api_key present
    assert qs.get("api_key", [""])[0] == "testkey_domains"


def test_search_non_200_round_028(monkeypatch):
    # If the response status is not 200, search should return empty list
    monkeypatch.setenv("SERPAPI_API_KEY", "testkey_non200")

    def fake_get(url, timeout=10):
        return FakeResponse(404, {"organic_results": []})

    _install_fake_get(monkeypatch, fake_get)

    s = SerpApiSearch("q_non200")
    assert s.search() == []


def test_search_exception_round_028(monkeypatch, capsys):
    # If requests.get raises, the function should handle it and return an empty list
    monkeypatch.setenv("SERPAPI_API_KEY", "testkey_exception")

    def fake_get(url, timeout=10):
        raise RuntimeError("network down")

    _install_fake_get(monkeypatch, fake_get)

    s = SerpApiSearch("q_broken")
    out = s.search()

    assert out == []
    captured = capsys.readouterr()
    # The implementation prints an error message containing 'Failed fetching sources.'
    assert "Failed fetching sources" in captured.out or "Failed fetching sources" in captured.err
