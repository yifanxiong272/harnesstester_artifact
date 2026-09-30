# file: gpt_researcher/retrievers/xquik/xquik.py:54-94
# asked: {"lines": [55, 56, 57, 58, 60, 62, 63, 64, 65, 68, 69, 71, 72, 74, 75, 76, 77, 78, 80, 81, 82, 84, 85, 86, 88, 89, 90, 91, 94], "branches": [[74, 75], [74, 94], [85, 86], [85, 88]]}
# gained: {"lines": [55, 56, 57, 58, 60, 62, 63, 64, 65, 68, 69, 71, 72, 74, 75, 76, 77, 78, 80, 81, 82, 84, 85, 86, 88, 89, 90, 91, 94], "branches": [[74, 75], [74, 94], [85, 86], [85, 88]]}

import json
import urllib
import pytest

from gpt_researcher.retrievers.xquik.xquik import XquikSearch


class DummyResponse:
    def __init__(self, data_bytes):
        self._data = data_bytes

    def read(self):
        return self._data

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


def _make_req_assertions(req, expected_query, expected_limit, expected_api_key):
    # Check URL contains encoded query and correct limit and queryType
    assert hasattr(req, "full_url")
    full = req.full_url
    # Query should be URL-encoded (spaces -> +)
    assert f"q={urllib.parse.quote_plus(expected_query)}" in full
    assert f"limit={expected_limit}" in full
    assert "queryType=Top" in full

    # Headers via Request.header_items (case-insensitive)
    headers = {k.lower(): v for k, v in req.header_items()}
    assert headers.get("x-api-key") == expected_api_key
    assert headers.get("accept") == "application/json"
    assert headers.get("user-agent") == "gpt-researcher/1.0"


def test_search_tweets_with_views_and_truncation_and_limit(monkeypatch):
    # Ensure get_api_key returns a known key
    monkeypatch.setattr(XquikSearch, "get_api_key", lambda self: "FAKEKEY123")

    # Create an instance with a query that will be URL-encoded
    qs = XquikSearch("some query with spaces")

    # Prepare a tweet with long text (>120 chars) and views present
    long_text = "x" * 150
    tweet = {
        "author": {"username": "alice"},
        "text": long_text,
        "id": "12345",
        "likeCount": 10,
        "retweetCount": 2,
        "viewCount": 500,
    }
    data = {"tweets": [tweet]}

    # Monkeypatch urllib.request.urlopen to assert request and return our data
    def fake_urlopen(req, timeout=...):
        _make_req_assertions(req, expected_query="some query with spaces", expected_limit=200, expected_api_key="FAKEKEY123")
        return DummyResponse(json.dumps(data).encode("utf-8"))

    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)

    # Call with max_results > 200 to trigger min(max_results, 200) branch
    results = qs._search_tweets(500)

    # One result expected
    assert isinstance(results, list) and len(results) == 1
    r = results[0]

    # Title should be truncated to 120 chars + '...'
    expected_title = f"@alice: {long_text[:120]}..."
    assert r["title"] == expected_title

    # href should include username and id
    assert r["href"] == "https://x.com/alice/status/12345"

    # Body should contain full text and engagement including views
    assert r["body"].startswith(long_text)
    assert "[10 likes, 2 RTs, 500 views]" in r["body"]


def test_search_tweets_missing_fields_and_no_views_defaults(monkeypatch):
    # Ensure get_api_key returns a known key
    monkeypatch.setattr(XquikSearch, "get_api_key", lambda self: "KEY2")

    qs = XquikSearch("empty")

    # Tweet missing many fields, viewCount absent (interpreted as 0)
    tweet = {
        # intentionally empty
    }
    data = {"tweets": [tweet]}

    # Monkeypatch urllib.request.urlopen to assert request and return our data
    def fake_urlopen(req, timeout=...):
        _make_req_assertions(req, expected_query="empty", expected_limit=5, expected_api_key="KEY2")
        return DummyResponse(json.dumps(data).encode("utf-8"))

    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)

    results = qs._search_tweets(5)

    assert isinstance(results, list) and len(results) == 1
    r = results[0]

    # Defaults: username -> unknown, text -> ""
    assert r["title"] == "@unknown: "

    # href should have trailing status/ (empty id)
    assert r["href"] == "https://x.com/unknown/status/"

    # Body should contain empty text and engagement with zeros and no 'views' mention
    assert r["body"].startswith("\n\n[")
    assert "[0 likes, 0 RTs]" in r["body"]
    assert "views" not in r["body"]
