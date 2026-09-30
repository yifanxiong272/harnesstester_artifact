import asyncio
import json
import types
import importlib
import pytest

from multi_agents.agents.writer import WriterAgent
import multi_agents.agents.writer as writer_mod

@pytest.mark.asyncio
async def test_writer_run_with_websocket_and_stream_round_048(monkeypatch):
    """
    Exercise the branches where a websocket and stream_output are provided.
    - Ensures stream_output is awaited for the initial "writing_report" message and
      again for the research_layout_content (JSON string).
    - Ensures print_agent_output is NOT called in this path.
    - Asserts returned payload preserves the write_sections content and headers.
    """
    calls = []

    async def dummy_stream(kind, name, message, websocket):
        # capture exact arguments passed for assertions
        calls.append((kind, name, message, websocket))

    # Prevent any accidental printing path from being used
    def fail_print(*args, **kwargs):
        raise AssertionError("print_agent_output should not be called in websocket path")

    monkeypatch.setattr(writer_mod, "print_agent_output", fail_print)

    # Create a WriterAgent with websocket and stream_output set
    agent = WriterAgent("FAKE_WS", dummy_stream, headers=None)

    # Provide a deterministic write_sections implementation
    async def fake_write_sections(state):
        # produce a structure that when json.dumps(..., indent=2) is called
        # will contain a predictable substring for assertions
        return {"section": "value"}

    agent.write_sections = fake_write_sections

    # Provide a deterministic get_headers
    def fake_get_headers(state):
        return {"Authorization": "init-token"}

    agent.get_headers = fake_get_headers

    research_state = {"task": {"verbose": True, "follow_guidelines": False}}

    result = await agent.run(research_state)

    # The returned content should merge the layout content with headers
    assert result["section"] == "value"
    assert result["headers"] == {"Authorization": "init-token"}

    # Two stream calls expected: initial writing_report and research_layout_content
    assert len(calls) == 2
    # first call is the initial message
    assert calls[0][0] == "logs"
    assert calls[0][1] == "writing_report"
    assert "Writing final research report" in str(calls[0][2])
    assert calls[0][3] == "FAKE_WS"

    # second call should be the JSON representation of research_layout_content
    assert calls[1][0] == "logs"
    assert calls[1][1] == "research_layout_content"
    assert isinstance(calls[1][2], str)
    # json indentation should produce a readable JSON string containing our key/value
    assert '"section": "value"' in calls[1][2]
    assert calls[1][3] == "FAKE_WS"


@pytest.mark.asyncio
async def test_writer_run_without_websocket_prints_and_revises_round_048(monkeypatch):
    """
    Exercise the branches where no websocket/stream_output are provided and
    follow_guidelines is True.
    - Ensures print_agent_output is used for top-level messages and the layout content.
    - Ensures revise_headers is awaited and its inner "headers" value is extracted.
    - Asserts final returned headers are the revised headers.
    """
    printed = []

    def fake_print_agent_output(msg, agent="WRITER"):
        # capture calls (both strings and dicts are valid inputs in the code)
        printed.append((msg, agent))

    monkeypatch.setattr(writer_mod, "print_agent_output", fake_print_agent_output)

    # Create a WriterAgent with no websocket (so print path is taken)
    agent = WriterAgent(None, None, headers=None)

    # deterministic write_sections
    async def fake_write_sections(state):
        return {"layout": "ok"}

    agent.write_sections = fake_write_sections

    # deterministic get_headers
    def fake_get_headers(state):
        return {"initial": "h"}

    agent.get_headers = fake_get_headers

    # deterministic revise_headers that matches expected return shape
    async def fake_revise_headers(task, headers):
        # return the shape: {"headers": {...}}
        return {"headers": {"Authorization": "Bearer X"}}

    agent.revise_headers = fake_revise_headers

    research_state = {"task": {"verbose": True, "follow_guidelines": True}}

    result = await agent.run(research_state)

    # Ensure layout content is preserved
    assert result["layout"] == "ok"

    # Ensure final headers were pulled from revise_headers return value
    assert result["headers"] == {"Authorization": "Bearer X"}

    # Confirm that print_agent_output was used at least for the final report message,
    # the research_layout_content (dict), and the rewriting layout message.
    messages = [p[0] for p in printed]
    # one message should contain the initial writing text
    assert any("Writing final research report" in str(m) for m in messages)
    # one entry should be the dict produced by write_sections
    assert any(isinstance(m, dict) and m.get("layout") == "ok" for m in messages)
    # one message should indicate rewriting layout
    assert any("Rewriting layout based on guidelines" in str(m) for m in messages)
