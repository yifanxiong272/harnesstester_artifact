# file: sweagent/run/run_single.py:159-177
# asked: {"lines": [175, 176], "branches": [[174, 175]]}
# gained: {"lines": [175, 176], "branches": [[174, 175]]}

import importlib
from types import SimpleNamespace
import pathlib
import pytest

def test_from_config_adds_open_pr_hook(monkeypatch, tmp_path):
    module = importlib.import_module("sweagent.run.run_single")
    RunSingle = module.RunSingle

    # Prepare collectors
    load_env_calls = []
    hooks_added = []
    log_calls = []

    # Fake logger with debug method
    class FakeLogger:
        def debug(self, *args, **kwargs):
            log_calls.append((args, kwargs))

    # Fake SaveApplyPatchHook and OpenPRHook to avoid side effects
    class FakeSaveApplyPatchHook:
        def __init__(self, apply_patch_locally):
            self.apply_patch_locally = apply_patch_locally

    class FakeOpenPRHook:
        def __init__(self, pr_config):
            self.pr_config = pr_config

    # Monkeypatch module-level dependencies
    monkeypatch.setattr(module, "load_environment_variables", lambda path: load_env_calls.append(path))
    monkeypatch.setattr(module, "SaveApplyPatchHook", FakeSaveApplyPatchHook)
    monkeypatch.setattr(module, "OpenPRHook", FakeOpenPRHook)

    # Fake SWEEnv.from_config
    class FakeSWEEnv:
        @staticmethod
        def from_config(cfg):
            return "fake-env"
    monkeypatch.setattr(module, "SWEEnv", FakeSWEEnv)

    # Fake get_agent_from_config returns a simple namespace that can hold replay_config
    agent_obj = SimpleNamespace()
    def fake_get_agent_from_config(agent_cfg):
        return agent_obj
    monkeypatch.setattr(module, "get_agent_from_config", fake_get_agent_from_config)

    # Replace RunSingle.__init__ to avoid running real initialization; it should set logger and add_hook
    def fake_init(self, env, agent, problem_statement, output_dir, actions):
        # store provided values for later assertions
        self._init_args = dict(env=env, agent=agent, problem_statement=problem_statement, output_dir=output_dir, actions=actions)
        self.logger = FakeLogger()
        # add_hook appends to hooks_added list
        def add_hook(h):
            hooks_added.append(h)
        self.add_hook = add_hook
    monkeypatch.setattr(RunSingle, "__init__", fake_init)

    # Construct config object expected by from_config
    config = SimpleNamespace()
    config.env_var_path = "some/env/path"
    called_set_default = {"flag": False}
    def set_default_output_dir():
        # set an output_dir Path that will be mkdir'ed by from_config
        called_set_default["flag"] = True
        config.output_dir = tmp_path / "out"
    config.set_default_output_dir = set_default_output_dir
    # other required attributes
    config.agent = "agent-config"
    config.env = "env-config"
    config.problem_statement = "ps"
    config.actions = SimpleNamespace(apply_patch_locally=True, open_pr=True, pr_config={"pr": "cfg"})

    # Call the method under test
    result = RunSingle.from_config(config)

    # Assertions

    # from_config should return the instance we initialized
    assert result is not None
    # __init__ should have been called and stored args
    assert hasattr(result, "_init_args")
    assert result._init_args["env"] == "fake-env"
    assert result._init_args["agent"] is agent_obj
    assert result._init_args["problem_statement"] == "ps"
    assert result._init_args["actions"] is config.actions

    # load_environment_variables should have been called with the provided env_var_path
    assert load_env_calls == ["some/env/path"]

    # set_default_output_dir should have been invoked
    assert called_set_default["flag"] is True

    # output_dir.mkdir should have created the directory
    assert config.output_dir.exists() and config.output_dir.is_dir()

    # agent.replay_config should have been set to the config object
    assert getattr(agent_obj, "replay_config") is config

    # SaveApplyPatchHook and OpenPRHook should have been added via add_hook
    assert len(hooks_added) == 2
    save_hook, openpr_hook = hooks_added
    assert isinstance(save_hook, FakeSaveApplyPatchHook)
    assert save_hook.apply_patch_locally is True
    assert isinstance(openpr_hook, FakeOpenPRHook)
    assert openpr_hook.pr_config == {"pr": "cfg"}

    # logger.debug should have been called with the Adding OpenPRHook message
    found_debug = any("Adding OpenPRHook" in " ".join(map(str, args)) for (args, _kwargs) in log_calls)
    assert found_debug, f"Expected logger.debug call with 'Adding OpenPRHook', got {log_calls}"
