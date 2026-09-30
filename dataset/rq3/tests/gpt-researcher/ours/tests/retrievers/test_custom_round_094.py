import os
import requests
import pytest

from gpt_researcher.retrievers.custom.custom import CustomRetriever


def test_init_raises_when_no_endpoint_round_094(monkeypatch):
    # Ensure RETRIEVER_ENDPOINT is not set so __init__ raises ValueError
    monkeypatch.delenv("RETRIEVER_ENDPOINT", raising=False)

    with pytest.raises(ValueError) as exc:
        CustomRetriever("irrelevant")

    assert "RETRIEVER_ENDPOINT environment variable not set" in str(exc.value)


def test_search_success_populates_params_and_returns_json_round_094(monkeypatch):
    # Arrange environment: set endpoint and some RETRIEVER_ARG_ variables
    endpoint = "http://fake-endpoint.local/search"
    monkeypatch.setenv("RETRIEVER_ENDPOINT", endpoint)
    monkeypatch.setenv("RETRIEVER_ARG_API_KEY", "secret_key")
    monkeypatch.setenv("RETRIEVER_ARG_MODE", "fast")

    captured = {}

    class DummyResponse:
        def raise_for_status(self):
            # Simulate a successful status
            return None

        def json(self):
            return [{"url": "http://example.com/page1", "raw_content": "Content"}]

    def mock_get(url, params=None, **kwargs):
        # Capture the call for assertions and return a dummy response
        captured['url'] = url
        captured['params'] = params
        return DummyResponse()

    # Patch the requests.get symbol where the module under test resolves it
    monkeypatch.setattr("gpt_researcher.retrievers.custom.custom.requests.get", mock_get)

    # Act
    retriever = CustomRetriever("search-term")
    result = retriever.search(max_results=10)

    # Assert
    assert result == [{"url": "http://example.com/page1", "raw_content": "Content"}]
    # Ensure the endpoint was used
    assert captured['url'] == endpoint
    # Expect params to include the lowered keys from RETRIEVER_ARG_ and the query
    expected_params = {"api_key": "secret_key", "mode": "fast", "query": "search-term"}
    assert captured['params'] == expected_params


def test_search_handles_requests_exception_round_094(monkeypatch, capsys):
    # Arrange environment to have an endpoint
    monkeypatch.setenv("RETRIEVER_ENDPOINT", "http://will-fail.local")

    def raising_get(*args, **kwargs):
        raise requests.RequestException("boom")

    # Patch the requests.get used by the module under test
    monkeypatch.setattr("gpt_researcher.retrievers.custom.custom.requests.get", raising_get)

    retriever = CustomRetriever("q")

    # Act
    result = retriever.search()

    # Capture printed output and assert
    captured_out = capsys.readouterr().out

    assert result is None
    assert "Failed to retrieve search results:" in captured_out
    assert "boom" in captured_out
