import json
from types import SimpleNamespace
import gpt_researcher.retrievers.bing.bing as bing_mod


class DummyResp:
    def __init__(self, text):
        self.text = text


class CapturingLogger:
    def __init__(self):
        self.errors = []
        self.warnings = []

    def error(self, msg):
        self.errors.append(str(msg))

    def warning(self, msg):
        self.warnings.append(str(msg))


def test_search_resp_none_round_038(monkeypatch):
    # Arrange: prepare a fake self and capture calls to requests.get
    calls = []

    def fake_get(url, headers=None, params=None):
        calls.append((url, headers, params))
        return None

    monkeypatch.setattr(bing_mod, "requests", SimpleNamespace(get=fake_get))

    fake_self = SimpleNamespace(query="who cares", api_key="API_KEY_123", logger=CapturingLogger())

    # Act
    result = bing_mod.BingSearch.search(fake_self, max_results=3)

    # Assert: when requests.get returns None the function should return an empty list
    assert result == []
    # requests.get should have been called once with expected url and contain the api key in headers
    assert len(calls) == 1
    called_url, called_headers, called_params = calls[0]
    assert called_url == "https://api.bing.microsoft.com/v7.0/search"
    assert called_headers is not None and called_headers.get('Ocp-Apim-Subscription-Key') == "API_KEY_123"
    assert called_params is not None and called_params.get('q') == "who cares"


def test_search_missing_webpages_key_triggers_error_round_038(monkeypatch):
    # Arrange: return JSON that lacks the expected webPages->value structure to trigger except branch
    bad_json = json.dumps({"somethingElse": {"value": []}})
    def fake_get(url, headers=None, params=None):
        return DummyResp(bad_json)

    monkeypatch.setattr(bing_mod, "requests", SimpleNamespace(get=fake_get))

    logger = CapturingLogger()
    fake_self = SimpleNamespace(query="q", api_key="k", logger=logger)

    # Act
    result = bing_mod.BingSearch.search(fake_self, max_results=1)

    # Assert: parsing/structure errors should log an error and return empty list
    assert result == []
    assert len(logger.errors) == 1
    assert "Error parsing Bing search results" in logger.errors[0]


def test_search_json_none_triggers_warning_round_038(monkeypatch):
    # Arrange: make json.loads return None by providing 'null' text
    def fake_get(url, headers=None, params=None):
        return DummyResp("null")

    monkeypatch.setattr(bing_mod, "requests", SimpleNamespace(get=fake_get))

    logger = CapturingLogger()
    fake_self = SimpleNamespace(query="none query", api_key="k2", logger=logger)

    # Act
    result = bing_mod.BingSearch.search(fake_self, max_results=5)

    # Assert: search_results becomes None -> warning and empty list
    assert result == []
    assert len(logger.warnings) == 1
    assert "No search results found for query: none query" in logger.warnings[0]


def test_search_skips_youtube_and_returns_normal_results_round_038(monkeypatch):
    # Arrange: create a response that contains both a youtube result and a normal result
    payload = {
        "webPages": {
            "value": [
                {"name": "Cool Video", "url": "https://www.youtube.com/watch?v=abc", "snippet": "a yt vid"},
                {"name": "Article Title", "url": "https://example.com/article", "snippet": "summary text"}
            ]
        }
    }

    captured = {}

    def fake_get(url, headers=None, params=None):
        # capture inputs for verification
        captured['url'] = url
        captured['headers'] = headers
        captured['params'] = params
        return DummyResp(json.dumps(payload))

    monkeypatch.setattr(bing_mod, "requests", SimpleNamespace(get=fake_get))

    logger = CapturingLogger()
    fake_self = SimpleNamespace(query="filter youtube", api_key="AK", logger=logger)

    # Act
    result = bing_mod.BingSearch.search(fake_self, max_results=10)

    # Assert: youtube result is skipped, the non-youtube result is normalized and returned
    assert isinstance(result, list)
    assert len(result) == 1
    item = result[0]
    assert item["title"] == "Article Title"
    assert item["href"] == "https://example.com/article"
    assert item["body"] == "summary text"

    # Also verify requests.get was called with expected url and that API key passed through
    assert captured['url'] == "https://api.bing.microsoft.com/v7.0/search"
    assert captured['headers']['Ocp-Apim-Subscription-Key'] == "AK"
    assert captured['params']['q'] == "filter youtube"
    assert captured['params']['count'] == 10
