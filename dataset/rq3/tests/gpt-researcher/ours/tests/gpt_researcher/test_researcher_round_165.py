import asyncio
import types
from types import SimpleNamespace

import gpt_researcher.skills.researcher as researcher_mod
from gpt_researcher.skills.researcher import ResearchConductor


def test_plan_research_happy_path_round_165():
    # Prepare spies/stand-ins for external collaborators
    stream_calls = []

    async def fake_stream_output(channel, stage, message, websocket):
        # record call shape exactly as used by the implementation
        stream_calls.append((channel, stage, message, websocket))

    get_search_called = {}

    async def fake_get_search_results(query, retriever, query_domains, researcher):
        # capture the exact call parameters
        get_search_called['query'] = query
        get_search_called['retriever'] = retriever
        get_search_called['query_domains'] = query_domains
        get_search_called['researcher'] = researcher
        # return deterministic search results
        return ["resultA", "resultB"]

    plan_outline_called = {}

    async def fake_plan_research_outline(**kwargs):
        # capture kwargs forwarded into the outline planner
        plan_outline_called.update(kwargs)
        return {"plan": "ok"}

    # Patch module-level names where the code under test resolves them
    original_stream = researcher_mod.stream_output
    original_get_search = researcher_mod.get_search_results
    original_plan_outline = researcher_mod.plan_research_outline
    try:
        researcher_mod.stream_output = fake_stream_output
        researcher_mod.get_search_results = fake_get_search_results
        researcher_mod.plan_research_outline = fake_plan_research_outline

        # Construct a ResearchConductor instance without invoking its constructor
        rc = ResearchConductor.__new__(ResearchConductor)

        # Create a fake researcher object with the exact attributes used by plan_research
        def fake_retriever():
            pass

        # Ensure retriever has a __name__ attribute for retriever_names creation
        fake_retriever.__name__ = "fake_retriever"

        fake_researcher = SimpleNamespace(
            websocket="fake_ws",
            retrievers=[fake_retriever],
            role="researcher_role",
            cfg={"cfg_key": "cfg_val"},
            parent_query="parent_q",
            report_type="report_x",
            add_costs=lambda *a, **k: "cost_added",
            kwargs={"extra_flag": True},
        )

        # Dummy logger to capture info calls
        class DummyLogger:
            def __init__(self):
                self.infos = []

            def info(self, msg):
                self.infos.append(msg)

        rc.researcher = fake_researcher
        rc.logger = DummyLogger()

        # Run the coroutine under test deterministically
        result = asyncio.run(rc.plan_research("test query", query_domains=["domain1"]))

        # Assertions: return value forwarded from the planner
        assert result == {"plan": "ok"}

        # stream_output was awaited twice: initial browsing message and planning message
        assert len(stream_calls) == 2
        # first stream should mention the original query
        assert "Browsing the web to learn more about the task: test query" in stream_calls[0][2]
        # second stream should mention planning the research strategy
        assert "Planning the research strategy and subtasks" in stream_calls[1][2]
        # websocket passed through correctly
        assert stream_calls[0][3] == "fake_ws"
        assert stream_calls[1][3] == "fake_ws"

        # get_search_results was called with the expected parameters
        assert get_search_called["query"] == "test query"
        assert get_search_called["retriever"] is fake_retriever
        assert get_search_called["query_domains"] == ["domain1"]
        assert get_search_called["researcher"] is fake_researcher

        # plan_research_outline received the expected forwarded parameters
        # check presence and some values
        assert plan_outline_called["query"] == "test query"
        assert plan_outline_called["search_results"] == ["resultA", "resultB"]
        assert plan_outline_called["agent_role_prompt"] == fake_researcher.role
        assert plan_outline_called["cfg"] == fake_researcher.cfg
        assert plan_outline_called["parent_query"] == fake_researcher.parent_query
        assert plan_outline_called["report_type"] == fake_researcher.report_type
        # cost_callback should be the same callable passed in researcher.add_costs
        assert plan_outline_called["cost_callback"] is fake_researcher.add_costs
        # retriever_names should be passed as a list containing the retriever's __name__
        assert plan_outline_called["retriever_names"] == ["fake_retriever"]
        # kwargs expansion preserved
        assert plan_outline_called["extra_flag"] is True

        # logger recorded both informative messages: initial results and final outline
        # one info should mention the number of results
        assert any("Initial search results obtained: 2 results" in m for m in rc.logger.infos)
        # one info should mention the planned outline (stringified dict)
        assert any("Research outline planned: {'plan': 'ok'}" in m for m in rc.logger.infos)

    finally:
        # restore patched names to avoid side effects for other tests
        researcher_mod.stream_output = original_stream
        researcher_mod.get_search_results = original_get_search
        researcher_mod.plan_research_outline = original_plan_outline
