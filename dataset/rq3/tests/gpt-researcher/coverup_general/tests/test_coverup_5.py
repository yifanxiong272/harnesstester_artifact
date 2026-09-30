# file: gpt_researcher/skills/researcher.py:266-365
# asked: {"lines": [272, 274, 275, 276, 277, 280, 283, 285, 286, 288, 289, 290, 291, 292, 293, 294, 296, 298, 299, 300, 301, 302, 303, 304, 308, 309, 310, 311, 313, 314, 315, 316, 317, 318, 319, 324, 325, 326, 327, 330, 331, 334, 335, 337, 338, 339, 340, 341, 342, 343, 344, 348, 349, 350, 351, 352, 355, 357, 358, 359, 360, 361, 362, 363, 364, 365], "branches": [[274, 275], [274, 276], [276, 277], [276, 280], [285, 286], [285, 330], [286, 288], [286, 296], [289, 290], [289, 330], [296, 298], [296, 311], [299, 300], [299, 308], [311, 313], [311, 324], [314, 315], [314, 330], [334, 335], [334, 337], [337, 338], [337, 348], [358, 359], [358, 362]]}
# gained: {"lines": [272, 274, 275, 276, 277, 280, 283, 285, 286, 288, 289, 290, 291, 292, 293, 294, 296, 298, 299, 300, 301, 302, 303, 304, 308, 309, 310, 311, 313, 314, 315, 316, 317, 318, 319, 324, 325, 326, 327, 330, 331, 334, 335, 337, 338, 339, 340, 341, 342, 343, 344, 348, 349, 350, 351, 352, 355, 357, 358, 359, 360, 361, 362, 363, 364, 365], "branches": [[274, 275], [276, 277], [285, 286], [285, 330], [286, 288], [286, 296], [289, 290], [296, 298], [296, 311], [299, 300], [311, 313], [311, 324], [314, 315], [334, 335], [337, 338], [337, 348], [358, 359], [358, 362]]}

import types
import pytest
import asyncio

from gpt_researcher.skills.researcher import ResearchConductor


class DummyLogger:
    def __init__(self):
        self.infos = []
        self.warnings = []
        self.errors = []

    def info(self, msg):
        self.infos.append(msg)

    def warning(self, msg):
        self.warnings.append(msg)

    def error(self, msg, exc_info=False):
        # store exc_info to assert it's passed when expected
        self.errors.append((msg, exc_info))


class DummyResearcher:
    def __init__(self, retrievers=None, verbose=False, websocket=None, report_type="report"):
        self.retrievers = retrievers or []
        self.verbose = verbose
        self.websocket = websocket
        self.report_type = report_type


def make_bound_method():
    """
    Return the unbound coroutine function for _get_context_by_web_search so tests may bind it to a dummy self.
    """
    return ResearchConductor._get_context_by_web_search


@pytest.mark.asyncio
async def test_mcp_disabled_strategy_calls_stream_output_and_returns_combined_context(monkeypatch):
    # Setup dummy self
    method = make_bound_method()
    # patch the stream_output global in the function's module so await stream_output uses our fake
    calls = []

    async def fake_stream_output(chan, key, message, websocket, *args, **kwargs):
        calls.append((chan, key, message, websocket, args, kwargs))

    method.__globals__['stream_output'] = fake_stream_output

    dummy_self = types.SimpleNamespace()
    dummy_self.logger = DummyLogger()
    # create a retriever whose __name__ contains 'mcpretriever' (case-insensitive)
    def mcpretriever_dummy():  # function name includes 'mcpretriever'
        pass
    dummy_self.researcher = DummyResearcher(retrievers=[mcpretriever_dummy], verbose=True, websocket="wss://dummy", report_type="report")
    dummy_self._mcp_results_cache = None

    async def fake_execute_mcp_research_for_queries(queries, retrievers):
        # Should not be called in 'disabled', but return something harmless if called
        return ["should_not_be_used"]

    async def fake_plan_research(query, query_domains):
        return ["sub1", "sub2"]

    async def fake_process_sub_query(sub_query, scraped_data, query_domains):
        return f"ctx_{sub_query}"

    # bind methods
    dummy_self._get_mcp_strategy = lambda: "disabled"
    dummy_self._execute_mcp_research_for_queries = fake_execute_mcp_research_for_queries
    dummy_self.plan_research = fake_plan_research
    dummy_self._process_sub_query = fake_process_sub_query

    # Bind and call
    bound = method.__get__(dummy_self, ResearchConductor)
    result = await bound("my query", scraped_data=None, query_domains=None)

    # Assertions
    # Combined context should be returned: two from plan + original appended => three entries
    assert isinstance(result, str)
    assert "ctx_sub1" in result and "ctx_sub2" in result and "ctx_my query" in result
    # MCP results cache should remain None (disabled)
    assert dummy_self._mcp_results_cache is None
    # stream_output should have been called at least once for mcp_disabled
    assert any(call[1] == "mcp_disabled" for call in calls)


