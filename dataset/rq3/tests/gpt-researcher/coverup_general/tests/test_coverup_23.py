# file: multi_agents/agents/human.py:10-59
# asked: {"lines": [10, 11, 12, 13, 14, 16, 18, 20, 21, 22, 23, 24, 25, 26, 29, 30, 31, 32, 33, 35, 36, 37, 39, 40, 43, 44, 47, 48, 50, 51, 52, 54, 56, 57, 58], "branches": [[18, 20], [18, 47], [20, 21], [20, 43], [32, 33], [32, 35], [47, 48], [47, 50], [51, 52], [51, 54]]}
# gained: {"lines": [10, 11, 12, 13, 14, 16, 18, 20, 21, 22, 23, 24, 25, 26, 29, 30, 31, 32, 33, 35, 36, 37, 39, 40, 43, 44, 47, 48, 50, 51, 52, 54, 56, 57, 58], "branches": [[18, 20], [18, 47], [20, 21], [20, 43], [32, 33], [32, 35], [47, 48], [47, 50], [51, 52], [51, 54]]}

import json
import builtins
import sys
import importlib.util
from pathlib import Path

import pytest


def _load_human_agent_class():
    """
    Try to import HumanAgent from the package. If the package path is not importable
    (ModuleNotFoundError), locate the human.py file under a repository directory named
    'gpt_researcher' or 'gpt-researcher' and load it as a module.
    """
    try:
        # Preferred import if package is on sys.path
        from gpt_researcher.multi_agents.agents.human import HumanAgent  # type: ignore
        return HumanAgent
    except Exception:
        # Search upward from this file for the project directory
        current = Path(__file__).resolve()
        for parent in [current] + list(current.parents):
            for candidate_name in ("gpt_researcher", "gpt-researcher"):
                candidate = parent / candidate_name / "multi_agents" / "agents" / "human.py"
                if candidate.is_file():
                    spec = importlib.util.spec_from_file_location("tests._temp_human_module", str(candidate))
                    module = importlib.util.module_from_spec(spec)
                    loader = spec.loader
                    assert loader is not None
                    loader.exec_module(module)
                    return getattr(module, "HumanAgent")
        raise ModuleNotFoundError("Could not find human.py in expected locations")


HumanAgent = _load_human_agent_class()


class _InnerWS:
    def __init__(self, text_or_exc):
        """
        text_or_exc: either a JSON string to return from receive_text,
                     or an Exception instance to raise when receive_text is awaited.
        """
        self._text_or_exc = text_or_exc

    async def receive_text(self):
        if isinstance(self._text_or_exc, Exception):
            raise self._text_or_exc
        return self._text_or_exc


class _WSWrapper:
    def __init__(self, inner):
        # HumanAgent expects self.websocket.websocket.receive_text()
        self.websocket = inner


@pytest.mark.asyncio
async def test_review_plan_with_websocket_human_feedback():
    # prepare websocket that returns a JSON with type human_feedback
    payload = {"type": "human_feedback", "content": "Looks good"}
    inner = _InnerWS(json.dumps(payload))
    ws = _WSWrapper(inner)

    called = []

    async def fake_stream_output(event, t, msg, websocket_arg):
        # record call and ensure websocket passed is our wrapper
        called.append((event, t, msg, websocket_arg))

    agent = HumanAgent(websocket=ws, stream_output=fake_stream_output)
    research_state = {"task": {"include_human_feedback": True}, "sections": ["a", "b"], "plan_revision_count": 0}

    result = await agent.review_plan(research_state)

    assert called, "stream_output should have been called"
    assert called[0][0] == "human_feedback"
    assert result["human_feedback"] == "Looks good"
    assert result["plan_revision_count"] == 1


@pytest.mark.asyncio
async def test_review_plan_with_websocket_unexpected_response_type():
    # prepare websocket that returns a JSON with unexpected type
    payload = {"type": "something_else", "content": "Ignore me"}
    inner = _InnerWS(json.dumps(payload))
    ws = _WSWrapper(inner)

    async def fake_stream_output(event, t, msg, websocket_arg):
        # simulate normal call but do nothing
        return

    agent = HumanAgent(websocket=ws, stream_output=fake_stream_output)
    research_state = {"task": {"include_human_feedback": True}, "sections": "layout", "plan_revision_count": 0}

    result = await agent.review_plan(research_state)

    # Since the response type wasn't "human_feedback", user_feedback remains None
    assert result["human_feedback"] is None
    assert result["plan_revision_count"] == 0


@pytest.mark.asyncio
async def test_review_plan_with_input_feedback_yes(monkeypatch):
    # No websocket provided -> should prompt via input
    # Patch input to return a non-"no" answer
    monkeypatch.setattr(builtins, "input", lambda prompt="": "I want more details")

    agent = HumanAgent(websocket=None, stream_output=None)
    research_state = {"task": {"include_human_feedback": True}, "sections": ["s1"], "plan_revision_count": 2}

    result = await agent.review_plan(research_state)

    assert result["human_feedback"] == "I want more details"
    # plan_revision_count should increment when feedback provided
    assert result["plan_revision_count"] == 3


@pytest.mark.asyncio
async def test_review_plan_with_input_feedback_no(monkeypatch):
    # input returns "no" (various casing/spaces)
    monkeypatch.setattr(builtins, "input", lambda prompt="": "  No  ")

    agent = HumanAgent(websocket=None, stream_output=None)
    research_state = {"task": {"include_human_feedback": True}, "sections": ["s1"], "plan_revision_count": 5}

    result = await agent.review_plan(research_state)

    # 'no' should be interpreted as no feedback -> human_feedback is None and count unchanged
    assert result["human_feedback"] is None
    assert result["plan_revision_count"] == 5


@pytest.mark.asyncio
async def test_review_plan_with_stream_output_raising_exception():
    # Provide websocket and a stream_output that raises to hit the exception branch
    inner = _InnerWS("unused")  # content won't be used because stream_output raises
    ws = _WSWrapper(inner)

    async def raising_stream_output(event, t, msg, websocket_arg):
        raise RuntimeError("stream error")

    agent = HumanAgent(websocket=ws, stream_output=raising_stream_output)
    research_state = {"task": {"include_human_feedback": True}, "sections": ["x"], "plan_revision_count": 0}

    result = await agent.review_plan(research_state)

    # On exception, feedback should remain None and count unchanged
    assert result["human_feedback"] is None
    assert result["plan_revision_count"] == 0


@pytest.mark.asyncio
async def test_review_plan_with_no_human_feedback_flag():
    # include_human_feedback False -> should skip prompts entirely
    agent = HumanAgent(websocket=None, stream_output=None)
    research_state = {"task": {"include_human_feedback": False}, "sections": ["a"], "plan_revision_count": 7}

    result = await agent.review_plan(research_state)
    assert result["human_feedback"] is None
    assert result["plan_revision_count"] == 7
