import asyncio
import random
from types import SimpleNamespace
from unittest import mock
import pytest

from gpt_researcher.skills.researcher import ResearchConductor


class DummyCfg:
    def __init__(self, max_search_results_per_query=5):
        self.max_search_results_per_query = max_search_results_per_query


class FakeResearcher:
    def __init__(self, retrievers):
        self.retrievers = retrievers
        self.cfg = DummyCfg()
        self.added_sources = []
        self.visited_urls = set()
        self.websocket = None
        self.role = "role"
        self.parent_query = None
        self.report_type = None
        self.add_costs = lambda *a, **k: None
        self.kwargs = {}
        self.verbose = False

    def add_research_sources(self, sources):
        # Preserve payload shape contract: expects a list of dicts
        self.added_sources.append(sources)


@pytest.mark.asyncio
async def test_search_handles_prefetched_and_url_round_166(monkeypatch):
    """Covers:
    - query_domains None branch (lines ~754->759)
    - skipping MCP retriever (line 761->762)
    - empty search_results continue branch (773->774)
    - prefetched content path (raw_content > 100) -> add_research_sources called (lines ~777-788)
    - url-only result path -> new_search_urls appended (line ~788-790)
    """

    # Define retriever classes used by the conductor
    class MyMCPRetriever:
        # __name__ includes 'mcpretriever' when lower-cased -> should be skipped
        def __init__(self, query, query_domains=None):
            raise AssertionError("MCP retriever should be skipped before instantiation")

    class EmptyRetriever:
        def __init__(self, query, query_domains=None):
            self.query = query

        def search(self, max_results=None):
            return []  # triggers the `if not search_results: continue` branch

    class PrefetchRetriever:
        def __init__(self, query, query_domains=None):
            self.query = query

        def search(self, max_results=None):
            long_content = "x" * 200
            return [{"href": "https://prefetched.example/page", "raw_content": long_content}]

    class UrlOnlyRetriever:
        def __init__(self, query, query_domains=None):
            self.query = query

        def search(self, max_results=None):
            return [{"url": "https://new.example/page", "raw_content": "snippet"}]

    # Put retrievers in the list in a deterministic order
    retriever_classes = [MyMCPRetriever, EmptyRetriever, PrefetchRetriever, UrlOnlyRetriever]
    researcher = FakeResearcher(retriever_classes)

    conductor = ResearchConductor(researcher)

    # Patch _get_new_urls to return its input unchanged (async function)
    async def fake_get_new_urls(urls):
        return urls

    conductor._get_new_urls = fake_get_new_urls

    # Patch random.shuffle to a no-op to keep deterministic order
    monkeypatch.setattr(random, "shuffle", lambda x: None)

    # Replace logger with a mock to avoid noisy output and to allow assertions in other tests
    conductor.logger = mock.Mock()

    new_search_urls, prefetched_content = await conductor._search_relevant_source_urls(
        query="dummy query",
        query_domains=None,  # exercise the branch that sets query_domains = []
    )

    # Assert that the prefetched content was detected and recorded
    assert isinstance(prefetched_content, list) and len(prefetched_content) == 1
    pref = prefetched_content[0]
    assert pref["url"] == "https://prefetched.example/page"
    assert "raw_content" in pref and len(pref["raw_content"]) > 100

    # Ensure add_research_sources was called with the expected payload shape
    assert researcher.added_sources == [[{"url": "https://prefetched.example/page"}]]

    # Assert that URL-only results were returned in new_search_urls
    assert new_search_urls == ["https://new.example/page"]

    # Ensure logger.error was not called in this successful flow
    conductor.logger.error.assert_not_called()


@pytest.mark.asyncio
async def test_search_logs_on_exception_round_166(monkeypatch):
    """Covers exception handling branch (lines ~790-791).
    Ensures that exceptions during retriever creation/search are logged.
    """

    class BadRetriever:
        def __init__(self, query, query_domains=None):
            # Raise during instantiation to trigger the except block
            raise RuntimeError("initialization failed")

    researcher = FakeResearcher([BadRetriever])
    conductor = ResearchConductor(researcher)

    # Patch _get_new_urls to avoid further processing
    async def fake_get_new_urls(urls):
        return urls

    conductor._get_new_urls = fake_get_new_urls

    # Replace logger with a mock to capture error calls
    conductor.logger = mock.Mock()

    # Also patch random.shuffle to deterministic no-op
    monkeypatch.setattr(random, "shuffle", lambda x: None)

    new_urls, prefetched_content = await conductor._search_relevant_source_urls(
        query="q",
        query_domains=["example.com"],
    )

    # Since the only retriever raised, outputs should be empty lists
    assert new_urls == []
    assert prefetched_content == []

    # logger.error should have been called with a message including the class name and exception message
    assert conductor.logger.error.call_count >= 1
    called_args = conductor.logger.error.call_args_list[0][0][0]
    assert "BadRetriever" in called_args
    assert "initialization failed" in called_args
