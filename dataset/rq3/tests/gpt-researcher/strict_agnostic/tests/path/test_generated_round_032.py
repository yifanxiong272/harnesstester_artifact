import pytest

from gpt_researcher.retrievers.searchapi.searchapi import SearchApiSearch


class FakeResponse:
    def __init__(self, status_code=200, data=None):
        self.status_code = status_code
        self._data = data

    def json(self):
        return self._data


def make_fake_get(return_value=None, raise_exc=None, record=None):
    """
    Create a fake requests.get replacement.
    - return_value: FakeResponse to return
    - raise_exc: Exception instance to raise
    - record: dict to store call arguments
    """
    def fake_get(url, headers=None, timeout=None):
        if record is not None:
            record.setdefault('url', url)
            record.setdefault('headers', headers)
            record.setdefault('timeout', timeout)
        if raise_exc:
            raise raise_exc
        return return_value

    return fake_get


def test_success_with_results_round_032(monkeypatch):
    """Hit status_code==200, skip youtube results, and stop after reaching max_results.

    The SearchApiSearch.__init__ reads SEARCHAPI_API_KEY from the environment;
    ensure it's set to avoid initialization exceptions.
    """
    # Ensure the environment key is present so __init__ does not raise
    monkeypatch.setenv('SEARCHAPI_API_KEY', 'TESTKEY123')

    # Prepare a response with multiple organic_results including a youtube link
    organic = [
        {"title": "Yt Video", "link": "https://www.youtube.com/watch?v=abc", "snippet": "yt"},
        {"title": "Result 1", "link": "https://example.com/1", "snippet": "one"},
        {"title": "Result 2", "link": "https://example.com/2", "snippet": "two"},
        {"title": "Result 3", "link": "https://example.com/3", "snippet": "three"},
    ]
    payload = {"organic_results": organic}
    fake_resp = FakeResponse(status_code=200, data=payload)

    record = {}
    monkeypatch.setattr('requests.get', make_fake_get(return_value=fake_resp, record=record))

    s = SearchApiSearch("hello world", None)

    # Request max_results=2 to exercise the break when results_processed>=max_results
    results = s.search(max_results=2)

    # Expect two non-youtube results returned, in the same order they appear
    assert isinstance(results, list)
    assert len(results) == 2
    assert results[0]["title"] == "Result 1"
    assert results[0]["href"] == "https://example.com/1"
    assert results[1]["title"] == "Result 2"

    # Check that the youtube result was skipped and not present
    assert all("youtube.com" not in r["href"] for r in results)

    # Validate that requests.get was called with an Authorization header containing the API key
    assert record.get('headers') is not None
    assert 'Authorization' in record['headers']
    assert record['headers']['Authorization'] == f"Bearer {s.api_key}"
    # Also verify the encoded query is present in the URL (space encoded as +)
    assert 'q=hello+world' in record['url']


def test_non_200_returns_empty_round_032(monkeypatch):
    """When response.status_code != 200, an empty list should be returned."""
    monkeypatch.setenv('SEARCHAPI_API_KEY', 'KEY')

    fake_resp = FakeResponse(status_code=500, data={"organic_results": [{"title": "x"}]})
    record = {}
    monkeypatch.setattr('requests.get', make_fake_get(return_value=fake_resp, record=record))

    s = SearchApiSearch("a b", None)

    result = s.search()
    assert result == []

    # Ensure the encoded query appears in the URL (space -> +)
    assert 'q=a+b' in record['url']


def test_status_200_but_empty_json_round_032(monkeypatch):
    """When response.json() is falsy (e.g., {}), the function should return an empty list."""
    monkeypatch.setenv('SEARCHAPI_API_KEY', 'K')

    fake_resp = FakeResponse(status_code=200, data={})
    monkeypatch.setattr('requests.get', make_fake_get(return_value=fake_resp))

    s = SearchApiSearch("nothing", None)

    result = s.search()
    assert result == []


def test_exception_during_request_round_032(monkeypatch):
    """If requests.get raises an exception, the function returns an empty list (handled by except)."""
    monkeypatch.setenv('SEARCHAPI_API_KEY', 'K')

    monkeypatch.setattr('requests.get', make_fake_get(raise_exc=RuntimeError('boom')))

    s = SearchApiSearch("err", None)

    result = s.search()
    assert result == []
