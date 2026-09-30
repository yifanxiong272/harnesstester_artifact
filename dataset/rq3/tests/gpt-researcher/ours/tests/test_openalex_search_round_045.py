import requests
from typing import Any, Dict

from gpt_researcher.retrievers.openalex import openalex as openalex_module
from gpt_researcher.retrievers.openalex.openalex import OpenAlexSearch


class DummyResponse:
    def __init__(self, data: Dict[str, Any], raise_exc: Exception = None):
        self._data = data
        self._raise_exc = raise_exc

    def raise_for_status(self):
        if self._raise_exc:
            raise self._raise_exc

    def json(self):
        return self._data


def test_search_success_includes_params_and_result_round_045(monkeypatch):
    # Capture requests.get call arguments
    captured = {}

    def fake_get(url, params=None, timeout=None):
        captured['url'] = url
        captured['params'] = params
        captured['timeout'] = timeout
        return DummyResponse({
            "results": [
                {"title": "TestTitle", "abstract_inverted_index": {}}
            ]
        })

    monkeypatch.setattr(openalex_module.requests, "get", fake_get)

    # Force deterministic href and abstract
    monkeypatch.setattr(OpenAlexSearch, "_pick_href", lambda self, res: "http://example.com/1")
    monkeypatch.setattr(OpenAlexSearch, "_reconstruct_abstract", lambda self, inv: "An abstract")

    s = OpenAlexSearch(query="q", sort="relevance_score:desc", query_domains=None)
    # exercise email and api_key branches
    s.email = "me@example.com"
    s.api_key = "APIKEY123"

    results = s.search(max_results=10)

    # Validate requests.get call
    assert captured['url'] == s.BASE_URL
    assert captured['timeout'] == 10
    assert captured['params'] == {
        "search": "q",
        "per_page": 10,
        "sort": "relevance_score:desc",
        "mailto": "me@example.com",
        "api_key": "APIKEY123",
    }

    # Validate returned result
    assert isinstance(results, list) and len(results) == 1
    item = results[0]
    assert item["title"] == "TestTitle"
    assert item["href"] == "http://example.com/1"
    assert item["body"] == "An abstract"


def test_search_handles_missing_title_and_abstract_fallback_round_045(monkeypatch):
    # Simulate result with missing title and no reconstructed abstract
    def fake_get(url, params=None, timeout=None):
        return DummyResponse({
            "results": [
                {"title": None, "abstract_inverted_index": {}}
            ]
        })

    monkeypatch.setattr(openalex_module.requests, "get", fake_get)

    # Ensure href truthy so the result is appended
    monkeypatch.setattr(OpenAlexSearch, "_pick_href", lambda self, res: "http://no-title.example")
    # Force abstract reconstruction to return None to trigger fallback
    monkeypatch.setattr(OpenAlexSearch, "_reconstruct_abstract", lambda self, inv: None)

    s = OpenAlexSearch(query="q2", sort="publication_date:desc", query_domains=None)

    results = s.search(max_results=5)

    assert isinstance(results, list) and len(results) == 1
    item = results[0]
    # missing title should become 'No Title'
    assert item["title"] == "No Title"
    assert item["href"] == "http://no-title.example"
    # missing abstract reconstruction should fall back
    assert item["body"] == "Abstract not available"


def test_search_request_exception_round_045(monkeypatch, capsys):
    # Simulate requests.get raising a RequestException
    def raising_get(url, params=None, timeout=None):
        raise requests.RequestException("simulated failure")

    monkeypatch.setattr(openalex_module.requests, "get", raising_get)

    s = OpenAlexSearch(query="q3", sort="cited_by_count:desc", query_domains=None)

    result = s.search(max_results=3)

    # Should return empty list on exception
    assert result == []

    # Printed error message should include clue about OpenAlex API and the exception
    captured = capsys.readouterr()
    assert "An error occurred while accessing OpenAlex API" in captured.out
    assert "simulated failure" in captured.out


def test_search_skips_result_without_href_round_045(monkeypatch):
    # Simulate a result where _pick_href returns falsy -> should be skipped
    def fake_get(url, params=None, timeout=None):
        return DummyResponse({"results": [{"title": "T", "abstract_inverted_index": {}}]})

    monkeypatch.setattr(openalex_module.requests, "get", fake_get)

    # Make _pick_href return None so the entry is not appended
    monkeypatch.setattr(OpenAlexSearch, "_pick_href", lambda self, res: None)
    # Abstract reconstruct shouldn't matter, but ensure deterministic
    monkeypatch.setattr(OpenAlexSearch, "_reconstruct_abstract", lambda self, inv: "ignored")

    s = OpenAlexSearch(query="q4", sort="relevance_score:desc", query_domains=None)

    results = s.search(max_results=1)

    # No items appended because href was falsy
    assert results == []
