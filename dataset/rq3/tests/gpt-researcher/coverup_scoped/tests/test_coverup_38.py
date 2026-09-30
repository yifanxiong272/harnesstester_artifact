# file: gpt_researcher/retrievers/bocha/bocha.py:10-58
# asked: {"lines": [21, 22, 23, 31, 32, 33, 34, 36, 37, 38, 39, 40, 43, 45, 46, 47, 50, 51, 52, 53, 54, 56, 58], "branches": [[50, 51], [50, 58]]}
# gained: {"lines": [21, 22, 23, 31, 32, 33, 34, 36, 37, 38, 39, 40, 43, 45, 46, 47, 50, 51, 52, 53, 54, 56, 58], "branches": [[50, 51], [50, 58]]}

import pytest
from types import SimpleNamespace

from gpt_researcher.retrievers.bocha.bocha import BoChaSearch


def test_bocha_search_with_query_domains(monkeypatch):
    # Set env var used in __init__
    monkeypatch.setenv("BOCHA_API_KEY", "abc123")

    captured = {}

    def fake_post(url, headers=None, json=None):
        # capture call arguments for assertions
        captured["url"] = url
        captured["headers"] = headers
        captured["json"] = json

        class FakeResponse:
            def json(self):
                return {
                    "data": {
                        "webPages": {
                            "value": [
                                {"name": "Title1", "url": "http://a", "snippet": "body1"}
                            ]
                        }
                    }
                }

        return FakeResponse()

    # Patch the requests.post used inside the module
    monkeypatch.setattr(
        "gpt_researcher.retrievers.bocha.bocha.requests.post", fake_post
    )

    # Instantiate with query_domains to exercise that branch
    b = BoChaSearch("query1", query_domains=["example.com"])

    # Check attributes set in __init__
    assert b.query == "query1"
    assert b.query_domains == ["example.com"]
    assert b.api_key == "abc123"

    # Call search and assert returned normalized structure
    results = b.search(max_results=3)
    assert results == [
        {"title": "Title1", "href": "http://a", "body": "body1"}
    ]

    # Verify that the request was composed as expected
    assert captured["url"] == "https://api.bochaai.com/v1/web-search"
    assert captured["headers"]["Authorization"] == "Bearer abc123"
    assert captured["headers"]["Content-Type"] == "application/json"
    assert captured["json"]["query"] == "query1"
    assert captured["json"]["count"] == 3
    # Extra sanity: freshness and summary keys present
    assert captured["json"]["freshness"] == "noLimit"
    assert captured["json"]["summary"] is True


def test_bocha_search_without_query_domains_and_default_count(monkeypatch):
    # Different API key to ensure env var usage per-test
    monkeypatch.setenv("BOCHA_API_KEY", "keyXYZ")

    captured = {}

    def fake_post_two(url, headers=None, json=None):
        captured["url"] = url
        captured["headers"] = headers
        captured["json"] = json

        class FakeResponse:
            def json(self):
                return {
                    "data": {
                        "webPages": {
                            "value": [
                                {"name": "T1", "url": "http://1", "snippet": "s1"},
                                {"name": "T2", "url": "http://2", "snippet": "s2"},
                            ]
                        }
                    }
                }

        return FakeResponse()

    monkeypatch.setattr(
        "gpt_researcher.retrievers.bocha.bocha.requests.post", fake_post_two
    )

    # Instantiate without query_domains to exercise the None default
    b2 = BoChaSearch("q2")

    assert b2.query == "q2"
    assert b2.query_domains is None
    assert b2.api_key == "keyXYZ"

    # Call search with default max_results (should be 7)
    results = b2.search()
    # Expect two normalized results returned by our fake response
    assert results == [
        {"title": "T1", "href": "http://1", "body": "s1"},
        {"title": "T2", "href": "http://2", "body": "s2"},
    ]

    # Verify the request used default count of 7
    assert captured["json"]["count"] == 7
    assert captured["headers"]["Authorization"] == "Bearer keyXYZ"
    assert captured["url"] == "https://api.bochaai.com/v1/web-search"
