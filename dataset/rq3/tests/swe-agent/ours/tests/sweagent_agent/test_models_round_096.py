import json
from pathlib import Path
from types import SimpleNamespace
import pytest

from sweagent.agent.models import ReplayModel, InstanceStats


def test_missing_replay_file_round_096(tmp_path):
    """When the configured replay_path does not exist, ReplayModel.__init__ should raise FileNotFoundError
    with the exact message constructed in the code.
    """
    missing = tmp_path / "does_not_exist.traj"
    # Ensure the path truly does not exist
    if missing.exists():
        missing.unlink()

    config = SimpleNamespace(replay_path=missing)
    tools = SimpleNamespace(use_function_calling=False, submit_command=lambda *a, **k: None)

    with pytest.raises(FileNotFoundError) as exc:
        ReplayModel(config, tools)

    # exact message must match the one raised in the constructor
    assert str(exc.value) == f"Replay file {missing} not found"


def test_loads_replay_file_and_sets_fields_round_096(tmp_path):
    """When a valid replay file exists, the constructor should parse the JSON-lines and
    populate _replays, initialize indices and copy over tool flags/submit_command.
    """
    # Prepare deterministic JSON-lines content: two lines, each a JSON object whose first value is the payload
    first_payload = [{"action": "one", "value": 1}]
    second_payload = ["two", 2]
    lines = [json.dumps({"first": first_payload}) + "\n", json.dumps({"second": second_payload}) + "\n"]

    fpath = tmp_path / "replay.traj"
    fpath.write_text("".join(lines))

    # Use a simple namespace for config that provides a Path-like replay_path attribute
    config = SimpleNamespace(replay_path=fpath)

    # Provide tool-like object with attributes the constructor expects
    def fake_submit(*args, **kwargs):
        return {"ok": True}

    tools = SimpleNamespace(use_function_calling=True, submit_command=fake_submit)

    model = ReplayModel(config, tools)

    # _replays should be a list with the two first-values from each JSON object line
    assert isinstance(model._replays, list)
    assert model._replays == [first_payload, second_payload]

    # indices initialized to 0
    assert getattr(model, "_replay_idx") == 0
    assert getattr(model, "_action_idx") == 0

    # stats should be an InstanceStats instance
    assert isinstance(model.stats, InstanceStats)

    # tool flags and submit_command preserved
    assert model.use_function_calling is True
    assert model.submit_command is fake_submit

    # logger should be present (type not strictly asserted to avoid coupling to logging impl)
    assert hasattr(model, "logger")
