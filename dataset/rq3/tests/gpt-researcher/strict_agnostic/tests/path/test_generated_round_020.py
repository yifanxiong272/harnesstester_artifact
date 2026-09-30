import json
import pytest

from gpt_researcher.retrievers.serper import serper as serper_mod
from gpt_researcher.retrievers.serper.serper import SerperSearch


class _Resp:
    def __init__(self, text):
        self.text = text


def test_search_resp_none_round_020(monkeypatch):
    """Ensure that when requests.request returns None the search method returns None."""
    # Ensure SERPER_API_KEY exists so __init__ doesn't raise
    monkeypatch.setenv("SERPER_API_KEY", "DUMMY_KEY_NONE")

    # Arrange
    s = SerperSearch("q")

    # Patch requests.request to simulate no response (resp is None)
    monkeypatch.setattr(serper_mod.requests, "request", lambda *args, **kwargs: None)

    # Act
    result = s.search()

    # Assert
    assert result is None


def test_search_invalid_json_round_020(monkeypatch):
    """When the response contains invalid JSON, search should catch the exception and return None.
    Also assert that the request was invoked with the expected API key and that the payload
    contains the query key.
    """
    monkeypatch.setenv("SERPER_API_KEY", "INITIAL_KEY_INVALID_JSON")
    captured = {}

    def fake_request(method, url, timeout=None, headers=None, data=None):
        # Capture the call parameters for later inspection
        captured["method"] = method
        captured["url"] = url
        captured["timeout"] = timeout
        captured["headers"] = headers
        captured["data"] = data
        return _Resp("not a json")

    monkeypatch.setattr(serper_mod.requests, "request", fake_request)

    s = SerperSearch("some query")
    # Ensure an API key is present so headers are populated; override to check header propagation
    s.api_key = "API_INVALID_JSON"

    # Act
    result = s.search()

    # Assert behavior: invalid JSON leads to None
    assert result is None

    # Assert that our fake_request was called and headers/data were passed in
    assert captured["headers"]["X-API-KEY"] == "API_INVALID_JSON"
    # The data field should be a JSON-encoded string containing the q (query) key
    parsed = json.loads(captured["data"])
    assert "q" in parsed
    assert parsed["q"].startswith("some query")


def test_search_json_null_round_020(monkeypatch):
    """When the response JSON is null (None), the search method should return None."""
    monkeypatch.setenv("SERPER_API_KEY", "KEY_NULL_ENV")

    def fake_request(method, url, timeout=None, headers=None, data=None):
        return _Resp("null")

    monkeypatch.setattr(serper_mod.requests, "request", fake_request)

    s = SerperSearch("q-null")

    result = s.search()

    assert result is None


def test_search_success_with_filters_round_020(monkeypatch, capsys):
    """Full successful flow: exercise exclude_sites, query_domains and optional parameters
    to ensure the built query and params are passed to requests.request, and that organic
    results are normalized to the expected format.
    """
    monkeypatch.setenv("SERPER_API_KEY", "API_FILTERS_ENV")
    captured = {}

    def fake_request(method, url, timeout=None, headers=None, data=None):
        captured["method"] = method
        captured["url"] = url
        captured["timeout"] = timeout
        captured["headers"] = headers
        captured["data"] = data
        # Return a valid JSON response with an organic result
        payload = {"organic": [{"title": "Title", "link": "http://example.com/page", "snippet": "Summary"}]}
        return _Resp(json.dumps(payload))

    monkeypatch.setattr(serper_mod.requests, "request", fake_request)

    s = SerperSearch("basequery")
    # populate filters that exercise multiple branches
    # override api_key to assert header usage later
    s.api_key = "API_FILTERS"
    s.exclude_sites = ["ex.com"]
    s.query_domains = ["a.com", "b.com"]
    s.country = "US"
    s.language = "en"
    s.time_range = "qdr:h"

    # Act
    result = s.search(max_results=5)

    # Assert the HTTP call was made as expected
    assert captured["method"] == "POST"
    assert captured["url"].endswith("/search")
    assert captured["headers"]["X-API-KEY"] == "API_FILTERS"

    # Inspect the JSON body sent to the API
    sent = json.loads(captured["data"])
    # The query should include the exclude-site token we provided
    assert "-site:ex.com" in sent["q"]
    # The domain query uses ' site:' prefix and OR between domains
    assert "site:a.com" in sent["q"] and "site:b.com" in sent["q"]

    # Optional parameters should be present
    assert sent.get("gl") == "US"
    assert sent.get("hl") == "en"
    assert sent.get("tbs") == "qdr:h"
    assert sent.get("num") == 5

    # The returned results should be normalized to title/href/body
    assert isinstance(result, list) and len(result) == 1
    assert result[0]["title"] == "Title"
    assert result[0]["href"] == "http://example.com/page"
    assert result[0]["body"] == "Summary"

    # The function prints a searching message; confirm it appeared
    printed = capsys.readouterr().out
    assert "Searching with query basequery..." in printed