@pytest.mark.asyncio
async def test_mcp_fast_strategy_caches_results_and_stream_output(monkeypatch):
    method = make_bound_method()
    calls = []

    async def fake_stream_output(chan, key, message, websocket, *args, **kwargs):
        calls.append((chan, key, message, websocket, args, kwargs))

    method.__globals__['stream_output'] = fake_stream_output

    dummy_self = types.SimpleNamespace()
    dummy_self.logger = DummyLogger()

    def mcpretriever_dummy(): pass
    dummy_self.researcher = DummyResearcher(retrievers=[mcpretriever_dummy], verbose=True, websocket="wss://ws", report_type="report")
    dummy_self._mcp_results_cache = None

    # _get_mcp_strategy returns 'fast'
    dummy_self._get_mcp_strategy = lambda: "fast"

    # _execute_mcp_research_for_queries should be awaited; provide coroutine
    async def fake_execute_mcp_research_for_queries(queries, retrievers):
        # return list mimicking context entries
        return ["mcp_ctx1", "mcp_ctx2"]

    async def fake_plan_research(query, query_domains):
        return ["subx"]

    async def fake_process_sub_query(sub_query, scraped_data, query_domains):
        return "result_subx"

    dummy_self._execute_mcp_research_for_queries = fake_execute_mcp_research_for_queries
    dummy_self.plan_research = fake_plan_research
    dummy_self._process_sub_query = fake_process_sub_query

    bound = method.__get__(dummy_self, ResearchConductor)
    result = await bound("qfast", scraped_data=None, query_domains=None)

    # Ensure cache was set
    assert dummy_self._mcp_results_cache == ["mcp_ctx1", "mcp_ctx2"]
    # Ensure the optimization stream_output was called
    assert any(call[1] == "mcp_optimization" for call in calls)
    # Combined context should include result_subx and appended original query's processed result
    assert isinstance(result, str)
    assert "result_subx" in result


@pytest.mark.asyncio
async def test_mcp_deep_strategy_does_not_execute_mcp_and_returns_empty_when_no_context(monkeypatch):
    method = make_bound_method()
    calls = []

    async def fake_stream_output(chan, key, message, websocket, *args, **kwargs):
        calls.append((chan, key, message, websocket, args, kwargs))

    method.__globals__['stream_output'] = fake_stream_output

    dummy_self = types.SimpleNamespace()
    dummy_self.logger = DummyLogger()

    def mcpretriever_dummy(): pass
    dummy_self.researcher = DummyResearcher(retrievers=[mcpretriever_dummy], verbose=True, websocket=None, report_type="report")
    dummy_self._mcp_results_cache = None

    # strategy deep
    dummy_self._get_mcp_strategy = lambda: "deep"

    # _execute_mcp_research_for_queries should NOT be called; make it raise if called
    async def should_not_be_called(*args, **kwargs):
        raise AssertionError("_execute_mcp_research_for_queries should not be called for deep strategy at this point")

    dummy_self._execute_mcp_research_for_queries = should_not_be_called

    # plan returns no subqueries so only original appended
    async def fake_plan_research(query, query_domains):
        return []

    # process returns None to simulate no results -> filtered out and [] returned
    async def fake_process_sub_query(sub_query, scraped_data, query_domains):
        return None

    dummy_self.plan_research = fake_plan_research
    dummy_self._process_sub_query = fake_process_sub_query

    bound = method.__get__(dummy_self, ResearchConductor)
    result = await bound("qdeep", scraped_data=None, query_domains=None)

    # Because process returns None, result should be [] (empty list)
    assert result == []
    # And for deep strategy, stream_output for mcp_comprehensive should have been called
    assert any(call[1] == "mcp_comprehensive" for call in calls)


