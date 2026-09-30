import asyncio
import pytest

from multi_agents.agents.editor import EditorAgent


class _FakeChain:
    def __init__(self):
        self.calls = []

    async def ainvoke(self, task_input, config=None):
        # record the exact inputs to verify config is propagated and task_input shape
        self.calls.append((task_input, config))
        # return the expected shape used by the implementation
        return {"draft": f"draft-{task_input.get('query')}"}


class _FakeWorkflow:
    def __init__(self, chain):
        self._chain = chain
        self.compile_called = False

    def compile(self):
        self.compile_called = True
        return self._chain


@pytest.mark.asyncio
async def test_run_parallel_research_multiple_round_147():
    # Create an EditorAgent instance without running __init__ so we can inject test doubles
    agent = object.__new__(EditorAgent)

    # Track that _initialize_agents is called and return a deterministic value
    init_called = {"called": False}

    def fake_initialize_agents():
        init_called["called"] = True
        return ["research-agent-1"]

    agent._initialize_agents = fake_initialize_agents

    # Prepare fake workflow and chain that record calls
    chain = _FakeChain()
    workflow = _FakeWorkflow(chain)
    agent._create_workflow = lambda: workflow

    # Provide a deterministic _create_task_input that preserves the shapes
    def fake_create_task_input(research_state, query, title):
        # Return a dict shape expected by the fake chain
        return {"query": query, "title": title}

    agent._create_task_input = fake_create_task_input

    # Record calls to logging method
    logged = {}

    def fake_log_parallel_research(queries):
        logged['queries'] = list(queries)

    agent._log_parallel_research = fake_log_parallel_research

    research_state = {"sections": ["q1", "q2"], "title": "MyTitle"}

    # Run the async method under test
    result = await EditorAgent.run_parallel_research(agent, research_state)

    # Assertions: initialization called, workflow compiled, logging called
    assert init_called["called"] is True
    assert workflow.compile_called is True
    assert logged["queries"] == ["q1", "q2"]

    # The fake chain should have been invoked once per section with correct inputs
    assert len(chain.calls) == 2
    for (task_input, config), expected_q in zip(chain.calls, ["q1", "q2"]):
        assert task_input == {"query": expected_q, "title": "MyTitle"}
        # confirm config propagation and exact tag value
        assert isinstance(config, dict)
        assert config.get("tags") == ["gpt-researcher"]

    # The return value should aggregate the drafts in order
    assert result == {"research_data": ["draft-q1", "draft-q2"]}


@pytest.mark.asyncio
async def test_run_parallel_research_empty_sections_round_147():
    # Instance without __init__, inject test doubles
    agent = object.__new__(EditorAgent)

    agent._initialize_agents = lambda: []

    # Chain that would raise if invoked; we expect it not to be invoked
    chain = _FakeChain()
    workflow = _FakeWorkflow(chain)
    agent._create_workflow = lambda: workflow

    # _create_task_input should not be called in this scenario, but provide one just in case
    called_task_inputs = []

    def fake_create_task_input(research_state, query, title):
        called_task_inputs.append((research_state, query, title))
        return {"query": query, "title": title}

    agent._create_task_input = fake_create_task_input

    logged = {}

    def fake_log_parallel_research(queries):
        logged['queries'] = list(queries)

    agent._log_parallel_research = fake_log_parallel_research

    research_state = {"sections": [], "title": None}

    result = await EditorAgent.run_parallel_research(agent, research_state)

    # Ensure logging saw the empty list and no tasks were created/invoked
    assert logged["queries"] == []
    assert called_task_inputs == []
    assert chain.calls == []

    # And returned research_data is an empty list
    assert result == {"research_data": []}
