import requests
import pytest

from gpt_researcher.retrievers.semantic_scholar.semantic_scholar import SemanticScholarSearch


class _FakeResponse:
    def __init__(self, payload, raise_on_status=False):
        # payload should be a dict returned by .json()
        self._payload = payload
        self._raise = raise_on_status

    def raise_for_status(self):
        if self._raise:
            raise requests.RequestException("simulated status error")

    def json(self):
        return self._payload


def test_search_success_open_access_round_080(monkeypatch):
    """Return one valid open-access result and assert it's transformed correctly and params are sent lowercased."""
    captured = {}

    def fake_get(url, params=None):
        # capture the incoming URL and params to assert on them
        captured['url'] = url
        captured['params'] = dict(params) if params is not None else None
        payload = {
            "data": [
                {
                    "title": "Example Paper",
                    "abstract": "An abstract",
                    "isOpenAccess": True,
                    "openAccessPdf": {"url": "http://example.com/paper.pdf"},
                }
            ]
        }
        return _FakeResponse(payload)

    monkeypatch.setattr(
        "gpt_researcher.retrievers.semantic_scholar.semantic_scholar.requests.get",
        fake_get,
    )

    s = SemanticScholarSearch(query="quantum", sort="citationCount")
    results = s.search(max_results=5)

    # verify the requests.get was called with the class BASE_URL and lowercase sort
    assert captured['url'] == SemanticScholarSearch.BASE_URL
    assert captured['params']['limit'] == 5
    # __init__ lowercases the sort
    assert captured['params']['sort'] == "citationcount"

    # verify returned structure and values
    assert isinstance(results, list) and len(results) == 1
    r = results[0]
    assert r["title"] == "Example Paper"
    assert r["href"] == "http://example.com/paper.pdf"
    assert r["body"] == "An abstract"


def test_search_skips_non_matching_and_uses_defaults_round_080(monkeypatch):
    """Provide multiple results where only one qualifies; that qualifying result lacks title/abstract/url keys to exercise default fallbacks."""

    def fake_get(url, params=None):
        payload = {
            "data": [
                # non-open-access -> should be skipped
                {"title": "Closed", "isOpenAccess": False, "openAccessPdf": {"url": "http://x"}},
                # open access but openAccessPdf is falsy -> skipped
                {"title": "NoPDF", "isOpenAccess": True, "openAccessPdf": None},
                # qualifies but missing title/abstract and openAccessPdf has no url -> defaults used
                {"isOpenAccess": True, "openAccessPdf": {"other": "val"}},
            ]
        }
        return _FakeResponse(payload)

    monkeypatch.setattr(
        "gpt_researcher.retrievers.semantic_scholar.semantic_scholar.requests.get",
        fake_get,
    )

    s = SemanticScholarSearch(query="q", sort="relevance")
    results = s.search(max_results=2)

    # Only the last entry should qualify
    assert isinstance(results, list) and len(results) == 1
    r = results[0]
    # missing title -> default "No Title"
    assert r["title"] == "No Title"
    # openAccessPdf present but missing 'url' key -> default "No URL"
    assert r["href"] == "No URL"
    # missing abstract -> default message
    assert r["body"] == "Abstract not available"


def test_search_empty_results_round_080(monkeypatch):
    """When API returns no data key or empty data list, search should return empty list (loop not entered)."""

    def fake_get_empty(url, params=None):
        # return payload without data key
        return _FakeResponse({})

    monkeypatch.setattr(
        "gpt_researcher.retrievers.semantic_scholar.semantic_scholar.requests.get",
        fake_get_empty,
    )

    s = SemanticScholarSearch(query="nothing", sort="publicationDate")
    results = s.search(max_results=1)

    assert results == []


def test_search_handles_request_exception_round_080(monkeypatch, capsys):
    """Simulate raise_for_status throwing to hit the except branch and ensure empty list is returned and message printed."""

    def fake_get_raise(url, params=None):
        return _FakeResponse({"data": []}, raise_on_status=True)

    monkeypatch.setattr(
        "gpt_researcher.retrievers.semantic_scholar.semantic_scholar.requests.get",
        fake_get_raise,
    )

    s = SemanticScholarSearch(query="err", sort="relevance")
    results = s.search(max_results=3)

    # exception path should return empty list
    assert results == []

    # and a message should have been printed about the RequestException
    captured = capsys.readouterr()
    assert "An error occurred while accessing Semantic Scholar API" in captured.out
