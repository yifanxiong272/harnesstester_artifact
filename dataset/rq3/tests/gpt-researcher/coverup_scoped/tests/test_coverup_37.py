# file: gpt_researcher/skills/researcher.py:48-87
# asked: {"lines": [55, 56, 57, 58, 59, 62, 63, 65, 66, 67, 68, 69, 72, 75, 76, 77, 78, 79, 80, 81, 82, 83, 84, 86, 87], "branches": []}
# gained: {"lines": [55, 56, 57, 58, 59, 62, 63, 65, 66, 67, 68, 69, 72, 75, 76, 77, 78, 79, 80, 81, 82, 83, 84, 86, 87], "branches": []}

import asyncio
import importlib
import types

import pytest


@pytest.mark.asyncio
async def test_plan_research_calls_stream_search_and_planning(monkeypatch):
    # Import the module and class under test
    mod = importlib.import_module("gpt_researcher.skills.researcher")
    ResearchConductor = mod.ResearchConductor

    # Prepare recorded call lists for assertions
    stream_calls = []
    search_calls = []
    outline_calls = []
    logger_messages = []

    # Async stub for stream_output that records parameters
    async def fake_stream_output(log_type, step, message, websocket):
        stream_calls.append((log_type, step, message, websocket))
        # simulate some small awaitable work
        await asyncio.sleep(0)

    # Async stub for get_search_results that records and returns a list
    async def fake_get_search_results(query, retriever, query_domains, researcher=None):
        search_calls.append((query, retriever, query_domains, researcher))
        await asyncio.sleep(0)
        # return some fake search results
        return [{"title": "result1"}, {"title": "result2"}]

    # Async stub for plan_research_outline that records the call and uses cost_callback
    async def fake_plan_research_outline(**kwargs):
        outline_calls.append(kwargs)
        # ensure cost_callback exists and is callable; call it to simulate usage
        cost_cb = kwargs.get("cost_callback")
        if callable(cost_cb):
            cost_cb(42)
        await asyncio.sleep(0)
        # return a sentinel outline
        return {"planned": ["step1", "step2"]}

    # Monkeypatch the module-level functions used in plan_research
    monkeypatch.setattr(mod, "stream_output", fake_stream_output)
    monkeypatch.setattr(mod, "get_search_results", fake_get_search_results)
    monkeypatch.setattr(mod, "plan_research_outline", fake_plan_research_outline)

    # Create a dummy researcher object with the attributes accessed in plan_research
    def dummy_retriever_func():
        return None

    # ensure it has a __name__
    dummy_retriever_func.__name__ = "dummy_retriever"

    class DummyResearcher:
        def __init__(self):
            self.websocket = object()
            self.retrievers = [dummy_retriever_func]
            self.role = "researcher_role"
            self.cfg = {"cfg_key": "cfg_val"}
            self.parent_query = "parent_q"
            self.report_type = "reportX"
            self.kwargs = {"extra_arg": 123}
            self._costs = []

        def add_costs(self, cost):
            # record costs for verification
            self._costs.append(cost)

    researcher = DummyResearcher()

    # Create conductor and replace its logger to capture info messages
    conductor = ResearchConductor(researcher)
    conductor.logger = types.SimpleNamespace(info=lambda msg: logger_messages.append(msg))

    # Run the method under test
    outline = await conductor.plan_research("test query", query_domains=["example.com"])

    # Assertions verifying the expected interactions and results

    # stream_output should have been called twice: browsing and planning
    assert len(stream_calls) == 2
    assert stream_calls[0][0] == "logs"
    assert "Browsing the web" in stream_calls[0][2] or "🌐 Browsing the web" in stream_calls[0][2]
    assert stream_calls[1][0] == "logs"
    assert "Planning the research strategy" in stream_calls[1][2] or "🤔 Planning the research strategy" in stream_calls[1][2]
    # websocket passed through should be the researcher's websocket
    assert stream_calls[0][3] is researcher.websocket
    assert stream_calls[1][3] is researcher.websocket

    # get_search_results should have been called once with expected args
    assert len(search_calls) == 1
    called_query, called_retriever, called_domains, called_researcher = search_calls[0]
    assert called_query == "test query"
    assert called_retriever is researcher.retrievers[0]
    assert called_domains == ["example.com"]
    assert called_researcher is researcher

    # plan_research_outline should have been invoked and returned the expected structure
    assert len(outline_calls) == 1
    outline_kwargs = outline_calls[0]
    assert outline_kwargs["query"] == "test query"
    # search_results passed should be the fake search results returned earlier
    assert isinstance(outline_kwargs["search_results"], list)
    assert outline_kwargs["agent_role_prompt"] == researcher.role
    assert outline_kwargs["cfg"] == researcher.cfg
    assert outline_kwargs["parent_query"] == researcher.parent_query
    assert outline_kwargs["report_type"] == researcher.report_type
    # cost_callback should be the researcher's add_costs method and was called (adds 42)
    assert callable(outline_kwargs["cost_callback"])
    assert researcher._costs == [42]
    # retriever_names should be a list containing the dummy retriever's __name__
    assert outline_kwargs["retriever_names"] == [dummy_retriever_func.__name__]
    # kwargs forwarded
    assert outline_kwargs.get("extra_arg") == 123

    # The returned outline should match the fake_plan_research_outline return value
    assert outline == {"planned": ["step1", "step2"]}

    # Logger should have received messages indicating search results and planned outline
    assert any("Initial search results obtained" in m for m in logger_messages)
    assert any("Research outline planned" in m for m in logger_messages)
