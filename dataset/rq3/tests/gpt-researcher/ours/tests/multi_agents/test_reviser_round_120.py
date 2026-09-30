import pytest
import types
from multi_agents.agents.reviser import ReviserAgent


@pytest.mark.asyncio
async def test_run_streaming_round_120(monkeypatch):
    # Capture calls to print_agent_output
    print_calls = []

    def fake_print(msg, agent=None):
        print_calls.append((msg, agent))

    monkeypatch.setattr("multi_agents.agents.reviser.print_agent_output", fake_print)

    # Prepare a fake stream_output coroutine that records its args
    stream_calls = []

    async def fake_stream(kind, name, message, websocket):
        stream_calls.append((kind, name, message, websocket))

    # Create a truthy websocket object and ReviserAgent with stream_output provided
    websocket_obj = object()
    agent = ReviserAgent(websocket_obj, fake_stream, headers={})

    # Patch the instance revise_draft to a controlled coroutine
    async def fake_revise(self, draft_state):
        return {"revision_notes": "notes", "draft": {"content": "new content"}}

    # bind async method to the instance
    agent.revise_draft = types.MethodType(fake_revise, agent)

    draft_state = {"task": {"verbose": True}}

    result = await agent.run(draft_state)

    # Initial print should have been called once announcing rewrite
    assert len(print_calls) == 1
    assert print_calls[0][0].startswith("Rewriting draft based on feedback")
    assert print_calls[0][1] == "REVISOR"

    # Because websocket and stream_output are present, stream_output should have been awaited with revision notes
    assert len(stream_calls) == 1
    assert stream_calls[0] == (
        "logs",
        "revision_notes",
        "Revision notes: notes",
        websocket_obj,
    )

    # Final returned structure should map draft and revision_notes from the revision
    assert result == {
        "draft": {"content": "new content"},
        "revision_notes": "notes",
    }


@pytest.mark.asyncio
async def test_run_verbose_no_stream_round_120(monkeypatch):
    # This test covers verbose=True but missing websocket/stream_output -> fallback to print_agent_output
    print_calls = []

    def fake_print(msg, agent=None):
        print_calls.append((msg, agent))

    monkeypatch.setattr("multi_agents.agents.reviser.print_agent_output", fake_print)

    # Create agent with no websocket and no stream_output
    agent = ReviserAgent(None, None, headers=None)

    async def fake_revise(self, draft_state):
        return {"revision_notes": "verbose-notes", "draft": {"content": "v2"}}

    agent.revise_draft = types.MethodType(fake_revise, agent)

    draft_state = {"task": {"verbose": True}}

    result = await agent.run(draft_state)

    # First call is the initial rewriting announcement; second is the revision notes printed via print_agent_output
    assert len(print_calls) == 2
    assert print_calls[0][0].startswith("Rewriting draft based on feedback")
    assert print_calls[0][1] == "REVISOR"

    # The second print is the revision notes
    assert print_calls[1] == ("Revision notes: verbose-notes", "REVISOR")

    assert result == {"draft": {"content": "v2"}, "revision_notes": "verbose-notes"}


@pytest.mark.asyncio
async def test_run_not_verbose_round_120(monkeypatch):
    # This test covers the branch when verbose is falsy: no extra printing/streaming occurs
    print_calls = []

    def fake_print(msg, agent=None):
        print_calls.append((msg, agent))

    monkeypatch.setattr("multi_agents.agents.reviser.print_agent_output", fake_print)

    agent = ReviserAgent(None, None, headers=None)

    async def fake_revise(self, draft_state):
        return {"revision_notes": "quiet-notes", "draft": {"content": "quiet"}}

    agent.revise_draft = types.MethodType(fake_revise, agent)

    draft_state = {"task": {"verbose": False}}

    result = await agent.run(draft_state)

    # Only the initial rewriting announcement should be printed
    assert len(print_calls) == 1
    assert print_calls[0][0].startswith("Rewriting draft based on feedback")
    assert print_calls[0][1] == "REVISOR"

    assert result == {"draft": {"content": "quiet"}, "revision_notes": "quiet-notes"}
