# file: sweagent/agent/models.py:463-466
# asked: {"lines": [465, 466], "branches": []}
# gained: {"lines": [465, 466], "branches": []}

import json
from types import SimpleNamespace
from pathlib import Path

import pytest

from sweagent.agent.models import ReplayModel


def _make_replay_file(path: Path, replays):
    # write each replay as a JSON object on its own line
    with path.open("w", encoding="utf-8") as f:
        for i, replay in enumerate(replays):
            # put the replay under a unique key so json.loads(...).values() works as in the module
            obj = {f"r{i}": replay}
            f.write(json.dumps(obj) + "\n")


def _make_model(tmp_path, replays):
    replay_file = tmp_path / "replays.traj"
    _make_replay_file(replay_file, replays)
    # config and tools can be simple objects with required attributes
    config = SimpleNamespace(replay_path=replay_file)
    tools = SimpleNamespace(use_function_calling=False, submit_command=None)
    model = ReplayModel(config, tools)
    return model, replays


def test_next_replay_increments_and_resets(tmp_path):
    # prepare two replays; each replay can be any JSON-serializable object (here a list)
    replays = [
        [{"action": "a1"}],
        [{"action": "a2"}],
    ]
    model, expected_replays = _make_model(tmp_path, replays)

    # initial state
    assert model._replay_idx == 0
    assert model._action_idx == 0
    # ensure replays were parsed correctly
    assert model._replays == expected_replays

    # set action index to a non-zero value to ensure reset happens
    model._action_idx = 7
    model._next_replay()

    # _next_replay should increment replay index and reset action index to 0
    assert model._replay_idx == 1
    assert model._action_idx == 0


def test_next_replay_multiple_calls(tmp_path):
    # prepare three replays
    replays = [
        [{"action": "r0"}],
        [{"action": "r1"}],
        [{"action": "r2"}],
    ]
    model, expected_replays = _make_model(tmp_path, replays)

    # call _next_replay multiple times and verify _replay_idx increments each time
    model._next_replay()
    assert model._replay_idx == 1
    assert model._action_idx == 0

    model._action_idx = 2
    model._next_replay()
    assert model._replay_idx == 2
    assert model._action_idx == 0

    # calling once more should increment beyond last index (behavior: just increments)
    model._next_replay()
    assert model._replay_idx == 3
    assert model._action_idx == 0
