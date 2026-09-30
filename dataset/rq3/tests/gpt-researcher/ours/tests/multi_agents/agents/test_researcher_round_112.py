import asyncio
from multi_agents.agents.researcher import ResearchAgent
import builtins


def test_run_depth_research_with_stream_output_round_112(monkeypatch):
    # Prepare agent with websocket and async stream_output
    agent = ResearchAgent(websocket=object(), stream_output=None, headers={"h": "v"})

    stream_calls = []

    async def fake_stream(kind, tag, message, websocket):
        # capture call for assertion
        stream_calls.append((kind, tag, message, websocket))

    # Assign the async stream function to the instance
    agent.stream_output = fake_stream

    # Prepare an async stub for run_subtopic_research that records its inputs and returns a predictable draft
    run_calls = []

    async def fake_run_subtopic_research(parent_query=None, subtopic=None, verbose=None, source=None, headers=None):
        run_calls.append({
            "parent_query": parent_query,
            "subtopic": subtopic,
            "verbose": verbose,
            "source": source,
            "headers": headers,
        })
        return {"subtopic_result": subtopic}

    agent.run_subtopic_research = fake_run_subtopic_research

    # Build draft_state matching the code expectations
    draft_state = {
        "task": {"query": "parentQ", "source": "websource", "verbose": True},
        "topic": "deep-topic"
    }

    # Run the coroutine synchronously via asyncio.run for deterministic behavior
    result = asyncio.run(agent.run_depth_research(draft_state))

    # Assert stream_output was called exactly once with expected parameters
    assert len(stream_calls) == 1, "expected stream_output to be called once"
    kind, tag, message, websocket_passed = stream_calls[0]
    assert kind == "logs"
    assert tag == "depth_research"
    assert "Running in depth research on the following report topic: deep-topic" in message
    # the websocket passed through should be exactly the agent.websocket object
    assert websocket_passed is agent.websocket

    # Assert run_subtopic_research was invoked with expected parameters
    assert len(run_calls) == 1
    call = run_calls[0]
    assert call["parent_query"] == "parentQ"
    assert call["subtopic"] == "deep-topic"
    assert call["verbose"] is True
    assert call["source"] == "websource"
    # headers passed must be the agent.headers dict reference
    assert call["headers"] == {"h": "v"}

    # Ensure return shape matches code: {"draft": <research_draft>}
    assert result == {"draft": {"subtopic_result": "deep-topic"}}


def test_run_depth_research_without_stream_output_calls_print_agent_output_round_112(monkeypatch):
    # Prepare agent without websocket or stream_output to hit the print branch
    agent = ResearchAgent(websocket=None, stream_output=None, headers={"x": 1})

    printed = []

    # Patch print_agent_output imported in the module to capture calls deterministically
    def fake_print_agent_output(message, agent="UNKNOWN"):
        printed.append({"message": message, "agent": agent})

    monkeypatch.setattr("multi_agents.agents.researcher.print_agent_output", fake_print_agent_output)

    # Stub run_subtopic_research to return a known payload and capture invocation
    run_calls = []

    async def fake_run_subtopic_research(parent_query=None, subtopic=None, verbose=None, source=None, headers=None):
        run_calls.append((parent_query, subtopic, verbose, source, headers))
        return {"ok": True}

    agent.run_subtopic_research = fake_run_subtopic_research

    draft_state = {
        "task": {"query": "pq", "source": "web", "verbose": False},
        "topic": "t-2"
    }

    result = asyncio.run(agent.run_depth_research(draft_state))

    # Validate that print_agent_output was called (the else branch)
    assert len(printed) == 1
    assert "Running in depth research on the following report topic: t-2" in printed[0]["message"]
    assert printed[0]["agent"] == "RESEARCHER"

    # Confirm run_subtopic_research was called with the right values
    assert len(run_calls) == 1
    parent_query, subtopic, verbose, source, headers = run_calls[0]
    assert parent_query == "pq"
    assert subtopic == "t-2"
    assert verbose is False
    assert source == "web"
    assert headers == {"x": 1}

    # Check return structure
    assert result == {"draft": {"ok": True}}
