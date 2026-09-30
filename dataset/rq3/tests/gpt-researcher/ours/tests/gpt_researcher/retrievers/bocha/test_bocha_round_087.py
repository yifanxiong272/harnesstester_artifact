import pytest
import gpt_researcher.retrievers.bocha.bocha as bocha
from gpt_researcher.retrievers.bocha.bocha import BoChaSearch


class DummyResponse:
    def __init__(self, payload):
        self._payload = payload

    def json(self):
        return self._payload


def test_search_with_results_round_087(monkeypatch):
    # Ensure API key is read from environment without accessing real services
    monkeypatch.setenv('BOCHA_API_KEY', 'testkey123')

    captured = {}

    def fake_post(url, headers=None, json=None):
        # capture the call inputs for assertions
        captured['url'] = url
        captured['headers'] = headers
        captured['json'] = json
        payload = {
            "data": {
                "webPages": {
                    "value": [
                        {"name": "Title1", "url": "https://example.com/page1", "snippet": "Snippet text 1"}
                    ]
                }
            }
        }
        return DummyResponse(payload)

    # Patch the requests.post symbol where the module resolves it
    monkeypatch.setattr(bocha.requests, 'post', fake_post)

    # Provide a query_domains value to exercise the __init__ assignment
    s = BoChaSearch('test-query', query_domains=['domainA'])
    assert s.query == 'test-query'
    assert s.query_domains == ['domainA']

    results = s.search(max_results=3)

    # Assertions that verify correct construction of request
    assert captured['url'] == 'https://api.bochaai.com/v1/web-search'
    assert captured['headers']['Authorization'] == 'Bearer testkey123'
    assert captured['headers']['Content-Type'] == 'application/json'
    assert captured['json']['query'] == 'test-query'
    assert captured['json']['count'] == 3
    assert captured['json']['freshness'] == 'noLimit'
    assert captured['json']['summary'] is True

    # Assertions that verify normalization of provider results
    assert isinstance(results, list)
    assert results == [{
        'title': 'Title1',
        'href': 'https://example.com/page1',
        'body': 'Snippet text 1'
    }]


def test_search_no_results_round_087(monkeypatch):
    # Ensure API key is read from environment without accessing real services
    monkeypatch.setenv('BOCHA_API_KEY', 'anotherkey')

    call_info = {}

    def fake_post_empty(url, headers=None, json=None):
        # capture the provided count to check default behavior
        call_info['count'] = json.get('count')
        return DummyResponse({"data": {"webPages": {"value": []}}})

    monkeypatch.setattr(bocha.requests, 'post', fake_post_empty)

    s = BoChaSearch('no-results')
    results = s.search()  # default max_results should be 7

    # Ensure the default count was sent and empty results produce an empty list
    assert call_info['count'] == 7
    assert results == []
