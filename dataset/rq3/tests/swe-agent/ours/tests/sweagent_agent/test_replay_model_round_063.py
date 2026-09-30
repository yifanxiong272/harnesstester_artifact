import json
from types import SimpleNamespace
from pathlib import Path
import pytest

from sweagent.agent.models import ReplayModel


class DummyConfig:
    def __init__(self, replay_path: Path):
        # ReplayModel expects a Path-like at config.replay_path
        self.replay_path = replay_path


def _make_model_with_file(tmp_path, content: str, use_function_calling: bool, submit_command: str):
    """Helper to write a simple single-line JSON replay and construct the model."""
    p = tmp_path / "replay.traj"
    # Keepends=True is used by the implementation; include a newline to match behavior
    p.write_text(content)
    cfg = DummyConfig(p)
    tools = SimpleNamespace(use_function_calling=use_function_calling, submit_command=submit_command)
    return ReplayModel(cfg, tools)


def test_submit_triggers_next_replay_round_063(tmp_path):
    """When the replay contains the literal string 'submit' as an action,
    query should return {'message': 'submit'} and advance to the next replay (._replay_idx += 1).
    """
    # One-line JSON where the value is a list with the string 'submit'
    content = '{"0": ["submit"]}\n'
    model = _make_model_with_file(tmp_path, content, use_function_calling=False, submit_command="do_submit")

    result = model.query(None)

    assert result == {"message": "submit"}
    # _next_replay increments _replay_idx and resets _action_idx to 0
    assert model._replay_idx == 1
    assert model._action_idx == 0


def test_index_error_use_function_calling_false_round_063(tmp_path):
    """When the actions list is empty and use_function_calling is False,
    the model should construct a fenced-code action using submit_command and
    return it wrapped as {'message': <fenced>}.
    Also ensure internal indices are updated predictably.
    """
    # An empty action list triggers the IndexError path in query
    content = '{"0": []}\n'
    submit_cmd = "do_submit"
    model = _make_model_with_file(tmp_path, content, use_function_calling=False, submit_command=submit_cmd)

    result = model.query(None)

    expected_message = f"```\n{submit_cmd}\n```"
    assert isinstance(result, dict)
    assert result.get("message") == expected_message

    # After attempting to pull an action, _action_idx is incremented by 1
    assert model._action_idx == 1
    # No replay rollover should have occurred in this case
    assert model._replay_idx == 0


def test_index_error_use_function_calling_true_returns_dict_round_063(tmp_path):
    """When the actions list is empty and use_function_calling is True,
    the model should return a dict action with message and tool_calls describing the function call.
    """
    content = '{"0": []}\n'
    submit_cmd = "submit_cmd"
    model = _make_model_with_file(tmp_path, content, use_function_calling=True, submit_command=submit_cmd)

    result = model.query(None)

    # Should be the dict constructed in the except branch when use_function_calling is True
    assert isinstance(result, dict)
    assert "message" in result
    assert f"Calling `{submit_cmd}` to submit." == result["message"]

    # Validate the tool_calls payload shape
    assert "tool_calls" in result
    tool_calls = result["tool_calls"]
    assert isinstance(tool_calls, list) and len(tool_calls) == 1
    tc = tool_calls[0]
    assert tc.get("type") == "function"
    assert tc.get("id") == "call_submit"
    func = tc.get("function")
    assert isinstance(func, dict)
    assert func.get("name") == submit_cmd
    assert func.get("arguments") == "{}"

    # Internal action index should have been incremented
    assert model._action_idx == 1
