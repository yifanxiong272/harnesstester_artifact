import asyncio
from multi_agents.agents import researcher as researcher_mod
from multi_agents.agents.researcher import ResearchAgent


def test_run_initial_research_streaming_round_148():
    """Verify the streaming branch (self.websocket and self.stream_output truthy).

    - stream_output should be awaited with expected args
    - research should be awaited and its return forwarded in the result
    """
    # Prepare agent with placeholders
    agent = ResearchAgent(websocket=None, stream_output=None, tone="friendly", headers={"h": "v"})

    # Provide a truthy websocket and async stream_output implementation that records calls
    ws = object()
    agent.websocket = ws
    stream_calls = []

    async def fake_stream_output(event, key, message, websocket):
        # record invocation for assertion
        stream_calls.append((event, key, message, websocket))
        return None

    agent.stream_output = fake_stream_output

    # Provide an async fake research that echoes the inputs for deterministic assertions
    async def fake_research(query, verbose, source, tone, headers):
        return {
            "ok": True,
            "query": query,
            "verbose": verbose,
            "source": source,
            "tone": tone,
            "headers": headers,
        }

    agent.research = fake_research

    # Create a research_state with explicit values (including a non-default source)
    task = {"query": "find the meaning of life", "verbose": False, "source": "local"}
    research_state = {"task": task}

    # Run the async method synchronously for test determinism
    result = asyncio.run(agent.run_initial_research(research_state))

    # Assertions: the stream_output must have been called exactly once with expected values
    assert len(stream_calls) == 1, "stream_output should be awaited once"
    event, key, message, websocket_passed = stream_calls[0]
    assert event == "logs"
    assert key == "initial_research"
    assert "Running initial research on the following query: find the meaning of life" in message
    assert websocket_passed is ws

    # The returned structure should include the original task and research result
    assert result["task"] is task
    assert result["initial_research"]["query"] == "find the meaning of life"
    assert result["initial_research"]["source"] == "local"
    # Ensure tone and headers were passed through
    assert result["initial_research"]["tone"] == agent.tone
    assert result["initial_research"]["headers"] == agent.headers


def test_run_initial_research_print_branch_round_148(monkeypatch):
    """Verify the non-streaming branch where print_agent_output is used.

    - print_agent_output should be invoked with the expected message and agent name
    - research should be awaited and its return forwarded
    """
    # Create agent with no websocket and no stream_output so the print branch is taken
    agent = ResearchAgent(websocket=None, stream_output=None, tone="formal", headers={"x": "y"})

    # Patch the module-level print_agent_output to capture its inputs
    printed = {}

    def fake_print_agent_output(message, agent=None):
        printed["message"] = message
        printed["agent"] = agent

    monkeypatch.setattr(researcher_mod, "print_agent_output", fake_print_agent_output)

    # Provide an async fake research that returns identifiable payload
    async def fake_research(query, verbose, source, tone, headers):
        return {
            "ok": True,
            "query": query,
            "verbose": verbose,
            "source": source,
            "tone": tone,
            "headers": headers,
        }

    agent.research = fake_research

    # Provide a task that omits 'source' to exercise the defaulting to 'web'
    task = {"query": "test default source", "verbose": True}
    research_state = {"task": task}

    # Execute
    result = asyncio.run(agent.run_initial_research(research_state))

    # Assert print_agent_output was called with expected signature and content
    assert printed.get("message") is not None
    assert "Running initial research on the following query: test default source" in printed["message"]
    assert printed.get("agent") == "RESEARCHER"

    # Assert returned research payload used default source 'web' and passed through tone/headers
    assert result["task"] is task
    assert result["initial_research"]["query"] == "test default source"
    assert result["initial_research"]["source"] == "web"
    assert result["initial_research"]["tone"] == agent.tone
    assert result["initial_research"]["headers"] == agent.headers
