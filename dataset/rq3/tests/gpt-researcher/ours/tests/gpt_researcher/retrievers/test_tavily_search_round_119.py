import pytest

from gpt_researcher.retrievers.tavily.tavily_search import TavilySearch


def test_search_success_round_119():
    """When _search returns a non-empty 'results' list, search() should map items to href/body pairs."""
    # Provide an API key via headers to avoid get_api_key printing during init
    ts = TavilySearch("some query", headers={"tavily_api_key": "abc"}, topic="topic-x", query_domains=["a.com"])

    captured = {}

    def fake_search(self, query, search_depth="basic", topic="general", days=2, max_results=10,
                    include_domains=None, exclude_domains=None, include_answer=False,
                    include_raw_content=False, include_images=False, use_cache=True):
        # record call details for assertions
        captured['query'] = query
        captured['search_depth'] = search_depth
        captured['max_results'] = max_results
        captured['topic'] = topic
        captured['include_domains'] = include_domains
        return {
            "results": [
                {"url": "http://a.example/1", "content": "first"},
                {"url": "http://b.example/2", "content": "second"},
            ]
        }

    # Patch the instance method deterministically
    ts._search = fake_search

    out = ts.search(max_results=2)

    # Assert the call parameters were propagated and mapping is correct
    assert captured['query'] == "some query"
    assert captured['search_depth'] == "basic"
    assert captured['max_results'] == 2
    assert captured['topic'] == "topic-x"
    # include_domains comes from instance.query_domains (set in ctor)
    assert captured['include_domains'] == ["a.com"]

    assert isinstance(out, list)
    assert out == [
        {"href": "http://a.example/1", "body": "first"},
        {"href": "http://b.example/2", "body": "second"},
    ]


def test_search_empty_results_triggers_exception_branch_round_119(capsys):
    """When _search returns an empty 'results' list, the code raises internally and returns an empty list and prints the error."""
    ts = TavilySearch("q2", headers={"tavily_api_key": "k"}, topic="t", query_domains=None)

    def fake_empty(self, *args, **kwargs):
        return {"results": []}

    ts._search = fake_empty

    out = ts.search(max_results=5)

    # The function should return an empty list when no sources are found
    assert out == []

    # Check that the printed message includes the exception text
    captured = capsys.readouterr()
    assert "No results found with Tavily API search." in captured.out
    assert "Failed fetching sources. Resulting in empty response." in captured.out


def test_search_internal_search_raises_round_119(capsys):
    """If the underlying _search raises an exception, search() should catch it, print and return []."""
    ts = TavilySearch("q3", headers={"tavily_api_key": "k2"})

    def fake_raise(self, *args, **kwargs):
        raise RuntimeError("upstream error")

    ts._search = fake_raise

    out = ts.search()

    assert out == []
    printed = capsys.readouterr().out
    assert "upstream error" in printed
    assert "Failed fetching sources. Resulting in empty response." in printed
