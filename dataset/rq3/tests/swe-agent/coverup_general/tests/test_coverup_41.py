# file: sweagent/run/run_replay.py:96-121
# asked: {"lines": [99, 101, 102, 103, 107, 109, 111, 112, 115, 116, 118], "branches": [[98, 99], [106, 107], [115, 116], [115, 118]]}
# gained: {"lines": [99, 101, 102, 103, 107, 109, 111, 112, 115, 116, 118], "branches": [[98, 99], [106, 107], [115, 116]]}

import json
import yaml
import importlib
import pytest
from types import SimpleNamespace
from pathlib import Path


@pytest.fixture(autouse=True)
def ensure_module_importable():
    try:
        mod = importlib.import_module("sweagent.run.run_replay")
    except Exception as e:
        pytest.skip(f"Module sweagent.run.run_replay not importable: {e}")
    return mod


def make_fake_classes(monkeypatch, module):
    class FakeModel:
        def __init__(self, dump_value=None):
            # store a dict to return from model_dump
            self._dump_value = dump_value or {"m": "orig"}

        def model_dump(self, mode="json"):
            return self._dump_value

    class FakeRunSingleConfig:
        last_validated = None

        def __init__(self, data):
            self._data = data
            self.agent = SimpleNamespace()
            # Always provide an object with model_dump, preserving provided dict if present
            model_dict = None
            if isinstance(data, dict) and "agent" in data and isinstance(data["agent"].get("model", None), dict):
                model_dict = data["agent"]["model"]
            self.agent.model = FakeModel(dump_value=model_dict)

        @classmethod
        def model_validate(cls, data):
            cls.last_validated = data
            return cls(data)

        def model_dump(self, mode="json"):
            # Return a JSON-serializable dict representing the config, using agent.model.model_dump()
            model_part = {"m": "orig"}
            if hasattr(self.agent.model, "model_dump"):
                model_part = self.agent.model.model_dump(mode="json")
            return {"agent": {"some": "value", "model": model_part}}

    class FakeReplayModelConfig:
        def __init__(self, replay_path):
            self.replay_path = replay_path

        def __repr__(self):
            return f"FakeReplayModelConfig(replay_path={self.replay_path!r})"

    monkeypatch.setattr(module, "RunSingleConfig", FakeRunSingleConfig, raising=True)
    monkeypatch.setattr(module, "ReplayModelConfig", FakeReplayModelConfig, raising=True)

    return FakeRunSingleConfig, FakeReplayModelConfig, FakeModel


def test_get_config_from_agent_with_string_replay_config(monkeypatch, tmp_path, ensure_module_importable):
    module = ensure_module_importable
    FakeRunSingleConfig, FakeReplayModelConfig, FakeModel = make_fake_classes(monkeypatch, module)

    inner = {"agent": {"some": "value", "model": {"m": "orig"}}}
    traj_obj = {"replay_config": json.dumps(inner)}
    traj_file = tmp_path / "traj.json"
    traj_file.write_text(json.dumps(traj_obj))

    dummy_deployment = SimpleNamespace()
    output_dir = tmp_path / "out"
    output_dir.mkdir()

    rr = module.RunReplay(traj_path=traj_file, deployment=dummy_deployment, output_dir=output_dir, update_config=None)

    config = rr.config

    assert isinstance(config.agent.model, FakeReplayModelConfig)
    assert config.agent.model.replay_path == rr._replay_action_trajs_path
    assert FakeRunSingleConfig.last_validated == inner


def test_get_config_from_agent_raises_value_error_on_missing_key(tmp_path, ensure_module_importable):
    module = ensure_module_importable

    traj_file = tmp_path / "traj_missing.json"
    traj_file.write_text(json.dumps({"not_replay_config": 1}))

    dummy_deployment = SimpleNamespace()
    output_dir = tmp_path / "out2"
    output_dir.mkdir()

    with pytest.raises(ValueError) as exc:
        module.RunReplay(traj_path=traj_file, deployment=dummy_deployment, output_dir=output_dir)

    assert "Replay config not found in trajectory. Are you running on an old trajectory?" in str(exc.value)


def test_get_config_from_agent_merges_update_config_preserving_model(monkeypatch, tmp_path, ensure_module_importable):
    module = ensure_module_importable
    FakeRunSingleConfig, FakeReplayModelConfig, FakeModel = make_fake_classes(monkeypatch, module)

    initial = {"agent": {"some": "value", "model": {"m": "orig"}}}
    traj_file = tmp_path / "traj2.json"
    traj_file.write_text(json.dumps({"replay_config": initial}))

    update_dict = {"agent": {"other_setting": "updated"}}
    update_file = tmp_path / "update.yaml"
    update_file.write_text(yaml.safe_dump(update_dict))

    dummy_deployment = SimpleNamespace()
    output_dir = tmp_path / "out3"
    output_dir.mkdir()

    rr = module.RunReplay(traj_path=traj_file, deployment=dummy_deployment, output_dir=output_dir, update_config=[update_file])

    config = rr.config

    merged = FakeRunSingleConfig.last_validated
    assert "agent" in merged
    assert "other_setting" in merged["agent"]
    assert merged["agent"]["model"] == {"m": "orig"}

    assert isinstance(config.agent.model, FakeReplayModelConfig)
    assert config.agent.model.replay_path == rr._replay_action_trajs_path
