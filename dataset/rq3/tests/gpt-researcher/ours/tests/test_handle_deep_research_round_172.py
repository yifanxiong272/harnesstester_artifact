import pytest
import asyncio
from unittest.mock import AsyncMock
from gpt_researcher import agent as agent_module

GPTResearcher = agent_module.GPTResearcher

@pytest.mark.asyncio
async def test_handle_deep_research_success_round_172():
    # Create instance without running __init__ to keep test isolated and deterministic
    inst = object.__new__(GPTResearcher)

    # Prepare a fake deep_researcher with attributes used by the method
    deep = type("DeepMock", (), {})()
    deep.breadth = 5
    deep.depth = 2
    deep.concurrency_limit = 4
    # run should be an async function returning a context list
    expected_context = ["result1", "result2", "result3"]
    deep.run = AsyncMock(return_value=expected_context)

    # Attach the mock deep_researcher and other required attributes
    inst.deep_researcher = deep
    inst.query = "test query"
    inst.visited_urls = ["http://a", "http://b"]

    # get_costs is synchronous in the source; patch to return a deterministic value
    def fake_get_costs():
        return 123.45
    inst.get_costs = fake_get_costs

    # _log_event should be an async callable; use AsyncMock to capture calls
    inst._log_event = AsyncMock()

    # Ensure context attribute starts as None to validate assignment
    inst.context = None

    # Call the async method under test
    returned = await GPTResearcher._handle_deep_research(inst, on_progress=None)

    # Verify returned context is what deep_researcher.run returned
    assert returned is expected_context
    assert inst.context is expected_context

    # _log_event should have been awaited 4 times for the steps in the method
    assert inst._log_event.await_count == 4

    # Inspect the sequence of calls and their kwargs
    calls = inst._log_event.await_args_list
    # Call 0: deep_research_initialize
    args0, kwargs0 = calls[0]
    assert args0[0] == "research"
    assert kwargs0.get("step") == "deep_research_initialize"
    details0 = kwargs0.get("details")
    assert isinstance(details0, dict)
    assert details0["type"] == "deep_research"
    assert details0["breadth"] == deep.breadth
    assert details0["depth"] == deep.depth
    assert details0["concurrency"] == deep.concurrency_limit

    # Call 1: deep_research_start
    args1, kwargs1 = calls[1]
    assert args1[0] == "research"
    assert kwargs1.get("step") == "deep_research_start"
    details1 = kwargs1.get("details")
    assert details1["query"] == inst.query
    assert details1["breadth"] == deep.breadth
    assert details1["depth"] == deep.depth
    assert details1["concurrency"] == deep.concurrency_limit

    # Call 2: deep_research_complete
    args2, kwargs2 = calls[2]
    assert args2[0] == "research"
    assert kwargs2.get("step") == "deep_research_complete"
    details2 = kwargs2.get("details")
    assert details2["context_length"] == len(expected_context)
    assert details2["visited_urls"] == len(inst.visited_urls)
    assert details2["total_costs"] == 123.45

    # Call 3: cost_update
    args3, kwargs3 = calls[3]
    assert args3[0] == "research"
    assert kwargs3.get("step") == "cost_update"
    details3 = kwargs3.get("details")
    assert details3["cost"] == 123.45
    assert details3["total_cost"] == 123.45
    assert details3["research_type"] == "deep_research"


@pytest.mark.asyncio
async def test_handle_deep_research_empty_round_172():
    # Test the path where deep_researcher.run returns an empty context and zero costs
    inst = object.__new__(GPTResearcher)

    deep = type("DeepMock", (), {})()
    deep.breadth = 0
    deep.depth = 0
    deep.concurrency_limit = 1
    expected_context = []
    deep.run = AsyncMock(return_value=expected_context)

    inst.deep_researcher = deep
    inst.query = ""
    inst.visited_urls = []

    def fake_get_costs():
        return 0.0
    inst.get_costs = fake_get_costs

    inst._log_event = AsyncMock()
    inst.context = None

    returned = await GPTResearcher._handle_deep_research(inst, on_progress=None)

    assert returned == expected_context
    assert inst.context == expected_context

    # Validate logging calls reflect zero/empty values
    assert inst._log_event.await_count == 4
    calls = inst._log_event.await_args_list
    # Check deep_research_complete details for zero lengths
    _, kwargs2 = calls[2]
    details2 = kwargs2.get("details")
    assert details2["context_length"] == 0
    assert details2["visited_urls"] == 0
    assert details2["total_costs"] == 0.0

    # Final cost_update should also reflect zero
    _, kwargs3 = calls[3]
    details3 = kwargs3.get("details")
    assert details3["cost"] == 0.0
    assert details3["total_cost"] == 0.0
    assert details3["research_type"] == "deep_research"
