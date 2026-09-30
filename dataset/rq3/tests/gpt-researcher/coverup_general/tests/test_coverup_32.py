# file: gpt_researcher/retrievers/openalex/openalex.py:44-84
# asked: {"lines": [51, 52, 53, 54, 56, 57, 58, 59, 61, 62, 63, 64, 65, 66, 68, 69, 70, 71, 72, 73, 75, 76, 77, 78, 79, 80, 84], "branches": [[56, 57], [56, 58], [58, 59], [58, 61], [70, 71], [70, 84], [75, 70], [75, 76]]}
# gained: {"lines": [51, 52, 53, 54, 56, 57, 58, 59, 61, 62, 63, 64, 65, 66, 68, 69, 70, 71, 72, 73, 75, 76, 77, 78, 79, 80, 84], "branches": [[56, 57], [56, 58], [58, 59], [58, 61], [70, 71], [70, 84], [75, 70], [75, 76]]}

import pytest
from types import SimpleNamespace

from gpt_researcher.retrievers.openalex import openalex as openalex_mod
from gpt_researcher.retrievers.openalex.openalex import OpenAlexSearch


def test_search_handles_request_exception(monkeypatch, capsys):
    # Arrange: make requests.get raise a RequestException
    def fake_get(*args, **kwargs):
        raise openalex_mod.requests.RequestException("network down")

    monkeypatch.setattr(openalex_mod.requests, "get", fake_get)

    s = OpenAlexSearch("test query")

    # Act
    results = s.search(max_results=5)

    # Assert that exception branch returns empty list and prints an error message
    captured = capsys.readouterr()
    assert results == []
    assert "An error occurred while accessing OpenAlex API" in captured.out


def test_search_builds_params_and_parses_results(monkeypatch):
    captured_params = {}

    # Build fake response JSON with several variations to exercise branches:
    # - result1: has pdf_url -> should pick pdf_url; abstract inverted index reconstructs text
    # - result2: no title -> "No Title"; no pdf_url but has landing_page_url -> pick landing
    # - result3: no pdf or landing but has id -> pick id
    # - result4: no href at all -> should be filtered out
    results_payload = [
        {
            "title": "First Paper",
            "best_oa_location": {"pdf_url": "https://example.org/first.pdf"},
            "abstract_inverted_index": {"world": [2], "hello": [1]},
            "id": "https://openalex.org/W1",
        },
        {
            # missing title
            "best_oa_location": {},
            "primary_location": {"landing_page_url": "https://example.org/landing"},
            "abstract_inverted_index": None,
            "id": "https://openalex.org/W2",
        },
        {
            "title": "Third Paper",
            "best_oa_location": {},
            "primary_location": {},
            "abstract_inverted_index": {},
            "id": "https://openalex.org/W3",
        },
        {
            "title": "No Href Paper",
            "best_oa_location": {},
            "primary_location": {},
            "abstract_inverted_index": {"only": [0]},
            # no id -> should be filtered out (href falsy)
        },
    ]

    class FakeResponse:
        def raise_for_status(self):
            pass

        def json(self):
            return {"results": results_payload}

    def fake_get(url, params=None, timeout=None):
        # Capture params for assertions
        captured_params.update({"url": url, "params": dict(params or {})})
        return FakeResponse()

    # Monkeypatch the requests.get used inside the module
    monkeypatch.setattr(openalex_mod.requests, "get", fake_get)

    # Create an instance and set email and api_key to exercise those branches
    s = OpenAlexSearch("my query", sort="relevance_score:desc")
    s.email = "me@example.com"
    s.api_key = "APIKEY123"

    # Act: request more than 25 to force per_page = 25
    out = s.search(max_results=30)

    # Assert params were built correctly
    assert captured_params["url"] == OpenAlexSearch.BASE_URL
    p = captured_params["params"]
    assert p["search"] == "my query"
    assert p["per_page"] == 25  # min(30,25)
    assert p["sort"] == "relevance_score:desc"
    assert p["mailto"] == "me@example.com"
    assert p["api_key"] == "APIKEY123"

    # Assert returned parsed results: should exclude the entry without any href
    # Expect 3 items appended
    assert isinstance(out, list)
    assert len(out) == 3

    # Check first item: uses pdf_url and reconstructs abstract "hello world"
    first = out[0]
    assert first["title"] == "First Paper"
    assert first["href"] == "https://example.org/first.pdf"
    assert first["body"] == "hello world"  # reconstructed from positions 1 and 2

    # Check second item: missing title -> "No Title", uses landing page, abstract not available
    second = out[1]
    assert second["title"] == "No Title"
    assert second["href"] == "https://example.org/landing"
    assert second["body"] == "Abstract not available"

    # Check third item: uses id as href, empty inverted index treated as None -> "Abstract not available"
    third = out[2]
    assert third["title"] == "Third Paper"
    assert third["href"] == "https://openalex.org/W3"
    assert third["body"] == "Abstract not available"


def test_search_without_email_api_key(monkeypatch):
    # Ensure that when email and api_key are falsy, they are not added to params
    captured_params = {}

    class FakeResponseEmpty:
        def raise_for_status(self):
            pass

        def json(self):
            return {"results": []}

    def fake_get(url, params=None, timeout=None):
        captured_params.update({"url": url, "params": dict(params or {})})
        return FakeResponseEmpty()

    monkeypatch.setattr(openalex_mod.requests, "get", fake_get)

    s = OpenAlexSearch("no creds", sort="publication_date:desc")
    # Explicitly ensure email and api_key are falsy
    s.email = None
    s.api_key = None

    out = s.search(max_results=5)

    # Verify no mailto or api_key in params
    assert "mailto" not in captured_params["params"]
    assert "api_key" not in captured_params["params"]
    # And function returns empty list when there are no results
    assert out == []