@pytest.mark.asyncio
async def test_unknown_mcp_strategy_defaults_to_fast_and_caches(monkeypatch):
    method = make_bound_method()
    calls = []

    async def fake_stream_output(channel, key, message, websocket, *args, **kwargs):
        calls.append((channel, key, message))
    method.__globals__['stream_output'] = fake_stream_output

    dummy_self = types.SimpleNamespace()
    dummy_self.logger = DummyLogger()

    def mcpretriever_dummy(): pass
    dummy_self.researcher = DummyResearcher(retrievers=[mcpretriever_dummy], verbose=False, websocket=None, report_type="report")
    dummy_self._mcp_results_cache = None

    # Unknown strategy
    dummy_self._get_mcp_strategy = lambda: "unknown_strategy"

    # _execute_mcp_research_for_queries should be called and set cache
    async def fake_execute_mcp_research_for_queries(queries, retrievers):
        return ["cached_a"]

    async def fake_plan_research(query, query_domains):
        return ["s1"]

    async def fake_process_sub_query(sub_query, scraped_data, query_domains):
        return "ok"

    dummy_self._execute_mcp_research_for_queries = fake_execute_mcp_research_for_queries
    dummy_self.plan_research = fake_plan_research
    dummy_self._process_sub_query = fake_process_sub_query

    bound = method.__get__(dummy_self, ResearchConductor)
    result = await bound("qunk", scraped_data=None, query_domains=None)

    # Cache should be set to returned list
    assert dummy_self._mcp_results_cache == ["cached_a"]
    # stream_output not called for MCP (verbose=False)
    assert calls == []
    assert isinstance(result, str)
    assert "ok" in result


@pytest.mark.asyncio
async def test_exception_in_gather_is_caught_and_returns_empty_and_logs_error(monkeypatch):
    method = make_bound_method()

    # patch stream_output to a no-op coroutine to ensure await works if called
    async def noop_stream_output(*args, **kwargs):
        return None
    method.__globals__['stream_output'] = noop_stream_output

    dummy_self = types.SimpleNamespace()
    dummy_self.logger = DummyLogger()

    # No retrievers so branch for MCP not entered
    dummy_self.researcher = DummyResearcher(retrievers=[], verbose=False, websocket=None, report_type="report")
    dummy_self._mcp_results_cache = None

    dummy_self._get_mcp_strategy = lambda: "fast"  # won't be used
    async def fake_plan_research(query, query_domains):
        return ["one", "two"]

    # Make one of the process_sub_query coroutines raise to trigger the except block
    async def proc_raises(sub_query, scraped_data, query_domains):
        if sub_query == "one":
            raise RuntimeError("boom")
        return "should_not_get_here"

    dummy_self.plan_research = fake_plan_research
    dummy_self._process_sub_query = proc_raises

    bound = method.__get__(dummy_self, ResearchConductor)
    result = await bound("qerr", scraped_data=None, query_domains=None)

    # On exception, should return empty list
    assert result == []
    # Logger should have an error recorded
    assert any("Error during web search" in e[0] for e in dummy_self.logger.errors)
