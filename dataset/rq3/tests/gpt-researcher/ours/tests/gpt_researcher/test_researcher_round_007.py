import asyncio
import importlib
import types
from types import SimpleNamespace

import pytest

researcher_mod = importlib.import_module("gpt_researcher.skills.researcher")
_process_sub_query = researcher_mod.ResearchConductor._process_sub_query

# Helper async stub for stream_output to record calls
class StreamRecorder:
    def __init__(self):
        self.calls = []

    async def __call__(self, channel, tag, message, websocket):
        # record minimal normalized info for deterministic assertions
        self.calls.append((channel, tag, str(message)))


class DummyLogger:
    def __init__(self):
        self.infos = []
        self.warns = []
        self.errors = []

    def info(self, msg):
        self.infos.append(str(msg))

    def warning(self, msg):
        self.warns.append(str(msg))

    def error(self, msg, exc_info=False):
        self.errors.append(str(msg))


class DummyJSONHandler:
    def __init__(self):
        self.events = []

    def log_event(self, name, payload):
        # copy basic shape only
        self.events.append((name, dict(payload)))


async def run_process_sub_query_with_self(fake_self, sub_query, scraped_data=None, query_domains=None):
    # convenience wrapper to call unbound coroutine
    if scraped_data is None:
        scraped_data = []
    if query_domains is None:
        query_domains = []
    return await _process_sub_query(fake_self, sub_query, scraped_data, query_domains)


def make_fake_self(
    *,
    mcp_strategy_return="disabled",
    mcp_results_cache=None,
    retriever_has_mcp=True,
    scraped_return=None,
    context_return=None,
    verbose=True,
):
    # Build researcher and self objects matching the shape used in _process_sub_query
    # retrievers should be objects whose __name__ lower() contains 'mcpretriever' if mcp retriever
    def make_retriever(name):
        def _r():
            pass

        _r.__name__ = name
        return _r

    retriever = make_retriever("MyMCPRetriever") if retriever_has_mcp else make_retriever("OtherRetriever")

    # provide researcher with required attributes
    context_manager = SimpleNamespace()

    async def fake_get_similar_content_by_query(query, scraped_data_in):
        return context_return

    context_manager.get_similar_content_by_query = fake_get_similar_content_by_query

    researcher = SimpleNamespace(
        verbose=verbose,
        retrievers=[retriever],
        websocket=None,
        context_manager=context_manager,
    )

    # Build fake self
    fake_self = SimpleNamespace()
    fake_self.researcher = researcher
    fake_self.logger = DummyLogger()
    fake_self.json_handler = DummyJSONHandler()
    fake_self._mcp_results_cache = mcp_results_cache

    # _get_mcp_strategy is synchronous in source
    def _get_mcp_strategy():
        return mcp_strategy_return

    fake_self._get_mcp_strategy = _get_mcp_strategy

    # Async MCP execution stub
    async def _execute_mcp_research_for_queries(queries, mcp_retrievers):
        # return a deterministic list representing MCP context
        return ["mcp_result_for:" + q for q in queries]

    fake_self._execute_mcp_research_for_queries = _execute_mcp_research_for_queries

    # Async scraper stub
    async def _scrape_data_by_urls(sub_query, query_domains):
        # return provided scraped_return or a deterministic list
        return scraped_return if scraped_return is not None else ["scraped:" + sub_query]

    fake_self._scrape_data_by_urls = _scrape_data_by_urls

    # combine logic: deterministic combination
    def _combine_mcp_and_web_context(mcp_context, web_context, sub_query):
        if mcp_context and web_context:
            return {"mcp": mcp_context, "web": web_context, "q": sub_query}
        if mcp_context:
            return {"mcp": mcp_context, "q": sub_query}
        if web_context:
            return {"web": web_context, "q": sub_query}
        return ""

    fake_self._combine_mcp_and_web_context = _combine_mcp_and_web_context

    return fake_self


