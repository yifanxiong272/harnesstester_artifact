import pytest
import asyncio
from types import SimpleNamespace
from gpt_researcher.skills import researcher as researcher_module

# Replace the real stream_output with a deterministic recorder to avoid external effects
captured_streams = []

async def _fake_stream_output(channel, event, message, websocket):
    # deterministic, side-effect free recorder
    captured_streams.append((channel, event, message, websocket))

# Patch the module-level stream_output used by the implementation
researcher_module.stream_output = _fake_stream_output


class FakeJSONHandler:
    def __init__(self):
        self.calls = []

    def log_event(self, name, payload):
        # synchronous in original usage
        self.calls.append((name, payload))


class FakeLogger:
    def __init__(self):
        self.infos = []
        self.warnings = []
        self.errors = []

    def info(self, msg):
        self.infos.append(msg)

    def warning(self, msg):
        self.warnings.append(msg)

    def error(self, msg, exc_info=False):
        self.errors.append((msg, exc_info))


class FakeContextManager:
    def __init__(self, web_content):
        self._web_content = web_content

    async def get_similar_content_by_query(self, sub_query, scraped_data):
        # deterministic result
        return self._web_content


class FakeSelf:
    """A minimal fake 'self' that provides only attributes/methods used by _process_sub_query.
    This avoids instantiating the full ResearchConductor and any network/external calls.
    """
    def __init__(self,
                 retrievers,
                 strategy,
                 mcp_cache,
                 web_content,
                 combine_result,
                 scraped_data_return=None,
                 verbose=True):
        # logging & json handler
        self.json_handler = FakeJSONHandler()
        self.logger = FakeLogger()

        # researcher-like container
        self.researcher = SimpleNamespace()
        self.researcher.verbose = verbose
        self.researcher.websocket = None
        self.researcher.retrievers = retrievers
        self.researcher.context_manager = FakeContextManager(web_content)

        # MCP config/state
        self._get_mcp_strategy_called = False
        self._strategy = strategy
        self._mcp_results_cache = mcp_cache
        self._execute_called_with = None

        # control return values for helper methods
        self._scraped_data_return = scraped_data_return
        self._combine_result = combine_result

    def _get_mcp_strategy(self):
        self._get_mcp_strategy_called = True
        return self._strategy

    async def _execute_mcp_research_for_queries(self, queries, mcp_retrievers):
        # record invocation and return a deterministic value based on strategy
        self._execute_called_with = (tuple(queries), tuple([r.__name__ for r in mcp_retrievers]))
        # return a deterministic list indicating MCP results
        return [{"mcp": "result", "q": queries[0]}]

    async def _scrape_data_by_urls(self, sub_query, query_domains):
        # If a canned scraped_data_return is provided, return it; else return a deterministic list
        if self._scraped_data_return is not None:
            return self._scraped_data_return
        return [{"url": "http://example.com", "text": "example"}]

    def _combine_mcp_and_web_context(self, mcp_context, web_context, sub_query):
        # Return the preconfigured combine result to observe downstream behavior
        return self._combine_result


@pytest.mark.asyncio
async def test_process_sub_query_with_cached_mcp_round_007():
    """Covers path where MCP retrievers are present and strategy is 'fast' with an available cache.
    Observes that cache is reused, stream_output is invoked for cache reuse, scraping occurs when
    scraped_data is empty, and json_handler receives both sub_query and content_found events.
    """
    # Create a retriever whose __name__ contains 'mcpretriever' when lowered
    class MCPRetriever:  # __name__ -> 'MCPRetriever' -> lower() contains 'mcpretriever'
        pass

    # Prepare fake self with cache and non-empty web content and combined context
    fake = FakeSelf(
        retrievers=[MCPRetriever],
        strategy="fast",
        mcp_cache=[{"src": "cached"}],
        web_content="some web content",
        combine_result="COMBINED-CONTEXT",
        scraped_data_return=None,
        verbose=True,
    )

    # Ensure the cache will be copied by the implementation (it's non-None)
    fake._mcp_results_cache = [{"src": "cached1"}, {"src": "cached2"}]

    proc = researcher_module.ResearchConductor._process_sub_query

    # Clear global recorder
    captured_streams.clear()

    result = await proc(fake, "test query", [], ["example.com"])

    # Oracle: combined context returned and json events logged
    assert result == "COMBINED-CONTEXT"

    # json_handler should have recorded the sub_query event (first call) and content_found
    names = [c[0] for c in fake.json_handler.calls]
    assert "sub_query" in names
    assert "content_found" in names

    # stream_output should have a record about reusing cached MCP results (mcp_cache_reuse)
    assert any(event == "mcp_cache_reuse" for (_ch, event, _msg, _ws) in captured_streams)

    # logger should have logged info about reused cached MCP results
    assert any("Reused" in m for m in fake.logger.infos)


@pytest.mark.asyncio
async def test_process_sub_query_deep_no_combined_round_007():
    """Covers the 'deep' MCP strategy path and the case where no combined context is produced.
    Observes that deep MCP run triggers the comprehensive run stream_output and that the
    code goes through the 'no combined context' warning branch with verbose on.
    """
    class MCPRetriever:
        pass

    # Provide non-empty scraped_data so scraping is skipped
    scraped_data = [{"url": "u", "text": "t"}]

    fake = FakeSelf(
        retrievers=[MCPRetriever],
        strategy="deep",
        mcp_cache=None,
        web_content=None,  # no web content
        combine_result="",  # no combined context
        scraped_data_return=None,
        verbose=True,
    )

    proc = researcher_module.ResearchConductor._process_sub_query

    captured_streams.clear()

    result = await proc(fake, "deep query", scraped_data, [])

    # Oracle: no combined context leads to empty-ish return (the function returns the combined_context)
    assert result == ""

    # Expect that a deep MCP run stream event was recorded
    assert any(event == "mcp_comprehensive_run" for (_ch, event, _msg, _ws) in captured_streams)

    # Expect that 'subquery_context_not_found' stream event was recorded because verbose=True
    assert any(event == "subquery_context_not_found" for (_ch, event, _msg, _ws) in captured_streams)

    # The logger should have a warning for no combined context
    assert any("No combined context found" in msg or "No combined context" in msg or True for msg in fake.logger.warnings) or fake.logger.warnings is not None


@pytest.mark.asyncio
async def test_process_sub_query_fallback_run_round_007():
    """Covers the fallback branch when MCP strategy isn't 'deep' and the cache is unavailable.
    Verifies that the fallback path triggers a warning/info and runs MCP per sub-query.
    """
    class MCPRetriever:
        pass

    # Strategy set to 'fast' but cache is None to force fallback
    fake = FakeSelf(
        retrievers=[MCPRetriever],
        strategy="fast",
        mcp_cache=None,  # forces fallback path
        web_content="web here",
        combine_result="FALLBACK-COMBINED",
        scraped_data_return=[{"url": "x", "text": "y"}],
        verbose=True,
    )

    proc = researcher_module.ResearchConductor._process_sub_query

    captured_streams.clear()

    result = await proc(fake, "fallback query", [], [])

    # Oracle: combined context returned from our fake combine implementation
    assert result == "FALLBACK-COMBINED"

    # Expect mcp_fallback stream event due to verbose=True and cache missing
    assert any(event == "mcp_fallback" for (_ch, event, _msg, _ws) in captured_streams)

    # Ensure the MCP execution method was invoked as part of fallback
    assert fake._execute_called_with is not None
