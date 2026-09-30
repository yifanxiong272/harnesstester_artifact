# file: gpt_researcher/retrievers/google/google.py:53-100
# asked: {"lines": [60, 61, 62, 63, 65, 67, 68, 70, 71, 73, 74, 75, 76, 77, 78, 79, 80, 82, 83, 86, 88, 89, 90, 91, 92, 93, 94, 96, 97, 98, 100], "branches": [[61, 62], [61, 65], [70, 71], [70, 73], [73, 74], [73, 75], [79, 80], [79, 82], [86, 88], [86, 100], [88, 89], [88, 90]]}
# gained: {"lines": [60, 61, 62, 63, 65, 67, 68, 70, 71, 73, 75, 76, 77, 78, 79, 80, 82, 83, 86, 88, 89, 90, 91, 92, 93, 94, 96, 97, 98, 100], "branches": [[61, 62], [61, 65], [70, 71], [70, 73], [73, 75], [79, 80], [79, 82], [86, 88], [86, 100], [88, 89], [88, 90]]}

import json
import pytest

from gpt_researcher.retrievers.google.google import GoogleSearch


class MockResponse:
    def __init__(self, status_code=200, text=""):
        self.status_code = status_code
        self.text = text


def test_search_with_domains_and_non_2xx_status_and_youtube_skip(monkeypatch, capsys):
    # Prepare search object with explicit API keys to avoid get_api_key/get_cx_key calls
    gs = GoogleSearch("my query", headers={"google_api_key": "API", "google_cx_key": "CX"})
    gs.query_domains = ["example.com", "foo.com"]

    # Prepare response containing one normal item and one youtube item (which should be skipped)
    data = {
        "items": [
            {"title": "Result 1", "link": "https://example.com/page1", "snippet": "Snippet 1"},
            {"title": "YouTube Video", "link": "https://www.youtube.com/watch?v=abc", "snippet": "YT Snippet"},
        ]
    }
    mock_resp = MockResponse(status_code=500, text=json.dumps(data))

    # Monkeypatch requests.get used inside the module
    monkeypatch.setattr(
        "gpt_researcher.retrievers.google.google.requests.get",
        lambda url: mock_resp,
    )

    # Execute search with max_results=2 (but one result is youtube and should be skipped)
    results = gs.search(max_results=2)

    # Assert that the non-youtube result is returned and has the expected normalized keys
    assert isinstance(results, list)
    assert len(results) == 1
    assert results[0] == {
        "title": "Result 1",
        "href": "https://example.com/page1",
        "body": "Snippet 1",
    }

    # Capture printed output to ensure the non-2xx status and query with domains were printed
    captured = capsys.readouterr()
    assert "Searching with query" in captured.out
    # The domain query should appear in the printed search query
    assert "(site:example.com OR site:foo.com) my query" in captured.out
    # Non-2xx status message should be printed
    assert "unexpected response status" in captured.out


def test_search_returns_none_on_json_null(monkeypatch):
    gs = GoogleSearch("q", headers={"google_api_key": "API", "google_cx_key": "CX"})
    gs.query_domains = None

    # Response text is 'null' which json.loads -> None, triggering the search_results is None branch
    mock_resp = MockResponse(status_code=200, text="null")

    monkeypatch.setattr(
        "gpt_researcher.retrievers.google.google.requests.get",
        lambda url: mock_resp,
    )

    result = gs.search()
    assert result is None


def test_search_returns_none_on_json_parse_error(monkeypatch):
    gs = GoogleSearch("q2", headers={"google_api_key": "API", "google_cx_key": "CX"})
    # Create a response with invalid JSON so json.loads will raise
    mock_resp = MockResponse(status_code=200, text="this is not json")

    monkeypatch.setattr(
        "gpt_researcher.retrievers.google.google.requests.get",
        lambda url: mock_resp,
    )

    result = gs.search()
    assert result is None


def test_search_handles_missing_fields_and_only_includes_valid_items(monkeypatch):
    gs = GoogleSearch("another query", headers={"google_api_key": "API", "google_cx_key": "CX"})
    # Items:
    # - one missing 'title' -> should trigger the except and be skipped
    # - one youtube link -> should be skipped
    # - one valid item -> should be included
    data = {
        "items": [
            {"link": "https://example.com/no_title", "snippet": "No title snippet"},
            {"title": "YT", "link": "https://youtube.com/watch?v=1", "snippet": "yt"},
            {"title": "Good", "link": "https://good.example/page", "snippet": "Good snippet"},
        ]
    }
    mock_resp = MockResponse(status_code=200, text=json.dumps(data))

    monkeypatch.setattr(
        "gpt_researcher.retrievers.google.google.requests.get",
        lambda url: mock_resp,
    )

    results = gs.search(max_results=10)
    # Only the valid non-youtube item should be present
    assert isinstance(results, list)
    assert len(results) == 1
    assert results[0]["title"] == "Good"
    assert results[0]["href"] == "https://good.example/page"
    assert results[0]["body"] == "Good snippet"
