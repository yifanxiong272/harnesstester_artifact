# file: sweagent/agent/models.py:468-504
# asked: {"lines": [492, 498, 499, 504], "branches": [[477, 492], [497, 498], [502, 504]]}
# gained: {"lines": [492, 498, 499, 504], "branches": [[477, 492], [497, 498], [502, 504]]}

import json
from pathlib import Path

from sweagent.agent.models import ReplayModel, ReplayModelConfig


class DummyTools:
    def __init__(self, use_function_calling: bool, submit_command: str):
        self.use_function_calling = use_function_calling
        self.submit_command = submit_command


def write_replay_file(path: Path, entries):
    lines = []
    for i, actions in enumerate(entries):
        obj = {f"traj{i}": actions}
        lines.append(json.dumps(obj))
    path.write_text("\n".join(lines))
    return path


def test_index_error_triggers_formatted_submit(tmp_path):
    # Create replay file with one replay whose actions list is empty -> IndexError on first access
    replay_path = tmp_path / "replay.traj"
    write_replay_file(replay_path, [ [] ])

    cfg = ReplayModelConfig(replay_path=replay_path)
    tools = DummyTools(use_function_calling=False, submit_command="my_submit_cmd")
    model = ReplayModel(cfg, tools)

    # preconditions
    assert model._action_idx == 0
    assert model._replay_idx == 0
    assert model.stats.api_calls == 0

    res = model.query(history=[])

    # stats incremented
    assert model.stats.api_calls == 1

    # since use_function_calling is False, expect the backtick-wrapped submit command
    bt = chr(96)  # avoid literal backtick in source to prevent any parsing issues
    expected_message = bt * 3 + "\n" + tools.submit_command + "\n" + bt * 3
    assert res == {"message": expected_message}

    # action index should have been incremented by 1
    assert model._action_idx == 1


def test_submit_string_triggers_next_replay_and_returns_message(tmp_path):
    # Create replay file with one replay whose single action is the string 'submit'
    replay_path = tmp_path / "replay2.traj"
    write_replay_file(replay_path, [ ["submit"] ])

    cfg = ReplayModelConfig(replay_path=replay_path)
    tools = DummyTools(use_function_calling=False, submit_command="irrelevant")
    model = ReplayModel(cfg, tools)

    # preconditions
    assert model._replay_idx == 0
    assert model._action_idx == 0
    assert model.stats.api_calls == 0

    res = model.query(history=[])

    # should return the submit message
    assert res == {"message": "submit"}

    # calling submit should advance to next replay and reset action idx
    assert model._replay_idx == 1
    assert model._action_idx == 0

    # stats incremented
    assert model.stats.api_calls == 1
