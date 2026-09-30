import requests
from unittest.mock import patch
from gpt_researcher.retrievers.pubmed_central import pubmed_central
from gpt_researcher.retrievers.pubmed_central.pubmed_central import PubMedCentralSearch


class FakeResponse:
    def __init__(self, payload):
        self._payload = payload

    def raise_for_status(self):
        # emulate successful response
        return None

    def json(self):
        return self._payload


def make_instance(db_type, query="testquery", api_key="API", params=None, base_search_url="http://example.com"):
    # Create an uninitialized instance and set attributes directly to avoid running unknown __init__ logic
    inst = object.__new__(PubMedCentralSearch)
    inst.db_type = db_type
    inst.query = query
    inst.api_key = api_key
    inst.params = params or {}
    inst.base_search_url = base_search_url
    return inst


def test_search_pubmed_builds_filtered_term_and_returns_ids_round_088(capsys):
    inst = make_instance(db_type="pubmed", query="cancer research", api_key="key123")

    captured = {}

    def fake_get(url, params=None):
        # capture the call for assertions and return a fake JSON payload
        captured['url'] = url
        captured['params'] = params
        payload = {"esearchresult": {"idlist": ["PMC1", "PMC2"]}}
        return FakeResponse(payload)

    target = 'gpt_researcher.retrievers.pubmed_central.pubmed_central.requests.get'
    with patch(target, new=fake_get):
        result = inst._search_articles(10)

    # Verify return value
    assert result == ["PMC1", "PMC2"]

    # Verify that the module built a filtered search term for PubMed
    assert captured['url'] == inst.base_search_url
    assert captured['params']['db'] == 'pubmed'
    # term should include both the original query and the full-text filters
    assert "cancer research" in captured['params']['term']
    assert "ffrft[filter] OR pmc[filter]" in captured['params']['term']

    # Output should announce number of found articles
    out = capsys.readouterr().out
    assert "Found 2 articles with full text available" in out


def test_search_pmc_uses_query_directly_and_handles_empty_list_round_088(capsys):
    inst = make_instance(db_type="pmc", query="genetics", api_key=None)

    captured = {}

    def fake_get(url, params=None):
        captured['url'] = url
        captured['params'] = params
        # Return empty idlist to exercise the len==0 branch
        payload = {"esearchresult": {"idlist": []}}
        return FakeResponse(payload)

    target = 'gpt_researcher.retrievers.pubmed_central.pubmed_central.requests.get'
    with patch(target, new=fake_get):
        result = inst._search_articles(5)

    # When db_type != 'pubmed', the search term should be exactly the query
    assert captured['params']['term'] == 'genetics'

    # Should return the empty list from the response
    assert result == []

    # Should have printed that zero articles were found
    out = capsys.readouterr().out
    assert "Found 0 articles with full text available" in out


def test_search_handles_requests_exception_and_returns_none_round_088(capsys):
    inst = make_instance(db_type="pubmed", query="errorcase")

    def raising_get(url, params=None):
        raise requests.RequestException("boom")

    target = 'gpt_researcher.retrievers.pubmed_central.pubmed_central.requests.get'
    with patch(target, new=raising_get):
        result = inst._search_articles(1)

    # On RequestException the method is expected to return None
    assert result is None

    out = capsys.readouterr().out
    # The printed message should include the exception message
    assert "Failed to search articles: boom" in out
