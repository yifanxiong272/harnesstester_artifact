# file: gpt_researcher/retrievers/custom/custom.py:6-52
# asked: {"lines": [12, 13, 14, 16, 17, 23, 24, 25, 26, 46, 47, 48, 49, 50, 51, 52], "branches": [[13, 14], [13, 16]]}
# gained: {"lines": [12, 13, 14, 16, 17, 23, 24, 25, 26, 46, 47, 48, 49, 50, 51, 52], "branches": [[13, 14], [13, 16]]}

import os
import pytest

from gpt_researcher.retrievers.custom import custom as custom_mod
from gpt_researcher.retrievers.custom.custom import CustomRetriever


def test_init_raises_when_no_env(monkeypatch):
    # Ensure the RETRIEVER_ENDPOINT is not set
    monkeypatch.delenv('RETRIEVER_ENDPOINT', raising=False)
    # Also ensure any RETRIEVER_ARG_ vars do not interfere
    monkeypatch.delenv('RETRIEVER_ARG_FOO', raising=False)

    with pytest.raises(ValueError) as exc:
        CustomRetriever("query")
    assert "RETRIEVER_ENDPOINT environment variable not set" in str(exc.value)


def test_populate_params_and_init_sets_params_and_query(monkeypatch):
    # Set endpoint and some RETRIEVER_ARG_ environment variables
    monkeypatch.setenv('RETRIEVER_ENDPOINT', 'http://example.local')
    monkeypatch.setenv('RETRIEVER_ARG_FOO', 'bar')
    monkeypatch.setenv('RETRIEVER_ARG_BAZ', '123')

    retriever = CustomRetriever("my-query")

    # Verify endpoint, params and query populated correctly
    assert retriever.endpoint == 'http://example.local'
    # Keys should be lowercased versions of suffixes after RETRIEVER_ARG_
    assert retriever.params == {'foo': 'bar', 'baz': '123'}
    assert retriever.query == 'my-query'


def test_search_success_calls_requests_get_and_returns_json(monkeypatch):
    # Prepare environment and retriever
    monkeypatch.setenv('RETRIEVER_ENDPOINT', 'http://api.test/search')
    monkeypatch.delenv('RETRIEVER_ARG_FOO', raising=False)

    retriever = CustomRetriever("search-term")

    expected = [
        {"url": "http://example.com/page1", "raw_content": "Content 1"},
        {"url": "http://example.com/page2", "raw_content": "Content 2"},
    ]

    class FakeResponse:
        def raise_for_status(self):
            return None

        def json(self):
            return expected

    # Define fake get that asserts it's called with the right endpoint and params
    def fake_get(url, params=None):
        assert url == retriever.endpoint
        # params should contain at least 'query'
        assert isinstance(params, dict)
        assert params.get('query') == retriever.query
        return FakeResponse()

    # Patch requests.get used in the module
    monkeypatch.setattr(custom_mod.requests, 'get', fake_get)

    result = retriever.search(max_results=10)
    assert result == expected


def test_search_handles_request_exception_and_returns_none(monkeypatch, capsys):
    # Prepare environment and retriever
    monkeypatch.setenv('RETRIEVER_ENDPOINT', 'http://api.test/fail')

    retriever = CustomRetriever("will-fail")

    # Define fake get that raises RequestException
    def fake_get_raises(url, params=None):
        raise custom_mod.requests.RequestException("network failure")

    monkeypatch.setattr(custom_mod.requests, 'get', fake_get_raises)

    result = retriever.search()
    captured = capsys.readouterr()
    assert result is None
    assert "Failed to retrieve search results" in captured.out
