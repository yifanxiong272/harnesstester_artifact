# file: gpt_researcher/retrievers/tavily/tavily_search.py:57-98
# asked: {"lines": [75, 76, 77, 78, 79, 80, 81, 82, 83, 84, 85, 86, 87, 90, 91, 94, 95, 98], "branches": [[94, 95], [94, 98]]}
# gained: {"lines": [75, 76, 77, 78, 79, 80, 81, 82, 83, 84, 85, 86, 87, 90, 91, 94, 95, 98], "branches": [[94, 95], [94, 98]]}

import json
import importlib
import pytest
import requests


def _get_module():
    return importlib.import_module("gpt_researcher.retrievers.tavily.tavily_search")


def test_search_success(monkeypatch):
    mod = _get_module()
    TavilySearch = mod.TavilySearch

    # Ensure deterministic API key
    monkeypatch.setattr(TavilySearch, "get_api_key", lambda self: "TESTKEY")

    recorded = {}

    def fake_post(url, data, headers, timeout):
        recorded["url"] = url
        recorded["data"] = data
        recorded["headers"] = headers
        recorded["timeout"] = timeout

        class FakeResp:
            status_code = 200

            def json(self):
                return {"result": "ok"}

            def raise_for_status(self):
                raise AssertionError("raise_for_status should not be called for 200")

        return FakeResp()

    # Patch the requests.post used in the module
    monkeypatch.setattr(mod.requests, "post", fake_post)

    inst = TavilySearch(query="irrelevant")
    result = inst._search(
        query="abc",
        search_depth="advanced",
        topic="tech",
        days=5,
        max_results=7,
        include_domains=["a.com"],
        exclude_domains=["b.com"],
        include_answer=True,
        include_raw_content=True,
        include_images=True,
        use_cache=False,
    )

    assert result == {"result": "ok"}

    expected_data = {
        "query": "abc",
        "search_depth": "advanced",
        "topic": "tech",
        "days": 5,
        "include_answer": True,
        "include_raw_content": True,
        "max_results": 7,
        "include_domains": ["a.com"],
        "exclude_domains": ["b.com"],
        "include_images": True,
        "api_key": "TESTKEY",
        "use_cache": False,
    }

    assert recorded["url"] == inst.base_url
    assert recorded["headers"] == inst.headers
    assert recorded["timeout"] == 100
    assert json.loads(recorded["data"]) == expected_data


def test_search_failure_raises(monkeypatch):
    mod = _get_module()
    TavilySearch = mod.TavilySearch

    # deterministic api key
    monkeypatch.setattr(TavilySearch, "get_api_key", lambda self: "FAILKEY")

    called = {"raise_called": False, "posted": None}

    def fake_post(url, data, headers, timeout):
        called["posted"] = {"url": url, "data": data, "headers": headers, "timeout": timeout}

        class FakeResp:
            status_code = 500

            def json(self):
                return {"should": "not be used"}

            def raise_for_status(self):
                called["raise_called"] = True
                raise requests.HTTPError("Server error")

        return FakeResp()

    monkeypatch.setattr(mod.requests, "post", fake_post)

    inst = TavilySearch(query="irrelevant2")

    with pytest.raises(requests.HTTPError):
        inst._search(query="fail", search_depth="basic", topic="general", days=1)

    # ensure raise_for_status was invoked and that a request was posted
    assert called["raise_called"] is True
    assert called["posted"] is not None
    posted_data = json.loads(called["posted"]["data"])
    assert posted_data["query"] == "fail"
    assert posted_data["api_key"] == "FAILKEY"
    assert called["posted"]["timeout"] == 100
