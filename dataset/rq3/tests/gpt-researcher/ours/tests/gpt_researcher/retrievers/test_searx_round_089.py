import importlib
import json
import requests
import pytest

# Import the module under test
module = importlib.import_module('gpt_researcher.retrievers.searx.searx')
SearxSearch = module.SearxSearch


class MockResponse:
    def __init__(self, json_data=None, raise_exc=None):
        # json_data can be a mapping or an Exception to raise from json()
        self._json_data = json_data
        self._raise_exc = raise_exc

    def raise_for_status(self):
        if self._raise_exc:
            raise self._raise_exc

    def json(self):
        if isinstance(self._json_data, Exception):
            raise self._json_data
        return self._json_data


def make_instance(base_url: str = "http://example.com/", query: str = "test"):
    # Create an instance without invoking __init__ to control attributes precisely
    inst = SearxSearch.__new__(SearxSearch)
    inst.base_url = base_url
    inst.query = query
    return inst


def test_search_success_round_089(monkeypatch):
    """Non-empty results: ensure mapping of url->href and content->body and max_results slicing."""
    # Prepare results with more items than max_results and some missing keys
    results_payload = {
        'results': [
            {'url': 'http://a.example/', 'content': 'Alpha'},
            {'content': 'NoURL'},  # missing url -> empty string expected
            {'url': 'http://b.example/', 'content': 'Beta'},
        ]
    }

    def mock_get(url, params=None, headers=None):
        # verify the function receives the expected search path
        assert url.endswith('search')
        # Ensure the params propagate the query
        assert params is not None and params.get('q') == 'term'
        return MockResponse(json_data=results_payload)

    monkeypatch.setattr(module.requests, 'get', mock_get)

    inst = make_instance(base_url='http://example.com/', query='term')

    # Request only 2 results, expect the first two mapped
    out = SearxSearch.search(inst, max_results=2)

    assert isinstance(out, list)
    assert len(out) == 2

    # First result preserves url and content
    assert out[0]['href'] == 'http://a.example/'
    assert out[0]['body'] == 'Alpha'

    # Second result had no url in payload -> default to empty string
    assert out[1]['href'] == ''
    assert out[1]['body'] == 'NoURL'


def test_search_empty_results_round_089(monkeypatch):
    """Empty or missing 'results' key should produce an empty list without errors."""
    # payload missing 'results' key entirely
    results_payload = {}

    def mock_get(url, params=None, headers=None):
        return MockResponse(json_data=results_payload)

    monkeypatch.setattr(module.requests, 'get', mock_get)

    inst = make_instance(base_url='http://example.com/', query='nothing')

    out = SearxSearch.search(inst, max_results=5)

    assert out == []


def test_search_http_error_round_089(monkeypatch):
    """requests.get raising a RequestException or response.raise_for_status causing a RequestException
    should be wrapped and re-raised with the specific message prefix."""

    # Case A: requests.get raises directly
    def mock_get_raises(url, params=None, headers=None):
        raise requests.exceptions.RequestException('network down')

    monkeypatch.setattr(module.requests, 'get', mock_get_raises)
    inst = make_instance()

    with pytest.raises(Exception) as excinfo:
        SearxSearch.search(inst, max_results=1)
    assert 'Error querying SearxNG:' in str(excinfo.value)
    assert 'network down' in str(excinfo.value)

    # Case B: response.raise_for_status raises an HTTPError
    def mock_get_http_error(url, params=None, headers=None):
        return MockResponse(json_data={'results': []}, raise_exc=requests.exceptions.HTTPError('bad status'))

    monkeypatch.setattr(module.requests, 'get', mock_get_http_error)

    with pytest.raises(Exception) as excinfo2:
        SearxSearch.search(inst, max_results=1)
    assert 'Error querying SearxNG:' in str(excinfo2.value)
    assert 'bad status' in str(excinfo2.value)


def test_search_json_error_round_089(monkeypatch):
    """If response.json() raises JSONDecodeError, it should be caught and a parsing Exception raised."""
    # Construct a JSONDecodeError instance
    jde = json.JSONDecodeError('Expecting value', doc='}', pos=0)

    def mock_get_broken_json(url, params=None, headers=None):
        return MockResponse(json_data=jde)

    monkeypatch.setattr(module.requests, 'get', mock_get_broken_json)

    inst = make_instance()

    with pytest.raises(Exception) as excinfo:
        SearxSearch.search(inst, max_results=3)

    assert str(excinfo.value) == 'Error parsing SearxNG response'
