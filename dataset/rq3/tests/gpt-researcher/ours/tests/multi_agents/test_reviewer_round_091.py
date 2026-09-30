import asyncio
import importlib
import types
from multi_agents.agents.reviewer import ReviewerAgent


def _make_async_method(return_value=None, raise_on_call=False):
    async def _fn(self, draft_state):
        if raise_on_call:
            raise AssertionError("review_draft should not be called")
        return return_value

    return _fn


def test_run_follow_and_verbose_round_091():
    # Arrange
    reviewer_mod = importlib.import_module("multi_agents.agents.reviewer")

    captured = []

    def fake_print_agent_output(msg, agent=None):
        # preserve signature (message, agent=...)
        captured.append((msg, agent))

    # Patch the module symbol where ReviewerAgent.run resolves it
    reviewer_mod.print_agent_output = fake_print_agent_output

    # Create agent (use constructor signature: websocket, stream_output, headers)
    agent = ReviewerAgent(None, False, {})

    # Patch the instance review_draft to a deterministic async stub
    fake_return = {"score": 5, "note": "ok"}
    agent.review_draft = types.MethodType(_make_async_method(return_value=fake_return), agent)

    draft_state = {
        "task": {
            "guidelines": "Keep it short",
            "follow_guidelines": True,
            "verbose": True,
        }
    }

    # Act
    result = asyncio.run(agent.run(draft_state))

    # Assert
    assert result == {"review": fake_return}

    # check that the expected print messages occurred
    # one message for entering review and one for verbose follow_guidelines
    messages = [m for m, _ in captured]
    assert any("Reviewing draft" in m for m in messages), "expected 'Reviewing draft' message"
    assert any("Following guidelines Keep it short" in m for m in messages), "expected verbose guidelines message"


def test_run_ignore_guidelines_round_091():
    # Arrange
    reviewer_mod = importlib.import_module("multi_agents.agents.reviewer")

    captured = []

    def fake_print_agent_output(msg, agent=None):
        captured.append((msg, agent))

    reviewer_mod.print_agent_output = fake_print_agent_output

    agent = ReviewerAgent(None, False, {})

    # Make review_draft raise if called to ensure the branch is not taken
    agent.review_draft = types.MethodType(_make_async_method(raise_on_call=True), agent)

    draft_state = {
        "task": {
            "guidelines": "Do nothing",
            "follow_guidelines": False,
        }
    }

    # Act
    result = asyncio.run(agent.run(draft_state))

    # Assert
    assert result == {"review": None}

    messages = [m for m, _ in captured]
    assert any("Ignoring guidelines" in m for m in messages), "expected 'Ignoring guidelines' message"
