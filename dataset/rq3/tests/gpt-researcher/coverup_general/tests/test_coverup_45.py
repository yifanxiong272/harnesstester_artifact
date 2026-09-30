# file: gpt_researcher/skills/researcher.py:48-87
# asked: {"lines": [55, 56, 57, 58, 59, 62, 63, 65, 66, 67, 68, 69, 72, 75, 76, 77, 78, 79, 80, 81, 82, 83, 84, 86, 87], "branches": []}
# gained: {"lines": [55, 56, 57, 58, 59, 62, 63, 65, 66, 67, 68, 69, 72, 75, 76, 77, 78, 79, 80, 81, 82, 83, 84, 86, 87], "branches": []}

import pytest
from types import SimpleNamespace

# Import the class under test and get its module for patching
from gpt_researcher.skills.researcher import ResearchConductor


class DummyLogger:
    def __init__(self):
        self.infos = []

    def info(self, msg):
        self.infos.append(msg)


@pytest.mark.asyncio
async def test_plan_research_calls_stream_and_returns_outline(monkeypatch):
    """Ensure plan_research calls stream_output twice, calls get_search_results and plan_research_outline,
    logs info messages, and returns the outline produced by plan_research_outline."""
    # Prepare collector structures to assert calls
    stream_calls = []
    search_called = {}
    outline_called = {}

    async def fake_stream_output(channel, stage, message, websocket):
        # record the call and ensure it's awaitable
        stream_calls.append((channel, stage, message, websocket))
        return None

    async def fake_get_search_results(query, retriever, query_domains, researcher=None):
        # record inputs and return a list of fake search results
        search_called['query'] = query
        search_called['retriever'] = retriever
        search_called['query_domains'] = query_domains
        search_called['researcher'] = researcher
        return ["result1", "result2"]

    async def fake_plan_research_outline(**kwargs):
        # record that it was called and the kwargs passed
        outline_called.update(kwargs)
        # return a fake outline object
        return {"outline": ["task1", "task2"], "kwargs_passed": kwargs}

    # Patch the names inside the researcher module (they were imported there at module import time)
    module_path = ResearchConductor.__module__
    monkeypatch.setattr(f"{module_path}.stream_output", fake_stream_output, raising=True)
    monkeypatch.setattr(f"{module_path}.get_search_results", fake_get_search_results, raising=True)
    monkeypatch.setattr(f"{module_path}.plan_research_outline", fake_plan_research_outline, raising=True)

    # Create dummy retriever functions to ensure __name__ works
    def retriever_one(q):  # simple callable
        return []

    # Fake researcher object with attributes used by plan_research
    researcher_obj = SimpleNamespace()
    researcher_obj.websocket = object()
    researcher_obj.retrievers = [retriever_one]
    researcher_obj.role = "researcher-role"
    researcher_obj.cfg = {"some": "cfg"}
    researcher_obj.parent_query = "parent"
    researcher_obj.report_type = "report"
    researcher_obj.kwargs = {}
    researcher_obj.add_costs = lambda c: None

    # Build a ResearchConductor instance with the researcher argument
    rc = ResearchConductor(researcher_obj)
    # Replace logger with dummy to capture logs
    rc.logger = DummyLogger()

    # Call the method under test
    query = "What is the impact of AI on education?"
    outline = await rc.plan_research(query)

    # Assertions: ensure stream_output called twice and messages include the query and planning text
    assert len(stream_calls) == 2
    assert any(query in call[2] for call in stream_calls), "stream_output messages should include the query"
    assert any("planning the research strategy" in call[2].lower() for call in stream_calls)

    # get_search_results must have been called with our query and retriever
    assert search_called["query"] == query
    assert search_called["retriever"] is retriever_one
    assert search_called["query_domains"] is None
    assert search_called["researcher"] is researcher_obj

    # plan_research_outline must have been called and returned outline must be forwarded
    assert isinstance(outline, dict)
    assert "outline" in outline and outline["outline"] == ["task1", "task2"]
    # ensure that the outline caller received expected keys
    assert outline_called["query"] == query
    assert outline_called["search_results"] == ["result1", "result2"]
    assert outline_called["agent_role_prompt"] == researcher_obj.role
    assert outline_called["cfg"] == researcher_obj.cfg
    assert outline_called["parent_query"] == researcher_obj.parent_query
    assert outline_called["report_type"] == researcher_obj.report_type
    # cost callback should be exactly the add_costs function we provided
    assert outline_called["cost_callback"] == researcher_obj.add_costs
    # retriever_names passed should be a list with the function's __name__
    assert outline_called["retriever_names"] == [retriever_one.__name__]

    # Logger should have been used to log at least the initial results and outline
    assert any("Initial search results obtained" in s for s in rc.logger.infos)
    assert any("Research outline planned" in s for s in rc.logger.infos)


@pytest.mark.asyncio
async def test_plan_research_with_query_domains_and_kwargs(monkeypatch):
    """Exercise the code path with explicit query_domains and researcher.kwargs to ensure those are forwarded."""
    stream_calls = []
    called = {}

    async def fake_stream_output(channel, stage, message, websocket):
        stream_calls.append((channel, stage, message, websocket))

    async def fake_get_search_results(query, retriever, query_domains, researcher=None):
        called['query'] = query
        called['query_domains'] = query_domains
        return []  # no results case

    async def fake_plan_research_outline(**kwargs):
        called['plan_kwargs'] = kwargs
        return ["only_task"]

    module_path = ResearchConductor.__module__
    monkeypatch.setattr(f"{module_path}.stream_output", fake_stream_output, raising=True)
    monkeypatch.setattr(f"{module_path}.get_search_results", fake_get_search_results, raising=True)
    monkeypatch.setattr(f"{module_path}.plan_research_outline", fake_plan_research_outline, raising=True)

    # Define retrievers with distinct names
    def retr_a(q): return []
    def retr_b(q): return []

    researcher_obj = SimpleNamespace()
    researcher_obj.websocket = object()
    researcher_obj.retrievers = [retr_a, retr_b]
    researcher_obj.role = "role2"
    researcher_obj.cfg = {"foo": "bar"}
    researcher_obj.parent_query = None
    researcher_obj.report_type = "summary"
    researcher_obj.kwargs = {"extra_param": 42}
    # Add a state-changing add_costs to ensure it's passed through (and doesn't error)
    costs = {"value": 0}

    def add_costs(amount):
        costs["value"] += amount

    researcher_obj.add_costs = add_costs

    rc = ResearchConductor(researcher_obj)
    rc.logger = DummyLogger()

    query = "Test domains"
    domains = ["example.com", "another.org"]

    outline = await rc.plan_research(query, query_domains=domains)

    # Ensure stream_output called twice
    assert len(stream_calls) == 2
    # get_search_results saw the domains
    assert called["query_domains"] == domains
    # plan_research_outline was called and received the kwargs merged
    assert "plan_kwargs" in called
    pk = called["plan_kwargs"]
    assert pk["query"] == query
    assert pk["search_results"] == []
    assert pk["agent_role_prompt"] == researcher_obj.role
    assert pk["cfg"] == researcher_obj.cfg
    assert pk["parent_query"] is None
    assert pk["report_type"] == researcher_obj.report_type
    # cost_callback should be the same function
    assert pk["cost_callback"] is researcher_obj.add_costs
    # retriever_names should match both retriever names
    assert pk["retriever_names"] == [retr_a.__name__, retr_b.__name__]
    # kwargs from researcher.kwargs should have been expanded into plan_research_outline call
    assert pk["extra_param"] == 42
    # returned outline should be forwarded
    assert outline == ["only_task"]
