# file: gpt_researcher/retrievers/openalex/openalex.py:44-84
# asked: {"lines": [51, 52, 53, 54, 56, 57, 58, 59, 61, 62, 63, 64, 65, 66, 68, 69, 70, 71, 72, 73, 75, 76, 77, 78, 79, 80, 84], "branches": [[56, 57], [56, 58], [58, 59], [58, 61], [70, 71], [70, 84], [75, 70], [75, 76]]}
# gained: {"lines": [51, 52, 53, 54, 56, 57, 58, 59, 61, 62, 63, 64, 65, 66, 68, 69, 70, 71, 72, 73, 75, 76, 77, 78, 79, 80, 84], "branches": [[56, 57], [56, 58], [58, 59], [58, 61], [70, 71], [70, 84], [75, 70], [75, 76]]}

import requests
import pytest

from gpt_researcher.retrievers.openalex.openalex import OpenAlexSearch


def test_search_handles_request_exception(monkeypatch, capsys):
    # Create instance (no env vars needed)
    s = OpenAlexSearch("test-query")

    # Patch the requests.get used in the module to raise a RequestException
    def fake_get_raise(*args, **kwargs):
        raise requests.RequestException("network failure")

    monkeypatch.setattr(
        "gpt_researcher.retrievers.openalex.openalex.requests.get", fake_get_raise
    )

    # Run search and assert it returns empty list and prints the error message
    result = s.search()
    assert result == []

    captured = capsys.readouterr()
    assert "An error occurred while accessing OpenAlex API" in captured.out
    assert "network failure" in captured.out


def test_search_params_and_result_processing(monkeypatch):
    # Set environment variables before creating the instance so __init__ picks them up
    monkeypatch.setenv("OPENALEX_EMAIL", "tester@example.com")
    monkeypatch.setenv("OPENALEX_API_KEY", "apikey123")

    s = OpenAlexSearch("my query", sort="relevance_score:desc")

    # Prepare fake results to exercise branches:
    # - first result has no title -> "No Title"
    # - second result will have a href of None -> skipped
    # - third result will have a title and href and an abstract
    results = [
        {"title": None, "abstract_inverted_index": None},
        {"title": "Second", "abstract_inverted_index": {"0": {}}},
        {"title": "Third", "abstract_inverted_index": {"0": {}}},
    ]

    # Track the params passed to requests.get across calls
    calls_params = []

    # Fake response object
    class FakeResponse:
        def __init__(self, results_payload):
            self._results_payload = results_payload

        def raise_for_status(self):
            # emulate a successful status
            return None

        def json(self):
            return {"results": self._results_payload}

    # We will vary _pick_href and _reconstruct_abstract behavior per call
    # Use instance-level patched methods to observe the input 'result' and call order
    def fake_pick_href(result):
        # choose href based on title
        t = result.get("title")
        if t is None:
            return "http://example.com/1"
        if t == "Second":
            return None
        if t == "Third":
            return "http://example.com/3"
        return None

    # reconstruct called once per result in order; use counter to vary return values
    reconstruct_call = {"n": 0}

    def fake_reconstruct(inverted):
        reconstruct_call["n"] += 1
        # For first result return None -> should become "Abstract not available"
        if reconstruct_call["n"] == 1:
            return None
        # For second result return something (but that result will be skipped due to no href)
        if reconstruct_call["n"] == 2:
            return "Second abstract"
        # For third result return the expected abstract
        if reconstruct_call["n"] == 3:
            return "Some abstract"
        return None

    # Patch the instance methods
    monkeypatch.setattr(s, "_pick_href", fake_pick_href)
    monkeypatch.setattr(s, "_reconstruct_abstract", fake_reconstruct)

    # Fake requests.get to capture params and return FakeResponse
    def fake_get(url, params=None, timeout=None):
        calls_params.append({"url": url, "params": params, "timeout": timeout})
        return FakeResponse(results)

    monkeypatch.setattr(
        "gpt_researcher.retrievers.openalex.openalex.requests.get", fake_get
    )

    # Call with a large max_results to ensure per_page is capped at 25
    search_results = s.search(max_results=100)

    # There should be two appended results: first and third (second had href None)
    assert len(search_results) == 2

    # Validate first appended entry (original title None => "No Title", abstract not available)
    first = search_results[0]
    assert first["title"] == "No Title"
    assert first["href"] == "http://example.com/1"
    assert first["body"] == "Abstract not available"

    # Validate second appended entry (Third)
    second = search_results[1]
    assert second["title"] == "Third"
    assert second["href"] == "http://example.com/3"
    assert second["body"] == "Some abstract"

    # Inspect captured params for the first call
    assert calls_params, "requests.get was not called"
    first_call = calls_params[0]
    params = first_call["params"]
    assert first_call["url"] == s.BASE_URL
    assert params["search"] == s.query
    assert params["mailto"] == "tester@example.com"
    assert params["api_key"] == "apikey123"
    assert params["sort"] == s.sort
    # per_page should be capped at 25 for max_results=100
    assert params["per_page"] == 25

    # Now call again with a smaller max_results to ensure per_page uses min(max_results, 25)
    s.search(max_results=5)
    assert calls_params[1]["params"]["per_page"] == 5
