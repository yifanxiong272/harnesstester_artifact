# file: sweagent/run/run_replay.py:138-171
# asked: {"lines": [151, 152, 155, 163, 169, 170], "branches": [[150, 151], [161, 167], [168, 169]]}
# gained: {"lines": [151, 152, 155, 163, 169, 170], "branches": [[150, 151], [168, 169]]}

import json
from types import SimpleNamespace
from pathlib import Path
import pytest

from sweagent.run.run_replay import RunReplay


def _make_instance(traj_history, tmp_path, parse_function_type="no_function", instance_stem="test-instance"):
    """
    Create a RunReplay instance without calling __init__, and set only the attributes
    required by _create_actions_file.
    """
    inst = object.__new__(RunReplay)
    inst._traj_data = {"history": traj_history}
    inst.config = SimpleNamespace(
        agent=SimpleNamespace(
            tools=SimpleNamespace(
                parse_function=SimpleNamespace(type=parse_function_type)
            )
        )
    )
    # set traj_path so the instance_id property (Path(traj_path).stem) returns instance_stem
    inst.traj_path = tmp_path / f"{instance_stem}.json"
    # ensure the file exists (content doesn't matter)
    inst.traj_path.write_text("{}")
    inst._replay_action_trajs_path = tmp_path / "actions.json"
    return inst


def test_raises_if_tool_calls_present_but_config_not_function_calling(tmp_path):
    # History has an assistant item with tool_calls, but config parse_function.type is not 'function_calling'
    history = [
        {"role": "assistant", "content": "did something", "tool_calls": [{"name": "tool1"}]}
    ]
    inst = _make_instance(history, tmp_path, parse_function_type="no_fc", instance_stem="ti1")
    with pytest.raises(ValueError) as excinfo:
        inst._create_actions_file()
    msg = str(excinfo.value)
    assert "Trajectory contains tool calls" in msg
    assert "function_calling" in msg


def test_assert_when_function_calling_but_missing_tool_calls(tmp_path):
    # Config expects function_calling, but the assistant item is missing tool_calls -> assertion should fail
    history = [
        {"role": "assistant", "content": "response without tool calls"}  # no 'tool_calls' key
    ]
    inst = _make_instance(history, tmp_path, parse_function_type="function_calling", instance_stem="ti2")
    with pytest.raises(AssertionError) as excinfo:
        inst._create_actions_file()
    msg = str(excinfo.value)
    assert "Config is set to use `function_calling`" in msg
    assert "trajectory item 0" in msg


def test_raises_when_no_actions_found(tmp_path):
    # History contains only non-assistant roles -> should raise "No actions found in trajectory"
    history = [
        {"role": "user", "content": "hello"},
        {"role": "system", "content": "system msg"}
    ]
    inst = _make_instance(history, tmp_path, parse_function_type="no_fc", instance_stem="ti3")
    with pytest.raises(ValueError) as excinfo:
        inst._create_actions_file()
    assert "No actions found in trajectory" in str(excinfo.value)


def test_writes_actions_file_with_function_calling_and_tool_calls(tmp_path):
    # Successful case: function_calling enabled and assistant item includes tool_calls
    history = [
        {"role": "assistant", "content": "call tool", "tool_calls": [{"name": "toolA", "args": {}}]},
        {"role": "user", "content": "ignored user message"},
        {"role": "assistant", "content": "another action", "tool_calls": [{"name": "toolB", "args": {"x": 1}}]}
    ]
    inst = _make_instance(history, tmp_path, parse_function_type="function_calling", instance_stem="instance123")
    inst._create_actions_file()

    # read file and assert contents
    text = Path(inst._replay_action_trajs_path).read_text()
    parsed = json.loads(text)
    assert "instance123" in parsed
    actions = parsed["instance123"]
    # two assistant actions should have been recorded
    assert isinstance(actions, list) and len(actions) == 2
    assert actions[0]["message"] == "call tool"
    assert "tool_calls" in actions[0]
    assert actions[0]["tool_calls"][0]["name"] == "toolA"
    assert actions[1]["message"] == "another action"
    assert actions[1]["tool_calls"][0]["name"] == "toolB"
