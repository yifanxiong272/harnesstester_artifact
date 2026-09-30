import json
import pytest

from gpt_researcher.retrievers.serper.serper import SerperSearch


class _Resp:
    def __init__(self, text):
        self.text = text


def test_search_resp_none_round_020(monkeypatch):
    # Ensure API key is present so __init__ does not raise
    monkeypatch.setenv('SERPER_API_KEY', 'test-key')

    # Patch requests.request used inside SerperSearch.search to return None
    monkeypatch.setattr(
        'gpt_researcher.retrievers.serper.serper.requests.request',
        lambda *args, **kwargs: None,
    )

    s = SerperSearch("q", None, None, None, None, None)
    # When the underlying request returns None, search should return None
    assert s.search() is None


def test_search_invalid_json_round_020(monkeypatch):
    # Ensure API key is present so __init__ does not raise
    monkeypatch.setenv('SERPER_API_KEY', 'test-key')

    # Patch to return a response object with invalid JSON in .text
    def fake_request(*args, **kwargs):
        return _Resp("not a json string")

    monkeypatch.setattr(
        'gpt_researcher.retrievers.serper.serper.requests.request',
        fake_request,
    )

    s = SerperSearch("q", None, None, None, None, None)

    # JSON decode fails -> search returns None
    assert s.search() is None


def test_search_search_results_none_round_020(monkeypatch):
    # Ensure API key is present so __init__ does not raise
    monkeypatch.setenv('SERPER_API_KEY', 'test-key')

    # Patch to return a response whose text is JSON null (-> Python None)
    def fake_request(*args, **kwargs):
        return _Resp("null")

    monkeypatch.setattr(
        'gpt_researcher.retrievers.serper.serper.requests.request',
        fake_request,
    )

    s = SerperSearch("q", None, None, None, None, None)

    # search_results becomes None -> function returns None
    assert s.search() is None


def test_search_success_with_filters_and_params_round_020(monkeypatch):
    # Ensure API key is present so __init__ does not raise
    monkeypatch.setenv('SERPER_API_KEY', 'very-secret-key')

    # This test verifies that query filters (exclude_sites and query_domains)
    # and optional params (country, language, time_range) are included in
    # the outgoing request payload and that results are normalized.

    captured = {}

    def fake_request(method, url, timeout, headers, data):
        # capture invocation details for assertions
        captured['method'] = method
        captured['url'] = url
        captured['timeout'] = timeout
        captured['headers'] = headers
        captured['data'] = data

        # Return a well-formed JSON response with one organic result
        payload = {
            "organic": [
                {"title": "T", "link": "http://x", "snippet": "s"}
            ]
        }
        return _Resp(json.dumps(payload))

    monkeypatch.setattr(
        'gpt_researcher.retrievers.serper.serper.requests.request',
        fake_request,
    )

    s = SerperSearch(
        "hello",
        ["a.com", "b.com"],  # query_domains
        "US",                 # country
        "en",                 # language
        "qdr:d",              # time_range
        ["spam.com", "ads.example"]  # exclude_sites
    )

    # Call with a non-default max_results to ensure 'num' placement
    results = s.search(max_results=3)

    # Verify the outgoing HTTP request was a POST to the expected host
    assert captured['method'] == "POST"
    assert captured['url'].endswith('/search')
    assert captured['timeout'] == 10

    # Headers should include the API key and content type
    assert captured['headers']['X-API-KEY'] == "very-secret-key"
    assert captured['headers']['Content-Type'] == 'application/json'

    # The payload data should decode to a dict with expected keys
    sent = json.loads(captured['data'])
    # 'q' should contain the original query, exclude site modifiers, and domain query
    assert "hello" in sent['q']
    # exclude sites were appended with -site:... for each site
    assert "-site:spam.com" in sent['q'] and "-site:ads.example" in sent['q']
    # domain query is prefixed with a space and uses OR between domains
    assert "site:a.com OR site:b.com" in sent['q']

    # Optional parameters should be present
    assert sent['gl'] == "US"
    assert sent['hl'] == "en"
    assert sent['tbs'] == "qdr:d"

    # num should match the max_results passed
    assert sent['num'] == 3

    # Verify normalized output structure
    assert isinstance(results, list)
    assert results == [{"title": "T", "href": "http://x", "body": "s"}]
