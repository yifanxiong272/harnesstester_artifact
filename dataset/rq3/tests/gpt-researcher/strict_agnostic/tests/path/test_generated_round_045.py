import requests
import pytest

from gpt_researcher.retrievers.openalex.openalex import OpenAlexSearch


class _FakeResponse:
    def __init__(self, json_data=None, raise_exc=None):
        self._json = json_data or {}
        self._raise_exc = raise_exc

    def raise_for_status(self):
        if self._raise_exc:
            raise self._raise_exc

    def json(self):
        return self._json


def test_search_handles_request_exception_round_045(monkeypatch):
    """If requests.get raises a RequestException, search should catch it and return an empty list."""
    # Use a valid sort value accepted by the class to avoid constructor assertion
    searcher = OpenAlexSearch(query="q", sort="relevance_score:desc", query_domains=None)

    def _raise_get(url, params=None, timeout=None):
        raise requests.RequestException("network fail simulated")

    monkeypatch.setattr(requests, "get", _raise_get)

    result = searcher.search()

    assert result == [], "Expected empty list when requests.get raises RequestException"


def test_search_with_email_and_api_key_and_results_round_045(monkeypatch):
    """When email and api_key are present, they should be passed to requests.get; results with missing title should default to 'No Title' and missing abstract should become 'Abstract not available'."""
    # Use a valid sort value accepted by the class
    searcher = OpenAlexSearch(query="query", sort="relevance_score:desc", query_domains=None)
    # enable both flags
    searcher.email = "me@example.com"
    searcher.api_key = "secret"

    # Prepare a fake response containing a single result with title=None
    fake_results = [
        {
            "title": None,
            "abstract_inverted_index": {"0": [0]},
        }
    ]

    def _fake_get(url, params=None, timeout=None):
        # Assert that email and api_key were included in params and per_page is capped at 25
        assert params is not None
        assert params.get("mailto") == "me@example.com"
        assert params.get("api_key") == "secret"
        # when we request max_results=30 below, per_page should be min(30,25)=25
        assert params.get("per_page") == 25
        return _FakeResponse(json_data={"results": fake_results})

    # Replace external calls and internal helper methods for deterministic behavior
    monkeypatch.setattr(requests, "get", _fake_get)
    # Force _pick_href to return a valid href
    searcher._pick_href = lambda r: "http://example.org/work"
    # Force _reconstruct_abstract to return None so default text is used
    searcher._reconstruct_abstract = lambda inverted: None

    results = searcher.search(max_results=30)

    assert isinstance(results, list) and len(results) == 1
    item = results[0]
    assert item["title"] == "No Title", "Missing title should become 'No Title'"
    assert item["href"] == "http://example.org/work"
    assert item["body"] == "Abstract not available", "Missing abstract should use the default message"


def test_search_skips_results_without_href_round_045(monkeypatch):
    """If _pick_href returns a falsy value, that result should be skipped from final list."""
    # Use a valid sort value accepted by the class
    searcher = OpenAlexSearch(query="q2", sort="relevance_score:desc", query_domains=None)

    # Response contains a single result that would otherwise be included
    fake_results = [{"title": "A Title", "abstract_inverted_index": {"0": [0]}}]

    def _fake_get_no_auth(url, params=None, timeout=None):
        # Ensure mailto and api_key are not present
        assert params is not None
        assert "mailto" not in params
        assert "api_key" not in params
        # When we pass max_results=2 below, per_page should be 2
        assert params.get("per_page") == 2
        return _FakeResponse(json_data={"results": fake_results})

    monkeypatch.setattr(requests, "get", _fake_get_no_auth)
    # Simulate that no href can be derived for the result
    searcher._pick_href = lambda r: None
    # If abstract reconstruction returns something, it should not matter because result is skipped
    searcher._reconstruct_abstract = lambda inverted: "some abstract"

    results = searcher.search(max_results=2)

    # Because href was falsy, the result should be skipped entirely
    assert results == [], "Results without href should be omitted from returned list"
