# file: sweagent/agent/models.py:443-461
# asked: {"lines": [451, 452], "branches": [[450, 451]]}
# gained: {"lines": [451, 452], "branches": [[450, 451]]}

import json
from pathlib import Path
import pytest

from sweagent.agent.models import ReplayModel


class DummyPath:
    def exists(self):
        return False

    def __str__(self):
        return "/nonexistent/path.traj"


class DummyConfigMissing:
    def __init__(self):
        self.replay_path = DummyPath()


class DummyTools:
    def __init__(self, use_function_calling=False, submit_command=False):
        self.use_function_calling = use_function_calling
        self.submit_command = submit_command


def test_replay_model_init_raises_file_not_found():
    cfg = DummyConfigMissing()
    tools = DummyTools()
    with pytest.raises(FileNotFoundError) as exc:
        ReplayModel(cfg, tools)
    assert str(exc.value) == f"Replay file {cfg.replay_path} not found"


def test_replay_model_init_reads_file(tmp_path):
    # Prepare a replay file with two JSON lines; each JSON object has a single key whose value is the replay list
    replay_content = [
        {"a": ["action1", {"type": "cmd", "cmd": "ls"}]},
        {"b": ["action2", {"type": "cmd", "cmd": "pwd"}]},
    ]
    p = tmp_path / "test.traj"
    # Write each JSON object on its own line (keepends=True in splitlines will preserve newline)
    p.write_text("\n".join(json.dumps(obj) for obj in replay_content) + "\n")

    class Config:
        def __init__(self, path):
            self.replay_path = path

    cfg = Config(p)
    tools = DummyTools(use_function_calling=True, submit_command=True)

    model = ReplayModel(cfg, tools)

    # _replays should be a list of the inner values of each JSON object (list values)
    expected = [list(json.loads(line).values())[0] for line in p.read_text().splitlines(keepends=True)]
    assert model._replays == expected
    assert model._replay_idx == 0
    assert model._action_idx == 0
    assert model.use_function_calling is True
    assert model.submit_command is True