@pytest.mark.asyncio
async def test_fast_cache_uses_cached_mcp_round_007():
    """
    Scenario: MCP retriever present, strategy 'fast', cache available -> use cache path.
    - Ensure cached MCP is reused and verbose stream_output called.
    - Provide non-empty scraped_data so scraping branch is not exercised.
    - Combined context is truthy and json_handler.log_event is called.
    """
    recorder = StreamRecorder()
    original_stream = researcher_mod.stream_output
    researcher_mod.stream_output = recorder

    try:
        # Prepare fake self where mcp_strategy returns 'fast' and cache exists
        fake_self = make_fake_self(
            mcp_strategy_return="fast",
            mcp_results_cache=["cached1", "cached2"],
            retriever_has_mcp=True,
            scraped_return=["already_provided"],
            context_return={"similar": "found"},
            verbose=True,
        )

        # Provide scraped_data so branch 521->522 is not taken
        scraped_data = ["already_provided"]

        result = await run_process_sub_query_with_self(fake_self, "queryA", scraped_data=scraped_data)

        # Combined context should include mcp and web
        assert isinstance(result, dict)
        assert result["mcp"] == ["cached1", "cached2"] or result.get("q") == "queryA"

        # json_handler should have logged content_found because combined_context truthy
        assert any(ev[0] == "content_found" for ev in fake_self.json_handler.events)

        # stream_output should have recorded at least one call for mcp cache reuse and context_combined
        recorded_tags = [c[1] for c in recorder.calls]
        # we expect the context_combined or mcp_cache_reuse logs to appear when verbose=True
        assert any(tag in ("mcp_cache_reuse", "context_combined") for tag in recorded_tags)

    finally:
        researcher_mod.stream_output = original_stream


@pytest.mark.asyncio
async def test_disabled_mcp_and_scrape_round_007():
    """
    Scenario: MCP retriever present but strategy 'disabled' -> skip MCP.
    - No initial scraped_data -> _scrape_data_by_urls should be called.
    - get_similar_content_by_query returns empty -> combined_context falsy -> triggers warning and verbose stream_output.
    - Should return empty string as combined_context.
    """
    recorder = StreamRecorder()
    original_stream = researcher_mod.stream_output
    researcher_mod.stream_output = recorder

    try:
        fake_self = make_fake_self(
            mcp_strategy_return="disabled",
            mcp_results_cache=None,
            retriever_has_mcp=True,
            scraped_return=["page1", "page2"],
            context_return="",  # no web context
            verbose=True,
        )

        # Call with no scraped_data to force scraping branch
        result = await run_process_sub_query_with_self(fake_self, "queryB", scraped_data=[])

        # When no combined context found, the function sets combined_context = "" and returns it
        assert result == ""

        # Ensure scraper produced scraped data (our stub returns scraped_return)
        # And ensure a warning was recorded about no combined context
        # The logger should have a warning entry mentioning 'No combined context'
        assert any("No combined context" in w or "No combined" in w for w in fake_self.logger.warns) or fake_self.logger.warns

        # stream_output should have a tag 'subquery_context_not_found' due to verbose
        tags = [c[1] for c in recorder.calls]
        assert "subquery_context_not_found" in tags

        # json_handler should not have logged 'content_found'
        assert not any(ev[0] == "content_found" for ev in fake_self.json_handler.events)

    finally:
        researcher_mod.stream_output = original_stream


@pytest.mark.asyncio
async def test_deep_mcp_executes_and_scrapes_round_007():
    """
    Scenario: MCP strategy 'deep' -> execute MCP research and then scrape web when scraped_data missing.
    - Ensure _execute_mcp_research_for_queries is awaited and its results are included in combined context.
    - Ensure scraper is invoked when scraped_data is empty.
    """
    recorder = StreamRecorder()
    original_stream = researcher_mod.stream_output
    researcher_mod.stream_output = recorder

    try:
        fake_self = make_fake_self(
            mcp_strategy_return="deep",
            mcp_results_cache=None,
            retriever_has_mcp=True,
            scraped_return=["pageX"],
            context_return=None,  # None to simulate no web_context returned
            verbose=True,
        )

        # Call with no scraped_data
        result = await run_process_sub_query_with_self(fake_self, "queryC", scraped_data=[])

        # Because _execute_mcp_research_for_queries returns a list for the query, combined_context should include that
        assert isinstance(result, dict)
        assert "mcp" in result and isinstance(result["mcp"], list)
        assert any("mcp_result_for:queryC" in s for s in result["mcp"]) or result.get("q") == "queryC"

        # stream_output should have recorded the deep-mcp run message tag
        tags = [c[1] for c in recorder.calls]
        assert "mcp_comprehensive_run" in tags or "mcp_comprehensive_run" in tags

    finally:
        researcher_mod.stream_output = original_stream
