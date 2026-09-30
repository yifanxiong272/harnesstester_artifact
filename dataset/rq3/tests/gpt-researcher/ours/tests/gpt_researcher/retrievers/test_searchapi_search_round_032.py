import importlib
from gpt_researcher.retrievers.searchapi import searchapi as searchapi_module
from gpt_researcher.retrievers.searchapi.searchapi import SearchApiSearch


class FakeResponse:
    def __init__(self, status_code, json_data=None):
        self.status_code = status_code
        self._json = json_data

    def json(self):
        return self._json


def test_search_success_with_results_and_youtube_and_max_results_round_032(monkeypatch):
    # Arrange: patch get_api_key to avoid env dependency
    monkeypatch.setattr(searchapi_module.SearchApiSearch, "get_api_key", lambda self: "DUMMY_API_KEY")

    captured = {}

    # Create results: first is youtube (should be skipped), second is a normal result (counted), third would be beyond max and should trigger break
    results_list = [
        {"title": "vid", "link": "https://www.youtube.com/watch?v=abc", "snippet": "yt snippet"},
        {"title": "first", "link": "https://example.com/1", "snippet": "first snippet"},
        {"title": "second", "link": "https://example.com/2", "snippet": "second snippet"},
    ]

    def fake_get(url, headers=None, timeout=None):
        # capture call details so we can assert header and URL were composed as expected
        captured['url'] = url
        captured['headers'] = headers
        captured['timeout'] = timeout
        return FakeResponse(200, {"organic_results": results_list})

    monkeypatch.setattr(searchapi_module, "requests", searchapi_module.requests)
    monkeypatch.setattr(searchapi_module.requests, "get", fake_get)

    # Act: set max_results=1 to force the break after first non-youtube result is processed
    s = SearchApiSearch("my query")
    results = s.search(max_results=1)

    # Assert: youtube entry skipped, only one non-youtube returned
    assert isinstance(results, list)
    assert len(results) == 1
    assert results[0]["title"] == "first"
    assert results[0]["href"] == "https://example.com/1"
    assert results[0]["body"] == "first snippet"

    # Assert: headers contain the Bearer token and custom source header
    assert 'Authorization' in captured['headers']
    assert captured['headers']['Authorization'] == 'Bearer DUMMY_API_KEY'
    assert captured['headers']['X-SearchApi-Source'] == 'gpt-researcher'

    # Assert: encoded URL contains the query parameter
    assert 'q=my+query' in captured['url'] or 'q=my%20query' in captured['url']
    assert captured['timeout'] == 20


def test_search_empty_search_results_round_032(monkeypatch):
    # Arrange: patch API key and make response.json return an empty dict (falsey)
    monkeypatch.setattr(searchapi_module.SearchApiSearch, "get_api_key", lambda self: "DUMMY2")

    def fake_get_empty(url, headers=None, timeout=None):
        return FakeResponse(200, {})

    monkeypatch.setattr(searchapi_module.requests, "get", fake_get_empty)

    # Act
    s = SearchApiSearch("another query")
    results = s.search(max_results=5)

    # Assert: no results when search_results is falsey
    assert results == []


def test_search_non_200_status_returns_empty_round_032(monkeypatch):
    # Arrange: patch API key and simulate non-200 response
    monkeypatch.setattr(searchapi_module.SearchApiSearch, "get_api_key", lambda self: "KEY3")

    def fake_get_404(url, headers=None, timeout=None):
        return FakeResponse(404, {"organic_results": [{"title": "x", "link": "https://example.com/x", "snippet": "x"}]})

    monkeypatch.setattr(searchapi_module.requests, "get", fake_get_404)

    # Act
    s = SearchApiSearch("q")
    results = s.search()

    # Assert: non-200 status leads to empty response (json not processed)
    assert results == []


def test_search_requests_exception_is_handled_round_032(monkeypatch):
    # Arrange: patch API key and have requests.get raise an exception
    monkeypatch.setattr(searchapi_module.SearchApiSearch, "get_api_key", lambda self: "KEY4")

    def fake_get_raises(url, headers=None, timeout=None):
        raise Exception("network error")

    monkeypatch.setattr(searchapi_module.requests, "get", fake_get_raises)

    # Act
    s = SearchApiSearch("q-exc")
    results = s.search()

    # Assert: exception path returns empty list and does not raise
    assert results == []
