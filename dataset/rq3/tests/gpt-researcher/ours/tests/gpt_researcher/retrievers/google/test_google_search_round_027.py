import json
import pytest

from gpt_researcher.retrievers.google.google import GoogleSearch


class _FakeResp:
    def __init__(self, status_code=200, text=''):
        self.status_code = status_code
        self.text = text


def _make_gs(query="ignore", headers=None, query_domains=None):
    # Provide headers to avoid reading environment variables in get_api_key/get_cx_key
    headers = headers or {"google_api_key": "FAKE_API_KEY", "google_cx_key": "FAKE_CX"}
    gs = GoogleSearch(query, headers, query_domains)
    return gs


def test_search_with_query_domains_round_027(monkeypatch):
    gs = _make_gs(query="hello")
    gs.query = "hello"
    gs.query_domains = ["a.com", "b.com"]

    captured = {}

    def fake_get(url):
        # capture the exact URL used so we can assert the domain query was built
        captured['url'] = url
        return _FakeResp(status_code=200, text=json.dumps({"items": []}))

    monkeypatch.setattr(
        "gpt_researcher.retrievers.google.google.requests.get",
        fake_get,
    )

    result = gs.search()

    # The query should include the constructed domain clause and the original query
    assert captured['url'] is not None
    assert "(site:a.com OR site:b.com) hello" in captured['url']
    # No items were returned by the fake response
    assert result == []


def test_search_handles_non_200_but_parses_json_round_027(monkeypatch):
    gs = _make_gs(query="q")
    gs.query = "q"
    gs.query_domains = None

    def fake_get(url):
        data = {
            "items": [
                {"title": "T1", "link": "http://example.com/1", "snippet": "S1"},
                {"title": "T2", "link": "http://example.com/2", "snippet": "S2"},
            ]
        }
        # use a non-2xx status to exercise that branch but still allow parsing
        return _FakeResp(status_code=500, text=json.dumps(data))

    monkeypatch.setattr(
        "gpt_researcher.retrievers.google.google.requests.get",
        fake_get,
    )

    # Request only one result to exercise slicing
    results = gs.search(max_results=1)

    assert isinstance(results, list)
    assert len(results) == 1
    assert results[0]["title"] == "T1"
    assert results[0]["href"] == "http://example.com/1"
    assert results[0]["body"] == "S1"


def test_search_returns_none_on_invalid_json_round_027(monkeypatch):
    gs = _make_gs(query="q")
    gs.query = "q"

    def fake_get_bad_json(url):
        # invalid JSON text causes json.loads to raise and the method to return None
        return _FakeResp(status_code=200, text="not a json")

    monkeypatch.setattr(
        "gpt_researcher.retrievers.google.google.requests.get",
        fake_get_bad_json,
    )

    result = gs.search()
    assert result is None


def test_search_returns_none_on_null_json_round_027(monkeypatch):
    gs = _make_gs(query="q")
    gs.query = "q"

    def fake_get_null(url):
        # json.loads('null') -> None, which should cause the method to return None
        return _FakeResp(status_code=200, text="null")

    monkeypatch.setattr(
        "gpt_researcher.retrievers.google.google.requests.get",
        fake_get_null,
    )

    result = gs.search()
    assert result is None


def test_search_skips_youtube_and_items_with_missing_fields_round_027(monkeypatch):
    gs = _make_gs(query="q")
    gs.query = "q"

    items = [
        {"title": "YT", "link": "https://youtube.com/watch?v=abc", "snippet": "s"},
        # missing 'title' to trigger the except and continue
        {"link": "http://missing-title", "snippet": "s2"},
        {"title": "Good", "link": "http://good", "snippet": "good snippet"},
    ]

    def fake_get(url):
        return _FakeResp(status_code=200, text=json.dumps({"items": items}))

    monkeypatch.setattr(
        "gpt_researcher.retrievers.google.google.requests.get",
        fake_get,
    )

    results = gs.search()

    # Only the valid non-youtube item with all fields should survive
    assert isinstance(results, list)
    assert len(results) == 1
    assert results[0]["title"] == "Good"
    assert results[0]["href"] == "http://good"
    assert results[0]["body"] == "good snippet"
